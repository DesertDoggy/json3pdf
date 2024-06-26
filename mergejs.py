import os
import argparse
from pathlib import Path
import logging
import glob
from datetime import datetime
from PyPDF2 import PdfReader, PdfWriter,PdfMerger
import powerlog
from powerlog import logger,verbose_print, info_print, error_print, variable_str, debug_print

# コマンドライン引数を解析する
parser = powerlog.create_parser()
parser = argparse.ArgumentParser(description='Add a text layer to a PDF file.')
parser.add_argument('--log-level', '-log', default='DEBUG', choices=['DEBUG', 'VERBOSE', 'INFO', 'WARNING'],
                    help='Set the logging level (default: DEBUG)')
parser.add_argument('-debug', action='store_const', const='INFO', dest='log_level',
                    help='Set the logging level to DEBUG')
groupLR = parser.add_mutually_exclusive_group(required=False)
groupLR.add_argument('--left', '-l', type=int, help='Number of points to move to the left (1 inch = 72 pt, 1 cm = 28.35 pt)')
groupLR.add_argument('--right', '-r', type=int, help='Number of points to move to the right (1 inch = 72 pt, 1 cm = 28.35 pt)')

groupUD = parser.add_mutually_exclusive_group(required=False)
groupUD.add_argument('--up', '-u', type=int, help='Number of points to move up (1 inch = 72 pt, 1 cm = 28.35 pt)')
groupUD.add_argument('--down', '-d', type=int, help='Number of points to move down (1 inch = 72 pt, 1 cm = 28.35 pt)')
parser.add_argument('--dpi', type=int, default=600, help='Specify the DPI of the document. The default is 600dpi.')
parser.add_argument('--threshold', '-t', default='Blanket', help='Specify the threshold page size incase dpi is not correct.Default is Blanket(Newspaper size).')
parser.add_argument('--clear', '-c', action='store_true', help='Merge clear text PDF to Original PDF.')
parser.add_argument('--process-pages', '-p', type=int, default=50, help='Number of pages to process.')
args = parser.parse_args()

powerlog.set_log_level(args)
process_num_pages = args.process_pages

# DPI変換係数を設定
units_per_inch = args.dpi
dpi_conversion_factor = 72 / args.dpi

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

# 閾値となるページサイズを設定
if args.threshold in page_sizes:
    threshold_page_size = tuple(size * 2 for size in page_sizes[args.threshold])
else:
    error_print(f' Page size"{args.threshold}" does not exist in the dictionary.')
    exit(1)

# 左右の移動
if args.left and not args.right:
    x_translation = args.left
elif args.right and not args.left:
    x_translation = -args.right
else:
    x_translation = 0

# 上下の移動
if args.up and not args.down:
    y_translation = args.up
elif args.down and not args.up:
    y_translation = -args.down
else:
    y_translation = 0

translation_matrix = [1, 0, 0, 1, x_translation, y_translation]

print(f'左右の移動量: {x_translation} 上下の移動量: {y_translation}')

# フォルダのパスを設定
if not args.clear:
    text_layer_folder = './OCRtextPDF'
    if not os.path.exists(text_layer_folder):
        os.makedirs(text_layer_folder,exist_ok=True)
        print(f'{text_layer_folder}フォルダを生成しました create {text_layer_folder} folder')
    else:
        print(f'{text_layer_folder}フォルダは既に存在します {text_layer_folder} folder already exists')
    existing_pdf_folder = './OptimizedPDF'
    if not os.path.exists(existing_pdf_folder):
        os.makedirs(existing_pdf_folder,exist_ok=True)
        print(f'{existing_pdf_folder}フォルダを生成しました create {existing_pdf_folder} folder')
    else:
        print(f'{existing_pdf_folder}フォルダは既に存在します {existing_pdf_folder} folder already exists')
    output_folder = './DraftPDF'
    if not os.path.exists(output_folder):
        os.makedirs(output_folder,exist_ok=True)
        print(f'{output_folder}フォルダを生成しました create {output_folder} folder')
    else:
        print(f'{output_folder}フォルダは既に存在します {output_folder} folder already exists')
