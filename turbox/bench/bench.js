const L = require('../harness/twlib.js');
L.silence();
(async () => {
    const H = await L.makeVM(process.argv[2]);
    const vm = H.vm;
    const out = {loadMs: +H.loadMs.toFixed(1)};
    const run = async (msg, reps) => {
        const res = [];
        for (let k = 0; k < reps; k++) {
            const d0 = Number(L.getVar(vm, 'done'));
            vm.runtime.startHats('event_whenbroadcastreceived', {BROADCAST_OPTION: msg});
            const f0 = H.frames.length;
            await L.frames(H, () => Number(L.getVar(vm, 'done')) > d0, msg);
            const fr = H.frames.slice(f0);
            res.push({frames: fr.length, work: +fr.reduce((a, f) => a + f.work, 0).toFixed(2), max: +Math.max(...fr.map(f => f.work)).toFixed(2)});
        }
        return res;
    };
    out.int = await run('b_int', 6);
    out.str = await run('b_str', 6);
    out.bs = await run('b_bs', 4);
    out.bs_hits = L.getVar(vm, 'res');
    out.chunk = await run('b_chunk', 2);
    out.Y0 = vm.runtime.getTargetForStage().lookupVariableByNameAndType('Y', 'list').value.slice(0, 3);
    console.log(JSON.stringify(out));
})();
