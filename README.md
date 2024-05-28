# json2pdf
Python scripts for importing Microsoft Azure document intelligence OCR json into original PDF files as clear text to create a searchable PDF file
 

Dependencies,前提条件
python environmetn + reportlab,PyPDF


Required files 必要なファイル
Pre OCR PDF file, JSON file created from PDF file using Document Intelligence.(DO NOT change json file name. Use as is downloaded.). TTF fonts if other than default is preffered.
Test is only done in 600dpi files for now.





概要
PDF Microsoft Azure Document Intelligence を用いてOCRしてえられたjsonファイルの内容をオリジナルPDFに透明テキストとして書き戻すためのスクリプト群です。

前提条件
reportlab,PyPDFをインストールしたpython実行環境

必要なファイル
OCRをかける元のPDFファイル
Document IntelligenceによるOCR結果のjsonファイル(ファイル名は変えないこと!ダウンロードした"hoge.pdf.json"のまま)
TTFフォント。デフォルト以外を指定したい場合。

注意事項
テストは600dpiで施行。他のファイルサイズも多分大丈夫だけど余裕があったらテストします。もしくは報告よろ
DIのアップロードサイズに上限があるけどdpiあればjpeg最低画質でもかなり正確っぽいので最適化するか分割はさんで対応を。
作者の本業はコンピュータサイエンスとは縁もゆかりもないので、バグ報告・機能追加要望は感謝しますが、対応する能力・時間があるとは限らないので対応する確率は5%未満(気が向いたらともいう)



使い方(現時点で。余裕あったら統合・パッケージ化したい)
1.スクリプト群直下のbeforeフォルダにPDFとjsonを突っ込む。data/fontsフォルダに必要なフォントを突っ込む。
2.OCR.pyをダブルクリックもしくはCLIから使用。afterフォルダにhoge_TextOnly.pdf生成。オプションでフォントサイズ・種類を指定可能。
3.mergeAdjust.pyでmergedフォルダにオリジナルに黒テキストが挿入されるのでフォントの大きさ・重なり位置を確認。
(重なりはmerge～のオプションで調整可能)(見出しなど個別のサイズ調整は現時点では非対応。端によるけど大きくはずれないので本文のテキストでの調整前提)
4.前回と同じオプションでそれぞれOCRclear.pyで透明テキストpdf生成、mergeAdjustClear.pyでオリジナルに透明テキスト挿入完了。
(DI用にPDF最適化した場合は4.でbeforeのPDFを最適化前に差し替えて)