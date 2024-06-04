import base64
from dotenv import load_dotenv
import os
from azure.core.credentials import AzureKeyCredential
from azure.ai.documentintelligence import DocumentIntelligenceClient
import json

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
    
    # Open the PDF file and send it for analysis
    with open(pdf_file_path, "rb") as f:
        base64_encoded_pdf = base64.b64encode(f.read()).decode()
        poller = document_intelligence_client.begin_analyze_document("prebuilt-read", {"base64Source": base64_encoded_pdf})
            
    # Wait for the analysis to complete
    document_intelligence_result = poller.result()

    # Save the JSON file to the json_folder
    json_file_path = os.path.join(json_folder, f"{pdf_file}.json")
    with open(json_file_path, "w", encoding="utf-8") as json_file:
        for page in document_intelligence_result.pages:
            for line in page.lines:
                json_file.write(line.content + "\n")
                print(line.content)


