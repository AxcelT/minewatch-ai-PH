# src/media.py

import os
from flask import Blueprint, send_from_directory, current_app
from werkzeug.utils import secure_filename
import config

media_bp = Blueprint("media", __name__, url_prefix="/frames")

@media_bp.route("/<path:filename>")
def serve_frame(filename):
    # sanitize and serve only from FRAMES_DIR
    safe_name = secure_filename(filename)
    frame_root = config.FRAMES_DIR
    # Optionally, verify file exists first:
    full_path = os.path.join(frame_root, safe_name)
    if not os.path.isfile(full_path):
        # Let Flask return a 404 for you
        return ("File not found", 404)
    # after
    return send_from_directory(frame_root, safe_name)

