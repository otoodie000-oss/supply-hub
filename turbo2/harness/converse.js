// Drive Turbo2.sb3 through its real UI loop (stage ask -> answer) for scripted conversations.
// Usage: node converse.js spec.json out.json
// spec: {sb3, cfg: {cfg_greedy:1,...}, convs: [[msg | {text, force:[ids]}], ...]}  (/reset between convs)
const lib = require('./lib.js');
const fs = require('fs');
lib.silence();

(async () => {
    const spec = JSON.parse(fs.readFileSync(process.argv[2]));
    const {vm, loadMs} = await lib.makeVM(spec.sb3);
    for (const k in (spec.cfg || {})) lib.setVar(vm, k, spec.cfg[k]);
    let question = false;
    vm.runtime.on('QUESTION', q => { if (q !== null) question = true; });
    const t0 = Date.now();
    vm.greenFlag();
    // queue of messages: each conv followed by /reset
    const queue = [];
    spec.convs.forEach((conv, ci) => {
        conv.forEach((m, ti) => queue.push({ci, ti, m: typeof m === 'string' ? {text: m} : m}));
        queue.push({ci, ti: -1, m: {text: '/reset'}});
    });
    let bootMs = null;
    const out = {loadMs, turns: []};
    let cur = null;
    let qi = -1;
    while (true) {
        const s0 = process.hrtime.bigint();
        vm.runtime._step();
        const dt = Number(process.hrtime.bigint() - s0) / 1e6;
        await lib.flush();
        if (cur) {
            cur.stepMs += dt;
            if (cur.firstTokMs === null && lib.list(vm, 'gen').length > 0) {
                cur.firstTokMs = cur.stepMs; cur.fwdAtFirst = Number(lib.getVar(vm, 'stat_fwd').value);
            }
        }
        if (question) {
            question = false;
            if (bootMs === null) { bootMs = Date.now() - t0; out.bootMs = bootMs; }
            if (cur && cur.q.ti >= 0) {
                const gen = lib.list(vm, 'gen').map(Number);
                const fwd = Number(lib.getVar(vm, 'stat_fwd').value);
                const rec = {conv: cur.q.ci, turn: cur.q.ti, msg: cur.q.m.text,
                    reply: String(lib.getVar(vm, 'reply_text').value), display: String(lib.getVar(vm, 'display').value),
                    gen, tool_call: String(lib.getVar(vm, 'tool_call_text').value),
                    tool_result: String(lib.getVar(vm, 'tool_result_text').value),
                    facts: Number(lib.getVar(vm, 'nfacts_used').value),
                    ms: cur.stepMs, firstTokMs: cur.firstTokMs, prefillFwd: (cur.fwdAtFirst || fwd) - cur.fwd0,
                    totalFwd: fwd - cur.fwd0, genTokens: gen.length, histLen: lib.list(vm, 'hist').length};
                if (spec.cfg && spec.cfg.cfg_debug === 1) rec.firstLogits = lib.list(vm, 'dbg_logits').map(Number);
                out.turns.push(rec);
            }
            qi++;
            if (qi >= queue.length) break;
            const q = queue[qi];
            lib.list(vm, 'gen').length = 0;
            const force = lib.list(vm, 'force');
            force.length = 0;
            (q.m.force || []).forEach(t => force.push(t));
            cur = {q, stepMs: 0, firstTokMs: null, fwd0: Number(lib.getVar(vm, 'stat_fwd').value), fwdAtFirst: null};
            vm.runtime.emit('ANSWER', q.m.text);
        }
        if (Date.now() - t0 > (spec.timeLimitMs || 3600000)) throw new Error('time limit');
    }
    out.chat = lib.list(vm, 'chat').slice();
    fs.writeFileSync(process.argv[3], JSON.stringify(out));
    console.log('turns', out.turns.length, 'bootMs', out.bootMs, 'loadMs', loadMs);
})();
