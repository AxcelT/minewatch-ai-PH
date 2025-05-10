# app.py
import os
from flask import Flask, render_template, request, redirect, url_for, flash
from src.video_processing import extract_frames
from src.gpt_integration import analyze_image
import src.config as config
import openai

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

@app.route('/extract', methods=['POST'])
def extract():
    interval = request.form.get('interval', str(config.FRAME_INTERVAL))
    try:
        interval = int(interval)
        if interval <= 0: raise ValueError
    except ValueError:
        flash(f"Invalid interval—using default {config.FRAME_INTERVAL}")
        interval = config.FRAME_INTERVAL

    global extracted_frames
    try:
        extracted_frames = extract_frames(config.VIDEO_PATH, 'data/frames', interval)
        flash(f"Extracted {len(extracted_frames)} frames")
    except Exception as e:
        flash(f"Extraction error: {e}")
    return redirect(url_for('index'))

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
