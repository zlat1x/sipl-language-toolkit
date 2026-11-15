import json
import xml.etree.ElementTree as ET
from sipl.lexer import tokenize
from sipl.parser import parse
from sipl.visualization import from_ast, to_data, to_dot, to_text, to_svg


def leaf_labels(node):
    if not node.children:
        return [node.label]
    return [value for child in node.children for value in leaf_labels(child)]


def test_concrete_tree_exact_source_token_sequence():
    source = "begin X := (1 + 2) * 3; if X > 1 then skip else X := 0 end"
    tree = from_ast(parse(source), source)
    leaves = leaf_labels(tree)
    actual = [label.split(": ", 1)[1] for label in leaves]
    assert actual == [token.text for token in tokenize(source)[:-1]]


def test_formats_and_spans():
    source = "begin\n X := 2\nend"
    tree = from_ast(parse(source), source)
    data = to_data(tree)
    assert data["span"]["start"]["line"] == 1
    assert "S / Assignment" in to_text(tree)
    assert "digraph SIPL" in to_dot(tree)
    assert 'tooltip="2:2"' in to_dot(tree)
    svg = to_svg(tree)
    parsed = ET.fromstring(svg)
    assert parsed.tag.endswith("svg")
    assert "2:2" in svg
    assert json.loads(json.dumps(data))["label"].startswith("P")


def test_not_and_or_concrete_tree():
    source = "begin if ¬(X > 0) ∨ Y = 2 then skip else skip end"
    tree = from_ast(parse(source), source)
    actual = [label.split(": ", 1)[1] for label in leaf_labels(tree)]
    assert actual == [t.text for t in tokenize(source)[:-1]]
