import json
from pathlib import Path
import pytest
from sipl.cli import main, parse_state

ROOT = Path(__file__).parents[1]


def test_main_all_commands(capsys):
    source = str(ROOT / "examples" / "power.sipl")
    for command in ["parse", "check", "run", "trace", "tree", "term", "eval-term"]:
        rc = main([command, source, "--json", "--var", "X=5", "--var", "Y=2"])
        captured = capsys.readouterr()
        assert rc == 0, captured.err + captured.out
        assert json.loads(captured.out)["ok"]


def test_main_text_and_formats(capsys):
    src = str(ROOT / "examples" / "branch.sipl")
    for format_ in ("dot", "svg", "json", "text"):
        assert main(["tree", src, "--format", format_]) == 0
        assert capsys.readouterr().out
    assert main(["term", src]) == 0
    assert "IF(" in capsys.readouterr().out
    assert main(["check", src]) == 0
    assert "Syntax OK" in capsys.readouterr().out
    assert main(["trace", src, "--var", "X=1", "--var", "Y=2"]) == 0
    assert "VariableChanged" in capsys.readouterr().out
    assert main(["eval-term", src, "--var", "X=1", "--var", "Y=2"]) == 0
    assert "Rules:" in capsys.readouterr().out
    assert main(["run", src, "--var", "X=1", "--var", "Y=2"]) == 0
    assert "Final state" in capsys.readouterr().out


def test_main_conformance(capsys):
    assert main(["conformance", str(ROOT / "conformance" / "cases")]) == 0
    assert "30/30" in capsys.readouterr().out


def test_error_modes(capsys):
    invalid = str(ROOT / "examples" / "invalid.sipl")
    undefined = str(ROOT / "examples" / "undefined.sipl")
    infinite = str(ROOT / "examples" / "infinite.sipl")
    assert main(["check", invalid]) == 2
    assert "E_PARSE" in capsys.readouterr().err
    assert main(["run", undefined]) == 3
    assert "E_UNDEFINED" in capsys.readouterr().err
    assert main(["run", infinite, "--max-steps", "15"]) == 3
    assert "E_STEP_LIMIT" in capsys.readouterr().err
    assert main(["run", infinite, "--max-steps", "0", "--json"]) == 4
    assert json.loads(capsys.readouterr().out)["diagnostics"][0]["code"] == "E_INPUT"


@pytest.mark.parametrize("state,assignments", [
    ('{"A":true}', []), ('[]', []), (None, ['oops']),
    ('{"1A":4}', []), ('{"begin":4}', []), (None, ['X=nan']), ('{bad', []),
])
def test_invalid_state(state, assignments):
    with pytest.raises(ValueError):
        parse_state(state, assignments)


def test_inprocess_conformance_failure(tmp_path, capsys):
    (tmp_path / 'case.json').write_text(json.dumps({"source": "begin X := 1 end", "expect": {"state": {"X": 2}}}))
    assert main(['conformance', str(tmp_path), '--json']) == 1
    assert json.loads(capsys.readouterr().out)['ok'] is False


def test_error_trace_contains_partial_history(capsys):
    undefined = str(ROOT / "examples" / "undefined.sipl")
    infinite = str(ROOT / "examples" / "infinite.sipl")
    assert main(["eval-term", undefined, "--json"]) == 3
    eval_data = json.loads(capsys.readouterr().out)
    assert eval_data["ok"] is False
    assert eval_data["data"]["state"] is None
    assert eval_data["data"]["transitions"][-1]["rule"] == "AF_UNDEFINED"
    assert main(["trace", infinite, "--json", "--max-steps", "15"]) == 3
    trace_data = json.loads(capsys.readouterr().out)
    assert trace_data["ok"] is False
    assert trace_data["data"]["events"][-1]["event"] == "ExecutionError"
