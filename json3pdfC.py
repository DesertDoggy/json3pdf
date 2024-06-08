import os
import argparse
from pathlib import Path
import logging
import glob
from datetime import datetime
import sys
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A3, A4, A5, A6, B4, B5, B6, B7, letter 
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.colors import Color
import json
import powerlog
from powerlog import logger,verbose_print, info_print, error_print, variable_str, debug_print
from pypdf import PdfReader
import math
import re
from shapely.geometry import Polygon
from difflib import SequenceMatcher

# 文字が日本語かどうかを判断する関数
def is_japanese(text):
    return bool(re.search(r'[\u3040-\u30ff\u3400-\u4dbf\u4e00-\u9fff\uf900-\ufaff\uff66-\uff9f]', text))

# ページサイズの辞書を作成
page_sizes = {
    "A3": (842, 1191),
    "A4": (595, 842),
    "A5": (420, 595),
    "A6": (298, 420),
    "B4": (729, 1032),
    "B5": (516, 729),
    "B6": (363, 516),
    "B7": (258, 363),
    "Tabloid": (792, 1224),  # タブロイド判のサイズ（11 x 17インチをポイントに変換）
    "Blanket": (4320, 6480)  # ブランケット判のサイズ（60 x 90インチをポイントに変換）
}

# コマンドライン引数を解析する
parser = powerlog.create_parser()
parser = argparse.ArgumentParser(description='PDFファイルにテキストを書き込む')
parser.add_argument('--log-level', '-log', default='INFO', choices=['DEBUG', 'VERBOSE', 'INFO', 'WARNING'],
                    help='Set the logging level (default: INFO)')
parser.add_argument('-debug', action='store_const', const='DEBUG', dest='log_level',
                    help='Set the logging level to DEBUG')
parser.add_argument('-s', '--size', type=int, help='フォントのサイズの調整（デフォルトは100）単位は%')
# 排他的なオプショングループを作成
font_threshold = parser.add_mutually_exclusive_group()
font_threshold.add_argument('--font-threshold','-t',default=None, type=int, help='連続した単語や行のフォントサイズ変更の閾値を指定します。単位は%')
font_threshold.add_argument('--individual', action='store_true', help='各単語のフォントサイズを個別に設定します')
parser.add_argument('-f', '--font', default='NotoSansJP-Regular', help='使用するフォントの名前を指定します（デフォルトはNotoSansJP-Regular）')
parser.add_argument('-d', '--dpi', type=int, default=600, help='文書のDPIを指定します（デフォルトは600）')
parser.add_argument('--page','-p', choices=list(page_sizes.keys()), help='The page size of the PDF.')
parser.add_argument('--layout', choices=['word', 'line', 'paragraph'], default='line', help='Choose the level of text to draw: word, line, or paragraph.')
parser.add_argument('--area', type=float, default=80,
                    help='areathreshold for counting lines in a paragraph. default is 80')
parser.add_argument('--similarity-threshold', '-st', type=float, default=0.1, 
                    help='Set the similarity threshold for adding lines to a paragraph. Default is 0.1')
args = parser.parse_args()

powerlog.set_log_level(args)

# 透明色を定義（赤、緑、青、アルファ）
transparent_color = Color(0, 0, 0, alpha=0)

# areaの値をパーセンテージから小数に変換
args.area /= 100.0

# OSに適した改行文字を取得
newline = os.linesep

# 文字列の類似度を計算する関数pyt
def similarity(a, b):
    return SequenceMatcher(None, a, b).ratio()

# similarity thresholdの値をパーセンテージから小数に変換
args.similarity_threshold /= 100.0

# DPI変換のための係数を設定
DPI_CONVERSION_FACTOR = args.dpi / 72

# ポイントをインチに変換する係数
INCH_TO_POINT = 72

# フォント名とパス
font_name = args.font
font_path = './data/fonts/' + font_name + '.ttf'

# フォントを登録
pdfmetrics.registerFont(TTFont(font_name, font_path))

# フォントサイズの係数を取得（デフォルトは1.0）
font_size_factor = 1.0 if args.size is None else args.size / 100.0

# フォントサイズ変化の閾値を取得（デフォルトはNone）
font_size_change_threshold = None if args.font_threshold is None else args.font_threshold / 100.0

# 入力フォルダと出力フォルダのパスを設定
json_folder = './DIjson'
if not os.path.exists(json_folder):
    os.makedirs(json_folder,exist_ok=True)
    print(f'Created {json_folder} folder')
else:
    print(f'{json_folder} folder already exists')
