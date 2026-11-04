import json
from os import path

from .util import run_cli

DEPLOY = path.join("tests", "test_cli", "deploy", "prepare_end.py")
ENV_VAR = "PYINFRA_PREPARE_END_FILE"


def _run(monkeypatch, tmp_path, *flags):
    record = tmp_path / "prepare_end.jsonl"
    monkeypatch.setenv(ENV_VAR, str(record))
    result = run_cli("-y", *flags, "@fake/onehost", DEPLOY)
    assert result.exit_code == 0, result.stderr

    calls = []
    if record.exists():
        calls = [json.loads(line) for line in record.read_text().splitlines()]
    return calls


def test_prepare_end_fires_once_for_a_normal_run(monkeypatch, tmp_path):
    assert _run(monkeypatch, tmp_path) == [{"dry": False, "debug": False}]


def test_prepare_end_reports_a_dry_run(monkeypatch, tmp_path):
    assert _run(monkeypatch, tmp_path, "--dry") == [{"dry": True, "debug": False}]


def test_prepare_end_reports_debug_operations(monkeypatch, tmp_path):
    assert _run(monkeypatch, tmp_path, "--debug-operations") == [{"dry": False, "debug": True}]


def test_prepare_end_reports_debug_facts(monkeypatch, tmp_path):
    assert _run(monkeypatch, tmp_path, "--debug-facts") == [{"dry": False, "debug": True}]
