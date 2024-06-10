import os
import io
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
from reportlab.platypus import Paragraph
from reportlab.lib.colors import Color
import json
import powerlog
from powerlog import logger,verbose_print, info_print, error_print, variable_str, debug_print,warning_print
from pypdf import PdfReader
import math
import re
from shapely.geometry import Polygon
from difflib import SequenceMatcher
import pytesseract
from PIL import Image
import pandas as pd
from colorama import Fore, Style

# 透明色を定義（赤、緑、青、アルファ）
transparent_color = Color(0, 0, 0, alpha=0)

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
parser.add_argument('--hfont','-hf', default='NotoSansJP-Regular.ttf', help='Sets horizontal font (default is NotoSansJP-Regular.ttf)')
parser.add_argument('--vfont','-vf', default='NotoSansJP-Regular.ttf', help='Sets vertical font (default is NotoSansJP-Regular.ttf)')
parser.add_argument('--dpi','-d', type=int, default=600, help='文書のDPIを指定します（デフォルトは600）')
parser.add_argument('--page','-p', choices=list(page_sizes.keys()), help='The page size of the PDF.')
parser.add_argument('--layout', choices=['word', 'line', 'paragraph'], default='line', help='Choose the level of text to draw: word, line, or paragraph(at the monent paragraph is unusable).')
parser.add_argument('--area','-ar', type=float, default=80,
                    help='area threshold for counting lines in a paragraph. default is 80')
parser.add_argument('--similarity', '-st', type=float, default=0.1, 
                    help='Set the similarity threshold for adding lines to a paragraph. Default is 0.1')
parser.add_argument('--adjust', '-ad', action='store_true', help='adjust the layout of lines and paragraphs. Experimental!!!Default is False')
parser.add_argument('--coordinate', '-ct', type=float, default=80,help='Set the coordinate threshold for coordinate adjustment for lines and paragraph. Default is 80')
parser.add_argument('--HV-threshold', '-hv', type=float, default=0.1, help='Set the threshold for horizontal and vertical text. Default is 0.1')
parser.add_argument('--clear','-c', action='store_true', help='output clear text PDF')
args = parser.parse_args()

powerlog.set_log_level(args)

# area/coordinate/similarity thresholdの値をパーセンテージから小数に変換
args.area /= 100.0
args.coordinate /= 100.0
args.similarity /= 100.0

# tesseractが使えるか確認
try:
    # pytesseractのget_tesseract_version関数を使用してTesseractのバージョンを取得
    pytesseract.get_tesseract_version()
    verbose_print(Fore.GREEN+'Tesseract is available.'+Style.RESET_ALL)
except pytesseract.TesseractNotFoundError:
    # Tesseractが見つからない場合、--adjustオプションを無効化
    if args.adjust:
        print("Warning: Tesseract not found. The --adjust option will be disabled.")
        args.adjust = False

# OSに適した改行文字を取得
newline = os.linesep

# 文字列の類似度を計算する関数pyt
def similarity(a, b):
    return SequenceMatcher(None, a, b).ratio()

# DPI変換のための係数を設定
DPI_CONVERSION_FACTOR = args.dpi / 72

# ポイントをインチに変換する係数
INCH_TO_POINT = 72

# 単位系からポイントへの変換係数を定義
unit_to_point_conversion_factors = {
    'inch': 72,  # 1インチ = 72ポイント
    # 必要に応じて他の単位系を追加
}

# レイアウトオプションをtesseractレベルに変換
level_dict = {'word': 5, 'line': 4, 'paragraph': 3}
level = level_dict[args.layout]

# フォントのパスを取得する関数
def get_font_path(get_font_name, font_type):
    font_path = './data/fonts/' + get_font_name
    if not os.path.splitext(get_font_name)[1]:  # 拡張子がない場合
        # デフォルトの拡張子を追加
        font_path += '.ttf'
    return font_path

# check if origin of bbox is bottom_right　(Some vertical texts, ex: English has a bounding box origin in bottom right.)
def is_origin_bottom_right(bbox_chk_coords):
    # バウンディングボックスの4つの点の座標を取得
    top_left, top_right, bottom_left, bottom_right = bbox_chk_coords

    # 右下の点が左下の点より右にあり、かつ、右上の点より下にあるか確認
    if bottom_right[0] >= bottom_left[0] and bottom_right[1] <= top_right[1]:
        return True

    # それ以外の場合、右下が起点となっていない
    return False

