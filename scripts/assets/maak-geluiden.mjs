// Makes the Universe OS system sounds: our own, synthesised (no recordings or sounds of other systems).
//   node scripts/assets/maak-geluiden.mjs  ->  pakket/universe-os/usr/share/sounds/universe/*.wav
// Style (Axel, 12 Oct): "not irritating but chill, like reggae space beats". One family: warm sub bass, offbeat
// chord stabs ("skank") with a dub echo, a soft one-drop kick and rim, spacey pads and bells with a wide reverb.
// Key A minor, 75 BPM. 48 kHz, 16 bit, stereo; peaks at -4 dB, the short UI sounds lower.
import {mkdirSync, writeFileSync} from 'node:fs';
import {dirname, join} from 'node:path';
import {fileURLToPath} from 'node:url';

const RATE = 48000, BPM = 75, BEAT = 60 / BPM;
const OUT = join(dirname(fileURLToPath(import.meta.url)), '../../pakket/universe-os/usr/share/sounds/universe');
const hz = n => 440 * Math.pow(2, (n - 69) / 12);
let seed = 12345; const rnd = () => (seed = (seed * 16807) % 2147483647) / 2147483647;

class Track {
  constructor(seconds) { this.n = Math.round(seconds * RATE); this.dry = new Float64Array(this.n); this.send = new Float64Array(this.n); this.L = new Float64Array(this.n); this.R = new Float64Array(this.n); }
  // add a mono voice: fn(t) -> sample, panned, with an echo/reverb send
  add(at, dur, fn, {gain = 1, pan = 0, send = .3} = {}) {
    const s0 = Math.round(at * RATE), len = Math.round(dur * RATE), l = Math.cos((pan + 1) * Math.PI / 4), r = Math.sin((pan + 1) * Math.PI / 4);
    for (let i = 0; i < len && s0 + i < this.n; i++) {
      if (s0 + i < 0) continue;
      const v = fn(i / RATE) * gain;
      this.L[s0 + i] += v * l * Math.SQRT2; this.R[s0 + i] += v * r * Math.SQRT2; this.send[s0 + i] += v * send;
    }
  }
}
const env = (t, a, d) => Math.min(1, t / a) * Math.exp(-Math.max(0, t - a) / d);
const lp = k => { let y = 0; return x => (y += k * (x - y)); }; // one-pole low pass

// ----- instruments -----
const bass = (note, dur, slideTo) => {
  const f0 = hz(note), f1 = slideTo ? hz(slideTo) : f0; let ph = 0; const filt = lp(.08);
  return t => { const f = f0 + (f1 - f0) * Math.min(1, t / dur); ph += 2 * Math.PI * f / RATE;
    const s = Math.sin(ph) + .25 * Math.sin(2 * ph) + .08 * Math.tanh(3 * Math.sin(ph));
    return filt(s) * 4 * env(t, .015, dur * .7) * (t < dur ? 1 : Math.exp(-(t - dur) / .05)); };
};
const skank = (notes, decay = .09) => { // short muted chord stab, the reggae offbeat
  const fs = notes.map(hz), filt = lp(.25);
  return t => { let s = 0; for (const f of fs) { const p = 2 * Math.PI * f * t; s += Math.sin(p) + .5 * Math.sin(3 * p) / 3 + .3 * Math.sin(2 * p); }
    return filt(s / fs.length) * env(t, .004, decay); };
};
const pad = (notes, dur) => { // detuned, softly filtered: space
  const fs = notes.flatMap(n => [hz(n) * .997, hz(n) * 1.003]), filt = lp(.05), ph = fs.map(() => rnd() * 6.28);
  return t => { let s = 0; fs.forEach((f, i) => { const x = (f * t + ph[i] / 6.28) % 1; s += (2 * x - 1) * .5 + Math.sin(2 * Math.PI * f * t + ph[i]) * .5; });
    const a = Math.min(1, t / (dur * .45)), r = t > dur * .7 ? Math.max(0, 1 - (t - dur * .7) / (dur * .3)) : 1;
    return filt(s / fs.length) * a * r * 1.6; };
};
const bell = (note, decay = 1.2) => {
  const f = hz(note);
  return t => (Math.sin(2 * Math.PI * f * t) + .35 * Math.sin(2 * Math.PI * f * 2.01 * t) * Math.exp(-t / .25) + .12 * Math.sin(2 * Math.PI * f * 3.98 * t) * Math.exp(-t / .08)) * env(t, .003, decay);
};
const kick = () => t => Math.sin(2 * Math.PI * (45 * t + 90 * (1 - Math.exp(-t / .03)) * .03)) * env(t, .002, .22) * 1.4;
const rim = () => { const filt = lp(.6); return t => (filt(rnd() * 2 - 1) * .6 + Math.sin(2 * Math.PI * 1700 * t) * .4) * env(t, .001, .035); };
const swish = (dur) => { const filt = lp(.15); return t => filt(rnd() * 2 - 1) * Math.sin(Math.PI * Math.min(1, t / dur)) * 1.2; };

