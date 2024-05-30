import fitz  # PyMuPDF
from PIL import Image
from pathlib import Path
import io
import logging
import verbose_logging  # カスタムログレベルVERBOSEとログの設定を追加するスクリプトをインポート

# 入力と出力のフォルダを設定
pdf_folder = Path('./OriginalPDF')
optpdf_folder = Path('./OptimizedPDF')

# 出力フォルダが存在しない場合は作成
optpdf_folder.mkdir(exist_ok=True)

# PDFファイルを処理
for pdf_path in pdf_folder.glob('*.pdf'):
    doc = fitz.open(pdf_path)
    optimized_doc = fitz.open()  # 最適化されたPDFを格納するための新しいドキュメント
    page_count = doc.page_count  # 総ページ数

    # 各ページを処理
    for page_number, page in enumerate(doc, start=1):
        # 進行状況を表示
        print(f'ページ {page_number}/{page_count} を処理中... (Processing page {page_number}/{page_count}) of {pdf_path.name}')

        # ページ内の画像を取得し、新しい画像で置き換える
        for img_index, img in enumerate(page.get_images(full=True)):
            xref = img[0]
            base_image = doc.extract_image(xref)
            image_bytes = base_image["image"]

            # PILを使用して画像を開き、JPEG2000形式で低画質に変換
            image = Image.open(io.BytesIO(image_bytes))
            with io.BytesIO() as output:
                image.save(output, format='JPEG2000', quality_mode='dB', quality_layers=[-80])
                new_image_bytes = output.getvalue()

            # 新しい画像を作成して、元の画像を置き換える
            rect = page.get_image_rects(img[0])[0]  # xrefを引数として渡す
            page.insert_image(rect, stream=new_image_bytes)

        # 最適化されたページを新しいドキュメントに追加
        optimized_doc.insert_pdf(doc, from_page=page.number, to_page=page.number)

    # 最適化されたPDFを保存
    optimized_pdf_path = optpdf_folder / pdf_path.name
    optimized_doc.save(optimized_pdf_path)
    optimized_doc.close()
    doc.close()

# 最終的なメッセージを表示
print("PDFの最適化が完了しました。 (PDF optimization is complete.)")
