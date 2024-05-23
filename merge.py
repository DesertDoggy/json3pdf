from PyPDF2 import PdfReader, PdfWriter
import os

# フォルダのパスを設定
text_layer_folder = "C:\\Data\\Documents\\OCR\\after"
existing_pdf_folder = "C:\\Data\\Documents\\OCR\\before"
output_folder = "C:\\Data\\Documents\\OCR\\merged"

# 透明テキストレイヤーPDFのファイル名を取得
text_pdf_files = [f for f in os.listdir(text_layer_folder) if f.endswith('_TextOnly.pdf')]

# 各透明テキストレイヤーPDFに対して処理を実行
for text_pdf_file in text_pdf_files:
    base_name = text_pdf_file.replace('_TextOnly.pdf', '')
    existing_pdf_file = base_name + '.pdf'
    output_pdf_file = base_name + '_merged.pdf'

    text_pdf_path = os.path.join(text_layer_folder, text_pdf_file)
    existing_pdf_path = os.path.join(existing_pdf_folder, existing_pdf_file)
    output_pdf_path = os.path.join(output_folder, output_pdf_file)

    if os.path.exists(text_pdf_path) and os.path.exists(existing_pdf_path):
        text_pdf = PdfReader(open(text_pdf_path, 'rb'))
        existing_pdf = PdfReader(open(existing_pdf_path, 'rb'))
        output_pdf = PdfWriter()

        for page_number in range(len(existing_pdf.pages)):
            existing_page = existing_pdf.pages[page_number]
            text_page = text_pdf.pages[page_number]

            # ページサイズを確認し、必要に応じて調整
            if existing_page.mediabox != text_page.mediabox:
                text_page.mediabox = existing_page.mediabox

            existing_page.merge_page(text_page)
            output_pdf.add_page(existing_page)

        with open(output_pdf_path, 'wb') as f:
            output_pdf.write(f)

        print(f'{output_pdf_file} の合成が完了しました。')
    else:
        print(f'{text_pdf_file} または {existing_pdf_file} が見つかりません。')

print('全てのPDFファイルの合成が完了しました。')