// ----- mix: dub echo (ping-pong, 3/8 beat) and a small Schroeder reverb on the send, then normalise -----
function render(track, {echo = .42, wet = .35, peak = .63, fade = .25} = {}) {
  const n = track.n, L = Float64Array.from(track.L), R = Float64Array.from(track.R);
  // ping-pong dub echo
  const d = Math.round(BEAT * .75 * RATE); const eL = new Float64Array(n), eR = new Float64Array(n); const hl = lp(.35), hr = lp(.35);
  for (let i = 0; i < n; i++) {
    const inL = track.send[i] + (i >= d ? eR[i - d] * echo : 0), inR = (i >= d ? eL[i - d] * echo : 0);
    eL[i] = hl(inL); eR[i] = hr(inR);
  }
  // reverb
  const combs = [1557, 1617, 1491, 1422].map(len => ({len, buf: new Float64Array(len), i: 0}));
  const aps = [225, 556].map(len => ({len, buf: new Float64Array(len), i: 0}));
  for (let i = 0; i < n; i++) {
    let x = track.send[i] * .5, y = 0;
    for (const c of combs) { const o = c.buf[c.i]; c.buf[c.i] = x + o * .84; c.i = (c.i + 1) % c.len; y += o; }
    y /= combs.length;
    for (const a of aps) { const o = a.buf[a.i]; const v = -y + o; a.buf[a.i] = y + o * .5; a.i = (a.i + 1) % a.len; y = v; }
    L[i] += (eL[i] + y) * wet * 2; R[i] += (eR[i] + y * .9) * wet * 2;
  }
  const f = Math.round(fade * RATE); for (let i = 0; i < f; i++) { const k = i / f; L[n - 1 - i] *= k; R[n - 1 - i] *= k; }
  let top = 1e-9; for (let i = 0; i < n; i++) top = Math.max(top, Math.abs(L[i]), Math.abs(R[i]));
  const g = peak / top;
  const data = Buffer.alloc(n * 4);
  for (let i = 0; i < n; i++) { data.writeInt16LE(Math.round(Math.max(-1, Math.min(1, L[i] * g)) * 32767), i * 4); data.writeInt16LE(Math.round(Math.max(-1, Math.min(1, R[i] * g)) * 32767), i * 4 + 2); }
  const head = Buffer.alloc(44);
  head.write('RIFF', 0); head.writeUInt32LE(36 + data.length, 4); head.write('WAVE', 8); head.write('fmt ', 12);
  head.writeUInt32LE(16, 16); head.writeUInt16LE(1, 20); head.writeUInt16LE(2, 22); head.writeUInt32LE(RATE, 24);
  head.writeUInt32LE(RATE * 4, 28); head.writeUInt16LE(4, 32); head.writeUInt16LE(16, 34); head.write('data', 36); head.writeUInt32LE(data.length, 40);
  return Buffer.concat([head, data]);
}

const Am = [57, 60, 64], C = [60, 64, 67], G = [55, 59, 62], F = [53, 57, 60], Em = [52, 55, 59];
const sounds = {};

