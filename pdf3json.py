from dotenv import load_dotenv
import os
import argparse
from azure.core.credentials import AzureKeyCredential
from azure.ai.documentintelligence import DocumentIntelligenceClient
import json
import powerlog
from powerlog import logger,verbose_print, info_print,warning_print, error_print, variable_str, debug_print
from PyPDF2 import PdfReader, PdfWriter
import base64
import shutil
import math

# コマンドライン引数を解析する
parser = powerlog.create_parser()
parser = argparse.ArgumentParser(description='Add a text layer to a PDF file.')
parser.add_argument('--log-level', '-log', default='INFO', choices=['DEBUG', 'VERBOSE', 'INFO', 'WARNING'],
                    help='Set the logging level (default: INFO)')
parser.add_argument('-debug', action='store_const', const='DEBUG', dest='log_level',
                    help='Set the logging level to DEBUG')
dividing = parser.add_mutually_exclusive_group()
dividing.add_argument('-p', '--pages', type=int, help='divide the PDF into specified number of pages. Default:300')
dividing.add_argument('--no-divide', action='store_true', help='Overrides auto divide of 300 pages and will try to process whole PDF')
dividing.add_argument('--divide','-d', type=int, help='divide the PDF into specified number of parts. Default:1')
default_max_pages = 300

#divide default 3 for Test↑
parser.add_argument('--attempts', type=int, default=3,
                    help='the maximum number of attempts. Default: 3')
parser.add_argument('--no-delete', action='store_true',help='Do not delete files')
args = parser.parse_args()

powerlog.set_log_level(args)

# Load environment variables from diAPI.env
load_dotenv('diAPI.env')
endpoint = os.getenv('DI_API_ENDPOINT')
credential = AzureKeyCredential(os.getenv('DI_API_KEY'))
document_intelligence_client = DocumentIntelligenceClient(endpoint, credential)

#Define input/output folder
optpdf_folder = './OptimizedPDF'
json_folder = './DIjson'
divpdf_folder = './TEMP/divPDF'
divjson_folder = "./TEMP/json"

# Create divpdf_folder if it doesn't exist
if not os.path.exists(divpdf_folder):
    os.makedirs(divpdf_folder)
os.makedirs(divjson_folder, exist_ok=True)

# Get list of PDF files in the optpdf_folder
pdf_files = [f for f in os.listdir(optpdf_folder) if f.endswith('.pdf')]

# Function to divide PDF into specified number of pages
def divide_pdf_by_pages(file_path, div_pages):
    error_print(f"Dividing {file_path} into {div_pages} page blocks")
    debug_print(f"Divide value: {divide_value} Divide pages: {div_pages}")
    reader = PdfReader(file_path)
    total_pages = len(reader.pages)
    if total_pages < div_pages:
        error_print(f"Warning: {file_path} has only {total_pages} pages, which is less than the specified division size of {div_pages}")
    for page in range(0, total_pages, div_pages):
        debug_print(f"Processing pages {page} to {min(page + div_pages, total_pages)}")
        writer = PdfWriter()
        for sub_page in range(page, min(page + div_pages, total_pages)):
            writer.add_page(reader.pages[sub_page])
        yield writer

# Function to divide PDF into specified number of parts
def divide_pdf(file_path, divide_value):
    error_print(f"Dividing {file_path} into {divide_value} parts")
    debug_print(f"Divide value: {divide_value} Divide pages: {div_pages}")
    reader = PdfReader(file_path)
    total_pages = len(reader.pages)
    pages_per_part = math.ceil(total_pages / divide_value)
    for page in range(0, total_pages, pages_per_part):
        debug_print(f"Processing pages {page} to {min(page + pages_per_part, total_pages)}")
        writer = PdfWriter()
        for sub_page in range(page, min(page + pages_per_part, total_pages)):
            writer.add_page(reader.pages[sub_page])
        yield writer

# Function to process PDF and send to Document Intelligence API and receive OCR results and save to JSON file
def process_pdf(file_path, client, output_folder):
    try:
        # Send PDF to Document Intelligence for OCR
        with open(file_path, "rb") as f:
            base64_encoded_pdf = base64.b64encode(f.read()).decode()
            poller = client.begin_analyze_document("prebuilt-read", {"base64Source": base64_encoded_pdf})
        verbose_print(f"Sent {file_path} to Document Intelligence for OCR. Waiting for results...")

        # Wait for OCR results
        analyze_result = poller.result()
        verbose_print(f"OCR completed for {file_path}")

        # Create dictionary from OCR results and add status
        result_dict = analyze_result.as_dict()
        result_dict["status"] = poller.status()

        # Save OCR results to JSON file
        json_file_path = os.path.join(output_folder, f"{os.path.basename(file_path)}.json")
        if os.path.exists(json_file_path):
            warning_print(f"Warning: {json_file_path} already exists and will be overwritten.")
            os.remove(json_file_path)
        with open(json_file_path, "w", encoding="utf-8") as json_file:
            json.dump(result_dict, json_file, ensure_ascii=False, indent=4)
        
        info_print(f"OCR result saved to {json_file_path}")
    except Exception as e:
        print(f"Failed to process {file_path}: {e}")

