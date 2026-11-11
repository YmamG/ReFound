(() => {
  'use strict';
  const ar = document.documentElement.lang.startsWith('ar');
  const t = (english, arabic) => ar ? arabic : english;
  document.documentElement.classList.add('js');
  const menu = document.querySelector('.menu-toggle');
  const nav = document.getElementById('main-nav');
  const header = document.querySelector('.site-header');
  if (menu && nav) {
    const mobileNav = window.matchMedia('(max-width: 800px)');
    menu.hidden = false;
    const setMenu = open => {
      nav.classList.toggle('is-open', open);
      nav.inert = mobileNav.matches && !open;
      menu.setAttribute('aria-expanded', String(open));
      menu.setAttribute('aria-label', open ? t('Close navigation', 'إغلاق القائمة') : t('Open navigation', 'فتح القائمة'));
    };
    menu.addEventListener('click', () => setMenu(menu.getAttribute('aria-expanded') !== 'true'));
    document.addEventListener('keydown', event => {
      if (event.key === 'Escape' && menu.getAttribute('aria-expanded') === 'true') { setMenu(false); menu.focus(); }
    });
    document.addEventListener('pointerdown', event => {
      if (header && !header.contains(event.target)) setMenu(false);
    });
    nav.querySelectorAll('a').forEach(link => link.addEventListener('click', () => setMenu(false)));
    mobileNav.addEventListener('change', () => setMenu(false));
    setMenu(false);
  }
  document.querySelectorAll('[data-dismiss]').forEach(button => button.addEventListener('click', () => button.closest('.notice').remove()));
  const summary = document.querySelector('.error-summary');
  if (summary) summary.focus();
  const idleButtons = new WeakMap();
  const liveStatus = document.createElement('span');
  liveStatus.className = 'sr-only';
  liveStatus.setAttribute('role', 'status');
  document.body.append(liveStatus);
  document.querySelectorAll('form[data-busy]').forEach(form => {
    form.addEventListener('submit', () => {
      const loading = form.method.toLowerCase() === 'get' ? t('Updating…', 'جارٍ التحديث…') : t('Sending…', 'جارٍ الإرسال…');
      liveStatus.textContent = loading;
      form.querySelectorAll('button[type="submit"]').forEach(button => {
        idleButtons.set(button, Array.from(button.childNodes, node => node.cloneNode(true)));
        const spinner = document.createElement('span');
        spinner.className = 'button-spinner'; spinner.setAttribute('aria-hidden', 'true');
        button.replaceChildren(spinner, document.createTextNode(loading));
        button.disabled = true; button.setAttribute('aria-busy', 'true');
      });
    });
  });
  window.addEventListener('pageshow', () => {
    liveStatus.textContent = '';
    document.querySelectorAll('button[aria-busy]').forEach(button => {
      const original = idleButtons.get(button);
      if (original) button.replaceChildren(...original);
      button.disabled = false; button.removeAttribute('aria-busy');
    });
  });
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
      if (!entry.isIntersecting) return;
      if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) { observer.unobserve(entry.target); return; }
      const elements = entry.target.querySelectorAll(':scope > .section-heading, :scope > .steps-grid > .step-card, :scope > .report-grid > .report-card, :scope > .owner-callout');
      elements.forEach((element, index) => {
        element.animate([
          { opacity: .55, transform: 'translateY(14px)' },
          { opacity: 1, transform: 'translateY(0)' }
        ], { duration: 460, delay: Math.min(index * 65, 195), easing: 'cubic-bezier(.2,.75,.25,1)', fill: 'backwards' });
      });
      observer.unobserve(entry.target);
    }), { threshold: 0.08 });
    document.querySelectorAll('[data-reveal]').forEach(element => observer.observe(element));
  }
})();
