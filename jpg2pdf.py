import os
import argparse
from pathlib import Path
import img2pdf
from PIL import Image
from PyPDF2 import PdfReader

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

# 出力フォルダが存在しない場合は作成
output_folder.mkdir(parents=True, exist_ok=True)
optpdf_folder.mkdir(parents=True, exist_ok=True)

# 対応する画像ファイルの拡張子
image_extensions = ['.jpeg', '.jpg', '.jpe', '.jif', '.jfif', '.jfi', '.jp2', '.j2k', '.jpf', '.jpx', '.jpm', '.mj2', '.png']

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
        for extension in image_extensions:
            images.extend(sorted(subdir.glob('*{}'.format(extension))))
        
        total_images_count = len(images)
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
print("\nSimple check results:")
print("Number of successfully created lossless PDFs: {} / {}".format(successful_lossless_pdfs, total_lossless_pdfs))
print("Number of failed lossless PDFs: {} / {}".format(failed_lossless_pdfs, total_lossless_pdfs))
print("Number of successfully created optimized PDFs: {} / {}".format(successful_optimized_pdfs, total_optimized_pdfs))
print("Number of failed optimized PDFs: {} / {}".format(failed_optimized_pdfs, total_optimized_pdfs))