import argparse
import configparser
import ast
import os
import tempfile
import powerlog
from powerlog import logger,verbose_print, info_print, error_print, variable_str, debug_print
from . import img2j2k, j2k2pdf,pdf3json,json3pdf,mergejs
import psutil


# コマンドライン引数を解析する
parser = powerlog.create_parser()
parser = argparse.ArgumentParser(description='Convert images to JP2 format and create optimized images for OCR.')
parser.add_argument('--log-level', '-log', default='INFO', choices=['DEBUG', 'VERBOSE', 'INFO', 'WARNING'],
                    help='Set the logging level (default: DEBUG)')
parser.add_argument('-debug', action='store_const', const='DEBUG', dest='log_level',
                    help='Set the logging level to DEBUG')
args = parser.parse_args()

powerlog.set_log_level(args)

# 接待ファイルのパス
default_path = './default.ini'
settings_path = './settings.ini'

# 設定ファイルを読み込む
def load_config(default_path, settings_path):
    config = configparser.ConfigParser()
    config.read(default_path)  # デフォルトの設定を読み込む
    config.read(settings_path)  # ユーザーの設定を読み込む（存在する場合）
    return config

# main関数

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('module', choices=['image', 'pdf', 'ocr', 'text', 'merge', 'full'], help='The module to run')
    parser.add_argument('--image', nargs=argparse.REMAINDER, help='Arguments for the image module')
    parser.add_argument('--pdf', nargs=argparse.REMAINDER, help='Arguments for the pdf module')
    parser.add_argument('--ocr', nargs=argparse.REMAINDER, help='Arguments for the ocr module')
    parser.add_argument('--text', nargs=argparse.REMAINDER, help='Arguments for the text module')
    parser.add_argument('--merge', nargs=argparse.REMAINDER, help='Arguments for the merge module')
    args = parser.parse_args()

    if args.module == 'full':
        img2j2k.run(*args.image_args)
        j2k2pdf.run(*args.pdf_args)
        pdf3json.run(*args.ocr_args)
        json3pdf.run(*args.text_args)
        mergejs.run(*args.merge_args)
    elif args.module == 'image':
        img2j2k.run(*args.args)
    elif args.module == 'pdf':
        j2k2pdf.run(*args.args)
    elif args.module == 'ocr':
        pdf3json.run(*args.args)
    elif args.module == 'text':
        json3pdf.run(*args.args)
    elif args.module == 'merge':
        mergejs.run(*args.args)


# .ini [Paths] section
config = load_config(default_path, settings_path)
input_folder = config.get('Paths', 'input_folder', fallback='./OriginalImages') # input_folder for img2j2k.py
lossless_folder = config.get('Paths', 'lossless_folder',fallback='./TEMP/lossless' ) #lossless_folder for img2j2k.py
optimized_folder = config.get('Paths', 'optimized_folder',fallback='./TEMP/optimized') #optimized_folder for img2j2k.py
origpdf_folder = config.get('Paths', 'origpdf_folder') # existing_pdf_folder for mergejs.py --clear
optpdf_folder = config.get('Paths', 'optpdf_folder') # existing_pdf_folder for mergejs.py
json_folder = config.get('Paths', 'json_folder')
textpdf_folder = config.get('Paths', 'textpdf_folder') # output_folder for json3pdf.py, text_layer_folder for mergejs.py
clearpdf_folder = config.get('Paths', 'clearpdf_folder') # output_folder for json3pdf.py, text_layer_folder for mergejs.py --clear
draftpdf_folder = config.get('Paths', 'draftpdf_folder') # output_folder for mergejs.py
finalpdf_folder = config.get('Paths', 'finalpdf_folder') # output_folder for mergejs.py --clear
use_system_temp = config.getboolean('Paths', 'use_system_temp')
divpdf_folder = config.get('Paths', 'divpdf_folder')
divjson_folder = config.get('Paths', 'divjson_folder')
tmp_path = config.get('Paths', 'tmp_path', fallback='.TEMP/tmp') #--temp for img2j2k.py
if args.temp.lower() == 'system':
    tmp_path = tempfile.gettempdir()
imagelog_folder = config.get('Paths', 'imagelog_folder')

