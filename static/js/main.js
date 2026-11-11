(() => {
  'use strict';
  document.documentElement.classList.add('js');
  const menu = document.querySelector('.menu-toggle');
  const nav = document.getElementById('main-nav');
  if (menu && nav) {
    menu.hidden = false;
    const closeMenu = () => { nav.classList.remove('is-open'); menu.setAttribute('aria-expanded', 'false'); menu.setAttribute('aria-label', 'Open navigation'); };
    menu.addEventListener('click', () => { const open = nav.classList.toggle('is-open'); menu.setAttribute('aria-expanded', String(open)); menu.setAttribute('aria-label', open ? 'Close navigation' : 'Open navigation'); });
    document.addEventListener('keydown', event => { if (event.key === 'Escape' && nav.classList.contains('is-open')) { closeMenu(); menu.focus(); } });
  }
  document.querySelectorAll('[data-dismiss]').forEach(button => button.addEventListener('click', () => button.closest('.notice').remove()));
  const errorSummary = document.querySelector('.error-summary');
  if (errorSummary) errorSummary.focus();
  document.querySelectorAll('form[data-busy]').forEach(form => {
    form.addEventListener('submit', () => { form.querySelectorAll('button[type="submit"]').forEach(button => { button.disabled = true; button.setAttribute('aria-busy', 'true'); }); });
  });
  window.addEventListener('pageshow', () => document.querySelectorAll('button[aria-busy]').forEach(button => { button.disabled = false; button.removeAttribute('aria-busy'); }));
  document.querySelectorAll('[data-item-photo]').forEach(image => { image.addEventListener('error', () => { image.hidden = true; }); if (image.complete && !image.naturalWidth) image.hidden = true; });
  const status = document.querySelector('[data-copy-status]');
  document.querySelectorAll('[data-copy-target]').forEach(button => button.addEventListener('click', async () => {
    const target = document.getElementById(button.dataset.copyTarget);
    try { await navigator.clipboard.writeText(target.textContent.trim()); if (status) status.textContent = 'Key copied. Store it somewhere private.'; }
    catch { const range = document.createRange(); range.selectNodeContents(target); const selection = window.getSelection(); selection.removeAllRanges(); selection.addRange(range); if (status) status.textContent = 'Select and copy the highlighted key, or download the key file.'; }
  }));
  const download = document.querySelector('[data-download-key]');
  if (download) download.addEventListener('click', () => {
    const key = document.getElementById('management-key').textContent.trim();
    const link = document.getElementById('management-link').href;
    const blob = new Blob(['ReFound private management key\n\nReport ID: ' + download.dataset.reportId + '\nManagement page: ' + link + '\nKey: ' + key + '\n\nKeep this file private. Check your inbox for messages; no automatic notifications are sent.\n'], { type: 'text/plain;charset=utf-8' });
    const url = URL.createObjectURL(blob); const anchor = document.createElement('a'); anchor.href = url; anchor.download = 'refound-' + download.dataset.reportId + '-private-key.txt'; anchor.click(); setTimeout(() => URL.revokeObjectURL(url), 1000);
    if (status) status.textContent = 'Key file prepared. Keep the downloaded file private.';
  });
  const input = document.querySelector('[data-photo-input]');
  if (input) {
    const preview = document.querySelector('[data-photo-preview]'); const name = document.querySelector('[data-photo-name]'); const clear = document.querySelector('[data-clear-photo]'); let objectURL;
    const reset = () => { if (objectURL) URL.revokeObjectURL(objectURL); objectURL = null; preview.hidden = true; preview.removeAttribute('src'); name.textContent = ''; clear.hidden = true; input.setCustomValidity(''); };
    input.addEventListener('change', () => { reset(); const file = input.files[0]; if (!file) return; if (file.size > 5 * 1024 * 1024 || !['image/jpeg', 'image/png'].includes(file.type)) { input.setCustomValidity('Choose a JPEG or PNG no larger than 5 MB.'); input.reportValidity(); name.textContent = 'Choose a JPEG or PNG no larger than 5 MB.'; clear.hidden = false; return; } objectURL = URL.createObjectURL(file); preview.src = objectURL; preview.hidden = false; clear.hidden = false; name.textContent = file.name; });
    clear.addEventListener('click', () => { input.value = ''; reset(); input.focus(); });
    preview.addEventListener('error', () => { preview.hidden = true; name.textContent = 'Preview unavailable. The server will check your image when you submit.'; });
    window.addEventListener('pagehide', () => { if (objectURL) URL.revokeObjectURL(objectURL); });
  }
})();
