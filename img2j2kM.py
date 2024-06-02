import os
import sys
import queue
import threading
import psutil
import argparse
from pathlib import Path
import logging
from colorama import Fore, Style
import traceback
import glob
from datetime import datetime
from PIL import Image
import shutil
import numpy as np
import ctypes
import glymur
import uuid

# コマンドライン引数を解析する
parser = argparse.ArgumentParser(description='Convert images to JP2 format and create optimized images for OCR.')
parser.add_argument('-s', '--simple-check', nargs='?', const=1, type=int, default=1,
                    help='Perform a simple check after creating each PDF (default: on)')
parser.add_argument('--log-level', '-log', default='DEBUG', choices=['DEBUG', 'VERBOSE', 'INFO', 'WARNING'],
                    help='Set the logging level (default: DEBUG)')
parser.add_argument('-debug', action='store_const', const='DEBUG', dest='log_level',
                    help='Set the logging level to DEBUG')
parser.add_argument('--dpi', type=int, help='DPI for the output image. Default estimates dpi and rounds read DPI to typical integer DPI values or 600 if read DPI N/A. Positive integer will use set value if read DPI is N/A. Negative integer will force set value. --dpi 0 will use read DPI without rounding.')
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
    print(Fore.RED + message + Style.RESET_ALL)
    logger.error(message)

# コンソールのカラーフォーマット
def variable_str(obj):
    return Fore.CYAN + Style.BRIGHT + str(obj) + Style.RESET_ALL

# ログ設定
log_folder = Path('./logs')
log_folder.mkdir(parents=True, exist_ok=True)

# 現在の日時を取得
now = datetime.now()

# ログファイル名に日時を含める
log_filename = log_folder / f'img2j2kM_{now.strftime("%Y%m%d_%H%M%S")}.log'

