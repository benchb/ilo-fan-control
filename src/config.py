import os
from pathlib import Path

# Load iLO configuration from container environment variables
ILO_HOST = os.environ["ILO_HOST"]
ILO_USER = os.environ["ILO_USER"]
ILO_PASS = os.environ["ILO_PASS"]

# CONFIGURE FOLDERS
__current_dir = Path(__file__)
STATIC_DIR = __current_dir.parent / "static"
TEMPLATES_DIR = __current_dir.parent / "templates"

# Background polling configuration
POLL_INTERVAL = 2 # seconds

# Fans configuration
FANS = [
    {"id": 0, "name": "Fan 1", "verbose-name": "Fan #1", "enabled": True},
    {"id": 1, "name": "Fan 2", "verbose-name": "Fan #2", "enabled": True},
    {"id": 2, "name": "Fan 3", "verbose-name": "Fan #3", "enabled": True},
    {"id": 3, "name": "Fan 4", "verbose-name": "Fan #4", "enabled": True},
    {"id": 4, "name": "Fan 5", "verbose-name": "Fan #5", "enabled": True},
    {"id": 5, "name": "Fan 6", "verbose-name": "Fan #6", "enabled": True},
    {"id": 6, "name": "Fan 7", "verbose-name": "Fan #7", "enabled": True}, 
    {"id": 7, "name": "Fan 8", "verbose-name": "Fan #8", "enabled": True},
]

