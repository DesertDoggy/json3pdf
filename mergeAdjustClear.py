import argparse
from pypdf import PdfReader, PdfWriter
import os
import logging
import verbose_logging  # カスタムログレベルVERBOSEとログの設定を追加するスクリプトをインポート

# コマンドライン引数を解析する
parser = argparse.ArgumentParser(description='PDFファイルにテキストレイヤーを追加します。')
parser.add_argument('--left', type=int, default=0, help='左に移動する単位数')
parser.add_argument('--right', type=int, default=0, help='右に移動する単位数')
parser.add_argument('--up', type=int, default=0, help='上に移動する単位数')
parser.add_argument('--down', type=int, default=48, help='下に移動する単位数')
parser.add_argument('--dpi', type=int, default=600, help='文書のDPIを指定します。デフォルトは600dpiです。')
args = parser.parse_args()

# DPIに基づいた変換行列を設定
units_per_inch = args.dpi
translation_matrix = [1, 0, 0, 1, (args.left - args.right) * units_per_inch, (args.up - args.down) * units_per_inch]

# フォルダのパスを設定
text_layer_folder = './after'
if not os.path.exists(text_layer_folder):
    os.makedirs(text_layer_folder,exist_ok=True)
    print(f'{text_layer_folder}フォルダを生成しました create {text_layer_folder} folder')
else:
    print(f'{text_layer_folder}フォルダは既に存在します {text_layer_folder} folder already exists')
existing_pdf_folder = './before'
if not os.path.exists(existing_pdf_folder):
    os.makedirs(existing_pdf_folder,exist_ok=True)
    print(f'{existing_pdf_folder}フォルダを生成しました create {existing_pdf_folder} folder')
else:
    print(f'{existing_pdf_folder}フォルダは既に存在します {existing_pdf_folder} folder already exists')
output_folder = './OCRdone'
if not os.path.exists(output_folder):
    os.makedirs(output_folder,exist_ok=True)
    print(f'{output_folder}フォルダを生成しました create {output_folder} folder')
else:
    print(f'{output_folder}フォルダは既に存在します {output_folder} folder already exists')

# 透明テキストレイヤーPDFのファイル名を取得
text_pdf_files = [f for f in os.listdir(text_layer_folder) if f.endswith('_ClearText.pdf')]

# 各透明テキストレイヤーPDFに対して処理を実行
for text_pdf_file in text_pdf_files:
    base_name = text_pdf_file.replace('_ClearText.pdf', '')
    existing_pdf_file = base_name + '.pdf'
    output_pdf_file = base_name + '_OCR.pdf'

    text_pdf_path = os.path.join(text_layer_folder, text_pdf_file)
    existing_pdf_path = os.path.join(existing_pdf_folder, existing_pdf_file)
    output_pdf_path = os.path.join(output_folder, output_pdf_file)

    if os.path.exists(text_pdf_path) and os.path.exists(existing_pdf_path):
        text_pdf = PdfReader(text_pdf_path)
        existing_pdf = PdfReader(existing_pdf_path)
        output_pdf = PdfWriter()

        for page_number in range(len(existing_pdf.pages)):
            existing_page = existing_pdf.pages[page_number]
            text_page = text_pdf.pages[page_number]

            # ページサイズを確認し、必要に応じて調整
            if existing_page.mediabox != text_page.mediabox:
                text_page.mediabox = existing_page.mediabox

            # テキストレイヤーの座標を調整する変換行列を定義
            text_page.add_transformation(translation_matrix)

            existing_page.merge_page(text_page)
            output_pdf.add_page(existing_page)

        with open(output_pdf_path, 'wb') as f:
            output_pdf.write(f)

        print(f'{output_pdf_file} の合成が完了しました。')
    else:
        print(f'{text_pdf_file} または {existing_pdf_file} が見つかりません。')

print('全てのPDFファイルの合成が完了しました。')
