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

#Define input/output folder
optpdf_folder = './OptimizedPDF'
json_folder = './DIjson'
divpdf_folder = './TEMP/divPDF'
divjson_folder = "./TEMP/json"


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
                    for page_span in page["spans"]:
                        page_span["offset"] += page_offset
                    merged_results["pages"].append(page)
                if data["pages"]:
                    page_offset += data["pages"][-1]["spans"][-1]["offset"] + data["pages"][-1]["spans"][-1]["length"] + 1

        merged_results["content"] = "\n".join(merged_results["content"])

        if not os.path.exists(json_folder):
            os.makedirs(json_folder)

        with open(os.path.join(json_folder, base_name + '.pdf.json'), 'w', encoding='utf-8') as f:
            json.dump(merged_results, f, ensure_ascii=False, indent=4)

    return merged_results

# Process each PDF file
for pdf_file in pdf_files:
    pdf_file_path = os.path.join(optpdf_folder, pdf_file)
    base_name = pdf_file.rsplit('.', 1)[0]

    try:
        with open(pdf_file_path, "rb") as file:
            pdf = PdfReader(file)
            total_pages = len(pdf.pages)
        # Divide PDF into specified number of pages if specified, if total_pages is less than specified, process the whole PDF
        if args.divide and total_pages > args.divide:
            pdf_parts = list(divide_pdf(pdf_file_path, args.divide))
            for i, pdf_part in enumerate(pdf_parts, start=1):  # start parameter set to 1
                output_pdf_path = os.path.join(divpdf_folder, f"{base_name}_part{i}.pdf")
                with open(output_pdf_path, "wb") as output_pdf:
                    pdf_part.write(output_pdf)
                process_pdf(output_pdf_path, document_intelligence_client, divjson_folder)
            merged_results = merge_ocr_results(base_name, divjson_folder, json_folder)
            with open(os.path.join(json_folder, base_name + '.pdf.json'), 'w', encoding='utf-8') as f:
                json.dump(merged_results, f, ensure_ascii=False, indent=4)

        else:
            process_pdf(pdf_file_path, document_intelligence_client, json_folder)
    except Exception as e:
        powerlog.debug_print(f"Error processing {pdf_file}: {e}")