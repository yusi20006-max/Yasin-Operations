from yasin_operations.cli import main
from yasin_operations.core.execution.executor import Executor
from yasin_operations.core.operations.models import Operation, OperationTarget
from yasin_operations.runtime.resources import snapshot
from yasin_operations.runtime.termux.config import TermuxRuntimeConfig
from yasin_operations.runtime.termux.diagnostics import detect_termux
from yasin_operations.runtime.termux.runit import RunitServiceBackend, RunitServiceDefinition
from yasin_operations.runtime.process import ProcessInfo
from yasin_operations.safety.classification import SafetyClass


class FakeInspector:
    def __init__(self, alive=True):
        self.alive = alive

    def list_processes(self):
        return [ProcessInfo(pid=123, name="demo", status="running")] if self.alive else []

    def get_process(self, pid):
        if pid != 123 or not self.alive:
            raise RuntimeError("missing")
        return ProcessInfo(pid=123, name="demo", status="running")

    def find_by_name(self, pattern):
        return self.list_processes()

    def is_alive(self, pid):
        return self.alive and pid == 123


def test_termux_config_is_environment_backed(monkeypatch):
    monkeypatch.setenv("YASIN_OPERATIONS_SERVICE_NAMES", "relay,press,ai")
    monkeypatch.setenv("YASIN_OPERATIONS_ALWAYS_ON", "false")
    config = TermuxRuntimeConfig.from_env()
    assert config.service_names == ("ai", "press", "relay")
    assert config.always_on is False
    assert [d.name for d in config.service_definitions()] == ["ai", "press", "relay"]


def test_resource_snapshot_has_process_identity():
    data = snapshot().as_dict()
    assert data["pid"] > 0
    assert data["user_cpu_seconds"] >= 0
    assert data["system_cpu_seconds"] >= 0


def test_runit_backend_does_not_mutate_when_unavailable(tmp_path):
    backend = RunitServiceBackend(
        FakeInspector(),
        service_root=str(tmp_path),
        definitions=[RunitServiceDefinition("demo", process_pattern="demo")],
        sv_path=str(tmp_path / "missing-sv"),
    )
    status = backend.get_status("demo")
    assert status.state.value == "unknown"
    assert status.health_state == "unavailable"


def test_termux_detection_is_noninvasive(tmp_path, monkeypatch):
    monkeypatch.delenv("PREFIX", raising=False)
    result = detect_termux(str(tmp_path))
    assert result.service_root == str(tmp_path)
    assert result.active_services == ()


def test_cli_dry_run_never_requires_termux(monkeypatch, capsys):
    monkeypatch.setenv("YASIN_OPERATIONS_SERVICE_NAMES", "demo")
    monkeypatch.setenv("YASIN_OPERATIONS_SERVICE_ROOT", "/missing")
    monkeypatch.setenv("YASIN_OPERATIONS_SV_PATH", "/missing/sv")
    assert main(["--json", "restart", "demo", "--dry-run"]) == 0
    output = capsys.readouterr().out
    assert '"success": true' in output
    assert '"dry_run": true' in output


def test_cli_mutation_requires_confirmation(monkeypatch, capsys):
    monkeypatch.setenv("YASIN_OPERATIONS_SERVICE_NAMES", "demo")
    monkeypatch.setenv("YASIN_OPERATIONS_SERVICE_ROOT", "/missing")
    monkeypatch.setenv("YASIN_OPERATIONS_SV_PATH", "/missing/sv")
    assert main(["--json", "restart", "demo"]) == 2
    output = capsys.readouterr().out
    assert "permission_denied" in output
