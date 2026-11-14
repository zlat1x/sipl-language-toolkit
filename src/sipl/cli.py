"""Stable command-line and JSON interface (schema version 1.0)."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from . import ast as a
from .conformance import run_suite
from .diagnostics import SIPLError
from .interpreter import ExecutionFailure, execute
from .parser import parse
from .semantics import SemanticEvaluationFailure, build, display, evaluate, to_data as term_data
from .visualization import from_ast, to_data as tree_data, to_dot, to_svg, to_text

VERSION = "1.0"


def parse_state(raw: str | None, assignments: list[str]) -> dict[str, int]:
    state = {}
    if raw:
        try:
            value = json.loads(raw)
        except json.JSONDecodeError as error:
            raise ValueError(f"Invalid --state JSON: {error.msg}") from error
        if not isinstance(value, dict):
            raise ValueError("--state must be a JSON object")
        state.update(value)
    for pair in assignments:
        name, separator, value = pair.partition("=")
        if not separator or not name.isidentifier() or not name.isascii():
            raise ValueError(f"Invalid --var {pair!r}; use NAME=INTEGER")
        try:
            state[name] = int(value)
        except ValueError as error:
            raise ValueError(f"Invalid integer in --var {pair!r}") from error
    if any(not isinstance(name, str) or not name.isidentifier() or not name.isascii()
           or name in {"begin", "end", "skip", "if", "then", "else", "while", "do"}
           or not isinstance(number, int) or isinstance(number, bool)
           for name, number in state.items()):
        raise ValueError("State variable names must be SIPL identifiers and values must be integers")
    return state


def argument_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="sipl", description="SIPL Language Toolkit")
    parser.add_argument("command", choices=["parse", "check", "run", "trace", "tree", "term", "eval-term", "conformance"])
    parser.add_argument("file", type=Path, help="SIPL source file, or conformance cases directory")
    parser.add_argument("--json", action="store_true", help="Emit envelope conforming to docs/json-api.md")
    parser.add_argument("--state", help='Initial state JSON, e.g. \'{"X":5,"Y":2}\'')
    parser.add_argument("--var", action="append", default=[], metavar="NAME=INTEGER", help="Initial variable; repeatable")
    parser.add_argument("--max-steps", type=int, default=10_000)
    parser.add_argument("--format", choices=["text", "json", "dot", "svg"], default="text", help="Tree output format")
    return parser


def envelope(command: str, ok: bool, data: object = None, diagnostics: list[dict] | None = None) -> dict:
    return {"schema_version": VERSION, "command": command, "ok": ok,
            "data": data, "diagnostics": diagnostics or []}


def main(argv: list[str] | None = None) -> int:
    parser = argument_parser()
    args = parser.parse_args(argv)
    try:
        if args.max_steps < 1:
            raise ValueError("--max-steps must be positive")
        if args.command == "conformance":
            suite = run_suite(args.file)
            ok = suite["passed"] == suite["total"]
            if args.json:
                print(json.dumps(envelope(args.command, ok, suite), ensure_ascii=False, indent=2))
            else:
                print(f"Conformance: {suite['passed']}/{suite['total']} passed")
                for item in suite["results"]:
                    print(f"{'PASS' if item['passed'] else 'FAIL'} {item['case']}: {item['message']}")
            return 0 if ok else 1
        source = args.file.read_text(encoding="utf-8-sig")
        program = parse(source)
        if args.command == "parse":
            payload = a.to_data(program)
            output = json.dumps(payload, ensure_ascii=False, indent=2)
        elif args.command == "check":
            payload = {"valid": True, "nodes": _node_count(program)}
            output = f"Syntax OK ({payload['nodes']} AST nodes)"
        elif args.command == "tree":
            tree = from_ast(program, source)
            payload = tree_data(tree)
            outputs = {"text": lambda: to_text(tree), "json": lambda: json.dumps(payload, ensure_ascii=False, indent=2),
                       "dot": lambda: to_dot(tree), "svg": lambda: to_svg(tree)}
            output = outputs[args.format]()
        elif args.command == "term":
            term = build(program)
            payload = {"text": display(term), "tree": term_data(term)}
            output = payload["text"]
        elif args.command in {"run", "trace", "eval-term"}:
            state = parse_state(args.state, args.var)
            if args.command == "eval-term":
                result = evaluate(build(program), state, args.max_steps)
                payload = {"state": result.state, "steps": result.steps, "transitions": result.transitions}
                output = f"Final state: {json.dumps(result.state, ensure_ascii=False)}\nRules: {len(result.transitions)}"
            else:
                result = execute(program, state, args.max_steps)
                payload = {"state": result.state, "steps": result.steps}
                if args.command == "trace":
                    payload["events"] = result.events
                    output = "\n".join(f"{x['step']:>5}  {x['event']:<20} {x['state']} {x['detail']}" for x in result.events)
                else:
                    output = f"Final state: {json.dumps(result.state, ensure_ascii=False)} (steps: {result.steps})"
        else:
            raise AssertionError(args.command)
        if args.json:
            print(json.dumps(envelope(args.command, True, payload), ensure_ascii=False, indent=2))
        else:
            print(output)
        return 0
    except SIPLError as error:
        partial = None
        if isinstance(error, SemanticEvaluationFailure):
            partial = {"state": None, "steps": error.steps, "transitions": error.transitions}
        elif isinstance(error, ExecutionFailure):
            partial = {"state": error.state, "steps": error.steps}
            if args.command == "trace":
                partial["events"] = error.events
        return _report(args.command, args.json, error.diagnostic.to_dict(),
                       2 if error.diagnostic.code in {"E_LEX", "E_PARSE"} else 3, partial)
    except (OSError, UnicodeError, ValueError) as error:
        code = "E_INPUT"
        diagnostic = {"code": code, "message": str(error), "span": None}
        return _report(args.command, args.json, diagnostic, 4)


def _node_count(node: a.Node) -> int:
    return 1 + sum(_node_count(child) for child in a.children(node))


def _report(command: str, structured: bool, diagnostic: dict, code: int, partial: object = None) -> int:
    if structured:
        print(json.dumps(envelope(command, False, partial, [diagnostic]), ensure_ascii=False, indent=2))
    else:
        pos = diagnostic.get("span")
        loc = f"{pos['start']['line']}:{pos['start']['column']}: " if pos else ""
        print(f"{loc}{diagnostic['code']}: {diagnostic['message']}", file=sys.stderr)
    return code


if __name__ == "__main__":
    raise SystemExit(main())
