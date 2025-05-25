import unittest
import os
import json
import shutil
from src.app import app, extracted_frames as global_extracted_frames, analysis_results as global_analysis_results

class TestFrameRemoval(unittest.TestCase):

    def setUp(self):
        self.client = app.test_client()
        self.app_context = app.app_context()
        self.app_context.push()

        # Configure a specific test frames directory
        # app.root_path is the directory where app.py is located (src/)
        self.frames_base_dir_name = 'data' # This is relative to app.root_path
        self.frames_sub_dir_name = 'frames_test' # Use a different subdir to avoid conflict with actual 'data/frames'
        
        # Construct the full path to the test frames directory
        self.test_frames_dir = os.path.join(app.root_path, self.frames_base_dir_name, self.frames_sub_dir_name)
        
        # Ensure the base 'data' directory exists
        os.makedirs(os.path.join(app.root_path, self.frames_base_dir_name), exist_ok=True)
        # Clean up and create the specific test frames directory
        if os.path.exists(self.test_frames_dir):
            shutil.rmtree(self.test_frames_dir)
        os.makedirs(self.test_frames_dir)

        self.dummy_frames_basenames = [f'test_frame{i}.jpg' for i in range(1, 4)] # test_frame1.jpg, test_frame2.jpg, test_frame3.jpg
        
        # These paths are relative to app.root_path, as stored in app.py globals
        self.dummy_frames_paths_keys = [
            os.path.join(self.frames_base_dir_name, self.frames_sub_dir_name, bn) 
            for bn in self.dummy_frames_basenames
        ]

        # Create dummy files in the test directory
        for key_path in self.dummy_frames_paths_keys:
            # physical_path is app.root_path + key_path
            physical_path = os.path.join(app.root_path, key_path)
            with open(physical_path, 'w') as f:
                f.write("dummy content") # Add some content to ensure it's a file

        # Populate globals
        # Make sure to assign to the imported global lists directly, not just class members
        global_extracted_frames[:] = self.dummy_frames_paths_keys # Use slicing to modify in place
        global_analysis_results.clear()
        for path_key in self.dummy_frames_paths_keys:
            global_analysis_results[path_key] = f"analysis_for_{os.path.basename(path_key)}"
        
        # Store original values of app.py's frame/analysis containers for restoration
        # This is important because app.py's remove_frames_route directly modifies the global variables
        # We need to ensure that the test setup correctly points to these global variables
        # And that it uses the *test-specific* paths for files.

        # The current setup for global_extracted_frames and global_analysis_results
        # correctly modifies the imported lists/dicts from app.py.
        # The paths stored in these globals will be like 'data/frames_test/test_frame1.jpg'.
        # The remove_frames_route in app.py uses os.path.join(app.root_path, frame_path_key)
        # so it will correctly resolve to /app/src/data/frames_test/test_frame1.jpg if app.root_path is /app/src/

    def tearDown(self):
        if os.path.exists(self.test_frames_dir):
            shutil.rmtree(self.test_frames_dir)
        
        # Clear globals after test
        global_extracted_frames[:] = []
        global_analysis_results.clear()
        
        self.app_context.pop()

    def test_successful_removal_one_frame(self):
        frames_to_remove_basenames = [self.dummy_frames_basenames[0]]
        frame_path_key_to_remove = self.dummy_frames_paths_keys[0]
        physical_path_to_remove = os.path.join(app.root_path, frame_path_key_to_remove)

        initial_extracted_count = len(global_extracted_frames)
        initial_analysis_count = len(global_analysis_results)

        response = self.client.post('/remove_frames', json={'frames': frames_to_remove_basenames})
        data = json.loads(response.data)

        self.assertEqual(response.status_code, 200)
        self.assertTrue(data['success'])
        self.assertEqual(data['message'], 'Selected frames processed for removal.')

        self.assertFalse(os.path.exists(physical_path_to_remove))
        self.assertIn(frame_path_key_to_remove, self.dummy_frames_paths_keys) # Check it was a valid key
        self.assertNotIn(frame_path_key_to_remove, global_extracted_frames)
        self.assertNotIn(frame_path_key_to_remove, global_analysis_results)
        
        self.assertEqual(len(global_extracted_frames), initial_extracted_count - 1)
        self.assertEqual(len(global_analysis_results), initial_analysis_count - 1)

        # Check other files still exist
        self.assertTrue(os.path.exists(os.path.join(app.root_path, self.dummy_frames_paths_keys[1])))

    def test_successful_removal_multiple_frames(self):
        frames_to_remove_basenames = self.dummy_frames_basenames[:2] # remove first two
        paths_keys_to_remove = self.dummy_frames_paths_keys[:2]
        
        initial_extracted_count = len(global_extracted_frames)
        initial_analysis_count = len(global_analysis_results)

        response = self.client.post('/remove_frames', json={'frames': frames_to_remove_basenames})
        data = json.loads(response.data)

        self.assertEqual(response.status_code, 200)
        self.assertTrue(data['success'])

        for key_path in paths_keys_to_remove:
            physical_path = os.path.join(app.root_path, key_path)
            self.assertFalse(os.path.exists(physical_path))
            self.assertNotIn(key_path, global_extracted_frames)
            self.assertNotIn(key_path, global_analysis_results)
        
        self.assertEqual(len(global_extracted_frames), initial_extracted_count - 2)
        self.assertEqual(len(global_analysis_results), initial_analysis_count - 2)
        
        # Check the third frame (not removed) still exists
        self.assertTrue(os.path.exists(os.path.join(app.root_path, self.dummy_frames_paths_keys[2])))
        self.assertIn(self.dummy_frames_paths_keys[2], global_extracted_frames)
        self.assertIn(self.dummy_frames_paths_keys[2], global_analysis_results)

    def test_removal_of_non_existent_frame_basename(self):
        non_existent_basename = "frame_that_never_was.jpg"
        frame_to_remove_basename = self.dummy_frames_basenames[0]
        path_key_to_remove = self.dummy_frames_paths_keys[0]
        physical_path_to_remove = os.path.join(app.root_path, path_key_to_remove)

        frames_payload = [non_existent_basename, frame_to_remove_basename]
        
        initial_extracted_count = len(global_extracted_frames)
        initial_analysis_count = len(global_analysis_results)

        response = self.client.post('/remove_frames', json={'frames': frames_payload})
        data = json.loads(response.data)

        self.assertEqual(response.status_code, 200) # Server handles non-existent files gracefully
        self.assertTrue(data['success'])

        # Existing frame should be removed
        self.assertFalse(os.path.exists(physical_path_to_remove))
        self.assertNotIn(path_key_to_remove, global_extracted_frames)
        self.assertNotIn(path_key_to_remove, global_analysis_results)
        
        self.assertEqual(len(global_extracted_frames), initial_extracted_count - 1)
        self.assertEqual(len(global_analysis_results), initial_analysis_count - 1)

    def test_removal_when_file_missing_but_in_globals(self):
        # Simulate a file that is in globals but already deleted from disk
        frame_to_remove_key = self.dummy_frames_paths_keys[0]
        physical_path_to_remove = os.path.join(app.root_path, frame_to_remove_key)
        
        # Manually delete it from disk
        os.remove(physical_path_to_remove)
        self.assertFalse(os.path.exists(physical_path_to_remove)) # Pre-condition
        self.assertIn(frame_to_remove_key, global_extracted_frames) # Pre-condition: still in global

        frames_payload = [os.path.basename(frame_to_remove_key)]
        initial_globals_count = len(global_extracted_frames)

        response = self.client.post('/remove_frames', json={'frames': frames_payload})
        data = json.loads(response.data)

        self.assertEqual(response.status_code, 200)
        self.assertTrue(data['success'])
        
        # Check it's removed from globals
        self.assertNotIn(frame_to_remove_key, global_extracted_frames)
        self.assertNotIn(frame_to_remove_key, global_analysis_results)
        self.assertEqual(len(global_extracted_frames), initial_globals_count - 1)

    def test_invalid_request_payload_no_json(self):
        response = self.client.post('/remove_frames', data="this is not json")
        self.assertEqual(response.status_code, 400) # Werkzeug/Flask handles non-JSON here
        data = json.loads(response.data)
        self.assertFalse(data['success'])
        self.assertIn("Invalid request format", data['message']) # Or specific message from Flask

    def test_invalid_request_payload_wrong_structure(self):
        response = self.client.post('/remove_frames', json={'some_other_key': ['frame1.jpg']})
        self.assertEqual(response.status_code, 400)
        data = json.loads(response.data)
        self.assertFalse(data['success'])
        self.assertEqual(data['message'], 'Invalid request format. Expected {"frames": [...]}')

    def test_invalid_request_payload_frames_not_list(self):
        response = self.client.post('/remove_frames', json={'frames': 'not_a_list.jpg'})
        self.assertEqual(response.status_code, 400)
        data = json.loads(response.data)
        self.assertFalse(data['success'])
        self.assertEqual(data['message'], 'Invalid request format. Expected {"frames": [...]}')

    def test_remove_no_frames_empty_list(self):
        initial_extracted_frames = list(global_extracted_frames)
        initial_analysis_results = dict(global_analysis_results)
        
        response = self.client.post('/remove_frames', json={'frames': []})
        data = json.loads(response.data)

        self.assertEqual(response.status_code, 200)
        self.assertTrue(data['success'])
        self.assertEqual(data['message'], 'No frames specified for removal.')

        # Check that no files were deleted and globals are unchanged
        self.assertEqual(global_extracted_frames, initial_extracted_frames)
        self.assertEqual(global_analysis_results, initial_analysis_results)
        for key_path in self.dummy_frames_paths_keys:
            physical_path = os.path.join(app.root_path, key_path)
            self.assertTrue(os.path.exists(physical_path))

if __name__ == '__main__':
    unittest.main()
