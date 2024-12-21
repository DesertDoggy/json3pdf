import argparse
import configparser
import os
import shutil
import platform
import glob
import subprocess
import powerlog
import re
from powerlog import logger,verbose_print, info_print, error_print, variable_str, debug_print,warning_print
from PyPDF2 import PdfReader


# コマンドライン引数を解析する
parser = powerlog.create_parser()
parser = argparse.ArgumentParser(description='Add ICC profile to PDF file.')
parser.add_argument('--log-level', '-log', default='INFO', choices=['DEBUG', 'VERBOSE', 'INFO', 'WARNING'],
                    help='Set the logging level (default: DEBUG)')
parser.add_argument('-debug', action='store_const', const='DEBUG', dest='log_level',
                    help='Set the logging level to DEBUG')
parser.add_argument('--icc', help='set ICC profile to use')
args = parser.parse_args()

powerlog.set_log_level(args)


# 設定ファイルのパス
default_path = './default.ini'
settings_path = './settings.ini'

# 設定ファイルを読み込む
def load_config(default_path, settings_path):
    config = configparser.ConfigParser()
    config.read(default_path)  # デフォルトの設定を読み込む
    config.read(settings_path)  # ユーザーの設定を読み込む（存在する場合）
    return config

class ModuleError(Exception):
    pass

def get_icc_profiles(pdf_path):
    command = [
        "gswin64c",
        "-o", "-",
        "-sDEVICE=txtwrite",
        "-f", pdf_path
    ]
    result = subprocess.run(command, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, encoding='utf-8')
    output = result.stdout
    icc_profiles = re.findall(r"/OutputICCProfile\s*\((.*?)\)", output)
    return icc_profiles


def add_icc_profile(input_pdf_path, output_pdf_path, icc_profile_path):
    # Check if the input PDF file exists
    if not os.path.isfile(input_pdf_path):
        error_print(f"Input PDF file {input_pdf_path} does not exist.")
        return

    # Check if the ICC profile file exists
    if not os.path.isfile(icc_profile_path):
        error_print(f"ICC profile file {icc_profile_path} does not exist.")
        return

    # Check if Ghostscript is installed
    if not shutil.which("gswin64c"):
        error_print("Ghostscript is not installed or not found in the system PATH.")
        return
    

    
    try:
        print("Adding ICC profile "+icc_profile_path)
        command = [
            "gswin64c",
            "-o", output_pdf_path,
            "-sDEVICE=pdfwrite",
            "-dDELAYSAFER",
            "-dEmbedAllFonts=true",
            "-dSubsetFonts=false",
            "-sOutputICCProfile=" + icc_profile_path,
            "-dPassThroughJPEGImages",
            "-dPassthroughJPXImages"
            "-f", input_pdf_path
        ]
        result = subprocess.run(command, check=True, stderr=subprocess.PIPE,encoding='utf-8')
        info_print("Added ICC profile "+icc_profile_path+" to "+output_pdf_path)
        if os.path.exists(output_pdf_path):
            icc_profiles = get_icc_profiles(output_pdf_path)
            info_print(f"Reading Info for {output_pdf_path}")
            info_print(f"{icc_profiles}")
        else:
            error_print(f"Output file {output_pdf_path} was not created")
    except Exception as e:
        error_print("Failed to add ICC profile to "+input_pdf_path)
        error_print('Error details: ' + str(e))
        if 'result' in locals():
            error_print(result.stderr)
    

def add_icc_to_folder(input_folder,output_folder,icc_profile_path):
    pdf_files = os.listdir(input_folder)
    if len(pdf_files)>0:
        for pdf_file in pdf_files:
            if pdf_file.endswith(".pdf"):
                pdf_name = os.path.basename(pdf_file)
                input_pdf_path = os.path.join(input_folder, pdf_file)
                output_pdf_path = os.path.join(output_folder,pdf_name)
                add_icc_profile(input_pdf_path,output_pdf_path,icc_profile_path)
    else:
        error_print(f"No PDF files were found in {input_folder}")

