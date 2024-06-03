# json3pdf         CAUTION! Disclaimer: these scripts are in currently in Alpha stage. It is also my first script, hence it might have unexpected critical errors, or more like many bugs are expected. It is recommended to keep the original image files, just in case.

## Description
Just a bunch of scripts for scanning books to PDF & adding clear text from OCR done by Microsoft Azure Document Intelligence.*1

img2j2k was written to 
convert png, tif, bmp files to lossless jpeg2000 for arhcival purposes because 
1.My scanner cannot convert to Lossless version of Jpeg2000. 
2.Other lossless formats are larger or PDF uncompatible. 
3.The "not going to mention PDF software" was slow and crashing. 
Convert to an optimized version of the same image because 1. Document Intelligense*1 only handles files up to 500MB. 2. Higher dpi is recommended for OCR purposes.
j2k2pdf was written to batch convert the images to PDF for that purpose, which mostly are features of img2pdf

So if you don"t care about degradation, or file size, able to scan as lossless Jpeg 2000, or the "not going to mention PDF software" is usable in your environment etc....,you do not need the pre OCR scripts, or you can just use img2pdf.
If you satisfied with regular OCR or other AI OCR you do not need the post OCR scripts.

## Dependencies

Python3 environment
openjpeg (openjp2.dll). Add file location to system path. *2,*3

needed pip install (per script)
img2j2k: PIL (pillow), numpy, glymur, lxml, colorama
j2k2pdf: img2pdf, PIL (pillow), PyPDF2, colorama
json3pdfB/C: reportlab
mergejsB/C: pypdf

## How to use (CLI options for scripts are described in following section)
### Preperation. 
1. prepare images to convert to PDF. 
These scripts are intended for performing OCR on scanned books for archive purposes. If DPI is unable to read from file, it will default to 600 dpi, which is not the traditional default 72 or 96 dpi. Also, when converting to jpeg 2000 might result in loss of dpi information from files due to the jpeg 2000 format. I have implemented code to  write dpi information to the xml, but at the moment you might need to specify dpi value from command line for each script if scan dpi is other than 600.
2. Place images in subfolder of ./OriginalImages. At the moment script will scan only the immediate subfolder.
3. PDF pages will be inserted in alphabetical order of file name. For compatability for planned script, it is recommended to rename file and subfolder to the specific format, but at the moment it should work if it's in alphabetical order.
        ./OriginalImages/TitleOfBook/TitleOfBook_cover,TitleOfBook_p0000,TitleOfBook_p0001,......,TitleOfBook_z0001,TitleOfBook_z0002...)
        _cover: cover of book, _p0000:inner cover or index, _p0001～:pages, _z0001～: unnumbered charts etc.
4. Add path of openjp2.dll to system so glymur can access it.*2,*3

### img2j2k.py (convert image files to PDF compatible Jpeg2000)
1. Put scanned images in subdirectory of ./OriginalImages. (./OriginalImages/Title/img.png...etc)
   !!Image file names are case sensitive in the next step(j2k2pdf). It is recommended to rename to required format before converting image files!!
2. Run script. Images will be converted to lossless Jpeg2000 for archive purposes, and optimized Jpeg2000 to be used for OCR.
3. Converted images will be placed in output folder. (./TEMP/lossless,./TEMP/optimized)
   
   by default it will convert the same images to both Lossless Jpeg2000 for Archival purposes and Lossy optimized Jpeg2000 to upload and perform OCR with Document Intelligence. *1
   Note that optimization will not resize the pixel resolution since higher dpi is recommended for OCR.
   If dpi is not specified with option, the script wil read the dpi from image file and round it to 72 or 50*n≧150, this is due to some scanner setting it in (probably) float value. If it cannot read from file it will default to 600.

### j2k2pdf.py (losslessly insert PDF compatible image files int PDF.)
(put PDF compatible images in input folder. input folder is same as output folder for img2j2k.py. if not exist create.)
1. Run script. Images will automatically created in output folder. Each subdirectory will be output as a independent PDF file.
   Output folder is ./OriginalPDF for lossless archival PDF and ./OptimizedPDF for optimized PDF to use for OCR.

  !!Image file names are case sensitivive. Rename to required format mentioned above before performing this step. This is to combine the scanned images in page order.
  Script will automatically read and set dpi as above, but at the moment dpi of jpeg2000 seems tricky and unable to apply, so it is reccomended to set an option if not 600.
  Script will also automatically estimate page size from resolution and dpi if page size is not set with option. At the moment compatible page size formats are A3 to A6,B4 to B7,Tabloid amd Blanket. Custom sizes are planned but not implemented yet.

### OCR
1. Upload optimized PDF to Microsoft Document Intelligence *1 Studio Read.
2. Run analysis and download created json file.
3. Place json file in ./DIjson folder. DO NOT change the name of the json file. Not even deleting the .pdf of .pdf.json. At the moment it is required for detecting it as OCR file of PDF. Also keep both the lossless and optimized PDF file names the same.

### json3pdfB.py (create black text PDF file to use for adjustment for final file)

1. Run script. This will output a _TextOnly PDF file from the json to output folder (./OCRtextPDF), with approximately the same layout as the original. 

You might need to adjust the font size with options. You can also use other ttf fonts if you place them in .data/fonts and set options. As a default NotoSansJP-Regular is bundled.
At the moment different fonts and sizes for different block is not supported. I might work on it later, but since it is intended to make scanned PDF searchable and adjusting to the main text is enough for such use, the priority is low.

### mergejsB.py (merge black text PDF file with optimized PDF file for adjustment)
1. Run script. This will output a _merged PDF file with the optimized PDF with a text layer merged from the _TextOnly PDF.
2. If the layout is off, adjust it with options and merge again until it is right.

Layout adjustment is set in points (1inch = 72pt, 1cm = 28.3465pt ) by options. 
Due to the fact that some PDF files are created without dpi in account (as is those from jpeg2000) and pagesize and result in a huge page size causing the dimensions vastly differing from regular size PDF and causing the fonts and layout to break or become missing th script will detect the pagesize and if the page size is over the threshold with a 10% margin, it will take into account the dpi when adjusting the layout by points.
At the moment vertical text layout is not supported, (adds as horizontal text. ).

### json3pdfC (create clear text PDF file to use for searchable text layer)
1. Run script. This will output a _ClearText PDF file to output folder (./OCRclearPDF).
   Use same (adjusted) options as json3pdfB.

### mergejsC (merge clear text PDF file with original PDF file for final output.)
1. Run script. This will output a _OCR searchable clear text PDF file to output folder (./OCRfinalPDF)
   Use same (adjusted) options as mergejsB.

*1. Microsoft,Azure,Document Intelligence　are trademarks of the Microsoft group of companies.
*2 openjpeg is licensed under the BSD license.
*3 dll is included in package (./data/dll). You can also download the latest version from the official site or repository.

##Options
### common options

