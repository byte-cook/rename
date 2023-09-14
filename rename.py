#!/usr/bin/env python3

import os
import argparse
import time
import logging
import string
import random
import shutil
import traceback
import textparser
from textparser import TokenType
import re
from textwrap import dedent
from pathlib import Path
from enum import Enum
from functools import cached_property
try:
    from mutagen.mp3 import MP3
    SUPPORT_MUTAGEN = True
except ImportError:
    SUPPORT_MUTAGEN = False

# commands
CMD_TEST = 'test'
CMD_ADD = 'add'
CMD_REMOVE = 'remove'
CMD_NUMBER = 'number'
CMD_REPLACE = 'replace'
CMD_LOWERCASE = 'lowercase'
CMD_UPPERCASE = 'uppercase'
CMD_CAMELCASE = 'camelcase'
CMD_SENTENCECASE = 'sentencecase'
CMD_SWAP = 'swap'
CMD_FILL = 'fill'
CMD_CUT = 'cut'
CMD_KEEP = 'keep'
CMD_DIR = 'dir'

# placeholders
PH_FILENAME = '|f|'
PH_BASENAME = '|b|'
PH_EXT = '|e|'
PH_FOLDER_0 = '|f0|'
PH_FOLDER_1 = '|f-1|'
PH_FOLDER_2 = '|f-2|'
PH_FOLDER_3 = '|f-3|'
PH_MODIFICATIONDATE = '|m|'
PH_MODIFICATIONDATE_YEAR = '|m:yyyy|'
PH_MODIFICATIONDATE_MONTH = '|m:mm|'
PH_MODIFICATIONDATE_DAY = '|m:dd|'
PH_ESCAPE = '||'
PH_AUDIO_ARTIST = '|artist|'
PH_AUDIO_ALBUM = '|album|'
PH_AUDIO_TRACK = '|track|'
PH_AUDIO_NO = '|no|'

# attributes
AT_SELECT = 's'
AT_GREEDY = '?'
AT_NUMBER = 'n'
AT_ALPHABETS = 'a'

# colors
ANSI_END = '\033[0m'
ANSI_BOLD = '\033[1m'
ANSI_DIM = '\033[2m'
ANSI_RED = '\033[31m'
ANSI_YELLOW = '\033[33m'
ANSI_CYAN = '\033[36m'
ANSI_GREY = '\033[37m'

class RenameError(Exception):
    def __init__(self, msg):
        self.msg = msg

class SelectPatternNameAttribute:
    def __init__(self, name):
        split = name.split(':')
        # the regex group name must be a valid python variable name (numbers are not allowed in the beginning)
        self.regExGroupName = '_' + split[0]
        self.placeholderName = '|' + split[0] + '|'
        if PH_ESCAPE != self.placeholderName and not split[0].isalnum():
            raise RenameError(f'Error: Only alphanumerics are allowed for placeholder name: {self.placeholderName}')
        # analyse attribute of a placeholder, e.g. "" or "s" or "s:7"
        attributes = split[1:]
        logging.debug(f'Attributes for "{name}": {attributes}')
        
        # set default values
        self.chars = quantifier = ''
        self.selected = greedy = False
        unrecognizedAttributes = []
        for a in attributes:
            if a == AT_SELECT:
                self.selected = True
            elif a == AT_GREEDY:
                greedy = True
            elif a == AT_NUMBER:
                self.chars += '0-9'
            elif a == AT_ALPHABETS:
                self.chars += 'a-zA-Z'
            elif a.isdecimal():
                quantifier = a
            elif not a:
                pass # ignore empty attributes
            else:
                unrecognizedAttributes.append(a)
        if unrecognizedAttributes:
            raise RenameError(f'Error: unrecognized attribute: {"".join(a for a in unrecognizedAttributes)}')
        if not self.chars:
            self.chars = '.'
        else:
            self.chars = f'[{self.chars}]'

        if quantifier:
            self.regExQuantifier = f'{{{quantifier}}}{"?" if greedy else ""}'
        else:
            self.regExQuantifier = f'*{"?" if greedy else ""}'
class SelectPatternToken:
    def __init__(self, type, value=''):
        self.type = type
        self.value = value
        if self.type == TokenType.PLACEHOLDER:
            self.nameAttr = SelectPatternNameAttribute(self.value)
        
    def toRegex(self):
        """Return the regex part for this token."""
        if self.type == TokenType.PLACEHOLDER:
            if PH_ESCAPE == self.nameAttr.placeholderName:
                return '\\|'
            else:
                return f'(?P<{self.nameAttr.regExGroupName}>{self.nameAttr.chars}{self.nameAttr.regExQuantifier})'
        else:
            return self.value.replace('.', '\\.').replace('*', '\\*').replace('?', '\\?')

    def __str__(self):
        if self.type == TokenType.PLACEHOLDER:
            return f'{ANSI_YELLOW}{self.nameAttr.placeholderName}{ANSI_END}'
        else:
            return self.value
