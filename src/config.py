# src/config.py

import os
from dotenv import load_dotenv

# Load .env from the project root
load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), "..", ".env"))

# API Key
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# Additional Configurations
FRAME_INTERVAL = int(os.getenv("FRAME_INTERVAL", 30))
VIDEO_PATH = os.getenv("VIDEO_PATH", "data/sample_video.mp4")