# Function to merge OCR results from divided PDFs
def merge_ocr_results(base_name, divjson_folder, json_folder):
    merged_results = {
        "apiVersion": "",
        "modelId": "",
        "stringIndexType": "",
        "content": [],
        "pages": [],
        "paragraphs": [],  
        "styles": [], 
        "contentFormat":[],
        "status": []
    }

    part_files = sorted([f for f in os.listdir(divjson_folder) if f.startswith(base_name) and f.endswith('.json')])

    if len(part_files) == 1:
        os.rename(os.path.join(divjson_folder, part_files[0]), os.path.join(json_folder, base_name + '.pdf.json'))
    else:
        page_offset = 0
        word_offset = 0
        line_offset = 0
        previous_page_offset_length = 0
        paragraph_offset = 0
        failed_parts = []
        last_style_offset_length = 0
        paragraph_page_offset = 0
        last_page_number = 0
        for filename in part_files:
            with open(os.path.join(divjson_folder, filename), 'r', encoding='utf-8') as f:
                data = json.load(f)
                # Check if the OCR process failed for _part
                if data["status"] != "succeeded":
                    failed_parts.append(filename)
                if not merged_results["apiVersion"]:
                    merged_results["apiVersion"] = data["apiVersion"]
                if not merged_results["modelId"]:
                    merged_results["modelId"] = data["modelId"]
                if not merged_results["stringIndexType"]:
                    merged_results["stringIndexType"] = data["stringIndexType"]
                merged_results["content"].append(data["content"])
                for page in data["pages"]:
                    page["pageNumber"] = len(merged_results["pages"]) + 1
                    if page["spans"]:
                        if page["pageNumber"] > 1 and merged_results["pages"]:
                            previous_page = merged_results["pages"][-1]
                            if previous_page["spans"]:
                                previous_page_offset_length = previous_page["spans"][-1]["offset"] + previous_page["spans"][-1]["length"]
                        else:
                          page["spans"][0]["offset"] = 0
                    for page_span in page["spans"]:
                        page_span["offset"] = page_offset
                        page_offset += page_span["length"] + 1
                    for word in page["words"]:
                        word_offset = previous_page_offset_length+1
                        word_span = word["span"]
                        word_span["offset"] = word_offset
                        word_offset += word_span["length"] + 1
                    for line in page["lines"]:
                        line_offset = previous_page_offset_length + 1
                        for linespan in line["spans"]:
                            linespan["offset"] = line_offset
                            line_offset += linespan["length"] + 1
                    merged_results["pages"].append(page)
                # Add paragraphs and styles
                for paragraph in data["paragraphs"]:
                    last_page_number = 0
                    for bounding_region in paragraph["boundingRegions"]:
                        if last_page_number < bounding_region["pageNumber"]:
                            last_page_number = bounding_region["pageNumber"]
                            bounding_region["pageNumber"] = paragraph_page_offset + last_page_number
                    for paragraph_span in paragraph["spans"]:
                        paragraph_span["offset"] = paragraph_offset
                        paragraph_offset += paragraph_span["length"] + 1
                    merged_results["paragraphs"].append(paragraph)
                paragraph_page_offset += last_page_number
                for style in data["styles"]:
                    # Update the offset for each span in the style, starting from the second part
                    if part_files.index(filename) > 0:
                        for span in style["spans"]:
                            span["offset"] += last_style_offset_length + 1

                    # Check if a style with the same confidence already exists
                    existing_style = next((s for s in merged_results["styles"] if s["confidence"] == style["confidence"]), None)
                    if existing_style is not None:
                        # If it exists, append the spans
                        existing_style["spans"].extend(style["spans"])
                    else:
                        # If it doesn't exist, append the style
                        merged_results["styles"].append(style)

                # Update last_style_offset_length with the last span's offset and length in the last style
                if merged_results["pages"]:
                    last_style_page = merged_results["pages"][-1]
                    if last_style_page["spans"]:
                        last_style_span = last_style_page["spans"][-1]
                        last_style_offset_length = last_style_span["offset"] + last_style_span["length"]

        merged_results["content"] = "\n".join(merged_results["content"])

    return merged_results

