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
parser.add_argument('--clear', '-c', action='store_true', help='clear text mode.')
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
origpdf_folder = config.get('Paths', 'origpdf_folder',fallback='./OriginalPDF') # existing_pdf_folder for mergejs.py --clear
optpdf_folder = config.get('Paths', 'optpdf_folder',fallback='./OptimizedPDF') # existing_pdf_folder for mergejs.py
json_folder = config.get('Paths', 'json_folder',fallback='./DIjson')
textpdf_folder = config.get('Paths', 'textpdf_folder',fallback='./OCRtextPDF') # output_folder for json3pdf.py, text_layer_folder for mergejs.py
clearpdf_folder = config.get('Paths', 'clearpdf_folder',fallback='./OCRclearPDF') # output_folder for json3pdf.py, text_layer_folder for mergejs.py --clear
draftpdf_folder = config.get('Paths', 'draftpdf_folder',fallback='./DraftPDF') # output_folder for mergejs.py
finalpdf_folder = config.get('Paths', 'finalpdf_folder',fallback='./OCRfinalPDF') # output_folder for mergejs.py --clear
use_system_temp = config.getboolean('Paths', 'use_system_temp',fallback= False)
divpdf_folder = config.get('Paths', 'divpdf_folder',fallback='./TEMP/divpdf')
divjson_folder = config.get('Paths', 'divjson_folder',fallback='./TEMP/json')
tmp_path = config.get('Paths', 'tmp_path', fallback='.TEMP/tmp') #--temp for img2j2k.py
if args.temp.lower() == 'system':
    tmp_path = tempfile.gettempdir()
imagelog_folder = config.get('Paths', 'imagelog_folder',fallback='./TEMP/imagelogs')

# .ini [dpi settings] section
use_individual_dpi = config.getboolean('dpi settings', 'use_individual_dpi',fallback= False)
main_default_dpi = config.getint('dpi settings', 'main_default_dpi',fallback= 600)

default_img_dpi = config.getint('image conversion', 'default_img_dpi',fallback=600) # --dpi for img2j2k.py
force_img_dpi = config.getboolean('image conversion', 'force_dpi',fallback= False) # --force-dpi for img2j2k.py

default_pdf_dpi = config.getint('image to pdf', 'default_pdf_dpi', fallback= 600) # --dpi for j2k2pdf.py
force_pdf_dpi = config.getboolean('image to pdf', 'force_pdf_dpi',fallback= False) # --force-dpi for j2k2pdf.py

default_text_dpi = config.getint('document settings', 'default_text_dpi',fallback= 600) #--dpi for json3pdf.py

adjustment_dpi = config.getint('document settings', 'adjustment_dpi',fallback= 600) #--dpi for mergejs.py
if use_individual_dpi == True:
    default_img_dpi = main_default_dpi
    default_pdf_dpi = main_default_dpi
    default_text_dpi = main_default_dpi
    adjustment_dpi = main_default_dpi

if default_img_dpi>1 and force_img_dpi == True:
    default_img_dpi *= -1

if args.module == 'image':
    if '--dpi' in args.image:
        dpi_index = args.image.index('--dpi')
        if dpi_index + 1 < len(args.image):
            default_img_dpi = int(args.image[dpi_index + 1])



if default_pdf_dpi > 0 and force_pdf_dpi == True:
    default_pdf_dpi *= -1

if args.module == 'pdf':
    if '--dpi' in args.pdf:
        dpi_index = args.pdf.index('--dpi')
        if dpi_index + 1 < len(args.pdf):
            default_pdf_dpi = int(args.pdf[dpi_index + 1])


if args.module == 'text':
    if '--dpi' in args.text:
        dpi_index = args.text.index('--dpi')
        if dpi_index + 1 < len(args.text):
            default_text_dpi = int(args.text[dpi_index + 1])


if args.module == 'merge':
    if '--dpi' in args.merge:
        dpi_index = args.merge.index('--dpi')
        if dpi_index + 1 < len(args.merge):
            adjustment_dpi = int(args.merge[dpi_index + 1])


# .ini [image conversion] section
skip_conversion_extensions = {
    'skip_conversion_extensions': config.get('image conversion', 'skip_conversion_extensions',fallback = '.j2c, .j2k, .jpc, .jp2, .jpf, .jpg, .jpeg, .jpm, .jpg2, .jpx, .mj2').split(', ')
} # skip conversion for pdf compatible images #image_extensions for j2k2pdf.py

supported_extensions = {
    'supported_extensions': config.get('image conversion', 'supported_extensions',fallback='.bmp, .gif, .j2c, .j2k, .jpc, .jp2, .jpf, .jpg, .jpeg, .jpm, .jpg2, .jpx, .mj2, .png, .psd, .tif, .tiff, .webp').split(', ')
} # supported image extensions for pillow
openjpeg_dll_name = config.get('image conversion', 'openjpeg_dll_name',fallback='openjp2.dll') #openjpeg_dll_name for j2k2pdf.py
if not config.get('image conversion', 'num_physical_cores') == None:
    num_physical_cores = config.getint('image conversion', 'num_physical_cores')
