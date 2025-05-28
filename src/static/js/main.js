// main.js
// Handles video upload, frame extraction via SSE, and frame removal in the client UI

document.addEventListener('DOMContentLoaded', () => {
  // --- Video Upload Section ---
  const fileInput      = document.getElementById('video');
  const cancelUpload   = document.getElementById('cancel-upload');
  const progressBar    = document.getElementById('upload-progress');
  const statusText     = document.getElementById('upload-status');
  const extractBtn     = document.getElementById('extract-btn');
  const analyzeBtn     = document.getElementById('analyze-btn');
  const cancelAnalysis = document.getElementById('cancel-analysis');
  const viewLinks      = Array.from(document.querySelectorAll('a'));

  // Enable or disable page controls during upload/extraction
  function setPageDisabled(disabled) {
    [fileInput, extractBtn, analyzeBtn, cancelAnalysis].forEach(el => el && (el.disabled = disabled));
    viewLinks.forEach(a => a.style.pointerEvents = disabled ? 'none' : '');
  }

  let xhrUpload;

  if (fileInput && progressBar && statusText) {
    // Handle new file selection and upload
    fileInput.addEventListener('change', () => {
      const file = fileInput.files[0];
      if (!file) return;

      setPageDisabled(true);
      fileInput.style.display    = 'none';
      cancelUpload.style.display = 'inline-block';

      // Prepare form data and start XHR upload
      const formData = new FormData();
      formData.append('video', file);
      xhrUpload = new XMLHttpRequest();
      xhrUpload.open('POST', '/upload', true);

      // Update progress bar
      xhrUpload.upload.onprogress = (e) => {
        if (e.lengthComputable) {
          progressBar.style.display = 'block';
          progressBar.value = Math.round((e.loaded / e.total) * 100);
        }
      };

      // Handle upload completion
      xhrUpload.onload = () => {
        setPageDisabled(false);
        fileInput.value            = '';
        fileInput.style.display    = '';
        cancelUpload.style.display = 'none';
        progressBar.style.display  = 'none';
        progressBar.value          = 0;

        if (xhrUpload.status === 200) {
          try {
            const resp = JSON.parse(xhrUpload.responseText);
            statusText.textContent = resp.success
              ? resp.message
              : 'Upload failed: ' + resp.message;
          } catch (err) {
            console.error('Upload JSON parse error', err);
            statusText.textContent = 'Unexpected server response.';
          }
        } else {
          statusText.textContent = 'Upload error: ' + xhrUpload.statusText;
        }
        setTimeout(() => { statusText.textContent = ''; }, 3000);
      };

      // Handle network errors
      xhrUpload.onerror = () => {
        setPageDisabled(false);
        fileInput.style.display    = '';
        cancelUpload.style.display = 'none';
        progressBar.style.display  = 'none';
        progressBar.value          = 0;
        statusText.textContent     = 'Upload network error.';
      };

      xhrUpload.send(formData);
    });

    // Allow user to cancel an ongoing upload
    cancelUpload.addEventListener('click', () => {
      if (xhrUpload) xhrUpload.abort();
      statusText.textContent     = 'Upload canceled.';
      setPageDisabled(false);
      fileInput.value            = '';
      fileInput.style.display    = '';
      cancelUpload.style.display = 'none';
      progressBar.style.display  = 'none';
      progressBar.value          = 0;
    });
  } else {
    console.warn('Upload elements not found in DOM');
  }

  // --- Frame Extraction Section (SSE) ---
  const intervalInput = document.getElementById('interval');
  const extractProg   = document.getElementById('extract-progress');
  let extracting      = false;

  if (extractBtn && intervalInput && extractProg) {
    extractBtn.addEventListener('click', (e) => {
      e.preventDefault();

      // Cancel extraction if already running
      if (extracting) {
        if (window._sseSource) window._sseSource.close();
        fetch('/extract/abort', { method: 'POST' });
        setPageDisabled(false);
        extractBtn.textContent = 'Extract Frames';
        extracting = false;
        return;
      }

      const interval = intervalInput.value.trim();
      extractProg.textContent = '';

      setPageDisabled(true);
      extractBtn.disabled = false;
      extractBtn.textContent = 'Cancel Extraction';
      extracting             = true;

      // Clean up any previous SSE
      if (window._sseSource) {
        window._sseSource.close();
      }

      // Start Server-Sent Events connection
      try {
        const src = new EventSource(`/extract?interval=${encodeURIComponent(interval)}`);
        window._sseSource = src;

        src.onmessage = (evt) => {
          extractProg.textContent += evt.data + "\n";

          // On completion, close SSE and show preview UI
          if (evt.data.startsWith("Extraction complete")) {
            window._sseSource.close();
            setPageDisabled(false);
            extractBtn.textContent = 'Extract Frames';
            extracting = false;

            document.getElementById('preview-section').style.display = 'block';

            // Fetch and render frame thumbnails
            fetch('/preview_frames')
              .then(response => response.json())
              .then(json => {
                const grid     = document.getElementById('preview-grid');
                const removeB  = document.getElementById('pre-remove-btn');
                const analyzeB = analyzeBtn

                grid.innerHTML = '';

                json.frames.forEach(name => {
                  const item = document.createElement('div');
                  item.classList.add('frame-item');

                  const cb = document.createElement('input');
                  cb.type        = 'checkbox';
                  cb.value       = name;
                  cb.classList.add('frame-checkbox');

                  const img = document.createElement('img');
                  img.src     = `/frames/${name}`;
                  img.width   = 160;
                  img.loading = 'lazy';

                  item.append(cb, img);
                  grid.appendChild(item);
                });

                // Enable remove and analyze buttons
                removeB.disabled  = false;
                analyzeB.disabled = false;

                // Wire up the Remove button in preview
                removeB.addEventListener('click', () => {
                  const toRemove = Array.from(
                    grid.querySelectorAll('.frame-checkbox:checked')
                  ).map(cb => cb.value);

                  if (!toRemove.length) return alert('Select frames first.');
                  removeB.disabled = true;

                  fetch('/remove_frames', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ frames: toRemove })
                  })
                  .then(r => r.json())
                  .then(data => {
                    if (data.success) {
                      toRemove.forEach(name => {
                        const el = grid.querySelector(`.frame-checkbox[value="${name}"]`).closest('.frame-item');
                        el.remove();
                      });
                    } else {
                      alert('Remove error: ' + data.message);
                    }
                  })
                  .catch(() => alert('Network error during removal'))
                  .finally(() => { removeB.disabled = false; });
                });
              });
          }
        };

        // Handle SSE errors
        src.onerror = (err) => {
          console.error('SSE error:', err);
          extractProg.textContent += "Error in extraction stream\n";
          window._sseSource.close();
          setPageDisabled(false);
          extractBtn.textContent = 'Extract Frames';
          extracting             = false;
        };
      } catch (err) {
        console.error('Failed to start EventSource', err);
        extractProg.textContent = "Could not start extraction.\n";
      }
    });
  } else {
    console.warn('Extraction elements not found in DOM');
  }

  // --- Analysis Section (SSE) ---
  const analysisProg = document.getElementById('analysis-progress');
  let analyzing     = false;

  if (analyzeBtn && cancelAnalysis && analysisProg) {
    analyzeBtn.addEventListener('click', (e) => {
      e.preventDefault();

      if (analyzing) {
        // cancel
        if (window._analysisSource) window._analysisSource.close();
        fetch('/analyze/abort', { method: 'POST' });
        setPageDisabled(false);
        analyzeBtn.textContent      = 'Run Analysis';
        cancelAnalysis.style.display = 'none';
        analyzing                   = false;
        return;
      }

      // start
      const context = document.getElementById('context').value.trim();
      analysisProg.textContent = '';

      setPageDisabled(true);
      analyzeBtn.disabled          = false; // so user can click “Stop”
      analyzeBtn.textContent       = 'Stop Analysis';
      cancelAnalysis.style.display = 'inline-block';
      analyzing                     = true;

      if (window._analysisSource) window._analysisSource.close();
      const src = new EventSource(`/analyze_stream?context=${encodeURIComponent(context)}`);
      window._analysisSource = src;

      src.onmessage = (evt) => {
        analysisProg.textContent += evt.data + "\n";
        if (evt.data.startsWith("Analysis complete")) {
          window._analysisSource.close();
          setPageDisabled(false);
          analyzeBtn.textContent       = 'Run Analysis';
          cancelAnalysis.style.display = 'none';
          analyzing                    = false;
        }
      };

      src.onerror = (err) => {
        console.error('SSE error:', err);
        analysisProg.textContent += "Error in analysis stream\n";
        window._analysisSource.close();
        setPageDisabled(false);
        analyzeBtn.textContent       = 'Run Analysis';
        cancelAnalysis.style.display = 'none';
        analyzing                    = false;
      };
    });

    cancelAnalysis.addEventListener('click', () => {
      // identical cancel logic
      if (window._analysisSource) window._analysisSource.close();
      fetch('/extract/abort', { method: 'POST' });
      setPageDisabled(false);
      analyzeBtn.textContent      = 'Run Analysis';
      cancelAnalysis.style.display = 'none';
      analyzing                   = false;
    });
  } else {
    console.warn('Analysis elements not found in DOM');
  }

  // --- Frame Removal Section ---
  const removeFramesBtn = document.getElementById('remove-frames-btn');

  if (removeFramesBtn) {
    // Handle removal of selected frames after analysis
    removeFramesBtn.addEventListener('click', () => {
      const selectedCheckboxes = document.querySelectorAll('.frame-checkbox:checked');
      const framesToRemove = Array.from(selectedCheckboxes).map(cb => cb.value);

      if (framesToRemove.length === 0) {
        alert('Please select frames to remove.');
        return;
      }

      removeFramesBtn.disabled = true;
      removeFramesBtn.textContent = 'Removing...';

      fetch('/remove_frames', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ frames: framesToRemove }),
      })
      .then(response => {
        if (!response.ok) {
          return response.json().then(errData => {
            throw new Error(errData.message || `Server error: ${response.statusText}`);
          });
        }
        return response.json();
      })
      .then(data => {
        if (data.success) {
          location.reload();
        } else {
          alert('Error removing frames: ' + (data.message || 'Unknown error from server.'));
        }
      })
      .catch(error => {
        console.error('Error:', error);
        alert('Failed to remove frames: ' + error.message);
      })
      .finally(() => {
        // Re-enable button if page not reloaded
        if (document.getElementById('remove-frames-btn')) {
          removeFramesBtn.disabled = false;
          removeFramesBtn.textContent = 'Remove Selected Frames';
        }
      });
    });
  } // end removeFramesBtn check
});
