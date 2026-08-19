from __future__ import annotations

import json
from types import SimpleNamespace

import pytest

from yasin_operations import cli


class FakeResult:
    def __init__(self, success: bool, data=None, error=None, operation_id: str = "op-1"):
        self.success = success
        self.data = data
        self.error = error
        self.operation_id = operation_id


class FakeExecutor:
    def __init__(self, result: FakeResult):
        self.result = result

    def execute(self, *args, **kwargs):
        return self.result


def _runtime(result: FakeResult):
    config = SimpleNamespace(
        service_root="/tmp/services",
        sv_path="/tmp/sv",
        service_names=("yasin-ai",),
        always_on=True,
        execution_timeout_seconds=30.0,
        startup_grace_seconds=2.0,
        log_level="INFO",
        service_definitions=lambda: (),
        missing_services=lambda: (),
    )
    return FakeExecutor(result), config, SimpleNamespace(entries=[])


def test_help_lists_commands_and_exit_contract(capsys):
    with pytest.raises(SystemExit) as exc:
        cli.build_parser().parse_args(["--help"])
    assert exc.value.code == 0
    output = capsys.readouterr().out
    for command in ("status", "health", "doctor", "start", "stop", "restart"):
        assert command in output


def test_global_options_are_accepted_before_and_after_subcommand():
    before = cli.build_parser().parse_args(
        ["--json", "--service-root", "/tmp/services", "doctor"]
    )
    after = cli.build_parser().parse_args(
        ["doctor", "--json", "--service-root", "/tmp/services"]
    )
    assert before.as_json is True
    assert after.as_json is True
    assert before.service_root == after.service_root == "/tmp/services"


def test_status_json_contract_and_success_exit(monkeypatch, capsys):
    monkeypatch.setattr(
        cli,
        "build_runtime",
        lambda overrides=None: _runtime(
            FakeResult(True, {"services": [{"name": "yasin-ai", "state": "running"}]})
        ),
    )
    assert cli.main(["--json", "status"]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["schema_version"] == cli.SCHEMA_VERSION
    assert payload["command"] == "status"
    assert payload["success"] is True
    assert payload["error"] is None
    assert payload["data"]["summary"]["health"] == "healthy"


def test_mutating_failure_has_stable_error_exit_and_json(monkeypatch, capsys):
    monkeypatch.setattr(
        cli,
        "build_runtime",
        lambda overrides=None: _runtime(FakeResult(False, {}, None, "op-2")),
    )
    assert cli.main(["restart", "yasin-ai", "--dry-run", "--json"]) == 2
    payload = json.loads(capsys.readouterr().out)
    assert payload["command"] == "restart"
    assert payload["success"] is False
    assert payload["operation_id"] == "op-2"


def test_configuration_failure_is_machine_readable(monkeypatch, capsys):
    def fail_runtime(overrides=None):
        raise cli.InvalidConfigurationError("service_root must be an absolute path")

    monkeypatch.setattr(cli, "build_runtime", fail_runtime)
    assert cli.main(["doctor", "--json"]) == cli.CONFIG_EXIT_ERROR
    payload = json.loads(capsys.readouterr().out)
    assert payload == {
        "command": "doctor",
        "error": {
            "category": "configuration",
            "message": "service_root must be an absolute path",
        },
        "schema_version": cli.SCHEMA_VERSION,
        "success": False,
    }


def test_doctor_degraded_exit_is_stable(monkeypatch, capsys):
    monkeypatch.setattr(cli, "build_runtime", lambda overrides=None: _runtime(FakeResult(True)))
    monkeypatch.setattr(
        cli,
        "detect_termux",
        lambda *args, **kwargs: SimpleNamespace(
            issues=["service root missing"],
            as_dict=lambda: {"is_termux": True, "issues": ["service root missing"]},
        ),
    )
    monkeypatch.setattr(
        cli,
        "resource_snapshot",
        lambda: SimpleNamespace(as_dict=lambda: {"pid": 1}),
    )
    assert cli.main(["--json", "doctor"]) == cli.DOCTOR_EXIT_DEGRADED
    payload = json.loads(capsys.readouterr().out)
    assert payload["command"] == "doctor"
    assert payload["success"] is False
    assert payload["error"]["category"] == "diagnostics"


def test_invalid_argument_uses_argparse_exit_code():
    with pytest.raises(SystemExit) as exc:
        cli.build_parser().parse_args(["status", "--timeout", "not-a-number"])
    assert exc.value.code == 2
