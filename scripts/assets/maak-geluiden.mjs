// Makes the Universe OS system sounds (our own, synthesised: no recordings or sounds of other systems).
//   node scripts/assets/maak-geluiden.mjs  ->  pakket/universe-os/usr/share/sounds/universe/*.wav
// Space-like bells over a soft pad, with a short echo: login rises, logout falls, shutdown falls deeper and ends on
// a low tone, a notification is a short double chime. 48 kHz, 16 bit, mono; peaks at -3 dB.
import {mkdirSync, writeFileSync} from 'node:fs';
import {dirname, join} from 'node:path';
import {fileURLToPath} from 'node:url';

const RATE = 48000;
const OUT = join(dirname(fileURLToPath(import.meta.url)), '../../pakket/universe-os/usr/share/sounds/universe');
const hz = n => 440 * Math.pow(2, (n - 69) / 12); // MIDI note -> frequency

function render(seconds, voices) {
  const n = Math.round(seconds * RATE), buf = new Float64Array(n);
  for (const v of voices) {
    const start = Math.round(v.at * RATE), f = hz(v.note);
    for (let i = 0; start + i < n; i++) {
      const t = i / RATE;
      const env = v.pad
        ? Math.min(1, t / v.attack) * Math.exp(-Math.max(0, t - v.attack) / v.decay)
        : Math.min(1, t / .004) * Math.exp(-t / v.decay);
      if (env < 1e-4 && t > v.attack + .01) break;
      let s;
      if (v.pad) s = Math.sin(2 * Math.PI * f * t) + .35 * Math.sin(2 * Math.PI * f * 2.003 * t) + .15 * Math.sin(2 * Math.PI * f * .5 * t);
      else s = Math.sin(2 * Math.PI * f * t) + .45 * Math.sin(2 * Math.PI * f * 2.76 * t) * Math.exp(-t / .12) + .2 * Math.sin(2 * Math.PI * f * 5.4 * t) * Math.exp(-t / .05);
      buf[start + i] += s * env * v.gain;
    }
  }
  // echo: a few taps that fade, for space
  const out = Float64Array.from(buf);
  for (const [delay, gain] of [[.11, .28], [.23, .18], [.37, .1]]) {
    const d = Math.round(delay * RATE);
    for (let i = d; i < n; i++) out[i] += buf[i - d] * gain;
  }
  // fade the very end so nothing clicks
  const fade = Math.round(.08 * RATE);
  for (let i = 0; i < fade; i++) out[n - 1 - i] *= i / fade;
  const peak = out.reduce((m, v) => Math.max(m, Math.abs(v)), 0) || 1, scale = .708 / peak;
  const data = Buffer.alloc(n * 2);
  for (let i = 0; i < n; i++) data.writeInt16LE(Math.round(Math.max(-1, Math.min(1, out[i] * scale)) * 32767), i * 2);
  const head = Buffer.alloc(44);
  head.write('RIFF', 0); head.writeUInt32LE(36 + data.length, 4); head.write('WAVE', 8); head.write('fmt ', 12);
  head.writeUInt32LE(16, 16); head.writeUInt16LE(1, 20); head.writeUInt16LE(1, 22); head.writeUInt32LE(RATE, 24);
  head.writeUInt32LE(RATE * 2, 28); head.writeUInt16LE(2, 32); head.writeUInt16LE(16, 34); head.write('data', 36);
  head.writeUInt32LE(data.length, 40);
  return Buffer.concat([head, data]);
}
const bell = (note, at, gain = .5, decay = .9) => ({note, at, gain, decay});
const pad = (note, at, gain = .18, attack = .5, decay = 1.2) => ({note, at, gain, attack, decay, pad: true});

const sounds = {
  // C major add 9, rising: a planet coming to life
  inloggen: render(3.0, [pad(48, 0, .2, .7, 1.6), pad(55, 0, .14, .8, 1.6), pad(64, .1, .1, .9, 1.4),
    bell(72, .05), bell(76, .2), bell(79, .35), bell(74, .5, .4), bell(84, .7, .45, 1.3)]),
  // the same colours, falling: everything goes back into the Earth
  afmelden: render(2.2, [pad(52, 0, .16, .3, .9), pad(48, .1, .14, .4, 1),
    bell(79, 0, .45), bell(76, .15, .45), bell(72, .3, .45), bell(67, .45, .5, 1.1)]),
  // deeper and slower, ends on a low tone that fades
  afsluiten: render(2.8, [pad(43, 0, .2, .4, 1.4), pad(36, .3, .22, .6, 1.6),
    bell(76, 0, .4), bell(72, .2, .42), bell(67, .4, .45), bell(60, .65, .5, 1.4)]),
  // a short double chime
  melding: render(.75, [bell(88, 0, .45, .35), bell(83, .09, .4, .45)]),
};
mkdirSync(OUT, {recursive: true});
for (const [name, wav] of Object.entries(sounds)) {
  writeFileSync(join(OUT, name + '.wav'), wav);
  console.log(name + '.wav', (wav.length / 1024).toFixed(0), 'KB');
}
