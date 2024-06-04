import os
import argparse
from pathlib import Path
import logging
import glob
from datetime import datetime
import img2pdf
from PIL import Image
from PyPDF2 import PdfReader
import json
import re
from colorama import Fore, Style

# CLIオプションの設定
parser = argparse.ArgumentParser()
parser.add_argument('-s', '--simple-check', nargs='?', const=1, type=int, default=1,
                    help='Perform a simple check after creating each PDF (default: on)')
parser.add_argument('--log-level', '-log', default='DEBUG', choices=['DEBUG', 'VERBOSE', 'INFO', 'WARNING'],
                    help='Set the logging level (default: DEBUG)')
parser.add_argument('-debug', action='store_const', const='DEBUG', dest='log_level',
                    help='Set the logging level to DEBUG')
parser.add_argument('--sub', action='store_true',
                    help='Keep the subdirectory structure and generate a separate PDF for each image')
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
log_filename = log_folder / f'j2k2pdf_{now.strftime("%Y%m%d_%H%M%S")}.log'

logging.basicConfig(filename=log_filename, filemode='a', format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', encoding='utf-8')
logger = logging.getLogger('j2k2pdf')  # ロガーの作成

# ログレベルの設定
log_level = getattr(logging, args.log_level.upper())
logger.setLevel(log_level)

# ログファイルのパスを取得
log_files = sorted(glob.glob(str(log_folder / 'j2k2pdf_*.log')))

# ログファイルが5個以上ある場合、古いものから削除
while len(log_files) > 5:
    os.remove(log_files.pop(0))

# 簡易チェックの結果を保存するカウンター
logger.debug('Setting up counters for simple check results.')  # ログメッセージの追加
successful_lossless_pdfs = 0
failed_lossless_pdfs = 0
successful_optimized_pdfs = 0
failed_optimized_pdfs = 0
total_lossless_pdfs = 0
total_optimized_pdfs = 0

# 入力フォルダと出力フォルダのパスを設定
logger.debug('Setting up input and output folder paths.')  # ログメッセージの追加
lossless_folder = Path('./TEMP/lossless')
output_folder = Path('./OriginalPDF')
optimized_folder = Path('./TEMP/optimized')
optpdf_folder = Path('./OptimizedPDF')

# 画像情報フォルダのパス
logger.debug('Setting up image info folder path.')  # ログメッセージの追加
imagelog_folder = Path('./TEMP/imagelogs')

# 出力フォルダと画像情報フォルダが存在しない場合は作成
logger.debug('Creating output and image info folders if they do not exist.')  # ログメッセージの追加
output_folder.mkdir(parents=True, exist_ok=True)
optpdf_folder.mkdir(parents=True, exist_ok=True)
imagelog_folder.mkdir(parents=True, exist_ok=True)

# 対応する画像ファイルの拡張子
logger.debug('Setting up image file extensions.')  # ログメッセージの追加
image_extensions = ['.jpeg', '.jpg', '.jpe', '.jif', '.jfif', '.jfi', '.jp2', '.j2k', '.jpf', '.jpx', '.jpm', '.mj2', '.png']

page_sizes = {
    "A3": (842, 1191),
    "A4": (595, 842),
    "A5": (420, 595),
    "A6": (298, 420),
    "B4": (729, 1032),
    "B5": (516, 729),
    "B6": (363, 516),
    "B7": (258, 363),
    "Tabloid": (792, 1224),  # タブロイド判のサイズ（11 x 17インチをポイントに変換）
    "Blanket": (4320, 6480)  # ブランケット判のサイズ（60 x 90インチをポイントに変換）
}

# ロスレスかどうかを判断する関数
def is_lossless(img):
    logger.debug('Determining if the image is lossless.')  # ログメッセージの追加
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
        logger.warning('Unknown image format: %s', encoding_format)  # ログメッセージの追加
        return 'Unknown'

# 画像情報を取得する関数
def imagelog_image_info(img,total_p):
    logger.debug('Getting image information.')  # ログメッセージの追加
    try:
        # 画像情報ファイルのパス
        imagelog_file_path = './imagelog_folder/imagelog_file.imglog'
        logger.debug('Image log file path: %s', imagelog_file_path)  # ログメッセージの追加

        filename = img.filename
        logger.debug('Image filename: %s', filename)  # ログメッセージの追加

        resolution = img.size
        logger.debug('Image resolution: %s', resolution)  # ログメッセージの追加

        encoding_format = img.format
        logger.debug('Image encoding format: %s', encoding_format)  # ログメッセージの追加

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
            logger.debug('Updated total_p to: %s', total_p)  # ログメッセージの追加
        else:
            filename_page = None

        logger.debug('Filename page: %s', filename_page)  # ログメッセージの追加
        
        # DPIを取得
        dpi = img.info.get('dpi', 'N/A')

        # Estimated DPIを計算
        logger.debug('Calculating estimated DPI.')  # ログメッセージの追加
        if dpi != 'N/A':
            if dpi < 72 or dpi % 50 != 0:
                estimated_dpi = max(72, ((dpi + 24) // 50) * 50)
            else:
                estimated_dpi = dpi
        else:
            estimated_dpi = 600

        # ロスレスかどうかを判断
        logger.debug('Determining if the image is lossless.')  # ログメッセージの追加
        try:
            is_lossless_result = is_lossless(img)
        except Exception as e:
            logger.error("Error in is_lossless_result: {}".format(e))
            is_lossless_result = 'N/A'

        # 画像情報ファイル名を生成
        logger.debug('Generating image info filename.')  # ログメッセージの追加
        now = datetime.now()
        imagelog_filename = f'{now.strftime("%Y%m%d%H%M%S")}.imglog'

        # スクリプトのあるディレクトリのパスを取得
        logger.debug('Getting the path of the directory where the script is located.')  # ログメッセージの追加
        base_path = os.path.dirname(os.path.abspath(__file__))

        # filenameを相対パスに変換
        logger.debug('Converting filename to relative path.')  # ログメッセージの追加
        filename = os.path.relpath(filename, base_path)

        imagelog_filepath = imagelog_folder / imagelog_filename
        logger.debug('Image log file path: %s', imagelog_filepath)  # ログメッセージの追加

        # 画像情報を辞書に格納
        logger.debug('Storing image info in a dictionary.')  # ログメッセージの追加
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
        logger.debug('Getting the path of the directory where the script is located.')  # ログメッセージの追加
        base_path = os.path.dirname(os.path.abspath(__file__))

        # filenameを相対パスに変換
        logger.debug('Converting filename to relative path.')  # ログメッセージの追加
        filename = os.path.relpath(filename, base_path)

        # 画像情報ファイルに書き込む
        logger.debug('Writing image info to imagelog file.')  # ログメッセージの追加
        try:
            with open(imagelog_filepath, 'a', encoding='utf-8') as imagelog_file:
                json.dump(image_info, imagelog_file, ensure_ascii=False)
                imagelog_file.write('\n')  # Add a newline after each image info
        except Exception as e:
            logger.error("Error writing image info to imagelog file: {}".format(e))

        logger.debug('Returning estimated DPI: %s', estimated_dpi)  # ログメッセージの追加
        return estimated_dpi

    except Exception as e:
        logger.error("Error in imagelog_image_info: {}".format(e))

def layout_fun(img_width_px, img_height_px, ndpi):
    logger.debug('Entering function layout_fun with parameters img_width_px=%s, img_height_px=%s, ndpi=%s', img_width_px, img_height_px, ndpi)  # 関数の開始をログに記録

    # 背景ページのサイズをポイントからピクセルに変換
    page_width_pt, page_height_pt = closest_page_size_pt
    logger.debug('Converted page size from points to pixels: page_width_pt=%s, page_height_pt=%s', page_width_pt, page_height_pt)  # 変換結果をログに記録

    # 画像をそのままのサイズで表示
    img_width_pt, img_height_pt = img_width_px * 72 / ndpi, img_height_px * 72 / ndpi
    logger.debug('Displayed image at its original size: img_width_pt=%s, img_height_pt=%s', img_width_pt, img_height_pt)  # 表示結果をログに記録

    # 画像を中央に配置
    x = (page_width_pt - img_width_pt) / 2
    y = (page_height_pt - img_height_pt) / 2
    logger.debug('Centered image: x=%s, y=%s', x, y)  # 配置結果をログに記録

    logger.debug('Exiting function layout_fun.')  # 関数の終了をログに記録
    return (page_width_pt, page_height_pt, x, y, x + img_width_pt, y + img_height_pt)

# lossless_folderとoptimized_folder内のサブディレクトリの総数を取得
logger.debug('Getting subdirectories in lossless_folder.')  # ログメッセージの追加
total_subdirs = [subdir for subdir in lossless_folder.iterdir() if subdir.is_dir()]
logger.debug('Counting subdirectories in lossless_folder.')  # ログメッセージの追加
total_subdirs_count = len(total_subdirs)
logger.debug('Getting subdirectories in optimized_folder.')  # ログメッセージの追加
total_optimized_subdirs = [subdir for subdir in optimized_folder.iterdir() if subdir.is_dir()]
logger.debug('Counting subdirectories in optimized_folder.')  # ログメッセージの追加
total_optimized_subdirs_count = len(total_optimized_subdirs)

#サブディレクトリの画像を取得する関数を定義
def get_images(subdir, image_extensions):
    images = []
    for extension in image_extensions:
        images.extend(sorted(subdir.glob('*{}'.format(extension))))
    return images

def get_total_p(subdir, image_extensions,total_p=0):
    for extension in image_extensions:
        total_p += len([img for img in subdir.glob('*_p*{}'.format(extension))])
    return total_p

def get_pdf_filename(subdir, total_subdirs, output_folder, optpdf_folder):
    if subdir in total_subdirs:
        pdf_filename = output_folder / "{}.pdf".format(subdir.name)
    else:
        pdf_filename = optpdf_folder / "{}.pdf".format(subdir.name)
    return pdf_filename

def get_pdf_directory_name(img_path, lossless_folder, output_folder, optimized_folder, optpdf_folder):
    if img_path.parent.parent.name == lossless_folder.name:
        return output_folder.name
    elif img_path.parent.parent.name == optimized_folder.name:
        return optpdf_folder.name
    else:
        return None
    
def get_dpi_info(img, total_p):
    dpi = img.info.get('dpi', (600, 600))
    estimated_dpi = imagelog_image_info(img,total_p)
    width_px, height_px = img.size
    width_pt = width_px / estimated_dpi * 72  # 幅をポイントで計算
    height_pt = height_px / estimated_dpi * 72  # 高さをポイントで計算
    return dpi, estimated_dpi, width_pt, height_pt

# lossless_folderとoptimized_folder内の各サブディレクトリをループ処理
for index, subdir in enumerate(total_subdirs + total_optimized_subdirs, start=1):
    if subdir.is_dir():
        logger.debug('Processing subdir %s of %s: %s', index, total_subdirs_count + total_optimized_subdirs_count, subdir.name)  # ログメッセージの追加
        total_p = 0  # total_pを初期化

        # サブディレクトリ内の画像を取得
        images = get_images(subdir, image_extensions)

        # サブディレクトリ内の画像の総数を取得
        total_images_count = len(images)

        #_pの数を取得
        total_p = get_total_p(subdir, image_extensions)

        # PDFファイル名を取得
        pdf_filename = get_pdf_filename(subdir, total_subdirs, output_folder, optpdf_folder)

        # 画像ファイルがある場合のみPDFに結合
        if images:
            image_files = []

            layout_fun = None  # ページサイズの計算用関数

            for image_index, image_path in enumerate(images, start=1):
                logger.debug('Converting image %s of %s in subdir %s', image_index, total_images_count, subdir.name)  # ログメッセージの追加

                with Image.open(image_path) as img:

                    # 画像ファイルのパス
                    img_path = Path(img.filename)
                    # サブディレクトリ名を取得
                    subdirectory_name = img_path.parent.name
                    logger.debug('Got image path and subdirectory name: %s, %s', img_path, subdirectory_name)  # ログメッセージの追加
 
                    # 画像ファイルがどのフォルダにあるかによってPDFディレクトリ名を設定
                    if img_path.parent.parent.name == lossless_folder.name:
                        pdf_directory_name = output_folder.name
                    elif img_path.parent.parent.name == optimized_folder.name:
                        pdf_directory_name = optpdf_folder.name
                    else:
                        pdf_directory_name = None
                    logger.debug('Set PDF directory name: %s', pdf_directory_name)  # ログメッセージの追加

                    # DPI、推定DPI、幅、高さを取得
                    dpi, estimated_dpi, width_pt, height_pt = get_dpi_info(img, total_p)
                    logger.debug('Got DPI, estimated DPI, width and height in points: %s, %s, %s, %s', dpi, estimated_dpi, width_pt, height_pt)  # ログメッセージの追加

                    try:
                        # Convert points to inches for console output
                        width_in = width_pt / 72
                        height_in = height_pt / 72
                        logger.debug('Converted width and height to inches: %s, %s', width_in, height_in)  # ログメッセージの追加
                    except Exception as e:
                        logger.error("Error in converting points to inches: {}".format(e))
                        
                    try:
                        # Find the closest page size
                        closest_page_size_format, closest_page_size_pt = min(page_sizes.items(), key=lambda size: abs(width_pt - size[1][0]) + abs(height_pt - size[1][1]))
                        logger.debug('Found closest page size: %s, %s', closest_page_size_format, closest_page_size_pt)  # ログメッセージの追加
                        verbose_print("Estimated page size for {}: {} ({} x {} inches)".format(image_path.name, closest_page_size_format, width_in, height_in))
                    except Exception as e:
                        logger.error("Error in finding closest page size: {}".format(e))

                    try:
                        # Pass only the page dimensions (width and height) to img2pdf.get_layout_fun
                        layout_fun = img2pdf.get_layout_fun(closest_page_size_pt)
                        logger.debug('Got layout function: %s', layout_fun)  # ログメッセージの追加

                        if layout_fun is None:
                            error_print("Failed to get layout function.")
                            sys.exit(1)
                    except Exception as e:
                        logger.error("Error in getting layout function: {}".format(e))

                    try:
                        # Get the actual page size from the layout function
                        imgwidthpx = width_px  # 画像の幅（ピクセル）
                        imgheightpx = height_px  # 画像の高さ（ピクセル）
                        logger.debug('Got actual page size: %s, %s', imgwidthpx, imgheightpx)  # ログメッセージの追加
                    except Exception as e:
                        logger.error("Error in getting actual page size: {}".format(e))

                    try:
                        ndpi = (estimated_dpi)  # DPI
                        logger.debug('Set NDPI: %s', ndpi)  # ログメッセージの追加
                    except Exception as e:
                        logger.error("Error in setting NDPI: {}".format(e))

                    try:
                        pdf_page_size = layout_fun(imgwidthpx,imgheightpx, ndpi)
                        logger.debug('Got PDF page size: %s', pdf_page_size)  # ログメッセージの追加
                        verbose_print("PDF page size will be: {}".format(pdf_page_size))
                    except Exception as e:
                        logger.error("Error in getting PDF page size from layout_fun: {}".format(e))

                    try:
                        # Check if the actual page size matches the estimated page size
                        if pdf_page_size == closest_page_size_pt:
                            logger.debug('Page size matches estimated size.')  # ログメッセージの追加
                            verbose_print(Fore.GREEN + "Page size for {}: matches estimated size ({} x {} inches)".format(image_path.name, width_in, height_in) + Style.RESET_ALL)
                        else:
                            logger.debug('Page size does not match estimated size.')  # ログメッセージの追加
                            verbose_print(Fore.YELLOW + "Page size for {}: does not match estimated size ({} x {} inches)".format(image_path.name, width_in, height_in) + Style.RESET_ALL)
                    except Exception as e:
                        logger.error("Error in checking page size match: {}".format(e))

                logger.debug('Appended image path to image_files: %s', str(image_path))  # ログメッセージの追加
                image_files.append(str(image_path))

            try:
                # img2pdfのconvert関数にページサイズを渡す
                with open(pdf_filename, "wb") as f:
                    logger.debug('Converting images to PDF: %s', [str(image_path) for image_path in image_files])  # ログメッセージの追加
                    f.write(img2pdf.convert([str(image_path) for image_path in image_files], layout_fun=layout_fun, dpi=estimated_dpi))
            except Exception as e:
                logger.error("Error in converting images to PDF: {}".format(e))

            try:
                # 簡易チェックの実行
                if args.simple_check:
                    with open(pdf_filename, 'rb') as f:
                        pdf = PdfReader(f)
                        logger.debug('Read PDF file: %s', pdf_filename)  # ログメッセージの追加
                        if subdir in total_subdirs:
                            total_lossless_pdfs += 1
                        else:
                            total_optimized_pdfs += 1
                        if len(pdf.pages) == total_images_count:
                            logger.debug('Simple check passed for: %s', pdf_filename)  # ログメッセージの追加
                            info_print("Simple check passed for {}".format(pdf_filename))
                            if subdir in total_subdirs:
                                successful_lossless_pdfs += 1
                            else:
                                successful_optimized_pdfs += 1
                        else:
                            logger.debug('Simple check failed for: %s', pdf_filename)  # ログメッセージの追加
                            info_print("Simple check failed for {}".format(pdf_filename))
                            if subdir in total_subdirs:
                                failed_lossless_pdfs += 1
                            else:
                                failed_optimized_pdfs += 1
            except Exception as e:
                logger.error("Error in simple check: {}".format(e))

# 全てのPDFが作成された後の結果の表示
if args.simple_check == 1:
    logging.info('Simple check results:')  # ログメッセージの追加
    info_print("\nSimple check results:")
    logging.info('Number of successfully created lossless PDFs: %s / %s', successful_lossless_pdfs, total_lossless_pdfs)  # ログメッセージの追加
    info_print("Number of successfully created lossless PDFs: {} / {}".format(successful_lossless_pdfs, total_lossless_pdfs))
    logging.info('Number of failed lossless PDFs: %s / %s', failed_lossless_pdfs, total_lossless_pdfs)  # ログメッセージの追加
    info_print("Number of failed lossless PDFs: {} / {}".format(failed_lossless_pdfs, total_lossless_pdfs))
    logging.info('Number of successfully created optimized PDFs: %s / %s', successful_optimized_pdfs, total_optimized_pdfs)  # ログメッセージの追加
    info_print("Number of successfully created optimized PDFs: {} / {}".format(successful_optimized_pdfs, total_optimized_pdfs))
    logging.info('Number of failed optimized PDFs: %s / %s', failed_optimized_pdfs, total_optimized_pdfs)  # ログメッセージの追加
    info_print("Number of failed optimized PDFs: {} / {}".format(failed_optimized_pdfs, total_optimized_pdfs))
    logging.info('Conversion completed.')  # ログメッセージの追加
    info_print("\nConversion completed.")
else:
    logging.info('Conversion completed. Simple check was skipped.')  # ログメッセージの追加
    info_print("\nConversion completed. Simple check was skipped.")