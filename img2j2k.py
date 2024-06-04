import os
import sys
import tempfile
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
import io
from lxml import etree as ET

# コマンドライン引数を解析する
parser = argparse.ArgumentParser(description='Convert images to JP2 format and create optimized images for OCR.')
parser.add_argument('--log-level', '-log', default='INFO', choices=['DEBUG', 'VERBOSE', 'INFO', 'WARNING'],
                    help='Set the logging level (default: DEBUG)')
parser.add_argument('-debug', action='store_const', const='DEBUG', dest='log_level',
                    help='Set the logging level to DEBUG')
parser.add_argument('--dpi', type=int, help='DPI for the output image. Default estimates dpi and rounds read DPI to typical integer DPI values or 600 if read DPI N/A. Positive integer will use set value if read DPI is N/A. Negative integer will force set value. --dpi 0 will use read DPI without rounding.')
group_check = parser.add_mutually_exclusive_group()
group_check.add_argument('--quick', '-q', action='store_true', help='Skip bit-perfect lossless conversion check.')
group_check.add_argument("--check", choices=["fast", "slow"], default="slow", help="Check for bit-perfect lossless conversion. Default = slow 'fast' uses glymur before renaming tmp file, 'slow' uses pillow/numpy after final output. This is to avoid Japanese input to glymur")
parser.add_argument("--temp", "-t", default='./TEMP/tmp', help="Specify the temporary directory path. Default:'./TEMP/tmp'Use 'system' for system's temp directory. Using same drive as output folder is recommended.")
group_encode_method = parser.add_mutually_exclusive_group()
group_encode_method.add_argument("--lossless", "-l", action="store_true", help="Perform only lossless conversion.")
group_encode_method.add_argument("--optimize", "-o", action="store_true", help="Perform only optimized conversion.")
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
if args.log_level.upper() == 'VERBOSE':
    log_level = VERBOSE
else:
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
input_folder = './OriginalImages'
lossless_folder = './TEMP/lossless'  
optimized_folder = './TEMP/optimized'
if args.temp.lower() == 'system':
    tmp_path = tempfile.gettempdir()
else:
    tmp_path = os.path.abspath(args.temp)

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
#test_image_path = './data/test/test.png'
#jp2k_test_path = './data/test/test.jp2'
# PILライブラリを使用して画像を読み込む
#image = Image.open(test_image_path)
# 画像データをnumpy配列に変換
#image_data = np.array(image)
# glymurライブラリを使用してJPEG 2000形式で保存
#jp2 = glymur.Jp2k(jp2k_test_path, data=image_data)

# グローバル変数とロックを初期化
lossless_count = 0
optimized_count = 0
img_per_subdir_count = 0
subdir_count = 0
subdir_total = 0
lossless_OK = 0
lossless_NO = 0
lossless_CHK = 0
count_lock = threading.Lock()
lossless_total = 0
optimized_total = 0
img_total = 0


# Glymurのスレッド数を2に設定 (JPEG2000は2 core以上はあまり効果がない)
glymur.set_option('lib.num_threads', 2)

# 物理コア数を取得
num_physical_cores = psutil.cpu_count(logical=False)

# Pythonのスレッド数（またはプロセス数）を物理コア数の半分に設定
num_threads = num_physical_cores // 2


#ディレクトリ内のサブディレクトリを扱う関数を定義
def convert_all_images(input_folder, lossless_folder, optimized_folder):
    global lossless_count, optimized_count, lossless_OK, lossless_NO, lossless_CHK, img_per_subdir_count, subdir_count, lossless_total, optimized_total, img_total
    for subdir in os.listdir(input_folder):
        with count_lock:
            subdir_count += 1
        input_subdir = os.path.join(input_folder, subdir)
        lossless_subdir = os.path.join(lossless_folder, subdir)
        optimized_subdir = os.path.join(optimized_folder, subdir)
        os.makedirs(lossless_subdir, exist_ok=True)
        os.makedirs(optimized_subdir, exist_ok=True)
        convert_image_subdir(input_subdir, lossless_subdir, optimized_subdir)

