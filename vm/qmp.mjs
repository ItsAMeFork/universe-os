// Bestuurt een QEMU-VM via het lokale QMP-beheerkanaal (alleen 127.0.0.1).
//   node qmp.mjs <poort> scherm <bestand.png>          schermafbeelding
//   node qmp.mjs <poort> typ "tekst"                    tekst typen (US-toetsenbord)
//   node qmp.mjs <poort> toets ctrl-alt-f2              toetscombinatie
//   node qmp.mjs <poort> klik <x> <y> [links|rechts]    muisklik op schermcoördinaat (usb-tablet nodig)
//   node qmp.mjs <poort> status                         draait de VM?
//   node qmp.mjs <poort> uit                            VM netjes uitzetten (ACPI)
import {createConnection} from 'node:net';
import {resolve} from 'node:path';

const [port, action, ...rest] = process.argv.slice(2);
const KEYS = {' ': 'spc', '\n': 'ret', '\t': 'tab', '-': 'minus', '=': 'equal', '[': 'bracket_left', ']': 'bracket_right',
  ';': 'semicolon', "'": 'apostrophe', '`': 'grave_accent', '\\': 'backslash', ',': 'comma', '.': 'dot', '/': 'slash'};
const SHIFTED = {'!': '1', '@': '2', '#': '3', '$': '4', '%': '5', '^': '6', '&': '7', '*': '8', '(': '9', ')': '0', '_': '-',
  '+': '=', '{': '[', '}': ']', ':': ';', '"': "'", '~': '`', '|': '\\', '<': ',', '>': '.', '?': '/'};
const NAMES = {ctrl: 'ctrl', alt: 'alt', shift: 'shift', super: 'meta_l', win: 'meta_l', enter: 'ret', esc: 'esc', tab: 'tab',
  del: 'delete', backspace: 'backspace', up: 'up', down: 'down', left: 'left', right: 'right', space: 'spc', print: 'print'};

function keyFor(ch) {
  if (/[a-z0-9]/.test(ch)) return {keys: [ch]};
  if (/[A-Z]/.test(ch)) return {keys: ['shift', ch.toLowerCase()]};
  if (KEYS[ch]) return {keys: [KEYS[ch]]};
  if (SHIFTED[ch]) return {keys: ['shift', SHIFTED[ch].match(/[0-9]/) ? SHIFTED[ch] : KEYS[SHIFTED[ch]]]};
  throw new Error('Teken niet ondersteund: ' + ch);
}
const sendkey = keys => ({execute: 'send-key', arguments: {keys: keys.map(k => ({type: 'qcode', data: k})), 'hold-time': 40}});

function session(commands) {
  return new Promise((done, fail) => {
    const sock = createConnection({host: '127.0.0.1', port: Number(port)});
    let buf = '', queue = [{execute: 'qmp_capabilities'}, ...commands], results = [];
    const next = () => { const c = queue.shift(); if (!c) { sock.destroy(); done(results); return; } if (c.wait) { setTimeout(next, c.wait); return; } sock.write(JSON.stringify(c) + '\n'); };
    sock.on('data', d => {
      buf += d; let i;
      while ((i = buf.indexOf('\n')) >= 0) {
        const line = buf.slice(0, i); buf = buf.slice(i + 1); if (!line.trim()) continue;
        const msg = JSON.parse(line);
        if (msg.QMP) { next(); continue; }
        if (msg.event) continue;
        if (msg.error) { sock.destroy(); fail(new Error(msg.error.desc)); return; }
        results.push(msg.return); next();
      }
    });
    sock.on('error', fail);
  });
}

const cmds = [];
if (action === 'scherm') cmds.push({execute: 'screendump', arguments: {filename: resolve(rest[0]), format: 'png'}});
else if (action === 'typ') for (const ch of rest.join(' ')) { cmds.push(sendkey(keyFor(ch).keys)); cmds.push({wait: 25}); }
else if (action === 'toets') cmds.push(sendkey(rest[0].split('-').map(k => NAMES[k] || k)));
else if (action === 'klik') {
  // Absolute coordinates for usb-tablet are 0..32767; the caller gives the screen size via env SCREEN=1280x800.
  const [w, h] = (process.env.SCREEN || '1280x800').split('x').map(Number);
  const x = Math.round(Number(rest[0]) / w * 32767), y = Math.round(Number(rest[1]) / h * 32767), btn = rest[2] === 'rechts' ? 'right' : 'left';
  const ev = (down) => ({execute: 'input-send-event', arguments: {events: [{type: 'abs', data: {axis: 'x', value: x}}, {type: 'abs', data: {axis: 'y', value: y}}, {type: 'btn', data: {down, button: btn}}]}});
  cmds.push(ev(true), {wait: 60}, ev(false));
} else if (action === 'status') cmds.push({execute: 'query-status'});
else if (action === 'uit') cmds.push({execute: 'system_powerdown'});
else { console.error('Gebruik: node qmp.mjs <poort> scherm|typ|toets|klik|status|uit ...'); process.exit(1); }

session(cmds).then(r => { if (action === 'status') console.log(r[r.length - 1]?.status); }).catch(e => { console.error('QMP-fout: ' + e.message); process.exit(2); });
