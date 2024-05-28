import os
from pathlib import Path
import img2pdf
from PIL import Image

# 入力フォルダと出力フォルダのパスを設定
lossless_folder = Path('./TEMP/lossless')
output_folder = Path('./OriginalPDF')

# 出力フォルダが存在しない場合は作成
output_folder.mkdir(parents=True, exist_ok=True)

# 対応する画像ファイルの拡張子
image_extensions = ['.jpeg', '.jpg', '.jpe', '.jif', '.jfif', '.jfi', '.jp2', '.j2k', '.jpf', '.jpx', '.jpm', '.mj2', '.png']

# lossless_folder内のサブディレクトリの総数を取得
total_subdirs = [subdir for subdir in lossless_folder.iterdir() if subdir.is_dir()]
total_subdirs_count = len(total_subdirs)

# lossless_folder内の各サブディレクトリをループ処理
for index, subdir in enumerate(total_subdirs, start=1):
    if subdir.is_dir():
        print(f"Processing subdir {index} of {total_subdirs_count}: {subdir.name}")
        # サブディレクトリ内の対応する画像ファイルを取得
        images = []
        for extension in image_extensions:
            images.extend(sorted(subdir.glob(f'*{extension}')))
        
        total_images_count = len(images)
        # PDFファイル名をサブディレクトリ名に設定
        pdf_filename = output_folder / f"{subdir.name}.pdf"
        
        # 画像ファイルがある場合のみPDFに結合
        if images:
            image_files = []
            layout_fun = None  # ページサイズの計算用関数
            for image_index, image_path in enumerate(images, start=1):
                print(f"Converting image {image_index} of {total_images_count} in subdir {subdir.name}")
                try:
                    with Image.open(image_path) as img:
                        # DPI情報を取得、またはデフォルト値を設定
                        dpi = img.info.get('dpi', (600, 600))
                        width_px, height_px = img.size
                        width_in = width_px / dpi[0]  # 幅をインチで計算
                        height_in = height_px / dpi[1]  # 高さをインチで計算
                        layout_fun = img2pdf.get_layout_fun((img2pdf.mm_to_pt(width_in * 25.4), img2pdf.mm_to_pt(height_in * 25.4)))
                        print(f"Page size for {image_path.name}: {width_in} x {height_in} inches")
                except Exception as e:
                    print(f"Error reading image size for {image_path.name}: {e}")
                image_files.append(str(image_path))
            
            # img2pdfのconvert関数にページサイズを渡す
            with open(pdf_filename, "wb") as f:
                f.write(img2pdf.convert(image_files, layout_fun=layout_fun))
            print(f"PDF created for {subdir.name}")
        else:
            print(f"No compatible image files found in {subdir.name}")

# 処理完了
print("PDF merging is complete.")
