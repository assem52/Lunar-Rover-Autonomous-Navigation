import os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FRONTEND_ROOT = os.path.join(BASE_DIR, "frontend")
FRONTEND_DIST = os.path.join(FRONTEND_ROOT, "dist")
STATIC_DIR = FRONTEND_DIST if os.path.isdir(FRONTEND_DIST) else FRONTEND_ROOT

MODELS_DIR = os.path.join(BASE_DIR, "models")
MAPS_DIR = os.path.join(BASE_DIR, "maps")
os.makedirs(MODELS_DIR, exist_ok=True)
os.makedirs(MAPS_DIR, exist_ok=True)

DEFAULT_MODEL_NAME = "default_model"
DEFAULT_MODEL_PATH = os.path.join(MODELS_DIR, f"{DEFAULT_MODEL_NAME}.json")
GRID_SIZE = 10
NUM_CRATERS = 4
NUM_ROCKS = 6
DEFAULT_SPEED = 0.12
