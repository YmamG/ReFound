/* Optional enhancement: server ordering and all reports remain available without JS. */
(() => {
  const options = document.querySelector('.match-options');
  const open = document.querySelector('input[name="options_open"]');
  if (options && open) options.addEventListener('toggle', () => { open.value = options.open ? '1' : '0'; });
  const deck = document.querySelector('.match-deck');
  const controls = document.querySelector('.deck-controls');
  if (!deck || !controls) return;
  const cards = Array.from(deck.children);
  const previous = controls.querySelector('[data-previous]');
  const next = controls.querySelector('[data-next]');
  const counter = controls.querySelector('[data-card-index]');
  let index = 0;
  const show = (value, focus = false) => {
    index = Math.max(0, Math.min(cards.length - 1, value));
    cards.forEach((card, position) => {
      card.hidden = position !== index;
      card.classList.toggle('is-entering', focus && position === index);
    });
    previous.disabled = index === 0;
    next.disabled = index === cards.length - 1;
    counter.textContent = String(index + 1);
    if (focus) cards[index].querySelector('h3').focus({preventScroll:true});
  };
  controls.hidden = cards.length < 2;
  deck.classList.add('deck-enhanced');
  previous.addEventListener('click', () => show(index - 1, true));
  next.addEventListener('click', () => show(index + 1, true));
  deck.addEventListener('keydown', event => {
    if (event.target.closest('input,textarea,select,a,button')) return;
    const rtl = document.documentElement.dir === 'rtl';
    if (event.key === 'ArrowRight' || event.key === 'ArrowLeft') {
      event.preventDefault();
      show(index + ((event.key === 'ArrowRight') !== rtl ? 1 : -1), true);
    }
  });
  show(0);
})();
