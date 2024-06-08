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
parser.add_argument('-s', '--size', type=int, default=8, help='フォントのサイズを指定します（デフォルトは60）')
parser.add_argument('-f', '--font', default='NotoSansJP-Regular', help='使用するフォントの名前を指定します（デフォルトはNotoSansJP-Regular）')
parser.add_argument('-d', '--dpi', type=int, default=600, help='文書のDPIを指定します（デフォルトは600）')
parser.add_argument('--page','-p', choices=list(page_sizes.keys()), help='The page size of the PDF.')
args = parser.parse_args()

powerlog.set_log_level(args)

# DPI変換のための係数を設定
DPI_CONVERSION_FACTOR = args.dpi / 72

# ポイントをインチに変換する係数
INCH_TO_POINT = 72

# フォント名とパス
font_name = args.font
font_path = './data/fonts/' + font_name + '.ttf'

# フォントを登録
pdfmetrics.registerFont(TTFont(font_name, font_path))

# 入力フォルダと出力フォルダのパスを設定
json_folder = './DIjson'
if not os.path.exists(json_folder):
    os.makedirs(json_folder,exist_ok=True)
    print(f'Created {json_folder} folder')
else:
    print(f'{json_folder} folder already exists')
output_folder = './OCRtextPDF'
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

        # 新しいPDFファイル名を設定（'.pdf' を削除してから '_TextOnly.pdf' を追加）
        base_filename = os.path.splitext(json_file)[0]
        base_filename = base_filename.replace('.pdf', '')  # '.pdf' を削除
        new_pdf_filename = base_filename + '_TextOnly.pdf'
        new_pdf_path = os.path.join(output_folder, new_pdf_filename)

        # ReportLabのキャンバスを作成
        c = canvas.Canvas(new_pdf_path, pagesize=page_size)

        # 各ページを処理
        for page in analyze_result['pages']:
            page_number = page['pageNumber']
            page_width = page['width'] * INCH_TO_POINT
            page_height = page['height'] * INCH_TO_POINT
            c.setPageSize((page_width, page_height))

            # 処理用の辞書を作成
            unprocessed_words = {i: word for i, word in enumerate(page['words'])}
            unprocessed_lines = {i: line for i, line in enumerate(page['lines'])}
            unprocessed_paragraphs = {i: paragraph for i, paragraph in enumerate(analyze_result['paragraphs'])}           

            # 各パラグラフを処理
            for paragraph_index in sorted(unprocessed_paragraphs.keys()):
                paragraph = unprocessed_paragraphs[paragraph_index]
                paragraph_text = ""  # パラグラフのテキストを初期化
                word_positions = []  # 各単語の位置情報を保存するリストを初期化

                # 各行を処理
                for line_index in sorted(unprocessed_lines.keys()):
                    line = unprocessed_lines[line_index]
                    line_text = ""  # 行のテキストを初期化

                    # 各単語を処理
                    for word_index in sorted(unprocessed_words.keys()):
                        word = unprocessed_words[word_index]

                        # 単語が現在の行に属しているか確認
                        if word['content'] in line['content']:
                            text = word['content']
                            line_text += text + " "  # 行のテキストに単語を追加

                            # 単語の位置情報を保存
                            x = word['polygon'][0] * INCH_TO_POINT
                            y = page_height - (word['polygon'][1] * INCH_TO_POINT)
                            width = (word['polygon'][2] - word['polygon'][0]) * INCH_TO_POINT
                            height = (word['polygon'][3] - word['polygon'][1]) * INCH_TO_POINT
                            word_positions.append((x, y, width, height))

                            # 処理が終わった単語を辞書から削除
                            del unprocessed_words[word_index]

                    # 行のテキストをパラグラフのテキストに追加
                    paragraph_text += line_text + "\n"  # 改行を追加

                    # 処理が終わった行を辞書から削除
                    del unprocessed_lines[line_index]

                # パラグラフのテキストを描画
                for (x, y, width, height), text in zip(word_positions, paragraph_text.split()):
                    font_size = args.size if args.size else height
                    c.setFont(font_name, font_size)
                    scale = width / c.stringWidth(text, font_name, font_size)
                    c.saveState()  # 現在の状態を保存
                    c.translate(x, y)  # 描画原点を移動
                    c.scale(scale, 1)  # 水平方向にスケール変換
                    c.drawString(0, 0, text)  # 描画原点から文字を描画
                    c.restoreState()

                # 処理が終わったパラグラフを辞書から削除
                del unprocessed_paragraphs[paragraph_index]
            
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
