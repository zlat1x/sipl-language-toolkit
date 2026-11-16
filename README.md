# SIPL Language Toolkit

**Theory of Programming · Individual course project · 2026**  
**Author:** Zlata Dovbyk · **Version:** 1.0.0 · **Language:** Python 3.10+

An installable, modular toolkit for the course's **SIPL** (SImple Programming Language). It translates SIPL source into a typed **AST with source positions**, executes programs using operational semantics, constructs and independently evaluates **semantic terms in the course's algebra**, exposes a versioned **JSON CLI**, generates concrete **syntax trees** in four formats and runs an independent **conformance suite**.

## Declared modules and assessment

| Task | Deliverable | Points |
|:--|:--|--:|
| CORE-01 | Course-aligned SIPL specification, Lark/EBNF, 14 positive + 19 negative grammar tests | 0.5 |
| CORE-02 | Recursive-descent parser, immutable typed AST and `SourceSpan` diagnostics | 1.5 |
| CORE-03 | Interpreter for all six statement forms with execution limits and extensive tests | 2.0 |
| CORE-04 | `BeforeStatement`, `AfterStatement`, `VariableChanged`, `ConditionEvaluated`, `Completed`, `ExecutionError` events | 1.0 |
| CORE-05 | `parse`, `check`, `run`, `trace`, and structured JSON with integration tests | 1.0 |
| CORE-06 | Independent JSON conformance suite: 30 cases covering AST, state and errors | 1.0 |
| VIS-01 | Source-linked concrete syntax tree, exported to text / JSON / DOT / SVG | 1.5 |
| SEM-01 | Recursive `sem_P`, `sem_S`, `sem_A`, `sem_B` term construction; golden tests | 2.0 |
| SEM-02 | Independent term evaluator with `AF_*` proof/transition trace and undefinedness | 2.0 |
| **Declared total** | **9 independent deliverables** | **12.5** |

**Maximum credit is 10.0 points.** Points are awarded only if a lecturer accepts a module's readiness criteria. The CLI, the operational interpreter, the independent denotational evaluator and the conformance runner have distinct responsibilities; the table does not double-count the same logic as a separate implementation. GitHub CI is supplied as an engineering convenience, **not** as a claimed REL module (it requires publication and a passing remote run).

## One-minute installation

From the repository root (PowerShell, CMD, Linux, macOS or WSL):

```bash
python -m pip install -e .
sipl check examples/power.sipl
sipl run examples/power.sipl --var X=5 --var Y=2
sipl term examples/power.sipl
sipl eval-term examples/power.sipl --var X=5 --var Y=2
sipl conformance conformance/cases
```

Expected final state for the power program: `{"R": 25, "X": 5, "Y": 0}`. The command does not modify input files. On some Windows installations use `py -m pip` for installation and `py -m sipl` instead of `sipl`; the toolkit also works without installation with `PYTHONPATH=src python -m sipl ...` (Bash) or `$env:PYTHONPATH="src"; python -m sipl ...` (PowerShell).

For reproducible automated tests:

```bash
python -m pip install -e ".[dev]"
python -m pytest -q
python -m pytest --cov=sipl --cov-branch --cov-report=term-missing
python -m build
```

The runtime depends only on Python's standard library. Test, build and reference grammar validation require the optional dev dependencies. Both fresh installation and source execution use the **same** package API.

## SIPL syntax

The grammar follows **Shyshatska, Kryvolap & Shyshatsky (2024), practicum pp. 8–10**, rules NP1, NS1–NS6, NA1–NA6, NB1–NB5. It supports integer variables, `+`, `-`, `*`, conditions with `=`, `>`, disjunction `∨`, negation `¬`, assignment `:=`, sequencing `;`, `if/then/else`, `while/do`, `begin/end`, and `skip`. Parentheses group arithmetic and conditions. Standard precedence and left associativity are documented in [`grammar/sipl.json`](grammar/sipl.json).

```sipl
begin
    R := 1;
    while Y > 0 do
    begin
        R := R * X;
        Y := Y - 1
    end
end
```

**Explicit lexical conveniences** beyond the printed BNF: names may include letters, digits and `_` (but not start with a digit); `!` is an alias of `¬`, and `|` is an alias of `∨`. These are convenience spellings, not additional operations. Keywords are lowercase and case-sensitive; variables such as `X` and `N` are distinct from `x` and `n`. **Do not write a trailing semicolon** immediately before `end`. SIPL v1 does not have division, I/O, declarations, boolean literals, `and`, `mod` or function declarations.

A missing variable is **undefined**, rather than automatically initialized to zero. Both evaluators reject it explicitly. A cycle with no terminating state is stopped by a configurable execution bound; the tool does not pretend to decide mathematical termination.

## Commands

```bash
sipl parse examples/factorial.sipl --json
sipl check examples/factorial.sipl
sipl run examples/gcd.sipl --state '{"M":8,"N":16}' --json
sipl trace examples/power.sipl --var X=5 --var Y=2 --json
sipl tree examples/branch.sipl --format text
sipl tree examples/branch.sipl --format json
sipl tree examples/branch.sipl --format dot > branch.dot
sipl tree examples/branch.sipl --format svg > branch.svg
sipl term examples/power.sipl
sipl eval-term examples/power.sipl --state '{"X":5,"Y":2}' --json
sipl conformance conformance/cases --json
```

Use `--var` on Windows to avoid shell-specific JSON quoting. `--max-steps 2000` customizes the default bound of 10,000. `tree` emits a real token-preserving concrete tree inferred from parser AST spans (including punctuation and grouping tokens), while `parse` emits the more compact AST. SVG export requires no Graphviz; DOT can optionally be rendered with `dot -Tpng branch.dot -o branch.png`.

| Code | Meaning | Exit code |
|---|---|---:|
| Successful invocation | Result or successful validation | `0` |
| Failed conformance suite | One or more mismatched cases | `1` |
| `E_LEX` / `E_PARSE` | Invalid character / malformed source | `2` |
| `E_UNDEFINED` / `E_STEP_LIMIT` | Partial state / execution bound | `3` |
| `E_INPUT` | Invalid file, state or CLI input | `4` |

See [`docs/json-api.md`](docs/json-api.md) for the stable integration envelope, [`docs/architecture.md`](docs/architecture.md) for internal components, and [`docs/conformance.md`](docs/conformance.md) for test fixtures.

## Directory structure

```text
grammar/            Formal EBNF, executable Lark specification and lexical contract
src/sipl/           Library, parser, AST, interpreter, semantic terms, tree exports, CLI
examples/           Correct and deliberately erroneous SIPL examples
tests/              Unit, grammar, integration, conformance and cross-model tests
conformance/cases/  Independent JSON test cases
.github/workflows/  Portable PR/push verification workflow
docs/               Architecture, JSON/API contract, conformance format
```

## Python API

The same library is accessible from any Python client:

```python
from sipl import parse, execute, build, evaluate

program = parse("begin X := 2; while X > 0 do X := X - 1 end")
assert execute(program).state == {"X": 0}
assert evaluate(build(program)).state == {"X": 0}
```

## Source, limits, academic integrity

The formal language and semantical rules derive from *Teoriia prohramuvannia. Praktykum* (O. Shyshatska, A. Kryvolap, A. Shyshatsky, 2024) and the course lectures. See [`docs/architecture.md`](docs/architecture.md) for precise rule correspondences and limitations. The 2026 project rubric explicitly caps the score at 10 despite a higher declared module sum.

**AI usage declaration:** ChatGPT (OpenAI) was used during project development and preparation of supporting materials. The software was verified through automated testing.
