from pathlib import Path

import pytest

import ilo_fan_control.data.states as states_module
import ilo_fan_control.models.fans as fans_module


@pytest.fixture
def fan_config(tmp_path: Path) -> Path:
    config_file = tmp_path / "fans.toml"
    config_file.write_text(
        """
[[fans]]
id = 0
name = "Fan 1"
enabled = true

[[fans]]
id = 1
name = "Fan 2"
enabled = true

[[fans]]
id = 2
name = "Disabled Fan"
enabled = false
""".strip(),
        encoding="utf-8",
    )
    return config_file


@pytest.fixture
def configured_fans(
    monkeypatch: pytest.MonkeyPatch,
    fan_config: Path,
) -> fans_module.Fans:
    monkeypatch.setattr(
        fans_module,
        "ensure_config_file",
        lambda: fan_config,
    )
    return fans_module.Fans()


@pytest.fixture
def isolated_database(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> Path:
    database_path = tmp_path / "states.db"
    monkeypatch.setattr(
        states_module,
        "DATABASE_PATH",
        database_path,
    )
    return database_path
