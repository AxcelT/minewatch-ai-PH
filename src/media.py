# src/media.py
# Blueprint for serving extracted frame image files

import os
from flask import Blueprint, send_from_directory, current_app
from werkzeug.utils import secure_filename
import config

# Initialize a blueprint at '/frames' prefix
media_bp = Blueprint('media', __name__, url_prefix='/frames')

@media_bp.route('/<path:filename>')
def serve_frame(filename):
    """
    Route: Serve a sanitized frame image from the configured frames directory.
    - Ensures only safe filenames are used
    - Returns HTTP 404 if the file does not exist
    """
    # Sanitize filename to prevent directory traversal
    safe_name = secure_filename(filename)
    frame_root = config.FRAMES_DIR

    # Construct full path and check existence
    full_path = os.path.join(frame_root, safe_name)
    if not os.path.isfile(full_path):
        current_app.logger.warning('Frame not found: %s', full_path)
        return ('File not found', 404)

    # Serve the requested frame file
    return send_from_directory(frame_root, safe_name)