logging.basicConfig(filename=log_filename, filemode='a', format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', encoding='utf-8')
logger = logging.getLogger('img2j2kM')  # ロガーの作成

# ログレベルの設定
log_level = getattr(logging, args.log_level.upper())
logger.setLevel(log_level)

# デバッグメッセージを出力すメッセージ
def debug_print(message):
    if log_level == logging.DEBUG:
        print(message)
        logger.debug(message)

# ログファイルのパスを取得
log_files = sorted(glob.glob(str(log_folder / 'img2j2kM_*.log')))

# ログファイルが5個以上ある場合、古いものから削除
while len(log_files) > 5:
    os.remove(log_files.pop(0))

# 入力フォルダと出力フォルダのパス
input_folder = './OriginalImages/DQ5'
lossless_folder = './TEMP/lossless/DQ5'  
optimized_folder = './TEMP/optimized/DQ5'
tmp_path = './TEMP/tmp'  

# 出力フォルダが存在しない場合は作成
if not os.path.exists(lossless_folder):
    os.makedirs(lossless_folder)
if not os.path.exists(optimized_folder):
    os.makedirs(optimized_folder)
if not os.path.exists(tmp_path):
    os.makedirs(tmp_path)

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

#本処理開始前の確認事項

#DLLの存在を確認する関数
def check_dll(dll_path):
    try:
        ctypes.cdll.LoadLibrary(dll_path)
        print(dll_name+" was successfully loaded from system PATH.")
    except OSError:
        error_print("Failed to load "+dll_name+" from system PATH.")

# DLLの名前を指定
dll_name = 'openjp2.dll'

# システムのPATHからDLLを探す
for path in os.environ['PATH'].split(os.pathsep):
    full_dll_path = os.path.join(path, dll_name)
    if os.path.exists(full_dll_path):
        check_dll(full_dll_path)
# glymurの確認
try:
    import glymur
    print("Glymur is installed correctly.")
except ImportError:
    print("Glymur is not installed.")
if glymur.lib.openjp2.OPENJP2:
    print("OpenJPEG is available. JP2K conversion is supported.")
else:
    print("OpenJPEG is not available. JP2K conversion is not supported.")

# glymurの設定ファイルの場所を確認する
glymur_config_path = os.path.join(os.path.expanduser('~'), 'glymur', 'glymurrc')
if os.path.isfile(glymur_config_path):
    # 設定ファイルが存在する場合、その場所を表示
    info_print("glymur setting file in " + glymur_config_path)
else:
    # 設定ファイルが存在しない場合、エラーメッセージを表示
    error_print("glymur setting file not found in "+glymur_config_path)

# 画像出力できるか確認
test_image_path = './data/test/test.png'
jp2k_test_path = './data/test/test.jpf'
# PILライブラリを使用して画像を読み込む
image = Image.open(test_image_path)
# 画像データをnumpy配列に変換
image_data = np.array(image)
# glymurライブラリを使用してJPEG 2000形式で保存
jp2 = glymur.Jp2k(jp2k_test_path, data=image_data)

# グローバル変数とロックを初期化
lossless_count = 0
optimized_count = 0
img_per_subdir_count = 0
subdir_count = 0
lossless_OK = 0
lossless_NO = 0
lossless_CHK = 0
count_lock = threading.Lock()

# ファイルキューの作成
file_queue = queue.Queue()

# Glymurのスレッド数を2に設定 (JPEG2000は2 core以上はあまり効果がない)
glymur.set_option('lib.num_threads', 2)

# 物理コア数を取得
num_physical_cores = psutil.cpu_count(logical=False)

# Pythonのスレッド数（またはプロセス数）を物理コア数の半分に設定
num_threads = num_physical_cores // 2

# 入力フォルダ内のすべてのファイルを取得
for file in os.listdir(input_folder):
    if file.lower().endswith(supported_extensions):
        file_queue.put(os.path.join(input_folder, file))
        img_per_subdir_count += 1
verbose_print(f"Total images in {input_folder}: {img_per_subdir_count}")

# 画像をロスレスのj2kファイルに変換する関数を定義
def convert_image():
    global lossless_count, lossless_OK, lossless_NO, lossless_CHK
    while not file_queue.empty():
        file_path = file_queue.get()
        try:
            with Image.open(file_path) as img:
                # 元画像の解像度を取得
                original_img_dpi = img.info.get('dpi', None)
                if original_img_dpi is None:
                    estimated_img_dpi = 600
                else:
                    # 72と150以上の50の倍数のうち、original_img_dpiに一番近いものを選択
                    estimated_img_dpi = min([72] + list(range(150, 1000, 50)), key=lambda x:abs(x-original_img_dpi[0]))

                # dpiの設定
                if args.dpi is None:
                    write_img_dpi = estimated_img_dpi
                elif args.dpi == 0:
                    write_img_dpi = original_img_dpi
                elif args.dpi < 0:
                    write_img_dpi = abs(args.dpi)
                else:
                    if original_img_dpi is None and args.dpi > 0:
                        write_img_dpi = abs(args.dpi)
                    else:
                        write_img_dpi = estimated_img_dpi
                verbose_print(Fore.YELLOW + f"DPI" + Fore.WHITE + " of "+file_path+"Original: "+variable_str(original_img_dpi)+", Estimated: "+variable_str(estimated_img_dpi)+", Write: "+variable_str(write_img_dpi))
                
                # Pillow Imageをnumpy arrayに変換
                img_array = np.array(img)

                # 一時的なファイル名を作成（日本語をglymurに渡さないため）
                tmp_filename = os.path.join(tmp_path, str(uuid.uuid4()) + '_temp.jpf')

                # 画像の変換と出力
                glymur.Jp2k(tmp_filename, data=img_array, cratios=[1])

                # 一時的なファイルを最終的な出力パスにリネーム
                output_path = os.path.join(lossless_folder, os.path.splitext(os.path.basename(file_path))[0] + '.jpf')
                shutil.move(tmp_filename, output_path)
                with count_lock:
                    lossless_count += 1
                    verbose_print(f"Lossless conversion for "+file_path+" complete!")
                    print(Fore.BLUE + "Lossless conversion" + Fore.CYAN+ str(lossless_count) + Fore.WHITE +"/" + Fore.CYAN + str(img_per_subdir_count)+Style.RESET_ALL)

                # 変換後の画像を読み込み
                converted_img_array = glymur.Jp2k(output_path)[:]
                
                # 元画像と変換後の画像がビットパーフェクトに一致するかどうかを確認
                is_bitperfect = np.array_equal(img_array, converted_img_array)
                with count_lock:
                    lossless_CHK += 1
                    if is_bitperfect:
                        lossless_OK += 1
                        verbose_print(f"Bitperfect conversion for {file_path} verified!")
                        print(Fore.YELLOW + "Bitperfect " + Fore.GREEN + " OK " + variable_str(lossless_OK) + Fore.WHITE +"/" +  Fore.RED + "NO " + Fore.CYAN + variable_str(lossless_NO) + Fore.WHITE + "/" + Fore.MAGENTA + "Total " + Fore.CYAN + variable_str(lossless_CHK) + Style.RESET_ALL)
                    else:
                        lossless_NO += 1
                        error_print(f"Bitperfect comparison for {file_path}: False")
                        print(Fore.YELLOW + "Bitperfect " + Fore.GREEN + " OK " + variable_str(lossless_OK) + Fore.WHITE +"/" +  Fore.RED + "NO " + Fore.CYAN + variable_str(lossless_NO) + Fore.WHITE + "/" + Fore.MAGENTA + "Total " + Fore.CYAN + variable_str(lossless_CHK) + Style.RESET_ALL)

        except Exception as e:
            logger.error(f"Error converting file {file_path}: {e}")
            logger.error(traceback.format_exc())
        finally:
            file_queue.task_done()

# スレッドの作成と開始
for _ in range(num_threads):  # num_threadsの数だけスレッドを作成
    t = threading.Thread(target=convert_image)
    t.daemon = True
    t.start()

# すべてのタスクが終了するのを待つ
file_queue.join()