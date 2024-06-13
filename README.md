# json3pdf
## CAUTION!: these scripts are in currently in Alpha stage. It is also my first script, hence it might have unexpected critical errors, or more like many bugs are expected. It is recommended to keep the original image files, just in case.
## Disclaimer: I am not a professional dev. Bug reports will be appreciated, but fixes are not guaranteed and replies can be slow.

- [English](./README.md)
- [日本語](./README_ja.md)

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
pdf3json: dotenv,azure.core.credentials,azure.ai.documentintelligence
json3pdf: reportlab
mergejs: PyPDF2

## How to use (CLI options for scripts are described in following section)
### Preperation. 
1. prepare images to convert to PDF. 
These scripts are intended for performing OCR on scanned books for archive purposes. If DPI is unable to read from file, it will default to 600 dpi, which is not the traditional default 72 or 96 dpi. Also, when converting to jpeg 2000 might result in loss of dpi information from files due to the jpeg 2000 format. I have implemented code to  write dpi information to the xml, but at the moment you might need to specify dpi value from command line for each script if scan dpi is other than 600.
2. Place images in subfolder of ./OriginalImages. At the moment script will scan only the immediate subfolder.
3. PDF pages will be inserted in alphabetical order of file name. For compatability for planned script, it is recommended to rename file and subfolder to the specific format, but at the moment it should work if it's in alphabetical order.(or not)
        ./OriginalImages/TitleOfBook/TitleOfBook_cover,TitleOfBook_p0000,TitleOfBook_p0001,......,TitleOfBook_z0001,TitleOfBook_z0002...)
        _cover: cover of book, _p0000:inner cover or index, _p0001～:pages, _z0001～: unnumbered charts etc.
4. Add path of openjp2.dll to system so glymur can access it.*2,*3

### img2j2k.py (convert image files to PDF compatible Jpeg2000)
1. Put scanned images in subdirectory of ./OriginalImages. (./OriginalImages/Title/img.png...etc)
   !!Image file names are format sensitive in the next step(j2k2pdf). It is recommended to rename to required format before converting image files!!
2. Run script. Images will be converted to lossless Jpeg2000 for archive purposes, and optimized Jpeg2000 to be used for OCR.
3. Converted images will be placed in output folder. (./TEMP/lossless,./TEMP/optimized)
   
   by default it will convert the same images to both Lossless Jpeg2000 for Archival purposes and Lossy optimized Jpeg2000 to upload and perform OCR with Document Intelligence. *1
   Note that optimization will not resize the pixel resolution since higher dpi is recommended for OCR.
   If dpi is not specified with option, the script wil read the dpi from image file and round it to 72 or 50*n≧150, this is due to some scanner setting it in (probably) float value. If it cannot read from file it will default to 600.

### j2k2pdf.py (losslessly insert PDF compatible image files int PDF.)
(put PDF compatible images in input folder. input folder is same as output folder for img2j2k.py. if not exist create.)
1. Run script. PDF will automatically be created in output folder. Each subdirectory will be output as a independent PDF file.
   Output folder is ./OriginalPDF for lossless archival PDF and ./OptimizedPDF for optimized PDF to use for OCR.

  !!Image file names are format sensitive. Rename to required format mentioned above before performing this step. This is to combine the scanned images in page order.
  Script will automatically read and set dpi as above, but at the moment dpi of jpeg2000 seems tricky and unable to apply, so it is reccomended to set an option if not 600.
  Script will also automatically estimate page size from resolution and dpi if page size is not set with option. At the moment compatible page size formats are A3 to A6,B4 to B7,Tabloid amd Blanket. Custom sizes are planned but not implemented yet.

### pdf3json (OCR)
1. Use the diAPI.env.template.txt and create a credentials file (.env) to use the Docunent Intelligence*1 API for OCR.
   Only Document Intelligence*1 Studio Read is supported. It might work with other modes, but there is no plan to implement it.
   Document Intelligence*1 Max file size limit is 500MB, but large files seem to fail frequently. If you run into this problem, try spliting the PDF file into multiple files. This will sometimes solve the problem.


### OCR alternative
1. Upload optimized PDF to Microsoft Document Intelligence *1 Studio Read.
2. Run analysis and download created json file.
3. Place json file in ./DIjson folder. DO NOT change the name of the json file. Not even deleting the .pdf of .pdf.json. At the moment it is required for detecting it as OCR file of PDF. Also keep both the lossless and optimized PDF file names the same.
   Only Document Intelligence*1 Studio Read is supported. It might work with other modes, but there is no plan to implement it.
   Document Intelligence*1 Max file size limit is 500MB, but large files seem to fail frequently. If you run into this problem, try spliting the PDF file into multiple files. This will sometimes solve the problem.

### json3pdf.py (create black text PDF file to use for adjustment for final file)

1. Run script. This will output a _TextOnly PDF file from the json to output folder (./OCRtextPDF), with approximately the same layout as the original. 

