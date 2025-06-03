# app.py
import os
import logging
from flask import (
    Flask, render_template, request,
    redirect, url_for, flash,
    Response, stream_with_context, jsonify,
    session, send_from_directory
)
from llm_integration import analyze_frames, analyze_frame, summarize_with_chain
from media import media_bp
import config
import cv2
import shutil
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Initialize Flask application and configuration
app = Flask(__name__)
app.config['SECRET_KEY'] = os.urandom(24)
app.config['UPLOAD_FOLDER'] = os.path.dirname(config.VIDEO_PATH)

# Register media blueprint for handling media-specific routes
app.register_blueprint(media_bp)

# Custom Jinja filter to extract base filename from path
def basename(path):
    return os.path.basename(path)
app.jinja_env.filters['basename'] = basename

# Configure logging to match Flask/Werkzeug style
logging.basicConfig(
    format='%(asctime)s %(levelname)s in %(module)s: %(message)s',
    level=logging.INFO
)

# Global state containers
extracted_frames = []
analysis_results = {}
abort_extraction = False

@app.route('/frames/<path:filename>')
def frame_file(filename):
    """Route: Serve extracted frame image files."""
    frame_root = os.path.join(os.getcwd(), 'data', 'frames')
    return send_from_directory(frame_root, filename)

@app.route('/')
def index():
    """Route: Render the main upload and extraction interface."""
    app.logger.info('GET / → rendering index.html')
    return render_template('index.html', default_interval=config.FRAME_INTERVAL)

@app.route('/upload', methods=['POST'])
def upload():
    """Route: Handle video file uploads from the client."""
    app.logger.info('POST /upload → files: %s', list(request.files.keys()))
    file = request.files.get('video')
    if not file or not file.filename:
        app.logger.warning('Upload failed: no file selected')
        return jsonify({'success': False, 'message': 'No file selected'}), 400

    dest = config.VIDEO_PATH
    os.makedirs(os.path.dirname(dest), exist_ok=True)
    file.save(dest)
    app.logger.info('Saved uploaded video to %s', dest)
    return jsonify({'success': True, 'message': 'Video uploaded successfully'})

@app.route('/extract')
def extract():
    """Route: Stream frame extraction events via Server-Sent Events (SSE)."""
    app.logger.info('GET /extract → args: %s', dict(request.args))
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

        count = idx = 0
        frame_dir = 'data/frames'

        # Prepare frame directory
        if os.path.exists(frame_dir):
            shutil.rmtree(frame_dir)
        os.makedirs(frame_dir, exist_ok=True)
        app.logger.info('Prepared frame directory: %s', frame_dir)

        try:
            while True:
                ret, frame = cap.read()
                if not ret:
                    app.logger.info('No more frames after %d reads', count)
                    break

                if count % interval == 0:
                    outpath = os.path.join(frame_dir, f"frame_{idx}.jpg")
                    cv2.imwrite(outpath, frame)
                    extracted_frames.append(outpath)
                    app.logger.info('Extracted frame %d → %s', idx + 1, outpath)
                    try:
                        yield f"data: Extracted frame {idx + 1}\n\n"
                    except (GeneratorExit, OSError) as e:
                        app.logger.info('Extraction stopped at frame %d: %s', idx + 1, e)
                        return
                    idx += 1
                count += 1

            app.logger.info('Extraction complete: %d frames', idx)
            try:
                yield f"data: Extraction complete: {idx} frames\n\n"
            except (GeneratorExit, OSError) as e:
                app.logger.info('Client disconnected before final message: %s', e)
        finally:
            cap.release()

    return Response(stream_with_context(generate()), mimetype='text/event-stream')

@app.route('/preview_frames')
def preview_frames():
    """Route: Provide list of extracted frame filenames for client preview."""
    basenames = [os.path.basename(p) for p in extracted_frames]
    return jsonify({'frames': basenames})

@app.route('/analyze', methods=['POST'])
def analyze():
    """Route: Analyze extracted frames using the GPT-based image analysis service."""
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
    analysis_results = {f: analyze_frames(f, context) for f in extracted_frames}
    app.logger.info('Analysis complete for %d frames', len(analysis_results))
    flash('Analysis complete')
    return redirect(url_for('results'))

@app.route('/analyze_stream')
def analyze_stream():
    context = request.args.get('context')
    def gen():
        for f in extracted_frames:
            res_dict = analyze_frame(f, context)
            analysis_results[f] = res_dict
            yield f"data: {f} → {res_dict}\n\n"
        yield "data: Analysis complete\n\n"
    return Response(stream_with_context(gen()),
                    mimetype='text/event-stream')

@app.route('/results')
def results():
    """Route: Render analysis results in the results view."""
    app.logger.info('GET /results → rendering results.html')
    return render_template('results.html', analysis_results=analysis_results)

@app.route('/final')
def final():
    """Route: Summarize analysis results into a final conclusion via LLM."""
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
def remove_frames_route():
    """Route: Remove selected frames from both filesystem and internal state."""
    global extracted_frames, analysis_results
    app.logger.info("POST /remove_frames received")

    data = request.get_json()
    if not data or 'frames' not in data or not isinstance(data['frames'], list):
        app.logger.warning("Invalid request format for /remove_frames: %s", data)
        return jsonify({'success': False, 'message': 'Invalid request format. Expected {"frames": [...]}'}), 400

    frames_to_remove = data['frames']
    if not frames_to_remove:
        app.logger.info("No frames specified for removal.")
        return jsonify({'success': True, 'message': 'No frames specified for removal.'})

    app.logger.info('Removing frames: %s', frames_to_remove)

    processed, failures = [], []
    for name in frames_to_remove:
        path_key = os.path.join('data', 'frames', name)
        physical = os.path.join(app.root_path, path_key)
        try:
            if os.path.exists(physical):
                os.remove(physical)
                app.logger.info('Removed file: %s', physical)
            else:
                app.logger.warning('File not found: %s', physical)
            processed.append(path_key)
        except Exception as e:
            app.logger.error('Error deleting file %s: %s', physical, e)
            failures.append(name)

    if processed:
        extracted_frames = [f for f in extracted_frames if f not in processed]
        app.logger.info('Updated extracted_frames, removed %d items', len(processed))
        for key in processed:
            analysis_results.pop(key, None)
        app.logger.info('Updated analysis_results, removed %d items', len(processed))

    if failures:
        return jsonify({'success': False, 'message': f"Failed to delete: {failures}. Others removed."}), 500

    return jsonify({'success': True, 'message': 'Selected frames processed for removal.'})

if __name__ == '__main__':
    app.logger.info('Launching MineWatch-AI-PH app on port 5000')
    app.run(host='0.0.0.0', port=5000, debug=True)
