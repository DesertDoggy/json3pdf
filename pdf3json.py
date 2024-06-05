from dotenv import load_dotenv
import os
from azure.core.credentials import AzureKeyCredential
from azure.ai.documentintelligence import DocumentIntelligenceClient
import json
import powerlog
from powerlog import logger,verbose_print, info_print, error_print, variable_str, debug_print
from PyPDF2 import PdfReader, PdfWriter
import base64

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

# Create divpdf_folder if it doesn't exist
if not os.path.exists(divpdf_folder):
    os.makedirs(divpdf_folder)

# Get list of PDF files in the optpdf_folder
pdf_files = [f for f in os.listdir(optpdf_folder) if f.endswith('.pdf')]

def divide_pdf(file_path, num_pages):
    error_print(f"Dividing {file_path} into {num_pages} pages")
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

for pdf_file in pdf_files:
    pdf_file_path = os.path.join(optpdf_folder, pdf_file)
    
    try:
        if args.divide:
            pdf_parts = list(divide_pdf(pdf_file_path, args.divide))
            for i, pdf_part in enumerate(pdf_parts, start=1):  # start parameter set to 1
                output_pdf_path = os.path.join(divpdf_folder, f"{pdf_file.rsplit('.', 1)[0]}_part{i}.pdf")
                with open(output_pdf_path, "wb") as output_pdf:
                    pdf_part.write(output_pdf)
                # ここでoutput_pdf_pathを使用してPDFを送信します
                with open(output_pdf_path, "rb") as f:
                    base64_encoded_pdf = base64.b64encode(f.read()).decode()
                    poller = document_intelligence_client.begin_analyze_document("prebuilt-read", {"base64Source": base64_encoded_pdf})
        else:
            # ここでpdf_file_pathを使用してPDFを送信します
            with open(pdf_file_path, "rb") as f:
                base64_encoded_pdf = base64.b64encode(f.read()).decode()
                poller = document_intelligence_client.begin_analyze_document("prebuilt-read", {"base64Source": base64_encoded_pdf})

        # Wait for the analysis to complete
        analyze_result = poller.result()

        # Convert the AnalyzeResult object to a dictionary
        result_dict = analyze_result.as_dict()

        # Add other information to the dictionary
        result_dict["status"] = poller.status()

        # Save the dictionary to a JSON file
        json_file_path = os.path.join(json_folder, f"{pdf_file}.json")
        with open(json_file_path, "w", encoding="utf-8") as json_file:
            json.dump(result_dict, json_file, ensure_ascii=False, indent=4)
            
        print(f"JSON file saved to {json_file_path}")
    except Exception as e:
        powerlog.debug_print(f"Error processing {pdf_file}: {e}")