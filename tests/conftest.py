from pathlib import Path

import pytest

import ilo_fan_control.data.states as states_module
from ilo_fan_control.ilo.redfish import FanReading
from ilo_fan_control.models.fans import Fans


@pytest.fixture
def fan_readings() -> list[FanReading]:
    return [
        FanReading(
            id=0,
            name="Fan 1",
            speed_percentage=20,
            state="Enabled",
            health="OK",
        ),
        FanReading(
            id=1,
            name="Fan 2",
            speed_percentage=30,
            state="Enabled",
            health="OK",
        ),
        FanReading(
            id=2,
            name="Fan 3",
            speed_percentage=None,
            state="Disabled",
            health=None,
        ),
    ]


@pytest.fixture
def configured_fans(
    fan_readings: list[FanReading],
) -> Fans:
    return Fans(fan_readings)


@pytest.fixture
def profiles_config(tmp_path: Path) -> Path:
    config_file = tmp_path / "profiles.toml"
    config_file.write_text(
        """
[[profiles]]
id = "silent"
name = "Sleep"
description = "As low as possible for a good night's sleep."
fa_icon = "moon"

[profiles.fan_settings]
0 = 8
1 = 8
""".strip(),
        encoding="utf-8",
    )
    return config_file


@pytest.fixture
def isolated_state_storage(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    profiles_config: Path,
) -> Path:
    database_path = tmp_path / "states.db"

    monkeypatch.setattr(
        states_module,
        "DATABASE_PATH",
        database_path,
    )
    monkeypatch.setattr(
        states_module,
        "ensure_config_file",
        lambda: profiles_config,
    )

    return database_path
