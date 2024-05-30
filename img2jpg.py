import argparse
from PIL import Image
from PIL import ImageChops
import os
import shutil
import logging
import verbose_logging  # カスタムログレベルVERBOSEとログの設定を追加するスクリプトをインポート

# コマンドライン引数を解析する
parser = argparse.ArgumentParser(description='Convert images to JP2 format and create optimized images for OCR.')
parser.add_argument('--quick', '-q', action='store_true', help='Skip bit-perfect lossless conversion check.')
args = parser.parse_args()

# 入力フォルダと出力フォルダのパス
input_folder = './OriginalImages'
lossless_folder = './TEMP/lossless'  
optimized_folder = './TEMP/optimized'  

# 出力フォルダが存在しない場合は作成
if not os.path.exists(lossless_folder):
    os.makedirs(lossless_folder)
if not os.path.exists(optimized_folder):
    os.makedirs(optimized_folder)

# 変換をスキップする拡張子リスト
skip_conversion_extensions = (
    '.j2c', '.j2k', '.jpc', '.jp2', '.jpf', '.jpg', '.jpeg', 
    '.jpm', '.jpg2', '.jpx', '.mj2'
)

# Pillowがサポートする画像形式の拡張子リスト
supported_extensions = (
    '.bmp', '.gif', '.j2c', '.j2k', '.jpc', '.jp2', '.jpf', '.jpg', '.jpeg', 
    '.jpm', '.jpg2', '.jpx', '.mj2', '.png', '.psd', '.tif', '.tiff', '.webp'
)

# 変換カウンター
lossless_count = 0
optimized_count = 0
total_images = 0

# 入力フォルダ内の全サブディレクトリを走査
for subdir, _, files in os.walk(input_folder):
    # サブディレクトリ構造を出力フォルダに反映
    subfolder_path_lossless = subdir.replace(input_folder, lossless_folder)
    subfolder_path_optimized = subdir.replace(input_folder, optimized_folder)
    if not os.path.exists(subfolder_path_lossless):
        os.makedirs(subfolder_path_lossless)
    if not os.path.exists(subfolder_path_optimized):
        os.makedirs(subfolder_path_optimized)
    
    # ファイル名順にソート
    files.sort()
    for file in files:
        # Pillowがサポートする画像形式のファイルのみを処理
        if file.lower().endswith(supported_extensions):
            total_images += 1
            # 元のファイルパス
            original_path = os.path.join(subdir, file)
            # 出力ファイルパス
            output_path_lossless = os.path.join(subfolder_path_lossless, os.path.splitext(file)[0] + '.jp2')
            output_path_optimized = os.path.join(subfolder_path_optimized, os.path.splitext(file)[0] + '.jp2')

            # 変換をスキップするファイルかどうかをチェック
            if file.lower().endswith(skip_conversion_extensions):
                # ファイルを出力フォルダにコピー
                shutil.copy2(original_path, output_path_lossless)
                print(f'PDF compatible file. Skipped conversion and copied {file} to {lossless_folder}.')
            else:
                # 画像を開いてJP2形式で保存
                with Image.open(original_path) as img:
                    img.save(output_path_lossless, 'JPEG2000', quality_mode='lossless')
                    lossless_count += 1
                    print(f'Lossless conversion completed for {file}. ({lossless_count}/{total_images})')
                    # 最適化画像の生成
                    img.save(output_path_optimized, 'JPEG2000', quality_mode='lossy', quality_layers=[20])
                    optimized_count += 1
                    print(f'Optimized image created for {file}. ({optimized_count}/{total_images})')

                # ビットパーフェクトなロスレス変換を確認する部分をスキップするオプションが指定されているかチェック
                if not args.quick:
                    with Image.open(original_path) as original_img, Image.open(output_path_lossless) as converted_img:
                        # 画像が同じサイズであることを確認
                        if original_img.size != converted_img.size:
                            print(f'The image sizes are different: {file}')
                        else:
                            # 画像間の差分を取得
                            diff = ImageChops.difference(original_img, converted_img)
                            # 差分があるかどうかを確認
                            if diff.getbbox() is None:
                                print(f'Bit-perfect lossless conversion confirmed for {file}.')
                            else:
                                print(f'The converted image differs from the original: {file}')
            # 次の画像の処理に移る前に行を空ける
            print()

# quickオプションが指定された場合のメッセージ
if args.quick:
    print('Conversion completed. The bit-perfect lossless conversion check was skipped due to the --quick option.')