else:
    num_physical_cores = psutil.cpu_count(logical=False)
num_threads = num_physical_cores // 2


lossless_conversion_check_mode = config.get('image conversion', 'lossless_conversion_check_mode',fallback='slow') # --check,--quick for img2j2k.py
if args.module == 'image':
    if '--check' in args.image:
        check_mode_index = args.image.index('--check')
        if check_mode_index + 1 < len(args.image):
            lossless_conversion_check_mode = args.image[check_mode_index + 1]
    elif '--quick' in args.image:
        lossless_conversion_check_mode = 'quick'

lossless_conversion = config.getboolean('image conversion', 'lossless_conversion',fallback= True) # Default or --lossless for img2j2k.py
optimizing_conversion = config.getboolean('image conversion', 'optimizing_conversion',fallback= True) # Default or --optimize for img2j2k.py
if lossless_conversion == False and optimizing_conversion == True:
    conversion_method_args = ['--optimize']
elif lossless_conversion == True and optimizing_conversion == False:
    conversion_method_args = ['--lossless']
else lossless_conversion == True and optimizing_conversion == True:
    conversion_method_args = None

# .ini [glymur] section
if not config.get('glymur', 'glymur_config_path') == None:
    glymur_config_path = config.get('glymur', 'glymur_config_path') #glymur_config_path for img2j2k.py
else:
    glymur_config_path = os.path.join(os.path.expanduser(~), glymur, glymurrc)
glymur_threads = config.getint('glymur', 'glymur_threads',fallback= 2) #glymur_threads for img2j2k.py


# .ini [OCR] section
document_intelligence_credentials_path = config.get('OCR', 'document_intelligence_credentials_path',fallback='./diAPI.env')#document_intelligence_credentials_path for pdf3json.py
div_mode = config.get('OCR', 'div_mode', fallback='auto') #(auto,pages,chunk,full)--divide, --pages, --no-divide for pdf3json.py
div_pages = config.getint('OCR', 'div_pages',fallback= 300) #--pages for pdf3json.py
divide_value = config.getint('OCR', 'divide_value',fallback= 1) #--divide for pdf3json.py
default_max_pages = config.getint('OCR', 'default_max_pages',fallback=300) # default_max_pages for pdf3json.py

if args.module == 'ocr':
    if '--pages' in args.ocr:
        div_mode = 'pages'
        pages_index = args.ocr.index('--pages')
        if pages_index + 1 < len(args.ocr):
            div_pages = int(args.ocr[pages_index + 1])
    elif '--divide' in args.ocr:
        div_mode = 'divide'
        divide_index = args.ocr.index('--divide')
        if divide_index + 1 < len(args.ocr):
            divide_value = int(args.ocr[divide_index + 1])
    elif '--no-divide' in args.ocr:
        div_mode = 'full'


max_attemps = config.getint('OCR', 'max_attemps',fallback= 3) # --attempts for pdf3json.py
if args.module == 'ocr':
    if '--attempts' in args.ocr:
        attempts_index = args.ocr.index('--attempts')
        if attempts_index + 1 < len(args.ocr):
            max_attemps = int(args.ocr[attempts_index + 1])

preserve_partial_files = config.getboolean('OCR', 'preserve_partial_files',fallback= False) # --no-delete for pdf3json.py
if args.module == 'ocr':
    if '--no-delete' in args.ocr:
        preserve_partial_files = True

# .ini [document settings] section
font_size = config.getint('document settings', 'font_size',fallback= 100) #--size for json3pdf.py
if args.module == 'text':
    if '--size' in args.text:
        size_index = args.text.index('--size')
        if size_index + 1 < len(args.text):
            font_size = int(args.text[size_index + 1])

font_threshold = config.get('document settings', 'font_threshold',fallback=None) #--font-threshold for json3pdf.py
if args.module == 'text':
    if '--font-threshold' in args.text:
        font_threshold_index = args.text.index('--font-threshold')
        if font_threshold_index + 1 < len(args.text):
            font_threshold = args.text[font_threshold_index + 1]

horizontal_font = config.get('document settings', 'horizontal_font',fallback='NotoSansJP-Regular.ttf') #--hfont for json3pdf.py
if args.module == 'text':
    if '--hfont' in args.text:
        hfont_index = args.text.index('--hfont')
        if hfont_index + 1 < len(args.text):
            horizontal_font = args.text[hfont_index + 1]

vertical_font = config.get('document settings', 'vertical_font',fallback='NotoSansJP-Regular.ttf') #--vfont for json3pdf.py
if args.module == 'text':
    if '--vfont' in args.text:
        vfont_index = args.text.index('--vfont')
        if vfont_index + 1 < len(args.text):
            vertical_font = args.text[vfont_index + 1]

page_size = config.get('document settings', 'page_size',fallback='A5') #--page for json3pdf.py
if args.module == 'text':
    if '--page' in args.text:
        page_index = args.text.index('--page')
        if page_index + 1 < len(args.text):
            page_size = args.text[page_index + 1]

