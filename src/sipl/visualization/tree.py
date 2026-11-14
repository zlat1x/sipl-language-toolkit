"""Concrete parse-tree exporters with true source token leaves and spans."""
from __future__ import annotations

from dataclasses import dataclass
from html import escape
from .. import ast as a
from ..lexer import tokenize


@dataclass(frozen=True, slots=True)
class TreeNode:
    label: str
    span: a.SourceSpan
    children: tuple["TreeNode", ...] = ()


CATEGORIES = {
    "Program": "P / Program", "Assign": "S / Assignment", "Sequence": "S / Sequence",
    "If": "S / Conditional", "While": "S / Loop", "Skip": "S / Skip", "Block": "S / Block",
    "Number": "a / Number", "Variable": "a / Variable", "Binary": "a / Expression",
    "Comparison": "b / Comparison", "Not": "b / Negation", "Or": "b / Disjunction",
}


def from_ast(program: a.Program, source: str) -> TreeNode:
    """Derive a concrete hierarchy by inserting every source token into AST intervals."""
    tokens = tokenize(source)[:-1]

    def recurse(node: a.Node) -> TreeNode:
        descendants = sorted(a.children(node), key=lambda child: child.span.start.offset)
        result: list[TreeNode] = []
        position = node.span.start.offset
        for child in descendants:
            if child.span.start.offset < position:
                raise ValueError("Overlapping AST spans")
            result.extend(TreeNode(f"{t.kind}: {t.text}", t.span) for t in tokens
                          if position <= t.span.start.offset < child.span.start.offset)
            result.append(recurse(child))
            position = child.span.end.offset
        result.extend(TreeNode(f"{t.kind}: {t.text}", t.span) for t in tokens
                      if position <= t.span.start.offset < node.span.end.offset)
        return TreeNode(CATEGORIES[type(node).__name__], node.span, tuple(result))

    return recurse(program)


def to_data(node: TreeNode) -> dict:
    return {"label": node.label, "span": a.to_data(node.span), "children": [to_data(v) for v in node.children]}


def to_text(node: TreeNode) -> str:
    lines: list[str] = []
    def visit(item: TreeNode, prefix: str = "", last: bool = True, root: bool = True) -> None:
        tag = "" if root else ("└── " if last else "├── ")
        pos = item.span.start
        lines.append(f"{prefix}{tag}{item.label} [{pos.line}:{pos.column}]")
        spacer = prefix + ("    " if last else "│   ") if not root else ""
        for idx, child in enumerate(item.children):
            visit(child, spacer, idx == len(item.children) - 1, False)
    visit(node)
    return "\n".join(lines)


def to_dot(node: TreeNode) -> str:
    lines = ['digraph SIPL {', '  graph [rankdir=TB, bgcolor="white"];',
             '  node [shape=box, style="rounded,filled", fillcolor="#eff6ff", fontname="Arial"];']
    counter = 0
    def visit(item: TreeNode, parent: int | None = None) -> None:
        nonlocal counter
        current = counter
        counter += 1
        label = item.label.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n")
        tip = f"{item.span.start.line}:{item.span.start.column}"
        lines.append(f'  n{current} [label="{label}", tooltip="{tip}"];')
        if parent is not None:
            lines.append(f"  n{parent} -> n{current};")
        for child in item.children:
            visit(child, current)
    visit(node)
    return "\n".join(lines + ["}"])


def to_svg(node: TreeNode) -> str:
    """Dependency-free SVG exporter: tidy subtree layout and source-span tooltips."""
    vertices: list[tuple[int, int, TreeNode]] = []
    edges: list[tuple[int, int, int, int]] = []
    unit_x, unit_y = 180, 76

    def measure(item: TreeNode) -> int:
        return max(1, sum(measure(child) for child in item.children))

    def place(item: TreeNode, start: int, depth: int, parent: tuple[int, int] | None = None) -> None:
        width = measure(item)
        x = int((start + width / 2) * unit_x)
        y = 42 + depth * unit_y
        vertices.append((x, y, item))
        if parent is not None:
            edges.append((parent[0], parent[1] + 18, x, y - 18))
        cursor = start
        for child in item.children:
            place(child, cursor, depth + 1, (x, y))
            cursor += measure(child)

    place(node, 0, 0)
    max_depth = max(y for _, y, _ in vertices) + 50
    canvas_width = max(320, measure(node) * unit_x + 20)
    xml = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {canvas_width} {max_depth}" width="{canvas_width}" height="{max_depth}" role="img" aria-label="SIPL parse tree">',
           '<rect width="100%" height="100%" fill="#ffffff"/>',
           '<g stroke="#94a3b8" stroke-width="1.5" fill="none">']
    xml += [f'<path d="M{x1},{y1} L{x2},{y2}"/>' for x1, y1, x2, y2 in edges]
    xml.append('</g><g font-family="DejaVu Sans,Arial,sans-serif" font-size="11" text-anchor="middle">')
    for x, y, item in vertices:
        label = escape(item.label)
        info = escape(f"{item.span.start.line}:{item.span.start.column}–{item.span.end.line}:{item.span.end.column}")
        xml.extend([f'<g><title>{info}: {label}</title><rect x="{x-82}" y="{y-17}" width="164" height="34" rx="7" fill="#eff6ff" stroke="#93c5fd"/>',
                    f'<text x="{x}" y="{y+4}">{label[:26]}{"…" if len(label) > 26 else ""}</text></g>'])
    xml.append('</g></svg>')
    return "\n".join(xml)
