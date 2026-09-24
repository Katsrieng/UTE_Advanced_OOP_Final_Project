/* Runs in <head> before CSS to prevent a light-theme flash. */
(() => {
  const storage = {
    get(key) { try { return localStorage.getItem(key); } catch { return null; } },
    set(key, value) { try { localStorage.setItem(key, value); } catch { /* Private mode remains usable. */ } }
  };
  window.igniteStorage = storage;
  const saved = storage.get('ignite-theme');
  document.documentElement.dataset.theme = saved === 'light' ? 'light' : 'dark';
  if (storage.get('ignite-sidebar') === 'collapsed') document.documentElement.classList.add('sidebar-collapsed');
  function syncButtons() {
    const dark = document.documentElement.dataset.theme === 'dark';
    document.querySelectorAll('.theme-toggle').forEach(button => {
      button.setAttribute('aria-label', `Switch to ${dark ? 'light' : 'dark'} mode`);
      button.title = button.getAttribute('aria-label');
      button.querySelector('.theme-icon').innerHTML = dark
        ? '<svg class="icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" aria-hidden="true"><circle cx="12" cy="12" r="4"/><path d="M12 2v2m0 16v2M2 12h2m16 0h2M5 5l1.5 1.5m11 11L19 19M5 19l1.5-1.5m11-11L19 5"/></svg>'
        : '<svg class="icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" aria-hidden="true"><path d="M20.5 14A8.5 8.5 0 0 1 10 3.5 8.5 8.5 0 1 0 20.5 14Z"/></svg>';
    });
  }
  document.addEventListener('DOMContentLoaded', () => {
    syncButtons();
    document.querySelectorAll('.theme-toggle').forEach(button => button.addEventListener('click', () => {
      const theme = document.documentElement.dataset.theme === 'dark' ? 'light' : 'dark';
      document.documentElement.dataset.theme = theme;
      storage.set('ignite-theme', theme);
      syncButtons();
      document.dispatchEvent(new CustomEvent('themechange', { detail: { theme } }));
    }));
  });
})();
