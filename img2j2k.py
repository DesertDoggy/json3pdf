import os
import argparse
from pathlib import Path
import logging
import glob
from datetime import datetime
from PIL import Image
from PIL import ImageChops
import shutil

# コマンドライン引数を解析する
parser = argparse.ArgumentParser(description='Convert images to JP2 format and create optimized images for OCR.')
parser.add_argument('-s', '--simple-check', nargs='?', const=1, type=int, default=1,
                    help='Perform a simple check after creating each PDF (default: on)')
parser.add_argument('--log-level', '-log', default='DEBUG', choices=['DEBUG', 'VERBOSE', 'INFO', 'WARNING'],
                    help='Set the logging level (default: DEBUG)')
parser.add_argument('-debug', action='store_const', const='DEBUG', dest='log_level',
                    help='Set the logging level to DEBUG')
parser.add_argument('--quick', '-q', action='store_true', help='Skip bit-perfect lossless conversion check.')
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
log_filename = log_folder / f'img2j2k_{now.strftime("%Y%m%d_%H%M%S")}.log'

logging.basicConfig(filename=log_filename, filemode='a', format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', encoding='utf-8')
logger = logging.getLogger('img2j2k')  # ロガーの作成

# ログレベルの設定
log_level = getattr(logging, args.log_level.upper())
logger.setLevel(log_level)

# ログファイルのパスを取得
log_files = sorted(glob.glob(str(log_folder / 'j2k2pdf_*.log')))

# ログファイルが5個以上ある場合、古いものから削除
while len(log_files) > 5:
    os.remove(log_files.pop(0))

# 入力フォルダと出力フォルダのパス
input_folder = './OriginalImages'
lossless_folder = './TEMP/lossless'  
optimized_folder = './TEMP/optimized'  

# 出力フォルダが存在しない場合は作成
if not os.path.exists(lossless_folder):
    os.makedirs(lossless_folder)
if not os.path.exists(optimized_folder):
    os.makedirs(optimized_folder)

# 変換をスキップする拡張子リスト
skip_conversion_extensions = (
    '.j2c', '.j2k', '.jpc', '.jp2', '.jpf', '.jpg', '.jpeg', 
    '.jpm', '.jpg2', '.jpx', '.mj2'
)

# Pillowがサポートする画像形式の拡張子リスト
supported_extensions = (
    '.bmp', '.gif', '.j2c', '.j2k', '.jpc', '.jp2', '.jpf', '.jpg', '.jpeg', 
    '.jpm', '.jpg2', '.jpx', '.mj2', '.png', '.psd', '.tif', '.tiff', '.webp'
)

# 入力フォルダ内の全サブディレクトリの総数をカウント
convert_subdir_total = sum(1 for subdir, _, _ in os.walk(input_folder) if subdir != input_folder)

# 現在処理しているサブディレクトリのカウント
convert_subdir_count = 0

# 入力フォルダ内の全サブディレクトリを走査
for subdir, _, files in os.walk(input_folder):
    # 入力フォルダ自体はカウントしない
    if subdir == input_folder:
        continue

    # サブディレクトリ構造を出力フォルダに反映
    subfolder_path_lossless = subdir.replace(input_folder, lossless_folder)
    subfolder_path_optimized = subdir.replace(input_folder, optimized_folder)
    if not os.path.exists(subfolder_path_lossless):
        os.makedirs(subfolder_path_lossless)
    if not os.path.exists(subfolder_path_optimized):
        os.makedirs(subfolder_path_optimized)
    
    # ファイル名順にソート
    files.sort()
    
    # サブディレクトリ内の画像ファイルの数をカウント
    total_images = sum(1 for file in files if file.lower().endswith(supported_extensions))

    # 変換カウンターの初期化
    lossless_count = 0
    optimized_count = 0

    # 現在処理しているサブディレクトリのカウントを更新
    convert_subdir_count += 1
    print(f'Processing subdirectory {convert_subdir_count} of {convert_subdir_total}')

    for file in files:
        # Pillowがサポートする画像形式のファイルのみを処理
        if file.lower().endswith(supported_extensions):
            # 元のファイルパス
            original_path = os.path.join(subdir, file)
            # 出力ファイルパス
            output_path_lossless = os.path.join(subfolder_path_lossless, os.path.splitext(file)[0] + '.jp2')
            output_path_optimized = os.path.join(subfolder_path_optimized, os.path.splitext(file)[0] + '.jp2')

            # 変換をスキップするファイルかどうかをチェック
            if file.lower().endswith(skip_conversion_extensions):
                # ファイルを出力フォルダにコピー
                shutil.copy2(original_path, output_path_lossless)
                print(f'PDF compatible file. Skipped conversion and copied {file} to {lossless_folder}.')
            else:
                # 画像を開いてJP2形式で保存
                with Image.open(original_path) as img:
                    img.save(output_path_lossless, 'JPEG2000', quality_mode='lossless')
                    lossless_count += 1
                    verbose_print(f'Lossless conversion for {file}.')
                    print(f'Lossless ({lossless_count}/{total_images}) of ({convert_subdir_count}/{convert_subdir_total})subdir')
                    # 最適化画像の生成
                    img.save(output_path_optimized, 'JPEG2000', quality_mode='lossy', quality_layers=[20])
                    optimized_count += 1
                    verbose_print(f'Optimized image created for {file}.')
                    print(f'Optimize ({optimized_count}/{total_images}) of ({convert_subdir_count}/{convert_subdir_total})subdir')

                # ビットパーフェクトなロスレス変換を確認する部分をスキップするオプションが指定されているかチェック
                if not args.quick:
                    with Image.open(original_path) as original_img, Image.open(output_path_lossless) as converted_img:
                        # 画像が同じサイズであることを確認
                        if original_img.size != converted_img.size:
                            print(f'The image sizes are different: {file}')
                        else:
                            # 画像間の差分を取得
                            diff = ImageChops.difference(original_img, converted_img)
                            # 差分があるかどうかを確認
                            if diff.getbbox() is None:
                                verbose_print(f'Bit-perfect lossless conversion confirmed for {file}.')
                            else:
                                verbose_print(f'The converted image differs from the original: {file}')
            # 次の画像の処理に移る前に行を空ける
            print()

# quickオプションが指定された場合のメッセージ
if args.quick:
    info_print('Conversion completed. The bit-perfect lossless conversion check was skipped due to the --quick option.')
