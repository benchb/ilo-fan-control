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
