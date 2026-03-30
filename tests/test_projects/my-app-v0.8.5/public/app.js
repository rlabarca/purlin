// ── Pure validation functions (exported for Node.js tests) ───────────────────

function validateIssueType(issueType) {
  return typeof issueType === 'string' && issueType.trim() !== '';
}

function validateFileSize(sizeBytes, maxBytes) {
  if (maxBytes === undefined) maxBytes = 5 * 1024 * 1024;
  return sizeBytes <= maxBytes;
}

function createDefaultState() {
  return { issueType: '', details: '', attachment: null };
}

// ── DOM wiring (browser-only) ─────────────────────────────────────────────────

if (typeof document !== 'undefined') {
  const selectEl       = document.getElementById('issue-type');
  const detailsEl      = document.getElementById('details');
  const fileInput      = document.getElementById('file-input');
  const btnUpload      = document.getElementById('btn-upload');
  const btnClose       = document.getElementById('btn-close');
  const btnCancel      = document.getElementById('btn-cancel');
  const btnSubmit      = document.getElementById('btn-submit');
  const issueError     = document.getElementById('issue-type-error');
  const attachError    = document.getElementById('attachment-error');
  const attachName     = document.getElementById('attachment-filename');
  const statusEl       = document.getElementById('modal-status');

  let attachedFile = null;

  // Upload button opens file picker
  btnUpload.addEventListener('click', () => fileInput.click());

  // File selected
  fileInput.addEventListener('change', () => {
    const file = fileInput.files[0];
    if (!file) return;

    if (!validateFileSize(file.size)) {
      attachError.textContent = 'File exceeds the 5MB size limit.';
      attachName.textContent = '';
      attachedFile = null;
      fileInput.value = '';
      return;
    }

    attachError.textContent = '';
    attachedFile = file;
    attachName.textContent = file.name;
  });

  // Reset form
  function resetForm() {
    selectEl.value = '';
    detailsEl.value = '';
    fileInput.value = '';
    attachedFile = null;
    attachName.textContent = '';
    attachError.textContent = '';
    issueError.textContent = '';
    statusEl.textContent = '';
    statusEl.className = 'modal-status';
  }

  btnClose.addEventListener('click', resetForm);
  btnCancel.addEventListener('click', resetForm);

  // Submit
  btnSubmit.addEventListener('click', async () => {
    // Validate issue type
    if (!validateIssueType(selectEl.value)) {
      issueError.textContent = 'Please select an issue type.';
      return;
    }
    issueError.textContent = '';

    const formData = new FormData();
    formData.append('issueType', selectEl.value);
    formData.append('details', detailsEl.value);
    if (attachedFile) {
      formData.append('attachment', attachedFile);
    }

    btnSubmit.disabled = true;
    try {
      const res = await fetch('/feedback', { method: 'POST', body: formData });
      const data = await res.json();
      if (res.ok) {
        statusEl.textContent = 'Thank you! Your feedback has been submitted.';
        statusEl.className = 'modal-status success';
        resetForm();
      } else {
        statusEl.textContent = 'Something went wrong. Please try again.';
        statusEl.className = 'modal-status error';
      }
    } catch (e) {
      statusEl.textContent = 'Something went wrong. Please try again.';
      statusEl.className = 'modal-status error';
    } finally {
      btnSubmit.disabled = false;
    }
  });
}

// ── CommonJS export for Node.js tests ─────────────────────────────────────────
if (typeof module !== 'undefined') {
  module.exports = { validateIssueType, validateFileSize, createDefaultState };
}