class SelectPatternHandler:
    """Handler for option --pattern."""
    def __init__(self, pattern):
        self.patternTokens = self._parsePattern(pattern)
        regexString = ''.join(t.toRegex() for t in self.patternTokens)
        try:
            logging.debug(f'Pattern tokens: {f"{ANSI_DIM} | {ANSI_END}".join(str(t) for t in self.patternTokens)}')
            logging.debug(f'Pattern regex: {regexString}')
            self.regex = re.compile(regexString)
        except re.error as e:
            raise RenameError(f'Error: Failed to parse pattern: {e}')
        
    def _parsePattern(self, pattern):
        """Parses the --pattern option."""
        textTokens = textparser.tokenize(pattern, '|', includeSep=False)
        tokens = []
        for tt in textTokens:
            tokens.append(SelectPatternToken(tt.type, tt.value))
        return tokens
        
    def parseToken(self, token, path, args):
        # https://docs.python.org/3/library/re.html
        match = self.regex.match(token.text)
        if not match:
            return [ FilenameToken(token.text, False) ]

        # only needed if a token is marked as selected
        selectionFilenameTokens = []
        selectionAttributeAvailable = False

        patternPlaceholders = {}
        for patternToken in self.patternTokens:
            if patternToken.type == TokenType.PLACEHOLDER and PH_ESCAPE != patternToken.nameAttr.placeholderName:
                matchedText = match.group(patternToken.nameAttr.regExGroupName)
                patternPlaceholders[patternToken.nameAttr.placeholderName] = matchedText
                
                selectionFilenameTokens.append(FilenameToken(matchedText, patternToken.nameAttr.selected, patternPlaceholders))
                selectionAttributeAvailable |= patternToken.nameAttr.selected
            else:
                selectionFilenameTokens.append(FilenameToken(patternToken.value, False, None))
        
        if selectionAttributeAvailable:
            # create new filename tokens for each PatternToken
            if logging.getLogger().isEnabledFor(logging.DEBUG):
                for t in selectionFilenameTokens:
                    if t.change:
                        logging.debug(f'{t}: {t.patternPlaceholders}')
            return selectionFilenameTokens
        else:
            # create single filename token for the whole pattern
            logging.debug(f'Pattern placeholders for {token}: {patternPlaceholders}')
            return [ FilenameToken(token.text, True, patternPlaceholders) ]
            
