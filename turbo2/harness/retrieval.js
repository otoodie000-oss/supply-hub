// Retrieval parity: run the Scratch bm25 block on queries via a test broadcast.
const lib = require('./lib.js');
const fs = require('fs');
lib.silence();
(async () => {
    const spec = JSON.parse(fs.readFileSync(process.argv[2]));
    const {vm} = await lib.makeVM(spec.sb3);
    lib.broadcast(vm, 'init_bm');
    await lib.runUntilIdle(vm);
    const tin = lib.list(vm, 'rq_in'); tin.length = 0; spec.queries.forEach(q => tin.push(q));
    lib.broadcast(vm, 'rq_run');
    await lib.runUntilIdle(vm);
    const out = lib.list(vm, 'rq_out').map(String);
    const picked = out.map(s => s === '' ? [] : s.split(' ').map(Number));
    fs.writeFileSync(process.argv[3], JSON.stringify({picked}));
    console.log('queries', picked.length);
})();
