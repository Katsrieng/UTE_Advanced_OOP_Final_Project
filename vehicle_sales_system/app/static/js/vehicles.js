/* Local preview only. Uploads happen with the existing vehicle form POST. */
(() => {
  const editor = document.querySelector('[data-photo-editor]');
  if (!editor) return;
  const input = editor.querySelector('#photo');
  const preview = editor.querySelector('.photo-preview-image');
  const error = document.querySelector('#photo-error');
  const selection = document.querySelector('#photo-selection');
  const clear = editor.querySelector('[data-clear-photo]');
  const original = { src: preview.src, alt: preview.alt, photo: preview.classList.contains('is-photo'), label: selection.textContent };
  let objectURL = null;
  let generation = 0;

  function releasePreview() {
    if (objectURL) URL.revokeObjectURL(objectURL);
    objectURL = null;
  }
  function restore() {
    generation++;
    releasePreview();
    preview.src = original.src;
    preview.alt = original.alt;
    preview.classList.toggle('is-photo', original.photo);
    input.value = '';
    clear.hidden = true;
    selection.textContent = original.label;
  }
  function reject(message) {
    restore();
    error.textContent = message;
    input.setAttribute('aria-invalid', 'true');
  }
  input.addEventListener('change', () => {
    error.textContent = '';
    input.removeAttribute('aria-invalid');
    const file = input.files[0];
    if (!file) { restore(); return; }
    if (!/\.(jpe?g|png|webp)$/i.test(file.name) || (file.type && !['image/jpeg', 'image/png', 'image/webp'].includes(file.type))) {
      reject('Choose a JPG, JPEG, PNG or WebP photo.'); return;
    }
    if (file.size > 5 * 1024 * 1024) {
      reject('The photo is too large. Maximum size is 5 MB.'); return;
    }
    releasePreview();
    const current = ++generation;
    objectURL = URL.createObjectURL(file);
    const candidateURL = objectURL;
    const candidate = new Image();
    candidate.onload = () => {
      if (current !== generation) return;
      if (candidate.naturalWidth * candidate.naturalHeight > 20_000_000) {
        reject('Choose a photo with no more than 20 million pixels.'); return;
      }
      preview.src = candidateURL;
      preview.alt = 'Preview of selected vehicle photo';
      preview.classList.add('is-photo');
      delete preview.dataset.fallback;
      clear.hidden = false;
      selection.textContent = `${file.name} · ${(file.size / 1024).toFixed(0)} KB · Not saved yet`;
    };
    candidate.onerror = () => { if (current === generation) reject('This file could not be read as an image. Choose another photo.'); };
    candidate.src = candidateURL;
  });
  clear.addEventListener('click', () => { restore(); error.textContent = ''; input.removeAttribute('aria-invalid'); });
  window.addEventListener('pagehide', releasePreview);
  window.addEventListener('pageshow', event => { if (event.persisted) restore(); });

  const remove = editor.querySelector('[data-remove-photo]');
  remove?.addEventListener('click', async () => {
    const confirmed = await window.confirmAction(
      'This will remove the uploaded photo and restore the default vehicle image. The vehicle itself will not be deleted. Other unsaved form changes will not be saved.',
      { title: 'Remove this vehicle photo?', confirmLabel: 'Remove Photo' }
    );
    if (!confirmed) return;
    remove.disabled = true;
    remove.classList.add('loading');
    const form = document.createElement('form');
    form.method = 'post';
    form.action = remove.dataset.removeUrl;
    for (const [name, value] of Object.entries({ csrf_token: input.form.querySelector('[name="csrf_token"]').value, confirm_remove: 'yes' })) {
      const field = document.createElement('input');
      field.type = 'hidden'; field.name = name; field.value = value;
      form.append(field);
    }
    document.body.append(form);
    form.submit();
  });
})();
