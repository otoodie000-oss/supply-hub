// Runs every helper test case in Scratch (TurboWarp) and compares with the Python twin.
const lib = require('./lib.js');
const fs = require('fs');
lib.silence();
(async () => {
    const cases = JSON.parse(fs.readFileSync(process.argv[3]));
    const {vm} = await lib.makeVM(process.argv[2]);
    const fill = (n, arr) => { const l = lib.list(vm, n); l.length = 0; arr.forEach(x => l.push(x)); };
    fill('tin', cases.map(c => c.call)); fill('tnow', cases.map(c => c.cfg_now)); fill('tseed', cases.map(c => c.seed));
    const t0 = Date.now();
    lib.broadcast(vm, 'tooltest');
    await lib.runUntilIdle(vm);
    const out = lib.list(vm, 'tout');
    const per = {};
    const bad = [];
    cases.forEach((c, i) => {
        const got = String(out[i]);
        const p = per[c.tool] || (per[c.tool] = {n: 0, ok: 0});
        p.n++;
        if (got === c.expect) p.ok++; else bad.push({call: c.call, now: c.cfg_now, seed: c.seed, expect: c.expect, got});
    });
    const res = {total: cases.length, passed: cases.length - bad.length, ms: Date.now() - t0, per, mismatches: bad};
    fs.writeFileSync(process.argv[4], JSON.stringify(res, null, 1));
    console.log('passed', res.passed, '/', res.total, 'in', res.ms, 'ms');
    bad.slice(0, 25).forEach(b => console.log('MISMATCH', JSON.stringify(b)));
})();
