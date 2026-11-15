import pytest
from sipl import execute, parse
from sipl.diagnostics import SIPLError


@pytest.mark.parametrize("source,initial,expected", [
    ("begin skip end", {}, {}),
    ("begin X := -3 end", {}, {"X": -3}),
    ("begin X := 3 + 2 * 4 end", {}, {"X": 11}),
    ("begin X := 2; X := X + 3 end", {}, {"X": 5}),
    ("begin if N > 0 then R := 7 else R := 8 end", {"N": 3}, {"N": 3, "R": 7}),
    ("begin if N > 0 then R := 7 else R := 8 end", {"N": 0}, {"N": 0, "R": 8}),
    ("begin X := 0; while N > 0 do begin X := X + 2; N := N - 1 end end", {"N": 4}, {"N": 0, "X": 8}),
    ("begin if ¬(X = 3) ∨ X > 1 then Y := 1 else Y := 2 end", {"X": 3}, {"X": 3, "Y": 1}),
    ("begin X := (10 - 3) - 2 end", {}, {"X": 5}),
    ("begin X := 4; if X > 0 then skip else X := 1 end", {}, {"X": 4}),
    ("begin X := 1 end", {"P": 42}, {"P": 42, "X": 1}),
    ("begin if (1 + 2) > 2 then R := 1 else R := -1 end", {}, {"R": 1}),
])
def test_result(source, initial, expected):
    assert execute(parse(source), initial).state == expected


def test_finite_loop_case():
    source = "begin R := 1; while Y > 0 do begin R := R * X; Y := Y - 1 end end"
    assert execute(parse(source), {"X": 5, "Y": 2}).state == {"R": 25, "X": 5, "Y": 0}


def test_undefined_variable_error():
    with pytest.raises(SIPLError) as error:
        execute(parse("begin X := Y + 1 end"))
    assert error.value.diagnostic.code == "E_UNDEFINED"
    assert error.value.diagnostic.span.start.column == 12


def test_infinite_loop_guard():
    with pytest.raises(SIPLError) as error:
        execute(parse("begin while 1 > 0 do skip end"), max_steps=20)
    assert error.value.diagnostic.code == "E_STEP_LIMIT"


def test_events_are_stable_and_snapshot_is_immutable():
    result = execute(parse("begin X := 1; X := X + 1 end"))
    names = [event["event"] for event in result.events]
    assert "BeforeStatement" in names
    assert "VariableChanged" in names
    assert "AfterStatement" in names
    assert names[-1] == "Completed"
    changes = [event for event in result.events if event["event"] == "VariableChanged"]
    assert [change["detail"]["new"] for change in changes] == [1, 2]
    assert changes[0]["state"]["X"] == 1
    assert changes[1]["state"]["X"] == 2


def test_condition_events():
    result = execute(parse("begin while X > 0 do X := X - 1 end"), {"X": 2})
    checks = [x["detail"]["value"] for x in result.events if x["event"] == "ConditionEvaluated"]
    assert checks == [True, True, False]


def test_initial_state_not_mutated():
    initial = {"N": 2}
    execute(parse("begin N := 10 end"), initial)
    assert initial == {"N": 2}


def test_zero_step_limit_rejected():
    with pytest.raises(ValueError):
        execute(parse("begin skip end"), max_steps=0)


def test_disjunction_is_strict_for_partial_state():
    """S²(or, p, q) requires both predicate arguments to be defined."""
    with pytest.raises(SIPLError) as error:
        execute(parse("begin if X > 0 ∨ M = 0 then skip else skip end"), {"X": 2})
    assert error.value.diagnostic.code == "E_UNDEFINED"
