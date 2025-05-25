// Add frame choosing feature (Frame choosing, and addition)

document.addEventListener('DOMContentLoaded', () => {
  //
  // 1. Video Upload
  //
  const fileInput    = document.getElementById('video');
  const cancelUpload = document.getElementById('cancel-upload');
  const progressBar  = document.getElementById('upload-progress');
  const statusText   = document.getElementById('upload-status');
  const extractBtn   = document.getElementById('extract-btn');
  const analyzeBtn   = document.querySelector('form[action$="/analyze"] button[type="submit"]');
  const viewLinks    = Array.from(document.querySelectorAll('a'));

  function setPageDisabled(disabled) {
    [fileInput, extractBtn, analyzeBtn].forEach(el => el && (el.disabled = disabled));
    viewLinks.forEach(a => a.style.pointerEvents = disabled ? 'none' : '');
  }

  let xhrUpload;

  if (fileInput && progressBar && statusText) {
    fileInput.addEventListener('change', () => {
      const file = fileInput.files[0];
      if (!file) return;

      setPageDisabled(true);
      fileInput.style.display    = 'none';
      cancelUpload.style.display = 'inline-block';

      const formData = new FormData();
      formData.append('video', file);

      xhrUpload = new XMLHttpRequest();
      xhrUpload.open('POST', '/upload', true);

      xhrUpload.upload.onprogress = (e) => {
        if (e.lengthComputable) {
          progressBar.style.display = 'block';
          progressBar.value = Math.round((e.loaded / e.total) * 100);
        }
      };

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

  //
  // 2. Frame Extraction (SSE)
  //
  const intervalInput = document.getElementById('interval');
  const extractProg   = document.getElementById('extract-progress');
  let extracting      = false;

  if (extractBtn && intervalInput && extractProg) {
    extractBtn.addEventListener('click', (e) => {
      e.preventDefault();

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

      if (window._sseSource) {
        window._sseSource.close();
      }

      try {
        const src = new EventSource(`/extract?interval=${encodeURIComponent(interval)}`);
        window._sseSource = src;

        src.onmessage = (evt) => {
          extractProg.textContent += evt.data + "\n";
          if (evt.data.startsWith("Extraction complete")) {
            window._sseSource.close();
            setPageDisabled(false);
            extractBtn.textContent = 'Extract Frames';
            extracting = false;

            // Show the pre-analysis preview UI
            document.getElementById('preview-section').style.display = 'block';

            // Fetch and render the thumbnails
            fetch('/preview_frames')
              .then(response => response.json())
              .then(json => {
                const grid     = document.getElementById('preview-grid');
                const removeB  = document.getElementById('pre-remove-btn');
                const analyzeB = document.querySelector('form[action$="/analyze"] button[type="submit"]');

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

                // Enable the Remove and Analyze buttons
                removeB.disabled  = false;
                analyzeB.disabled = false;

                // Wire up the Remove button
                removeB.addEventListener('click', () => {
                  const toRemove = Array.from(
                    grid.querySelectorAll('.frame-checkbox:checked')
                  ).map(cb => cb.value);

                  if (!toRemove.length) {
                    return alert('Select frames first.');
                  }
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
                        const el = grid.querySelector(`.frame-checkbox[value="${name}"]`)
                                        .closest('.frame-item');
                        el.remove();
                      });
                    } else {
                      alert('Remove error: ' + data.message);
                    }
                  })
                  .catch(() => alert('Network error during removal'))
                  .finally(() => {
                    removeB.disabled = false;
                  });
                });
              });
          }
        };

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

  //
  // 3. Frame Removal
  //
  const removeFramesBtn = document.getElementById('remove-frames-btn');

  if (removeFramesBtn) {
    removeFramesBtn.addEventListener('click', () => {
      const selectedCheckboxes = document.querySelectorAll('.frame-checkbox:checked');
      const framesToRemove = Array.from(selectedCheckboxes).map(cb => cb.value);

      if (framesToRemove.length === 0) {
        alert('Please select frames to remove.');
        return;
      }

      // Disable button to prevent multiple clicks
      removeFramesBtn.disabled = true;
      removeFramesBtn.textContent = 'Removing...';

      fetch('/remove_frames', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ frames: framesToRemove }),
      })
      .then(response => {
        if (!response.ok) {
          // Try to get error message from response body if possible
          return response.json().then(errData => {
            throw new Error(errData.message || `Server error: ${response.statusText}`);
          }).catch(() => {
            // If parsing error body fails, throw generic error
            throw new Error(`Server error: ${response.statusText} (Status: ${response.status})`);
          });
        }
        return response.json();
      })
      .then(data => {
        if (data.success) {
          // alert('Frames removed successfully. Reloading...'); // Optional: give user feedback before reload
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
        // Re-enable button if it's still on the page (i.e., no reload happened)
        if (document.getElementById('remove-frames-btn')) {
            removeFramesBtn.disabled = false;
            removeFramesBtn.textContent = 'Remove Selected Frames';
        }
      });
    });
  } else {
    // This is not an error, just means the button isn't on the current page.
    // console.log('Remove frames button not found on this page.');
  }
});
