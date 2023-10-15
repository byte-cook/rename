#!/usr/bin/env python3

import unittest
import os
import sys
import time
import shutil
from datetime import datetime
from unittest import mock
from unittest import TestCase
from pathlib import Path

# import from parent dir
PROJECT_DIR = Path(__file__).absolute().parent
sys.path.insert(0, PROJECT_DIR.parent.as_posix())
import rename
ROOT_PATH = PROJECT_DIR / 'root'
ROOT_DIR = ROOT_PATH.as_posix()

# files
MP3_WITH_ID3_TAGS = 'mp3-with-tags.mp3'
MP3_NO_ARTIST = 'mp3-no-tags.mp3'

# Usage:
# > test_rename.py
# > test_rename.py TestRename.test_clean

class TestRename(unittest.TestCase):
    def setUp(self):
        os.makedirs(ROOT_DIR, exist_ok=True)
        shutil.rmtree(ROOT_DIR)
        os.makedirs(ROOT_DIR, exist_ok=True)

    def test_add(self):
        print('======= test_add ===')
        self._createSingleFiles(ROOT_DIR, 'a.txt', 'b.txt')
        rename.main(['--debug', 'add', '10_', ROOT_DIR])
        self._assertFilesExist(ROOT_DIR, '10_a.txt', '10_b.txt')

    def test_case_lower(self):
        print('======= test_case_lower ===')
        self._createSingleFiles(ROOT_DIR, 'DATA_For_me.txt', 'DAtA_For_you.txt')
        rename.main(['-v', '--index-to', '4', 'lowercase', ROOT_DIR])
        self._assertFilesExist(ROOT_DIR, 'data_For_me.txt', 'data_For_you.txt')
    def test_case_upper(self):
        print('======= test_case_upper ===')
        self._createSingleFiles(ROOT_DIR, 'DATA_For_me.txt', 'DAtA_For_you.txt')
        rename.main(['--debug', '-e', 'uppercase', ROOT_DIR])
        self._assertFilesExist(ROOT_DIR, 'DATA_For_me.TXT', 'DAtA_For_you.TXT')
    def test_case_camel(self):
        print('======= test_case_camel ===')
        self._createSingleFiles(ROOT_DIR, 'you\'re right.txt', 'this is my file.txt')
        rename.main(['--debug', '-b', 'camelcase', ROOT_DIR])
        self._assertFilesExist(ROOT_DIR, 'You\'re Right.txt', 'This Is My File.txt')
    def test_case_sentence(self):
        print('======= test_case_sentence ===')
        self._createSingleFiles(ROOT_DIR, 'you\'re right.txt', 'this is my file.txt')
        rename.main(['--debug', '-b', 'sentencecase', ROOT_DIR])
        self._assertFilesExist(ROOT_DIR, 'You\'re right.txt', 'This is my file.txt')

    def test_cut(self):
        print('======= test_cut ===')
        self._createSingleFiles(ROOT_DIR, '05-you\'re right.txt', '06-this is my file.txt', 'a.txt')
        rename.main(['--debug', '-b', 'cut', '3', ROOT_DIR])
        self._assertFilesExist(ROOT_DIR, 'you\'re right.txt', 'this is my file.txt', '.txt')
    def test_cut_end(self):
        print('======= test_cut_end ===')
        self._createSingleFiles(ROOT_DIR, 'you\'re right_AB.txt', 'this is my file_CD.txt', 'a.txt')
        rename.main(['--debug', '-b', 'cut', '-e', '3', ROOT_DIR])
        self._assertFilesExist(ROOT_DIR, 'you\'re right.txt', 'this is my file.txt', '.txt')

    def test_clean(self):
        print('======= test_clean ===')
        shutil.rmtree(ROOT_DIR)

    def test_dir(self):
        print('======= test_dir ===')
        self._createSingleFiles(ROOT_DIR, 'a.txt', 'this is my file.txt')
        rename.main(['--debug', '--index', '10', 'dir', 'new dir', ROOT_DIR])
        self._assertFilesExist(ROOT_DIR, 'a.txt')
        self._assertFilesNotExist(ROOT_DIR, 'this is my file.txt')
        newDir = str(Path(ROOT_DIR, 'new dir'))
        self._assertFilesExist(newDir, 'this is my file.txt')
    def test_dir_selected(self):
        print('======= test_dir_selected ===')
        self._createSingleFiles(ROOT_DIR, 'IMG_2020.jpg', 'IMG_2020-2.jpg', 'IMG_2022.jpg')
        rename.main(['--debug', '-b', '--index-from', '5', '--index-to', '8', 'dir', '|s|', ROOT_DIR])
        self._assertFilesNotExist(ROOT_DIR, 'IMG_2020.jpg', 'IMG_2022.jpg')
        _2020Dir = str(Path(ROOT_DIR, '2020'))
        self._assertFilesExist(_2020Dir, 'IMG_2020.jpg', 'IMG_2020-2.jpg')
        _2022Dir = str(Path(ROOT_DIR, '2022'))
        self._assertFilesExist(_2022Dir, 'IMG_2022.jpg')

    def test_file_nonexist(self):
        print('======= test_file_nonexist ===')
        with self.assertRaises(SystemExit) as cm:
            rename.main(['--debug', 'test', 'file-does-not-exist.ext'])
        self.assertEqual(cm.exception.code, 1)

    def test_file_exclude(self):
        print('======= test_file_exclude ===')
        self._createSingleFiles(ROOT_DIR, 'podcast 1 title.mp3', 'podcast 2 title.mp3', 'text.txt', 'image.png')
        rename.main(['--debug', '--exclude', '*.mp3', '--exclude', '*.png', 'add', 'my_', ROOT_DIR])
        self._assertFilesExist(ROOT_DIR, 'podcast 1 title.mp3', 'podcast 2 title.mp3', 'my_text.txt', 'image.png')
    def test_file_exclude_include(self):
        print('======= test_file_exclude_include ===')
        self._createSingleFiles(ROOT_DIR, 'podcast 1 title.mp3', 'podcast 2 title.mp3', 'text.txt', 'image.png')
        rename.main(['--debug', '--exclude', '*.mp3', '--exclude', '*.png', '--include', '*2 title.mp3', 'add', 'my_', ROOT_DIR])
        self._assertFilesExist(ROOT_DIR, 'podcast 1 title.mp3', 'my_podcast 2 title.mp3', 'my_text.txt', 'image.png')
    def test_file_exclude_include_path(self):
        print('======= test_file_exclude_include_path ===')
        f1Dir = str(Path(ROOT_DIR, 'Folder 1'))
        os.makedirs(f1Dir, exist_ok=True)
        self._createSingleFiles(f1Dir, 'track-1.mp3', 'track-2.mp3', 'cover.jpg')
        f2Dir = str(Path(ROOT_DIR, 'Folder 2'))
        os.makedirs(f2Dir, exist_ok=True)
        self._createSingleFiles(f2Dir, 'track-1.mp3', 'track-2.mp3', 'cover.jpg')
        rename.main(['--debug', '-r', '--exclude', '*.mp3', '--include', '*/Folder 2/*2.mp3', 'add', 'my_', ROOT_DIR])
        self._assertFilesExist(f1Dir, 'track-1.mp3', 'track-2.mp3', 'my_cover.jpg')
        self._assertFilesExist(f2Dir, 'track-1.mp3', 'my_track-2.mp3', 'my_cover.jpg')

    def test_fill(self):
        print('======= test_fill ===')
        self._createSingleFiles(ROOT_DIR, 'podcast 1 title.mp3', 'podcast 2 title.mp3', 'podcast 17 title.mp3', 'podcast 120 title.mp3')
        rename.main(['--debug', '--textx-from', 'cast ', '--textx-to', ' title', 'fill', '0', ROOT_DIR])
        self._assertFilesExist(ROOT_DIR, 'podcast 001 title.mp3', 'podcast 002 title.mp3', 'podcast 017 title.mp3', 'podcast 120 title.mp3')
    def test_fill_twotokens(self):
        print('======= test_fill_twotokens ===')
        self._createSingleFiles(ROOT_DIR, 'podcast 1 title 1.mp3', 'podcast 2 title 22.mp3', 'podcast 117 title.mp3')
        rename.main(['--debug', '--char-num', 'fill', '0', ROOT_DIR])
        self._assertFilesExist(ROOT_DIR, 'podcast 001 title 1.mp3', 'podcast 002 title 22.mp3', 'podcast 117 title.mp3')
    def test_fill_width(self):
        print('======= test_fill_width ===')
        self._createSingleFiles(ROOT_DIR, 'podcast 1.mp3')
        rename.main(['--debug', '-b', '--indexr-from', '1', 'fill', '-e', '-w', '3', 'x', ROOT_DIR])
        self._assertFilesExist(ROOT_DIR, 'podcast 1xx.mp3')
    def test_fill_text(self):
        print('======= test_fill_text ===')
        self._createSingleFiles(ROOT_DIR, 'Chapter 1 the beginning.ext', 'Chapter 2 the next chapter.ext', 'Chapter 10 the next chapter.ext')
        rename.main(['--debug', '--text-from', 'pter ', '--char-num', 'fill', '0', ROOT_DIR])
        self._assertFilesExist(ROOT_DIR, 'Chapter 01 the beginning.ext', 'Chapter 02 the next chapter.ext', 'Chapter 10 the next chapter.ext')
        
    def test_keep(self):
        print('======= test_keep ===')
        self._createSingleFiles(ROOT_DIR, 'A123.jpg', 'B1234.jpg', 'C12345.jpg')
        rename.main(['--debug', '-b', 'keep', '5', ROOT_DIR])
        self._assertFilesExist(ROOT_DIR, 'A123.jpg', 'B1234.jpg', 'C1234.jpg')
    def test_keep_end(self):
        print('======= test_keep_end ===')
        self._createSingleFiles(ROOT_DIR, '123A.jpg', '1234B.jpg', '12345C.jpg')
        rename.main(['--debug', '-b', 'keep', '-e', '5', ROOT_DIR])
        self._assertFilesExist(ROOT_DIR, '123A.jpg', '1234B.jpg', '2345C.jpg')
    def test_keep_withpattern(self):
        print('======= test_keep_withpattern ===')
        self._createSingleFiles(ROOT_DIR, 'img_2018-image one.jpg', 'img_20220824-image two.jpg')
        rename.main(['--debug', '--pattern', 'img_|Y:s|-|any|', 'keep', '4', ROOT_DIR])
        self._assertFilesExist(ROOT_DIR, 'img_2018-image one.jpg', 'img_2022-image two.jpg')
    def test_keep_withpattern_end(self):
        print('======= test_keep_withpattern_end ===')
        self._createSingleFiles(ROOT_DIR, 'img_2018-image one.jpg', 'img_08242022-image two.jpg')
        rename.main(['--debug', '--pattern', 'img_|Y:s|-|any|', 'keep', '-e', '4', ROOT_DIR])
        self._assertFilesExist(ROOT_DIR, 'img_2018-image one.jpg', 'img_2022-image two.jpg')

    def test_mkdir(self):
        print('======= test_mkdir ===')
        today = datetime.today().strftime('%Y-%m-%d')
        self._createSingleFiles(ROOT_DIR, 'aa.jpg', 'bb.jpg')
        rename.main(['--debug', 'replace', '|m|/|f|', ROOT_DIR])
        self._assertFilesExist(ROOT_DIR, f'{today}/aa.jpg', f'{today}/bb.jpg')
    def test_mkdir_parent(self):
        print('======= test_mkdir_parent ===')
        subDir = str(Path(ROOT_DIR, 'sub'))
        os.makedirs(subDir, exist_ok=True)
        self._createSingleFiles(subDir, 'aa.jpg', 'bb.jpg')
        rename.main(['--debug', 'replace', '../|f|', subDir])
        self._assertFilesExist(ROOT_DIR, f'aa.jpg', f'bb.jpg')
        self.assertEqual(len(os.listdir(subDir)), 0)
    def test_mkdir_parent_fileexists(self):
        print('======= test_mkdir_parent_fileexists ===')
        subDir = str(Path(ROOT_DIR, 'sub'))
        os.makedirs(subDir, exist_ok=True)
        self._createSingleFiles(subDir, 'aa.txt', 'bb.txt')
        self._createSingleFiles(ROOT_DIR, 'aa.txt')
        with self.assertRaises(SystemExit) as cm:
            rename.main(['--debug', 'replace', '../|f|', subDir])
        self.assertEqual(cm.exception.code, 2)
        self._assertFilesExist(ROOT_DIR, f'bb.txt')
        self._assertFilesExist(subDir, f'aa.txt')
        self.assertEqual(len(os.listdir(subDir)), 1)

    def test_not_overwrite_add(self):
        print('======= test_not_overwrite_add ===')
        self._createSingleFiles(ROOT_DIR, 'a.txt', '#a.txt')
        with self.assertRaises(SystemExit) as cm:
            rename.main(['--debug', 'add', '#', os.path.join(ROOT_DIR, 'a.txt')])
        self.assertEqual(cm.exception.code, 2)
        self._assertFilesExist(ROOT_DIR, 'a.txt', '#a.txt')
        self._assertFilesContent(ROOT_DIR, 'a.txt', 'a.txt')
        self._assertFilesContent(ROOT_DIR, '#a.txt', '#a.txt')
    def test_not_overwrite_remove(self):
        print('======= test_not_overwrite_remove ===')
        self._createSingleFiles(ROOT_DIR, '11a.txt', '12a.txt', '21a.txt', '22a.txt', '77a.txt')
        with self.assertRaises(SystemExit) as cm:
            rename.main(['--debug', '--index', '1', 'remove', ROOT_DIR])
        self.assertEqual(cm.exception.code, 2)
        self._assertFilesExist(ROOT_DIR, '1a.txt', '2a.txt', '21a.txt', '22a.txt', '7a.txt')
    def test_not_overwrite_order(self):
        print('======= test_not_overwrite_order ===')
        self._createSingleFiles(ROOT_DIR, 'a.txt', 'aa.txt', 'aaa.txt')
        rename.main(['--debug', 'add', 'a', ROOT_DIR])
        self._assertFilesExist(ROOT_DIR, 'aa.txt', 'aaa.txt', 'aaaa.txt')
        self._assertFilesContent(ROOT_DIR, 'aa.txt', 'a.txt')
        self._assertFilesContent(ROOT_DIR, 'aaa.txt', 'aa.txt')
        self._assertFilesContent(ROOT_DIR, 'aaaa.txt', 'aaa.txt')
    def test_not_overwrite_numbering(self):
        print('======= test_not_overwrite_numbering ===')
        self._createSingleFiles(ROOT_DIR, '1.txt', '2.txt', '3.txt')
        rename.main(['--debug', '-b', 'number', '--replace', '-s', '2', ROOT_DIR])
        self._assertFilesExist(ROOT_DIR, '2.txt', '3.txt', '4.txt')
        self._assertFilesContent(ROOT_DIR, '2.txt', '1.txt')
        self._assertFilesContent(ROOT_DIR, '3.txt', '2.txt')
        self._assertFilesContent(ROOT_DIR, '4.txt', '3.txt')

    def test_numbering(self):
        print('======= test_numbering ===')
        self._createSingleFiles(ROOT_DIR, 'aa.txt', 'bb.txt')
        rename.main(['--debug', 'number', '-a', '-', ROOT_DIR])
        self._assertFilesExist(ROOT_DIR, '1-aa.txt', '2-bb.txt')
    def test_numbering_at_the_end(self):
        print('======= test_numbering_at_the_end ===')
        self._createSingleFiles(ROOT_DIR, 'aa.txt', 'bb.txt')
        rename.main(['--debug', '-b', 'number', '-w', '2', '-e', '-b', '#', ROOT_DIR])
        self._assertFilesExist(ROOT_DIR, 'aa#01.txt', 'bb#02.txt')
    def test_numbering_twotokens(self):
        print('======= test_numbering_twotokens ===')
        self._createSingleFiles(ROOT_DIR, 'a long file.txt', 'b file.txt')
        rename.main(['--debug', '--text', ' ', 'number', ROOT_DIR])
        self._assertFilesExist(ROOT_DIR, 'a1 long file.txt', 'b2 file.txt')
    def test_numbering_width_autodetect(self):
        print('======= test_numbering_width_autodetect ===')
        self._createFiles(ROOT_DIR, 100, 'track-')
        rename.main(['--debug', '--textx-from', '-', 'fill', '0', ROOT_DIR])
        rename.main(['--debug', 'number', '-a', '#', ROOT_DIR])
        self._assertFilesExist(ROOT_DIR, '001#track-001.txt', '012#track-012.txt', '081#track-081.txt', '100#track-100.txt')
    def test_numbering_width_autodetect_2(self):
        print('======= test_numbering_width_autodetect_2 ===')
        self._createSingleFiles(ROOT_DIR, 'IMG_1.jpg', 'IMG_2.jpg', 'IMG_3.jpg', 'IMG_4.jpg')
        rename.main(['--debug', '-b', 'number', '-b', '2023-', '--replace', '-i', '33', '-s', '2', ROOT_DIR])
        # the calculation of the width must take into account the increment parameter
        self._assertFilesExist(ROOT_DIR, '2023-002.jpg', '2023-035.jpg', '2023-068.jpg', '2023-101.jpg')
    def test_numbering_width_autodetect_3(self):
        print('======= test_numbering_width_autodetect_3 ===')
        self._createSingleFiles(ROOT_DIR, 'IMG_1.jpg', 'IMG_2.jpg', 'IMG_3.jpg')
        rename.main(['--debug', '-b', 'number', '-b', '2023-', '--replace', '--increment', '33', '--start', '35', ROOT_DIR])
        # the calculation of the width must take into account the increment parameter
        self._assertFilesExist(ROOT_DIR, '2023-035.jpg', '2023-068.jpg', '2023-101.jpg')
    def test_numbering_reset(self):
        print('======= test_numbering_reset ===')
        stonesDir = str(Path(ROOT_PATH / 'rolling stones'))
        os.makedirs(stonesDir, exist_ok=True)
        self._createFiles(stonesDir, 13, 'track-')
        rename.main(['--debug', '-b', '--textx-from', 'track-', 'fill', '0', stonesDir])
        whoDir = str(Path(ROOT_DIR, 'the who').absolute())
        os.makedirs(whoDir, exist_ok=True)
        self._createFiles(whoDir, 9, 'track-')
        
        rename.main(['--debug', '-r', 'number', '-a', '#', ROOT_DIR])
        self._assertFilesExist(stonesDir, '01#track-01.txt', '07#track-07.txt', '09#track-09.txt', '13#track-13.txt')
        self._assertFilesExist(whoDir, '01#track-1.txt', '02#track-2.txt', '09#track-9.txt')
    def test_numbering_noreset(self):
        print('======= test_numbering_noreset ===')
        stonesDir = str(Path(ROOT_PATH / 'rolling stones'))
        os.makedirs(stonesDir, exist_ok=True)
        self._createFiles(stonesDir, 13, 'track-')
        rename.main(['--debug', '-b', '--textx-from', 'track-', 'fill', '0', stonesDir])
        whoDir = str(Path(ROOT_DIR, 'the who').absolute())
        os.makedirs(whoDir, exist_ok=True)
        self._createFiles(whoDir, 9, 'track-')
        
        rename.main(['--debug', '-r', 'number', '--no-reset', '-a', '#', ROOT_DIR])
        self._assertFilesExist(stonesDir, '01#track-01.txt', '07#track-07.txt', '09#track-09.txt', '13#track-13.txt')
        self._assertFilesExist(whoDir, '14#track-1.txt', '15#track-2.txt', '22#track-9.txt')
    def test_numbering_replace(self):
        print('======= test_numbering_replace ===')
        self._createSingleFiles(ROOT_DIR, 'IMG_098.jpg', 'IMG_099.jpg')
        rename.main(['--debug', '-b', 'number', '-b', '2023-', '--replace', ROOT_DIR])
        self._assertFilesExist(ROOT_DIR, '2023-1.jpg', '2023-2.jpg')
    def test_numbering_increment(self):
        print('======= test_numbering_increment ===')
        self._createSingleFiles(ROOT_DIR, 'IMG_098.jpg', 'IMG_099.jpg')
        rename.main(['--debug', '-b', 'number', '-b', '2023-', '--replace', '-i', '10', ROOT_DIR])
        # the calculation of the width must take into account the increment parameter
        self._assertFilesExist(ROOT_DIR, '2023-01.jpg', '2023-11.jpg')

    def test_placeholder_audio(self):
        print('======= test_placeholder_audio ===')
        shutil.copy(MP3_WITH_ID3_TAGS, ROOT_DIR)
        rename.main(['--debug', '-b', 'replace', '|no|-|artist| - |album| - |track|', ROOT_DIR])
        self._assertFilesExist(ROOT_DIR, '01-The Artist - The Album - The Track.mp3')
    def test_placeholder_audio_noartist(self):
        print('======= test_placeholder_audio_noartist ===')
        shutil.copy(MP3_NO_ARTIST, ROOT_DIR)
        with self.assertRaises(SystemExit) as cm:
            rename.main(['--debug', '-b', 'replace', '|artist| - |album| - |track|', ROOT_DIR])
        self.assertEqual(cm.exception.code, 1)
        self._assertFilesExist(ROOT_DIR, MP3_NO_ARTIST)
    def test_placeholder_folders(self):
        print('======= test_placeholder_folders ===')
        albumDir = os.path.abspath(os.path.join(ROOT_DIR, 'rolling stones', 'beggars banquet'))
        os.makedirs(albumDir, exist_ok=True)
        
        self._createSingleFiles(albumDir, '01 sympathy.mp3', '02 dear doctor.mp3')
        rename.main(['--debug', '-b', 'replace', '|f-1| - |f0| - |b|', albumDir])
        self._assertFilesExist(albumDir, 'rolling stones - beggars banquet - 01 sympathy.mp3', 'rolling stones - beggars banquet - 02 dear doctor.mp3')
    def test_placeholder_notfound(self):
        print('======= test_placeholder_notfound ===')
        self._createSingleFiles(ROOT_DIR, 'aa.txt')
        with self.assertRaises(SystemExit) as cm:
            rename.main(['add', '|notfound|_', ROOT_DIR])
        self.assertEqual(cm.exception.code, 1)
        self._assertFilesExist(ROOT_DIR, 'aa.txt')
    def test_placeholder_reserved(self):
        print('======= test_placeholder_reserved ===')
        self._createSingleFiles(ROOT_DIR, 'aa.txt')
        with self.assertRaises(SystemExit) as cm:
            rename.main(['--debug', '--pattern', '|m|.txt', 'add', 'NEW_', ROOT_DIR])
        self.assertEqual(cm.exception.code, 1)
        self._assertFilesExist(ROOT_DIR, 'aa.txt')
    def test_placeholder_syntaxerror(self):
        print('======= test_placeholder_syntaxerror ===')
        self._createSingleFiles(ROOT_DIR, 'aa.txt')
        with self.assertRaises(SystemExit) as cm:
            rename.main(['add', '|b||', ROOT_DIR])
        self.assertEqual(cm.exception.code, 1)
        self._assertFilesExist(ROOT_DIR, 'aa.txt')
    def test_placeholder_selected(self):
        print('======= test_placeholder_selected ===')
        self._createSingleFiles(ROOT_DIR, 'a.txt', 'abc.txt')
        rename.main(['-b', 'add', '|s|', ROOT_DIR])
        self._assertFilesExist(ROOT_DIR, 'aa.txt', 'abcabc.txt')

    def test_replace_ext(self):
        print('======= test_replace_ext ===')
        self._createSingleFiles(ROOT_DIR, 'aa.txt', 'bb.txt')
        rename.main(['--debug', '-e', 'replace', 'csv', ROOT_DIR])
        self._assertFilesExist(ROOT_DIR, 'aa.csv', 'bb.csv')

    def test_replace_placeholder(self):
        print('======= test_replace_placeholder ===')
        self._createSingleFiles(ROOT_DIR, 'aa.txt', 'bb.jpg')
        rename.main(['--debug', '-b', 'replace', 'prefix-|b|_|e|', ROOT_DIR])
        self._assertFilesExist(ROOT_DIR, 'prefix-aa_txt.txt', 'prefix-bb_jpg.jpg')

    def test_replace_text(self):
        print('======= test_replace_text ===')
        self._createSingleFiles(ROOT_DIR, 'this_is_a_file.txt', 'another_file.jpg')
        rename.main(['--debug', '--text', '_', 'replace', ' ', ROOT_DIR])
        self._assertFilesExist(ROOT_DIR, 'this is a file.txt', 'another file.jpg')

    def test_remove_ext(self):
        print('======= test_remove_ext ===')
        self._createSingleFiles(ROOT_DIR, 'aa.txt', 'bb.txt')
        rename.main(['--debug', '-e', 'remove', ROOT_DIR])
        if os.name == 'nt':
            self._assertFilesExist(ROOT_DIR, 'aa', 'bb')
        else:
            self._assertFilesExist(ROOT_DIR, 'aa.', 'bb.')

    def test_remove_index(self):
        print('======= test_remove_index ===')
        self._createSingleFiles(ROOT_DIR, '01aa.txt', '02bb.txt')
        rename.main(['--debug', '--index-to', '2', 'remove', ROOT_DIR])
        self._assertFilesExist(ROOT_DIR, 'aa.txt', 'bb.txt')

    def test_select_basename(self):
        print('======= test_select_basename ===')
        self._createSingleFiles(ROOT_DIR, 'another_file.JPG')
        rename.main(['--debug', '-b', 'replace', 'newname', ROOT_DIR])
        self._assertFilesExist(ROOT_DIR, 'newname.JPG')
    def test_select_ext(self):
        print('======= test_select_ext ===')
        self._createSingleFiles(ROOT_DIR, 'this_is_a_file.JPG', 'another_file.JPG')
        rename.main(['--debug', '-e', 'lowercase', ROOT_DIR])
        self._assertFilesExist(ROOT_DIR, 'this_is_a_file.jpg', 'another_file.jpg')
    def test_select_ext_withdot(self):
        print('======= test_select_ext_withdot ===')
        self._createSingleFiles(ROOT_DIR, 'a track.mp3', 'second track.mp3')
        rename.main(['--debug', '-E', 'number', '-b', '-', ROOT_DIR])
        self._assertFilesExist(ROOT_DIR, 'a track-1.mp3', 'second track-2.mp3')
        
    def test_select_dir(self):
        print('======= test_select_dir ===')
        for i in range(7):
            subDir = str(Path(ROOT_DIR, f'sub{i}'))
            os.makedirs(subDir, exist_ok=True)
        rename.main(['--debug', '--dir-only', '-vr', 'number', '-b', 'CD ', ROOT_DIR])
        rename.main(['--debug', '--dir-only', '-r', '--text-from', 'sub', 'remove', ROOT_DIR])
        self._assertFilesExist(ROOT_DIR, 'CD 1', 'CD 2', 'CD 6')
        self._assertFilesNotExist(ROOT_DIR, 'sub1', 'sub2', 'sub6')
    
    def test_select_index(self):
        print('======= test_select_index ===')
        self._createSingleFiles(ROOT_DIR, 'Img_11.png', 'Img_2.png', 'Img_.png', 'ZZZ.png')
        rename.main(['--debug', '-b', '--index', '4', 'replace', '#', ROOT_DIR])
        self._assertFilesExist(ROOT_DIR, 'Img#11.png', 'Img#2.png', 'Img#.png', 'ZZZ.png')
    def test_select_index_illegalvalue(self):
        print('======= test_select_index_illegalvalue ===')
        self._createSingleFiles(ROOT_DIR, 'Img_11.png', 'Img_2.png', 'Img_.png', 'ZZZ.png')
        with self.assertRaises(SystemExit) as cm:
            rename.main(['--debug', '-b', '--index', '0', 'replace', '#', ROOT_DIR])
        self.assertEqual(cm.exception.code, 2)
        self._assertFilesExist(ROOT_DIR, 'Img_11.png', 'Img_2.png', 'Img_.png', 'ZZZ.png')
    def test_select_index_from(self):
        print('======= test_select_index_from ===')
        self._createSingleFiles(ROOT_DIR, 'aaa123.txt', 'bbb123.txt')
        rename.main(['--debug', '-b', '--index-from', '4', 'replace', '_', ROOT_DIR])
        self._assertFilesExist(ROOT_DIR, 'aaa_.txt', 'bbb_.txt')
    def test_select_index_to(self):
        print('======= test_select_index_to ===')
        self._createSingleFiles(ROOT_DIR, '123aaa.txt', '123bbb.txt', 'z.txt')
        rename.main(['--debug', '--index-to', '3', 'replace', '_', ROOT_DIR])
        self._assertFilesExist(ROOT_DIR, '_aaa.txt', '_bbb.txt', '_xt')
    def test_select_index_range(self):
        print('======= test_select_index_range ===')
        self._createSingleFiles(ROOT_DIR, '123aaa456.txt', '123bbb.txt', '1.txt')
        rename.main(['--debug', '-b', '--index-from', '4', '--index-to', '6', 'replace', '_', ROOT_DIR])
        self._assertFilesExist(ROOT_DIR, '123_456.txt', '123_.txt', '1.txt')
    def test_select_index_range_from_eq_to(self):
        print('======= test_select_index_range_from_eq_to ===')
        self._createSingleFiles(ROOT_DIR, '123a456.txt', '123b.txt', '1.txt')
        rename.main(['--debug', '-b', '--index-from', '4', '--index-to', '4', 'replace', '_', ROOT_DIR])
        self._assertFilesExist(ROOT_DIR, '123_456.txt', '123_.txt', '1.txt')
    def test_select_index_range_from_gt_to(self):
        print('======= test_select_index_range_from_gt_to ===')
        self._createSingleFiles(ROOT_DIR, '123aaa456.txt', '123bbb.txt', '1.txt')
        rename.main(['--debug', '-b', '--index-from', '6', '--index-to', '4', 'replace', '_', ROOT_DIR])
        self._assertFilesExist(ROOT_DIR, '123aaa456.txt', '123bbb.txt', '1.txt')
    def test_select_indexr_from(self):
        print('======= test_select_indexr_from ===')
        self._createSingleFiles(ROOT_DIR, 'aaa123.txt', 'bbb123.txt')
        rename.main(['--debug', '-b', '--indexr-from', '4', 'replace', '_', ROOT_DIR])
        self._assertFilesExist(ROOT_DIR, 'aa_.txt', 'bb_.txt')
    def test_select_indexr_to(self):
        print('======= test_select_indexr_to ===')
        self._createSingleFiles(ROOT_DIR, '123aaa.txt', '123bbb.txt', 'z.txt')
        rename.main(['--debug', '-b', '--indexr-to', '3', 'replace', '_', ROOT_DIR])
        self._assertFilesExist(ROOT_DIR, '_aa.txt', '_bb.txt', 'z.txt')
    def test_select_indexr_to_2(self):
        print('======= test_select_indexr_to_2 ===')
        self._createSingleFiles(ROOT_DIR, '123aaa.txt', '123bbb.txt', 'zz.txt')
        rename.main(['--debug', '--indexr-to', '6', 'replace', '_', ROOT_DIR])
        self._assertFilesExist(ROOT_DIR, '_a.txt', '_b.txt', '_z.txt')
    def test_select_indexr_range(self):
        print('======= test_select_indexr_range ===')
        self._createSingleFiles(ROOT_DIR, '123aaa456.txt', '123bbb.txt', '1.txt')
        rename.main(['--debug', '-b', '--indexr-from', '6', '--indexr-to', '4', 'replace', '_', ROOT_DIR])
        self._assertFilesExist(ROOT_DIR, '123_456.txt', '_bbb.txt', '1.txt')
    def test_select_indexr_range_from_gt_to(self):
        print('======= test_select_indexr_range_from_gt_to ===')
        self._createSingleFiles(ROOT_DIR, '123aaa456.txt', '123bbb.txt', '1.txt')
        rename.main(['--debug', '-b', '--indexr-from', '4', '--indexr-to', '6', 'remove', ROOT_DIR])
        self._assertFilesExist(ROOT_DIR, '123aaa456.txt', '123bbb.txt', '1.txt')
    def test_select_index_combindedrange(self):
        print('======= test_select_index_combindedrange ===')
        self._createSingleFiles(ROOT_DIR, 'a123aaa456b.txt', 'c1234XXXXXXXbbbd.txt', '1.txt')
        rename.main(['--debug', '-b', '--index-from', '2', '--indexr-to', '2', 'remove', ROOT_DIR])
        self._assertFilesExist(ROOT_DIR, 'ab.txt', 'cd.txt', '1.txt')
    def test_select_index_illegalcombination(self):
        print('======= test_select_index_illegalcombination ===')
        self._createSingleFiles(ROOT_DIR, 'a123aaa456b.txt', 'c1234XXXXXXXbbbd.txt', '1.txt')
        with self.assertRaises(SystemExit) as cm:
            rename.main(['--debug', '--index', '2', '--index-from', '2', '--indexr-to', '2', 'remove', ROOT_DIR])
        self.assertEqual(cm.exception.code, 1)
        self._assertFilesExist(ROOT_DIR, 'a123aaa456b.txt', 'c1234XXXXXXXbbbd.txt', '1.txt')

    def test_select_text_remove(self):
        print('======= test_select_text_remove ===')
        self._createSingleFiles(ROOT_DIR, 'this_is_a_file.jpg', 'another_file.jpg')
        rename.main(['--debug', '--text', '_', 'remove', ROOT_DIR])
        self._assertFilesExist(ROOT_DIR, 'thisisafile.jpg', 'anotherfile.jpg')
    def test_select_text_illegalvalue(self):
        print('======= test_select_text_illegalvalue ===')
        self._createSingleFiles(ROOT_DIR, 'this_is_a_file.jpg', 'another_file.jpg')
        with self.assertRaises(SystemExit) as cm:
            rename.main(['--debug', '--text', '', 'remove', ROOT_DIR])
        self.assertEqual(cm.exception.code, 2)
        self._assertFilesExist(ROOT_DIR, 'this_is_a_file.jpg', 'another_file.jpg')
    def test_select_text_to(self):
        print('======= test_select_text_to ===')
        self._createSingleFiles(ROOT_DIR, 'IMG_01.jpg', 'IMG_02.jpg', '03.jpg')
        rename.main(['--debug', '-b', '--text-to', 'G_', 'remove', ROOT_DIR])
        self._assertFilesExist(ROOT_DIR, '01.jpg', '02.jpg', '03.jpg')
    def test_select_text_to_excl(self):
        print('======= test_select_text_to_excl ===')
        self._createSingleFiles(ROOT_DIR, 'IMG_#01.jpg', 'IMG_#02.jpg', 'IMG_02.jpg')
        rename.main(['--debug', '-b', '--textx-to', '#', 'remove', ROOT_DIR])
        self._assertFilesExist(ROOT_DIR, '#01.jpg', '#02.jpg', 'IMG_02.jpg')
    def test_select_text_illegalcombination(self):
        print('======= test_select_text_illegalcombination ===')
        self._createSingleFiles(ROOT_DIR, 'IMG_#01.jpg', 'IMG_#02.jpg', 'IMG_02.jpg')
        with self.assertRaises(SystemExit) as cm:
            rename.main(['--debug', '--text', 'IMG', '--textx-to', '#', 'remove', ROOT_DIR])
        self.assertEqual(cm.exception.code, 1)
        self._assertFilesExist(ROOT_DIR, 'IMG_#01.jpg', 'IMG_#02.jpg', 'IMG_02.jpg')

    def test_select_char_num(self):
        print('======= test_select_char_num ===')
        self._createSingleFiles(ROOT_DIR, '1938-11aaa.ext', '1981-2222b.ext')
        rename.main(['--debug', '--index-from', '5', '--char-num', 'remove', ROOT_DIR])
        self._assertFilesExist(ROOT_DIR, '1938-aaa.ext', '1981-b.ext')
    def test_select_char_non_num(self):
        print('======= test_select_char_not_num ===')
        self._createSingleFiles(ROOT_DIR, '1938-11aaa.ext', '1981-2222b.ext')
        rename.main(['--debug', '-b', '--index-from', '6', '--char-non-num', 'remove', ROOT_DIR])
        self._assertFilesExist(ROOT_DIR, '1938-11.ext', '1981-2222.ext')
    def test_select_char_alpha(self):
        print('======= test_select_char_alpha ===')
        self._createSingleFiles(ROOT_DIR, '1938-~1b1~.ext', '1981-22ab++.ext')
        rename.main(['--debug', '-b', '--index-from', '6', '--char-alpha', 'replace', '_', ROOT_DIR])
        self._assertFilesExist(ROOT_DIR, '1938-~1_1~.ext', '1981-22_++.ext')
    def test_select_char_non_alpha(self):
        print('======= test_select_char_not_alpha ===')
        self._createSingleFiles(ROOT_DIR, '1938-~11a~aa.ext', '1981-222+2b.ext')
        rename.main(['--debug', '-b', '--index-from', '6', '--char-non-alpha', 'replace', '_', ROOT_DIR])
        self._assertFilesExist(ROOT_DIR, '1938-_a_aa.ext', '1981-_b.ext')
    def test_select_char_alnum(self):
        print('======= test_select_char_alnum ===')
        self._createSingleFiles(ROOT_DIR, '1938-~11~.ext', '1981-22++.ext')
        rename.main(['--debug', '-b', '--index-from', '6', '--char-alnum', 'remove', ROOT_DIR])
        self._assertFilesExist(ROOT_DIR, '1938-~~.ext', '1981-++.ext')
    def test_select_char_non_alnum(self):
        print('======= test_select_char_not_alnum ===')
        self._createSingleFiles(ROOT_DIR, '1938-~11a~aa.ext', '1981-222+2b.ext')
        rename.main(['--debug', '-b', '--index-from', '6', '--char-non-alnum', 'remove', ROOT_DIR])
        self._assertFilesExist(ROOT_DIR, '1938-11aaa.ext', '1981-2222b.ext')
    def test_select_char_upper(self):
        print('======= test_select_char_upper ===')
        self._createSingleFiles(ROOT_DIR, 'thisFileIsInCamelCase.ext', 'only1Uppercase.ext')
        rename.main(['--debug', '--char-upper', 'add', ' ', ROOT_DIR])
        self._assertFilesExist(ROOT_DIR, 'this File Is In Camel Case.ext', 'only1 Uppercase.ext')

    def test_select_index_text_1(self):
        print('======= test_index_select_1 ===')
        self._createSingleFiles(ROOT_DIR, 'img 2011#my text must be changed.ext')
        rename.main(['--debug', '-b', '--index-from', '4', '--text', 'm', 'uppercase', ROOT_DIR])
        self._assertFilesExist(ROOT_DIR, 'img 2011#My text Must be changed.ext')
    def test_select_index_text_2(self):
        print('======= test_index_select_2 ===')
        self._createSingleFiles(ROOT_DIR, 'img 2011#mein text ist lang.ext')
        rename.main(['--debug', '--index-from', '7', '--text', ' ', 'replace', '-', ROOT_DIR])
        self._assertFilesExist(ROOT_DIR, 'img 2011#mein-text-ist-lang.ext')

    def test_select_pattern(self):
        print('======= test_select_pattern ===')
        self._createSingleFiles(ROOT_DIR, 'A10 - B20 - C30.ext', 'name 1 - name 2 - name 3.ext', 'name.ext')
        rename.main(['--debug', '-b', '--pattern', '|1| - |2| - |3|', 'replace', '|2| - |1|_|3|', ROOT_DIR])
        self._assertFilesExist(ROOT_DIR, 'B20 - A10_C30.ext', 'name 2 - name 1_name 3.ext', 'name.ext')
    def test_select_pattern_text_multi(self):
        print('======= test_select_pattern_text_multi ===')
        self._createSingleFiles(ROOT_DIR, 'a - cd 3 - z - cd 3.ext')
        rename.main(['--debug', '-b', '--text', 'cd 3', '--pattern', '|1| |2|', 'replace', '|1| 0|2|', ROOT_DIR])
        self._assertFilesExist(ROOT_DIR, 'a - cd 03 - z - cd 03.ext')
    def test_select_pattern_char_multi(self):
        print('======= test_select_pattern_type_multi ===')
        self._createSingleFiles(ROOT_DIR, 'AA-12 z-14 4.ext')
        rename.main(['--debug', '-b', '--index-from', '3', '--char-alnum', '--pattern', '|1|', 'replace', '|1|.', ROOT_DIR])
        self._assertFilesExist(ROOT_DIR, 'AA-12. z.-14. 4..ext')
    def test_select_pattern_illegalgroupname(self):
        print('======= test_select_pattern_illegalgroupname ===')
        self._createSingleFiles(ROOT_DIR, 'album - track.ext')
        with self.assertRaises(SystemExit) as cm:
            rename.main(['--debug', '-b', '--pattern', '|_al|-|tr-2|', 'replace', '|tr-2|', ROOT_DIR])
        self.assertEqual(cm.exception.code, 1)
        self._assertFilesExist(ROOT_DIR, 'album - track.ext')
    def test_select_pattern_syntaxerror(self):
        print('======= test_select_pattern_syntaxerror ===')
        self._createSingleFiles(ROOT_DIR, 'album - track.ext')
        with self.assertRaises(SystemExit) as cm:
            rename.main(['--debug', '-b', '--pattern', '|1|-|2||', 'replace', '|tr-2|', ROOT_DIR])
        self.assertEqual(cm.exception.code, 1)
        self._assertFilesExist(ROOT_DIR, 'album - track.ext')
    def test_select_pattern_illegalattributes(self):
        print('======= test_select_pattern_illegalattributes ===')
        self._createSingleFiles(ROOT_DIR, 'album - track.ext')
        with self.assertRaises(SystemExit) as cm:
            rename.main(['--debug', '-b', '--pattern', '|1:2s|-|2:xz|', 'replace', '|tr-2|', ROOT_DIR])
        self.assertEqual(cm.exception.code, 1)
        self._assertFilesExist(ROOT_DIR, 'album - track.ext')
    def test_select_pattern_withpipe(self):
        print('======= test_select_pattern_withpipe ===')
        self._createSingleFiles(ROOT_DIR, 'album - track.ext')
        rename.main(['--debug', '-b', '--pattern', '||-|t|', 'replace', '|t|', ROOT_DIR])
        self._assertFilesExist(ROOT_DIR, 'album - track.ext')
    def test_select_pattern_patternwithwildcards(self):
        print('======= test_select_pattern_patternwithwildcards ===')
        self._createSingleFiles(ROOT_DIR, 'album.track 1.ext', 'album_track 2.ext')
        rename.main(['--debug', '-b', '--pattern', '|al|.|tr|', 'replace', '|tr| - |al|', ROOT_DIR])
        self._assertFilesExist(ROOT_DIR, 'track 1 - album.ext', 'album_track 2.ext')
    def test_select_pattern_greedy(self):
        print('======= test_select_pattern_greedy ===')
        self._createSingleFiles(ROOT_DIR, 'Stones - beggars banquet - track one.ext', 'name 1 - name 2.ext')
        rename.main(['--debug', '-b', '--pattern', '|1| - |2|', 'replace', '|2| - |1|', ROOT_DIR])
        self._assertFilesExist(ROOT_DIR, 'track one - Stones - beggars banquet.ext', 'name 2 - name 1.ext')
    def test_select_pattern_non_greedy(self):
        print('======= test_select_pattern_non_greedy ===')
        self._createSingleFiles(ROOT_DIR, 'Stones - beggars banquet - track one.ext', 'name 1 - name 2.ext')
        rename.main(['--debug', '-b', '--pattern', '|1:?| - |2|', 'replace', '|2| - |1|', ROOT_DIR])
        self._assertFilesExist(ROOT_DIR, 'beggars banquet - track one - Stones.ext', 'name 2 - name 1.ext')
    def test_select_pattern_quantity(self):
        print('======= test_select_pattern_quantity ===')
        self._createSingleFiles(ROOT_DIR, 'IMG_20180122 - one.ext', 'IMG_20200824 - two.ext')
        rename.main(['--debug', '-b', '--pattern', 'IMG_|Y:4||M:2||D:2| - |1|', 'replace', '|Y|-|M|-|D| - |1|', ROOT_DIR])
        self._assertFilesExist(ROOT_DIR, '2018-01-22 - one.ext', '2020-08-24 - two.ext')
    def test_select_pattern_dir(self):
        print('======= test_select_pattern_dir ===')
        self._createSingleFiles(ROOT_DIR, 'report6part4.txt', 'report8part1.txt')
        rename.main(['--debug', '-b', '--pattern', 'report|1|part|2|', 'replace', 'french/rapport|1|partie|2|', ROOT_DIR])
        subDir = str(Path(ROOT_DIR, 'french'))
        self._assertFilesExist(subDir, 'rapport6partie4.txt', 'rapport8partie1.txt')
    def test_select_pattern_withselect(self):
        print('======= test_select_pattern_withselect ===')
        self._createSingleFiles(ROOT_DIR, 'Stones - beggars banquet - track one.ext')
        rename.main(['--debug', '-b', '--pattern', '|1| - |2:s| - |3|', 'camelcase', ROOT_DIR])
        self._assertFilesExist(ROOT_DIR, 'Stones - Beggars Banquet - track one.ext')
    def test_select_pattern_withselect_placeholder(self):
        print('======= test_select_pattern_withselect_placeholder ===')
        self._createSingleFiles(ROOT_DIR, 'Stones - beggars banquet - track one.ext')
        rename.main(['-v', '-b', '--pattern', '|1| - |2:s| - |3|', 'replace', '|3|_|2|', ROOT_DIR])
        self._assertFilesExist(ROOT_DIR, 'Stones - track one_beggars banquet - track one.ext')
    def test_select_pattern_withselect_twice(self):
        print('======= test_select_pattern_withselect_twice ===')
        self._createSingleFiles(ROOT_DIR, 'Stones - beggars Banquet - Track one.ext')
        rename.main(['--debug', '-b', '--pattern', '|1| - |2:s| - |3:s|', 'lowercase', ROOT_DIR])
        self._assertFilesExist(ROOT_DIR, 'Stones - beggars banquet - track one.ext')
    def test_select_pattern_withattribute(self):
        print('======= test_select_pattern_withattribute ===')
        self._createSingleFiles(ROOT_DIR, 'Stones - beggars banquet - track one.ext')
        rename.main(['--debug', '-b', '--pattern', '|1:s:?| - |2|', 'uppercase', ROOT_DIR])
        self._assertFilesExist(ROOT_DIR, 'STONES - beggars banquet - track one.ext')
    def test_select_pattern_number(self):
        print('======= test_select_pattern_number ===')
        self._createSingleFiles(ROOT_DIR, '123abc.ext', '123456def.ext')
        rename.main(['--debug', '-b', '--pattern', '|1:n:s||2|', 'replace', '_', ROOT_DIR])
        self._assertFilesExist(ROOT_DIR, '_abc.ext', '_def.ext')
    def test_select_pattern_alphabets(self):
        print('======= test_select_pattern_alphabets ===')
        self._createSingleFiles(ROOT_DIR, 'abc123.ext', 'def123456.ext')
        rename.main(['--debug', '-b', '--pattern', '|1:a:s||2|', 'replace', '_', ROOT_DIR])
        self._assertFilesExist(ROOT_DIR, '_123.ext', '_123456.ext')
    def test_select_pattern_filewithPipe(self):
        print('======= test_select_pattern_filewithPipe ===')
        if os.name == 'nt':
            print('skipped on Windows')
            return
        self._createSingleFiles(ROOT_DIR, 'very|important.ext', 'my|file.ext')
        rename.main(['--debug', '-b', '--pattern', '|1||||2|', 'replace', '|2|_|1|_||', ROOT_DIR])
        self._assertFilesExist(ROOT_DIR, 'important_very_|.ext', 'file_my_|.ext')

    def test_simulate(self):
        print('======= test_simulate ===')
        self._createSingleFiles(ROOT_DIR, 'a.txt', 'b.txt')
        rename.main(['--debug', '-n', 'add', '#', ROOT_DIR])
        self._assertFilesExist(ROOT_DIR, 'a.txt', 'b.txt')

    def test_swap(self):
        print('======= test_swap ===')
        self._createSingleFiles(ROOT_DIR, '1981_video.mp4', '1985_video.mp4', 'video.mp4')
        rename.main(['--debug', '-b', 'swap', '_', ROOT_DIR])
        self._assertFilesExist(ROOT_DIR, 'video_1981.mp4', 'video_1985.mp4', 'video.mp4')
    def test_swap_right(self):
        print('======= test_swap_right ===')
        self._createSingleFiles(ROOT_DIR, '1981video.mp4', '1985video.mp4', 'video.mp4')
        rename.main(['--debug', '-b', 'swap', '-r', 'vi', ROOT_DIR])
        self._assertFilesExist(ROOT_DIR, 'video1981.mp4', 'video1985.mp4', 'video.mp4')
    def test_swap_left(self):
        print('======= test_swap_left ===')
        self._createSingleFiles(ROOT_DIR, '1981movie.mp4', '1981video.mp4', 'video.mp4')
        rename.main(['--debug', '-b', 'swap', '-l', '81', ROOT_DIR])
        self._assertFilesExist(ROOT_DIR, 'movie1981.mp4', 'video1981.mp4', 'video.mp4')

    def test_test(self):
        print('======= test_test ===')
        self._createSingleFiles(ROOT_DIR, 'IMG_#01.jpg', 'IMG_#02.jpg', 'IMG_02.jpg', 'a very long, very long file name to test.txt')
        self._createFiles(ROOT_DIR, 50, 'IMG_')
        rename.main(['-b', '--index-from', '4', 'test', ROOT_DIR])

    def test_test_placeholder(self):
        print('======= test_test_placeholder ===')
        self._createSingleFiles(ROOT_DIR, 'IMG_#01.jpg', 'IMG_#02.jpg', 'IMG_02.jpg', 'a very long, very long file name to test.txt')
        self._createFiles(ROOT_DIR, 50, 'IMG_')
        rename.main(['-b', '--index-from', '4', 'test', '-p', ROOT_DIR])
    def test_test_placeholder_pattern(self):
        print('======= test_test_placeholder_pattern ===')
        self._createSingleFiles(ROOT_DIR, 'IMG_#01-image one.jpg', 'IMG_#02-image two.jpg', 'a very long, very long file name to test.txt')
        rename.main(['-b', '--pattern', 'IMG_#|1|-|2|', 'test', '-p', ROOT_DIR])

    # Helper methods
    def _createFiles(self, dir, numberFiles=1, prefix='file-', start=0):
        os.makedirs(dir, exist_ok=True)
        for i in range(start, numberFiles):
            fileName = f'{prefix}{i+1}.txt'
            filePath = os.path.join(dir, fileName)
            with open(filePath, 'x') as f:
                f.write(fileName)
    
    def _createSingleFiles(self, dir, *files):
        os.makedirs(dir, exist_ok=True)
        for file in files:
            filePath = os.path.join(dir, file)
            with open(filePath, 'x') as f:
                f.write(file)

    def _assertFilesExist(self, dir, *files):
        for file in files:
            filePath = os.path.join(dir, file)
            self.assertTrue(os.path.exists(filePath), msg=f'File does not exist: {filePath}')
            self.assertEqual(str(Path(filePath).resolve()), str(Path(filePath)), msg=f'File name is different: {filePath}')

    def _assertFilesNotExist(self, dir, *files):
        for file in files:
            filePath = os.path.join(dir, file)
            self.assertFalse(os.path.exists(filePath), msg=f'File does exist: {filePath}')
    
    def _assertFilesContent(self, dir, file, content):
        filePath = os.path.join(dir, file)
        with open(filePath, 'r') as f:
            self.assertEqual(f.read(), content)

if __name__ == '__main__':
    unittest.main()
    