TEMPERATURE_SENSORS = [
    {"name": "01-Inlet Ambient", "id": 1, "verbose-name": "Inlet", "enabled": True, "safe-max": 70},
    {"name": "02-CPU 1", "id": 2, "verbose-name": "CPU 1", "enabled": True, "safe-max": 85},
    {"name": "03-CPU 2", "id": 3, "verbose-name": "CPU 2", "enabled": True, "safe-max": 85},
    {"name": "04-P1 DIMM 1-3", "id": 4, "verbose-name": "P1 DIMM 1–3", "enabled": True, "safe-max": 85},
    {"name": "05-P1 DIMM 4-6", "id": 5, "verbose-name": "P1 DIMM 4–6", "enabled": True, "safe-max": 85},
    {"name": "06-P1 DIMM 7-9", "id": 6, "verbose-name": "P1 DIMM 7–9", "enabled": True, "safe-max": 85},
    {"name": "07-P1 DIMM 10-12", "id": 7, "verbose-name": "P1 DIMM 10–12", "enabled": True, "safe-max": 85},
    {"name": "08-P2 DIMM 1-3", "id": 8, "verbose-name": "P2 DIMM 1–3", "enabled": True, "safe-max": 85},
    {"name": "09-P2 DIMM 4-6", "id": 9, "verbose-name": "P2 DIMM 4–6", "enabled": True, "safe-max": 85},
    {"name": "10-P2 DIMM 7-9", "id": 10, "verbose-name": "P2 DIMM 7–9", "enabled": True, "safe-max": 85},
    {"name": "11-P2 DIMM 10-12", "id": 11, "verbose-name": "P2 DIMM 10–12", "enabled": True, "safe-max": 85},
    {"name": "12-HD Max", "id": 12, "verbose-name": "Hard Drive Max", "enabled": False, "safe-max": 80},
    {"name": "13-Chipset", "id": 13, "verbose-name": "Chipset", "enabled": False, "safe-max": 85},
    {"name": "14-P/S 1", "id": 14, "verbose-name": "Power Supply 1", "enabled": False, "safe-max": 80},
    {"name": "15-P/S 2", "id": 15, "verbose-name": "Power Supply 2", "enabled": False, "safe-max": 80},
    {"name": "16-P/S 2 Zone", "id": 16, "verbose-name": "PSU 2 Zone", "enabled": True, "safe-max": 75},
    {"name": "17-VR P1", "id": 17, "verbose-name": "VR P1", "enabled": False, "safe-max": 90},
    {"name": "18-VR P2", "id": 18, "verbose-name": "VR P2", "enabled": False, "safe-max": 90},
    {"name": "19-VR P1 Mem", "id": 19, "verbose-name": "VR P1 Memory", "enabled": False, "safe-max": 90},
    {"name": "20-VR P1 Mem", "id": 20, "verbose-name": "VR P1 Memory", "enabled": False, "safe-max": 90},
    {"name": "21-VR P2 Mem", "id": 21, "verbose-name": "VR P2 Memory", "enabled": False, "safe-max": 90},
    {"name": "22-VR P2 Mem", "id": 22, "verbose-name": "VR P2 Memory", "enabled": False, "safe-max": 90},
    {"name": "23-VR P1Vtt Zone", "id": 23, "verbose-name": "VR P1 Vtt Zone", "enabled": False, "safe-max": 90},
    {"name": "24-VR P2Vtt Zone", "id": 24, "verbose-name": "VR P2 Vtt Zone", "enabled": False, "safe-max": 90},
    {"name": "25-HD Controller", "id": 25, "verbose-name": "HD Controller", "enabled": True, "safe-max": 80},
    {"name": "26-iLO Zone", "id": 26, "verbose-name": "iLO Zone", "enabled": False, "safe-max": 90},
    {"name": "27-LOM Card", "id": 27, "verbose-name": "LOM Card", "enabled": False, "safe-max": 90},
    {"name": "28-PCI 1", "id": 28, "verbose-name": "PCI 1", "enabled": False, "safe-max": 85},
    {"name": "29-PCI 2", "id": 29, "verbose-name": "PCI 2", "enabled": False, "safe-max": 85},
    {"name": "30-PCI 3", "id": 30, "verbose-name": "PCI 3", "enabled": False, "safe-max": 85},
    {"name": "31-PCI 4", "id": 31, "verbose-name": "PCI 4", "enabled": False, "safe-max": 85},
    {"name": "32-PCI 5", "id": 32, "verbose-name": "PCI 5", "enabled": False, "safe-max": 85},
    {"name": "33-PCI 6", "id": 33, "verbose-name": "PCI 6", "enabled": False, "safe-max": 85},
    {"name": "34-PCI 1 Zone", "id": 34, "verbose-name": "PCI 1 Zone", "enabled": True, "safe-max": 85},
    {"name": "35-PCI 2 Zone", "id": 35, "verbose-name": "PCI 2 Zone", "enabled": True, "safe-max": 85},
    {"name": "36-PCI 3 Zone", "id": 36, "verbose-name": "PCI 3 Zone", "enabled": True, "safe-max": 85},
    {"name": "37-PCI 4 Zone", "id": 37, "verbose-name": "PCI 4 Zone", "enabled": False, "safe-max": 85},
    {"name": "38-PCI 5 Zone", "id": 38, "verbose-name": "PCI 5 Zone", "enabled": False, "safe-max": 85},
    {"name": "39-PCI 6 Zone", "id": 39, "verbose-name": "PCI 6 Zone", "enabled": False, "safe-max": 85},
    {"name": "40-I/O Board 1", "id": 40, "verbose-name": "I/O Board 1", "enabled": False, "safe-max": 85},
    {"name": "41-I/O Board 2", "id": 41, "verbose-name": "I/O Board 2", "enabled": False, "safe-max": 85},
    {"name": "42-VR P1 Zone", "id": 42, "verbose-name": "VR P1 Zone", "enabled": False, "safe-max": 90},
    {"name": "43-BIOS Zone", "id": 43, "verbose-name": "BIOS Zone", "enabled": False, "safe-max": 85},
    {"name": "44-System Board", "id": 44, "verbose-name": "System Board", "enabled": False, "safe-max": 70},
    {"name": "45-SuperCap Max", "id": 45, "verbose-name": "SuperCap Max", "enabled": False, "safe-max": 85},
    {"name": "46-Chipset Zone", "id": 46, "verbose-name": "Chipset Zone", "enabled": False, "safe-max": 85},
    {"name": "47-Battery Zone", "id": 47, "verbose-name": "Battery Zone", "enabled": False, "safe-max": 85},
    {"name": "48-I/O Zone", "id": 48, "verbose-name": "I/O Zone", "enabled": False, "safe-max": 85},
    {"name": "49-Sys Exhaust", "id": 49, "verbose-name": "System Exhaust", "enabled": True, "safe-max": 70},
    {"name": "50-Sys Exhaust", "id": 50, "verbose-name": "System Exhaust", "enabled": False, "safe-max": 70}
]

# Fan modes configuration
SILENT_MODE_SPEED = 13 # In a range of 0-255 (0-100% speed)
MANUAL_DEFAULT_SPEED = 18 # In a range of 0-255 (0-100% speed)
