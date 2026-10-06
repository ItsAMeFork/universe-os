import assert from 'node:assert/strict';
import {latestValue} from '../../pakket/universe-os/usr/share/universe-os/ui/requests.js';
const sleep=ms=>new Promise(r=>setTimeout(r,ms));
let release;const values=[],errors=[];
const setter=latestValue(async value=>{values.push(value);if(value===3)await new Promise(r=>release=r);if(value===6)throw Error('test');},e=>errors.push(e.message),5);
setter(1);setter(2);setter(3);await sleep(20);
assert.deepEqual(values,[3]);setter(4);setter(5);await sleep(20);assert.deepEqual(values,[3]);
release();await sleep(20);assert.deepEqual(values,[3,5]);setter(6);await sleep(20);assert.deepEqual(errors,['test']);setter(7);await sleep(20);assert.deepEqual(values,[3,5,6,7]);
console.log('PASS: latest slider value, one request in flight, error recovery');
