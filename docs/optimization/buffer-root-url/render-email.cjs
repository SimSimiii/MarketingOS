// Read-only browser review of saved deliverables. Never launches a generation.
const fs = require('node:fs');
const path = require('node:path');
const { chromium } = require('C:/Users/oussa/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright');
const execution = process.argv[2];
if (!/^[a-f0-9-]{36}$/.test(execution || '')) throw new Error('Execution UUID required');
const directory = path.join(__dirname, 'runs', execution);
const result = JSON.parse(fs.readFileSync(path.join(directory, 'result.json'), 'utf8'));
const emails = result.assets.filter(asset => asset.asset_type === 'email');
let browser;
(async () => {
  browser = await chromium.launch({executablePath: 'C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe', headless: true});
  const checks = [];
  for (let index = 0; index < emails.length; index++) {
    const asset = emails[index];
    fs.writeFileSync(path.join(directory, `email-${index + 1}.html`), asset.content_html);
    fs.writeFileSync(path.join(directory, `email-${index + 1}.txt`), asset.content);
    for (const width of [1280, 390]) {
      const page = await browser.newPage({viewport: {width, height: 900}});
      await page.setContent(asset.content_html, {waitUntil: 'domcontentloaded'});
      await page.evaluate(() => document.fonts.ready);
      const layout = await page.evaluate(() => ({
        width: innerWidth, scrollWidth: document.documentElement.scrollWidth,
        links: Array.from(document.querySelectorAll('a[href]')).map(a => ({text: a.textContent.trim(), href: a.href})),
        text: document.body.innerText,
      }));
      checks.push({email: index + 1, ...layout});
      await page.screenshot({path: path.join(directory, `email-${width}.png`), fullPage: true});
      await page.close();
    }
  }
  fs.writeFileSync(path.join(directory, 'render-check.json'), JSON.stringify({checks}, null, 2));
  console.log(JSON.stringify(checks.map(({email, width, scrollWidth, links}) => ({email, width, scrollWidth, links}))));
})().catch(error => {console.error(error); process.exitCode = 1;}).finally(async () => {if (browser) await browser.close();});
