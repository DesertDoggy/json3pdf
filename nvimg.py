import numpy as np
from nvimage import Codec

# 画像データの読み込み（ここではランダムなデータを使用）
img = np.random.randint(0, 256, (1024, 1024, 3), dtype=np.uint8)

# nvImageCodecのインスタンスを作成
codec = Codec()

# 画像データをJPEG2000形式にエンコード
jp2_data = codec.encode(img, 'jp2')

# エンコードしたデータをファイルに書き込み
with open('output.jp2', 'wb') as f:
    f.write(jp2_data)