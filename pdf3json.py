from dotenv import load_dotenv
import os
from azure.core.credentials import AzureKeyCredential
from azure.ai.documentintelligence import DocumentIntelligenceClient
import json
import powerlog
from powerlog import logger,verbose_print, info_print,warning_print, error_print, variable_str, debug_print
from PyPDF2 import PdfReader, PdfWriter
import base64
import shutil

# コマンドライン引数を解析する
parser = powerlog.create_parser()
group = parser.add_mutually_exclusive_group()
group.add_argument('-d', '--divide', type=int, default=300, help='divide the PDF into specified number of pages. Default:300')
group.add_argument('--no-divide', action='store_true', help='Overrides auto divide of 300 pages and will try to process whole PDF')
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
def divide_pdf(file_path, num_pages):
    error_print(f"Dividing {file_path} into {num_pages} page blocks")
    reader = PdfReader(file_path)
    total_pages = len(reader.pages)
    if total_pages < num_pages:
        error_print(f"Warning: {file_path} has only {total_pages} pages, which is less than the specified division size of {num_pages}")
    for page in range(0, total_pages, num_pages):
        debug_print(f"Processing pages {page} to {min(page + num_pages, total_pages)}")
        writer = PdfWriter()
        for sub_page in range(page, min(page + num_pages, total_pages)):
            writer.add_page(reader.pages[sub_page])
        yield writer

# Function to process PDF and send to Document Intelligence API and receive OCR results and save to JSON file
def process_pdf(file_path, client, output_folder):
    # ここでfile_pathを使用してPDFを送信します
    with open(file_path, "rb") as f:
        base64_encoded_pdf = base64.b64encode(f.read()).decode()
        poller = client.begin_analyze_document("prebuilt-read", {"base64Source": base64_encoded_pdf})
    verbose_print(f"Sent {file_path} to Docunent Intelligence for OCR. Waiting for results...")

    # Wait for the analysis to complete
    analyze_result = poller.result()
    verbose_print(f"OCR completed for {file_path}")

    # Convert the AnalyzeResult object to a dictionary
    result_dict = analyze_result.as_dict()

    # Add other information to the dictionary
    result_dict["status"] = poller.status()

    # Save the dictionary to a JSON file
    json_file_path = os.path.join(output_folder, f"{os.path.basename(file_path)}.json")
    with open(json_file_path, "w", encoding="utf-8") as json_file:
        json.dump(result_dict, json_file, ensure_ascii=False, indent=4)
        
    info_print(f"OCR result saved to {json_file_path}")

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
                    for paragraph_span in paragraph["spans"]:
                        paragraph_span["offset"] = paragraph_offset
                        paragraph_offset += paragraph_span["length"] + 1
                    merged_results["paragraphs"].append(paragraph)
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

        if not os.path.exists(json_folder):
            os.makedirs(json_folder)

        with open(os.path.join(json_folder, base_name + '.pdf.json'), 'w', encoding='utf-8') as f:
            json.dump(merged_results, f, ensure_ascii=False, indent=4)

    return merged_results

def divide_and_process_pdf(pdf_file_path, divide_value, base_name, document_intelligence_client, divpdf_folder, divjson_folder, json_folder):
    pdf_parts = list(divide_pdf(pdf_file_path, divide_value))
    for i, pdf_part in enumerate(pdf_parts, start=1):  # start parameter set to 1
        output_pdf_path = os.path.join(divpdf_folder, f"{base_name}_part{i}.pdf")
        with open(output_pdf_path, "wb") as output_pdf:
            pdf_part.write(output_pdf)
        process_pdf(output_pdf_path, document_intelligence_client, divjson_folder)
    merged_results = merge_ocr_results(base_name, divjson_folder, json_folder)
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

    try:
        with open(pdf_file_path, "rb") as file:
            pdf = PdfReader(file)
            total_pages = len(pdf.pages)
        # Divide PDF into specified number of pages if specified, if total_pages is less than specified, process the whole PDF
        divide_pages = args.divide
        # If total_pages is less than divide_pages or --no-divide is specified, process the whole PDF
        if total_pages <= divide_pages or args.no_divide:
            attempt = 0
            max_attempts = args.attempts
            #If processing full size PDF fails, divide into smaller parts and process
            while attempt < max_attempts:
                # Try to process the full size PDF
                if attempt == 0:
                    try:
                        process_pdf(pdf_file_path, document_intelligence_client, json_folder)
                        break
                    except Exception as e:
                        error_print(f"Error processing full size {pdf_file}: {e}")
                        error_print(f"Attempting to divide {pdf_file} into smaller parts")
                        attempt += 1
                        # If total_pages is more than 300, divide into 2 parts
                        if total_pages > args.divide:
                            if total_pages % args.divide == 0:
                                divide_value = total_pages // args.divide
                            else:
                                divide_value = total_pages // args.divide + 1
                        else:
                            divide_value = 2
                # If processing full size PDF fails, divide into smaller parts and process
                if attempt > 0:
                    try:
                        divide_and_process_pdf(pdf_file_path, divide_value, base_name, document_intelligence_client, divpdf_folder, divjson_folder, json_folder)
                        break
                    except Exception as e:
                        error_print(f"Error processing {pdf_file} in parts: {e}")
                        error_print(f"Attempting to divide {pdf_file} into smaller parts")
                        attempt += 1
                        divide_value += 1                        

        else:
            # If total_pages is more than 300*n, divide into (n+1) parts
            if total_pages > divide_pages:
                if total_pages % divide_pages == 0:
                    divide_value = total_pages // divide_pages
                else:
                    divide_value = total_pages // divide_pages + 1
            attempt = 0
            max_attempts = args.attempts
            #If proccesing fails divide into smaller parts and process
            while attempt < max_attempts:
                try:
                    divide_and_process_pdf(pdf_file_path, divide_value, base_name, document_intelligence_client, divpdf_folder, divjson_folder, json_folder)
                    break
                except Exception as e:
                    error_print(f"Error processing {pdf_file} in parts: {e}")
                    error_print(f"Attempting to divide {pdf_file} into smaller parts")
                    attempt += 1
                    divide_value += 1
    except Exception as e:
        powerlog.debug_print(f"Error processing {pdf_file}: {e}")