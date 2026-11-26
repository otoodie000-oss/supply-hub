// Headless TurboWarp harness for TurboX (also used to audit Turbo 2.0).
//  * TurboWarp scratch-vm fork, compiler enabled, warp timer off.
//  * runtime.currentStepTime = 1000/fps (TurboWarp default fps = 30) and microtasks/immediates
//    flushed between frames (skipping the flush looks like a hang).
//  * No renderer headless, so a say bubble never requests a redraw; we emulate the browser by
//    requesting one on every SAY event (a redraw ends the frame early, exactly as in the GUI).
//  * Frames: each runtime._step() is one frame; its work time is measured with hrtime. A simulated
//    wall clock advances by max(frame interval, work) so latencies model a 30 fps browser.
//  * ask prompts are answered programmatically (QUESTION -> ANSWER events).
const fs = require('fs');
const path = require('path');
const TW_ROOT = process.env.TW_VM || '/home/user/tw/scratch-vm';

function silence () {
    const filt = f => (...a) => {
        const s = a.map(String).join(' ');
        if (/storage|costume|asset|loadCostume|Missing|could not load|renderer|Failed to/i.test(s)) return;
        f(...a);
    };
    console.log = filt(console.log); console.warn = filt(console.warn); console.error = filt(console.error);
}

const flush = () => new Promise(r => setImmediate(r));
const now = () => Number(process.hrtime.bigint()) / 1e6;

async function makeVM (sb3Path, fps = 30) {
    const VM = require(path.join(TW_ROOT, 'src/index.js'));
    const vm = new VM();
    vm.setCompilerOptions({enabled: true, warpTimer: false});
    vm.setFramerate(fps);
    const buf = fs.readFileSync(sb3Path);
    const t0 = now();
    await vm.loadProject(buf);
    const loadMs = now() - t0;
    vm.runtime.currentStepTime = 1000 / fps;
    vm.runtime.on('SAY', () => vm.runtime.requestRedraw());
    const H = {vm, fps, loadMs, frames: [], simMs: 0, question: null, said: []};
    vm.runtime.on('QUESTION', q => { H.question = q; });
    vm.runtime.on('SAY', (t, type, text) => { H.said.push({simMs: H.simMs, text: String(text)}); });
    return H;
}

// Run frames until until() is true (checked after each frame) or the simulated limit is reached.
// tag labels the frames (e.g. 'boot', 'idle', 'answer').
async function frames (H, until, tag, limitMs = 600000) {
    const iv = 1000 / H.fps;
    const start = H.simMs;
    let n = 0;
    while (true) {
        const t0 = now();
        H.vm.runtime._step();
        const work = now() - t0;
        await flush();
        H.frames.push({tag, work});
        H.simMs += Math.max(iv, work);
        n++;
        if (until && until()) break;
        if (H.simMs - start > limitMs) throw new Error('frame limit exceeded (' + tag + ')');
    }
    return {frames: n, simMs: H.simMs - start};
}

function stage (vm) { return vm.runtime.getTargetForStage(); }
function findVar (vm, name) {
    for (const t of vm.runtime.targets) {
        for (const id in t.variables) if (t.variables[id].name === name) return t.variables[id];
    }
    throw new Error('no variable ' + name);
}
function getVar (vm, name) { return findVar(vm, name).value; }
function setVar (vm, name, value) { findVar(vm, name).value = value; }

function answer (H, text) {
    H.question = null;
    H.vm.runtime.emit('ANSWER', text);
}

function frameStats (fr) {
    const w = fr.map(f => f.work).sort((a, b) => a - b);
    if (!w.length) return {n: 0};
    const q = p => w[Math.min(w.length - 1, Math.floor(p * w.length))];
    return {n: w.length, max: +w[w.length - 1].toFixed(2), p99: +q(0.99).toFixed(2), p50: +q(0.5).toFixed(2),
        over50: w.filter(x => x > 50).length};
}

module.exports = {silence, makeVM, frames, flush, getVar, setVar, answer, frameStats, stage, now};
