// Speed benchmark: ms/token for prefill (no LM head) and decode (with LM head) at several
// context positions, plus load time.  Usage: node bench.js model.sb3
const lib = require('./lib.js');
lib.silence();
(async () => {
    const {vm, loadMs} = await lib.makeVM(process.argv[2]);
    let t = Date.now();
    lib.broadcast(vm, 'init');
    await lib.runUntilIdle(vm);
    const allocMs = Date.now() - t;
    const res = {loadMs, allocMs};
    const run = async (start, n, need) => {
        lib.setVar(vm, 'bench_start', start); lib.setVar(vm, 'bench_n', n); lib.setVar(vm, 'bench_need', need);
        const t0 = process.hrtime.bigint();
        lib.broadcast(vm, 'bench');
        await lib.runUntilIdle(vm);
        return Number(process.hrtime.bigint() - t0) / 1e6 / n;
    };
    res.prefill_0_32 = await run(0, 32, 0);
    res.decode_32_48 = await run(32, 16, 1);
    res.prefill_48_200 = await run(48, 152, 0);
    res.decode_200_216 = await run(200, 16, 1);
    res.prefill_216_480 = await run(216, 264, 0);
    res.decode_480_496 = await run(480, 16, 1);
    console.log(JSON.stringify(res));
})();
