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
            extracting             = false;
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
});
