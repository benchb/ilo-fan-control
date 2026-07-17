import logging
import tomllib
from dataclasses import dataclass
from enum import StrEnum
from importlib.resources import files
from pathlib import Path

from ilo_fan_control.env import CONFIGS_PATH, SILENT_FAN_SETTING

logger = logging.getLogger(__name__)

DEFAULT_CONFIG_FILE = files("ilo_fan_control.defaults").joinpath("fans.toml")
CONFIG_FILE = CONFIGS_PATH / "fans.toml"


def ensure_config_file() -> Path:
    if not CONFIG_FILE.exists():
        logger.info(f"Creating default fan configuration file at {CONFIG_FILE}")
        CONFIG_FILE.write_bytes(DEFAULT_CONFIG_FILE.read_bytes())

    return CONFIG_FILE


class FanConfigurationError(Exception):
    pass


class FanNotFoundError(Exception):
    pass


class FanMode(StrEnum):
    AUTO = "auto"
    SILENT = "silent"
    MANUAL = "manual"


@dataclass
class Fan:
    id: int
    name: str
    mode: FanMode = FanMode.AUTO
    speed: int | None = None
    setting: int = SILENT_FAN_SETTING
    enabled: bool = True

    def update_speed(self, speed: int) -> None:
        """Updates the Fan speed reading.

        Args:
            speed (int): Speed reading from iLO API. (in %)
        """

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

    def set_silent(self):
        """Places iLO Fan in manual speed. It uses whatever is the 'ILO_FAN_CONTROL_SILENT_FAN_SETTING'."""

        if not self.enabled:
            logger.debug(f"Fan id number {self.id} is disabled. Skipping.")
            return

        # TODO: Call iLO
        ...

        self.mode = FanMode.SILENT

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
    def __init__(self):
        self._config_file = ensure_config_file()
        self._fans = self._load(self._config_file)
        self._fans_by_id = {fan.id: fan for fan in self._fans}

        if len(self._fans_by_id) != len(self._fans):
            raise FanConfigurationError("Duplicate fan IDs in configuration.")

    @staticmethod
    def _load(
        config_file: Path,
    ) -> list[Fan]:
        """Loads the Fans list from the TOML configuration file.

        Args:
            config_file (Path): _description_

        Raises:
            FanConfigurationError: Raised if any problem is found with the TOML file or its contents

        Returns:
            list[Fan]: List with Fan objects
        """

        try:
            with config_file.open("rb") as file:
                config = tomllib.load(file)
        except tomllib.TOMLDecodeError as error:
            raise FanConfigurationError(f"Invalid fan configuration: {error}") from error

        configured_fans = config.get("fans")

        if not isinstance(configured_fans, list):
            raise FanConfigurationError("Missing [[fans]] configuration.")

        fans: list[Fan] = []

        for configured_fan in configured_fans:
            try:
                fan = Fan(
                    id=configured_fan["id"],
                    name=configured_fan["name"],
                    enabled=configured_fan.get(
                        "enabled",
                        True,
                    ),
                )
            except KeyError as error:
                raise FanConfigurationError(f"Missing fan property: {error.args[0]}") from error

            fans.append(fan)

        logger.info(
            "Loaded %d fans from %s",
            len(fans),
            config_file,
        )

        return fans

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

    def update_speed(self, fan_id: int, speed: int) -> None:
        """Updates the speed reading value.

        Args:
            fan_id (int): Integer Fan ID.
            speed (int): New reading value (in %).
        """

        self.get(fan_id).update_speed(speed)

    def set_auto(self) -> None:
        """Sets all the Fans to auto mode."""

        for fan in self._fans:
            fan.set_auto()

    def set_silent(self) -> None:
        """Sets all the Fans to silent mode."""

        for fan in self._fans:
            fan.set_silent()

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
