"""Denotational SIPL terms following the course algebra AS, S, IF, WH, id."""
from __future__ import annotations

from dataclasses import dataclass
from .. import ast as a
from ..diagnostics import Diagnostic, SIPLError


@dataclass(frozen=True, slots=True)
class Term:
    op: str
    args: tuple[object, ...]
    span: a.SourceSpan


def build(node: a.Node) -> Term:
    if isinstance(node, (a.Program, a.Block)):
        return build(node.body)
    if isinstance(node, a.Number):
        return Term("const", (node.value,), node.span)
    if isinstance(node, a.Variable):
        return Term("read", (node.name,), node.span)
    if isinstance(node, a.Binary):
        return Term("super", ({"+": "add", "-": "sub", "*": "mult"}[node.op],
                              build(node.left), build(node.right)), node.span)
    if isinstance(node, a.Comparison):
        return Term("super", ({"=": "eq", ">": "gr"}[node.op],
                              build(node.left), build(node.right)), node.span)
    if isinstance(node, a.Or):
        return Term("super", ("or", build(node.left), build(node.right)), node.span)
    if isinstance(node, a.Not):
        return Term("super", ("neg", build(node.operand)), node.span)
    if isinstance(node, a.Assign):
        return Term("assign", (node.name, build(node.value)), node.span)
    if isinstance(node, a.Sequence):
        terms = [build(item) for item in node.statements]
        term = terms[0]
        for second in terms[1:]:
            term = Term("seq", (term, second), a.source_span(term.span, second.span))
        return term
    if isinstance(node, a.If):
        return Term("if", (build(node.condition), build(node.then_branch), build(node.else_branch)), node.span)
    if isinstance(node, a.While):
        return Term("while", (build(node.condition), build(node.body)), node.span)
    if isinstance(node, a.Skip):
        return Term("id", (), node.span)
    raise TypeError(type(node))


def to_data(term: Term) -> dict:
    return {"op": term.op, "args": [to_data(v) if isinstance(v, Term) else v for v in term.args],
            "span": a.to_data(term.span)}


def display(term: Term) -> str:
    op, args = term.op, term.args
    if op == "const":
        return str(args[0])
    if op == "read":
        return f"{args[0]}⇒"
    if op == "super":
        return f"S^{len(args)-1}({args[0]}, {', '.join(display(x) for x in args[1:])})"
    if op == "assign":
        return f"AS^{args[0]}({display(args[1])})"
    if op == "seq":
        return f"({display(args[0])} · {display(args[1])})"
    if op == "if":
        return f"IF({', '.join(display(v) for v in args)})"
    if op == "while":
        return f"WH({display(args[0])}, {display(args[1])})"
    if op == "id":
        return "id"
    raise ValueError(op)


class SemanticEvaluationFailure(SIPLError):
    """Undefined semantic evaluation with its already-applied rule trace."""

    def __init__(self, diagnostic: Diagnostic, steps: int, transitions: list[dict]):
        super().__init__(diagnostic)
        self.steps = steps
        self.transitions = list(transitions)


@dataclass(slots=True)
class SemanticResult:
    state: dict[str, int]
    steps: int
    transitions: list[dict]


class Evaluator:
    """Separate evaluator of semantic terms, independent of AST interpreter."""
    def __init__(self, max_steps: int = 10_000):
        if max_steps <= 0:
            raise ValueError("max_steps must be positive")
        self.limit = max_steps
        self.steps = 0
        self.transitions: list[dict] = []

    def record(self, rule: str, term: Term, before: dict[str, int], after: dict[str, int] | None = None,
               **detail: object) -> None:
        self.transitions.append({"rule": rule, "term": display(term), "span": a.to_data(term.span),
                                 "before": dict(sorted(before.items())),
                                 "after": dict(sorted(after.items())) if after is not None else None,
                                 "detail": detail})

    def value(self, term: Term, state: dict[str, int]) -> int | bool:
        if term.op == "const":
            result = term.args[0]
            self.record("AF_CONST", term, state, value=result)
            return result
        if term.op == "read":
            name = term.args[0]
            if name not in state:
                raise SIPLError(Diagnostic("E_UNDEFINED", f"Variable {name!r} is undefined", term.span))
            result = state[name]
            self.record("AF_DNM", term, state, value=result)
            return result
        if term.op == "super":
            name = term.args[0]
            operands = [self.value(part, state) for part in term.args[1:]]
            operations = {"add": lambda v: v[0] + v[1], "sub": lambda v: v[0] - v[1],
                          "mult": lambda v: v[0] * v[1], "eq": lambda v: v[0] == v[1],
                          "gr": lambda v: v[0] > v[1], "or": lambda v: v[0] or v[1],
                          "neg": lambda v: not v[0]}
            result = operations[name](operands)
            self.record("AF_S", term, state, operator=name, operands=operands, value=result)
            return result
        raise TypeError(f"Expected an expression term, got {term.op}")

    def tick(self, term: Term) -> None:
        if self.steps >= self.limit:
            raise SIPLError(Diagnostic("E_STEP_LIMIT", f"Semantic evaluation exceeded {self.limit} steps", term.span))
        self.steps += 1

    def statement(self, term: Term, state: dict[str, int]) -> dict[str, int]:
        self.tick(term)
        if term.op == "id":
            after = dict(state)
            self.record("AF_ID", term, state, after)
            return after
        if term.op == "assign":
            value = self.value(term.args[1], state)
            after = {**state, term.args[0]: value}
            self.record("AF_AS", term, state, after, variable=term.args[0], value=value)
            return after
        if term.op == "seq":
            middle = self.statement(term.args[0], state)
            after = self.statement(term.args[1], middle)
            self.record("AF_SEQ", term, state, after, middle=middle)
            return after
        if term.op == "if":
            decision = self.value(term.args[0], state)
            after = self.statement(term.args[1] if decision else term.args[2], state)
            self.record("AF_IF", term, state, after, condition=decision)
            return after
        if term.op == "while":
            current = dict(state)
            iterations = 0
            while True:
                self.tick(term)
                condition = self.value(term.args[0], current)
                if not condition:
                    self.record("AF_WH", term, state, current, iterations=iterations, condition=False)
                    return current
                prior = current
                current = self.statement(term.args[1], current)
                self.record("AF_WH_ITER", term, prior, current, iteration=iterations + 1, condition=True)
                iterations += 1
        raise TypeError(f"Expected statement term, got {term.op}")

    def evaluate(self, term: Term, state: dict[str, int] | None = None) -> SemanticResult:
        initial = dict(state or {})
        if any(not isinstance(name, str) or not isinstance(value, int) or isinstance(value, bool)
               for name, value in initial.items()):
            raise ValueError("State must map names to integers")
        try:
            final_state = self.statement(term, initial)
        except SIPLError as error:
            self.record("AF_UNDEFINED", term, initial, diagnostic=error.diagnostic.to_dict())
            raise SemanticEvaluationFailure(error.diagnostic, self.steps, self.transitions) from error
        return SemanticResult(dict(sorted(final_state.items())), self.steps, self.transitions)


def evaluate(term: Term, state: dict[str, int] | None = None, max_steps: int = 10_000) -> SemanticResult:
    return Evaluator(max_steps).evaluate(term, state)
