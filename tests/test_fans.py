import pytest

from ilo_fan_control.ilo.redfish import FanReading
from ilo_fan_control.models.fans import (
    FanMode,
    FanNotFoundError,
    Fans,
)


def test_fans_load_and_change_modes(
    configured_fans: Fans,
) -> None:
    assert [fan.id for fan in configured_fans.all()] == [0, 1, 2]
    assert configured_fans.exists(0)
    assert not configured_fans.exists(99)

    configured_fans.set_manual(
        {
            0: 20,
            1: 30,
            2: 40,
        }
    )

    assert configured_fans.get(0).mode is FanMode.MANUAL
    assert configured_fans.get(0).setting == 20
    assert configured_fans.get(1).mode is FanMode.MANUAL
    assert configured_fans.get(1).setting == 30

    # Disabled fans ignore mode and setting changes.
    assert configured_fans.get(2).mode is FanMode.AUTO
    assert configured_fans.get_settings() == {
        0: 20,
        1: 30,
    }

    configured_fans.set_auto()

    assert configured_fans.get(0).mode is FanMode.AUTO
    assert configured_fans.get(1).mode is FanMode.AUTO
    assert configured_fans.get(2).mode is FanMode.AUTO


def test_fans_update_redfish_readings(
    configured_fans: Fans,
) -> None:
    configured_fans.update_readings(
        [
            FanReading(
                id=0,
                name="Fan 1",
                speed_percentage=45,
                state="Enabled",
                health="OK",
            ),
            FanReading(
                id=1,
                name="Fan 2",
                speed_percentage=50,
                state="Disabled",
                health=None,
            ),
            FanReading(
                id=2,
                name="Fan 3",
                speed_percentage=35,
                state="Enabled",
                health="OK",
            ),
        ]
    )

    assert configured_fans.get(0).speed == 45
    assert configured_fans.get(0).enabled

    assert configured_fans.get(1).speed is None
    assert not configured_fans.get(1).enabled

    assert configured_fans.get(2).speed == 35
    assert configured_fans.get(2).enabled


def test_invalid_values_and_unknown_fans_are_rejected(
    configured_fans: Fans,
) -> None:
    fan = configured_fans.get(0)

    fan.update_speed(45)
    fan.update_speed(101)
    assert fan.speed == 45

    configured_fans.set_speed(0, 25)
    configured_fans.set_speed(0, True)

    assert fan.setting == 25
    assert fan.mode is FanMode.MANUAL

    with pytest.raises(FanNotFoundError):
        configured_fans.get(99)
