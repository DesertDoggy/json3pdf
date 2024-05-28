import os
import img2pdf
from pathlib import Path
import argparse

# Set up CLI arguments for DPI
parser = argparse.ArgumentParser(description='Convert images to PDF with specified DPI.')
parser.add_argument('--dpi', type=int, default=72, help='DPI for PDF conversion (default: 72)')
args = parser.parse_args()

# Set input and output folders
working_folder = Path('./TEMP')
output_folder = Path('./OriginalPDF')

# Create output folder if it doesn't exist
os.makedirs(output_folder, exist_ok=True)

# All extensions for JPEG 2000
jpeg2000_extensions = ('.jp2', '.j2k', '.jpf', '.jpm', '.jpg2', '.j2c', '.jpc', '.jpx', '.mj2')

# Traverse all subdirectories in working_folder
for subdir in working_folder.glob('**/*'):
    # Process only subdirectories
    if subdir.is_dir():
        # Sort files by name
        files = sorted(subdir.glob('*'), key=lambda x: x.name)
        # Generate PDF file path
        pdf_filename = output_folder / f"{subdir.name}.pdf"
        # Add image file paths to list
        img_paths = [file for file in files if file.suffix.lower() in ('.png', '.jpg', '.jpeg', '.bmp') + jpeg2000_extensions]
        # Convert to PDF if there are image files
        if img_paths:
            try:
                with open(pdf_filename, "wb") as f:
                    f.write(img2pdf.convert([str(path) for path in img_paths], dpi=args.dpi))
                print(f"PDF created for {subdir.name}. / {subdir.name} のPDFが生成されました。")
            except Exception as e:
                print(f"Failed to convert to PDF: {e} / PDFへの変換に失敗しました：{e}")
        else:
            print(f"No image files found in {subdir.name} / {subdir.name} に画像ファイルが見つかりませんでした。")

print("All PDFs have been created. The operation is complete. / すべてのPDFが生成されました。操作が完了しました。")
