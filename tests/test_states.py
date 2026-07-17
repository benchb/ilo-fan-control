from pathlib import Path

import pytest

import ilo_fan_control.data.states as states_module
import ilo_fan_control.models.fans as fans_module
from ilo_fan_control.data.states import (
    AppState,
    ProfileNameAlreadyExistsError,
    ProfileNotFoundError,
    Profiles,
)
from ilo_fan_control.models.fans import FanMode, Fans


def test_profiles_crud_and_validation(
    configured_fans: Fans,
    isolated_database: Path,
) -> None:
    profiles = Profiles(configured_fans)

    quiet = profiles.create(
        "  Quiet  ",
        {
            0: 120,
            99: 50,
        },
    )

    assert quiet.name == "Quiet"
    assert quiet.fan_settings == {0: 100, 1: 0}
    assert profiles.get(quiet.id) == quiet
    assert profiles.exists(quiet.id)

    performance = profiles.create(
        "Performance",
        {0: 60, 1: 70},
    )

    with pytest.raises(ProfileNameAlreadyExistsError):
        profiles.create("quiet", {0: 10, 1: 10})

    updated = profiles.update(
        quiet.id,
        name="Balanced",
        fan_settings={0: 30, 1: 40},
    )
    assert updated.name == "Balanced"
    assert updated.fan_settings == {0: 30, 1: 40}

    profiles.delete(performance.id)
    assert not profiles.exists(performance.id)

    with pytest.raises(ProfileNotFoundError):
        profiles.get(performance.id)


def test_app_state_restores_persisted_manual_profile(
    configured_fans: Fans,
    isolated_database: Path,
) -> None:
    profiles = Profiles(configured_fans)
    app_state = AppState(configured_fans, profiles)

    assert app_state.mode is FanMode.AUTO
    assert app_state.get_fan_settings() == {
        0: states_module.SILENT_FAN_SETTING,
        1: states_module.SILENT_FAN_SETTING,
    }

    profile = profiles.create(
        "Gaming",
        {0: 25, 1: 35},
    )
    app_state.set_profile(profile.id)

    restarted_fans = fans_module.Fans()
    restarted_profiles = Profiles(restarted_fans)
    restored_state = AppState(
        restarted_fans,
        restarted_profiles,
    )

    assert restored_state.mode is FanMode.MANUAL
    assert restored_state.selected_profile_id == profile.id
    assert restored_state.get_fan_settings() == {0: 25, 1: 35}
    assert restarted_fans.get(0).mode is FanMode.MANUAL
    assert restarted_fans.get(0).setting == 25
    assert restarted_fans.get(1).mode is FanMode.MANUAL
    assert restarted_fans.get(1).setting == 35
    assert restarted_fans.get(2).mode is FanMode.AUTO
