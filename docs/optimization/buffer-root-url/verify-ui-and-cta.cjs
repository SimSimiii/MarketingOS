// Read the delivered CTA and actual application UI without submitting any form.
const fs = require('node:fs');
const path = require('node:path');
const { chromium } = require('C:/Users/oussa/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright');
const execution = process.argv[2];
if (!/^[a-f0-9-]{36}$/.test(execution || '')) throw new Error('Execution UUID required');
const root = __dirname;
const directory = path.join(root, 'runs', execution);
const config = JSON.parse(fs.readFileSync(path.join(root, 'case.json'), 'utf8'));
const render = JSON.parse(fs.readFileSync(path.join(directory, 'render-check.json'), 'utf8'));
const link = render.checks[0].links.find(link => link.href.startsWith('https://'));
let browser;
(async () => {
  browser = await chromium.launch({ executablePath: 'C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe', headless: true });
  const page = await browser.newPage({ viewport: { width: 1440, height: 1000 } });
  const response = await page.goto(link.href, { waitUntil: 'domcontentloaded', timeout: 45000 });
  await page.locator('body').waitFor();
  const cta = { link, final_url: page.url(), status: response.status(), title: await page.title(),
    text: (await page.locator('body').innerText()).slice(0, 16000),
    inputs: await page.locator('input').evaluateAll(nodes => nodes.map(node => ({type: node.type, placeholder: node.placeholder}))) };
  await page.screenshot({ path: path.join(directory, 'cta-destination.png'), fullPage: true });
  fs.writeFileSync(path.join(directory, 'cta-check.json'), JSON.stringify(cta, null, 2));
  const app = await browser.newPage({ viewport: { width: 1440, height: 1000 } });
  const errors = [];
  app.on('pageerror', error => errors.push(error.message));
  const url = `http://localhost:3000/campaigns/${config.campaign_id}/executions/${execution}/`;
  const appResponse = await app.goto(url, { waitUntil: 'domcontentloaded', timeout: 45000 });
  await app.getByText('Buffer', {exact: false}).first().waitFor({timeout: 45000});
  // The data comes from the app's real proxy. No request interception or mock routes.
  await app.waitForFunction(() => /completed|review|terminé/i.test(document.body.innerText), null, {timeout: 45000});
  const ui = {url, status: appResponse.status(), errors, text: (await app.locator('body').innerText()).slice(0, 25000)};
  await app.screenshot({path: path.join(directory, 'execution-ui.png'), fullPage: true});
  fs.writeFileSync(path.join(directory, 'ui-check.json'), JSON.stringify(ui, null, 2));
  console.log(JSON.stringify({cta: {url: cta.final_url, status: cta.status, title: cta.title}, ui: {status: ui.status, errors}}));
})().catch(error => {console.error(error); process.exitCode = 1;}).finally(async () => {if (browser) await browser.close();});
