# Rename.py: Batch renaming of files

Rename.py makes renaming many files at once easy. Just define what should be changed and how. No need to study regular expressions or similar. 
Rename.py also supports to move selected files to another directory. Moreover, you can also rename folders with this program.

The general structure of a command is as follows:
```
rename.py SELECT-OPTIONS COMMAND COMMAND-ARGUMENTS FILES
```
SELECT-OPTIONS: Define what to change (which parts of a file name).
COMMAND COMMAND-ARGUMENTS: Define how to change (e.g. add a text).
FILES: Define the files that should be renamed. If missing, all files in the current directory are changed.

Rename.py will never overwrite other files. If a destination file already exists, this file is simply skipped.

If you can't use Rename.py to rename files as you want, feel free to create an issue. 


## Install

1. Install Python3 as follows in Ubuntu/Debian Linux:

```
sudo apt install python3.6
```

2. Use pip to install dependencies:
```
pip3 install mutagen
```
This step is optional and only needed if you want to use metadata (e.g. ID3 tags in MP3 files) to rename files.

3. Download Rename.py and set execute permmissions:
```
curl -LJO https://raw.githubusercontent.com/byte-cook/rename/main/rename.py
curl -LJO https://raw.githubusercontent.com/byte-cook/rename/main/textparser.py
chmod +x rename.py 
```

## Example usage

Change extension (selected by "-e") to lower case for all files in current directory (option "-v" for verbose output):
```
rename.py -ve lowercase
Image.JPG -> Image.jpg
```

Add prefix "my_" for all files:
```
rename.py add "my_"
image-01.jpg -> my_image-01.jpg
```

Cut first three characters:
```
rename.py cut 3
01-image.jpg -> image.jpg
```

Use the "test" command to show what part of the file name is selected:
```
rename.py --index-to 4 test
        10        20
123456789|123456789|
image-01.jpg         : imag
image-02.jpg         : imag
README.md            : READ
```

Replace all underscores by spaces:
```
rename.py --text "_" replace " "
IMG_2011#very_long_text.ext -> IMG 2011#very long text.ext
```

Add numbering in the beginning:
```
rename.py number -a #
a file.ext -> 1#a file.ext
second file.ext -> 2#second file.ext
```

Add numbering at the end with width 2:
```
rename.py -nE number -w 2
a file.ext -> a file01.ext
second file.ext -> second file02.ext
```

Create new directories by date of last change and move file there:
```
rename.py -v replace "|m|/|f|"
file1.ext -> 2023-03-12/file1.ext
file2.ext -> 2023-03-12/file2.ext
file3.ext -> 2023-04-12/file3.ext
```

Get list of all (build-in) placeholders:
```
rename.py test -p myfile.ext
File name   : |f|     myfile.ext
Base name   : |b|     myfile
Extension   : |e|     ext
...
```

Remove by text range:
```
rename.py -v --text-from " podc" --text-to "2023" remove
01 podcast-1a2sde 2023-the beginning.ext -> 01-the beginning.ext
02 podcast-1a2sde 2023-the next chapter.ext -> 02-the next chapter.ext
```

Fill leading zeros:
```
rename.py -v --text-from "pter " --char-num fill 0
Chapter 1 the beginning.ext -> Chapter 01-the beginning.ext
Chapter 2 the next chapter.ext -> Chapter 02-the next chapter.ext
...
Chapter 10 chapter 10.ext: File name not changed
Chapter 11 another chapter.ext: File name not changed
```

Swap two parts:
```
rename.py -b swap "-"
19810312-data 1.ext -> data_1-19810312.ext
20180122-info.ext -> info-20180122.ext
```

Copy report6part4.txt to directory french/rapport6partie4.txt along with all similarly named files:
```
rename.py -b --pattern "report|1|part|2|" replace "french/rapport|1|partie|2|" 
report6part4.txt -> french/rapport6partie4.txt
report8part1.txt -> french/rapport8partie1.txt
```

Add space between CamelCase text:
```
rename.py --char-upper add " "
thisFileIsInCamelCase.ext -> this File Is In Camel Case.ext
```

