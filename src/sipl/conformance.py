"""Conformance runner for declarative, implementation-neutral JSON cases."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from .ast import shape
from .diagnostics import SIPLError
from .interpreter import execute
from .parser import parse


def check_case(case: dict) -> tuple[bool, str]:
    try:
        program = parse(case["source"])
        expected = case["expect"]
        if "error" in expected:
            try:
                execute(program, case.get("state", {}), case.get("max_steps", 1000))
            except SIPLError as error:
                actual = error.diagnostic.code
                return actual == expected["error"], f"expected {expected['error']}, got {actual}"
            return False, f"expected {expected['error']}, got success"
        if "ast" in expected and shape(program) != expected["ast"]:
            return False, "AST structure mismatch"
        if "state" in expected:
            state = execute(program, case.get("state", {}), case.get("max_steps", 1000)).state
            if state != expected["state"]:
                return False, f"expected state {expected['state']}, got {state}"
        return True, "ok"
    except SIPLError as error:
        actual = error.diagnostic.code
        expected = case.get("expect", {}).get("error")
        return actual == expected, f"expected {expected}, got {actual}"
    except (KeyError, TypeError, ValueError) as error:
        return False, f"invalid case: {error}"


def run_suite(directory: str | Path) -> dict:
    root = Path(directory)
    cases = sorted(root.glob("*.json"))
    if not cases:
        raise ValueError(f"No conformance cases in {root}")
    results = []
    for path in cases:
        try:
            case = json.loads(path.read_text(encoding="utf-8"))
            ok, message = check_case(case)
        except (ValueError, OSError, json.JSONDecodeError) as error:
            ok, message = False, str(error)
        results.append({"case": path.name, "passed": ok, "message": message})
    return {"total": len(results), "passed": sum(item["passed"] for item in results), "results": results}


def main(argv: list[str] | None = None) -> int:
    argument = argparse.ArgumentParser(description="Independent SIPL conformance cases")
    argument.add_argument("directory", type=Path)
    args = argument.parse_args(argv)
    result = run_suite(args.directory)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["passed"] == result["total"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
