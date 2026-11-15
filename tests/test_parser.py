from pathlib import Path
import pytest
from sipl import ast as a
from sipl.diagnostics import SIPLError
from sipl.lexer import tokenize
from sipl.parser import parse


POSITIVE = [
    "begin skip end",
    "begin X := 1 end",
    "begin X := -7 end",
    "begin X := 1; Y := 2 end",
    "begin begin skip end end",
    "begin if N > 0 then X := 1 else X := 2 end",
    "begin while N > 0 do N := N - 1 end",
    "begin X := (1 + 2) * 3 end",
    "begin if ¬(A = B) then skip else skip end",
    "begin if A > 0 ∨ B = 0 then skip else skip end",
    "begin if (A + 2) > B then skip else skip end",
    "begin if A > 0 then if B > 0 then X := 1 else X := 2 else X := 3 end",
    "begin if !(A = 0) | B > 3 then skip else skip end",
    "begin A := 3; while A > 0 do begin A := A - 1; skip end end",
]
NEGATIVE = [
    "", "skip", "begin end", "begin X = 1 end", "begin X := ; end",
    "begin skip; end", "begin ;skip end", "begin skip;;skip end",
    "begin if A > 0 then skip end", "begin while A > 0 skip end",
    "begin X := 1 + end", "begin X := 1 * end", "begin X := (1 + 2 end",
    "begin if A < 0 then skip else skip end", "begin X := 2 / 3 end",
    "begin if A then skip else skip end", "begin $ := 1 end",
    "begin if (A > 0 then skip else skip end", "begin skip end end",
]


@pytest.mark.parametrize("source", POSITIVE)
def test_valid_grammar(source):
    assert isinstance(parse(source), a.Program)


@pytest.mark.parametrize("source", NEGATIVE)
def test_invalid_grammar(source):
    with pytest.raises(SIPLError) as caught:
        parse(source)
    assert caught.value.diagnostic.code in {"E_LEX", "E_PARSE"}
    assert caught.value.diagnostic.span.start.line >= 1
    assert caught.value.diagnostic.span.start.column >= 1


def test_precedence_and_associativity():
    root = parse("begin X := 10 - 3 - 2 * 2 end")
    outer = root.body.value
    assert isinstance(outer, a.Binary) and outer.op == "-"
    assert isinstance(outer.left, a.Binary) and outer.left.op == "-"
    assert isinstance(outer.right, a.Binary) and outer.right.op == "*"


def test_source_positions():
    root = parse("begin\n  X := 42\nend")
    assert (root.body.span.start.line, root.body.span.start.column) == (2, 3)
    assert (root.body.value.span.start.line, root.body.value.span.start.column) == (2, 8)
    assert root.body.value.span.end.column == 10
    assert root.span.end.line == 3


def test_lexer_positions_negative_literal():
    tokens = tokenize("begin X := -12 end")
    assert [(v.kind, v.text) for v in tokens][3:5] == [("MINUS", "-"), ("NUMBER", "12")]


def test_lark_machine_readable_grammar():
    lark = pytest.importorskip("lark")
    grammar = (Path(__file__).parents[1] / "grammar" / "sipl.lark").read_text()
    checker = lark.Lark(grammar, parser="earley")
    for source in POSITIVE:
        checker.parse(source)
    # The reference grammar should also reject a representative sample.
    for source in ["skip", "begin end", "begin X := ; end", "begin X := 2 / 3 end"]:
        with pytest.raises(lark.exceptions.LarkError):
            checker.parse(source)
