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

if __name__ == '__main__':
    app.logger.info('Launching MineWatch-AI-PH app on port 5000')
    app.run(host='0.0.0.0', port=5000, debug=True)
