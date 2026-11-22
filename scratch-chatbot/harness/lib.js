// Headless driver for the chatbot .sb3 in vanilla scratch-vm or TurboWarp's fork.
//  * sets runtime.currentStepTime (vanilla leaves it null until start())
//  * flushes microtasks/immediates between steps (the ask/answer and procedure
//    promises resolve there; omitting it looks like a hang)
//  * answers the Stage's ask prompts programmatically
const fs = require('fs');
const path = require('path');

const TW_ROOT = process.env.TW_VM || '/home/user/tw/scratch-vm';

function makeVM (kind) {
    let VM;
    if (kind === 'turbowarp') {
        VM = require(path.join(TW_ROOT, 'src/index.js'));
    } else {
        VM = require('scratch-vm');
    }
    const vm = new VM();
    if (kind === 'turbowarp') vm.setCompilerOptions({enabled: true});
    vm.runtime.currentStepTime = 1000 / 30;
    return vm;
}

function silence () {
    // scratch-vm logs a warning per costume when no storage is attached
    const orig = console.log;
    const origWarn = console.warn;
    const origErr = console.error;
    const filt = f => (...a) => {
        const s = a.map(String).join(' ');
        if (/storage|costume|asset|loadCostume|Missing|could not load/i.test(s)) return;
        f(...a);
    };
    console.log = filt(orig); console.warn = filt(origWarn); console.error = filt(origErr);
}

async function loadProject (vm, sb3Path) {
    await vm.loadProject(fs.readFileSync(sb3Path));
    vm.runtime.currentStepTime = 1000 / 30;
}

function stageVar (vm, name) {
    const st = vm.runtime.getTargetForStage();
    for (const id in st.variables) {
        if (st.variables[id].name === name) return st.variables[id];
    }
    throw new Error('no variable ' + name);
}

const flush = () => new Promise(r => setImmediate(r));

/**
 * Run a scripted conversation. messages: array of strings (may include "/reset").
 * Returns one record per message: {msg, reply, gen, firstLogits, ms, fwd, genTokens, genMs, chat}
 */
async function converse (vm, messages, opts = {}) {
    const cfg = opts.cfg || {};
    for (const k in cfg) stageVar(vm, k).value = cfg[k];
    let questionPending = false;
    let lastSay = null;
    const onQ = q => { if (q !== null) questionPending = true; };
    const onSay = (target, type, text) => { if (!target.isStage) lastSay = text; };
    vm.runtime.on('QUESTION', onQ);
    vm.runtime.on('SAY', onSay);
    const t0 = Date.now();
    vm.greenFlag();
    const res = [];
    let idx = -1;
    let turnStart = 0; let fwd0 = 0; let genStart = null; let stepMs = 0;
    const timeLimit = opts.timeLimitMs || 1e12;
    let loadMs = null;
    while (true) {
        const s0 = process.hrtime.bigint();
        vm.runtime._step();
        const dt = Number(process.hrtime.bigint() - s0) / 1e6;
        stepMs += dt;
        await flush();
        if (idx >= 0 && genStart === null && stageVar(vm, 'gen').value.length > 0) genStart = {t: stepMs, n: 1};
        if (questionPending) {
            questionPending = false;
            if (loadMs === null) loadMs = Date.now() - t0;
            if (idx >= 0) {
                const gen = stageVar(vm, 'gen').value.slice();
                const r = {
                    msg: messages[idx],
                    reply: String(lastSay === null ? '' : lastSay),
                    gen: gen.map(Number),
                    ms: stepMs - turnStart,
                    fwd: Number(stageVar(vm, 'stat_fwd').value) - fwd0,
                    genTokens: gen.length,
                    genMs: genStart ? stepMs - genStart.t : 0,
                    histLen: stageVar(vm, 'hist').value.length,
                    chat: stageVar(vm, 'chat').value.slice()
                };
                if (opts.debug) r.firstLogits = stageVar(vm, 'dbg_logits').value.map(Number);
                res.push(r);
                if (opts.onTurn) opts.onTurn(r, idx);
            }
            idx++;
            if (idx >= messages.length) break;
            lastSay = null;
            turnStart = stepMs;
            genStart = null;
            fwd0 = Number(stageVar(vm, 'stat_fwd').value);
            vm.runtime.emit('ANSWER', messages[idx]);
        }
        if (Date.now() - t0 > timeLimit) throw new Error('time limit exceeded');
    }
    vm.runtime.removeListener('QUESTION', onQ);
    vm.runtime.removeListener('SAY', onSay);
    return {turns: res, loadMs};
}

module.exports = {makeVM, loadProject, converse, stageVar, silence};
