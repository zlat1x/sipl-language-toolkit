"""Concrete operational SIPL semantics and reusable event stream."""
from __future__ import annotations

from dataclasses import dataclass, field
from .. import ast as a
from ..diagnostics import Diagnostic, SIPLError


class ExecutionFailure(SIPLError):
    """Runtime failure carrying the complete diagnostic and partial event history."""

    def __init__(self, diagnostic: Diagnostic, state: dict[str, int], steps: int, events: list[dict]):
        super().__init__(diagnostic)
        self.state = dict(sorted(state.items()))
        self.steps = steps
        self.events = list(events)


@dataclass(slots=True)
class ExecutionResult:
    state: dict[str, int]
    steps: int
    events: list[dict] = field(default_factory=list)


class Interpreter:
    def __init__(self, state: dict[str, int] | None = None, max_steps: int = 10_000):
        if max_steps <= 0:
            raise ValueError("max_steps must be positive")
        self.state = dict(state or {})
        if any(not isinstance(k, str) or not isinstance(v, int) or isinstance(v, bool)
               for k, v in self.state.items()):
            raise ValueError("State must map variable names to integers")
        self.max_steps = max_steps
        self.steps = 0
        self.events: list[dict] = []

    def emit(self, event: str, node: a.Node, **detail: object) -> None:
        self.events.append({"event": event, "step": self.steps, "span": a.to_data(node.span),
                            "state": dict(sorted(self.state.items())), "detail": detail})

    def arithmetic(self, node: a.Node) -> int:
        if isinstance(node, a.Number):
            return node.value
        if isinstance(node, a.Variable):
            if node.name not in self.state:
                raise SIPLError(Diagnostic("E_UNDEFINED", f"Variable {node.name!r} is undefined", node.span))
            return self.state[node.name]
        if isinstance(node, a.Binary):
            lhs, rhs = self.arithmetic(node.left), self.arithmetic(node.right)
            return {"+": lambda: lhs + rhs, "-": lambda: lhs - rhs, "*": lambda: lhs * rhs}[node.op]()
        raise TypeError(type(node))

    def condition(self, node: a.Node) -> bool:
        if isinstance(node, a.Comparison):
            left, right = self.arithmetic(node.left), self.arithmetic(node.right)
            return left == right if node.op == "=" else left > right
        if isinstance(node, a.Not):
            return not self.condition(node.operand)
        if isinstance(node, a.Or):
            left = self.condition(node.left)
            right = self.condition(node.right)
            return left or right
        raise TypeError(type(node))

    def tick(self, node: a.Node) -> None:
        if self.steps >= self.max_steps:
            raise SIPLError(Diagnostic("E_STEP_LIMIT", f"Execution exceeded {self.max_steps} steps", node.span))
        self.steps += 1
        self.emit("BeforeStatement", node, kind=type(node).__name__)

    def statement(self, node: a.Node) -> None:
        self.tick(node)
        if isinstance(node, a.Assign):
            value = self.arithmetic(node.value)
            before = self.state.get(node.name)
            self.state[node.name] = value
            self.emit("VariableChanged", node, name=node.name, old=before, new=value)
        elif isinstance(node, a.Sequence):
            for item in node.statements:
                self.statement(item)
        elif isinstance(node, a.Block):
            self.statement(node.body)
        elif isinstance(node, a.Skip):
            pass
        elif isinstance(node, a.If):
            decision = self.condition(node.condition)
            self.emit("ConditionEvaluated", node.condition, value=decision)
            self.statement(node.then_branch if decision else node.else_branch)
        elif isinstance(node, a.While):
            while True:
                # Count repeat condition evaluations, including the terminating false one.
                if self.steps >= self.max_steps:
                    raise SIPLError(Diagnostic("E_STEP_LIMIT", f"Execution exceeded {self.max_steps} steps", node.span))
                self.steps += 1
                decision = self.condition(node.condition)
                self.emit("ConditionEvaluated", node.condition, value=decision)
                if not decision:
                    break
                self.statement(node.body)
        else:
            raise TypeError(type(node))
        self.emit("AfterStatement", node, kind=type(node).__name__)

    def run(self, program: a.Program) -> ExecutionResult:
        try:
            self.statement(program.body)
            self.emit("Completed", program, status="ok")
        except SIPLError as error:
            self.emit("ExecutionError", program, diagnostic=error.diagnostic.to_dict())
            raise ExecutionFailure(error.diagnostic, self.state, self.steps, self.events) from error
        return ExecutionResult(dict(sorted(self.state.items())), self.steps, self.events)


def execute(program: a.Program, state: dict[str, int] | None = None, max_steps: int = 10_000) -> ExecutionResult:
    return Interpreter(state, max_steps).run(program)
