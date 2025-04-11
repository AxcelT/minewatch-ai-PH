# Module for video ingestion and frame extraction
import cv2
import os
import shutil

def extract_frames(video_path: str, output_dir: str = "data/frames", interval: int = 30):
    """
    Extract frames from the video every 'interval' frames and save them to output_dir.
    Overwrites the output_dir by clearing it before extraction.
    """
    # Validate interval
    if not isinstance(interval, int) or interval <= 0:
        print(f"[Warning] Invalid interval '{interval}' provided. Falling back to default value of 30.")
        interval = 30

    # Validate video path
    if not os.path.exists(video_path):
        raise FileNotFoundError(f"[Error] Video path does not exist: {video_path}")

    # Clear and recreate output directory
    if os.path.exists(output_dir):
        shutil.rmtree(output_dir)
    os.makedirs(output_dir)

    # Open the video file
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        raise IOError(f"[Error] Unable to open video file: {video_path}")
    
    count = 0
    saved_index = 0
    saved_frames = []

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        if count % interval == 0:
            frame_filename = os.path.join(output_dir, f"frame_{saved_index}.jpg")
            success = cv2.imwrite(frame_filename, frame)
            if success:
                saved_frames.append(frame_filename)
                saved_index += 1
            else:
                print(f"[Warning] Failed to write frame at count {count}")

        count += 1

    cap.release()

    print(f"[Info] Extracted {len(saved_frames)} frames to '{output_dir}' using interval {interval}.")
    return saved_frames