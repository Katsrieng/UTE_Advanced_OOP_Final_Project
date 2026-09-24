/* Shared behavior for server-rendered pages; no application state in the DOM. */
(() => {
  const root = document.documentElement;
  const sidebar = document.querySelector('.sidebar');
  const mobile = document.querySelector('.mobile-menu');
  const overlay = document.querySelector('.drawer-overlay');
  const collapse = document.querySelector('.collapse-toggle');
  let drawerFocus;
  function setDrawer(open) {
    root.classList.toggle('drawer-open', open);
    if (overlay) overlay.hidden = !open;
    mobile?.setAttribute('aria-expanded', String(open));
    mobile?.setAttribute('aria-label', open ? 'Close navigation' : 'Open navigation');
    if (sidebar) sidebar.inert = !open && window.innerWidth <= 768;
    if (open) { drawerFocus = document.activeElement; sidebar?.querySelector('a')?.focus(); }
    else drawerFocus?.focus();
  }
  function syncCollapse() {
    const collapsed = root.classList.contains('sidebar-collapsed');
    collapse?.setAttribute('aria-expanded', String(!collapsed));
    collapse?.setAttribute('aria-label', collapsed ? 'Expand sidebar' : 'Collapse sidebar');
  }
  collapse?.addEventListener('click', () => {
    root.classList.toggle('sidebar-collapsed');
    window.igniteStorage.set('ignite-sidebar', root.classList.contains('sidebar-collapsed') ? 'collapsed' : 'expanded');
    syncCollapse();
  });
  syncCollapse();
  mobile?.addEventListener('click', () => setDrawer(!root.classList.contains('drawer-open')));
  overlay?.addEventListener('click', () => setDrawer(false));
  function resize() {
    if (window.innerWidth > 768) setDrawer(false);
    if (sidebar) sidebar.inert = window.innerWidth <= 768 && !root.classList.contains('drawer-open');
  }
  resize();
  window.addEventListener('resize', resize);
  document.addEventListener('keydown', event => {
    if (event.key === 'Escape') {
      if (root.classList.contains('drawer-open')) setDrawer(false);
      document.querySelectorAll('.dropdown[open]').forEach(dropdown => { dropdown.open = false; dropdown.querySelector('summary').focus(); });
    }
    if (event.key === '/' && !event.ctrlKey && !event.metaKey && !['INPUT', 'TEXTAREA', 'SELECT'].includes(document.activeElement.tagName)) {
      event.preventDefault(); document.querySelector('.global-search input')?.focus();
    }
    if (event.key === 'Tab' && root.classList.contains('drawer-open')) {
      const targets = [...sidebar.querySelectorAll('a,button')].filter(el => el.offsetParent !== null);
      const first = targets[0], last = targets.at(-1);
      if (event.shiftKey && document.activeElement === first) { event.preventDefault(); last.focus(); }
      else if (!event.shiftKey && document.activeElement === last) { event.preventDefault(); first.focus(); }
    }
  });
  document.querySelectorAll('.dropdown').forEach(dropdown => {
    dropdown.addEventListener('toggle', () => {
      if (!dropdown.open) return;
      document.querySelectorAll('.dropdown[open]').forEach(other => { if (other !== dropdown) other.open = false; });
      if (dropdown.classList.contains('row-dropdown')) {
        const rect = dropdown.querySelector('summary').getBoundingClientRect();
        const panel = dropdown.querySelector('.dropdown-panel');
        panel.style.left = Math.max(8, Math.min(rect.right - 200, innerWidth - 208)) + 'px';
        panel.style.top = Math.max(8, Math.min(rect.bottom + 4, innerHeight - panel.offsetHeight - 8)) + 'px';
      }
    });
  });
  document.addEventListener('click', event => document.querySelectorAll('.dropdown[open]').forEach(dropdown => { if (!dropdown.contains(event.target)) dropdown.open = false; }));
  document.addEventListener('scroll', () => document.querySelectorAll('.row-dropdown[open]').forEach(dropdown => { dropdown.open = false; }), true);
  window.toast = (message, type = 'info') => {
    const host = document.querySelector('#toasts');
    if (!host) return;
    const toast = document.createElement('div');
    toast.className = `alert toast ${['success', 'error', 'warning', 'info'].includes(type) ? type : 'info'}`;
    const text = document.createElement('span'); text.textContent = message;
    const close = document.createElement('button'); close.type = 'button'; close.className = 'icon-button'; close.setAttribute('aria-label', 'Dismiss notification'); close.textContent = '×';
    close.addEventListener('click', () => toast.remove());
    toast.append(text, close); host.append(toast);
    let timer = setTimeout(() => toast.remove(), 6000);
    toast.addEventListener('mouseenter', () => clearTimeout(timer));
    toast.addEventListener('focusin', () => clearTimeout(timer));
    toast.addEventListener('mouseleave', () => { timer = setTimeout(() => toast.remove(), 4000); });
  };
  document.querySelectorAll('[data-dismiss]').forEach(button => button.addEventListener('click', () => button.closest('.alert').remove()));
  document.querySelectorAll('[data-toast]').forEach(alert => { window.toast(alert.firstChild.textContent.trim(), alert.dataset.toast); alert.remove(); });
  window.confirmAction = (message, options = {}) => new Promise(resolve => {
    const dialog = document.querySelector('#confirmation');
    document.querySelector('#confirmation-message').textContent = message;
    document.querySelector('#confirmation-title').textContent = options.title || 'Confirm action';
    dialog.querySelector('[value="confirm"]').textContent = options.confirmLabel || 'Confirm';
    dialog.returnValue = '';
    dialog.addEventListener('close', () => resolve(dialog.returnValue === 'confirm'), { once: true });
    dialog.showModal();
  });
  document.querySelector('[data-password-toggle]')?.addEventListener('click', event => {
    const input = document.querySelector('#password'), show = input.type === 'password';
    input.type = show ? 'text' : 'password'; event.currentTarget.textContent = show ? 'Hide' : 'Show';
    event.currentTarget.setAttribute('aria-label', show ? 'Hide password' : 'Show password');
  });
  document.querySelectorAll('[data-print]').forEach(button => button.addEventListener('click', () => window.print()));
  document.querySelectorAll('form:not([data-custom-submit])').forEach(form => form.addEventListener('submit', event => {
    if (event.defaultPrevented || form.method === 'dialog' || form.method === 'get') return;
    const button = event.submitter;
    if (button) { button.classList.add('loading'); button.setAttribute('aria-busy', 'true'); setTimeout(() => { button.disabled = true; }, 0); }
  }));
  window.addEventListener('pageshow', () => document.querySelectorAll('.loading').forEach(button => { button.classList.remove('loading'); button.disabled = false; button.removeAttribute('aria-busy'); }));
  document.querySelector('#form-errors')?.focus();
  document.querySelectorAll('img[data-image-fallback], img[src*="/images/vehicles/"]').forEach(image => {
    const fallback = () => {
      if (image.dataset.fallback) return;
      image.dataset.fallback = 'true';
      image.src = image.dataset.imageFallback || image.src.replace(/\/[^/]+$/, '/sedan.svg');
      image.classList.remove('is-photo');
      if (image.alt) image.alt = 'Generic vehicle illustration';
    };
    image.addEventListener('error', fallback);
    if (image.complete && !image.naturalWidth) fallback();
  });
})();