else:
    text_layer_folder = './OCRclearPDF'
    if not os.path.exists(text_layer_folder):
        os.makedirs(text_layer_folder,exist_ok=True)
        print(f'{text_layer_folder}フォルダを生成しました create {text_layer_folder} folder')
    else:
        print(f'{text_layer_folder}フォルダは既に存在します {text_layer_folder} folder already exists')
    existing_pdf_folder = './OriginalPDF'
    if not os.path.exists(existing_pdf_folder):
        os.makedirs(existing_pdf_folder,exist_ok=True)
        print(f'{existing_pdf_folder}フォルダを生成しました create {existing_pdf_folder} folder')
    else:
        print(f'{existing_pdf_folder}フォルダは既に存在します {existing_pdf_folder} folder already exists')
    output_folder = './OCRfinalPDF'
    if not os.path.exists(output_folder):
        os.makedirs(output_folder,exist_ok=True)
        print(f'{output_folder}フォルダを生成しました create {output_folder} folder')
    else:
        print(f'{output_folder}フォルダは既に存在します {output_folder} folder already exists')

# テキストレイヤーPDFのファイル名を取得
if not args.clear:
    text_pdf_files = [f for f in os.listdir(text_layer_folder) if f.endswith('_TextOnly.pdf')]
else:
    text_pdf_files = [f for f in os.listdir(text_layer_folder) if f.endswith('_ClearText.pdf')]

# 各テキストレイヤーPDFに対して処理を実行
for text_pdf_file in text_pdf_files:
    if not args.clear:
        base_name = text_pdf_file.replace('_TextOnly.pdf', '')
    else:
        base_name = text_pdf_file.replace('_ClearText.pdf', '')
    existing_pdf_file = base_name + '.pdf'
    if not args.clear:
        output_pdf_file = base_name + '_Draft.pdf'
    else:
        output_pdf_file = base_name + '_OCR.pdf'

    text_pdf_path = os.path.join(text_layer_folder, text_pdf_file)
    existing_pdf_path = os.path.join(existing_pdf_folder, existing_pdf_file)
    output_pdf_path = os.path.join(output_folder, output_pdf_file)

    if os.path.exists(text_pdf_path) and os.path.exists(existing_pdf_path):
        text_pdf = PdfReader(text_pdf_path)
        existing_pdf = PdfReader(existing_pdf_path)
        merger = PdfMerger()

        for i in range(0, len(existing_pdf.pages), process_num_pages):
            output_pdf = PdfWriter()
            for page_number in range(i, min(i + process_num_pages, len(existing_pdf.pages))):
                existing_page = existing_pdf.pages[page_number]
                text_page = text_pdf.pages[page_number]

                # ページサイズを確認し、必要に応じて調整
                if existing_page.mediabox != text_page.mediabox:
                    text_page.mediabox = existing_page.mediabox

                # ページサイズが異常に大きい場合、translation_matrixをdpi_conversion_factorで除算する
                page_width, page_height = existing_page.mediabox[2], existing_page.mediabox[3]
                if page_width > threshold_page_size[0] or page_height > threshold_page_size[1]:
                    adjusted_translation_matrix = translation_matrix.copy()
                    adjusted_translation_matrix[-2] /= dpi_conversion_factor
                    adjusted_translation_matrix[-1] /= dpi_conversion_factor
                else:
                    adjusted_translation_matrix = translation_matrix
                # テキストレイヤーの座標を調整する変換行列を定義
                text_page.add_transformation(adjusted_translation_matrix)

                existing_page.merge_page(text_page)
                output_pdf.add_page(existing_page)

            # 一時ファイルに書き出し
            temp_pdf_path = f'temp_{i}.pdf'
            with open(temp_pdf_path, 'wb') as f:
                output_pdf.write(f)

            # 一時ファイルをマージ
            merger.append(temp_pdf_path)

        # 最終的なPDFを書き出し
        with open(output_pdf_path, 'wb') as f:
            merger.write(f)

        print(f'{output_pdf_file} の合成が完了しました。')
    else:
        print(f'{text_pdf_file} または {existing_pdf_file} が見つかりません。')

print('全てのPDFファイルの合成が完了しました。')
