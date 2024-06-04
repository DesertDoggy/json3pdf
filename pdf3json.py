from dotenv import load_dotenv
import os
from azure.core.credentials import AzureKeyCredential
from azure.ai.documentintelligence import DocumentIntelligenceClient

# Load environment variables from diAPI.env
load_dotenv('diAPI.env')
endpoint = os.getenv('DI_API_ENDPOINT')
credential = AzureKeyCredential(os.getenv('DI_API_KEY'))
document_intelligence_client = DocumentIntelligenceClient(endpoint, credential)

#Define input/output folder
optpdf_folder = Path('./OptimizedPDF')
json_folder = './DIjson'