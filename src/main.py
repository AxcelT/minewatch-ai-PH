# Entry point of your application
import os
import shutil
import tkinter as tk
from tkinter import filedialog, messagebox
from tkinter.scrolledtext import ScrolledText
from video_processing import extract_frames
from gpt_integration import analyze_image
import config
import openai  # Needed for generating final conclusion

# Global variables to hold extracted frames and the individual frame analyses
extracted_frames = []
analysis_results = {}

def upload_video():
    """Prompt the user to select a video file and copy it to the project data folder."""
    file_path = filedialog.askopenfilename(
        title="Select Video File",
        filetypes=[("Video Files", "*.mp4;*.avi;*.mov"), ("All files", "*.*")]
    )
    if file_path:
        dest = config.VIDEO_PATH
        # Ensure the parent directory for VIDEO_PATH exists.
        os.makedirs(os.path.dirname(dest), exist_ok=True)
        try:
            shutil.copyfile(file_path, dest)
            status_label.config(text=f"Video uploaded: {os.path.basename(file_path)}")
            extract_button.config(state=tk.NORMAL)
        except Exception as e:
            messagebox.showerror("Upload Error", f"Failed to copy file: {e}")
    else:
        messagebox.showinfo("Upload", "No file selected.")


def extract_frames_callback():
    """Extract frames from the uploaded video using a user-specified interval and update the GUI state."""
    # Read the interval from the entry widget.
    try:
        interval_val = int(interval_entry.get())
        if interval_val <= 0:
            raise ValueError
    except ValueError:
        messagebox.showwarning(
            "Interval Input",
            f"Invalid frame interval input. Falling back to default: {config.FRAME_INTERVAL}"
        )
        interval_val = config.FRAME_INTERVAL

    try:
        frames = extract_frames(config.VIDEO_PATH, output_dir="data/frames", interval=interval_val)
        global extracted_frames
        extracted_frames = frames
        status_label.config(text=f"Extracted {len(frames)} frames (Interval: {interval_val}).")
        analysis_button.config(state=tk.NORMAL)
    except Exception as e:
        messagebox.showerror("Extraction Error", str(e))


def run_analysis_callback():
    """Run GPT API inference on each extracted frame and display the results."""
    # Clear previous results in the text area.
    result_text.delete("1.0", tk.END)
    if not extracted_frames:
        messagebox.showerror("Error", "No frames available for analysis. Please extract frames first.")
        return

    global analysis_results
    analysis_results = {}  # Reset previous results
    total = len(extracted_frames)
    context = (
        "Site type: open pit; Mineral: Gold; "
        "Environmental conditions: tropical climate, seasonal rainfall patterns, potential tailings overflow."
    )
    for index, frame in enumerate(extracted_frames):
        status_label.config(text=f"Analyzing frame {index + 1} of {total}...")
        root.update()  # Update the GUI status
        analysis = analyze_image(frame, context)
        analysis_results[frame] = analysis
        result_text.insert(tk.END, f"{frame}:\n{analysis}\n\n")
    status_label.config(text="Analysis complete. Check results below.")


# def final_conclusion_callback():
#     """Generate a final conclusion using the collated analysis from all frames."""
#     if not analysis_results:
#         messagebox.showerror("Error", "No analysis results available. Please run the analysis first.")
#         return

#     # Combine all individual analyses into one large text blob.
#     combined_text = "\n".join(analysis_results.values())
    
#     # Create a prompt for the GPT API to generate a final conclusion.
#     prompt = (
#         "Based on the following frame analyses of a mining site, "
#         "please provide a final comprehensive conclusion summarizing the overall environmental conditions and "
#         "potential issues detected:\n\n"
#         f"{combined_text}\n\n"
#         "Final Conclusion:"
#     )
    
    try:
        # Call the GPT API using the chat completion endpoint.
        response = openai.ChatCompletion.create(
            model="gpt-4",  # or use the model appropriate for text input
            messages=[
                {"role": "system", "content": "You are a mining site analysis expert."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=300,
        )
        conclusion = response["choices"][0]["message"]["content"]
    except Exception as e:
        conclusion = f"Error generating final conclusion: {e}"
    
    result_text.insert(tk.END, "\n=== Final Conclusion ===\n" + conclusion + "\n")
    status_label.config(text="Final conclusion appended.")


# ----------------------
# Tkinter GUI Setup
# ----------------------
root = tk.Tk()
root.title("MineWatch AI - PH")

# Frame for the buttons.
btn_frame = tk.Frame(root)
btn_frame.pack(pady=10)

upload_button = tk.Button(btn_frame, text="Upload Video", width=15, command=upload_video)
upload_button.grid(row=0, column=0, padx=5)

extract_button = tk.Button(btn_frame, text="Extract Frames", width=15, state=tk.DISABLED, command=extract_frames_callback)
extract_button.grid(row=0, column=1, padx=5)

analysis_button = tk.Button(btn_frame, text="Run Analysis", width=15, state=tk.DISABLED, command=run_analysis_callback)
analysis_button.grid(row=0, column=2, padx=5)

# Add a label and entry for custom frame interval.
interval_label = tk.Label(btn_frame, text="Frame Interval:")
interval_label.grid(row=1, column=0, pady=5, padx=5, sticky="e")

interval_entry = tk.Entry(btn_frame, width=10)
interval_entry.insert(0, str(config.FRAME_INTERVAL))  # Pre-populate with default interval value.
interval_entry.grid(row=1, column=1, pady=5, padx=5, sticky="w")

# Button for final conclusion.
# conclusion_button = tk.Button(root, text="Show Final Conclusion", width=20, command=final_conclusion_callback)
# conclusion_button.pack(pady=5)

# Status label to display current processing status.
status_label = tk.Label(root, text="Awaiting action...")
status_label.pack(pady=5)

# Text area for displaying analysis results.
result_text = ScrolledText(root, width=80, height=20)
result_text.pack(padx=10, pady=10)

root.mainloop()
