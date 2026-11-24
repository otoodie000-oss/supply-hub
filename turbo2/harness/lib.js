// Headless TurboWarp driver for Turbo 2.0.
//  * compiler enabled; runtime.currentStepTime set (vanilla leaves it null until start())
//  * microtasks/immediates flushed between steps (ask/answer + procedure promises resolve
//    there; skipping this looks like a hang)
//  * ask prompts answered programmatically
const fs = require('fs');
const path = require('path');
const TW_ROOT = process.env.TW_VM || '/home/user/tw/scratch-vm';

function silence () {
    const filt = f => (...a) => {
        const s = a.map(String).join(' ');
        if (/storage|costume|asset|loadCostume|Missing|could not load|renderer/i.test(s)) return;
        f(...a);
    };
    console.log = filt(console.log); console.warn = filt(console.warn); console.error = filt(console.error);
}

async function makeVM (sb3Path) {
    const VM = require(path.join(TW_ROOT, 'src/index.js'));
    const vm = new VM();
    vm.setCompilerOptions({enabled: true, warpTimer: false});
    vm.runtime.currentStepTime = 1000 / 60;
    const t0 = Date.now();
    await vm.loadProject(fs.readFileSync(sb3Path));
    vm.runtime.currentStepTime = 1000 / 60;
    return {vm, loadMs: Date.now() - t0};
}

const flush = () => new Promise(r => setImmediate(r));

function stage (vm) { return vm.runtime.getTargetForStage(); }
function getVar (vm, name) {
    const st = stage(vm);
    for (const id in st.variables) if (st.variables[id].name === name) return st.variables[id];
    throw new Error('no variable ' + name);
}
function setVar (vm, name, value) { getVar(vm, name).value = value; }
function list (vm, name) { return getVar(vm, name).value; }

// Run until no threads are active (or a predicate holds). Answers asks with answerFn().
async function runUntilIdle (vm, opts = {}) {
    const limit = opts.timeLimitMs || 600000;
    const t0 = Date.now();
    let steps = 0;
    while (true) {
        vm.runtime._step();
        steps++;
        await flush();
        if (opts.until && opts.until()) break;
        if (!opts.until && vm.runtime.threads.length === 0) break;
        if (Date.now() - t0 > limit) throw new Error('time limit exceeded');
    }
    return steps;
}

function broadcast (vm, msg) {
    return vm.runtime.startHats('event_whenbroadcastreceived', {BROADCAST_OPTION: msg});
}

module.exports = {silence, makeVM, flush, getVar, setVar, list, runUntilIdle, broadcast, stage};
