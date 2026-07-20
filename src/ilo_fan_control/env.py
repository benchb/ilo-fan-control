import logging
import os
from pathlib import Path

logger = logging.getLogger("uvicorn.error")

# Usefull paths
PACKAGE_SOURCE_DIRECTORY = Path(__file__).resolve().parent

# Default app paths
DEFAULT_PERSISTENT_DATA_PATH = Path.home() / ".local/share/ilo-fan-control"
DEFAULT_CONFIGS_PATH = Path.home() / ".config/ilo-fan-control"

# Safely get definitive paths
PERSISTENT_DATA_PATH = Path(
    os.getenv(
        "ILO_FAN_CONTROL_PERSISTENT_DATA_PATH",
        DEFAULT_PERSISTENT_DATA_PATH,
    )
)

CONFIGS_PATH = Path(
    os.getenv(
        "ILO_FAN_CONTROL_CONFIGS_PATH",
        DEFAULT_CONFIGS_PATH,
    )
)

# Make sure the paths exist
PERSISTENT_DATA_PATH.mkdir(parents=True, exist_ok=True)
CONFIGS_PATH.mkdir(parents=True, exist_ok=True)

# Import silent fan setting
DEFAULT_SILENT_FAN_SETTING = 5

try:
    SILENT_FAN_SETTING = int(
        os.getenv(
            "ILO_FAN_CONTROL_SILENT_FAN_SETTING",
            DEFAULT_SILENT_FAN_SETTING,
        )
    )
except ValueError:
    logger.warning(
        f"Invalid value for 'ILO_FAN_CONTROL_SILENT_FAN_SETTING'. Using default: {DEFAULT_SILENT_FAN_SETTING}"
    )
    SILENT_FAN_SETTING = DEFAULT_SILENT_FAN_SETTING

if not 1 <= SILENT_FAN_SETTING <= 100:
    logger.warning(
        f"'ILO_FAN_CONTROL_SILENT_FAN_SETTING' must be between 1 and 100. Using default: {DEFAULT_SILENT_FAN_SETTING}"
    )
    SILENT_FAN_SETTING = DEFAULT_SILENT_FAN_SETTING

# Load iLO administrator account info (make it fail if absent)
try:
    ILO_HOST = os.getenv("ILO_HOST")
    ILO_ADMIN_USER = os.getenv("ILO_ADMIN_USER")
    ILO_ADMIN_PASSWORD = os.getenv("ILO_ADMIN_PASSWORD")

    missing_variables = [
        name
        for name, value in {
            "ILO_HOST": ILO_HOST,
            "ILO_ADMIN_USER": ILO_ADMIN_USER,
            "ILO_ADMIN_PASSWORD": ILO_ADMIN_PASSWORD,
        }.items()
        if not value or not value.strip()
    ]

    if missing_variables:
        raise ValueError(f"Missing required environment variables: {', '.join(missing_variables)}")

    ILO_HOST = ILO_HOST.strip()
    ILO_ADMIN_USER = ILO_ADMIN_USER.strip()
    ILO_ADMIN_PASSWORD = ILO_ADMIN_PASSWORD.strip()

except ValueError as error:
    logger.critical(f"Failed to load iLO administrator account information: {error}")
    raise
except Exception:
    logger.exception(
        "An unexpected error happened while loading iLO administrator account information."
    )
    raise
