# app.py
import os
import logging
from flask import (
    Flask, render_template, request,
    redirect, url_for, flash,
    Response, stream_with_context, jsonify,
    session, send_from_directory
)
from gpt_integration import analyze_image
from media import media_bp
from services.llm_service import summarize_with_chain  # or summarize_with_openai
import config as config
import openai
import cv2
import shutil

# Load .env
from dotenv import load_dotenv
load_dotenv()

# Initialize Flask app
app = Flask(__name__)
app.config['SECRET_KEY'] = os.urandom(24)
app.config['UPLOAD_FOLDER'] = os.path.dirname(config.VIDEO_PATH)

#Blueprint for media routes
app.register_blueprint(media_bp)

def basename(path):
    return os.path.basename(path)
app.jinja_env.filters['basename'] = basename
# Configure logging to match Flask/Werkzeug style
logging.basicConfig(
    format='%(asctime)s %(levelname)s in %(module)s: %(message)s',
    level=logging.INFO
)

# Globals to hold state
extracted_frames = []
analysis_results = {}
abort_extraction = False

@app.route('/frames/<path:filename>')
def frame_file(filename):
    # app.root_path is the folder where app.py lives
    frame_root = os.path.join(app.root_path, 'data', 'frames')
    return send_from_directory(frame_root, filename)

@app.route('/')
def index():
    app.logger.info('GET / → rendering index.html')
    return render_template('index.html', default_interval=config.FRAME_INTERVAL)

@app.route('/upload', methods=['POST'])
def upload():
    app.logger.info('POST /upload → files: %s', list(request.files.keys()))
    file = request.files.get('video')
    if not file or file.filename == '':
        app.logger.warning('Upload failed: no file selected')
        return jsonify({'success': False, 'message': 'No file selected'}), 400

    dest = config.VIDEO_PATH
    os.makedirs(os.path.dirname(dest), exist_ok=True)
    file.save(dest)
    app.logger.info('Saved uploaded video to %s', dest)
    return jsonify({'success': True, 'message': 'Video uploaded successfully'})

@app.route('/extract')
def extract():
    """
    Server-Sent Events endpoint streaming one event per extracted frame.
    The client should connect via:
        new EventSource(`/extract?interval=${n}`)
    """
    app.logger.info('GET /extract → args: %s', dict(request.args))
    # Parse "interval" from query-string; fallback to default
    try:
        interval = int(request.args.get('interval', config.FRAME_INTERVAL))
        if interval <= 0:
            raise ValueError
    except ValueError:
        interval = config.FRAME_INTERVAL
        app.logger.warning('Invalid interval provided; using default %d', interval)
        flash(f"Invalid interval—using default {config.FRAME_INTERVAL}")

    def generate():
        global extracted_frames
        extracted_frames = []

        app.logger.info('Starting video capture from %s', config.VIDEO_PATH)
        cap = cv2.VideoCapture(config.VIDEO_PATH)
        if not cap.isOpened():
            app.logger.error('Cannot open video: %s', config.VIDEO_PATH)
            yield "data: ERROR: cannot open video\n\n"
            return

        count = 0
        idx = 0
        frame_dir = 'data/frames'

        # Clear old frames
        if os.path.exists(frame_dir):
            shutil.rmtree(frame_dir)
        os.makedirs(frame_dir, exist_ok=True)
        app.logger.info('Frame directory cleared and ready (%s)', frame_dir)

        try:
            while True:
                ret, frame = cap.read()
                if not ret:
                    app.logger.info('No more frames to read after %d loops', count)
                    break

                if count % interval == 0:
                    outpath = os.path.join(frame_dir, f"frame_{idx}.jpg")
                    cv2.imwrite(outpath, frame)
                    extracted_frames.append(outpath)
                    app.logger.info('Extracted frame %d → %s', idx + 1, outpath)
                    try:
                        # this yield will raise if the client has disconnected
                        yield f"data: Extracted frame {idx + 1}\n\n"
                    except GeneratorExit:
                        app.logger.info('Extraction aborted by client at frame %d', idx + 1)
                        return
                    except OSError as e:
                        app.logger.info('Client disconnected (OS error) at frame %d: %s', idx + 1, e)
                        return
                    idx += 1

                count += 1

            # only emit completion if we got here normally
            app.logger.info('Extraction complete: %d frames', idx)
            try:
                yield f"data: Extraction complete: {idx} frames\n\n"
            except GeneratorExit:
                app.logger.info('Client disconnected before final message at frame %d', idx)
            except OSError as e:
                app.logger.info('Client disconnected (OS error) before final message at frame %d: %s', idx, e)
        finally:
            cap.release()

    return Response(stream_with_context(generate()), mimetype='text/event-stream')

@app.route('/analyze', methods=['POST'])
def analyze():
    app.logger.info('POST /analyze → %d frames in queue', len(extracted_frames))
    if not extracted_frames:
        app.logger.warning('Analyze failed: no frames extracted')
        flash('No frames—please extract first')
        return redirect(url_for('index'))

    context = request.form.get('context') or (
        "Site type: open pit; Mineral: Gold; tropical climate, rainfall patterns, tailings overflow."
    )
    app.logger.info('Analysis context: %s', context)

    global analysis_results
    analysis_results = {}
    for f in extracted_frames:
        app.logger.info('Analyzing frame %s', f)
        analysis_results[f] = analyze_image(f, context)

    app.logger.info('Analysis complete for %d frames', len(analysis_results))
    flash('Analysis complete')
    return redirect(url_for('results'))

