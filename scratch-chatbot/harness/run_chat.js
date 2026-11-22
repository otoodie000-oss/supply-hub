// usage: node run_chat.js <sb3> <vanilla|turbowarp> <json-file-with-{"messages":[...],"cfg":{...},"debug":bool}> [out.json]
const fs = require('fs');
const {makeVM, loadProject, converse, silence} = require('./lib');

(async () => {
    silence();
    const [sb3, kind, specPath, outPath] = process.argv.slice(2);
    const spec = JSON.parse(fs.readFileSync(specPath, 'utf8'));
    const vm = makeVM(kind);
    await loadProject(vm, sb3);
    const out = await converse(vm, spec.messages, {
        cfg: spec.cfg || {}, debug: !!spec.debug,
        onTurn: (r, i) => {
            const per = r.fwd ? (r.ms / r.fwd).toFixed(1) : '-';
            const g = r.genTokens ? (r.genMs / r.genTokens).toFixed(1) : '-';
            console.error(`[${kind}] turn ${i}: ${r.fwd} fwd in ${r.ms.toFixed(0)} ms (${per} ms/fwd; gen ${g} ms/token), hist=${r.histLen}`);
            console.error(`   you: ${r.msg}\n   bot: ${r.reply}`);
        }
    });
    console.error(`[${kind}] load+dequant ${out.loadMs} ms`);
    if (outPath) fs.writeFileSync(outPath, JSON.stringify(out));
    process.exit(0);
})().catch(e => { console.error(e); process.exit(1); });
