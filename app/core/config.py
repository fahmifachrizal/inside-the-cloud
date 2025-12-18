import os

# Base directory is 2 levels up from this file (app/core/ -> app/ -> root)
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

TEMP_DIR = os.path.join(BASE_DIR, "temp")
DATA_DIR = os.path.join(BASE_DIR, "app", "data")

# Ensure dirs exist
os.makedirs(TEMP_DIR, exist_ok=True)
os.makedirs(DATA_DIR, exist_ok=True)