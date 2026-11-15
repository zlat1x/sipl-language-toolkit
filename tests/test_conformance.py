from pathlib import Path
from sipl.conformance import run_suite, check_case


def test_suite():
    result = run_suite(Path(__file__).parents[1] / "conformance" / "cases")
    assert result["total"] >= 24
    assert result["passed"] == result["total"], result["results"]


def test_conformance_detects_a_wrong_state():
    ok, message = check_case({"source": "begin R := 2 end", "expect": {"state": {"R": 3}}})
    assert not ok
    assert "expected state" in message


def test_conformance_detects_wrong_ast():
    ok, message = check_case({"source": "begin R := 2 end", "expect": {"ast": {"kind": "Skip"}}})
    assert not ok
    assert "AST" in message