layout_type = config.get('document settings', 'layout_type',fallback='line') #--layout for json3pdf.py
if args.module == 'text':
    if '--layout' in args.text:
        layout_index = args.text.index('--layout')
        if layout_index + 1 < len(args.text):
            layout_type = args.text[layout_index + 1]

area_threshold = config.getint('document settings', 'area_threshold',fallback= 80) #--area for json3pdf.py
if args.module == 'text':
    if '--area' in args.text:
        area_index = args.text.index('--area')
        if area_index + 1 < len(args.text):
            area_threshold = int(args.text[area_index + 1])

similarity_threshold = config.getfloat('document settings', 'similarity_threshold',fallback=0.1) #--similarity for json3pdf.py
if args.module == 'text':
    if '--similarity' in args.text:
        similarity_index = args.text.index('--similarity')
        if similarity_index + 1 < len(args.text):
            similarity_threshold = float(args.text[similarity_index + 1])

adjust_layout = config.getboolean('document settings', 'adjust_layout',fallback= False) #--adjust for json3pdf.py
if args.module == 'text':
    if '--adjust' in args.text:
        adjust_layout = True

coordinate_threshold = config.getint('document settings', 'coordinate_threshold',fallback=80) #--coordinate for json3pdf.py
if args.module == 'text':
    if '--coordinate' in args.text:
        coordinate_index = args.text.index('--coordinate')
        if coordinate_index + 1 < len(args.text):
            coordinate_threshold = int(args.text[coordinate_index + 1])

if args.clear:
    is_clear = True

elif args.module == 'full':
    if '--clear' in args.text and '--clear' in args.merge:
        is_clear = True
    if '--clear' not in args.text and '--clear' not in args.merge:
        is_clear = False
    else:
        error_print('"--clear" option mismatch!!')
        error_print('You must use "--clear" for the main module or with both the text and merge modules in "--full" mode')
        exit(1)
else:
    is_clear = False


#--clear for json3pdf.py, mergejs.py
default_layout_search_limit = config.getint('document settings', 'default_layout_search_limit',fallback= 50) #--search for json3pdf.py
default_layout_ignore = config.getint('document settings', 'default_layout_ignore',fallback= 2) #--search for json3pdf.py
search_limit = default_layout_search_limit,default_layout_ignore
if args.module == 'text':
    if '--search' in args.text:
        search_index = args.text.index('--search')
        if search_index + 1 < len(args.text):
            search_limit = int(args.text[search_index + 1])

horizonatl_adjustment = config.getint('document settings', 'horizonatl_adjustment',fallback= 0) #--left, --right for mergejs.py
if args.module == 'merge':
    if '--left' in args.merge:
        left_index = args.merge.index('--left')
        if left_index + 1 < len(args.merge):
            horizonatl_adjustment = -int(args.merge[left_index + 1])
    elif '--right' in args.merge:
        right_index = args.merge.index('--right')
        if right_index + 1 < len(args.merge):
            horizonatl_adjustment = int(args.merge[right_index + 1])

vertical_adjustment = config.getint('document settings', 'vertical_adjustment',fallback= 0) #--up, --down for mergejs.py
if args.module == 'merge':
    if '--up' in args.merge:
        up_index = args.merge.index('--up')
        if up_index + 1 < len(args.merge):
            vertical_adjustment = int(args.merge[up_index + 1])
    elif '--down' in args.merge:
        down_index = args.merge.index('--down')
        if down_index + 1 < len(args.merge):
            vertical_adjustment = -int(args.merge[down_index + 1])


max_pagesize = config.get('document settings', 'max_pagesize') #--threshold for mergejs.py
if args.module == 'merge':
    if '--threshold' in args.merge:
        threshold_index = args.merge.index('--threshold')
        if threshold_index + 1 < len(args.merge):
            max_pagesize = args.merge[threshold_index + 1]

proccess_num_pages = config.getint('document settings', 'proccess_num_pages') #--process-pages for mergejs.py
if args.module == 'merge':
    if '--process-pages' in args.merge:
        process_index = args.merge.index('--process-pages')
        if process_index + 1 < len(args.merge):
            proccess_num_pages = int(args.merge[process_index + 1])

# .ini [PageSizes] section
page_sizes = {
    "A3": (842, 1191),
    "A4": (595, 842),
    "A5": (420, 595),
    "A6": (298, 420),
    "B4": (729, 1032),
    "B5": (516, 729),
    "B6": (363, 516),
    "B7": (258, 363),
    "Tabloid": (792, 1224),
}

for key in config['PageSizes']:
    page_sizes[key] = tuple(ast.literal_eval(config['PageSizes'][key]))

# .ini [logs] section
log_folder = config.get('logs', 'log_folder',fallback='./logs') #--log_folder for all scripts
log_level = config.get('logs', 'log_level',fallback='INFO') #--log_level for all scripts
debug = config.getboolean('logs', 'debug',fallback= False) #--debug for all scripts

