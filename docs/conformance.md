# Implementation-neutral conformance suite

A fixture is a UTF-8 JSON file of the form:

```json
{
  "id": "example",
  "source": "begin R := 2 end",
  "state": {},
  "expect": {
    "state": {"R": 2},
    "ast": {
      "kind": "Program",
      "body": {"kind": "Assign", "name": "R", "value": {"kind": "Number", "value": 2}}
    }
  }
}
```

The fields `source` and `expect` are mandatory. `state` defaults to `{}`. For expected runtime/lexical/syntactic failures use `"expect": {"error": "E_STEP_LIMIT"}` and optionally `"max_steps": 30`. For a successful case, `expect.state` and `expect.ast` are independently optional; successful parsing still has to complete and error-free runs are checked when `state` is present. AST expectations are **source-span-free** recursive node shapes so fixtures are not coupled to formatting.

There are 30 committed independent cases (`01`–`15`: valid; `16`–`30`: invalid, including undefinedness and execution limit). They are separate files and can be consumed by another SIPL implementation or inspected manually. `sipl.conformance.check_case` and `run_suite` are library APIs; `python -m sipl.conformance conformance/cases` is an executable runner.

```bash
sipl conformance conformance/cases
python -m sipl.conformance conformance/cases
python -m pytest -q tests/test_conformance.py
```

`conformance` returns process code 0 if every case passed, otherwise 1. A negative test *passes* only if the particular expected error code is reported; successful execution when an error is expected fails the suite. Unit tests include an intentional mismatch to verify that the runner is not trivially always green.
