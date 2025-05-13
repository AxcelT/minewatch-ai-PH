# app.py
import os
from flask import Flask, render_template, request, redirect, url_for, flash, Response, stream_with_context
from gpt_integration import analyze_image
import config as config
import openai
import cv2
import shutil

# Load .env
from dotenv import load_dotenv
load_dotenv()

app = Flask(__name__)
app.config['SECRET_KEY'] = os.urandom(24)
app.config['UPLOAD_FOLDER'] = os.path.dirname(config.VIDEO_PATH)

extracted_frames = []
analysis_results = {}

@app.route('/')
def index():
    return render_template('index.html', default_interval=config.FRAME_INTERVAL)

@app.route('/upload', methods=['POST'])
def upload():
    file = request.files.get('video')
    if not file or file.filename == '':
        flash('No file selected')
        return redirect(url_for('index'))

    dest = config.VIDEO_PATH
    os.makedirs(os.path.dirname(dest), exist_ok=True)
    file.save(dest)
    flash('Video uploaded successfully')
    return redirect(url_for('index'))

@app.route('/extract')
def extract():
    """
    Server-Sent Events endpoint streaming one event per extracted frame.
    The client should connect via:
        new EventSource(`/extract?interval=${n}`)
    """
    # Parse "interval" from query-string; fallback to default
    try:
        interval = int(request.args.get('interval', config.FRAME_INTERVAL))
        if interval <= 0:
            raise ValueError
    except ValueError:
        interval = config.FRAME_INTERVAL
        flash(f"Invalid interval—using default {config.FRAME_INTERVAL}")

    def generate():
        global extracted_frames
        extracted_frames = []

        cap = cv2.VideoCapture(config.VIDEO_PATH)
        if not cap.isOpened():
            yield "data: ERROR: cannot open video\n\n"
            return

        count = 0
        idx = 0
        frame_dir = 'data/frames'

        # Clear old frames
        if os.path.exists(frame_dir):
            shutil.rmtree(frame_dir)
        os.makedirs(frame_dir, exist_ok=True)

        while True:
            ret, frame = cap.read()
            if not ret:
                break

            if count % interval == 0:
                outpath = os.path.join(frame_dir, f"frame_{idx}.jpg")
                cv2.imwrite(outpath, frame)
                extracted_frames.append(outpath)
                yield f"data: Extracted frame {idx + 1}\n\n"
                idx += 1

            count += 1

        cap.release()
        yield f"data: Extraction complete: {idx} frames\n\n"

    return Response(stream_with_context(generate()), mimetype='text/event-stream')

@app.route('/analyze', methods=['POST'])
def analyze():
    if not extracted_frames:
        flash('No frames—please extract first')
        return redirect(url_for('index'))

    context = request.form.get('context') or \
        "Site type: open pit; Mineral: Gold; tropical climate, rainfall patterns, tailings overflow."
    global analysis_results
    analysis_results = {}
    for f in extracted_frames:
        analysis_results[f] = analyze_image(f, context)
    flash('Analysis complete')
    return redirect(url_for('results'))

@app.route('/results')
def results():
    return render_template('results.html', analysis_results=analysis_results)

@app.route('/final')
def final():
    if not analysis_results:
        flash('No analysis to summarize')
        return redirect(url_for('results'))
    combined = "\n".join(analysis_results.values())
    prompt = (
        "Summarize the following analyses into a final conclusion:\n\n" + combined
    )
    try:
        resp = openai.ChatCompletion.create(
            model="gpt-4",
            messages=[
                {"role":"system","content":"You are a mining site expert."},
                {"role":"user","content":prompt}
            ],
            max_tokens=300
        )
        conclusion = resp.choices[0].message.content
    except Exception as e:
        conclusion = f"Error: {e}"
    return render_template('final.html', final_conclusion=conclusion)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
