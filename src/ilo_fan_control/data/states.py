import json
import logging
import sqlite3
import time
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from uuid import uuid4

from ilo_fan_control.env import PERSISTENT_DATA_PATH, SILENT_FAN_SETTING
from ilo_fan_control.models.fans import FanMode, FanNotFoundError, Fans

logger = logging.getLogger(__name__)

DATABASE_PATH = PERSISTENT_DATA_PATH / "states.db"

SCHEMA = """
    CREATE TABLE IF NOT EXISTS profiles (
        id            TEXT PRIMARY KEY,
        name          TEXT NOT NULL COLLATE NOCASE UNIQUE,
        fan_settings  TEXT NOT NULL,
        created_at_ms INTEGER NOT NULL,
        updated_at_ms INTEGER NOT NULL
    );

    CREATE TABLE IF NOT EXISTS application_settings (
        key   TEXT PRIMARY KEY,
        value TEXT NOT NULL
    );
"""


class ProfileNameAlreadyExistsError(Exception):
    pass


class ProfileNotFoundError(Exception):
    pass


@contextmanager
def _connection() -> Iterator[sqlite3.Connection]:
    DATABASE_PATH.parent.mkdir(parents=True, exist_ok=True)

    connection = sqlite3.connect(
        DATABASE_PATH,
        timeout=5.0,
    )
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    connection.execute("PRAGMA busy_timeout = 5000")

    try:
        yield connection
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()


def _initialize_database() -> None:
    with _connection() as connection:
        connection.executescript(SCHEMA)


@dataclass()
class Profile:
    id: str
    name: str
    fan_settings: dict[int, int]

    def get_setting(self, fan_id: int) -> int | None:
        """Gets the profile setting for a given Fan.

        Args:
            fan_id (int): iLO fan identifier

        Raises:
            FanNotFoundError: If fan_id is not in the profile settings

        Returns:
            int | None: Returns the fan setting speed
        """
        try:
            return self.fan_settings[fan_id]
        except KeyError as error:
            raise FanNotFoundError(
                f"Fan id number {fan_id} was not found in '{self.name}' profile settings."
            ) from error

    def __str__(self) -> str:
        settings = ", ".join(
            f"{fan_id}: {setting}%" for fan_id, setting in sorted(self.fan_settings.items())
        )

        return f"Profile(id={self.id!r}, name={self.name!r}, fan_settings={{{settings}}})"