# check origin and direction of polygon
def determine_origin(bbox_chk_coords):
    # バウンディングボックスの4つの点の座標を取得
    bbox1, bbox2, bbox3, bbox4 = bbox_chk_coords

    # ポリゴンを作成
    poly = Polygon(bbox_chk_coords)

    # ポリゴンの重心を計算
    centroid = poly.centroid

    angles = []
    positions = []
    for bbox in bbox_chk_coords:
        position = None
        # 重心とbbox1との角度を計算
        angle = math.atan2(bbox[1] - centroid.y, bbox[0] - centroid.x)
        angles.append(angle)
        # 角度から起点を判断
        if 0 < angle <= math.pi /2:
            position = "top_right"
        elif math.pi /2 < angle <= math.pi or angle == - math.pi:
            origin = "top_left"
        elif - math.pi < angle <= - math.pi/2:
            position = "bottom_left"
        elif - math.pi/2 < angle <= 0:
            position = "bottom_right"
        else:
            position = "unknown"
        positions.append(position)
    angle_diffs = [(angles[i] - angles[i-1] + math.pi) % (2*math.pi) - math.pi for i in range(1, len(angles))]
    if all(angle_diffs) > 0:
        polygon_direction = "clockwise"
    elif all(angle_diffs) < 0:
        polygon_direction = "counterclockwise"
    else:
        polygon_direction = "diagonal"

    origin = positions [0]
    return origin, polygon_direction



# 横書き用のフォントを登録
h_font_name = args.hfont
h_font_path = get_font_path(h_font_name, 'h')
info_print(f'Horizontal font: {h_font_name}')
pdfmetrics.registerFont(TTFont(h_font_name, h_font_path))

# 縦書き用のフォントを登録
v_font_name = args.vfont
v_font_path = get_font_path(v_font_name, 'v')
info_print(f'Vertical font: {v_font_name}')
pdfmetrics.registerFont(TTFont(v_font_name, v_font_path))

# フォントサイズの係数を取得（デフォルトは1.0）
font_size_factor = 1.0 if args.size is None else args.size / 100.0

# フォントサイズ変化の閾値を取得（デフォルトはNone）
font_size_change_threshold = None if args.font_threshold is None else args.font_threshold / 100.0

# 水平方向と垂直方向のテキストの閾値を取得
hv_threshold = args.HV_threshold
info_print(f'Horizontal and vertical text threshold: {hv_threshold}')

# 座標間の距離を計算
def calculate_distance(x1, y1, x2, y2):
    return math.sqrt((x2 - x1)**2 + (y2 - y1)**2)

# 入力フォルダと出力フォルダのパスを設定
json_folder = './DIjson'
if not os.path.exists(json_folder):
    os.makedirs(json_folder,exist_ok=True)
    print(f'Created {json_folder} folder')
else:
    print(f'{json_folder} folder already exists')

if not args.clear:
    output_folder = './OCRtextPDF'
    if not os.path.exists(output_folder):
        os.makedirs(output_folder,exist_ok=True)
        print(f'Created {output_folder} folder')
    else:
        print(f'{output_folder} folder already exists')
else:
    output_folder = './OCRclearPDF'
    if not os.path.exists(output_folder):
        os.makedirs(output_folder,exist_ok=True)
        print(f'Created {output_folder} folder')
    else:
        print(f'{output_folder} folder already exists')

