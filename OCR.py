import powerlog  # カスタムログレベルVERBOSEとログの設定を追加するスクリプトをインポート
import logging
import argparse
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.colors import Color
import os
import sys
import json

# コマンドライン引数を解析する
parser = argparse.ArgumentParser(description='PDFファイルにテキストを書き込む')
parser.add_argument('-s', '--size', type=int, default=60, help='フォントのサイズを指定します（デフォルトは60）')
parser.add_argument('-f', '--font', default='NotoSansJP-Regular', help='使用するフォントの名前を指定します（デフォルトはNotoSansJP-Regular）')
parser.add_argument('-d', '--dpi', type=int, default=600, help='文書のDPIを指定します（デフォルトは600）')
args = parser.parse_args()

# DPI変換のための係数を設定
DPI_CONVERSION_FACTOR = args.dpi / 72

# フォント名とパス
font_name = args.font
font_path = './data/fonts/' + font_name + '.ttf'

# フォントを登録
pdfmetrics.registerFont(TTFont(font_name, font_path))

# 入力フォルダと出力フォルダのパスを設定
input_folder = './before'
if not os.path.exists(input_folder):
    os.makedirs(input_folder,exist_ok=True)
    print(f'{input_folder}フォルダを生成しました create {input_folder} folder')
else:
    print(f'{input_folder}フォルダは既に存在します {input_folder} folder already exists')
output_folder = './after'
if not os.path.exists(output_folder):
    os.makedirs(output_folder,exist_ok=True)
    print(f'{output_folder}フォルダを生成しました create {output_folder} folder')
else:
    print(f'{output_folder}フォルダは既に存在します {output_folder} folder already exists')

# 入力フォルダ内の全てのJSONファイルを取得
json_files = [f for f in os.listdir(input_folder) if f.endswith('.pdf.json')]

for json_file in json_files:
    # OCR結果のJSONファイル名を設定
    ocr_json_path = os.path.join(input_folder, json_file)

    # JSONファイルが存在する場合のみ処理を実行
    if os.path.exists(ocr_json_path):
        with open(ocr_json_path, 'r', encoding='utf-8') as f:
            ocr_data = json.load(f)

        # 新しいPDFファイル名を設定（'.pdf' を削除してから '_TextOnly.pdf' を追加）
        base_filename = os.path.splitext(json_file)[0]
        base_filename = base_filename.replace('.pdf', '')  # '.pdf' を削除
        new_pdf_filename = base_filename + '_TextOnly.pdf'
        new_pdf_path = os.path.join(output_folder, new_pdf_filename)

        # ReportLabのキャンバスを作成
        c = canvas.Canvas(new_pdf_path, pagesize=letter)

        # JSONファイルからページ情報を取得し、テキストを書き込む
        for page in ocr_data['analyzeResult']['pages']:
            page_width = page['width'] * DPI_CONVERSION_FACTOR  # DPI変換を適用
            page_height = page['height'] * DPI_CONVERSION_FACTOR
            c.setPageSize((page_width, page_height))

            # フォントを設定（引数から取得したサイズを使用）
            c.setFont(font_name, args.size * DPI_CONVERSION_FACTOR)  # DPI変換を適用

            for word_info in page['words']:
                text = word_info['content']
                # OCR結果のポリゴンから座標を取得し、PDFの座標系に変換（DPI変換を適用）
                x = word_info['polygon'][0] * DPI_CONVERSION_FACTOR
                y = page_height - (word_info['polygon'][1] * DPI_CONVERSION_FACTOR)
                c.drawString(x, y, text)

            # 次のページに移動
            c.showPage()

        # PDFファイルを保存
        c.save()

print('全てのPDFファイルの処理が完了しました。')
