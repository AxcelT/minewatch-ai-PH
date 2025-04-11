# Module for video ingestion and frame extraction
import cv2
import os
import shutil

def extract_frames(video_path: str, output_dir: str = "data/frames", interval: int = 30):
    """
    Extract frames from the video every 'interval' frames and save them to output_dir.
    Overwrites the output_dir by clearing it before extraction.
    """
    # Clear the output directory if it exists
    if os.path.exists(output_dir):
        shutil.rmtree(output_dir)
    os.makedirs(output_dir)

    cap = cv2.VideoCapture(video_path)
    
    if not cap.isOpened():
        raise IOError(f"Unable to open video file: {video_path}")
    
    count = 0
    saved_frames = []

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        # Save the frame if it meets the interval criteria.
        if count % interval == 0:
            frame_filename = os.path.join(output_dir, f"frame_{count}.jpg")
            cv2.imwrite(frame_filename, frame)
            saved_frames.append(frame_filename)
        
        count += 1
    
    cap.release()
    return saved_frames

# To Test independently. Uncomment the following lines:
if __name__ == "__main__":
    frames = extract_frames("data/sample_video.mp4")
    print(f"Extracted {len(frames)} frames.")