def divide_and_process_pdf(pdf_file_path, divide_value, div_pages,base_name, document_intelligence_client, divpdf_folder, divjson_folder, json_folder):
    if args.divide:
        pdf_parts = list(divide_pdf(pdf_file_path, divide_value))
        debug_print(f"Divide value: {divide_value}, Divide pages: {div_pages} function is divide_pdf")
    elif args.pages:
        pdf_parts = list(divide_pdf_by_pages(pdf_file_path, div_pages))
        debug_print(f"Divide value: {divide_value}, Divide pages: {div_pages} function is divide_pdf_by_pages")
    else:
        pdf_parts = list(divide_pdf(pdf_file_path, divide_value))
        debug_print(f"Divide value: {divide_value}, Divide pages: {div_pages} function is divide_pdf")
    for i, pdf_part in enumerate(pdf_parts, start=1):  # start parameter set to 1
        output_pdf_path = os.path.join(divpdf_folder, f"{base_name}_part{i}.pdf")
        with open(output_pdf_path, "wb") as output_pdf:
            pdf_part.write(output_pdf)
        process_pdf(output_pdf_path, document_intelligence_client, divjson_folder)
    merged_results = merge_ocr_results(base_name, divjson_folder, json_folder)
    if os.path.exists(os.path.join(json_folder, base_name + '.pdf.json')):
        warning_print(f"{base_name}.pdf.json already exists and will be overwritten.")
        os.remove(os.path.join(json_folder, base_name + '.pdf.json'))
    with open(os.path.join(json_folder, base_name + '.pdf.json'), 'w', encoding='utf-8') as f:
        json.dump(merged_results, f, ensure_ascii=False, indent=4)
    verbose_print("Merged OCR results saved to " + variable_str(os.path.join(json_folder, base_name + '.pdf.json')))

    # If not in debug mode, delete part files
    if not args.no_delete:
        part_files = [f for f in os.listdir(divpdf_folder) if f.startswith(base_name + "_part")]
        for part_file in part_files:
            try:
                os.remove(os.path.join(divpdf_folder, part_file))
                warning_print(f"Deleted {part_file} in {divpdf_folder}")
            except Exception as e:
                error_print(f"Failed to delete {part_file} in {divpdf_folder}. Reason: {e}")
        part_files = [f for f in os.listdir(divjson_folder) if f.startswith(base_name + "_part")]
        for part_file in part_files:
            try:
                os.remove(os.path.join(divjson_folder, part_file))
                warning_print(f"Deleted {part_file} in {divjson_folder}")
            except Exception as e:
                error_print(f"Failed to delete {part_file} in {divpdf_folder}. Reason: {e}")


# Process each PDF file
for pdf_file in pdf_files:
    pdf_file_path = os.path.join(optpdf_folder, pdf_file)
    base_name = pdf_file.rsplit('.', 1)[0]
    with open(pdf_file_path, "rb") as file:
        pdf = PdfReader(file)
        total_pages = len(pdf.pages)

    # specify method and numbur of parts to divide, depending on options and page nunbers
    divide_value = 1
    div_pages = default_max_pages
    if args.pages:
        if args.pages >= default_max_pages:
            args.pages = None
    if args.no_divide:
        divide_value = 1
    elif args.divide:
        divide_value = args.divide
    elif args.pages:
        div_pages = args.pages
    else:
        if total_pages <= default_max_pages:
            divide_value = 1
        else:
            if total_pages % default_max_pages == 0:
                divide_value = total_pages // default_max_pages
            else:
                divide_value = total_pages // default_max_pages + 1
    debug_print(f"Divide value: {divide_value}, Divide pages: {div_pages}")
        

    try:
        attempt = 0
        max_attempts = args.attempts
        #If proccesing fails divide into smaller parts and process
        while attempt < max_attempts:
            if divide_value == 1 and not args.pages:
                try:
                    process_pdf(pdf_file_path, document_intelligence_client, json_folder)
                    break
                except Exception as e:
                    error_print(f"Failed to process {pdf_file}: {e}")
                    error_print(f"Attempting to divide {pdf_file} into smaller parts")
                    attempt += 1
                    divide_value += 1
            else:
                try:
                    divide_and_process_pdf(pdf_file_path, divide_value, div_pages, base_name, document_intelligence_client, divpdf_folder, divjson_folder, json_folder)
                    break
                except Exception as e:
                    error_print(f"Failed to process {pdf_file}: {e}")
                    error_print(f"Attempting to divide {pdf_file} into smaller parts")
                    attempt += 1
                    divide_value += 1
    except Exception as e:
        powerlog.debug_print(f"Error processing {pdf_file}: {e}")