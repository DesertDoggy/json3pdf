import os
import json
import argparse
from pathlib import Path
from datetime import datetime
import logging
import verbose_logging  # カスタムログレベルVERBOSEとログの設定を追加するスクリプトをインポート
import fitz # PyMuPDF
import io
from PIL import Image
from colorama import Fore, Style, Back

# ログ設定
log_folder = Path('./logs')
log_folder.mkdir(parents=True, exist_ok=True)
logging.basicConfig(filename=log_folder / 'pdf.chk.py.log', filemode='w', format='%(name)s - %(levelname)s - %(message)s')

# CLIオプションの設定
parser = argparse.ArgumentParser()
parser.add_argument('-s', '--advanced-check', nargs='?', const=1, type=int, default=1,
                    help='Perform a simple check after creating each PDF (default: on)')
args = parser.parse_args()

# ロスレスかどうかを判断する関数
def is_lossless(img):
    encoding_format = img.format
    if encoding_format in ['JPEG', 'JPG', 'JPE', 'JIF', 'JFIF', 'JFI']:
        return False
    elif encoding_format in ['JPEG2000','JP2', 'J2K', 'JPF', 'JPX', 'JPM', 'MJ2']:
        irreversible = img.info.get('irreversible')
        if not irreversible:
            return True
        else:
            return False
    elif encoding_format == 'PNG':
        return True
    else:
        return 'Unknown'

# PDFフォルダのパスを設定
output_folder = Path('./OriginalPDF')
optpdf_folder = Path('./OptimizedPDF')

# 画像情報フォルダのパス
# imagelog_folder内の最新の.imglogファイルを見つける
imagelog_folder = Path('./TEMP/imagelogs')
latest_imglog_file = max(imagelog_folder.glob('*.imglog'), key=os.path.getmtime)

# .imglogファイルを開き、各行をJSONとして解析する
with open(latest_imglog_file, 'r', encoding='utf-8') as f:
    for line in f:
        image_info = json.loads(line)

        # 指定されたPDFファイルから対応するページを抽出する
        pdf_file_path = image_info['PDF file path']
        pdf_page_number = image_info['PDF page number'] - 1  # 0-indexed

        # PDFファイルを開く
        pdf_file = fitz.open(pdf_file_path)

        # 対応するページを取得する
        page = pdf_file.load_page(pdf_page_number)

        # ページから画像を抽出する
        pix = page.get_pixmap()

        # 画像データを取得する
        image_data = pix.samples

        # PIL Imageに変換する
        extracted_image = Image.frombytes("RGB", [pix.width, pix.height], image_data)

        # 画像情報を取得する
        extracted_image_info = {
            'Resolution': (pix.width, pix.height),
            'DPI': extracted_image.info.get('dpi', 'N/A'),
            'Estimated DPI': 'N/A',  # PDFから抽出した画像にはEstimated DPIは存在しない
            'Image format': extracted_image.format,
            'Image mode': extracted_image.mode,
            'Is Lossless': is_lossless(extracted_image),
            'Displayed DPI': (extracted_image.size[0] / page.mediabox.width * 72, 
                              extracted_image.size[1] / page.mediabox.height * 72)  # PDF内で表示される解像度
                                }

        # 画像の相対パスを表示
        image_path = image_info['Filename']
        print(f'{Fore.YELLOW}Image Path: {image_path}{Style.RESET_ALL}\n')

        # 元の画像情報と抽出した画像情報を比較する
        for key in ['Resolution', 'DPI', 'Estimated DPI', 'Image format', 'Image mode', 'Is Lossless']:
            if key == 'Resolution':
                # 解像度の比較では誤差を許容しない
                if abs(image_info[key][0] - extracted_image_info[key][0]) / image_info[key][0] <= 0.05 and \
                  abs(image_info[key][1] - extracted_image_info[key][1]) / image_info[key][1] <= 0.05:
                    print(f'{key} (Extracted Image): {Fore.GREEN}OK{Style.RESET_ALL}')
                else:
                    print(f'{key} (Extracted Image): {Fore.RED}NG{Style.RESET_ALL}, expected {image_info[key]}, but got {extracted_image_info[key]}')

                # PDF内で表示される解像度とも比較、誤差5%を許容する
                displayed_dpi = (extracted_image.size[0] / page.mediabox.width * 72, 
                                extracted_image.size[1] / page.mediabox.height * 72)
                if abs(image_info[key][0] - displayed_dpi[0]) / image_info[key][0] <= 0.05 and \
                  abs(image_info[key][1] - displayed_dpi[1]) / image_info[key][1] <= 0.05:
                    print(f'{key} (Displayed in PDF): {Fore.GREEN}OK{Style.RESET_ALL}')
                else:
                    print(f'{key} (Displayed in PDF): {Fore.RED}NG{Style.RESET_ALL}, expected {image_info[key]}, but got {displayed_dpi}')
            else:
                if image_info[key] == extracted_image_info[key]:
                    print(f'{key}: {Fore.GREEN}OK{Style.RESET_ALL}')
                else:
                    print(f'{key}: {Fore.RED}NG{Style.RESET_ALL}, expected {image_info[key]}, but got {extracted_image_info[key]}')

        # 画像ごとの検証結果の間に空行を追加
        print()