import argparse
import configparser
import powerlog
from powerlog import logger,verbose_print, info_print, error_print, variable_str, debug_print
from . import img2j2k, j2k2pdf,pdf3json,json3pdf,mergejs


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
    parser.add_argument('module', choices=['image', 'pdf', 'ocr', 'text', 'merge'], help='The module to run')
    parser.add_argument('args', nargs=argparse.REMAINDER, help='Arguments for the module')
    args = parser.parse_args()

    if args.module == 'image':
        img2j2k.run(args.args)
    elif args.module == 'pdf':
        j2k2pdf.run(args.args)
    elif args.module == 'ocr':
        pdf3json.run(args.args)
    elif args.module == 'text':
        json3pdf.run(args.args)
    elif args.module == 'merge':
        mergejs.run(args.args)

config = load_config(default_path, settings_path)
input_folder = config.get('Paths', 'input_folder')
lossless_folder = config.get('Paths', 'lossless_folder')
optimized_folder = config.get('Paths', 'optimized_folder')
origpdf_folder = config.get('Paths', 'origpdf_folder')
optpdf_folder = config.get('Paths', 'optpdf_folder')
json_folder = config.get('Paths', 'json_folder')
textpdf_folder = config.get('Paths', 'textpdf_folder')
clearpdf_folder = config.get('Paths', 'clearpdf_folder')
draftpdf_folder = config.get('Paths', 'draftpdf_folder')
finalpdf_folder = config.get('Paths', 'finalpdf_folder')
use_system_temp = config.getboolean('Paths', 'use_system_temp')
divpdf_folder = config.get('Paths', 'divpdf_folder')
divjson_folder = config.get('Paths', 'divjson_folder')
tmp_path = config.get('Paths', 'tmp_path')
imagelog_folder = config.get('Paths', 'imagelog_folder')

skip_conversion_extensions = config.get('image conversion', 'skip_conversion_extensions')
supported_extensions = config.get('image conversion', 'supported_extensions')
openjpeg_dll_name = config.get('image conversion', 'openjpeg_dll_name')

[Paths]
input_folder = ./OriginalImages # input_folder for img2j2k.py
lossless_folder = ./TEMP/lossless #lossless_folder for img2j2k.py  
optimized_folder = ./TEMP/optimized #optimized_folder for img2j2k.py
origpdf_folder = ./OriginalPDF # existing_pdf_folder for mergejs.py --clear
optpdf_folder = ./OptimizedPDF # existing_pdf_folder for mergejs.py
json_folder = ./DIjson
textpdf_folder = ./OCRtextPDF # output_folder for json3pdf.py, text_layer_folder for mergejs.py 
clearpdf_folder = ./OCRclearPDF # output_folder for json3pdf.py, text_layer_folder for mergejs.py --clear
draftpdf_folder = ./DraftPDF # output_folder for mergejs.py
finalpdf_folder = ./OCRfinalPDF # output_folder for mergejs.py --clear
use_system_temp = False
divpdf_folder = ./TEMP/divPDF
divjson_folder = ./TEMP/json
tmp_path = ./TEMP/tmp #--temp for img2j2k.py
imagelog_folder = ./TEMP/imagelogs

[image conversion]
skip_conversion_extensions = .j2c, .j2k, .jpc, .jp2, .jpf, .jpg, .jpeg, .jpm, .jpg2, .jpx, .mj2 # skip conversion for pdf compatible images #image_extensions for j2k2pdf.py
supported_extensions = .bmp, .gif, .j2c, .j2k, .jpc, .jp2, .jpf, .jpg, .jpeg, .jpm, .jpg2, .jpx, .mj2, .png, .psd, .tif, .tiff, .webp # supported image extensions for pillow
openjpeg_dll_name = openjp2.dll #openjpeg_dll_name for j2k2pdf.py
num_physical_cores = #psutil.cpu_count(logical=False)
num_threads = # number of simultaneous images proceessed. #num_physical_cores // 2
DPI = 600 # --dpi for img2j2k.py
lossless_conversion_check_mode = slow # --check,--quick for img2j2k.py
lossless_conversion = True # Default or --lossless for img2j2k.py
optimizing_conversion = True # Default or --optimize for img2j2k.py


[glymur]
glymur_config_path = #os.path.join(os.path.expanduser(~), glymur, glymurrc)
glyumur_threads = 2 # number of threads to use per image. #glymur.set_option(lib.num_threads, 2)

[OCR]
document_intelligence_credentials_path = ./diAPI.env
div_mode = auto #--divide, --pages, --no-divide for pdf3json.py
default_max_pages = 300 # default_max_pages for pdf3json.py
max_attemps = 3 # --attempts for pdf3json.py
preserve_partial_files = False # --no-delete for pdf3json.py


[document settings]
font_size = 100 #--size for json3pdf.py
font_threshold = #--font-threshold for json3pdf.py
horizontal_font = NotoSansJP-Regular.ttf #--hfont for json3pdf.py
vertical_font = NotoSansJP-Regular.ttf #--vfont for json3pdf.py
default_dpi = 600 #--dpi for json3pdf.py
page_size = A5 #--page for json3pdf.py
layout_type = line #--layout for json3pdf.py
area_threshold = 80 #--area for json3pdf.py
similarity_threshold = 0.1 #--similarity for json3pdf.py
adjust_layout = False #--adjust for json3pdf.py
coordinate_threshold = 80 #--coordinate for json3pdf.py
#--clear for json3pdf.py, mergejs.py
default_layout_search_limit = 50 #--search for json3pdf.py
default_layout_ignore = 2 #--search for json3pdf.py
horizonatl_adjustment = 0 #--left, --right for mergejs.py
vertical_adjustment = 0 #--up, --down for mergejs.py
adjustment_dpi = 600 #--dpi for mergejs.py
max_pagesize = Blanket #--threshold for mergejs.py

[PageSizes]
A3 = [842, 1191]
A4 = [595, 842]
A5 = [420, 595]
A6 = [298, 420]
B4 = [729, 1032]
B5 = [516, 729]
B6 = [363, 516]
B7 = [258, 363]
Tabloid = [792, 1224]
Blanket = [4320, 6480]

[logs]
log_folder = ./logs
log_level = INFO #--log_level for all scripts. DEBUG, VERBOSE, INFO, WARNING, ERROR, CRITICAL
debug = False #--debug for all scripts