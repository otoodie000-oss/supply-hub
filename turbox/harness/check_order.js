// Verify that every binary-searched list in the .sb3 is strictly increasing under scratch-vm's Cast.compare
// (the comparison the compiled '<' / '=' blocks use).  Usage: node harness/check_order.js SB3
const fs = require('fs');
const path = require('path');
const JSZip = require(path.join(process.env.TW_VM || '/home/user/tw/scratch-vm', 'node_modules/@turbowarp/jszip'));
const Cast = require(path.join(process.env.TW_VM || '/home/user/tw/scratch-vm', 'src/util/cast.js'));
(async () => {
  const zip = await JSZip.loadAsync(fs.readFileSync(process.argv[2]));
  const pj = JSON.parse(await zip.file('project.json').async('string'));
  const stage = pj.targets.find(t => t.isStage);
  const lists = {};
  for (const id in stage.lists) lists[stage.lists[id][0]] = stage.lists[id][1];
  const out = {};
  for (const name of ['E_NAME', 'A_KEY', 'WORDS', 'VOC', 'SPEC_SORTED', 'CH_IN']) {
    const a = lists[name];
    let bad = 0, eq = 0, first = null;
    for (let i = 0; i + 1 < a.length; i++) {
      const c = Cast.compare(a[i], a[i + 1]);
      if (c > 0) { bad++; if (!first) first = [a[i], a[i + 1]]; }
      if (c === 0) eq++;
    }
    out[name] = {items: a.length, out_of_order: bad, equal_neighbours: eq, first_bad: first};
  }
  console.log(JSON.stringify(out, null, 1));
})();
