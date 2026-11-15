# SIPL JSON protocol · v1.0

The CLI guarantees an envelope for all commands invoked with `--json`:

```json
{
  "schema_version": "1.0",
  "command": "run",
  "ok": true,
  "data": {"state": {"R": 25, "X": 5, "Y": 0}, "steps": 19},
  "diagnostics": []
}
```

`schema_version`, `command`, `ok`, `data`, `diagnostics` are present in this order. Error responses use `ok:false` and a nonempty `diagnostics` list, without extraneous text on standard output. Parse/input failures use `data:null`; runtime/semantic failures can include a partial `data` object holding execution events or already-applied semantic transitions so that a debugger can inspect a failed run. `diagnostics[i]` contains `code`, `message`, and `span` (null for input errors).

A `span` has `start` and `end` positions, each `{ "line": n, "column": n, "offset": n }`: `line` and `column` are **1-based**, `offset` is **0-based Unicode code-point offset** and `end` is exclusive. State is a mapping of source variable names to **arbitrary-precision signed integers** (JSON numbers); there are no implicit variable declarations or default values.

## Command-specific `data`

| Command | Shape |
|---|---|
| `parse` | Typed recursive AST object `{kind, span, ...fields}`. |
| `check` | `{valid: true, nodes: integer}`. Syntax verification does not require all variables to be defined. |
| `run` | `{state: object, steps: integer}`. |
| `trace` | `{state, steps, events: [Event]}`. |
| `term` | `{text: string, tree: Term}`. |
| `eval-term` | `{state, steps, transitions: [Transition]}`. |
| `tree` | Concrete tree object `{label, span, children: [...]}`. Use `--format svg` / `--format dot` without `--json` for raw export. |
| `conformance` | `{total, passed, results:[{case,passed,message}]}`. |

Events contain `{event, step, span, state, detail}`, with snapshot semantics: event states will never mutate if later assignments occur. Event kinds are `BeforeStatement`, `AfterStatement`, `VariableChanged`, `ConditionEvaluated`, `Completed` and `ExecutionError` (runtime only). `step` counts statement entries and repeated condition evaluations; this is an implementation safety bound, not the number of CPU instructions.

A semantic transition has `{rule,term,span,before,after,detail}`. Rules include `AF_CONST`, `AF_DNM` (variable read), `AF_S` (function superposition), `AF_AS` (assignment), `AF_SEQ` (composition), `AF_IF`, `AF_WH`, `AF_WH_ITER` and `AF_ID`. `after` can be null for pure value evaluation. Undefined computations raise `E_UNDEFINED` and do not produce an invented final state. In a failed `eval-term` response, `data.state` is null and `data.transitions` ends with `AF_UNDEFINED`; failed `trace` responses retain `ExecutionError` and preceding events.

## Compatibility

Version `1.0` fixes field names, diagnostic codes and exit codes. Minor releases may add fields, commands and new error codes. Breaking fields or span representation require a major version. The separate `sipl.conformance` module accepts independently authored JSON cases and does not require CLI output comparisons.
