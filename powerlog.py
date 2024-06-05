import os
import sys
import logging
from pathlib import Path
from datetime import datetime
import argparse
import glob
from colorama import Fore, Style

# コマンドライン引数を設定する

parser = argparse.ArgumentParser(description='set log level')
parser.add_argument('--log-level', '-log', default='INFO', choices=['DEBUG', 'VERBOSE', 'INFO', 'WARNING'],
                    help='Set the logging level (default: INFO)')
parser.add_argument('-debug', action='store_const', const='DEBUG', dest='log_level',
                    help='Set the logging level to DEBUG')

# カスタムログレベルVERBOSEを作成
VERBOSE = 15
logging.addLevelName(VERBOSE, "VERBOSE")

def verbose(self, message, *args, **kws):
    if self.isEnabledFor(VERBOSE):
        self._log(VERBOSE, message, args, **kws) 

logging.Logger.verbose = verbose

def create_parser():
    # コマンドライン引数を設定する
    parser = argparse.ArgumentParser(description='set log level')
    parser.add_argument('--log-level', '-log', default='INFO', choices=['DEBUG', 'VERBOSE', 'INFO', 'WARNING'],
                        help='Set the logging level (default: INFO)')
    parser.add_argument('-debug', action='store_const', const='DEBUG', dest='log_level',
                        help='Set the logging level to DEBUG')
    return parser

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

# 呼び出したスクリプト名を取得
script_name = os.path.basename(sys.argv[0]).split('.')[0]

# ログファイル名に日時を含める
log_filename = log_folder / (script_name + f'_{now.strftime("%Y%m%d_%H%M%S")}.log')

logging.basicConfig(filename=log_filename, filemode='a', format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', encoding='utf-8')
logger = logging.getLogger(script_name)  # ロガーの作成

# ログレベルの設定を関数にする
def set_log_level(args):
    global log_level
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
log_files = sorted(glob.glob(str(log_folder / (script_name + '_*.log'))))

# ログファイルが5個以上ある場合、古いものから削除
while len(log_files) > 5:
    os.remove(log_files.pop(0))