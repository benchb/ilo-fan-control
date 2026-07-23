from pathlib import Path

import pytest

from ilo_fan_control.data.states import (
    AppState,
    BuiltinProfileModificationError,
    ProfileNameAlreadyExistsError,
    ProfileNotFoundError,
    ProfileSource,
    Profiles,
)
from ilo_fan_control.ilo.redfish import FanReading
from ilo_fan_control.models.fans import (
    DEFAULT_FAN_SETTING,
    FanMode,
    Fans,
)


def test_profiles_builtin_and_user_crud(
    configured_fans: Fans,
    isolated_state_storage: Path,
) -> None:
    profiles = Profiles(configured_fans)

    builtin = profiles.get("silent")

    assert builtin.name == "Sleep"
    assert builtin.description == ("As low as possible for a good night's sleep.")
    assert builtin.fa_icon == "moon"
    assert builtin.source is ProfileSource.BUILTIN
    assert builtin.fan_settings == {0: 8, 1: 8}
    assert not builtin.editable
    assert not builtin.deletable

    quiet = profiles.create(
        "  Quiet  ",
        {
            0: 120,
            99: 50,
        },
        description="Low-noise user profile.",
        fa_icon="volume-low",
    )

    assert quiet.name == "Quiet"
    assert quiet.description == "Low-noise user profile."
    assert quiet.fa_icon == "volume-low"
    assert quiet.source is ProfileSource.USER
    assert quiet.fan_settings == {
        0: 100,
        1: DEFAULT_FAN_SETTING,
    }
    assert profiles.get(quiet.id) == quiet
    assert profiles.exists(quiet.id)

    performance = profiles.create(
        "Performance",
        {0: 60, 1: 70},
    )

    with pytest.raises(ProfileNameAlreadyExistsError):
        profiles.create(
            "quiet",
            {0: 10, 1: 10},
        )

    updated = profiles.update(
        quiet.id,
        name="Balanced",
        description="Balanced user profile.",
        fa_icon="scale-balanced",
        fan_settings={0: 30, 1: 40},
    )

    assert updated.name == "Balanced"
    assert updated.description == "Balanced user profile."
    assert updated.fa_icon == "scale-balanced"
    assert updated.fan_settings == {
        0: 30,
        1: 40,
    }

    with pytest.raises(BuiltinProfileModificationError):
        profiles.update(
            builtin.id,
            name="Changed",
        )

    with pytest.raises(BuiltinProfileModificationError):
        profiles.delete(builtin.id)

    profiles.delete(performance.id)
    assert not profiles.exists(performance.id)

    with pytest.raises(ProfileNotFoundError):
        profiles.get(performance.id)


def test_app_state_restores_persisted_user_profile(
    configured_fans: Fans,
    fan_readings: list[FanReading],
    isolated_state_storage: Path,
) -> None:
    profiles = Profiles(configured_fans)
    app_state = AppState(
        configured_fans,
        profiles,
    )

    assert app_state.mode is FanMode.AUTO
    assert app_state.selected_profile_id is None
    assert app_state.get_fan_settings() == {
        0: DEFAULT_FAN_SETTING,
        1: DEFAULT_FAN_SETTING,
    }

    profile = profiles.create(
        "Gaming",
        {0: 25, 1: 35},
    )
    app_state.set_profile(profile.id)

    restarted_fans = Fans(fan_readings)
    restarted_profiles = Profiles(restarted_fans)
    restored_state = AppState(
        restarted_fans,
        restarted_profiles,
    )

    assert restored_state.mode is FanMode.MANUAL
    assert restored_state.selected_profile_id == profile.id
    assert restored_state.get_fan_settings() == {
        0: 25,
        1: 35,
    }

    assert restarted_fans.get(0).mode is FanMode.MANUAL
    assert restarted_fans.get(0).setting == 25
    assert restarted_fans.get(1).mode is FanMode.MANUAL
    assert restarted_fans.get(1).setting == 35

    # Disabled fans remain untouched.
    assert restarted_fans.get(2).mode is FanMode.AUTO


def test_app_state_restores_builtin_profile(
    configured_fans: Fans,
    fan_readings: list[FanReading],
    isolated_state_storage: Path,
) -> None:
    profiles = Profiles(configured_fans)
    app_state = AppState(
        configured_fans,
        profiles,
    )

    app_state.set_profile("silent")

    restarted_fans = Fans(fan_readings)
    restarted_profiles = Profiles(restarted_fans)
    restored_state = AppState(
        restarted_fans,
        restarted_profiles,
    )

    assert restored_state.mode is FanMode.MANUAL
    assert restored_state.selected_profile_id == "silent"
    assert restored_state.get_fan_settings() == {
        0: 8,
        1: 8,
    }
    assert restarted_fans.get(0).setting == 8
    assert restarted_fans.get(1).setting == 8
