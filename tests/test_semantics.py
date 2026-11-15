from pathlib import Path
import pytest
from sipl import parse, execute
from sipl.semantics import build, display, evaluate
from sipl.diagnostics import SIPLError


@pytest.mark.parametrize("source,initial", [
    ("begin skip end", {}),
    ("begin N := 12 end", {}),
    ("begin N := -2; R := N * N + 1 end", {}),
    ("begin if X > 0 then Y := 1 else Y := 2 end", {"X": -2}),
    ("begin if ¬(X = 0) ∨ X > 2 then Y := 1 else Y := 2 end", {"X": 0}),
    ("begin while N > 0 do N := N - 1 end", {"N": 3}),
    ("begin A := 1; while N > 0 do begin A := A * 2; N := N - 1 end end", {"N": 6}),
    ("begin A := 1; B := 2; C := A + B end", {}),
])
def test_semantic_and_operational_results_coincide(source, initial):
    root = parse(source)
    interpreter = execute(root, initial)
    semantics = evaluate(build(root), initial)
    assert interpreter.state == semantics.state
    assert semantics.transitions


def test_golden_power_term():
    root = parse("begin R := 1; while Y > 0 do begin R := R * X; Y := Y - 1 end end")
    expected = "(AS^R(1) · WH(S^2(gr, Y⇒, 0), (AS^R(S^2(mult, R⇒, X⇒)) · AS^Y(S^2(sub, Y⇒, 1)))))"
    assert display(build(root)) == expected
    result = evaluate(build(root), {"X": 5, "Y": 2})
    assert result.state["R"] == 25
    assert [t["rule"] for t in result.transitions].count("AF_WH_ITER") == 2
    assert [t["rule"] for t in result.transitions].count("AF_WH") == 1


def test_golden_if_term():
    root = parse("begin if X > 0 then skip else Y := -1 end")
    assert display(build(root)) == "IF(S^2(gr, X⇒, 0), id, AS^Y(-1))"


def test_independent_evaluation_error():
    with pytest.raises(SIPLError) as error:
        evaluate(build(parse("begin R := Q end")))
    assert error.value.diagnostic.code == "E_UNDEFINED"


def test_independent_infinite_loop_guard():
    with pytest.raises(SIPLError) as error:
        evaluate(build(parse("begin while 1 > 0 do skip end")), max_steps=20)
    assert error.value.diagnostic.code == "E_STEP_LIMIT"


def test_trace_rule_coverage():
    root = parse("begin if ¬(A = 1) ∨ B > 2 then C := A + B else skip end")
    result = evaluate(build(root), {"A": 1, "B": 3})
    rules = {record["rule"] for record in result.transitions}
    assert {"AF_IF", "AF_AS", "AF_S", "AF_DNM", "AF_CONST"} <= rules


def test_semantic_samples():
    cases = [("power.sipl", {"X": 5, "Y": 3}), ("gcd.sipl", {"M": 8, "N": 16}),
             ("factorial.sipl", {"N": 5}), ("fibonacci.sipl", {"N": 8})]
    root = Path(__file__).parents[1] / "examples"
    for name, initial in cases:
        program = parse((root / name).read_text())
        assert evaluate(build(program), initial).state == execute(program, initial).state


def test_disjunction_is_strict_for_partial_state():
    with pytest.raises(SIPLError) as error:
        evaluate(build(parse("begin if X > 0 ∨ M = 0 then skip else skip end")), {"X": 2})
    assert error.value.diagnostic.code == "E_UNDEFINED"