class FilenameParser:
    """Parser a file name and creates FilenameToken's."""
    def __init__(self):
        self.selectorLevel1 = []
        self.selectorLevel2 = []
        self.selectorLevel3 = []
        self.selectorLevel4 = []
        self.selectorLevel5 = []

    def init(self, args):
        # basename/ext
        if args.basename:
            self.selectorLevel1.append(self._selectBasename)
        elif args.ext:
            self.selectorLevel1.append(self._selectExt)
        elif args.extWithDot:
            self.selectorLevel1.append(self._selectExtWithDot)
        
        # index
        if args.selectIndex:
            self.selectorLevel2.append(self._selectIndex)
            if args.selectIndexTo or args.selectIndexRightTo or args.selectIndexFrom or args.selectIndexRightFrom:
                raise RenameError(f'Error: combinations of index arguments are not allowed')
        else:
            # index from/to must be evaluated together because otherwise the indexation would change
            if args.selectIndexTo or args.selectIndexRightTo or args.selectIndexFrom or args.selectIndexRightFrom:
                self.selectorLevel2.append(self._selectIndexRange)

        #text
        if args.selectText:
            self.selectorLevel3.append(self._selectText)
            if args.selectTextFrom or args.selectTextExclFrom or args.selectTextTo or args.selectTextExclTo:
                raise RenameError(f'Error: combinations of text arguments are not allowed')
        else:
            if args.selectTextFrom:
                self.selectorLevel3.append(self._selectTextFrom)
            elif args.selectTextExclFrom:
                self.selectorLevel3.append(self._selectTextXFrom)
            
            if args.selectTextTo:
                self.selectorLevel3.append(self._selectTextTo)
            elif args.selectTextExclTo:
                self.selectorLevel3.append(self._selectTextXTo)
                
        # char
        if args.charNum:
            self.selectorLevel4.append(self._selectCharNum)
        elif args.charNonNum:
            self.selectorLevel4.append(self._selectcharNonNum)
        elif args.charAlpha:
            self.selectorLevel4.append(self._selectCharAlpha)
        elif args.charNonAlpha:
            self.selectorLevel4.append(self._selectCharNonAlpha)
        elif args.charAlnum:
            self.selectorLevel4.append(self._selectCharAlnum)
        elif args.charNonAlnum:
            self.selectorLevel4.append(self._selectCharNonAlnum)
        elif args.charUpper:
            self.selectorLevel4.append(self._selectCharUpper)
        elif args.charLower:
            self.selectorLevel4.append(self._selectCharLower)
        
        # pattern
        if args.pattern:
            selectPattern = SelectPatternHandler(args.pattern)
            self.selectorLevel5.append(selectPattern.parseToken)

    def _selectBasename(self, token, path, args):
        return [ FilenameToken(path.stem, True), FilenameToken(path.suffix, False) ]
    def _selectExt(self, token, path, args):
        stem = FilenameToken(path.stem, False)
        ext = path.suffix
        if not ext:
            return [ stem ]
        else:
            # remove leading dot from extension
            return [ stem, FilenameToken(ext[0], False), FilenameToken(ext[1:], True) ]
    def _selectExtWithDot(self, token, path, args):
        stem = FilenameToken(path.stem, False)
        ext = path.suffix
        if not ext:
            return [ stem ]
        else:
            return [ stem, FilenameToken(path.suffix, True) ]

    def _selectIndex(self, token, path, args):
        index = args.selectIndex-1
        logging.debug(f'Split token "{token.text}" by index: {index}')
        try:
            return [ FilenameToken(token.text[:index], False), FilenameToken(token.text[index], True), FilenameToken(token.text[index+1:], False) ]
        except IndexError as e:
            logging.debug(e)
            return [ FilenameToken(token.text, False) ]
    def _selectIndexRange(self, token, path, args):
        indexFrom = None
        if args.selectIndexFrom or args.selectIndexRightFrom:
            indexFrom = args.selectIndexFrom-1 if args.selectIndexFrom else -1*args.selectIndexRightFrom
        indexTo = None
        if args.selectIndexTo or args.selectIndexRightTo:
            indexTo = args.selectIndexTo if args.selectIndexTo else -1*args.selectIndexRightTo+1
        logging.debug(f'Split token "{token.text}" by index: {indexFrom}:{indexTo}')

        selectedText = token.text[indexFrom:indexTo]
        if not selectedText:
            # no text could be extracted, return original token
            return [ FilenameToken(token.text, False) ]

        if indexFrom is not None and indexTo is not None:
            return [ FilenameToken(token.text[:indexFrom], False), FilenameToken(selectedText, True), FilenameToken(token.text[indexTo:], False) ]
        elif indexFrom is not None:
            return [ FilenameToken(token.text[:indexFrom], False), FilenameToken(selectedText, True) ]
        elif indexTo is not None:
            return [ FilenameToken(selectedText, True), FilenameToken(token.text[indexTo:], False) ]
        else:
            # this case should not be possible, nothing will be changed
            return token

    def _selectText(self, token, path, args):
        split = token.text.split(args.selectText)
        logging.debug(f'Split token by text: {args.selectText} -> {split}')
        t = []
        for s in split:
            if t:
                # do not append token for the first item: "a-b".split("-") -> [ "a", "b" ]
               t.append(FilenameToken(args.selectText, True))
            t.append(FilenameToken(s, False))
        return t
    def _selectTextFrom(self, token, path, args):
        # https://docs.python.org/3/library/stdtypes.html#bytes.partition
        partition = token.text.partition(args.selectTextFrom)
        logging.debug(f'Split token by text from: {args.selectTextFrom} -> {partition}')
        if not partition[1] and not partition[2]:
            # string not found if partions 1+2 are empty -> partition 0 contains original text
            return [ FilenameToken(partition[0], False) ]
        else:
            return [ FilenameToken(partition[0], False), FilenameToken(partition[1]+partition[2], True) ]
    def _selectTextXFrom(self, token, path, args):
        partition = token.text.partition(args.selectTextExclFrom)
        logging.debug(f'Split token by text from (excluded): {args.selectTextExclFrom} -> {partition}')
        if not partition[1] and not partition[2]:
            # string not found if partions 1+2 are empty -> partition 0 contains original text
            return [ FilenameToken(partition[0], False) ]
        else:
            return [ FilenameToken(partition[0]+partition[1], False), FilenameToken(partition[2], True) ]
    def _selectTextTo(self, token, path, args):
        partition = token.text.partition(args.selectTextTo)
        logging.debug(f'Split token by text from (excluded): {args.selectTextTo} -> {partition}')
        if not partition[1] and not partition[2]:
            # string not found if partions 1+2 are empty -> partition 0 contains original text
            return [ FilenameToken(partition[0], False) ]
        else:
            return [ FilenameToken(partition[0]+partition[1], True), FilenameToken(partition[2], False) ]
    def _selectTextXTo(self, token, path, args):
        partition = token.text.partition(args.selectTextExclTo)
        logging.debug(f'Split token by text from (excluded): {args.selectTextExclTo} -> {partition}')
        if not partition[1] and not partition[2]:
            # string not found if partions 1+2 are empty -> partition 0 contains original text
            return [ FilenameToken(partition[0], False) ]
        else:
            return [ FilenameToken(partition[0], True), FilenameToken(partition[1]+partition[2], False) ]

    def _selectCharNum(self, token, path, args):
        return self._selectCharHelper(token, path, args, lambda c: c.isnumeric())
    def _selectcharNonNum(self, token, path, args):
        return self._selectCharHelper(token, path, args, lambda c: not c.isnumeric())
    def _selectCharAlpha(self, token, path, args):
        return self._selectCharHelper(token, path, args, lambda c: c.isalpha())
    def _selectCharNonAlpha(self, token, path, args):
        return self._selectCharHelper(token, path, args, lambda c: not c.isalpha())
    def _selectCharAlnum(self, token, path, args):
        return self._selectCharHelper(token, path, args, lambda c: c.isalnum())
    def _selectCharNonAlnum(self, token, path, args):
        return self._selectCharHelper(token, path, args, lambda c: not c.isalnum())
    def _selectCharUpper(self, token, path, args):
        return self._selectCharHelper(token, path, args, lambda c: c.isupper())
    def _selectCharLower(self, token, path, args):
        return self._selectCharHelper(token, path, args, lambda c: c.islower())
    def _selectCharHelper(self, token, path, args, func):
        t = []
        tmp = FilenameToken('', False)
        for c in token.text:
            isdigit = func(c)
            if isdigit and tmp.change:
                tmp.text += c
            elif not isdigit and not tmp.change:
                tmp.text += c
            elif isdigit and not tmp.change:
                t.append(tmp)
                tmp = FilenameToken(c, True)
            elif not isdigit and tmp.change:
                t.append(tmp)
                tmp = FilenameToken(c, False)
        t.append(tmp)
        return t

    def getTokens(self, path, args):
        filePath = path.relative_to(os.getcwd()) if path.is_relative_to(os.getcwd()) else path
        logging.debug(f'Get tokens for "{filePath}"')
        tokens = [ FilenameToken(path.name, True) ]
        logging.debug(f'Level 0: Tokens of "{filePath}": {f"{ANSI_DIM} | {ANSI_END}".join(str(t) for t in tokens)}')
        for l1 in self.selectorLevel1:
            tokens = self._replaceChangeTokens(tokens, l1, path, args)
        logging.debug(f'Level 1: Tokens of "{filePath}": {f"{ANSI_DIM} | {ANSI_END}".join(str(t) for t in tokens)}')
        for l2 in self.selectorLevel2:
            tokens = self._replaceChangeTokens(tokens, l2, path, args)
        logging.debug(f'Level 2: Tokens of "{filePath}": {f"{ANSI_DIM} | {ANSI_END}".join(str(t) for t in tokens)}')
        for l3 in self.selectorLevel3:
            tokens = self._replaceChangeTokens(tokens, l3, path, args)
        logging.debug(f'Level 3: Tokens of "{filePath}": {f"{ANSI_DIM} | {ANSI_END}".join(str(t) for t in tokens)}')
        for l4 in self.selectorLevel4:
            tokens = self._replaceChangeTokens(tokens, l4, path, args)
        logging.debug(f'Level 4: Tokens of "{filePath}": {f"{ANSI_DIM} | {ANSI_END}".join(str(t) for t in tokens)}')
        for l5 in self.selectorLevel5:
            tokens = self._replaceChangeTokens(tokens, l5, path, args)
        logging.debug(f'=> Tokens of "{filePath}": {f"{ANSI_DIM} | {ANSI_END}".join(str(t) for t in tokens)}')
        # validate tokens
        for t in tokens:
            if t.change and not t.text:
                # selected text must not be empty
                raise RenameError(f'{path}: Parsing failed: Token is empty')
        return tokens

    def _replaceChangeTokens(self, tokens, selector, path, args):
        newTokens = []
        for token in tokens:
            if token.change:
                newTokens.extend(selector(token, path, args))
            else:
                newTokens.append(token)
        return newTokens

