import os
import argparse
from PIL import Image
import img2pdf

# argparseを使用してCLIオプションを処理
parser = argparse.ArgumentParser(description='画像ファイルをPDFに結合します。')
# '--dpi'オプションを省略可能にし、デフォルト値をNoneに設定
parser.add_argument('--dpi', '-d', type=str, default=None,
                    help='画像のDPIを設定します。fを付けると強制的にこのDPIを使用します。')
args = parser.parse_args()

# 強制DPIフラグとDPI値を取得
# DPIが指定されていない場合はNoneを保持
force_dpi = args.dpi.endswith('f') if args.dpi else False
dpi_value = float(args.dpi[:-1]) if force_dpi else (float(args.dpi) if args.dpi else None)

# 入力フォルダと出力フォルダのパスを設定
working_folder = './TEMP'
output_folder = './OriginalPDF'

# 入力フォルダ内の全サブディレクトリを走査
for subdir, dirs, files in os.walk(working_folder):
    # サブディレクトリ内の画像ファイルのみをフィルタリング
    image_files = [os.path.join(subdir, file) for file in files if file.lower().endswith(('.png', '.jpg', '.jpeg', '.gif', '.jp2', '.jpf', '.jpx', '.j2k', '.j2c', '.jpc'))]
    # 画像ファイルが存在する場合のみ処理
    if image_files:
        # ファイル名でソート
        image_files.sort()
        # 出力PDFのファイル名をサブディレクトリ名に設定
        pdf_filename = os.path.basename(subdir) + '.pdf'
        pdf_path = os.path.join(output_folder, pdf_filename)
        
        # 画像からDPIを読み取り、指定されたルールに従ってDPIを設定
        output_dpi = None
        if not force_dpi:
            try:
                with Image.open(image_files[0]) as img:
                    # 画像からDPIを読み取り、最も近い50の倍数に調整
                    x_dpi, y_dpi = img.info['dpi']
                   avg_dpi = (x_dpi + y_dpi) / 2
                   if avg_dpi < 72:
                        output_dpi = 72
                    else
                        output_dpi = round(avg_dpi / 50) * 50
            except KeyError:
                # DPI情報がない場合は指定されたDPIを使用
                output_dpi = dpi_value
        else:
            # 強制DPIを使用
            output_dpi = dpi_value
        
         画像をPDFに結合して出力
        with open(pdf_path, "wb") as f:
            f.write(img2pdf.convert(image_files, dpi=(output_dpi, output_dpi)))

print('PDFファイルの結合が完了しました。')
