# src/config.py

import os
from dotenv import load_dotenv

# Load .env from project root
load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), "..", ".env"))

# Base directories
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
DATA_DIR     = os.path.join(PROJECT_ROOT, "data")
FRAMES_DIR   = os.path.join(DATA_DIR, "frames")

# API Key
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# Additional Configurations
FRAME_INTERVAL = int(os.getenv("FRAME_INTERVAL", 30))
VIDEO_PATH     = os.getenv("VIDEO_PATH", os.path.join(DATA_DIR, "sample_video.mp4"))
