// Package TurboX.sb3 into a standalone offline HTML file with the TurboWarp packager (Node API).
// Usage: node harness/package_html.js SB3 OUT.html   (needs @turbowarp/packager installed; see README)
const fs = require('fs');
const Packager = require(process.env.TW_PACKAGER || '/home/user/work/pkgr/node_modules/@turbowarp/packager');
(async () => {
  const [sb3, out] = process.argv.slice(2);
  const loaded = await Packager.loadProject(fs.readFileSync(sb3));
  const p = new Packager.Packager();
  p.project = loaded;
  p.options.app.windowTitle = 'TurboX';
  p.options.autoplay = true;
  p.options.framerate = 30;
  p.options.compiler.enabled = true;
  p.options.compiler.warpTimer = false;
  const r = await p.package();
  fs.writeFileSync(out, r.data);
  console.log(JSON.stringify({out, bytes: fs.statSync(out).size, type: r.type}));
})().catch(e => { console.error(e); process.exit(1); });
