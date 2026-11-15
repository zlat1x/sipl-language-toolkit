import json
import os
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).parents[1]


def call(*args):
    env = {**os.environ, "PYTHONPATH": str(ROOT / "src")}
    return subprocess.run([sys.executable, "-m", "sipl", *map(str, args)],
                          capture_output=True, text=True, env=env, check=False)


def test_commands_and_json_contract():
    source = ROOT / "examples" / "power.sipl"
    for command in ("parse", "check", "run", "trace", "tree", "term", "eval-term"):
        p = call(command, source, "--json", "--var", "X=2", "--var", "Y=3")
        assert p.returncode == 0, p.stderr + p.stdout
        result = json.loads(p.stdout)
        assert list(result) == ["schema_version", "command", "ok", "data", "diagnostics"]
        assert result["schema_version"] == "1.0"
        assert result["ok"] is True
    assert json.loads(call("run", source, "--json", "--var", "X=2", "--var", "Y=3").stdout)["data"]["state"]["R"] == 8


def test_tree_formats():
    source = ROOT / "examples" / "branch.sipl"
    for format_, marker in [("dot", "digraph SIPL"), ("svg", "<svg"), ("text", "Program"), ("json", "children")]:
        result = call("tree", source, "--format", format_)
        assert result.returncode == 0
        assert marker in result.stdout


def test_invalid_syntax_error_and_code():
    result = call("check", ROOT / "examples" / "invalid.sipl", "--json")
    assert result.returncode == 2
    parsed = json.loads(result.stdout)
    assert parsed["ok"] is False
    assert parsed["diagnostics"][0]["span"]["start"]["line"] == 2


def test_undefined_and_limit_exit_codes():
    undefined = call("run", ROOT / "examples" / "undefined.sipl", "--json")
    infinite = call("run", ROOT / "examples" / "infinite.sipl", "--json", "--max-steps", "20")
    assert undefined.returncode == infinite.returncode == 3
    assert json.loads(undefined.stdout)["diagnostics"][0]["code"] == "E_UNDEFINED"
    assert json.loads(infinite.stdout)["diagnostics"][0]["code"] == "E_STEP_LIMIT"


def test_invalid_input_error_code():
    invalid = call("run", ROOT / "examples" / "power.sipl", "--json", "--var", "INVALID")
    assert invalid.returncode == 4
    assert json.loads(invalid.stdout)["diagnostics"][0]["code"] == "E_INPUT"


def test_conformance_cli():
    result = call("conformance", ROOT / "conformance" / "cases", "--json")
    assert result.returncode == 0, result.stdout
    data = json.loads(result.stdout)["data"]
    assert data["passed"] == data["total"]
    assert data["total"] >= 20