output_folder = './OCRclearPDF'
if not os.path.exists(output_folder):
    os.makedirs(output_folder,exist_ok=True)
    print(f'Created {output_folder} folder')
else:
    print(f'{output_folder} folder already exists')

optpdf_folder = Path('./OptimizedPDF')

# 入力フォルダ内の全てのJSONファイルを取得
json_files = [f for f in os.listdir(json_folder) if f.endswith('.pdf.json')]

# JSONファイルの総数を取得し、コンソールに表示
total_json_files = len(json_files)
info_print(f'Total JSON files: {total_json_files}')

# PDFファイルのカウンターを初期化
pdf_counter = 0

def test_similarity():
    assert similarity("hello", "hello") == 1.0
    assert similarity("hello", "hEllo") < 1.0
    assert similarity("hello", "world") < 1.0

test_similarity()

for json_file in json_files:
    # OCR結果のJSONファイル名を設定
    ocr_json_path = os.path.join(json_folder, json_file)

    # JSONファイルが存在する場合のみ処理を実行
    if os.path.exists(ocr_json_path):
        with open(ocr_json_path, 'r', encoding='utf-8') as f:
            ocr_data = json.load(f)

        # OCR元のPDFファイル名を設定
        ocr_pdf_path = optpdf_folder / json_file.replace('.json', '')

        # PDFファイルが存在する場合のみページサイズを読み取る

        if args.page is not None:
            page_size = page_sizes[args.size]
        else:
            if ocr_pdf_path.exists():
                with open(ocr_pdf_path, 'rb') as f:
                    pdf = PdfReader(f)
                    page = pdf.pages[0]
                    width_pt = page.mediabox[2]
                    height_pt = page.mediabox[3]
                    # ページサイズを辞書から探す
                    for size, (w, h) in page_sizes.items():
                        if abs(width_pt - w) < 1 and abs(height_pt - h) < 1:
                            page_size = size
                            break
            # ページサイズが見つからない場合はA5に設定
            else:
                page_size = 'A5'

        # Check if 'analyzeResult' key exists: json downloaded from web has ''key, json created from API does not.
        if 'analyzeResult' in ocr_data:
            analyze_result = ocr_data['analyzeResult']
        else:
            analyze_result = ocr_data  # Treat the whole JSON as the content of 'analyzeResult'

        # 新しいPDFファイル名を設定（'.pdf' を削除してから '_ClearText.pdf' を追加）
        base_filename = os.path.splitext(json_file)[0]
        base_filename = base_filename.replace('.pdf', '')  # '.pdf' を削除
        new_pdf_filename = base_filename + '_ClearText.pdf'
        new_pdf_path = os.path.join(output_folder, new_pdf_filename)

        # ReportLabのキャンバスを作成
        c = canvas.Canvas(new_pdf_path, pagesize=page_size)

        # 各ページを処理
        for page in analyze_result['pages']:
            page_number = page['pageNumber']
            page_width = page['width'] * INCH_TO_POINT
            page_height = page['height'] * INCH_TO_POINT
            c.setPageSize((page_width, page_height))
            # 各単語を処理
            if args.layout == 'word':
                items = page['words']
            elif args.layout == 'line':
                items = page['lines']
            elif args.layout == 'paragraph':
                items = [p for p in analyze_result['paragraphs'] if p['boundingRegions'][0]['pageNumber'] == page_number]
                lines = page['lines']
                # Create a copy of lines list to manipulate it
                lines_copy = lines.copy()

            prev_font_size = None
            for item in items:
                if args.layout == 'paragraph':
                    paragraph_text = item['content']
                    debug_print(f'paragraph_text: {paragraph_text}') 
                    text = ''
                    polygon = item['boundingRegions'][0]['polygon']
                    line_count = 0
                    item_polygon_coords = [(polygon[i], polygon[i + 1]) for i in range(0, len(polygon), 2)]
                    item_polygon = Polygon(item_polygon_coords)
                    prev_line_bottom = None

                    for line in lines_copy:
                        debug_print(f'checking line: {line}')
                        line_polygon_coords = [(line['polygon'][i], line['polygon'][i + 1]) for i in range(0, len(line['polygon']), 2)]
                        line_polygon = Polygon(line_polygon_coords)
                        line_bottom = min(line_polygon_coords, key=lambda coord: coord[1])[1]
                        if prev_line_bottom is not None and line_bottom < prev_line_bottom:
                            text += newline

                        # Only add line content to text if it matches the similarity threshold or more with a part of the paragraph text
                        if similarity(line['content'], paragraph_text) >= args.similarity_threshold:
                            text += line['content']
                            debug_print(f'Added line content: {line["content"]}') 
                            # Remove the line from lines_copy list after adding its content to text
                            lines_copy.remove(line)
                            line_count += 1
                            debug_print(f'line_count: {line_count}')

                            # Remove the same content from paragraph_text
                            paragraph_text = paragraph_text.replace(line['content'], '', 1)
                            debug_print(f'Remaining paragraph_text: {paragraph_text}')

                            # If paragraph_text is empty, break the loop to move to the next item
                            if not paragraph_text:
                                debug_print('No more content in paragraph_text. Moving to the next item.')
                                break
                        else:
                            error_print(f'Line content does not match the similarity threshold: {line["content"]}')
                            error_print(f'similarity threshold: {args.similarity_threshold}')

                        prev_line_bottom = line_bottom
                else:
                    text = item['content']
                    polygon = item['polygon']
                    # itemのpolygonを座標のペアのリストに変換
                    item_polygon_coords = [(polygon[i], polygon[i + 1]) for i in range(0, len(polygon), 2)]
                    item_polygon = Polygon(item_polygon_coords)

                x1, y1, x2, y2, x3, y3, x4, y4 = [v * INCH_TO_POINT for v in polygon]
                rotation = item.get('rotation', 0)
                # 文字の向きを決定
                if math.isclose(x1, x4) and math.isclose(y2, y3):  # 垂直
                    x, y = x1, page_height - y1
                    width = abs(y3 - y1)
                    height = abs(x3 - x1)
                elif math.isclose(y1, y2) and math.isclose(x3, x4):  # 水平
                    x, y = x1, page_height - y1
                    width = abs(x3 - x1)
                    height = abs(y3 - y1)
                else:  # 斜め
                    x, y = x1, page_height - y1
                    width = math.sqrt((x2 - x1)**2 + (y2 - y1)**2)
                    height = math.sqrt((x4 - x1)**2 + (y4 - y1)**2)

                # フォントサイズを計算（高さに係数を適用）
                font_size = height * font_size_factor
                if args.layout == 'line':
                    font_size *= 0.9  # 行のフォントサイズのデフォルト係数、テスト環境で決定した数値
                    font_size *= (1 - 0.1 * (len(text) / 100))  # フォントサイズを微調整
                elif args.layout == 'paragraph':
                    if line_count > 0:
                        font_size /= line_count
                    else:
                        error_print("No lines were counted. Cannot calculate font size.")                    
                        font_size += 0  # 段落のフォントサイズを行数で調整

                # 前の単語と比較してフォントサイズが閾値以上変化した場合にのみフォントサイズを変更
                if not args.individual and prev_font_size is not None and font_size_change_threshold is not None and abs(font_size - prev_font_size) / prev_font_size > font_size_change_threshold:
                    font_size = prev_font_size

                prev_font_size = font_size

                if args.layout == 'word' or args.layout == 'line':
                    c.setFont(font_name, font_size)
                    string_width = c.stringWidth(text, font_name, font_size)
                    scale = width / string_width
                else:
                    c.setFont(font_name, font_size)
                    string_width = c.stringWidth(text, font_name, font_size)
                    scale = 1

                # フォントの上昇と下降を取得
                font = pdfmetrics.getFont(font_name)
                ascent = font.face.ascent * (font_size / 1000.0)
                descent = font.face.descent * (font_size / 1000.0)

                # yの位置を調整
                y += descent

                c.saveState()  # 現在の状態を保存
                c.translate(x, y)  # 描画原点を移動
                c.rotate(rotation)  # 文字の向きに合わせて回転
                if is_japanese(text):  # 文字が日本語の場合
                    c.scale(1, scale)  # 垂直方向にスケール変換
                else:  # 文字が英語の場合
                    c.scale(scale, 1)  # 水平方向にスケール変換
                # テキストの色を透明に設定
                c.setFillColor(transparent_color)
                c.drawString(0, 0, text)  # 描画原点から文字を描画
                c.restoreState()

            # 次のページに移動
            c.showPage()

        # PDFファイルを保存
        c.save()

        # PDFファイルのカウンターを増やす
        pdf_counter += 1

        # PDFファイルが作成されたことを表示（何個目/総数の形で表示）
        info_print(f'PDF file {new_pdf_filename} has been created. ({pdf_counter}/{total_json_files})')
else:
    # JSONファイルが存在しないことを表示
    info_print(f'No JSON files found, so no PDF file was created.')

info_print('All PDF file processing is complete.')