def search_icc_profiles(icc_profile_folder, icc_profile_name,icc_manufactures):
    # icc_profile_folder内の全ての.iccファイルを検索
    icc_files = glob.glob(os.path.join(icc_profile_folder, "*.icc")) + glob.glob(os.path.join(icc_profile_folder, "*.icm"))

    # icc_profile_nameを含むファイルを探す
    matching_files = [file for file in icc_files if icc_profile_name.lower() in os.path.basename(file).lower()]

    if not matching_files:
        error_print(f"ICC profile including {icc_profile_name} was not found")
        icc_profile_path = None
        return icc_profile_path
    else:
        if len(matching_files)>1:
            warning_print(f"Multiple files mataching {icc_profile_name} were found.")
            warning_print("Profile priority is Scanner > Hardware > Software/OS manufactures > Generic profiles.")
            warning_print("Use precise profile name to add a specific profile")
        icc_profile_path = None
        if icc_profile_name.lower() == "srgb" or icc_profile_name.lower() == "p3":
            if icc_manufactures:
                for manufacturer in icc_manufactures:
                    for file in matching_files:
                        if manufacturer.lower() in os.path.basename(file).lower():
                            icc_profile_path = file
                            break
                    if icc_profile_path:
                        break

        if not icc_profile_path:
            icc_profile_path = matching_files[0]
            warning_print(f"{icc_profile_path} will be used for {icc_profile_name} profile")

        return icc_profile_path

def run (input_folder = None,output_folder = None,icc_profile_folder = None,icc_profile_name = None, icc_manufactures = None):
    local_dir = os.getcwd()
    if input_folder == None:
        input_folder = local_dir
        warning_print("Input PDF folder for adding ICC was not defined. Set input folder to "+input_folder)
    if output_folder == None:
        output_folder = os.path.join(local_dir,"ICC_PDF")
        warning_print("Output folder for adding ICC was not defined. Set output folder to "+output_folder)
    if icc_profile_folder == None:
        icc_profile_folder = os.path.join(local_dir,"data","icc")
        warning_print("ICC profile folder was not defined. Will search for profile in OS statndard directory and "+icc_profile_folder)
    if platform.system() == "Windows":
        os_icc_dir = r"C:\Windows\System32\spool\drivers\color"
    elif platform.system() == "Darwin":
        os_icc_dir = "/Library/ColorSync/Profiles"
    elif platform.system() == "Linux":
        os_icc_dir = "/usr/share/color/icc"
    else:
        os_icc_dir = None  
    debug_print("operating system default icc path is "+str(os_icc_dir))
    if icc_profile_name == None:
        icc_profile_name = "sRGB"
        warning_print(f"ICC profile was not specified. Set to defaults. {icc_profile_name}")
    if os.path.exists(input_folder):
        if os.path.exists(icc_profile_folder):
            info_print(f"Searching for ICC profile {icc_profile_name} in {icc_profile_folder}")
            icc_profile_path = search_icc_profiles(icc_profile_folder,icc_profile_name,icc_manufactures)
        if not icc_profile_path:
            if os_icc_dir:
                warning_print(f"ICC profile folder not specified. Searching for ICC Profile {icc_profile_name} in {os_icc_dir}")
                icc_profile_path = search_icc_profiles(os_icc_dir,icc_profile_name,icc_manufactures)
        if icc_profile_path:
            add_icc_to_folder (input_folder, output_folder, icc_profile_path)
        else:
            error_print(f"ICC profile {icc_profile_name} was not found on system")



    else:
        error_print("Input folder for adding ICC profile does not exist")


config = load_config(default_path, settings_path)

icc_manufacture_scanner = config.get('color_management', 'scanner_manufacturer',fallback = 'EPSON, ew, CANON, NEC, PFU, Fujitsu, Brother').split(', ')
icc_manufacture_hardware = config.get('color_management', 'hardware_manufacturer',fallback = 'ASUS, Dell, Gigabyte').split(', ')
icc_manufacture_software = config.get('color_management', 'software_manufacturer',fallback = 'Adobe, Microsoft, Apple, Google').split(', ')
icc_manufactures = icc_manufacture_scanner + icc_manufacture_hardware + icc_manufacture_software

input_folder = "./BeforeICC"
output_folder = "./AfterICC"
icc_profile_folder = "./data/icc"
icc_profile_name = args.icc

run (input_folder,output_folder,icc_profile_folder,icc_profile_name, icc_manufactures)
