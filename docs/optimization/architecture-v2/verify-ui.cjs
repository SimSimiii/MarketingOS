const fs = require('node:fs');
const path = require('node:path');
const {chromium} = require('C:/Users/oussa/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright');
(async () => {
  const output = path.resolve('docs/optimization/architecture-v2/ui');
  fs.mkdirSync(output, {recursive:true});
  const browser = await chromium.launch({executablePath:'C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe',headless:true});
  const report = {errors:[],views:[]};
  try {
    for (const [label,width,height] of [['desktop',1280,960],['mobile',390,844]]) {
      const page = await browser.newPage({viewport:{width,height},deviceScaleFactor:1});
      page.on('pageerror', error => report.errors.push(error.message));
      let submitted;
      await page.route('**/api/**', async route => {
        if (!['GET','HEAD','OPTIONS'].includes(route.request().method())) {
          if (new URL(route.request().url()).pathname === '/api/campaigns') submitted = route.request().postDataJSON();
          await route.fulfill({status:409,contentType:'application/json',body:JSON.stringify({detail:'UI validation: submission intercepted; no record created.'})});
        } else await route.continue();
      });
      await page.goto('http://localhost:3000/campaigns',{waitUntil:'networkidle'});
      await page.getByRole('button',{name:'New campaign',exact:true}).click();
      const dialog = page.getByRole('dialog');
      const labels = await dialog.locator('label').allTextContents();
      await dialog.locator('#name').fill('UI validation campaign');
      await dialog.locator('#reader-relationship').selectOption('subscriber');
      await dialog.locator('#announcement-facts').fill('Our workshop registration opens on 20 October.');
      await dialog.locator('#reason-now').fill('The programme is available.');
      await dialog.locator('#campaign-objective').scrollIntoViewIfNeeded();
      await page.screenshot({path:path.join(output,label+'.png'),fullPage:false});
      await dialog.locator('#strategy_mode').scrollIntoViewIfNeeded();
      await page.screenshot({path:path.join(output,label+'-approach.png'),fullPage:false});
      const metrics = await page.evaluate(() => ({viewport:innerWidth,document:document.documentElement.scrollWidth,dialog:document.querySelector('[role="dialog"]')?.getBoundingClientRect().width}));
      await dialog.getByRole('button',{name:/Launch Email/i}).click();
      await page.waitForTimeout(300);
      if (!submitted || submitted.strategy_mode !== 'auto' || submitted.intent.objective !== 'announcement' || submitted.intent.reader_relationship !== 'subscriber' || !submitted.intent.announcement.includes('20 October')) throw new Error('Intent did not reach the intercepted campaign payload');
      report.views.push({label,metrics,labels,strategy_mode:submitted.strategy_mode,submitted_intent:submitted.intent});
      await page.close();
    }
    fs.writeFileSync(path.join(output,'verification.json'),JSON.stringify(report,null,2));
    if (report.errors.length) throw new Error('Browser page errors: '+report.errors.join('; '));
    console.log(JSON.stringify(report.views.map(view=>({label:view.label,metrics:view.metrics,intent:view.submitted_intent})),null,2));
  } finally { await browser.close(); }
})().catch(error=>{console.error(error.stack);process.exitCode=1;});
