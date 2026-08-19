import os
from pathlib import Path
from unittest.mock import patch

import pytest

from yasin_operations.config.config import (
    DEFAULT_SERVICE_ROOT,
    DEFAULT_SV_PATH,
    InvalidConfigurationError,
    OperationsConfig,
    load_config,
)


def test_defaults():
    config = OperationsConfig()
    assert config.service_root == DEFAULT_SERVICE_ROOT
    assert config.sv_path == DEFAULT_SV_PATH
    assert config.service_names == ()
    assert config.execution_timeout_seconds == 30
    assert config.startup_grace_seconds == 2
    assert config.always_on is True
    assert config.log_level == "INFO"


def test_explicit_construction_and_registry():
    config = OperationsConfig(
        service_root="/tmp/services",
        sv_path="/tmp/sv",
        service_names=("yasin-ai", "yasinpress"),
        execution_timeout_seconds=60,
        startup_grace_seconds=5,
        always_on=False,
        log_level="DEBUG",
    )
    assert config.service_names == ("yasin-ai", "yasinpress")
    assert config.execution_timeout_seconds == 60
    assert config.startup_grace_seconds == 5
    assert config.always_on is False
    assert [item.name for item in config.service_definitions()] == ["yasin-ai", "yasinpress"]


def test_defaults_are_safe_for_termux():
    config = OperationsConfig()
    assert config.service_root == "/data/data/com.termux/files/usr/var/service"
    assert config.sv_path == "/data/data/com.termux/files/usr/bin/sv"
    assert Path(config.service_root).is_absolute()
    assert Path(config.sv_path).is_absolute()


def test_rejects_relative_paths():
    with pytest.raises(InvalidConfigurationError, match="service_root"):
        OperationsConfig(service_root="relative/services")
    with pytest.raises(InvalidConfigurationError, match="sv_path"):
        OperationsConfig(sv_path="sv")


def test_rejects_non_positive_timeout():
    with pytest.raises(InvalidConfigurationError, match="positive"):
        OperationsConfig(execution_timeout_seconds=0)


def test_rejects_negative_startup_grace():
    with pytest.raises(InvalidConfigurationError, match="negative"):
        OperationsConfig(startup_grace_seconds=-1)


def test_rejects_invalid_log_level():
    with pytest.raises(InvalidConfigurationError):
        OperationsConfig(log_level="NOT_A_LEVEL")


def test_rejects_invalid_service_names():
    with pytest.raises(InvalidConfigurationError):
        OperationsConfig(service_names=("",))
    with pytest.raises(InvalidConfigurationError):
        OperationsConfig(service_names=("nested/service",))
    with pytest.raises(InvalidConfigurationError):
        OperationsConfig(service_names=(" yasin-ai",))


def test_load_config_uses_defaults_when_env_empty():
    with patch.dict(os.environ, {}, clear=True):
        config = load_config()
    assert config == OperationsConfig()


def test_load_config_environment_overrides_defaults():
    env = {
        "YASIN_OPERATIONS_SERVICE_ROOT": "/tmp/services",
        "YASIN_OPERATIONS_SV_PATH": "/tmp/sv",
        "YASIN_OPERATIONS_SERVICE_NAMES": "yasinpress, yasin-ai, yasinpress",
        "YASIN_OPERATIONS_EXECUTION_TIMEOUT_SECONDS": "90",
        "YASIN_OPERATIONS_STARTUP_GRACE_SECONDS": "4.5",
        "YASIN_OPERATIONS_ALWAYS_ON": "false",
        "YASIN_OPERATIONS_LOG_LEVEL": "DEBUG",
    }
    with patch.dict(os.environ, env, clear=True):
        config = load_config()
    assert config.service_root == "/tmp/services"
    assert config.sv_path == "/tmp/sv"
    assert config.service_names == ("yasin-ai", "yasinpress")
    assert config.execution_timeout_seconds == 90
    assert config.startup_grace_seconds == 4.5
    assert config.always_on is False
    assert config.log_level == "DEBUG"


def test_explicit_overrides_win_over_environment():
    env = {
        "YASIN_OPERATIONS_SERVICE_ROOT": "/env/services",
        "YASIN_OPERATIONS_SERVICE_NAMES": "env-service",
        "YASIN_OPERATIONS_ALWAYS_ON": "true",
    }
    with patch.dict(os.environ, env, clear=True):
        config = load_config(
            {
                "service_root": "/cli/services",
                "service_names": ("cli-service",),
                "always_on": False,
            }
        )
    assert config.service_root == "/cli/services"
    assert config.service_names == ("cli-service",)
    assert config.always_on is False


def test_unknown_override_is_rejected():
    with pytest.raises(InvalidConfigurationError, match="unknown configuration"):
        load_config({"not_a_setting": True})


def test_load_config_invalid_env_values_raise_clear_errors():
    with patch.dict(
        os.environ, {"YASIN_OPERATIONS_EXECUTION_TIMEOUT_SECONDS": "not_a_number"}, clear=True
    ):
        with pytest.raises(InvalidConfigurationError, match="must be a number"):
            load_config()

    with patch.dict(
        os.environ, {"YASIN_OPERATIONS_ALWAYS_ON": "sometimes"}, clear=True
    ):
        with pytest.raises(InvalidConfigurationError, match="boolean"):
            load_config()


def test_missing_services_are_reported_without_mutation(tmp_path):
    root = tmp_path / "services"
    root.mkdir()
    (root / "present").mkdir()
    config = OperationsConfig(
        service_root=str(root),
        service_names=("missing", "present"),
    )
    assert config.missing_services() == ("missing",)
    assert (root / "present").is_dir()


def test_service_definitions_do_not_require_service_directories(tmp_path):
    config = OperationsConfig(
        service_root=str(tmp_path / "not-created"),
        service_names=("yasin-ai",),
    )
    definitions = config.service_definitions()
    assert len(definitions) == 1
    assert definitions[0].name == "yasin-ai"
    assert not Path(config.service_root).exists()