// Startup (login screen after the pc starts): two bars of one-drop reggae in space, the pad swells, bells rise.
{
  const t = new Track(BEAT * 8 + 3);
  t.add(0, BEAT * 8 + 1, pad([45, 57, 60, 64, 71], BEAT * 8 + 1), {gain: .35, send: .5});
  const bars = [[Am, 33], [F, 29], [C, 36], [G, 31]];
  bars.forEach(([chord, root], b) => {
    const at = b * BEAT * 2; // half a bar per chord: Am F C G
    t.add(at, BEAT * 1.6, bass(root, BEAT * 1.5), {gain: .55, send: .05});
    t.add(at + BEAT * .5, .3, skank(chord.map(x => x + 12)), {gain: .32, pan: -.3, send: .6});
    t.add(at + BEAT * 1.5, .3, skank(chord.map(x => x + 12)), {gain: .32, pan: .3, send: .6});
    if (b % 2 === 1) { t.add(at, .5, kick(), {gain: .45, send: .02}); t.add(at, .1, rim(), {gain: .2, pan: .2, send: .4}); } // one drop on 3
  });
  [[69, 0.0], [72, .55], [76, 1.1], [79, 2.2], [81, 3.3], [84, 4.4], [81, 5.4]].forEach(([n, at], i) => t.add(.3 + at, 2.4, bell(n, 1.6), {gain: .22, pan: i % 2 ? .45 : -.45, send: .7}));
  t.add(BEAT * 8, 2.6, bass(33, 2.2), {gain: .5, send: .1});
  t.add(BEAT * 8, 2.8, bell(69, 2.2), {gain: .22, send: .8});
  sounds.opstarten = render(t, {echo: .45, wet: .4, peak: .63, fade: .9});
}
// Login: a skank, a bass drop and rising bells: the planet bursts open.
{
  const t = new Track(3.4);
  t.add(0, 2.6, pad([57, 64, 69], 2.6), {gain: .25, send: .5});
  t.add(0, .9, bass(33, .8), {gain: .5, send: .05}); t.add(0, .5, kick(), {gain: .4, send: .02});
  t.add(BEAT * .5, .3, skank(Am.map(x => x + 12)), {gain: .3, pan: -.3, send: .7});
  [[69, .05], [72, .25], [76, .45], [81, .7]].forEach(([n, at], i) => t.add(at, 2, bell(n, 1.3), {gain: .25, pan: [-.4, .4, -.2, .2][i], send: .6}));
  sounds.inloggen = render(t, {fade: .5});
}
// Logout: bells fall back, the bass slides down, the echo carries it away.
{
  const t = new Track(3);
  t.add(0, 2.2, pad([55, 60, 64], 2.2), {gain: .22, send: .5});
  [[81, 0], [76, .2], [72, .4], [69, .65]].forEach(([n, at], i) => t.add(at, 1.8, bell(n, 1.1), {gain: .24, pan: [.3, -.3, .2, -.2][i], send: .6}));
  t.add(.6, 1.3, bass(36, 1.1, 33), {gain: .45, send: .1});
  t.add(BEAT * .5, .3, skank(F.map(x => x + 12)), {gain: .25, pan: .3, send: .7});
  sounds.afmelden = render(t, {fade: .6});
}
// Shutdown: slower and deeper, a long bass slide into the low A and a fading pad.
{
  const t = new Track(3.8);
  t.add(0, 3.2, pad([53, 57, 60, 64], 3.2), {gain: .26, send: .5});
  [[84, 0], [79, .3], [76, .6], [72, .95], [69, 1.35]].forEach(([n, at], i) => t.add(at, 2, bell(n, 1.4), {gain: .22, pan: i % 2 ? .35 : -.35, send: .6}));
  t.add(.9, 2.4, bass(40, 2, 33), {gain: .5, send: .1}); t.add(.9, .5, kick(), {gain: .35});
  sounds.afsluiten = render(t, {fade: 1});
}
// Short UI sounds (lower): notification, error, device in/out, lock/unlock, trash, screenshot, volume, battery.
const short = (fill, secs, peak = .45) => { const t = new Track(secs); fill(t); return render(t, {echo: .3, wet: .25, peak, fade: .15}); };
sounds.melding = short(t => { t.add(0, .8, bell(81, .45), {gain: .3, pan: -.2, send: .5}); t.add(BEAT * .25, .8, bell(76, .55), {gain: .28, pan: .2, send: .5}); }, 1.4);
sounds.fout = short(t => { t.add(0, .7, bell(64, .4), {gain: .3, send: .3}); t.add(.12, .8, bell(63, .5), {gain: .3, send: .3}); t.add(0, .5, bass(28, .35), {gain: .35, send: 0}); }, 1.2);
sounds['apparaat-in'] = short(t => { t.add(0, .6, bell(69, .3), {gain: .3, send: .4}); t.add(.1, .7, bell(76, .45), {gain: .3, send: .4}); t.add(0, .3, skank(Am.map(x => x + 12)), {gain: .2, send: .5}); }, 1.1);
sounds['apparaat-uit'] = short(t => { t.add(0, .6, bell(76, .3), {gain: .3, send: .4}); t.add(.1, .7, bell(69, .45), {gain: .3, send: .4}); }, 1.1);
sounds.vergrendelen = short(t => { t.add(0, .9, pad([57, 60, 64], .8), {gain: .3, send: .4}); t.add(0, .5, bass(33, .3), {gain: .35}); t.add(.05, .5, bell(69, .3), {gain: .2, send: .3}); }, 1.1);
sounds.ontgrendelen = short(t => { t.add(0, .9, bell(72, .4), {gain: .25, pan: -.3, send: .5}); t.add(.1, .9, bell(76, .5), {gain: .25, pan: .3, send: .5}); t.add(.2, .9, bell(81, .6), {gain: .22, send: .6}); }, 1.4);
sounds.prullenbak = short(t => { t.add(0, .35, swish(.35), {gain: .25, send: .3}); t.add(.18, .5, bell(57, .25), {gain: .25, send: .3}); }, .8, .35);
sounds.schermafbeelding = short(t => { t.add(0, .06, rim(), {gain: .5, send: .2}); t.add(.08, .06, rim(), {gain: .35, send: .2}); t.add(0, .5, bell(88, .2), {gain: .12, send: .5}); }, .6, .35);
sounds.volume = short(t => { t.add(0, .25, bell(76, .08), {gain: .3, send: .15}); }, .3, .3);
sounds.waarschuwing = short(t => { [[76, 0], [72, .2], [69, .4]].forEach(([n, at]) => t.add(at, .8, bell(n, .5), {gain: .26, send: .5})); }, 1.6);
// Launch countdown after an update (last 10 s): a soft rim + low bell per second, then the launch: a rising swell.
sounds.aftellen = short(t => { t.add(0, .08, rim(), {gain: .35, send: .4}); t.add(0, .6, bell(57, .25), {gain: .25, send: .4}); t.add(0, .4, bass(33, .2), {gain: .25}); }, .7, .38);
{
  const t = new Track(3.2);
  t.add(0, 2.4, swish(2.4), {gain: .3, send: .6});
  t.add(0, 2.6, pad([57, 64, 69, 76], 2.6), {gain: .3, send: .6});
  t.add(0, 2.2, bass(28, 2, 40), {gain: .45, send: .1}); t.add(0, .5, kick(), {gain: .4});
  [[69, .4], [76, .8], [81, 1.2], [88, 1.6]].forEach(([n, at], i) => t.add(at, 1.5, bell(n, 1), {gain: .2, pan: i % 2 ? .4 : -.4, send: .7}));
  sounds.lancering = render(t, {fade: .8});
}

mkdirSync(OUT, {recursive: true});
for (const [name, wav] of Object.entries(sounds)) {
  writeFileSync(join(OUT, name + '.wav'), wav);
  console.log(name.padEnd(17), (wav.length / RATE / 4).toFixed(2) + ' s', (wav.length / 1024).toFixed(0) + ' KB');
}
