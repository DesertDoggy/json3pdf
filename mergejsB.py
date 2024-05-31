import os
import argparse
from pathlib import Path
import logging
import glob
from datetime import datetime
from pypdf import PdfReader, PdfWriter

# コマンドライン引数を解析する
parser = argparse.ArgumentParser(description='PDFファイルにテキストレイヤーを追加します。')
parser.add_argument('--log-level', '-log', default='DEBUG', choices=['DEBUG', 'VERBOSE', 'INFO', 'WARNING'],
                    help='Set the logging level (default: DEBUG)')
parser.add_argument('-debug', action='store_const', const='DEBUG', dest='log_level',
                    help='Set the logging level to DEBUG')
parser.add_argument('--left', type=int, default=0, help='左に移動する単位数')
parser.add_argument('--right', type=int, default=0, help='右に移動する単位数')
parser.add_argument('--up', type=int, default=0, help='上に移動する単位数')
parser.add_argument('--down', type=int, default=48, help='下に移動する単位数')
parser.add_argument('--dpi', type=int, default=600, help='文書のDPIを指定します。デフォルトは600dpiです。')
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
log_filename = log_folder / f'mergejsB_{now.strftime("%Y%m%d_%H%M%S")}.log'

logging.basicConfig(filename=log_filename, filemode='a', format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', encoding='utf-8')
logger = logging.getLogger('mergejsB')  # ロガーの作成

# ログレベルの設定
log_level = getattr(logging, args.log_level.upper())
logger.setLevel(log_level)

# ログファイルのパスを取得
log_files = sorted(glob.glob(str(log_folder / 'mergejsB_*.log')))

# ログファイルが5個以上ある場合、古いものから削除
while len(log_files) > 5:
    os.remove(log_files.pop(0))

# DPIに基づいた変換行列を設定
units_per_inch = args.dpi
translation_matrix = [1, 0, 0, 1, (args.left - args.right) * units_per_inch, (args.up - args.down) * units_per_inch]

# フォルダのパスを設定
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

# テキストレイヤーPDFのファイル名を取得
text_pdf_files = [f for f in os.listdir(text_layer_folder) if f.endswith('_TextOnly.pdf')]

# 各テキストレイヤーPDFに対して処理を実行
for text_pdf_file in text_pdf_files:
    base_name = text_pdf_file.replace('_TextOnly.pdf', '')
    existing_pdf_file = base_name + '.pdf'
    output_pdf_file = base_name + '_merged.pdf'

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
