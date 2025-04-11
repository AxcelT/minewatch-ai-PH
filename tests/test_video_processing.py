import os
import pytest
from src.video_processing import extract_frames

# Sample video and test output directory for all test cases
TEST_VIDEO_PATH = "data/sample_video.mp4"
TEST_OUTPUT_DIR = "tests/output_frames"

# ✅ Test 1: Basic extraction using the default interval (30)
def test_valid_extraction_default_interval():
    frames = extract_frames(TEST_VIDEO_PATH, output_dir=TEST_OUTPUT_DIR)
    assert len(frames) > 0  # Check that at least one frame was saved
    assert all(os.path.exists(f) for f in frames)  # Ensure all listed frames actually exist

# ⚠️ Test 2: Pass None as interval, should fallback to 30
def test_invalid_interval_none():
    frames = extract_frames(TEST_VIDEO_PATH, output_dir=TEST_OUTPUT_DIR, interval=None)
    assert len(frames) > 0

# ⚠️ Test 3: Pass zero as interval, should also fallback to 30
def test_invalid_interval_zero():
    frames = extract_frames(TEST_VIDEO_PATH, output_dir=TEST_OUTPUT_DIR, interval=0)
    assert len(frames) > 0

# ❌ Test 4: Use a nonexistent video path, expect FileNotFoundError
def test_nonexistent_video_path():
    with pytest.raises(FileNotFoundError):
        extract_frames("data/does_not_exist.mp4")

# ✅ Test 5: Use a custom output dir and custom frame interval
def test_custom_output_dir_and_interval():
    frames = extract_frames(TEST_VIDEO_PATH, output_dir=TEST_OUTPUT_DIR, interval=10)
    assert len(frames) > 0
    assert os.path.exists(TEST_OUTPUT_DIR)