class FilenameToken:
    """Part of a file name."""
    def __init__(self, text, change, patternPlaceholders={}):
        self.text = text
        self.change = change
        self.patternPlaceholders = patternPlaceholders
        
    def updateText(self, newText, end):
        if end:
            self.text += newText
        else:
            self.text = newText + self.text

    def __str__(self):
        if self.change:
            return f'{ANSI_CYAN}{self.text}{ANSI_END}'
        else:
            return self.text

class FileRenamer:
    """Renames a file."""
    def __init__(self, path, tokens):
        self.path = path.resolve()
        self.tokens = tokens
        self.done = False
        # ensure that file name is equal with tokens
        tokenFileName = "".join(t.text for t in self.tokens)
        if self.path.name != tokenFileName:
            raise RenameError(f'{self.path}: Parsing failed: {tokenFileName}')
    
    def getTokensToChange(self):
        return list(filter(lambda t: t.change, self.tokens))
    def getFirstTokenToChange(self):
        return next((t for t in self.tokens if t.change), None)
   
    def getSrcFile(self):
        return self.path.relative_to(os.getcwd()) if self.path.is_relative_to(os.getcwd()) else self.path
    
    def getDstFile(self):
        newFilename = "".join(t.text for t in self.tokens)
        newPath = self.path.parent / newFilename
        return newPath.relative_to(os.getcwd()) if newPath.is_relative_to(os.getcwd()) else newPath
    
    def resolvePlaceholders(self, text, token):
        tokens = textparser.tokenize(text, sep='|', includeSep=True)
        logging.debug(f'Resolve placeholder tokens for "{self.getSrcFile()}": {f"{ANSI_DIM} | {ANSI_END}".join(str(t) for t in tokens)}')
        
        resolvedText = ''
        for t in tokens:
            if t.isText():
                resolvedText += t.value
            else:
                resolvedText += self.replaceSinglePlaceholder(t.value, token)
        return resolvedText
        
    def replaceSinglePlaceholder(self, placeholder, token, raiseIfNotFound=True):
        """Return the resolved text for the given placeholder."""
        if PH_FILENAME == placeholder:
            return self.path.name
        if PH_BASENAME == placeholder:
            return self.path.stem
        if PH_EXT == placeholder:
            return self.path.suffix[1:]
        if PH_MODIFICATIONDATE == placeholder:
            mTimestamp = self.path.stat().st_mtime
            mDate = time.strftime("%Y-%m-%d", time.gmtime(mTimestamp))
            return mDate
        if PH_MODIFICATIONDATE_YEAR == placeholder:
            mTimestamp = self.path.stat().st_mtime
            mDate = time.strftime("%Y", time.gmtime(mTimestamp))
            return mDate
        if PH_MODIFICATIONDATE_MONTH == placeholder:
            mTimestamp = self.path.stat().st_mtime
            mDate = time.strftime("%m", time.gmtime(mTimestamp))
            return mDate
        if PH_MODIFICATIONDATE_DAY == placeholder:
            mTimestamp = self.path.stat().st_mtime
            mDate = time.strftime("%d", time.gmtime(mTimestamp))
            return mDate
        # folders
        phFolders = {PH_FOLDER_0: 2, PH_FOLDER_1: 3, PH_FOLDER_2: 4, PH_FOLDER_3: 5}
        for ph in phFolders:
            if ph == placeholder:
                parts = self.path.parts
                if len(parts) >= phFolders[ph]:
                    return parts[-phFolders[ph]]
        # metadata 
        if SUPPORT_MUTAGEN and self.path.suffix == '.mp3':
            if PH_AUDIO_ARTIST == placeholder or PH_AUDIO_ALBUM == placeholder or PH_AUDIO_TRACK == placeholder or PH_AUDIO_NO == placeholder:
                # https://mutagen.readthedocs.io/en/latest/user/id3.html
                # https://stackoverflow.com/questions/71468239/function-to-write-id3-tag-with-python-3-mutagen
                # logging.debug('All available keys: ' + str(EasyID3.valid_keys.keys()))
                audio = self._easyID3
                if PH_AUDIO_ARTIST == placeholder and 'artist' in audio:
                    return audio['artist'][0]
                if PH_AUDIO_ALBUM == placeholder and 'album' in audio:
                    return audio['album'][0]
                if PH_AUDIO_TRACK == placeholder and 'title' in audio:
                    return audio['title'][0]
                if PH_AUDIO_NO == placeholder and 'tracknumber' in audio:
                    tracknumber = audio['tracknumber'][0]
                    return f'{tracknumber:>02}'
        
        # placeholders from --pattern option
        if token is not None:
            for ph in token.patternPlaceholders:
                if ph == placeholder:
                    return token.patternPlaceholders[ph]

        # escape
        if PH_ESCAPE == placeholder:
            return '|'
        if raiseIfNotFound:
            raise RenameError(f'Error: Cannot resolve placeholder "{placeholder}"')
        return placeholder
    
    @cached_property
    def _easyID3(self):
        from mutagen.easyid3 import EasyID3
        logging.debug(f'Create EasyID3 object for "{self.getSrcFile()}"')
        audio = EasyID3(self.path)
        logging.debug(f'Audio metadata: {audio}')
        return audio
        
    def renameDryRun(self, deletedFiles, createdFiles):
        """Only return True if DstFile does not exist."""
        src = self.getSrcFile()
        dst = self.getDstFile()
        if self.done:
            return False
        if src == dst:
            if str(src) != str(dst):
                print(f'{src} -> {dst}')
                self.done = True
                return True
            else:
                print(f'{ANSI_DIM}{src}: File name not changed{ANSI_END}')
                self.done = True
                return False
        elif (os.path.exists(dst) and dst not in deletedFiles) or dst in createdFiles:
            # file cannot be renamed
            return False
        else:
            print(f'{src} -> {dst}')
            self.done = True
            return True
        return False
    
    def rename(self, args):
        """Rename the file and return True if succeeded."""
        src = self.getSrcFile()
        dst = self.getDstFile()
        if self.done:
            return False
        elif src == dst:
            if str(src) != str(dst):
                msg = f'{src} -> {dst}'
                print(msg) if args.verbose else logging.debug(msg)
                
                # file system is case insensitive: temp move "src" to "src.<RANDOM>"
                randomPostfix = ''.join(random.choices(string.ascii_uppercase + string.digits, k=5))
                tmpSrc = str(src) + f'.{randomPostfix}'
                logging.debug(f'Use tmp file: {tmpSrc}')
                if not os.path.exists(tmpSrc):
                    shutil.move(src, tmpSrc)
                    # IMPORTANT: this case can only happen if src == dst (never overwrite dst otherwise)
                    shutil.move(tmpSrc, dst)
                    self.done = True
                    return True
                return False
            else:
                print(f'{ANSI_DIM}{src}: File name not changed{ANSI_END}')
                self.done = True
                return False
        elif not os.path.exists(dst):
            msg = f'{src} -> {dst}'
            print(msg) if args.verbose else logging.debug(msg)

            if not os.path.exists(dst.parent):
                os.makedirs(dst.parent, exist_ok=True)
            shutil.move(src, dst)
            self.done = True
            return True
        return False
        
