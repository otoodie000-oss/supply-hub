// Fail the build if any two vocab entries compare equal under Scratch's Cast.compare
// (case-insensitive, numeric when both parse as numbers).  Checked against both the
// vanilla scratch-vm and the TurboWarp fork's Cast implementation.
// usage: node check_vocab.js ../vocab.json [path/to/turbowarp/scratch-vm]
const path = require('path');
const fs = require('fs');
const vocabPath = process.argv[2] || path.join(__dirname, '..', 'vocab.json');
const twRoot = process.argv[3] || '/home/user/tw/scratch-vm';
const v = JSON.parse(fs.readFileSync(vocabPath, 'utf8'));
const entries = v.specials.concat(v.pieces);
const impls = [['scratch-vm', path.join(__dirname, 'node_modules/scratch-vm/src/util/cast.js')]];
if (fs.existsSync(path.join(twRoot, 'src/util/cast.js'))) impls.push(['turbowarp', path.join(twRoot, 'src/util/cast.js')]);
let bad = 0;
for (const [name, p] of impls) {
    const Cast = require(p);
    let collisions = 0;
    for (let i = 0; i < entries.length; i++) {
        if (entries[i] === '' || (entries[i] !== ' ' && entries[i].trim() === '')) {
            console.log(`[${name}] empty/whitespace entry at ${i}: ${JSON.stringify(entries[i])}`); collisions++;
        }
        for (let j = i + 1; j < entries.length; j++) {
            if (Cast.compare(entries[i], entries[j]) === 0) {
                console.log(`[${name}] COLLISION ${i}:${JSON.stringify(entries[i])} == ${j}:${JSON.stringify(entries[j])}`);
                collisions++;
            }
        }
    }
    // Digits: every piece containing a digit must be exactly one digit.
    entries.forEach((e, i) => { if (/[0-9]/.test(e) && e.length !== 1) { console.log(`[${name}] digit piece ${i} ${e}`); collisions++; } });
    console.log(`[${name}] ${entries.length} entries, ${entries.length * (entries.length - 1) / 2} pairs checked, collisions: ${collisions}`);
    bad += collisions;
}
if (bad) { console.error('VOCAB CHECK FAILED'); process.exit(1); }
console.log('VOCAB CHECK OK');
