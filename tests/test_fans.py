import pytest

from ilo_fan_control.models.fans import (
    FanMode,
    FanNotFoundError,
    Fans,
)


def test_fans_load_and_change_modes(configured_fans: Fans) -> None:
    assert [fan.id for fan in configured_fans.all()] == [0, 1, 2]
    assert configured_fans.exists(0)
    assert not configured_fans.exists(99)

    configured_fans.set_manual({0: 20, 1: 30, 2: 40})

    assert configured_fans.get(0).mode is FanMode.MANUAL
    assert configured_fans.get(0).setting == 20
    assert configured_fans.get(1).mode is FanMode.MANUAL
    assert configured_fans.get(1).setting == 30
    assert configured_fans.get(2).mode is FanMode.AUTO
    assert configured_fans.get_settings() == {0: 20, 1: 30}

    configured_fans.set_silent()
    assert configured_fans.get(0).mode is FanMode.SILENT
    assert configured_fans.get(1).mode is FanMode.SILENT
    assert configured_fans.get(2).mode is FanMode.AUTO

    configured_fans.set_auto()
    assert configured_fans.get(0).mode is FanMode.AUTO
    assert configured_fans.get(1).mode is FanMode.AUTO


def test_invalid_values_and_unknown_fans_are_rejected(
    configured_fans: Fans,
) -> None:
    configured_fans.update_speed(0, 45)
    configured_fans.update_speed(0, 101)
    assert configured_fans.get(0).speed == 45

    configured_fans.set_speed(0, 25)
    configured_fans.set_speed(0, True)
    assert configured_fans.get(0).setting == 25
    assert configured_fans.get(0).mode is FanMode.MANUAL

    with pytest.raises(FanNotFoundError):
        configured_fans.get(99)
