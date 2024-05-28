import os
import argparse
from pathlib import Path
from datetime import datetime
import logging

# ログ設定
log_folder = Path('./logs')
log_folder.mkdir(parents=True, exist_ok=True)
logging.basicConfig(filename=log_folder / 'pdf.chk.py.log', filemode='w', format='%(name)s - %(levelname)s - %(message)s')

# CLIオプションの設定
parser = argparse.ArgumentParser()
parser.add_argument('-s', '--simple-check', nargs='?', const=1, type=int, default=1,
                    help='Perform a simple check after creating each PDF (default: on)')
args = parser.parse_args()

# 簡易チェックの結果を保存するカウンター
successful_lossless_pdfs = 0
failed_lossless_pdfs = 0
successful_optimized_pdfs = 0
failed_optimized_pdfs = 0
total_lossless_pdfs = 0
total_optimized_pdfs = 0

# 入力フォルダと出力フォルダのパスを設定
lossless_folder = Path('./TEMP/lossless')
output_folder = Path('./OriginalPDF')
optimized_folder = Path('./TEMP/optimized')
optpdf_folder = Path('./OptimizedPDF')

# 画像情報フォルダのパス
imagelog_folder = Path('./TEMP/imagelogs')

# 出力フォルダと画像情報フォルダが存在しない場合は作成
output_folder.mkdir(parents=True, exist_ok=True)
optpdf_folder.mkdir(parents=True, exist_ok=True)
imagelog_folder.mkdir(parents=True, exist_ok=True)