document.addEventListener('DOMContentLoaded', () => {
  //
  // 1. Video Upload
  //
  const fileInput   = document.getElementById('video');
  const progressBar = document.getElementById('upload-progress');
  const statusText  = document.getElementById('upload-status');

  if (fileInput && progressBar && statusText) {
    fileInput.addEventListener('change', () => {
      const file = fileInput.files[0];
      if (!file) return;

      const formData = new FormData();
      formData.append('video', file);

      const xhr = new XMLHttpRequest();
      xhr.open('POST', '/upload', true);

      xhr.upload.onprogress = (e) => {
        if (e.lengthComputable) {
          const pct = (e.loaded / e.total) * 100;
          progressBar.style.display = 'block';
          progressBar.value = Math.round(pct);
        }
      };

      xhr.onload = () => {
        if (xhr.status === 200) {
          try {
            const resp = JSON.parse(xhr.responseText);
            if (resp.success) {
              statusText.textContent = resp.message;
              // auto‐hide after a bit
              setTimeout(() => {
                progressBar.style.display = 'none';
                progressBar.value = 0;
                statusText.textContent = '';
              }, 3000);
            } else {
              statusText.textContent = 'Upload failed: ' + resp.message;
            }
          } catch (err) {
            console.error('Upload JSON parse error', err);
            statusText.textContent = 'Unexpected server response.';
          }
        } else {
          statusText.textContent = 'Upload error: ' + xhr.statusText;
        }
      };

      xhr.onerror = () => {
        statusText.textContent = 'Upload network error.';
      };

      xhr.send(formData);
    });
  } else {
    console.warn('Upload elements not found in DOM');
  }

  //
  // 2. Frame Extraction (SSE)
  //
  const extractBtn    = document.getElementById('extract-btn');
  const intervalInput = document.getElementById('interval');
  const extractProg   = document.getElementById('extract-progress');

  if (extractBtn && intervalInput && extractProg) {
    extractBtn.addEventListener('click', (e) => {
      e.preventDefault();
      const interval = intervalInput.value.trim();
      extractProg.textContent = '';

      // ensure previous EventSource is closed
      if (window._sseSource) {
        window._sseSource.close();
      }

      try {
        const src = new EventSource(`/extract?interval=${encodeURIComponent(interval)}`);
        window._sseSource = src;

        src.onmessage = (evt) => {
          extractProg.textContent += evt.data + "\n";
          if (evt.data.startsWith("Extraction complete")) {
            src.close();
          }
        };

        src.onerror = (err) => {
          console.error('SSE error:', err);
          extractProg.textContent += "Error in extraction stream\n";
          src.close();
        };
      } catch (err) {
        console.error('Failed to start EventSource', err);
        extractProg.textContent = "Could not start extraction.\n";
      }
    });
  } else {
    console.warn('Extraction elements not found in DOM');
  }
});
