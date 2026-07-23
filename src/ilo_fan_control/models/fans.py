import logging
import tomllib
from dataclasses import dataclass
from enum import StrEnum
from importlib.resources import files
from pathlib import Path

from ilo_fan_control.env import CONFIGS_PATH
from ilo_fan_control.ilo.redfish import FanReading

logger = logging.getLogger(__name__)

DEFAULT_FAN_SETTING = 10


class FanNotFoundError(Exception):
    pass


class FanMode(StrEnum):
    AUTO = "auto"
    MANUAL = "manual"


@dataclass
class Fan:
    id: int
    name: str
    mode: FanMode = FanMode.AUTO
    speed: int | None = None
    setting: int = DEFAULT_FAN_SETTING
    enabled: bool = True

    def update_state(self, state: bool) -> None:
        """Updates whether the Fan is enabled or not in iLO.

        Args:
            state (bool): True if Fan is Enabled, False otherwise.
        """

        self.enabled = state

    def update_speed(self, speed: int | None) -> None:
        """Updates the Fan speed reading.

        Args:
            speed (int): Speed reading from iLO API. (in %)
        """

        if speed is None:
            self.speed = None
            return

        if not 0 <= speed <= 100:
            logger.error(
                f"Invalid speed value for Fan id number {self.id} (value={speed}). Skipping."
            )
            return

        self.speed = speed

    def set_auto(self):
        """Places iLO Fan in PID control mode."""

        if not self.enabled:
            logger.debug(f"Fan id number {self.id} is disabled. Skipping.")
            return

        # TODO: Call iLO

        self.mode = FanMode.AUTO

    def set_speed(self, setting: int):
        """Places iLO Fan in manual speed. It will use a user manual setting.

        Args:
            setting (int): Fan manual setting to apply. (in %)
        """

        if not self.enabled:
            logger.debug(f"Fan id number {self.id} is disabled. Skipping.")
            return

        if type(setting) is not int or not 0 <= setting <= 100:
            logger.error(
                f"Invalid setting for Fan id number {self.id} (value={setting}). Skipping."
            )
            return

        # TODO: Call iLO
        ...

        self.setting = setting
        self.mode = FanMode.MANUAL

    def __str__(self) -> str:
        speed = "unknown" if self.speed is None else f"{self.speed}%"

        return (
            f"Fan("
            f"id={self.id}, "
            f"name={self.name!r}, "
            f"mode={self.mode.value}, "
            f"speed={speed}, "
            f"setting={self.setting}%, "
            f"enabled={self.enabled}"
            f")"
        )


class Fans:
    def __init__(self, fan_readings: list[FanReading]):
        self._fans: list[Fan] = []
        self._fans_by_id: dict[int, Fan] = {}

        for reading in fan_readings:
            fan = Fan(
                id=reading.id,
                name=reading.name,
                speed=reading.speed_percentage,
                enabled=reading.state == "Enabled",
            )

            self._fans.append(fan)
            self._fans_by_id[fan.id] = fan

    def all(self) -> list[Fan]:
        """Return a list with the configured Fan instances.

        Returns:
            list[Fan]: List of Fan instances.
        """

        return self._fans.copy()

    def get(self, fan_id: int) -> Fan:
        """Return a specific Fan instance, by id.

        Args:
            fan_id (int): Integer iLO ID for the Fan.

        Raises:
            FanNotFoundError: Error if Fan not configured.

        Returns:
            Fan: Fan instance.
        """

        try:
            return self._fans_by_id[fan_id]
        except KeyError as error:
            raise FanNotFoundError(f"Fan id number {fan_id} was not found.") from error

    def exists(self, fan_id: int) -> bool:
        """Checks if a given Fan exists.

        Args:
            fan_id (int): Integer iLO Fan ID.

        Returns:
            bool: True if exists, false otherwise.
        """

        return fan_id in self._fans_by_id

    def get_settings(self) -> dict[int, int]:
        """Returns a Fans settings dictionary representation.

        Returns:
            dict[int, int]: Dictionary with fan_id and fan_setting pair.
        """

        return {fan.id: fan.setting for fan in self._fans if fan.enabled}

    def update_readings(self, fan_readings: list[FanReading]) -> None:
        """Updates the fan readings.

        Args:
            fan_readings (list[FanReading]): List of FanReading instances from the iLO Rest Client.
        """

        for reading in fan_readings:
            fan = self.get(reading.id)
            enabled = reading.state == "Enabled"

            fan.update_state(enabled)

            if enabled:
                fan.update_speed(reading.speed_percentage)
            else:
                fan.update_speed(None)

    def set_auto(self) -> None:
        """Sets all the Fans to auto mode."""

        for fan in self._fans:
            fan.set_auto()

    def set_manual(self, fan_settings: dict[int, int]) -> None:
        """Sets all the fans to manual mode at once.

        Args:
            fan_settings (dict[int, int]): Fans settings dictionary representation {fan_id:fan_setting, ...}.
        """
        for fan_id, setting in fan_settings.items():
            self.set_speed(fan_id, setting)

    def set_speed(self, fan_id: int, setting: int) -> None:
        """Sets a specific Fan to manual mode.

        Args:
            fan_id (int): Integer iLO Fan ID.
            setting (int): Setting value for speed of the Fan.
        """
        self.get(fan_id).set_speed(setting)

    def __str__(self) -> str:
        if not self._fans:
            return "Fans([])"

        entries = "\n".join(f"  {fan}" for fan in self._fans)

        return f"Fans[\n{entries}\n]"