class Profiles:
    def __init__(self, configured_fans: Fans) -> None:
        self._configured_fans = configured_fans
        _initialize_database()

    def _safe_name(self, name: str) -> str:
        """Clears any extra spaces and makes sure the name is not too large.

        Args:
            name (str): Profile name

        Raises:
            ValueError: If name is not valid or is too big.

        Returns:
            str: Clean Profile name.
        """
        safe_name = name.strip()

        if not safe_name:
            raise ValueError("Profile name cannot be empty.")

        if len(safe_name) > 50:
            raise ValueError("Profile name cannot exceed 50 characters.")

        return safe_name

    def _safe_settings(
        self,
        profile_name: str,
        fan_settings: dict[int, int],
    ) -> dict[int, int]:
        """Validates the settings of a profile.

        Args:
            profile_name (str): Name of the profile.
            fan_settings (dict[int, int]): Fan settings to validate.

        Returns:
            dict[int, int]: Validated fan settings.
        """

        safe_settings: dict[int, int] = {}

        for fan_id, setting in fan_settings.items():
            # Ignore not configured fan_ids
            if not self._configured_fans.exists(fan_id):
                logger.warning(
                    f"Fan id number {fan_id} does not exist in configured Fans. Ignoring setting for '{profile_name}' profile..."
                )
                continue

            # Ignore invalid setting types
            if type(setting) is not int:
                logger.warning(
                    f"Invalid setting for fan id number {fan_id} in profile {profile_name}: {setting}"
                )
                continue

            # Cap setting value inside bounds
            safe_setting = max(0, min(100, setting))

            if safe_setting != setting:
                logger.info(
                    f"Fan id number {fan_id} setting in '{profile_name}' profile was capped from {setting}% to {safe_setting}%."
                )

            safe_settings[fan_id] = safe_setting

        # Warn for a profile created with no valid settings!
        if not safe_settings:
            logger.warning(f"Profile '{profile_name}' contains no valid fan settings.")

        # Add a default setting for every enabled fan missing from the profile.
        for fan in self._configured_fans.all():
            if fan.enabled:
                safe_settings.setdefault(fan.id, 0)

        return safe_settings

    def _from_row(
        self,
        row: sqlite3.Row,
    ) -> Profile:
        """Creates a Profile from a database row.

        Args:
            row (sqlite3.Row): Profile database row.

        Raises:
            ValueError: If the stored settings are invalid.

        Returns:
            Profile: Loaded profile.
        """

        # Try to load the json string from the database
        try:
            raw_settings = json.loads(row["fan_settings"])
        except json.JSONDecodeError as error:
            raise ValueError(f"Invalid fan settings stored for profile {row['id']}.") from error

        # Check if the parsed text is a dictionary
        if not isinstance(raw_settings, dict):
            raise ValueError(f"Invalid fan settings stored for profile {row['id']}.")

        fan_settings: dict[int, int] = {}

        # Check if the parsed fan id is a valid integer
        for fan_id, setting in raw_settings.items():
            try:
                parsed_fan_id = int(fan_id)
            except (TypeError, ValueError):
                logger.warning(
                    f"Invalid fan ID {fan_id} stored in profile '{row['name']}'. Ignoring."
                )
                continue

            fan_settings[parsed_fan_id] = setting

        return Profile(
            id=row["id"],
            name=row["name"],
            fan_settings=self._safe_settings(
                row["name"],
                fan_settings,
            ),
        )

    def create(self, name: str, fan_settings: dict[int, int]):
        """Creates a Profile for manual fan speeds in the database.

        Args:
            name (str): Verbose name for the profile.
            fan_settings (dict[int, int]): Key-value pair with fan ids and speed settings.

        Raises:
            ProfileNameAlreadyExistsError: If a profile with the same name already exists.

        Returns:
            Profile: Profile object of the created profile.
        """

        profile_id = str(uuid4())
        safe_name = self._safe_name(name)
        safe_settings = self._safe_settings(safe_name, fan_settings)
        timestamp_ms = int(time.time() * 1_000)
        values = (
            profile_id,
            safe_name,
            json.dumps(safe_settings, sort_keys=True),
            timestamp_ms,
            timestamp_ms,
        )

        try:
            with _connection() as connection:
                connection.execute(
                    "INSERT INTO profiles (id, name, fan_settings, created_at_ms, updated_at_ms) VALUES (?, ?, ?, ?, ?)",
                    values,
                )

        except sqlite3.IntegrityError as error:
            if "profiles.name" in str(error):
                raise ProfileNameAlreadyExistsError(safe_name) from error
            raise

        return Profile(id=profile_id, name=safe_name, fan_settings=safe_settings)

    def all(self) -> list[Profile]:
        """Retrieves a list of all Profiles in the database.

        Returns:
            list[Profile]: List of Profiles
        """

        with _connection() as connection:
            rows = connection.execute(
                """
                SELECT id, name, fan_settings
                FROM profiles
                ORDER BY name COLLATE NOCASE
                """
            ).fetchall()

        return [self._from_row(row) for row in rows]

    def get(self, profile_id: str) -> Profile:
        """Gets a single Profile data from the database.

        Args:
            profile_id (str): UUID of the Profile

        Raises:
            ProfileNotFoundError: If UUID does not exist in the database.

        Returns:
            Profile: Profile object.
        """

        with _connection() as connection:
            row = connection.execute(
                """
                SELECT id, name, fan_settings
                FROM profiles
                WHERE id = ?
                """,
                (profile_id,),
            ).fetchone()

        if row is None:
            raise ProfileNotFoundError(profile_id)

        return self._from_row(row)

    def exists(self, profile_id: str) -> bool:
        """Checks if a profile exists.

        Args:
            profile_id (str): UUID of the profile.

        Returns:
            bool: True if the profile exists.
        """

        try:
            self.get(profile_id)
            return True
        except ProfileNotFoundError:
            return False

    def update(
        self,
        profile_id: str,
        *,
        name: str | None = None,
        fan_settings: dict[int, int] | None = None,
    ) -> Profile:
        """Updates an existing Profile in the database

        Args:
            profile_id (str): UUID of the Profile
            name (str | None, optional): New verbose name for the profile. Defaults to None.
            fan_settings (dict[int, int] | None, optional): New key-value pair with fan ids and speed settings. Defaults to None.

        Raises:
            ProfileNotFoundError: If UUID does not exist in the database.
            ProfileNameAlreadyExistsError: If another Profile already contains the same name. Names must be UNIQUE.

        Returns:
            Profile: Updated Profile object.
        """

        current_profile = self.get(profile_id)

        safe_name = self._safe_name(name) if name is not None else current_profile.name

        safe_settings = (
            self._safe_settings(
                safe_name,
                fan_settings,
            )
            if fan_settings is not None
            else current_profile.fan_settings
        )

        updated_at_ms = int(time.time() * 1_000)

        try:
            with _connection() as connection:
                connection.execute(
                    """
                    UPDATE profiles
                    SET
                        name = ?,
                        fan_settings = ?,
                        updated_at_ms = ?
                    WHERE id = ?
                    """,
                    (
                        safe_name,
                        json.dumps(safe_settings, sort_keys=True),
                        updated_at_ms,
                        profile_id,
                    ),
                )

        except sqlite3.IntegrityError as error:
            if "profiles.name" in str(error):
                raise ProfileNameAlreadyExistsError(safe_name) from error
            raise

        return Profile(
            id=profile_id,
            name=safe_name,
            fan_settings=safe_settings,
        )

    def delete(self, profile_id: str) -> None:
        """Deletes a Profile from the database

        Args:
            profile_id (str): UUID of the Profile.

        Raises:
            ProfileNotFoundError: If the UUID was not found in the database.
        """

        with _connection() as connection:
            cursor = connection.execute(
                """
                DELETE FROM profiles
                WHERE id = ?
                """,
                (profile_id,),
            )

            if cursor.rowcount == 0:
                raise ProfileNotFoundError(profile_id)