class TestCmd():
    PLACEHOLDERS = { PH_FILENAME : 'File name', PH_BASENAME : 'Base name', PH_EXT : 'Extension', 
        PH_FOLDER_0 : 'Folder', PH_FOLDER_1 : 'Parent folder', PH_FOLDER_2 : 'Parent folder 2', PH_FOLDER_3 : 'Parent folder 3', 
        PH_MODIFICATIONDATE : 'Last modified', PH_MODIFICATIONDATE_YEAR : 'Last modified year', PH_MODIFICATIONDATE_MONTH : 'Last modified month', PH_MODIFICATIONDATE_DAY : 'Last modified day',
        PH_AUDIO_ARTIST : 'Audio artist', PH_AUDIO_ALBUM : 'Audio album', PH_AUDIO_TRACK : 'Audio track', PH_AUDIO_NO : 'Audio Number',
        PH_ESCAPE : 'Escape pipe "|"' }
    
    def __init__(self, renamers, args):
        self.length = -1
        for renamer in renamers:
            fileName = str(renamer.getSrcFile().name)
            self.length = max(self.length, int(len(fileName) / 10) + 1)
        self.indexPrinted = self.length == -1

    def apply(self, renamer, args):
        if args.showPlaceholders:
            print(f'Placeholders for: {renamer.getSrcFile()}')
            for ph in TestCmd.PLACEHOLDERS:
                text = renamer.replaceSinglePlaceholder(ph, None, raiseIfNotFound=False)
                if text != ph:
                    print(f'{TestCmd.PLACEHOLDERS[ph]:<20}: {ph:8} {ANSI_CYAN}{text}{ANSI_END}')

            for t in renamer.tokens:
                for ph in t.patternPlaceholders:
                    print(f'{"Custom placeholder":<20}: {ph:8} {ANSI_CYAN}{t.patternPlaceholders[ph]}{ANSI_END}')
                    
            print()
        else:
            fileName = str(renamer.getSrcFile().name)
            if not self.indexPrinted:
                print(f'{ANSI_BOLD}', end='')
                for i in range(self.length):
                    print(f'        {(i+1)*10}', end='')
                print(f'   ', end='')
                for i in range(self.length):
                    print(f'        {(i+1)*10}', end='')
                print()
                print(f'{"123456789|" * self.length}   {"123456789|" * self.length}')
                print(f'{ANSI_END}', end='')
                self.indexPrinted = True
            ansiStart = ANSI_DIM if renamer.getFirstTokenToChange() is None else ''
            print(f'{ansiStart}{fileName:<{10*self.length}} : {"".join(str(t) for t in renamer.getTokensToChange())}{ANSI_END}')

class FillCmd():
    def __init__(self, renamers, args):
        if len(args.char) > 1:
            raise RenameError(f'The fill character must be exactly one character long: {args.char}')
        self.width = args.width if args.width else -1
        if self.width == -1:
            for renamer in renamers:
                tokens = renamer.getTokensToChange()
                if tokens:
                    self.width = max(self.width, len(tokens[0].text))

    def apply(self, renamer, args):
        t = renamer.getFirstTokenToChange()
        if t is not None:
            if args.end:
                t.text = t.text.ljust(self.width, args.char)
            else:
                t.text = t.text.rjust(self.width, args.char)