optpdf_folder = Path('./OptimizedPDF')
optimized_folder = Path('./TEMP/optimized')

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

        #元画像のフォルダ
        image_folder = optimized_folder / json_file.replace('.pdf.json', '')

        # フォルダが存在することを確認
        if not image_folder.exists():
            args.adjust = False
            warning_print(f"Warning: Folder {image_folder} does not exist.--adjust option will be disabled.")

        # image_folder内の画像ファイルをアルファベット順にソート
        image_files = sorted(image_folder.glob('*.jp2'))

        # 画像ファイルが存在することを確認
        if not image_files:
            args.adjust = False
            print(f"Error: No image files found in {image_folder}.--adjust option will be disabled.")

        # Check if 'analyzeResult' key exists: json downloaded from web has ''key, json created from API does not.
        if 'analyzeResult' in ocr_data:
            analyze_result = ocr_data['analyzeResult']
        else:
            analyze_result = ocr_data  # Treat the whole JSON as the content of 'analyzeResult'

        # 新しいPDFファイル名を設定（'.pdf' を削除してから '_TextOnly.pdf' を追加）
        base_filename = os.path.splitext(json_file)[0]
        base_filename = base_filename.replace('.pdf', '')  # '.pdf' を削除
        if args.clear:
            new_pdf_filename = base_filename + '_ClearText.pdf'
        else:
            new_pdf_filename = base_filename + '_TextOnly.pdf'
        new_pdf_path = os.path.join(output_folder, new_pdf_filename)

        # ReportLabのキャンバスを作成
        c = canvas.Canvas(new_pdf_path, pagesize=page_size)

        info_print(f'Creating PDF file {new_pdf_filename}...')
        info_print(f'Layout: {args.layout}')

        # 各ページを処理
        for i, page in enumerate(analyze_result['pages']):
            page_number = page['pageNumber']
            # Document Intelligenceの単位系を取得
            di_unit = page['unit']
            # 単位系からポイントへの変換係数を取得
            unit_to_point_conversion_factor = unit_to_point_conversion_factors.get(di_unit, 1)  # デフォルトは1
            # ページサイズを取得
            page_width = page['width'] * unit_to_point_conversion_factor
            page_height = page['height'] * unit_to_point_conversion_factor
            c.setPageSize((page_width, page_height))

            verbose_print(f'Processing page {page_number}...')

            # iがimage_filesの長さを超えないようにする
            if args.adjust and i<len(image_files):
                tesseract_ocr = pytesseract.image_to_data(Image.open(image_files[i]))
                image = Image.open(image_files[i])
                verbose_print(f'performing_osd for page {page_number} and {i} with tesseract: {tesseract_ocr}')
                # 画像のサイズ（ピクセル単位）を取得
                image_width, image_height = image.size
                debug_print(f'image size: {image.size}')
            elif args.adjust:
                error_print(f"Image file not found for page {page_number}.in {image_folder}")

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

            if args.adjust and i<len(image_files):
                tesseract_bboxes = []

                # pandasを使用してデータを解析
                read_tess_data = pd.read_csv(io.StringIO(tesseract_ocr), sep='\t', quotechar='"', on_bad_lines='skip', engine='python')

                # 'bbox'情報が含まれる行を抽出
                bbox_data = read_tess_data[read_tess_data['level'] == level]

                # 各行のbbox情報を取得
                for index, row in bbox_data.iterrows():
                    bbox = [row['left'], row['top'], row['width'], row['height']]
                    tesseract_bboxes.append(bbox)
                debug_print(f'tesseract_bboxes: {tesseract_bboxes}')


                # bboxリストをcoordsリストに変換
                bbox_coords = []
                # tesseractのピクセル単位の座標系をDocument Intelligenceの座標系(以前に取取得)に変換
                tess_to_di_conversion_factor = unit_to_point_conversion_factor / (args.dpi*max(image_width, image_height))
                for tesseract_bbox in tesseract_bboxes:
                    x, y, width, height = tesseract_bbox
                    x /= image_width
                    y /= image_height
                    width /= image_width
                    height /= image_height
                    bbox_to_polygon_coords = [(x, y), (x + width, y), (x + width, y + height), (x, y + height), (x, y)]
                    bbox_coords.append(bbox_to_polygon_coords)

            #メイン処理
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
                        if similarity(line['content'], paragraph_text) >= args.similarity:
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
                            error_print(f'similarity threshold: {args.similarity}')

                        prev_line_bottom = line_bottom
                else:
                    text = item['content']
                    polygon = item['polygon']
                    # itemのpolygonを座標のペアのリストに変換
                    item_polygon_coords = [(polygon[i], polygon[i + 1]) for i in range(0, len(polygon), 2)]
                    item_polygon = Polygon(item_polygon_coords)
                    debug_print(f'item_polygon: {item_polygon_coords}')
                    
                    if args.adjust and i<len(image_files):
                        # tesseract_の座標とitemのpolygonを比較
                        for tesseract_polygon_coord in bbox_coords:
                            tesseract_polygon = Polygon(tesseract_polygon_coord)
                            debug_print(f'tesseract_polygon coord: {tesseract_polygon_coord}')

                        # tesseractの座標とitemのpolygonが重なっている割合を計算
                            ocr_intersection = item_polygon.intersection(tesseract_polygon).area
                            ocr_overlap = ocr_intersection / item_polygon.area
                            debug_print(f'ocr_overlap: {ocr_overlap}for item {text}')

                            # 重なっている割合が閾値を超えている場合、tesseractの座標を使用
                            if ocr_overlap > args.coordinate:  
                                item_polygon = tesseract_polygon
                                verbose_print(f'Using osd polygon for item {text}')
                                break

                x1, y1, x2, y2, x3, y3, x4, y4 = [v * unit_to_point_conversion_factor for v in polygon]
                bbox_chk_coords = [(x1,y1),(x2,y2),(x3,y3),(x4,y4)]
                origin, polygon_direction = determine_origin(bbox_chk_coords)
                if origin == "unknown" or polygon_direction == "diagonal":
                    error_print(f'Unknown origin or diagonal polygon for item {text}. Layout may be incorrect.')
                
                # 座標間の距離を計算
                distances = [
                    (calculate_distance(x1, y1, x2, y2), ((x1, y1), (x2, y2))),
                    (calculate_distance(x2, y2, x3, y3), ((x2, y2), (x3, y3))),
                    (calculate_distance(x3, y3, x4, y4), ((x3, y3), (x4, y4))),
                    (calculate_distance(x4, y4, x1, y1), ((x4, y4), (x1, y1))),
                    (calculate_distance(x1, y1, x3, y3), ((x1, y1), (x3, y3))),
                    (calculate_distance(x2, y2, x4, y4), ((x2, y2), (x4, y4)))
                ]

                # 長さ順に並べ替え
                distances.sort(key=lambda x: x[0])

                # 最後の2つが対角線、次の2つが長辺、最初の2つが短辺
                diagonals = distances[-2:]
                long_sides = distances[2:4]
                short_sides = distances[:2]
                # 長辺と短辺の長さを取得
                long_side_length = (long_sides[0][0]+long_sides[1][0])/2
                short_side_length = (short_sides[0][0]+short_sides[1][0])/2

                if origin == "bottom_left":
                    origin_offset = 0
                elif origin == "bottom_right":
                    origin_offset = 1
                elif origin == "top_right":
                    origin_offset = 2
                elif origin == "top_left":
                    origin_offset = 3
                else:
                    origin_offset = 0
                # 長辺と短辺が近似的に等しいかどうかをチェック
                if args.layout == 'word' or args.layout == 'line':
                    if abs(long_side_length - short_side_length) / long_side_length < 0.6:
                        rotation = 0
                if args.layout == 'paragraph':
                    if abs(long_side_length - short_side_length)/long_side_length < hv_threshold:
                        rotation = 0
                else:
                    if abs(y3 - y1) < abs(x3 - x1):
                        rotation = math.degrees(math.atan2(y1 - y2, x2 - x1)) + 90 * origin_offset
                    else:
                        rotation = math.degrees(math.atan2(y2 - y3, x3 - x2)) + 90 * origin_offset
                    if -180 <= rotation <= -135 or -45 <= rotation <= 45 or 135 <= rotation <= 180:
                        script_direction = 'horizontal'
                    else:
                        script_direction = 'vertical'
                        rotation += 180

                debug_print(f'text' + text + 'is' + script_direction)
                debug_print(f'Is Japanese?:{is_japanese(text)}')
                debug_print(f'Origin and rotation is:{determine_origin(bbox_chk_coords)}')

                # フォントサイズを計算（高さに係数を適用）
                font_size = short_side_length * font_size_factor
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
                if script_direction == 'horizontal':
                    font_name = h_font_name
                else:
                    font_name = v_font_name
                prev_font_size = font_size

                if args.layout == 'word' or args.layout == 'line':
                    c.setFont(font_name, font_size)
                    string_width = c.stringWidth(text, font_name, font_size)
                    scale = long_side_length / string_width
                else:
                    c.setFont(font_name, font_size)
                    string_width = c.stringWidth(text, font_name, font_size)
                    scale = 1

                # フォントの上昇と下降を取得
                font = pdfmetrics.getFont(font_name)
                ascent = font.face.ascent * (font_size / 1000.0)
                descent = font.face.descent * (font_size / 1000.0)

                # 描画原点を設定
                x = x1
                y = page_height - y1 - ascent        

                c.saveState()  # 現在の状態を保存
                c.translate(x, y)  # 描画原点を移動
                if script_direction == 'vertical':
                    if is_japanese(text):  # 文字が日本語の場合
                        c.scale(1,scale )  # 垂直方向にスケール変換
                        c.rotate(rotation+180)
                    else:  # 文字が英語の場合
                        c.scale(scale, 1)  # 水平方向にスケール変換
                        c.rotate(rotation+180)
                else:
                    c.scale(scale, 1)
                    c.rotate(rotation)
                if args.clear:
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
info_print(f'font_threshold:{font_size_change_threshold}, individual:{args.individual}, layout:{args.layout}, HV-threshold:{hv_threshold}')