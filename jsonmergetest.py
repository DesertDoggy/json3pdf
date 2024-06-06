from dotenv import load_dotenv
import os
from azure.core.credentials import AzureKeyCredential
from azure.ai.documentintelligence import DocumentIntelligenceClient
import json
import powerlog
from powerlog import logger,verbose_print, info_print, error_print, variable_str, debug_print
from PyPDF2 import PdfReader, PdfWriter
import base64
import shutil

# コマンドライン引数を解析する
parser = powerlog.create_parser()
parser.add_argument('-d', '--divide', type=int, help='divide the PDF into specified number of pages')
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

    # Wait for the analysis to complete
    analyze_result = poller.result()

    # Convert the AnalyzeResult object to a dictionary
    result_dict = analyze_result.as_dict()

    # Add other information to the dictionary
    result_dict["status"] = poller.status()

    # Save the dictionary to a JSON file
    json_file_path = os.path.join(output_folder, f"{os.path.basename(file_path)}.json")
    with open(json_file_path, "w", encoding="utf-8") as json_file:
        json.dump(result_dict, json_file, ensure_ascii=False, indent=4)
        
    print(f"JSON file saved to {json_file_path}")

def merge_ocr_results(base_name, divjson_folder, json_folder):
    merged_results = {
        "apiVersion": "",
        "modelId": "",
        "stringIndexType": "",
        "content": [],
        "pages": []
    }

    part_files = sorted([f for f in os.listdir(divjson_folder) if f.startswith(base_name) and f.endswith('.json')])

    if len(part_files) == 1:
        os.rename(os.path.join(divjson_folder, part_files[0]), os.path.join(json_folder, base_name + '.pdf.json'))
    else:
        page_offset = 0
        word_offset = 0
        line_offset = 0
        previous_page_offset_length = 0
        for filename in part_files:
            with open(os.path.join(divjson_folder, filename), 'r', encoding='utf-8') as f:
                data = json.load(f)
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
                    for span in page["spans"]:
                        span["offset"] = page_offset
                        page_offset += span["length"] + 1
                    for word in page["words"]:
                        word_offset = previous_page_offset_length+1
                        wordspan = word["span"]
                        wordspan["offset"] = word_offset
                        word_offset += wordspan["length"] + 1
                    for line in page["lines"]:
                        line_offset = previous_page_offset_length + 1
                        for linespan in line["spans"]:
                            linespan["offset"] = line_offset
                            line_offset += linespan["length"] + 1
                    merged_results["pages"].append(page)

        merged_results["content"] = "\n".join(merged_results["content"])

        if not os.path.exists(json_folder):
            os.makedirs(json_folder)

        with open(os.path.join(json_folder, base_name + '.pdf.json'), 'w', encoding='utf-8') as f:
            json.dump(merged_results, f, ensure_ascii=False, indent=4)

    return merged_results

# Process each PDF file
for pdf_file in pdf_files:
    base_name = pdf_file.rsplit('.', 1)[0]

    try:
        merged_results = merge_ocr_results(base_name, divjson_folder, json_folder)
        print("merge_ocr_results function passed the test.")
    except Exception as e:
        print(f"Error testing merge_ocr_results function: {e}")