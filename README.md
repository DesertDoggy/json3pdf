# json2pdf
Python scripts for importing Microsoft Azure document intelligence OCR json into original PDF files as clear text to create a searchable PDF file
PDF Microsoft Azure Document Intelligence を用いてOCRしてえられたjsonファイルの内容をオリジナルPDFに透明テキストとして書き戻すためのスクリプト群です。 

Dependencies,前提条件
python environmetn + reportlab,PyPDF
reportlab,PyPDFをインストールしたpython実行環境

Required files 必要なファイル
Pre OCR PDF file, JSON file created from PDF file using Document Intelligence.(DO NOT change json file name. Use as is downloaded.)
Test is only done in 600dpi files for now.
OCRをかける元のPDFファイル, Document IntelligenceによるOCR結果のjsonファイル(ファイル名は変えないこと!ダウンロードした"hoge.pdf.json"のまま)
テストは600dpiで施行。他のファイルサイズも多分大丈夫だけど余裕があったらテストします。もしくは報告よろ
DIのアップロードサイズに上限があるけどdpiあればjpeg最低画質でもかなり正確っぽいので最適化するか分割はさんで対応を。



使い方(現時点で。余裕あったら統合・パッケージ化したい)
スクリプト群