// 0.3.3: the clock on the Earth of the login screen (ui/klok.js). Run: node docs/tests/klok.mjs
import assert from 'node:assert/strict';
import {klokTekst,startKlok} from '../../pakket/universe-os/usr/share/universe-os/ui/klok.js';

assert.deepEqual(klokTekst(new Date(2026, 9, 28, 19, 4)), {tijd: '19:04', datum: 'woensdag 28 oktober'});
assert.deepEqual(klokTekst(new Date(2026, 0, 1, 0, 0)), {tijd: '00:00', datum: 'donderdag 1 januari'});
assert.deepEqual(klokTekst(new Date(2026, 11, 27, 9, 59)), {tijd: '09:59', datum: 'zondag 27 december'});

// Writes only when the text changes; checks every second (after a sleep the time is right within 1 s).
let now = new Date(2026, 9, 28, 19, 4, 58), timers = [];
const tijd = {textContent: ''}, datum = {textContent: ''};
let writes = 0;
for (const e of [tijd, datum]) {
  let v = '';
  Object.defineProperty(e, 'textContent', {get: () => v, set: x => { v = x; writes++; }});
}
const stop = startKlok(tijd, datum, {now: () => now, every: (f, ms) => { timers.push([f, ms]); return 1; }, clear() {}});
assert.equal(tijd.textContent, '19:04');
assert.equal(datum.textContent, 'woensdag 28 oktober');
assert.equal(timers.length, 1);
assert.equal(timers[0][1], 1000);
const before = writes;
timers[0][0]();
assert.equal(writes, before, 'same minute: nothing written');
now = new Date(2026, 9, 28, 19, 5, 0);
timers[0][0]();
assert.equal(tijd.textContent, '19:05');
assert.equal(writes, before + 1, 'only the time changed');
now = new Date(2026, 9, 29, 7, 30, 0); // woke from sleep the next morning
timers[0][0]();
assert.equal(tijd.textContent, '07:30');
assert.equal(datum.textContent, 'donderdag 29 oktober');
assert.equal(typeof stop, 'function');
// Missing elements (page script ran without the markup) never throw.
startKlok(null, null, {now: () => now, every: () => 0, clear() {}});
console.log('PASS klok: tijd/datum in het Nederlands, schrijft alleen bij verandering, klopt na slaapstand');
