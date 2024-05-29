import os
import argparse
from pathlib import Path
import img2pdf
from PIL import Image
from PyPDF2 import PdfReader
from datetime import datetime
import logging
import json
import re

# ログ設定
log_folder = Path('./logs')
log_folder.mkdir(parents=True, exist_ok=True)
logging.basicConfig(filename=log_folder / 'jpg2pdf.py.log', filemode='w', format='%(name)s - %(levelname)s - %(message)s')

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

# 対応する画像ファイルの拡張子
image_extensions = ['.jpeg', '.jpg', '.jpe', '.jif', '.jfif', '.jfi', '.jp2', '.j2k', '.jpf', '.jpx', '.jpm', '.mj2', '.png']

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

# 画像情報を取得する関数
def imagelog_image_info(img,total_p):
    try:
        # 画像情報ファイルのパス
        imagelog_file_path = './imagelog_folder/imagelog_file.imglog'

        filename = img.filename
        resolution = img.size
        encoding_format = img.format

        # filenameからページ番号を抽出
        match_p = re.search(r'_p(\d+)', filename)
        match_z = re.search(r'_z(\d+)', filename)

        if "_cover" in filename:
            filename_page = 1
        elif match_p:
            filename_page = int(match_p.group(1)) + 2
        elif match_z:
            filename_page = int(match_z.group(1)) + total_p + 3
            total_p += 1  # _zの接尾辞がついたファイルが処理されたので、total_pを更新
        else:
            filename_page = None

        # DPIを取得
        dpi = img.info.get('dpi', 'N/A')

        # Estimated DPIを計算
        if dpi != 'N/A':
            if dpi < 72 or dpi % 50 != 0:
                estimated_dpi = max(72, ((dpi + 24) // 50) * 50)
            else:
                estimated_dpi = dpi
        else:
            estimated_dpi = 600

        # ロスレスかどうかを判断
        try:
            is_lossless_result = is_lossless(img)
        except Exception as e:
            logging.error("Error in is_lossless_result: {}".format(e))
            is_lossless_result = 'N/A'

        # 画像情報ファイル名を生成
        now = datetime.now()
        imagelog_filename = f'{now.strftime("%Y%m%d%H%M%S")}.imglog'

        # スクリプトのあるディレクトリのパスを取得
        base_path = os.path.dirname(os.path.abspath(__file__))

        # filenameを相対パスに変換
        filename = os.path.relpath(filename, base_path)

        imagelog_filepath = imagelog_folder / imagelog_filename

        # 画像情報を辞書に格納
        image_info = {
            "Filename": filename,
            "Resolution": resolution,
            "DPI": dpi,
            "Estimated DPI": estimated_dpi,
            "Encoding Format": encoding_format,
            "Is Lossless": is_lossless_result,
            "Image format": img.format,
            "Image size": img.size,
            "Image mode": img.mode,
            "PDF page number": filename_page,
            "PDF file name": subdirectory_name+'.pdf',
            "PDF directory name": pdf_directory_name,
            "PDF file path": './'+pdf_directory_name+'/'+subdirectory_name+'.pdf',
        }

        # スクリプトのあるディレクトリのパスを取得
        base_path = os.path.dirname(os.path.abspath(__file__))

        # filenameを相対パスに変換
        filename = os.path.relpath(filename, base_path)

        # 画像情報ファイルに書き込む
        try:
            with open(imagelog_filepath, 'a', encoding='utf-8') as imagelog_file:
                json.dump(image_info, imagelog_file, ensure_ascii=False)
                imagelog_file.write('\n')  # Add a newline after each image info
        except Exception as e:
            logging.error("Error writing image info to imagelog file: {}".format(e))


    except Exception as e:
        logging.error("Error in imagelog_image_info: {}".format(e))


# lossless_folderとoptimized_folder内のサブディレクトリの総数を取得
total_subdirs = [subdir for subdir in lossless_folder.iterdir() if subdir.is_dir()]
total_subdirs_count = len(total_subdirs)
total_optimized_subdirs = [subdir for subdir in optimized_folder.iterdir() if subdir.is_dir()]
total_optimized_subdirs_count = len(total_optimized_subdirs)

# lossless_folderとoptimized_folder内の各サブディレクトリをループ処理
for index, subdir in enumerate(total_subdirs + total_optimized_subdirs, start=1):
    if subdir.is_dir():
        print("\nProcessing subdir {} of {}: {}".format(index, total_subdirs_count + total_optimized_subdirs_count, subdir.name))
        # サブディレクトリ内の対応する画像ファイルを取得
        images = []
        total_p = 0  # total_pを初期化
        for extension in image_extensions:
            images.extend(sorted(subdir.glob('*{}'.format(extension))))
            
        total_images_count = len(images)

        # サブディレクトリ内の_pxxxxの総数を取得
        try:
            total_p += len([img for img in subdir.glob('*_p*{}'.format(extension))])
        except Exception as e:
            logging.error("Error in counting _p files: {}".format(e))

        # PDFファイル名をサブディレクトリ名に設定
        if subdir in total_subdirs:
            pdf_filename = output_folder / "{}.pdf".format(subdir.name)
        else:
            pdf_filename = optpdf_folder / "{}.pdf".format(subdir.name)

        # 画像ファイルがある場合のみPDFに結合
        if images:
            image_files = []
            layout_fun = None  # ページサイズの計算用関数
            for image_index, image_path in enumerate(images, start=1):
                print("Converting image {} of {} in subdir {}".format(image_index, total_images_count, subdir.name))
                try:
                    with Image.open(image_path) as img:
                        # 画像ファイルのパス
                        img_path = Path(img.filename)
                        # サブディレクトリ名を取得
                        subdirectory_name = img_path.parent.name

                        # 画像ファイルがどのフォルダにあるかによってPDFディレクトリ名を設定

                        if img_path.parent.parent.name == lossless_folder.name:
                            pdf_directory_name = output_folder.name
                        elif img_path.parent.parent.name == optimized_folder.name:
                            pdf_directory_name = optpdf_folder.name
                        else:
                            pdf_directory_name = None

                        # 画像情報を取得し、ログに書き込む
                        imagelog_image_info(img,total_p)
                        # DPI情報を取得、またはデフォルト値を設定
                        dpi = img.info.get('dpi', (600, 600))
                        width_px, height_px = img.size
                        width_in = width_px / dpi[0]  # 幅をインチで計算
                        height_in = height_px / dpi[1]  # 高さをインチで計算
                        layout_fun = img2pdf.get_layout_fun((img2pdf.mm_to_pt(width_in * 25.4), img2pdf.mm_to_pt(height_in * 25.4)))
                        print("Page size for {}: {} x {} inches".format(image_path.name, width_in, height_in))

                except Exception as e:
                    print("Error reading image size for {}: {}".format(image_path.name, e))
                image_files.append(str(image_path))

            with open(pdf_filename, "wb") as f:
                f.write(img2pdf.convert([str(image_path) for image_path in image_files]))

            # 簡易チェックの実行
            if args.simple_check:
                with open(pdf_filename, 'rb') as f:
                    pdf = PdfReader(f)
                    if subdir in total_subdirs:
                        total_lossless_pdfs += 1
                    else:
                        total_optimized_pdfs += 1
                    if len(pdf.pages) == total_images_count:
                        print("Simple check passed for {}".format(pdf_filename))
                        if subdir in total_subdirs:
                            successful_lossless_pdfs += 1
                        else:
                            successful_optimized_pdfs += 1
                    else:
                        print("Simple check failed for {}".format(pdf_filename))
                        if subdir in total_subdirs:
                            failed_lossless_pdfs += 1
                        else:
                            failed_optimized_pdfs += 1
                        
                        # img2pdfのconvert関数にページサイズを渡す
                        with open(pdf_filename, 'wb') as f:
                            f.write(img2pdf.convert(image_files, layout_fun=layout_fun))

# 全てのPDFが作成された後の結果の表示
if args.simple_check == 1:
    print("\nSimple check results:")
    print("Number of successfully created lossless PDFs: {} / {}".format(successful_lossless_pdfs, total_lossless_pdfs))
    print("Number of failed lossless PDFs: {} / {}".format(failed_lossless_pdfs, total_lossless_pdfs))
    print("Number of successfully created optimized PDFs: {} / {}".format(successful_optimized_pdfs, total_optimized_pdfs))
    print("Number of failed optimized PDFs: {} / {}".format(failed_optimized_pdfs, total_optimized_pdfs))
    print("\nConversion completed.")
else:
    print("\nConversion completed. Simple check was skipped.")