import os
from unittest.mock import patch

import pytest

from yasin_operations.config.config import (
    InvalidConfigurationError,
    OperationsConfig,
    load_config,
)


def test_defaults():
    config = OperationsConfig()
    assert config.execution_timeout_seconds == 30
    assert config.log_level == "INFO"


def test_explicit_construction():
    config = OperationsConfig(execution_timeout_seconds=60, log_level="DEBUG")
    assert config.execution_timeout_seconds == 60
    assert config.log_level == "DEBUG"


def test_rejects_non_positive_timeout():
    with pytest.raises(InvalidConfigurationError):
        OperationsConfig(execution_timeout_seconds=0)


def test_rejects_negative_timeout():
    with pytest.raises(InvalidConfigurationError):
        OperationsConfig(execution_timeout_seconds=-5)


def test_rejects_invalid_log_level():
    with pytest.raises(InvalidConfigurationError):
        OperationsConfig(log_level="NOT_A_LEVEL")


def test_load_config_uses_defaults_when_env_empty():
    with patch.dict(os.environ, {}, clear=True):
        config = load_config()
    assert config.execution_timeout_seconds == 30
    assert config.log_level == "INFO"


def test_load_config_env_override():
    env = {
        "YASIN_OPERATIONS_EXECUTION_TIMEOUT_SECONDS": "90",
        "YASIN_OPERATIONS_LOG_LEVEL": "DEBUG",
    }
    with patch.dict(os.environ, env, clear=True):
        config = load_config()
    assert config.execution_timeout_seconds == 90
    assert config.log_level == "DEBUG"


def test_load_config_invalid_env_timeout_raises():
    with patch.dict(
        os.environ, {"YASIN_OPERATIONS_EXECUTION_TIMEOUT_SECONDS": "not_a_number"}, clear=True
    ):
        with pytest.raises(InvalidConfigurationError):
            load_config()


def test_load_config_invalid_env_log_level_raises():
    with patch.dict(
        os.environ, {"YASIN_OPERATIONS_LOG_LEVEL": "NOT_A_LEVEL"}, clear=True
    ):
        with pytest.raises(InvalidConfigurationError):
            load_config()
