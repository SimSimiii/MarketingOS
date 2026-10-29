const fs = require('node:fs');
const path = require('node:path');
const { chromium } = require('C:/Users/oussa/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright');

let browser;
(async () => {
  browser = await chromium.launch({executablePath: 'C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe', headless: true});
  const page = await browser.newPage({viewport: {width: 1440, height: 1000}});
  const errors = [];
  page.on('pageerror', error => errors.push(error.message));
  const brand = JSON.parse(fs.readFileSync(path.join(__dirname, 'case.json'), 'utf8')).brand_id;
  await page.goto(`http://localhost:3000/brands/${brand}/market/`);
  await page.getByRole('tab', {name: /Competitors/}).waitFor({timeout: 60000});
  await page.getByRole('tab', {name: /Competitors/}).click();
  await page.getByText('Fathom Analytics', {exact: true}).first().waitFor();
  await page.getByRole('button', {name: /Fathom Analytics/}).first().click();
  await page.getByText('Fit hypothesis based on read pages:', {exact: false}).first().waitFor();
  await page.screenshot({path: path.join(__dirname, 'ui-functional', 'competitors.png')});
  const marketText = await page.locator('body').innerText();
  await page.getByRole('tab', {name: /Audiences/}).click();
  await page.getByRole('textbox', {name: 'Search audiences'}).waitFor();
  await page.screenshot({path: path.join(__dirname, 'ui-functional', 'audiences.png')});
  const audienceText = await page.locator('body').innerText();
  await page.getByRole('textbox', {name: 'Search audiences'}).fill('public sector');
  await page.getByRole('button', {name: 'Audience details & evidence'}).click();
  await page.locator('summary').filter({hasText: /^Research v\d+ ·/}).click();
  const limitations = page.getByText(/Research limitations \(/).first();
  await limitations.waitFor();
  await limitations.scrollIntoViewIfNeeded();
  await limitations.click();
  await page.screenshot({path: path.join(__dirname, 'ui-functional', 'research-limitations.png')});
  fs.writeFileSync(path.join(__dirname, 'ui-functional', 'market-check.json'), JSON.stringify({
    errors, competitorsVisible: marketText.includes('Fathom Analytics'), researchLimitationsVisible: await limitations.isVisible(),
    audienceWorkspaceVisible: audienceText.includes('Search') && audienceText.includes('public sector'),
    marketText, audienceText,
  }, null, 2));
  if (process.argv[2]) {
    const campaign = JSON.parse(fs.readFileSync(path.join(__dirname, 'case.json'), 'utf8')).campaign_id;
    await page.goto(`http://localhost:3000/campaigns/${campaign}/executions/${process.argv[2]}/`);
    await page.getByText('Evaluate analytics without cookies', {exact: false}).first().waitFor({timeout: 60000});
    const text = await page.locator('body').innerText();
    fs.writeFileSync(path.join(__dirname, 'ui-functional', 'final-execution-check.json'), JSON.stringify({
      errors, subjectVisible: text.includes('Evaluate analytics without cookies'),
      reviewLabels: (text.match(/Drafts need review/g) || []).length, text,
    }, null, 2));
    await page.screenshot({path: path.join(__dirname, 'ui-functional', 'final-execution.png')});
  }
  console.log(JSON.stringify({errors, checked: ['Competitors', 'Audiences']}));
})().catch(error => {console.error(error); process.exitCode = 1;}).finally(async () => {if (browser) await browser.close();});