def convert_image_subdir(input_subdir, lossless_subdir, optimized_subdir):
    global lossless_count, optimized_count, lossless_OK, lossless_NO, lossless_CHK, img_per_subdir_count, subdir_count, lossless_total, optimized_total, img_total
    lossless_count = optimized_count = img_per_subdir_count = 0
    # ファイルキューの作成
    file_queue = queue.Queue()
    # 入力フォルダ内のすべてのファイルを取得
    for filename in os.listdir(input_subdir):
        if filename.endswith(supported_extensions):
            output_path = os.path.join(lossless_subdir, filename)
            output_path_opt = os.path.join(optimized_subdir, filename)
            # 入力ファイルのパスと出力ファイルのパスの両方をキューに追加
            file_queue.put((os.path.join(input_subdir, filename), output_path, output_path_opt))
            img_per_subdir_count += 1
    verbose_print(f"Total images in {input_subdir}: {img_per_subdir_count}")

    threads = []
    # スレッドの作成と開始
    for _ in range(num_threads):  # num_threadsの数だけスレッドを作成
        t = threading.Thread(target=convert_image,args=(file_queue,lossless_subdir,optimized_subdir))
        t.daemon = True
        t.start()
        threads.append(t)

    # すべてのスレッドが終了するのを待つ
    for t in threads:
        t.join()