# .ini [image conversion] section
skip_conversion_extensions = {
    'skip_conversion_extensions': config.get('image conversion', 'skip_conversion_extensions').split(', ')
} # skip conversion for pdf compatible images #image_extensions for j2k2pdf.py
supported_extensions = {
    'supported_extensions': config.get('image conversion', 'supported_extensions').split(', ')
} # supported image extensions for pillow
openjpeg_dll_name = config.get('image conversion', 'openjpeg_dll_name') #openjpeg_dll_name for j2k2pdf.py
if not config.get('image conversion', 'num_physical_cores') == None:
    num_physical_cores = config.getint('image conversion', 'num_physical_cores')
else:
    num_physical_cores = psutil.cpu_count(logical=False)
num_threads = num_physical_cores // 2
DPI = config.getint('image conversion', 'DPI') # --dpi for img2j2k.py
lossless_conversion_check_mode = config.get('image conversion', 'lossless_conversion_check_mode') # --check,--quick for img2j2k.py
lossless_conversion = config.getboolean('image conversion', 'lossless_conversion') # Default or --lossless for img2j2k.py
optimizing_conversion = config.getboolean('image conversion', 'optimizing_conversion') # Default or --optimize for img2j2k.py

# .ini [glymur] section
glymur_config_path = config.get('glymur', 'glymur_config_path') #glymur_config_path for img2j2k.py
glymur_threads = config.getint('glymur', 'glymur_threads') #glymur_threads for img2j2k.py

# .ini [OCR] section
document_intelligence_credentials_path = config.get('OCR', 'document_intelligence_credentials_path')#document_intelligence_credentials_path for pdf3json.py
div_mode = config.get('OCR', 'div_mode') #--divide, --pages, --no-divide for pdf3json.py
default_max_pages = config.getint('OCR', 'default_max_pages') # default_max_pages for pdf3json.py
max_attemps = config.getint('OCR', 'max_attemps') # --attempts for pdf3json.py
preserve_partial_files = config.getboolean('OCR', 'preserve_partial_files') # --no-delete for pdf3json.py

# .ini [document settings] section
font_size = config.getint('document settings', 'font_size') #--size for json3pdf.py
font_threshold = config.get('document settings', 'font_threshold') #--font-threshold for json3pdf.py
horizontal_font = config.get('document settings', 'horizontal_font') #--hfont for json3pdf.py
vertical_font = config.get('document settings', 'vertical_font') #--vfont for json3pdf.py
default_dpi = config.getint('document settings', 'default_dpi') #--dpi for json3pdf.py
page_size = config.get('document settings', 'page_size') #--page for json3pdf.py
layout_type = config.get('document settings', 'layout_type') #--layout for json3pdf.py
area_threshold = config.getint('document settings', 'area_threshold') #--area for json3pdf.py
similarity_threshold = config.getfloat('document settings', 'similarity_threshold') #--similarity for json3pdf.py
adjust_layout = config.getboolean('document settings', 'adjust_layout') #--adjust for json3pdf.py
coordinate_threshold = config.getint('document settings', 'coordinate_threshold') #--coordinate for json3pdf.py
if args.clear:
    is_clear = True
else:
    is_clear = False
#--clear for json3pdf.py, mergejs.py
default_layout_search_limit = config.getint('document settings', 'default_layout_search_limit') #--search for json3pdf.py
default_layout_ignore = config.getint('document settings', 'default_layout_ignore') #--search for json3pdf.py
horizonatl_adjustment = config.getint('document settings', 'horizonatl_adjustment') #--left, --right for mergejs.py
vertical_adjustment = config.getint('document settings', 'vertical_adjustment') #--up, --down for mergejs.py
adjustment_dpi = config.getint('document settings', 'adjustment_dpi') #--dpi for mergejs.py
max_pagesize = config.get('document settings', 'max_pagesize') #--threshold for mergejs.py
proccess_num_pages = config.getint('document settings', 'proccess_num_pages') #--process-pages for mergejs.py

# .ini [PageSizes] section
page_sizes = {}
for key in config['PageSizes']:
    page_sizes[key] = tuple(ast.literal_eval(config['PageSizes'][key]))

# .ini [logs] section
log_folder = config.get('logs', 'log_folder') #--log_folder for all scripts
log_level = config.get('logs', 'log_level') #--log_level for all scripts
debug = config.getboolean('logs', 'debug') #--debug for all scripts

[logs]
log_folder = ./logs
log_level = INFO #--log_level for all scripts. DEBUG, VERBOSE, INFO, WARNING, ERROR, CRITICAL
debug = False #--debug for all scripts

