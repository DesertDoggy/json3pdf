from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.colors import Color
import os
import json

# Yu Gothicフォントのパスを設定
# 通常はWindowsのフォントディレクトリにあります
yu_gothic_path = 'C:\\Windows\\Fonts\\YuGothM.ttc'

# フォントを登録
pdfmetrics.registerFont(TTFont('YuGothic', yu_gothic_path))

# 入力フォルダと出力フォルダのパスを設定
input_folder = "C:\\Data\\Documents\\OCR\\before"
output_folder = "C:\\Data\\Documents\\OCR\\after"

# 入力フォルダ内の全てのJSONファイルを取得
json_files = [f for f in os.listdir(input_folder) if f.endswith('.pdf.json')]

for json_file in json_files:
    # OCR結果のJSONファイル名を設定
    ocr_json_path = os.path.join(input_folder, json_file)

    # JSONファイルが存在する場合のみ処理を実行
    if os.path.exists(ocr_json_path):
        with open(ocr_json_path, 'r', encoding='utf-8') as f:
            ocr_data = json.load(f)

        # 新しいPDFファイル名を設定（'.pdf' を削除してから '_ClearText.pdf' を追加）
        base_filename = os.path.splitext(json_file)[0]
        base_filename = base_filename.replace('.pdf', '')  # '.pdf' を削除
        new_pdf_filename = base_filename + '_ClearText.pdf'
        new_pdf_path = os.path.join(output_folder, new_pdf_filename)

        # ReportLabのキャンバスを作成
        c = canvas.Canvas(new_pdf_path, pagesize=letter)

        # 透明色を定義（赤、緑、青、アルファ）
        transparent_color = Color(0, 0, 0, alpha=0)

        # JSONファイルからページ情報を取得し、テキストを書き込む
        for page in ocr_data['analyzeResult']['pages']:
            page_width = page['width'] * 72  # インチからポイントへの変換
            page_height = page['height'] * 72
            c.setPageSize((page_width, page_height))

            # フォントを設定
            c.setFont('YuGothic', 8)

            for word_info in page['words']:
                text = word_info['content']
                # OCR結果のポリゴンから座標を取得し、PDFの座標系に変換
                x = word_info['polygon'][0] * 72
                y = page_height - (word_info['polygon'][1] * 72)
                # テキストの色を透明に設定
                c.setFillColor(transparent_color)
                c.drawString(x, y, text)

            # 次のページに移動
            c.showPage()

        # PDFファイルを保存
        c.save()

print('全てのPDFファイルの処理が完了しました。')