class NumberCmd():
    def __init__(self, renamers, args):
        self.start = args.start
        self.width = args.width if args.width else -1
        if self.width == -1:
            if args.noReset:
                self.width = len(str(len(renamers)))
            else:
                fileCountPerFolder = {}
                for r in renamers:
                    dir = r.path.parent
                    fileCountPerFolder[dir] = fileCountPerFolder[dir]+1 if dir in fileCountPerFolder else 1
                logging.debug(f'File count for folders: {fileCountPerFolder}')
                self.width = len(str(max(fileCountPerFolder.values())))
        self.increment = args.increment
        self.before = args.before if args.before else ""
        self.after = args.after if args.after else ""
        self.current = args.start
        self.currentDir = None
        
    def apply(self, renamer, args):
        if not args.noReset:
            # reset start index for each folder
            if self.currentDir is None or self.currentDir == renamer.path.parent:
                self.currentDir = renamer.path.parent
            else: 
                self.currentDir = renamer.path.parent
                self.current = self.start
        t = renamer.getFirstTokenToChange()
        if t is not None:
            numberText = f'{renamer.resolvePlaceholders(self.before, t)}{self.current:0{self.width}d}{renamer.resolvePlaceholders(self.after, t)}'
            t.updateText(numberText, args.end)
        self.current += self.increment

def getCommand(args, renamers):
    """Returns a function to call for renaming. For actions that require a state, an object is created and a member function is returned."""
    if args.command in (CMD_TEST):
        return TestCmd(renamers, args).apply
    elif args.command in (CMD_ADD):
        def add(renamer, args):
            for t in renamer.getTokensToChange():
                addText = renamer.resolvePlaceholders(args.text, t)
                t.updateText(addText, args.end)
        return add
    elif args.command in (CMD_REMOVE):
        def remove(renamer, args):
            for t in renamer.getTokensToChange():
                t.text = ''
        return remove
    elif args.command in (CMD_REPLACE):
        def replace(renamer, args):
            for t in renamer.getTokensToChange():
                t.text = renamer.resolvePlaceholders(args.text, t)
        return replace
    elif args.command in (CMD_LOWERCASE):
        def lowercase(renamer, args):
            for t in renamer.getTokensToChange():
                t.text = t.text.lower()
        return lowercase
    elif args.command in (CMD_UPPERCASE):
        def uppercase(renamer, args):
            for t in renamer.getTokensToChange():
                t.text = t.text.upper()
        return uppercase
    elif args.command in (CMD_CAMELCASE):
        def camelcase(renamer, args):
            for t in renamer.getTokensToChange():
                t.text = string.capwords(t.text)
        return camelcase
    elif args.command in (CMD_SENTENCECASE):
        def sentencecase(renamer, args):
            for t in renamer.getTokensToChange():
                t.text = t.text.capitalize()
        return sentencecase
    elif args.command in (CMD_FILL):
        return FillCmd(renamers, args).apply
    elif args.command in (CMD_SWAP):
        def swap(renamer, args):
            for t in renamer.getTokensToChange():
                partition = t.text.partition(args.separator)
                if not partition[1] and not partition[2]:
                    # separator not found
                    pass
                else:
                    if args.left:
                        t.text = partition[2]+partition[0]+partition[1]
                    elif args.right:
                        t.text = partition[1]+partition[2]+partition[0]
                    else:
                        t.text = partition[2]+partition[1]+partition[0]
        return swap
    elif args.command in (CMD_NUMBER):
        return NumberCmd(renamers, args).apply
    elif args.command in (CMD_CUT):
        def cut(renamer, args):
            for t in renamer.getTokensToChange():
                if args.end:
                    t.text = t.text[:-args.index]
                else:
                    t.text = t.text[args.index:]
        return cut
    elif args.command in (CMD_KEEP):
        def keep(renamer, args):
            for t in renamer.getTokensToChange():
                if args.end:
                    lenght = len(t.text)
                    start = max(0, lenght-args.index) # not negative
                    t.text = t.text[start:]
                else:
                    t.text = t.text[:args.index]
        return keep
    elif args.command in (CMD_DIR):
        def dir(renamer, args):
            # only apply to files that matches the select options
            if renamer.getFirstTokenToChange() is not None:
                firstToken = renamer.tokens[0]
                targetDir = args.dir if args.dir.endswith('/') else args.dir + '/'
                firstToken.text = renamer.resolvePlaceholders(targetDir, firstToken) + firstToken.text
        return dir

def getPaths(tops, recursive=False, dirOnly=False):
    """Returns all files and folders."""
    paths = []
    for top in tops:
        if not os.path.exists(top):
            raise RenameError(f'Error: File "{top}" does not exist')
        top = os.path.abspath(top)
        if os.path.isdir(top):
            if recursive:
                for (root, dirs, files) in os.walk(top):
                    if dirOnly:
                        for d in dirs:
                            d = os.path.join(root, d)
                            paths.append(d)
                    else:
                        for f in files:
                            f = os.path.join(root, f)
                            paths.append(f)
            elif dirOnly:
                paths.append(top)
            else:
                for f in os.listdir(top):
                    f = os.path.join(top, f)
                    if not os.path.isdir(f):
                        paths.append(f)
        elif not dirOnly:
            paths.append(top)
    # remove duplicates
    paths = set(paths)
    return paths

def positiveInt(value):
    """Check if value is positive int."""
    ivalue = int(value)
    if ivalue <= 0:
        raise argparse.ArgumentTypeError(f'invalid positive int value: {value}')
    return ivalue

def nonEmptyString(value):
    """Check if value is not empty."""
    if not value:
        raise argparse.ArgumentTypeError(f'invalid non-empty text: {value}')
    return value
    
