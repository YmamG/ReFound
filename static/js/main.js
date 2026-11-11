(() => {
  'use strict';
  const ar = document.documentElement.lang.startsWith('ar');
  const t = (english, arabic) => ar ? arabic : english;
  document.documentElement.classList.add('js');
  const menu = document.querySelector('.menu-toggle');
  const nav = document.getElementById('main-nav');
  if (menu && nav) {
    menu.hidden = false;
    const closeMenu = () => {
      nav.classList.remove('is-open');
      menu.setAttribute('aria-expanded', 'false');
      menu.setAttribute('aria-label', t('Open navigation', 'فتح القائمة'));
    };
    menu.addEventListener('click', () => {
      const open = nav.classList.toggle('is-open');
      menu.setAttribute('aria-expanded', String(open));
      menu.setAttribute('aria-label', open ? t('Close navigation', 'إغلاق القائمة') : t('Open navigation', 'فتح القائمة'));
    });
    document.addEventListener('keydown', event => {
      if (event.key === 'Escape' && nav.classList.contains('is-open')) { closeMenu(); menu.focus(); }
    });
  }
  document.querySelectorAll('[data-dismiss]').forEach(button => button.addEventListener('click', () => button.closest('.notice').remove()));
  const summary = document.querySelector('.error-summary');
  if (summary) summary.focus();
  document.querySelectorAll('form[data-busy]').forEach(form => {
    form.addEventListener('submit', () => form.querySelectorAll('button[type="submit"]').forEach(button => {
      button.disabled = true; button.setAttribute('aria-busy', 'true');
      button.dataset.originalText = button.textContent;
      button.textContent = t('Sending…', 'جارٍ الإرسال…');
    }));
  });
  window.addEventListener('pageshow', () => document.querySelectorAll('button[aria-busy]').forEach(button => {
    button.disabled = false; button.removeAttribute('aria-busy');
    if (button.dataset.originalText) button.textContent = button.dataset.originalText;
  }));
  document.querySelectorAll('[data-item-photo]').forEach(image => {
    image.addEventListener('error', () => { image.hidden = true; });
    if (image.complete && !image.naturalWidth) image.hidden = true;
  });
  const input = document.querySelector('[data-photo-input]');
  if (input) {
    const preview = document.querySelector('[data-photo-preview]');
    const name = document.querySelector('[data-photo-name]');
    const clear = document.querySelector('[data-clear-photo]');
    let objectURL;
    const reset = () => {
      if (objectURL) URL.revokeObjectURL(objectURL);
      objectURL = null; preview.hidden = true; preview.removeAttribute('src');
      name.textContent = ''; clear.hidden = true; input.setCustomValidity('');
    };
    input.addEventListener('change', () => {
      reset(); const file = input.files[0]; if (!file) return;
      if (file.size > 5 * 1024 * 1024 || !['image/jpeg', 'image/png'].includes(file.type)) {
        const message = t('Choose a JPEG or PNG no larger than 5 MB.', 'اختر صورة JPEG أو PNG لا تتجاوز 5 ميجابايت.');
        input.setCustomValidity(message); input.reportValidity(); name.textContent = message; clear.hidden = false; return;
      }
      objectURL = URL.createObjectURL(file); preview.src = objectURL; preview.hidden = false;
      clear.hidden = false; name.textContent = file.name;
    });
    clear.addEventListener('click', () => { input.value = ''; reset(); input.focus(); });
    preview.addEventListener('error', () => {
      preview.hidden = true;
      name.textContent = t('Preview unavailable. The server will check your image when you submit.', 'المعاينة غير متاحة. سيتحقق الموقع من الصورة عند الإرسال.');
    });
    window.addEventListener('pagehide', () => { if (objectURL) URL.revokeObjectURL(objectURL); });
  }
  if ('IntersectionObserver' in window && !window.matchMedia('(prefers-reduced-motion: reduce)').matches) {
    const observer = new IntersectionObserver(entries => entries.forEach(entry => {
      if (entry.isIntersecting) {
        entry.target.classList.remove('reveal-pending'); entry.target.classList.add('reveal-visible'); observer.unobserve(entry.target);
      }
    }), { threshold: 0.06 });
    document.querySelectorAll('[data-reveal]').forEach(element => { element.classList.add('reveal-pending'); observer.observe(element); });
  }
})();
