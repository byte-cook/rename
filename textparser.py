#!/usr/bin/env python3

from enum import Enum

class TokenType(Enum):
    TEXT = 1
    PLACEHOLDER = 2
class TextToken:
    def __init__(self, type):
        self.type = type
        self.value = ''

    def isPlaceholder(self):
        return TokenType.PLACEHOLDER == self.type
    
    def isText(self):
        return TokenType.TEXT == self.type

    def __str__(self):
        return self.value

def tokenize(input, sep='|', includeSep=False):
    """
    Read input and return tokens. Tokens are enclosed by sep. Use sep twice to escape sep.
    Examples:
    "a|b"     -> syntax error: single sep is not allowed
    "ab|c|"   -> ab + |c|
    "ab||c"   -> ab + || + c
    """
    if input.count(sep) % 2 == 1:
        raise Exception(f'Syntax error: {input}')
    
    tokens = []
    t = None
    for c in input:
        if c == '|':
            if t is None:
                t = TextToken(TokenType.PLACEHOLDER)
            elif t.type == TokenType.PLACEHOLDER:
                tokens.append(t)
                t = None
            elif t.type == TokenType.TEXT:
                tokens.append(t)
                t = TextToken(TokenType.PLACEHOLDER)
        else:
            if t is None:
                t = TextToken(TokenType.TEXT)
            t.value += c
    if t is not None:
        tokens.append(t)
    
    if includeSep:
        for t in tokens:
            if t.isPlaceholder():
                t.value = sep + t.value + sep
    return tokens
    
