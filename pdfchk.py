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
parser.add_argument('-s', '--advanced-check', nargs='?', const=1, type=int, default=1,
                    help='Perform a simple check after creating each PDF (default: on)')
args = parser.parse_args()

# 詳細チェックの結果を保存するカウンター

# PDFフォルダのパスを設定
output_folder = Path('./OriginalPDF')
optpdf_folder = Path('./OptimizedPDF')

# 画像情報フォルダのパス
imagelog_folder = Path('./TEMP/imagelogs')
