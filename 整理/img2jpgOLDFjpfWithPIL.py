import argparse
from PIL import Image
from PIL import ImageChops
import os
import shutil  # shutilモジュールをインポート

def nearest_preferred_dpi(dpi_value, default_dpi):
    if dpi_value < 72:
        return 72
    elif dpi_value < 150:
        return 72 if abs(dpi_value - 72) < abs(dpi_value - 150) else 150
    else:
        return round(dpi_value / 50) * 50 if default_dpi else dpi_value

# コマンドライン引数を解析する
parser = argparse.ArgumentParser(description='Convert images to JPF format with specified DPI.')
parser.add_argument('--dpi', type=int, nargs='+', metavar='DPI', help='The DPI to set for the converted images, single or double value.')
parser.add_argument('--quick', '-q', action='store_true', help='Skip bit-perfect lossless conversion check.')
args = parser.parse_args()

# 入力フォルダと出力フォルダのパス
input_folder = './OriginalImages'
output_folder = './TEMP'

# 出力フォルダが存在しない場合は作成
if not os.path.exists(output_folder):
    os.makedirs(output_folder)

# 変換をスキップする拡張子リスト
skip_conversion_extensions = (
    '.j2c', '.j2k', '.jpc', '.jp2', '.jpf', '.jpg', '.jpeg', 
    '.jpm', '.jpg2', '.jpx', '.mj2'
)

# Pillowがサポートする画像形式の拡張子リスト
# アルファベット順に並べ、同じ画像フォーマットは連続するようにする
supported_extensions = (
    '.bmp', '.gif', '.j2c', '.j2k', '.jpc', '.jp2', '.jpf', '.jpg', '.jpeg', 
    '.jpm', '.jpg2', '.jpx', '.mj2', '.png', '.psd', '.tif', '.tiff', '.webp'
)

# 入力フォルダ内の全サブディレクトリを走査
for subdir, _, files in os.walk(input_folder):
    # サブディレクトリ構造を出力フォルダに反映
    subfolder_path = subdir.replace(input_folder, output_folder)
    if not os.path.exists(subfolder_path):
        os.makedirs(subfolder_path)
    
    # ファイル名順にソート
    files.sort()
    for file in files:
        # Pillowがサポートする画像形式のファイルのみを処理
        if file.lower().endswith(supported_extensions):
            # 元のファイルパス
            original_path = os.path.join(subdir, file)
            # 出力ファイルパス
            output_path = os.path.join(subfolder_path, os.path.splitext(file)[0] + '.jpf')

                        # 変換をスキップするファイルかどうかをチェック
            if file.lower().endswith(skip_conversion_extensions):
                # ファイルを出力フォルダにコピー
                shutil.copy2(original_path, output_path)
                # コンソールにメッセージを表示
                print(f'PDF compatible file. Skipped conversion and copied {file} to {output_folder}.')
                print(f'PDF対応形式。変換をスキップし、{file}を{output_folder}にコピーしました。')
            else:
            
                # 画像を開いてJPF形式で保存
                with Image.open(original_path) as img:
                    # DPIを読み取り、最も近い72または50の倍数の整数値に調整
                    original_dpi = img.info.get('dpi', (600,600))
                    # コマンドライン引数でDPIが指定されているかチェック
                    if args.dpi:
                        # シングルDPIが指定された場合はダブルに変換
                        target_dpi = tuple(args.dpi * 2) if len(args.dpi) == 1 else tuple(args.dpi)
                    else:
                        target_dpi = (nearest_preferred_dpi(original_dpi[0], True), nearest_preferred_dpi(original_dpi[1], True))
                    img.save(output_path, 'JPEG2000', quality_mode='lossless', dpi=target_dpi)
                
                # 変換後の画像を開いてフォーマットと画質を確認
                with Image.open(output_path) as converted_img:
                    # 画像フォーマットと画質を取得
                    format = converted_img.format
                    mode = converted_img.mode
                    # ファイル名の後に変換元と変換後のDPI情報を表示
                    print(f'Converted {original_path} as {format} with {mode} mode. Original DPI: {original_dpi}. Target DPI: {target_dpi}.')

                # ビットパーフェクトなロスレス変換を確認する部分をスキップするオプションが指定されているかチェック
                if not args.quick:
                    with Image.open(original_path) as original_img, Image.open(output_path) as converted_img:
                        # 画像が同じサイズであることを確認
                        if original_img.size != converted_img.size:
                            print(f'The image sizes are different: {file}')
                        else:
                            # 画像間の差分を取得
                            diff = ImageChops.difference(original_img, converted_img)
                            # 差分があるかどうかを確認
                            if diff.getbbox() is None:
                                print(f'Bit-perfect lossless conversion confirmed: {file}')
                                print(f'ビットパーフェクトなロスレス変換が確認されました: {file}')
                            else:
                                print(f'The converted image differs from the original: {file}')
                                print(f'変換後の画像が元の画像と異なります: {file}')

# quickオプションが指定された場合のメッセージ
if args.quick:
    print('Conversion completed. The bit-perfect lossless conversion check was skipped due to the --quick option.')
    print('変換が完了しました。--quick オプションが指定されたため、ビットパーフェクトなロスレス変換の確認は行われませんでした。')