You might need to adjust the font size with options. You can also use other ttf fonts if you place them in .data/fonts and set options. As a default NotoSansJP-Regular is bundled.*4

### mergejs.py (merge black text PDF file with optimized PDF file for adjustment)
1. Run script. This will output a _merged PDF file with the optimized PDF with a text layer merged from the _TextOnly PDF.
2. If the layout is off, adjust it with options and merge again until it is right.

Layout adjustment is set in points (1inch = 72pt, 1cm = 28.3465pt ) by options. 
Due to the fact that some PDF files are created without dpi in account (as is those from jpeg2000) and pagesize and result in a huge page size causing the dimensions vastly differing from regular size PDF and causing the fonts and layout to break or become missing th script will detect the pagesize and if the page size is over the threshold with a 10% margin, it will take into account the dpi when adjusting the layout by points.
Vertical text is supported partially and can be used for clear text, or horizontal languages (ex.English). 

### json3pdf (create clear text PDF file to use for searchable text layer)
1. Run script with --clear,-c option. This will output a _ClearText PDF file to output folder (./OCRclearPDF).
   Use same (adjusted) options as the draft.

### mergejs (merge clear text PDF file with original PDF file for final output.)
1. Run script with --clear,-c option. This will output a _OCR searchable clear text PDF file to output folder (./OCRfinalPDF)
   Use same (adjusted) options as the draft.

*1. Microsoft,Azure,Document Intelligence　are trademarks of the Microsoft group of companies.
*2 openjpeg is licensed under the BSD license.
*3 dll is included in package (./data/dll). You can also download the latest version from the official site or repository.
*4 Open Font License

##Options
### common options
--log-level, -log, -debug: sets log level.:  --log-level DEBUG,VERBOSE,INFO,WARNING:default INFO
### img2j2k
--dpi: sets dpi for output image metadata.: --dpi integer: positive (--dpi 300)used set dpi if not read from image file. negative (--dpi -300) forces set dpi. 0 (--dpi 0) uses read dpi from file without rounding to typical integer value.: default dpi for unknown read dpi is 600.
--quick, -q: skips bitperfect lossless conversion check.
--check: sets bitperfect lossless conversion check type.:--check slow, opens the final output file with pillow and numpy. --check fast, opens the temporary (converted output file before renaming to final file name.) file with glymur and compares with original file.:Default --check slow.
      This is due to a workaround to convert files including Japanese (and possibly CJK and other language fonts) which is incompatible with glymur (or openjpeg)
--temp,-t: sets temporary file work folder.: This is experimental. Since the script renames the temporary file as final output it is recommended to keep default or set as same drive as output.
--lossless,-l: performs only lossless conversion
--optimize,-o: performs only optimize conversion. lossless check will be skipped.

### j2k2pdf
--simple-check,-s: performes a simple check if PDF was created successfully. Default:1, 0=off)

### json3pdf
--pages,-p:divide the PDF into specified number of pages. Default will divide if PDF is over 300 pages.
--divide,-d:help='divide the PDF into specified number of parts. Default:1
--no-divide,help='Overrides auto divide maximum of 300 pages and will try to process whole PDF
--attempts,the maximum number of attempts. Default: 3
--no-delete will keep the divided PDF files and non-merged json files in case the merge fails.

### pdf3json
--size,-s: adjusts the font size. Default 100 (%)
--font-threshold,-t:--individual:Keeps the same font size for items unless the change exceeds the threshold. units is %. --individual ignores threshold (at the moment threshold will default to none)
--hfont,-hf:Sets horizontal font.default: NotoSansJP-Regular.ttf *4
--vfont,-vf':Sets vertical font.default:NotoSansJP-Regular.ttf *4
--dpi,-d: default:600
--page,-p, Set page size of the PDF. Default:A5 if cannot read page size from JSON
--layout:Method to draw text. word, line, or paragraph. Default: line(line is recommended for serchable text PDF. word is recommended if for some reason you need vertical visible text (ex:copy layout for Japanese). at the monent paragraph is unusable).
#--area,-ar:area threshold for counting lines in a paragraph. Experimental!!!default: 80
#--similarity,-st:Set the similarity threshold for adding lines to a paragraph. Experimental!!!Default:0.1
#--adjust, -ad:adjust the layout of lines and paragraphs. Experimental!!!Default:False
#--coordinate, -ct:Set the coordinate threshold for coordinate adjustment for lines and paragraph.Experimental!!! Default:80 #Probably no need. Optimized base code.
--clear,-c:output clear text PDF
--search,-se,search page limit and ignore character number for layout "line" main text direction detection. Default:(50,2)

### mergejs
--left',-l,--right,-r,--up,-u,--down,-d:Number of points to move and adjust text layer (1 inch = 72 pt, 1 cm = 28.35 pt)
--dpi:Specify the DPI of the document.default:600
--threshold,-t:Specify the threshold page size incase dpi is not correct.Default:Blanket(Newspaper size)
--clear,-c:Merge clear text PDF to Original PDF.
--process-pages,-p, type=int, default=50, help=Number of pages to process at once.