def main(argv=None):
    try:
        PROG_DESC = """\
            Batch renaming of files.
            
            The general structure of a command is as follows:
            > rename.py SELECT-OPTIONS COMMAND COMMAND-ARGUMENTS FILES
            
            SELECT-OPTIONS              : Define what to change (which parts of a file name).
            COMMAND COMMAND-ARGUMENTS   : Define how to change (e.g. add a text).
            FILES                       : Define the files that should be renamed. Default is to use the current directory.

            The order of the select options is as follows: 
            1. basename/ext 
            2. index 
            3. text 
            4. char 
            5. pattern.

            === Select by pattern ===
            
            The --pattern option allows to group a file name. To do this, define placeholders in the following form: 
            |NAME| or |NAME[:ATTR ...]|
                
            NAME the alphanumeric name of the placeholder. It can then be used in the command.
            ATTR is used to change the behavior of the placeholder. The following possibilities exist:
                ?   : placeholder does not behave greedily (default behavior is greedy)
                s   : select this token (default is to select the whole pattern text)
                a   : matches alphabets a-zA-Z (default is to match any character: .)
                n   : matches numbers 0-9 (default is to match any character: .)
                1-9 : number of characters to be read in (default is 0 or more: *)
            
            Example for file "20180122-description-long.jpg": --pattern "|Y:4||M:2||D:2|-|A:s:?|-|B|" 
                |Y| = 2018
                |M| = 01
                |D| = 22
                |A| = description (selected, not greedy)
                |B| = long.jpg
            
            === Command test ===
            
            The test command allows to check which parts of the name are selected. The -p option prints the available placeholders for each file.
            This can be very helpful to try out the various options without risk.
            
            """
        
        parser = argparse.ArgumentParser(description=dedent(PROG_DESC), formatter_class=argparse.RawTextHelpFormatter)
        parser.add_argument('--debug', help='activate DEBUG logging', action='store_true')
        parser.add_argument('-v', '--verbose', action='store_true', help='explain what is being done')
        parser.add_argument('-n', '--dry-run', action='store_true', dest='simulate', help='simulate backup process')
        parser.add_argument('-r', '--recursive', action='store_true', help='perform command recursively')
        parser.add_argument('--dir-only', action='store_true', dest='dirOnly', help='rename folders only')
        # basename/ext
        group_1 = parser.add_argument_group('1. Select the part of a filename to change (<basename>.<ext>)')
        group_1 = group_1.add_mutually_exclusive_group()
        group_1.add_argument('-b', action='store_true', dest='basename', help='select basename to change')
        group_1.add_argument('-e', action='store_true', dest='ext', help='select extension to change without dot')
        group_1.add_argument('-E', action='store_true', dest='extWithDot', help='change extension only with dot')
        # index
        group_2 = parser.add_argument_group('2. Select text to change either by single index (--index) or range index (--index*)')
        group_2.add_argument('--index', dest='selectIndex', type=positiveInt, help='select single character to change by index from the left')
        group_2.add_argument('--index-from', dest='selectIndexFrom', type=positiveInt, help='select text to change by start index from the left')
        group_2.add_argument('--index-to', dest='selectIndexTo', type=positiveInt, help='select text to change by end index from the left')
        group_2.add_argument('--indexr-from', dest='selectIndexRightFrom', type=positiveInt, help='select text to change by start index from the right')
        group_2.add_argument('--indexr-to', dest='selectIndexRightTo', type=positiveInt, help='select text to change by end index from the right')
        # text
        group_3 = parser.add_argument_group('3. Select text to change either by text (--text) or text ranges (--text*)')
        group_3.add_argument('--text', dest='selectText', type=nonEmptyString, help='select matching text to change')
        group_3.add_argument('--text-from', dest='selectTextFrom', type=nonEmptyString, help='select text to change by start index from the left')
        group_3.add_argument('--text-to', dest='selectTextTo', type=nonEmptyString, help='select text to change by end index from the left')
        group_3.add_argument('--textx-from', dest='selectTextExclFrom', type=nonEmptyString, help='select text to change by start index from the left')
        group_3.add_argument('--textx-to', dest='selectTextExclTo', type=nonEmptyString, help='select text to change by start index from the left')
        # char
        group_4 = parser.add_argument_group('4. Select text to change by character type')
        group_4 = group_4.add_mutually_exclusive_group()
        group_4.add_argument('--char-num', action='store_true', dest='charNum', help='select only numberics to change')
        group_4.add_argument('--char-non-num', action='store_true', dest='charNonNum', help='select all except numerics to change')
        group_4.add_argument('--char-alpha', action='store_true', dest='charAlpha', help='select only alphabets to change')
        group_4.add_argument('--char-non-alpha', action='store_true', dest='charNonAlpha', help='select all except alphabets to change')
        group_4.add_argument('--char-alnum', action='store_true', dest='charAlnum', help='select only alphanumerics to change')
        group_4.add_argument('--char-non-alnum', action='store_true', dest='charNonAlnum', help='select all except alphanumerics to change')
        group_4.add_argument('--char-upper', action='store_true', dest='charUpper', help='select upper case alphabets to change (A-Z)')
        group_4.add_argument('--char-lower', action='store_true', dest='charLower', help='select upper case alphabets to change (a-z)')
        # pattern
        group_5 = parser.add_argument_group('5. Select text to change by pattern')
        group_5.add_argument('--pattern', help='the pattern to parse')

        subparsers = parser.add_subparsers(dest='command')
        subparsers.required = True
        # test
        testParser = subparsers.add_parser(CMD_TEST, help='print selected text and exit')
        testParser.add_argument('-p', action='store_true', dest='showPlaceholders', help='show placeholders')
        testParser.add_argument('file', nargs='*', default='.', help='file or folder')
        # add
        addParser = subparsers.add_parser(CMD_ADD, help='add text before/after selected text: cd -> ABcd')
        addParser.add_argument('-e', action='store_true', dest='end', help='add TEXT at the end')
        addParser.add_argument('text', help='the text to add')
        addParser.add_argument('file', nargs='*', default='.', help='file or folder')
        # remove
        removeParser = subparsers.add_parser(CMD_REMOVE, help='remove selected text: ABcd -> cd')
        removeParser.add_argument('file', nargs='*', default='.', help='file or folder')
        # replace
        replaceParser = subparsers.add_parser(CMD_REPLACE, help='replace selected text: ABcd -> EFcd')
        replaceParser.add_argument('text', help='the text to use')
        replaceParser.add_argument('file', nargs='*', default='.', help='file or folder')
        # lower
        lowerParser = subparsers.add_parser(CMD_LOWERCASE, help='change selected text to lower case: Ab -> ab')
        lowerParser.add_argument('file', nargs='*', default='.', help='file or folder')
        # upper
        upperParser = subparsers.add_parser(CMD_UPPERCASE, help='change selected text to UPPER CASE: ab -> AB')
        upperParser.add_argument('file', nargs='*', default='.', help='file or folder')
        # camel
        camelParser = subparsers.add_parser(CMD_CAMELCASE, help='change selected text to Camel Case: ab cd -> Ab Cd')
        camelParser.add_argument('file', nargs='*', default='.', help='file or folder')
        # sentence
        sentenceParser = subparsers.add_parser(CMD_SENTENCECASE, help='change selected text to Sentence case: ab cd -> Ab cd')
        sentenceParser.add_argument('file', nargs='*', default='.', help='file or folder')
        # fill
        fillParser = subparsers.add_parser(CMD_FILL, help='Fill the selected text with CHAR until they have the same width: 1, 100 -> 001, 100')
        fillParser.add_argument('-w', dest='width', type=int, help='set the width of the text')
        fillParser.add_argument('-e', action='store_true', dest='end', help='add TEXT at the end')
        fillParser.add_argument('char', help='the fill character')
        fillParser.add_argument('file', nargs='*', default='.', help='file or folder')
        # swap
        swapParser = subparsers.add_parser(CMD_SWAP, help='swap selected text by separator: a_b -> b_a')
        swapParser.add_argument('-l', action='store_true', dest='left', help='separator belongs to left part')
        swapParser.add_argument('-r', action='store_true', dest='right', help='separator belongs to right part')
        swapParser.add_argument('separator', help='the separator')
        swapParser.add_argument('file', nargs='*', default='.', help='file or folder')
        # number
        numberParser = subparsers.add_parser(CMD_NUMBER, help='add numbering before/after selected text: a, b -> 01-a, 02-b')
        numberParser.add_argument('-e', action='store_true', dest='end', help='add NUMBER at the end')
        numberParser.add_argument('-b', dest='before', help='add TEXT before NUMBER')
        numberParser.add_argument('-a', dest='after', help='add TEXT after NUMBER')
        numberParser.add_argument('-w', dest='width', type=int, help='set the width of NUMBER, e.g. 2: 01,02,03 / 3: 001,002,003')
        numberParser.add_argument('-s', dest='start', type=int, default=1, help='start index (default: 1)')
        numberParser.add_argument('-i', dest='increment', type=int, default=1, help='step size (default: 1)')
        numberParser.add_argument('--no-reset', action='store_true', dest='noReset', help='avoid restart for each folder')
        numberParser.add_argument('file', nargs='*', default='.', help='file or folder')
        # cut
        cutParser = subparsers.add_parser(CMD_CUT, help='cut the selected text at the beginning/end: ABcd -> cd')
        cutParser.add_argument('-e', action='store_true', dest='end', help='cut TEXT at the end')
        cutParser.add_argument('index', type=int, help='number characters to cut')
        cutParser.add_argument('file', nargs='*', default='.', help='file or folder')
        # keep
        keepParser = subparsers.add_parser(CMD_KEEP, help='keep the selected text at the beginning/end, rest will be deleted: abC, deFG -> ab, de')
        keepParser.add_argument('-e', action='store_true', dest='end', help='keep TEXT at the end')
        keepParser.add_argument('index', type=int, help='number characters to keep')
        keepParser.add_argument('file', nargs='*', default='.', help='file or folder')
        # dir
        dirParser = subparsers.add_parser(CMD_DIR, help='move the matching files to DIR: abc -> dir/abc')
        dirParser.add_argument('dir', help='the target directory')
        dirParser.add_argument('file', nargs='*', default='.', help='file or folder')
        
        args = parser.parse_args(argv)
        
        # init logging
        level = logging.DEBUG if args.debug else logging.WARNING
        logging.basicConfig(format='%(levelname)s: %(message)s', level=level, force=True)
        
        # get files
        files = getPaths(args.file, recursive=args.recursive, dirOnly=args.dirOnly)
        files = sorted(files)
        
        # init parser
        parser = FilenameParser()
        parser.init(args)
        
        # create renamer
        renamers = []
        for file in files:
            path = Path(file).resolve()
            tokens = parser.getTokens(path, args)
            renamer = FileRenamer(path, tokens)
            renamers.append(renamer)
        
        command = getCommand(args, renamers)
        for renamer in renamers:
            command(renamer, args)

        if args.command in (CMD_TEST):
            return

        if args.simulate:
            deletedFiles = []
            createdFiles = []
            while True:
                fileRenamed = False
                for f in renamers:
                    fileRenamed |= f.renameDryRun(deletedFiles, createdFiles)
                    if fileRenamed:
                        deletedFiles.append(f.getSrcFile())
                        createdFiles.append(f.getDstFile())
                if not fileRenamed:
                    break

            # check if all files could be renamed
            for f in renamers:
                if not f.done:
                    print(f'{ANSI_RED}{f.getSrcFile()}: Renaming failed to {f.getDstFile()}{ANSI_END}')
        else:
            # rename files
            while True:
                # repeat until no file could be renamed anymore
                fileRenamed = False
                for f in renamers:
                    fileRenamed |= f.rename(args)
                if not fileRenamed:
                    break

            # check if all files could be renamed
            failed = False
            for f in renamers:
                if not f.done:
                    print(f'{ANSI_RED}{f.getSrcFile()}: Renaming failed to {f.getDstFile()}{ANSI_END}')
                    failed = True
            if failed:
                exit(2)

    except Exception as e:
        print(e)
        logging.debug(type(e))
        if args.debug:
            traceback.print_exc()
        exit(1)

if __name__ == '__main__':
    main()

