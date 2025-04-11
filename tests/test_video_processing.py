import os
import shutil
import pytest
from src.video_processing import extract_frames

TEST_VIDEO_PATH = "data/sample_video.mp4"
TEST_OUTPUT_DIR = "tests/output_frames"

# 🔧 Fixture to automatically clean up the test output directory after each test
@pytest.fixture(autouse=True)
def clean_output_dir():
    yield  # Let the test execute
    if os.path.exists(TEST_OUTPUT_DIR):
        shutil.rmtree(TEST_OUTPUT_DIR)

# ✅ Test 1: Basic extraction using default interval
def test_valid_extraction_default_interval():
    frames = extract_frames(TEST_VIDEO_PATH, output_dir=TEST_OUTPUT_DIR)
    assert len(frames) > 0
    assert all(os.path.exists(f) for f in frames)

# ⚠️ Test 2: Interval is None (fallback to default)
def test_invalid_interval_none():
    frames = extract_frames(TEST_VIDEO_PATH, output_dir=TEST_OUTPUT_DIR, interval=None)
    assert len(frames) > 0

# ⚠️ Test 3: Interval is zero (fallback to default)
def test_invalid_interval_zero():
    frames = extract_frames(TEST_VIDEO_PATH, output_dir=TEST_OUTPUT_DIR, interval=0)
    assert len(frames) > 0

# ❌ Test 4: File does not exist
def test_nonexistent_video_path():
    with pytest.raises(FileNotFoundError):
        extract_frames("data/does_not_exist.mp4")

# ✅ Test 5: Custom interval and output dir
def test_custom_output_dir_and_interval():
    frames = extract_frames(TEST_VIDEO_PATH, output_dir=TEST_OUTPUT_DIR, interval=10)
    assert len(frames) > 0
    assert os.path.exists(TEST_OUTPUT_DIR)
