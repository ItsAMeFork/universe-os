// Makes scripts/assets/kern.png: the glowing core between the login screen and the desktop (12 Oct, Axel: "the
// login animation and the desktop must flow into each other"). The login screen ends on exactly this picture (the
// planet charges up and flashes into the core, explode.js CORE), swaybg shows it while the desktop loads, and the
// desktop starts from it (world.js: the core explodes, the Earth forms and the planets fly out). Logging out ends on
// it again. Keep the stops below the same as CORE in pakket/.../ui/explode.js.
//   node scripts/assets/maak-kern.mjs
import {writeFileSync} from 'node:fs';
import {dirname, join} from 'node:path';
import {fileURLToPath} from 'node:url';
import {deflateSync} from 'node:zlib';

const W = 1920, H = 1080, BG = [5, 8, 21];
// [offset, r, g, b, a] of a radial gradient with radius min(W,H)*0.55 around the centre
const CORE = [[0, 255, 247, 236, 1], [.1, 255, 214, 160, .95], [.3, 255, 138, 72, .5], [.62, 120, 84, 255, .16], [1, 60, 40, 160, 0]];
const R = Math.min(W, H) * .55;
const raw = Buffer.alloc((W * 3 + 1) * H);
for (let y = 0; y < H; y++) {
  raw[y * (W * 3 + 1)] = 0;
  for (let x = 0; x < W; x++) {
    const t = Math.min(1, Math.hypot(x + .5 - W / 2, y + .5 - H / 2) / R);
    let i = 0; while (i < CORE.length - 2 && t > CORE[i + 1][0]) i++;
    const [o0, r0, g0, b0, a0] = CORE[i], [o1, r1, g1, b1, a1] = CORE[i + 1], k = (t - o0) / (o1 - o0);
    const a = a0 + (a1 - a0) * k, col = [r0 + (r1 - r0) * k, g0 + (g1 - g0) * k, b0 + (b1 - b0) * k];
    const o = y * (W * 3 + 1) + 1 + x * 3;
    for (let c = 0; c < 3; c++) raw[o + c] = Math.round(col[c] * a + BG[c] * (1 - a));
  }
}
const table = [];
for (let n = 0; n < 256; n++) { let c = n; for (let k = 0; k < 8; k++) c = c & 1 ? 0xedb88320 ^ (c >>> 1) : c >>> 1; table[n] = c >>> 0; }
const crc = b => { let x = 0xffffffff; for (const v of b) x = table[(x ^ v) & 255] ^ (x >>> 8); return (x ^ 0xffffffff) >>> 0; };
const chunk = (type, data) => { const l = Buffer.alloc(4); l.writeUInt32BE(data.length); const td = Buffer.concat([Buffer.from(type), data]); const c = Buffer.alloc(4); c.writeUInt32BE(crc(td)); return Buffer.concat([l, td, c]); };
const ihdr = Buffer.alloc(13); ihdr.writeUInt32BE(W); ihdr.writeUInt32BE(H, 4); ihdr[8] = 8; ihdr[9] = 2;
const out = join(dirname(fileURLToPath(import.meta.url)), 'kern.png');
writeFileSync(out, Buffer.concat([Buffer.from([137, 80, 78, 71, 13, 10, 26, 10]), chunk('IHDR', ihdr), chunk('IDAT', deflateSync(raw, {level: 9})), chunk('IEND', Buffer.alloc(0))]));
console.log(out);