@app.route('/results')
def results():
    app.logger.info('GET /results → rendering results.html')
    return render_template('results.html', analysis_results=analysis_results)

@app.route('/final')
def final():
    app.logger.info('GET /final → summarizing %d analysis entries', len(analysis_results))
    if not analysis_results:
        app.logger.warning('Final summary failed: no analysis results')
        flash('No analysis to summarize')
        return redirect(url_for('results'))

    app.logger.info('Sending summary prompt to OpenAI (token limit: 300)')

    try:
        conclusion = summarize_with_chain(analysis_results)
        app.logger.info('Received final conclusion from OpenAI')
    except Exception as e:
        app.logger.error('LLM error in /final: %s', e)
        conclusion = f"Error: {e}"

    return render_template('final.html', final_conclusion=conclusion)

@app.route('/remove_frames', methods=['POST'])
def remove_frames_route(): # Renamed to avoid conflict with os.remove_frames if it existed
    global extracted_frames, analysis_results
    app.logger.info("POST /remove_frames received")

    data = request.get_json()
    if not data or 'frames' not in data or not isinstance(data['frames'], list):
        app.logger.warning("Invalid request format for /remove_frames: %s", data)
        return jsonify({'success': False, 'message': 'Invalid request format. Expected {"frames": [...]}'}), 400

    frames_to_remove_basenames = data['frames']
    if not frames_to_remove_basenames:
        app.logger.info("No frames specified for removal.")
        return jsonify({'success': True, 'message': 'No frames specified for removal.'})

    app.logger.info(f"Request to remove frames: {frames_to_remove_basenames}")

    # Keep track of frames that were successfully found and processed for removal from data structures
    processed_for_removal_keys = []
    # Keep track of frames that couldn't be deleted from filesystem
    filesystem_delete_failures = []

    for basename_frame in frames_to_remove_basenames:
        # Construct the full path key as stored in extracted_frames and analysis_results
        # This assumes app.root_path is the project root where 'data' directory resides.
        # Given frame_dir = 'data/frames' in extract(), this is consistent.
        frame_path_key = os.path.join('data', 'frames', basename_frame)
        
        app.logger.info(f"Processing removal for frame key: {frame_path_key}")

        # Attempt to remove from filesystem
        try:
            # The actual physical path for os.remove should be relative to app.root_path if not absolute
            # os.path.join(app.root_path, frame_path_key) might be more robust if CWD changes
            # However, given 'data/frames' is used directly in extract, this should be fine.
            physical_frame_path = os.path.join(app.root_path, frame_path_key)
            if not os.path.exists(physical_frame_path): # Check before attempting delete
                 app.logger.warning(f"Filesystem: Frame not found, skipping delete: {physical_frame_path}")
            else:
                os.remove(physical_frame_path)
                app.logger.info(f"Filesystem: Successfully removed frame file: {physical_frame_path}")
            
            # If file deletion (or file not found) is successful, mark for removal from data structures
            processed_for_removal_keys.append(frame_path_key)

        except FileNotFoundError: # Should be caught by os.path.exists now, but good to keep
            app.logger.warning(f"Filesystem: Frame not found during os.remove, skipping: {physical_frame_path}")
            processed_for_removal_keys.append(frame_path_key) # Still attempt to remove from lists
        except OSError as e:
            app.logger.error(f"Filesystem: Error deleting file {physical_frame_path}: {e}")
            filesystem_delete_failures.append(basename_frame)
            # Decide if this is critical. For now, we'll log and continue,
            # but the frame might remain in the data structures if not added to processed_for_removal_keys.
            # For safety, we won't add it to processed_for_removal_keys if the delete failed for reasons other than not found.

    # Update global lists/dicts
    if processed_for_removal_keys:
        original_extracted_count = len(extracted_frames)
        extracted_frames = [f for f in extracted_frames if f not in processed_for_removal_keys]
        app.logger.info(f"Data: `extracted_frames` updated. Removed {original_extracted_count - len(extracted_frames)} items.")

        original_analysis_count = len(analysis_results)
        for key_to_remove in processed_for_removal_keys:
            if key_to_remove in analysis_results:
                analysis_results.pop(key_to_remove)
        app.logger.info(f"Data: `analysis_results` updated. Removed {original_analysis_count - len(analysis_results)} items.")
    
    if filesystem_delete_failures:
        return jsonify({
            'success': False, 
            'message': f"Some frames could not be deleted from the filesystem: {filesystem_delete_failures}. Data structures updated for others."
        }), 500

    return jsonify({'success': True, 'message': 'Selected frames processed for removal.'})


if __name__ == '__main__':
    app.logger.info('Launching MineWatch-AI-PH app on port 5000')
    app.run(host='0.0.0.0', port=5000, debug=True)
