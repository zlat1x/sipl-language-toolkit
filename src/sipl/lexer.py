"""SIPL lexical analysis. Positions are 1-based; offsets are 0-based."""
from __future__ import annotations

from dataclasses import dataclass
from .ast import Position, SourceSpan
from .diagnostics import Diagnostic, SIPLError

KEYWORDS = frozenset({"begin", "end", "skip", "if", "then", "else", "while", "do"})
SINGLE = {";": "SEMI", ":": "COLON", "=": "EQ", ">": "GT", "+": "PLUS", "-": "MINUS",
          "*": "STAR", "(": "LPAREN", ")": "RPAREN", "∨": "OR", "|": "OR", "¬": "NOT", "!": "NOT"}


@dataclass(frozen=True, slots=True)
class Token:
    kind: str
    text: str
    span: SourceSpan


def tokenize(source: str) -> list[Token]:
    tokens: list[Token] = []
    index = 0
    line, column = 1, 1
    length = len(source)
    while index < length:
        char = source[index]
        if char.isspace():
            if char == "\n":
                line += 1
                column = 1
            else:
                column += 1
            index += 1
            continue
        start = Position(line, column, index)
        if char.isascii() and (char.isalpha() or char == "_"):
            j = index + 1
            while j < length and source[j].isascii() and (source[j].isalnum() or source[j] == "_"):
                j += 1
            raw = source[index:j]
            kind = raw.upper() if raw in KEYWORDS else "IDENT"
        elif char in "0123456789":
            j = index + 1
            while j < length and source[j] in "0123456789":
                j += 1
            raw, kind = source[index:j], "NUMBER"
        elif source.startswith(":=", index):
            raw, kind = ":=", "ASSIGN"
        elif char in SINGLE and char != ":":
            raw, kind = char, SINGLE[char]
        else:
            end = Position(line, column + 1, index + 1)
            raise SIPLError(Diagnostic("E_LEX", f"Unexpected character {char!r}", SourceSpan(start, end)))
        end = Position(line, column + len(raw), index + len(raw))
        tokens.append(Token(kind, raw, SourceSpan(start, end)))
        index += len(raw)
        column += len(raw)
    pos = Position(line, column, index)
    tokens.append(Token("EOF", "", SourceSpan(pos, pos)))
    return tokens
