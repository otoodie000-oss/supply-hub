// End-to-end check of the packaged TurboX.html in headless Chromium with ALL network blocked:
// load it from file://, wait for the first ask prompt, type questions into the real ask box, read the replies.
// Usage: node harness/check_html.js build/TurboX.html
const { chromium } = require('playwright');
const path = require('path');
(async () => {
    const file = 'file://' + path.resolve(process.argv[2]);
    const qs = process.argv.slice(3).length ? process.argv.slice(3) :
        ['What is the capital of France?', 'What is 15% of 80?', 'Tell me a joke about cats.', '/help'];
    const browser = await chromium.launch();
    const page = await browser.newPage();
    const blocked = [];
    await page.route('**/*', r => r.request().url().startsWith('file://') || r.request().url().startsWith('data:') ?
        r.continue() : (blocked.push(r.request().url()), r.abort()));
    const t0 = Date.now();
    await page.goto(file);
    await page.waitForFunction(() => window.vm && window.vm.runtime, null, {timeout: 60000});
    await page.evaluate(() => {
        window.__said = [];
        window.vm.runtime.on('SAY', (t, type, text) => { if (text) window.__said.push(String(text)); });
    });
    await page.waitForSelector('.sc-question-input', {timeout: 60000});
    const readyMs = Date.now() - t0;
    const out = [];
    for (const q of qs) {
        await page.evaluate(() => { window.__said = []; });
        await page.fill('.sc-question-input', q);
        const s = Date.now();
        await page.press('.sc-question-input', 'Enter');
        await page.waitForFunction(() => {
            const el = document.querySelector('.sc-question-input');
            return window.__said.length > 0 && el && el.offsetParent !== null && el.value === '';
        }, null, {timeout: 60000});
        await page.waitForTimeout(300);
        const said = await page.evaluate(() => window.__said[window.__said.length - 1]);
        out.push({q, reply: said, ms: Date.now() - s});
    }
    console.log(JSON.stringify({readyMs, blocked, turns: out}, null, 1));
    await browser.close();
})();
