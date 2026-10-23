// Privacy Ghost mode. Off until the switch is turned on. The switch is larger than the others on purpose.
const STYLE = `
.ghost-hero{border-color:#85ffe366;background:#102033;padding:28px}
.ghost-hero .switch{width:120px;height:68px}
.ghost-hero .switch-track::after{width:52px;height:52px;top:6px;left:6px}
.ghost-hero .switch input:checked+.switch-track::after{transform:translateX(52px)}
.ghost-hero .switch-title{font-size:2em}
.ghost-hero .switch-state{font-size:1.35em}
`;
let styled = false;

function ensureStyle() {
 if (styled) return;
 styled = true;
 const el = document.createElement('style');
 el.textContent = STYLE;
 document.head.append(el);
}

function paint(box, state, note, next) {
 const on = !!next?.aan;
 box.checked = on;
 state.textContent = next?.tekst || (on ? 'Aan' : 'Uit');
 state.className = 'switch-state ' + (on ? 'aan' : 'uit');
 note.textContent = next?.uitleg || '';
}

export function mountGhost(root, h, status, save) {
 ensureStyle();
 const box = h('input', {type: 'checkbox', 'aria-label': 'Ghost-modus'});
 const state = h('span', {class: 'switch-state uit'}, 'Uit');
 const note = h('p', {class: 'muted'}, '');
 const message = h('p', {class: 'message', role: 'status'});
 paint(box, state, note, status || {aan: false, tekst: 'Uit'});
 box.addEventListener('change', async () => {
  box.disabled = true;
  message.className = 'message';
  message.textContent = 'Bezig…';
  try {
   const next = await save(box.checked);
   paint(box, state, note, next);
   message.textContent = next?.aan ? 'Ghost-modus staat aan.' : 'Ghost-modus staat uit.';
  } catch (error) {
   box.checked = !box.checked;
   message.className = 'message error';
   message.textContent = error.message || 'Mislukt.';
  } finally {
   box.disabled = false;
  }
 });
 root.append(h('section', {class: 'card ghost-hero'},
  h('h3', {}, 'Ghost-modus'),
  h('label', {class: 'switch-row'},
   h('span', {class: 'switch'}, box, h('span', {class: 'switch-track', 'aria-hidden': 'true'})),
   h('span', {class: 'switch-copy'},
    h('span', {class: 'switch-title'}, 'Ghost-modus'),
    state)),
  note,
  message));
}
