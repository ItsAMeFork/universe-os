// 0.3.4: rekenwerk van de profielfoto-editor (ui/profielfoto-ui.js). Run: node docs/tests/profielfoto-ui.mjs
import assert from 'node:assert/strict';
import {beginBeeld,verschuif,zoom,uitsnede} from '../../pakket/universe-os/usr/share/universe-os/ui/profielfoto-ui.js';

// Automatic: the middle, as big as possible (the short side).
let s=beginBeeld(3000,2000);
assert.deepEqual(uitsnede(s),{x:500,y:0,size:2000});
s=beginBeeld(640,960);
assert.deepEqual(uitsnede(s),{x:0,y:160,size:640});

// Zoom in 2x: half the side, still around the middle; never below 1x or above 8x.
s=zoom(beginBeeld(3000,2000),2);
assert.deepEqual(uitsnede(s),{x:1000,y:500,size:1000});
assert.equal(uitsnede(zoom(s,0.3)).size,2000);
assert.equal(uitsnede(zoom(s,50)).size,250);

// Dragging right by the whole circle (260 px on screen) moves the photo right: the crop goes left by one side.
s=verschuif(zoom(beginBeeld(3000,2000),2),260,0,260);
assert.deepEqual(uitsnede(s),{x:0,y:500,size:1000});
// The crop never leaves the photo, however far you drag.
s=verschuif(s,99999,-99999,260);
assert.deepEqual(uitsnede(s),{x:0,y:1000,size:1000});
s=verschuif(beginBeeld(3000,2000),0,500,260);
assert.deepEqual(uitsnede(s),{x:500,y:0,size:2000},'at 1x a landscape photo cannot move up/down');
// Zooming out after dragging pulls the crop back inside.
s=zoom(verschuif(zoom(beginBeeld(3000,2000),4),-99999,-99999,260),1);
assert.deepEqual(uitsnede(s),{x:1000,y:0,size:2000});
console.log('PASS profielfoto-editor: midden, zoom 1-8x, slepen, altijd binnen de foto');
