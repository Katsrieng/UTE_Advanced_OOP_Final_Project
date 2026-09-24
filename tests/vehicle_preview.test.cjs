const { test } = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const source = fs.readFileSync(path.join(__dirname, '../app/static/js/vehicles.js'), 'utf8');

function previewFile(file, dimensions = [24, 16], readable = true) {
  const handlers = {};
  const classes = new Set();
  const preview = { src: 'original.svg', alt: 'Original', dataset: {}, classList: {
    contains: v => classes.has(v), add: v => classes.add(v),
    toggle: (v, enabled) => enabled ? classes.add(v) : classes.delete(v),
  }};
  const input = { files: [file], value: file.name, invalid: false,
    addEventListener: (name, fn) => { handlers[name] = fn; },
    setAttribute: () => { input.invalid = true; }, removeAttribute: () => { input.invalid = false; },
  };
  const error = { textContent: '' };
  const selection = { textContent: 'Original' };
  const clear = { hidden: true, addEventListener: (_, fn) => { handlers.clear = fn; } };
  const elements = { '#photo': input, '.photo-preview-image': preview, '[data-clear-photo]': clear };
  const editor = { querySelector: name => elements[name] || null };
  const revoked = [];
  class Image {
    constructor() { [this.naturalWidth, this.naturalHeight] = dimensions; }
    set src(value) { readable ? this.onload() : this.onerror(); }
  }
  vm.runInNewContext(source, {
    document: { querySelector: name => ({ '[data-photo-editor]': editor, '#photo-error': error, '#photo-selection': selection })[name] },
    URL: { createObjectURL: () => 'blob:selected', revokeObjectURL: url => revoked.push(url) },
    Image, window: { addEventListener: (name, fn) => { handlers[name] = fn; } },
  });
  handlers.change();
  return { input, preview, error, selection, clear, handlers, revoked };
}

for (const [name, type] of [
  ['car.jpg', 'image/jpeg'], ['car.jpeg', 'image/jpeg'], ['car.png', 'image/png'],
  ['car.webp', 'image/webp'], ['CAR.PNG', 'image/x-png'], ['car.png', ''],
  ['car.png', 'application/octet-stream'],
]) {
  test(`preview accepts decoded ${name} with MIME ${type || '(empty)'}`, () => {
    const result = previewFile({ name, type, size: 1024 });
    assert.equal(result.error.textContent, '');
    assert.equal(result.preview.src, 'blob:selected');
    assert.equal(result.input.value, name); // Selection remains available for form upload.
    assert.equal(result.clear.hidden, false);
    result.handlers.clear();
    assert.equal(result.preview.src, 'original.svg');
    assert.equal(result.input.value, '');
    assert.deepEqual(result.revoked, ['blob:selected']);
  });
}
test('unsupported extension is rejected even with an image MIME type', () => {
  assert.equal(previewFile({ name: 'car.svg', type: 'image/png', size: 1 }).input.invalid, true);
});
test('undecodable PNG is rejected', () => {
  const result = previewFile({ name: 'car.png', size: 1 }, [24, 16], false);
  assert.equal(result.input.invalid, true);
  assert.equal(result.preview.src, 'original.svg');
});
test('byte and pixel limits are retained', () => {
  assert.equal(previewFile({ name: 'car.png', size: 5 * 1024 * 1024 + 1 }).input.invalid, true);
  assert.equal(previewFile({ name: 'car.png', size: 1 }, [5000, 4001]).input.invalid, true);
});
