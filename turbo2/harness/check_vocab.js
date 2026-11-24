// Fails (exit 1) if any two vocab entries compare equal under Scratch's Cast.compare
// (TurboWarp fork), or if any piece is empty, whitespace-only other than " ", or
// contains a digit while being longer than one character.
const path = require('path');
const fs = require('fs');
const TW = process.env.TW_VM || '/home/user/tw/scratch-vm';
const Cast = require(path.join(TW, 'src/util/cast.js'));
const v = JSON.parse(fs.readFileSync(process.argv[2] || path.join(__dirname, '../tok/vocab.json')));
const entries = v.specials.concat(v.pieces);
let bad = 0;
for (const p of v.pieces) {
    if (p === '' || (p.trim() === '' && p !== ' ') || (/[0-9]/.test(p) && p.length > 1)) {
        console.log('BAD PIECE', JSON.stringify(p)); bad++;
    }
}
let pairs = 0;
for (let i = 0; i < entries.length; i++) {
    for (let j = i + 1; j < entries.length; j++) {
        pairs++;
        if (Cast.compare(entries[i], entries[j]) === 0) {
            if (bad < 20) console.log('COLLISION', i, JSON.stringify(entries[i]), j, JSON.stringify(entries[j]));
            bad++;
        }
    }
}
const msg = `entries=${entries.length} pairs=${pairs} problems=${bad}`;
console.log(msg);
fs.writeFileSync(path.join(__dirname, '../results/vocab_check.txt'), msg + '\n');
process.exit(bad ? 1 : 0);
