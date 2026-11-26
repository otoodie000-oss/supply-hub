// Run conversations through TurboX.sb3 in headless TurboWarp and record replies, traces and timing.
// Usage: node harness/run_sb3.js SB3 ITEMS.json OUT.jsonl [fbb]
//   ITEMS.json: [{id, turns: [..], now: "y m d h mi off" | "", seed: n}]
// Each item: set cfg_now/cfg_seed, green flag (fresh session), answer each ask with the next turn.
const fs = require('fs');
const T = require('./twlib.js');

async function main () {
    T.silence();
    const [sb3, itemsPath, outPath, fbb] = process.argv.slice(2);
    const items = JSON.parse(fs.readFileSync(itemsPath, 'utf8'));
    const H = await T.makeVM(sb3, 30);
    const vm = H.vm;
    const out = fs.createWriteStream(outPath);
    const listVal = name => T.getVar(vm, name).slice();
    process.stderr.write(JSON.stringify({loadMs: +H.loadMs.toFixed(0)}) + '\n');
    if (fbb !== undefined) T.setVar(vm, 'cfg_fbb', Number(fbb));
    let first = true;
    for (const it of items) {
        T.setVar(vm, 'cfg_now', it.now || '');
        T.setVar(vm, 'cfg_seed', it.seed || 12345);
        const f0 = H.frames.length;
        const s0 = H.simMs;
        vm.greenFlag();
        await T.frames(H, () => H.question !== null, first ? 'flag_first' : 'flag');
        const flagMs = H.simMs - s0;
        first = false;
        const turns = [];
        for (const text of it.turns) {
            const t0 = H.simMs;
            const said0 = H.said.length;
            const fa = H.frames.length;
            T.answer(H, text);
            await T.frames(H, () => T.getVar(vm, 'busy') == 0 && H.question !== null, 'answer');
            let firstWord = null;
            for (let k = said0; k < H.said.length; k++) {
                const s = H.said[k];
                if (s.text !== '...' && s.text !== '' && firstWord === null) firstWord = s.simMs - t0;
            }
            const fs_ = T.frameStats(H.frames.slice(fa));
            turns.push({reply: String(T.getVar(vm, 'display')), mode: String(T.getVar(vm, 'reply_mode')),
                trace: listVal('TRACE').map(String), latencyMs: +(H.simMs - t0).toFixed(1),
                firstWordMs: firstWord === null ? null : +firstWord.toFixed(1), frames: fs_,
                tokens: T.getVar(vm, 'stat_tokens')});
        }
        out.write(JSON.stringify({id: it.id, turns, flagMs: +flagMs.toFixed(1)}) + '\n');
    }
    // idle frames
    await T.frames(H, null, 'idle', 3000).catch(() => {});
    const byTag = {};
    for (const f of H.frames) (byTag[f.tag] = byTag[f.tag] || []).push(f);
    const stats = {};
    for (const k in byTag) stats[k] = T.frameStats(byTag[k]);
    process.stderr.write(JSON.stringify({frames: stats, loadMs: +H.loadMs.toFixed(0)}) + '\n');
    out.end();
}
main().catch(e => { console.error(e); process.exit(1); });
