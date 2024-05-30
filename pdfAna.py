import fitz  # PyMuPDF
import os
import logging
import verbose_logging  # カスタムログレベルVERBOSEとログの設定を追加するスクリプトをインポート

def analyze_pdf_images(pdf_path):
    # PDFファイルを開く
    pdf = fitz.open(pdf_path)
    image_info_list = []

    # 各ページについて画像情報を抽出
    for page_num in range(len(pdf)):
        page = pdf[page_num]
        image_list = page.get_images(full=True)

        for img_index, img in enumerate(image_list, start=1):
            xref = img[0]
            base_image = pdf.extract_image(xref)
            image_info = {
                'ページ': page_num + 1,
                '画像インデックス': img_index,
                '幅': base_image['width'],
                '高さ': base_image['height'],
                '画像フォーマット': base_image['ext'],
                '圧縮タイプ': img[2]
            }
            image_info_list.append(image_info)

    pdf.close()
    return image_info_list

def main():
    output_folder = './OriginalPDF'  # PDFファイルが保存されているフォルダ
    pdf_files = [f for f in os.listdir(output_folder) if f.endswith('.pdf')]

    for pdf_file in pdf_files:
        pdf_path = os.path.join(output_folder, pdf_file)
        image_info_list = analyze_pdf_images(pdf_path)

        # 画像情報を出力
        for image_info in image_info_list:
            print(f"PDFファイル: {pdf_file}")
            print(f" ページ: {image_info['ページ']}")
            print(f" 画像インデックス: {image_info['画像インデックス']}")
            print(f" 幅: {image_info['幅']}ピクセル")
            print(f" 高さ: {image_info['高さ']}ピクセル")
            print(f" 画像フォーマット: {image_info['画像フォーマット']}")
            print(f" 圧縮タイプ: {image_info['圧縮タイプ']}")
            print('-----------------------------')

if __name__ == '__main__':
    main()
