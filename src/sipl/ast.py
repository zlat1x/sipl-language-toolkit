"""Immutable SIPL abstract syntax nodes and source locations."""
from __future__ import annotations

from dataclasses import dataclass, fields


@dataclass(frozen=True, slots=True)
class Position:
    line: int
    column: int
    offset: int


@dataclass(frozen=True, slots=True)
class SourceSpan:
    start: Position
    end: Position


@dataclass(frozen=True, slots=True)
class Node:
    span: SourceSpan


@dataclass(frozen=True, slots=True)
class Number(Node):
    value: int


@dataclass(frozen=True, slots=True)
class Variable(Node):
    name: str


@dataclass(frozen=True, slots=True)
class Binary(Node):
    op: str
    left: Node
    right: Node


@dataclass(frozen=True, slots=True)
class Comparison(Node):
    op: str
    left: Node
    right: Node


@dataclass(frozen=True, slots=True)
class Not(Node):
    operand: Node


@dataclass(frozen=True, slots=True)
class Or(Node):
    left: Node
    right: Node


@dataclass(frozen=True, slots=True)
class Assign(Node):
    name: str
    value: Node


@dataclass(frozen=True, slots=True)
class Sequence(Node):
    statements: tuple[Node, ...]


@dataclass(frozen=True, slots=True)
class If(Node):
    condition: Node
    then_branch: Node
    else_branch: Node


@dataclass(frozen=True, slots=True)
class While(Node):
    condition: Node
    body: Node


@dataclass(frozen=True, slots=True)
class Skip(Node):
    pass


@dataclass(frozen=True, slots=True)
class Block(Node):
    body: Node


@dataclass(frozen=True, slots=True)
class Program(Node):
    body: Node


def source_span(start: Node | SourceSpan, end: Node | SourceSpan) -> SourceSpan:
    first = start.span if isinstance(start, Node) else start
    last = end.span if isinstance(end, Node) else end
    return SourceSpan(first.start, last.end)


def children(node: Node) -> tuple[Node, ...]:
    result: list[Node] = []
    for field in fields(node):
        value = getattr(node, field.name)
        if isinstance(value, Node):
            result.append(value)
        elif isinstance(value, tuple):
            result.extend(item for item in value if isinstance(item, Node))
    return tuple(result)


def to_data(value: object) -> object:
    if isinstance(value, (Node, Position, SourceSpan)):
        data = {f.name: to_data(getattr(value, f.name)) for f in fields(value)}
        if isinstance(value, Node):
            return {"kind": type(value).__name__, **data}
        return data
    if isinstance(value, tuple):
        return [to_data(v) for v in value]
    return value


def shape(node: Node) -> object:
    """Stable span-free AST shape for conformance tests."""
    value = to_data(node)
    def strip(item: object) -> object:
        if isinstance(item, list):
            return [strip(v) for v in item]
        if isinstance(item, dict):
            return {k: strip(v) for k, v in item.items() if k != "span"}
        return item
    return strip(value)