class AppState:
    APP_STATE_VERSION = 1

    def __init__(self, configured_fans: Fans, profiles: Profiles) -> None:
        self._configured_fans = configured_fans
        self._profiles = profiles

        # Get default values before loading
        self.mode = FanMode.AUTO
        self.selected_profile_id: str | None = None
        self.manual_fan_settings: dict[int, int] = self._default_settings()

        _initialize_database()
        self._load()

    def _default_settings(self) -> dict[int, int]:
        """Creates the default manual fan settings.

        Returns:
            dict[int, int]: Default settings for enabled fans.
        """

        return {fan.id: SILENT_FAN_SETTING for fan in self._configured_fans.all() if fan.enabled}

    def _safe_settings(
        self,
        fan_settings: dict[int, int],
    ) -> dict[int, int]:
        """Validates manual fan settings.

        Args:
            fan_settings (object): Settings to validate.

        Returns:
            dict[int, int]: Validated fan settings.
        """

        # Retrieve initial base settings
        safe_settings = self._default_settings()

        if not isinstance(fan_settings, dict):
            logger.warning(
                "Invalid manual fan settings in application state. Using default settings."
            )
            return safe_settings

        # Validate each given fan_id and setting
        for raw_fan_id, setting in fan_settings.items():
            # Handle wrong id type
            try:
                fan_id = int(raw_fan_id)
            except (TypeError, ValueError):
                logger.warning(f"Invalid fan id {raw_fan_id} in application state. Ignoring.")
                continue

            # Handle non existing fan id
            if not self._configured_fans.exists(fan_id):
                logger.warning(f"Fan id number {fan_id} is not configured. Ignoring.")
                continue

            fan = self._configured_fans.get(fan_id)

            # Ignore if the fan is disabled
            if not fan.enabled:
                continue

            # Type check the setting type
            if type(setting) is not int:
                logger.warning(f"Invalid manual setting for fan {fan_id}: {setting}. Ignoring.")
                continue

            # Update fan_id setting in the initial safe settings.
            safe_settings[fan_id] = max(0, min(100, setting))

        return safe_settings

    def _load(self) -> None:
        """Loads the stored state and initializes the fans."""

        # Get app state from the database
        with _connection() as connection:
            row = connection.execute(
                "SELECT value FROM application_settings WHERE key = 'app_state'"
            ).fetchone()

        # Save current default state if no state found in the database
        if row is None:
            logger.info("No application state found. Creating default state.")
            self.save()
            return

        # Parse the stored json
        try:
            raw_state = json.loads(row["value"])
        except json.JSONDecodeError:
            logger.exception("Invalid application state JSON. Using default state.")
            self.save()
            return

        # Check if parsed state is a dictionary
        if not isinstance(raw_state, dict):
            logger.warning("Invalid application state. Using default state.")
            self.save()
            return

        # Get last selected Fan mode
        try:
            self.mode = FanMode(raw_state.get("mode", FanMode.AUTO))
        except ValueError:
            logger.warning(f"Invalid application mode {raw_state.get('mode')}. Using Auto.")
            self.mode = FanMode.AUTO

        # Safely get last manual fan settings
        self.manual_fan_settings = self._safe_settings(raw_state.get("manual_fan_settings", {}))

        # Initialize Fans state from the last known AppState
        if self.mode == FanMode.MANUAL:
            # Set each Fan to the last stored setting
            self._configured_fans.set_manual(self.manual_fan_settings.copy())

            # Set the selected profile if valid
            selected_profile_id = raw_state.get("selected_profile_id", None)
            if self._profiles.exists(selected_profile_id):
                self.selected_profile_id = selected_profile_id
            else:
                self.selected_profile_id = None

        elif self.mode == FanMode.SILENT:
            self._configured_fans.set_silent()
            self.selected_profile_id = None
        else:
            self._configured_fans.set_auto()
            self.selected_profile_id = None

    def save(self) -> None:
        """Saves the current application state."""

        serialized_state = json.dumps(
            self.as_dict(),
            sort_keys=True,
        )

        with _connection() as connection:
            connection.execute(
                """
                INSERT INTO application_settings (
                    key,
                    value
                )
                VALUES ('app_state', ?)
                ON CONFLICT(key) DO UPDATE SET
                    value = excluded.value
                """,
                (serialized_state,),
            )

    def get_fan_settings(self) -> dict[int, int]:
        """Gets the stored manual fan settings.

        Returns:
            dict[int, int]: Copy of the manual fan settings.
        """
        return self.manual_fan_settings.copy()

    def set_auto(self) -> None:
        """Stores automatic mode as the current mode."""

        self.mode = FanMode.AUTO
        self.selected_profile_id = None
        self.save()

    def set_manual(self, fan_settings: dict[int, int] | None = None) -> None:
        """Stores manual mode and its fan settings.

        Args:
            fan_settings (dict[int, int] | None, optional): Manual fan settings.
                Existing settings are kept when omitted.
        """

        self.mode = FanMode.MANUAL
        self.selected_profile_id = None

        # Update fan_settings if given
        if fan_settings is not None:
            self.manual_fan_settings = self._safe_settings(fan_settings)

        self.save()

    def set_silent(self) -> None:
        """Stores silent mode as the current mode."""

        self.mode = FanMode.SILENT
        self.selected_profile_id = None
        self.save()

    def set_profile(self, profile_id: str) -> None:
        """Stores a profile as the active manual configuration.

        Args:
            profile_id (str): UUID of the profile.
        """

        if not self._profiles.exists(profile_id):
            return

        profile = self._profiles.get(profile_id)

        self.mode = FanMode.MANUAL
        self.selected_profile_id = profile.id
        self.manual_fan_settings = profile.fan_settings.copy()

        self.save()

    def as_dict(self) -> dict[str, object]:
        """Gets the application state as a dictionary.

        Returns:
            dict[str, object]: Serializable application state.
        """

        return {
            "version": self.APP_STATE_VERSION,
            "mode": self.mode.value,
            "selected_profile_id": self.selected_profile_id,
            "manual_fan_settings": (self.manual_fan_settings.copy()),
        }

    def __str__(self) -> str:
        return json.dumps(
            self.as_dict(),
            indent=2,
            sort_keys=True,
        )
