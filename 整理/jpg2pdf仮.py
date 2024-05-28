import os
import argparse
from reportlab.pdfgen import canvas
from reportlab.lib.utils import ImageReader
from PIL import Image

# コマンドライン引数を解析する
parser = argparse.ArgumentParser(description='JPG画像をPDFに結合します。')
parser.add_argument('--size', type=str, default='A5', choices=['A3', 'A4', 'A5', 'A6', 'B4', 'B5', 'B6', 'B7'], help='ページサイズを指定します。')
parser.add_argument('--dpi', type=int, default=600, help='画像のDPIを指定します。')
parser.add_argument('--resample', action='store_true', help='画像をリサンプリングしてサイズを変更するかどうかを指定します。')
args = parser.parse_args()

# ページサイズの辞書を定義する
point_sizes = {
    'A3': (841.9, 1190.6),
    'A4': (595.3, 841.9),
    'A5': (419.5, 595.3),
    'A6': (297.6, 419.5),
    'B4': (729.1, 1031.8),
    'B5': (516.9, 729.1),
    'B6': (364.6, 516.9),
    'B7': (257.9, 364.6)
}

# ピクセルサイズの辞書を定義する
pixel_sizes = {size: (int(points[0] * args.dpi / 72), int(points[1] * args.dpi / 72)) for size, points in point_sizes.items()}

def make_pdf(images, pdf_filename, page_size, resample):
    pixel_size = pixel_sizes[page_size]
    c = canvas.Canvas(pdf_filename, pagesize=pixel_size)
    for image in images:
        try:
            im = Image.open(image)
            im_width, im_height = im.size
            if resample:
                # リサンプリングとリサイズを行う
                ratio = min(pixel_size[0] / im_width, pixel_size[1] / im_height)
                im = im.resize((int(im_width * ratio), int(im_height * ratio)), Image.Resampling.LANCZOS)
                c.drawImage(ImageReader(im), 0, 0, width=int(im_width * ratio), height=int(im_height * ratio))
            else:
                c.drawImage(ImageReader(im), 0, 0, width=im_width, height=im_height)
            c.showPage()
            print(f"Added image {image} to PDF {'with resampling' if resample else 'without resampling'}.")
        except Exception as e:
            print(f"Error processing image {image}: {e}")
    c.save()

def collect_images(directory):
    images = []
    for root, dirs, files in os.walk(directory):
        for file in sorted(files):
            if file.lower().endswith(('.jpeg', '.jpg', '.jpe', '.jfif', '.jif', '.jfi', '.jp2', '.j2k', '.jpf', '.jpx', '.jpm', '.mj2')):
                images.append(os.path.join(root, file))
    return images

working_folder = './TEMP'
output_folder = './OriginalPDF'

if not os.path.exists(output_folder):
    os.makedirs(output_folder)

for subdir, dirs, files in os.walk(working_folder):
    if subdir != working_folder:  # ルートディレクトリをスキップする
        images = collect_images(subdir)
        if images:
            pdf_filename = os.path.join(output_folder, os.path.basename(subdir) + '.pdf')
            make_pdf(images, pdf_filename, args.size, args.resample)
