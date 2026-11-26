// Audit Turbo 2.0 in headless TurboWarp at 30 fps: load time, green flag -> ready, idle frames,
// and per-frame work while answering. Usage: node audit_t20.js Turbo2.sb3 out.json
const L = require('../harness/twlib.js');
const fs = require('fs');
L.silence();
(async () => {
    const sb3 = process.argv[2];
    const loads = [];
    for (let i = 0; i < 3; i++) { const H0 = await L.makeVM(sb3); loads.push(+H0.loadMs.toFixed(0)); }
    const H = await L.makeVM(sb3);
    H.vm.greenFlag();
    const boot = await L.frames(H, () => H.question !== null, 'boot');
    const idle = await L.frames(H, () => H.simMs > boot.simMs + 3000, 'idle');
    const prompts = ['what is the capital of thailand?', "what's 17.5% of 240?", 'tell me a story about a kind dragon'];
    const turns = [];
    for (const p of prompts) {
        const gen0 = L.getVar(H.vm, 'stat_fwd');
        L.answer(H, p);
        const r = await L.frames(H, () => H.question !== null, 'answer');
        turns.push({prompt: p, frames: r.frames, sim_s: +(r.simMs / 1000).toFixed(2),
            forward_passes: Number(L.getVar(H.vm, 'stat_fwd')) - Number(gen0),
            reply: String(L.getVar(H.vm, 'display'))});
    }
    const by = t => L.frameStats(H.frames.filter(f => f.tag === t));
    const out = {loadMs: loads, boot_sim_ms: +boot.simMs.toFixed(0), boot_frames: by('boot'), idle_frames: by('idle'),
        answer_frames: by("answer"), turns, big_frames: H.frames.map((f, i) => ({i, tag: f.tag, ms: +f.work.toFixed(1)})).filter(f => f.ms > 50)};
    fs.writeFileSync(process.argv[3], JSON.stringify(out, null, 1));
    console.log(JSON.stringify(out, null, 1));
})();