# 画像変換関数を定義
def convert_image(file_queue, lossless_subdir, optimized_subdir):
    global lossless_count, optimized_count, lossless_OK, lossless_NO, lossless_CHK, img_per_subdir_count, subdir_count, lossless_total, optimized_total, img_total

    while not file_queue.empty():
        # 入力ファイルのパスと出力ファイルのパスの両方を取得
        file_path,output_path, output_path_opt = file_queue.get()
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

                # DPI情報をXMLデータとして作成
                dpi_str = str(write_img_dpi)
                xml_data = f"""
                <info>
                    <dpi>{dpi_str}</dpi>
                </info>
                """
                # XMLデータをパース
                xml = io.BytesIO(xml_data.encode())
                tree = ET.parse(xml)

                # XMLBoxを作成
                xmlbox = glymur.jp2box.XMLBox(xml=tree)

                
                # Pillow Imageをnumpy arrayに変換
                img_array = np.array(img)

                if not args.optimize:
                    # 一時的なファイル名を作成（日本語をglymurに渡さないため）
                    tmp_filename = os.path.join(tmp_path, str(uuid.uuid4()) + '_temp.jp2')

                    # ロスレス画像の変換と出力
                    jp2Lossless = glymur.Jp2k(tmp_filename, data=img_array, cratios=[1])

                    # XMLBoxを追加
                    jp2Lossless.append(xmlbox)

                    # メタデータを読む関数を定義
                    jp2Read = glymur.Jp2k(tmp_filename)

                    #デバッグ用作成ファイルメタデータ確認＆詳細出力
                    #if log_level == logging.DEBUG:
                        #埋め込んだメタデータ確認
                        #glymur.set_option('print.codestream', False)
                        #debug_print(f"Metadata for converted {file_path}: {jp2Read.box}")
                        
                    # メタデータのboxを検索
                    for box in jp2Read.box:
                        # XMLBoxを探す
                        if isinstance(box, glymur.jp2box.XMLBox):
                            # XMLを解析
                            root = box.xml.getroot()
                            # dpi要素を探す
                            dpi_elements = root.findall('.//dpi')
                            for read_dpi in dpi_elements:
                                verbose_print(f"Confirming"+Fore.YELLOW+" DPI "+Style.RESET_ALL+"for"+file_path +Fore.CYAN+ read_dpi.text+Style.RESET_ALL)

                    #チェックの方法に基づいて画像を読み込み
                    if args.check == "fast" and not args.quick:
                        debug_print("Checking bit-perfect conversion using glymur...")
                        # glymurを使用して画像を読み込み
                        converted_img_array = glymur.Jp2k(tmp_filename)[:]

                        # 元画像と変換後の画像がビットパーフェクトに一致するかどうかを確認
                        is_bitperfect = np.array_equal(img_array, converted_img_array)

                    # 一時的なファイルを最終的な出力パスにリネーム
                    output_path = os.path.join(lossless_subdir, os.path.splitext(os.path.basename(file_path))[0] + '.jp2')
                    shutil.move(tmp_filename, output_path)
                    with count_lock:
                        lossless_count += 1
                        verbose_print(f"Lossless conversion for "+file_path+" complete!")
                        print(Fore.BLUE + "Lossless conversion" + Fore.CYAN+ str(lossless_count) + Fore.WHITE +"/" + Fore.CYAN + str(img_per_subdir_count)+Style.RESET_ALL+"for subdir"+Fore.CYAN+str(subdir_count)+" / "+str(subdir_total)+Style.RESET_ALL)

                    if not args.check == "fast" and not args.quick:
                        debug_print("Checking bit-perfect conversion using Pillow...")
                        # Pillowを使用して画像を読み込み
                        converted_img = Image.open(output_path)
                        converted_img_array = np.array(converted_img)

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
                            error_print(f"Bitperfect conversion for {file_path}: Failed!")
                            print(Fore.YELLOW + "Bitperfect " + Fore.GREEN + " OK " + variable_str(lossless_OK) + Fore.WHITE +"/" +  Fore.RED + "NO " + Fore.CYAN + variable_str(lossless_NO) + Fore.WHITE + "/" + Fore.MAGENTA + "Total " + Fore.CYAN + variable_str(lossless_CHK) + Style.RESET_ALL)
                
                if not args.lossless:
                    # 一時的なファイル名を作成（日本語をglymurに渡さないため）
                    tmp_filename_opt = os.path.join(tmp_path, str(uuid.uuid4()) + '_temp_opt.jp2')

                    # 最適化された画像の変換と出力
                    jp2Optimized = glymur.Jp2k(tmp_filename_opt, data=img_array, cratios=[80])

                    # XMLBoxを追加
                    jp2Optimized.append(xmlbox)

                    # 一時的なファイルを最終的な出力パスにリネーム
                    output_path_opt = os.path.join(optimized_subdir, os.path.splitext(os.path.basename(file_path))[0] + '.jp2')
                    shutil.move(tmp_filename_opt, output_path_opt)

                    with count_lock:
                        optimized_count += 1
                        verbose_print(f"Optimized conversion for {file_path} complete!")
                        print(Fore.BLUE + "Optimized conversion" + Fore.CYAN+ str(optimized_count) + Fore.WHITE +"/" + Fore.CYAN + str(img_per_subdir_count)+Style.RESET_ALL)

        except Exception as e:
            logger.error(f"Error converting file {file_path}: {e}")
            logger.error(traceback.format_exc())
        finally:
            file_queue.task_done()

#本処理開始
subdir_total = len([name for name in os.listdir(input_folder) if os.path.isdir(os.path.join(input_folder, name))])

convert_all_images(input_folder, lossless_folder, optimized_folder)

current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")
info_print(f"Conversion complete! {current_time}")
info_print(f"Total subdirectories processed: {subdir_count} / {subdir_total}")
info_print(f"Total images processed: {optimized_count} / {img_total}")

if args.quick or args.optimize:
    info_print("Note: Lossless check was skipped due to --quick or --optimize option.")
else:
    info_print(Fore.YELLOW + "Bitperfect " +Fore.WHITE+"lossless convertion check"+ Fore.GREEN + " OK " + variable_str(lossless_OK) + Fore.WHITE +"/" +  Fore.RED + "NO " + Fore.CYAN + variable_str(lossless_NO) + Fore.WHITE + "/" + Fore.MAGENTA + "Total " + Fore.CYAN + variable_str(lossless_CHK) + Style.RESET_ALL)