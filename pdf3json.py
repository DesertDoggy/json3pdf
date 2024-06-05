import base64
from dotenv import load_dotenv
import os
from azure.core.credentials import AzureKeyCredential
from azure.ai.documentintelligence import DocumentIntelligenceClient
import json
import powerlog

# コマンドライン引数を解析する
parser = powerlog.create_parser()
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

# Get list of PDF files in the optpdf_folder
pdf_files = [f for f in os.listdir(optpdf_folder) if f.endswith('.pdf')]

for pdf_file in pdf_files:
    pdf_file_path = os.path.join(optpdf_folder, pdf_file)
    
    try:
        # Open the PDF file and send it for analysis
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
        debug_print(f"Error processing {pdf_file}: {e}")