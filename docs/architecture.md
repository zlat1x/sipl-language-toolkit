# Architecture, language contract and theory mapping

## Layers and data flow

```text
.sipl source
    │
    ▼
lexer.py ───────► Token(kind, text, SourceSpan)
    │
    ▼
parser.py ──────► immutable typed AST (ast.py)
    │                    ├──► interpreter/runtime.py ──► State + Event[]
    │                    ├──► semantics/terms.py ──────► Term ─► State + RuleTrace[]
    │                    └──► visualization/tree.py ──► concrete tree + Text/JSON/DOT/SVG
    │
    └────────────► cli.py ─► versioned JSON envelope or readable output
                          │
                          └► conformance.py (independent fixtures)
```

`ast.py` and `diagnostics.py` are stable cross-component types. `SourceSpan` is half-open and carries line, column and offset. Data crosses subsystem boundaries as typed frozen AST objects, immutable term objects or JSON-safe dictionaries; there is no parser or interpreter copy in a presentation layer.

## Semantics (Praktykum 2024, pp. 13–16)

SIPL state is a partial map `State : Var ⇀ ℤ`. Evaluation of a variable outside its domain is undefined (`E_UNDEFINED`). Both operational and denotational layers produce compatible state transformations on supported programs.

| SIPL | Formal term | Course rule |
|---|---|---|
| `x := a` | `AS^x(sem_A(a))` | `NS_Stm_As`, `AF_AS` |
| `S1 ; S2` | `sem_S(S1) · sem_S(S2)` | `NS_Stm_Seq`, `AF_SEQ` |
| `if b then S1 else S2` | `IF(sem_B(b),sem_S(S1),sem_S(S2))` | `NS_Stm_If`, `AF_IF` |
| `while b do S` | `WH(sem_B(b),sem_S(S))` | `NS_Stm_Wh`, `AF_WH` |
| `skip` | `id` | `NS_Stm_skip`, `AF_ID` |
| `begin S end` | `sem_S(S)` | `NS_Stm_BE` |
| `a1+a2` / `-` / `*` | `S^2(add/sub/mult, ..., ...)` | `NS_A_Add/Sub/Mult` |
| `a1=a2` / `a1>a2` | `S^2(eq/gr, ..., ...)` | `NS_B_eq/gr` |
| `b1∨b2` / `¬b` | `S^2(or, ..., ...)` / `S^1(neg,...)` | `NS_B_or/neg` |

The operational interpreter counts statement entries and loop predicate checks and emits immutable snapshots; an infinite loop triggers `E_STEP_LIMIT`. On failure, event and transition histories remain accessible to the CLI through structured exception types. The term evaluator is **separate** and recursively applies `AF_AS`, `AF_SEQ`, `AF_IF`, `AF_WH`, `AF_ID` to terms with its own limit, creating a trace with source spans and before/after states. `S^2(or, p, q)` evaluates both operands as a composition of partial predicates, not a short-circuit extension of the language.

### Worked example

```sipl
begin
 R := 1;
 while Y > 0 do begin R := R * X; Y := Y - 1 end
end
```

The generated term is:

```
(AS^R(1) · WH(S^2(gr, Y⇒, 0),
  (AS^R(S^2(mult, R⇒, X⇒)) · AS^Y(S^2(sub, Y⇒, 1)))))
```

For `[X↦5,Y↦2]`, the state after initialization is `[R↦1,X↦5,Y↦2]`, after the first iteration is `[R↦5,X↦5,Y↦1]`, after the second iteration is `[R↦25,X↦5,Y↦0]`. The third condition check is false, so the resulting value is `R=25`. Both evaluators are checked against each other with multiple inputs.

## Grammar decisions

The course BNF is recursive and ambiguous until precedence, associativity, and nearest-`else` conventions are selected. We use descending precedence `*`, `+/-`, comparisons, `¬`, `∨`, statements and `;`. Arithmetic binary operators associate to the left. A `while` or `if` body consumes one statement (use `begin/end` for more), and a following `;` belongs to the outer statement sequence. `else` matches the nearest unmatched `if`. The canonical written grammar is `grammar/sipl.ebnf`, a machine-parseable Lark form is `grammar/sipl.lark`, and the exact token/precedence contract is `grammar/sipl.json`.

The tree exporter derives a **token-preserving concrete representation** from the actual typed AST and lexer tokens. It inserts delimiters and operator terminals into each AST node's source interval; leaf token sequence is proved identical to the lexer sequence in tests. This is a source-linked concrete tree, not a screenshot or a reconstructed string template. The DOT and SVG exporters are generated from the same object.

## Explicit boundaries

- No division, modulus, literal booleans, function definitions, declarations, arrays, procedures, or I/O in SIPL v1.
- Parenthesized arithmetic and conditions are supported. A negative **integer literal** is legal; arbitrary unary negation of variables is not a BNF operation.
- The syntax checker proves only syntactic well-formedness, not termination or total correctness.
- The step limit reports undecided/nonterminating-looking executions, never a formal mathematical proof of nontermination.
- No compiler, external VS Code debugger, market release or PyPI publication is claimed.
- The parser uses a hand-written recursive descent rather than an auto-generated Lark parser; the grammar is a separate formal, machine-parseable reference validated in tests.

## Testing and independence

The independently maintained conformance JSON cases assert AST shapes, states and diagnostic codes. Unit tests compare `interpreter.execute` and `semantics.evaluate(build(...))` on finite examples; tests also cover undefinedness, nonterminating loops, source-spans and CLI output. The workflow at `.github/workflows/ci.yml` defines clean environment checks; its **remote status cannot be asserted before an actual GitHub push**.
