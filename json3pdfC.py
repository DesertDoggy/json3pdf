import os
import argparse
from pathlib import Path
import logging
import glob
import sys
from datetime import datetime
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.colors import Color
import json

# コマンドライン引数を解析する
parser = argparse.ArgumentParser(description='PDFファイルにテキストを書き込む')
parser.add_argument('--log-level', '-log', default='DEBUG', choices=['DEBUG', 'VERBOSE', 'INFO', 'WARNING'],
                    help='Set the logging level (default: DEBUG)')
parser.add_argument('-debug', action='store_const', const='DEBUG', dest='log_level',
                    help='Set the logging level to DEBUG')
parser.add_argument('-s', '--size', type=int, default=60, help='フォントのサイズを指定します（デフォルトは60）')
parser.add_argument('-f', '--font', default='NotoSansJP-Regular', help='使用するフォントの名前を指定します（デフォルトはNotoSansJP-Regular）')
parser.add_argument('-d', '--dpi', type=int, default=600, help='文書のDPIを指定します（デフォルトは600）')
args = parser.parse_args()

# カスタムログレベルVERBOSEを作成
VERBOSE = 15
logging.addLevelName(VERBOSE, "VERBOSE")

def verbose(self, message, *args, **kws):
    if self.isEnabledFor(VERBOSE):
        self._log(VERBOSE, message, args, **kws) 

logging.Logger.verbose = verbose

#verbose and info logging instead of print
def verbose_print(message):
    print(message)
    logger.verbose(message)

def info_print(message):
    print(message)
    logger.info(message)

def error_print(message):
    print(message)
    logger.error(message)

# ログ設定
log_folder = Path('./logs')
log_folder.mkdir(parents=True, exist_ok=True)

# 現在の日時を取得
now = datetime.now()

# ログファイル名に日時を含める
log_filename = log_folder / f'json3pdfC_{now.strftime("%Y%m%d_%H%M%S")}.log'

logging.basicConfig(filename=log_filename, filemode='a', format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', encoding='utf-8')
logger = logging.getLogger('json3pdfC')  # ロガーの作成

# ログレベルの設定
log_level = getattr(logging, args.log_level.upper())
logger.setLevel(log_level)

# ログファイルのパスを取得
log_files = sorted(glob.glob(str(log_folder / 'json3pdfC_*.log')))

# ログファイルが5個以上ある場合、古いものから削除
while len(log_files) > 5:
    os.remove(log_files.pop(0))

# フォント名とパス
font_name = args.font
font_path = './data/fonts/' + font_name + '.ttf'

# フォントを登録
pdfmetrics.registerFont(TTFont(font_name, font_path))

# 入力フォルダと出力フォルダのパスを設定
input_folder = './DIjson'
if not os.path.exists(input_folder):
    os.makedirs(input_folder,exist_ok=True)
    print(f'{input_folder}フォルダを生成しました create {input_folder} folder')
else:
    print(f'{input_folder}フォルダは既に存在します {input_folder} folder already exists')
output_folder = './OCRclearPDF'
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

        # 新しいPDFファイル名を設定（'.pdf' を削除してから '_ClearText.pdf' を追加）
        base_filename = os.path.splitext(json_file)[0]
        base_filename = base_filename.replace('.pdf', '')  # '.pdf' を削除
        new_pdf_filename = base_filename + '_ClearText.pdf'
        new_pdf_path = os.path.join(output_folder, new_pdf_filename)

        # ReportLabのキャンバスを作成
        c = canvas.Canvas(new_pdf_path, pagesize=letter)

        # 透明色を定義（赤、緑、青、アルファ）
        transparent_color = Color(0, 0, 0, alpha=0)

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
                # テキストの色を透明に設定
                c.setFillColor(transparent_color)
                c.drawString(x, y, text)

            # 次のページに移動
            c.showPage()

        # PDFファイルを保存
        c.save()

print('全てのPDFファイルの処理が完了しました。')
