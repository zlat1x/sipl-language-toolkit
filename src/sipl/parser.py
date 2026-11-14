"""Recursive-descent SIPL parser with explicit precedence and typed AST."""
from __future__ import annotations

from dataclasses import replace
from . import ast as a
from .diagnostics import Diagnostic, SIPLError
from .lexer import Token, tokenize


class Parser:
    def __init__(self, source: str):
        self.tokens = tokenize(source)
        self.index = 0

    def peek(self) -> Token:
        return self.tokens[self.index]

    def take(self, kind: str) -> Token:
        token = self.peek()
        if token.kind != kind:
            expected = kind.lower()
            got = repr(token.text) if token.text else "end of input"
            raise SIPLError(Diagnostic("E_PARSE", f"Expected {expected}, got {got}", token.span))
        self.index += 1
        return token

    def match(self, kind: str) -> Token | None:
        if self.peek().kind == kind:
            return self.take(kind)
        return None

    def parse(self) -> a.Program:
        begin = self.take("BEGIN")
        body = self.sequence({"END"})
        end = self.take("END")
        self.take("EOF")
        return a.Program(a.SourceSpan(begin.span.start, end.span.end), body)

    def sequence(self, end_tokens: set[str]) -> a.Node:
        if self.peek().kind in end_tokens | {"EOF", "ELSE"}:
            raise SIPLError(Diagnostic("E_PARSE", "Expected a statement", self.peek().span))
        items = [self.statement()]
        while self.match("SEMI"):
            if self.peek().kind in end_tokens | {"EOF", "ELSE", "SEMI"}:
                raise SIPLError(Diagnostic("E_PARSE", "Expected a statement after ';'", self.peek().span))
            items.append(self.statement())
        if len(items) == 1:
            return items[0]
        return a.Sequence(a.source_span(items[0], items[-1]), tuple(items))

    def statement(self) -> a.Node:
        token = self.peek()
        if token.kind == "IDENT":
            name = self.take("IDENT")
            self.take("ASSIGN")
            value = self.arithmetic()
            return a.Assign(a.SourceSpan(name.span.start, value.span.end), name.text, value)
        if token.kind == "SKIP":
            return a.Skip(self.take("SKIP").span)
        if token.kind == "BEGIN":
            begin = self.take("BEGIN")
            body = self.sequence({"END"})
            end = self.take("END")
            return a.Block(a.SourceSpan(begin.span.start, end.span.end), body)
        if token.kind == "IF":
            first = self.take("IF")
            condition = self.condition()
            self.take("THEN")
            then_branch = self.statement()
            self.take("ELSE")
            else_branch = self.statement()
            return a.If(a.SourceSpan(first.span.start, else_branch.span.end), condition, then_branch, else_branch)
        if token.kind == "WHILE":
            first = self.take("WHILE")
            condition = self.condition()
            self.take("DO")
            body = self.statement()
            return a.While(a.SourceSpan(first.span.start, body.span.end), condition, body)
        raise SIPLError(Diagnostic("E_PARSE", "Expected assignment, skip, begin, if or while", token.span))

    def arithmetic(self, min_precedence: int = 0) -> a.Node:
        token = self.peek()
        if token.kind == "NUMBER":
            raw = self.take("NUMBER")
            node: a.Node = a.Number(raw.span, int(raw.text))
        elif token.kind == "MINUS":
            first = self.take("MINUS")
            number = self.take("NUMBER")
            node = a.Number(a.SourceSpan(first.span.start, number.span.end), -int(number.text))
        elif token.kind == "IDENT":
            raw = self.take("IDENT")
            node = a.Variable(raw.span, raw.text)
        elif token.kind == "LPAREN":
            open_tok = self.take("LPAREN")
            inner = self.arithmetic()
            close = self.take("RPAREN")
            node = replace(inner, span=a.SourceSpan(open_tok.span.start, close.span.end))
        else:
            raise SIPLError(Diagnostic("E_PARSE", "Expected an arithmetic expression", token.span))
        operators = {"PLUS": (1, "+"), "MINUS": (1, "-"), "STAR": (2, "*")}
        while self.peek().kind in operators:
            precedence, symbol = operators[self.peek().kind]
            if precedence < min_precedence:
                break
            self.index += 1
            right = self.arithmetic(precedence + 1)
            node = a.Binary(a.source_span(node, right), symbol, node, right)
        return node

    def condition(self) -> a.Node:
        node = self.negation()
        while self.match("OR"):
            right = self.negation()
            node = a.Or(a.source_span(node, right), node, right)
        return node

    def negation(self) -> a.Node:
        if self.peek().kind == "NOT":
            token = self.take("NOT")
            inner = self.negation()
            return a.Not(a.SourceSpan(token.span.start, inner.span.end), inner)
        if self.peek().kind == "LPAREN":
            saved = self.index
            try:
                return self.comparison()
            except SIPLError:
                self.index = saved
                opening = self.take("LPAREN")
                inner = self.condition()
                closing = self.take("RPAREN")
                return replace(inner, span=a.SourceSpan(opening.span.start, closing.span.end))
        return self.comparison()

    def comparison(self) -> a.Comparison:
        left = self.arithmetic()
        raw = self.peek()
        if raw.kind not in {"EQ", "GT"}:
            raise SIPLError(Diagnostic("E_PARSE", "Expected '=' or '>' in a condition", raw.span))
        self.index += 1
        right = self.arithmetic()
        return a.Comparison(a.source_span(left, right), raw.text, left, right)


def parse(source: str) -> a.Program:
    return Parser(source).parse()
