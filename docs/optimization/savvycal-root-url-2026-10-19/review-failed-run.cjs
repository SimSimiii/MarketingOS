// Read actual failed execution UI and the proposed CTA; no form submission.
const fs = require('node:fs');
const path = require('node:path');
const {chromium} = require('C:/Users/oussa/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright');
const root = __dirname;
const config = JSON.parse(fs.readFileSync(path.join(root, 'case.json'), 'utf8'));
const execution = '43b2b74b-6e43-47a2-8dae-3772d0cfff2a';
const dir = path.join(root, 'runs', execution);
const result = JSON.parse(fs.readFileSync(path.join(dir, 'result.json'), 'utf8'));
const proposed = result.result.brief.emails[0].next_step_url;
const link = new URL(proposed, config.website_url).href;
let browser;
(async () => {
  browser = await chromium.launch({executablePath:'C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe',headless:true});
  const ctaPage = await browser.newPage({viewport:{width:1280,height:900}});
  const response = await ctaPage.goto(link,{waitUntil:'domcontentloaded',timeout:45000});
  await ctaPage.locator('body').waitFor();
  const cta = {scope:'Proposed CTA only; no email asset was delivered',url:link,final_url:ctaPage.url(),status:response.status(),title:await ctaPage.title(),
    text:(await ctaPage.locator('body').innerText()).slice(0,12000),inputs:await ctaPage.locator('input').evaluateAll(nodes=>nodes.map(n=>({type:n.type,placeholder:n.placeholder})))};
  await ctaPage.screenshot({path:path.join(dir,'proposed-cta.png'),fullPage:true});
  fs.writeFileSync(path.join(dir,'proposed-cta-check.json'),JSON.stringify(cta,null,2));
  const checks = [];
  for (const width of [1440,390]) {
    const page = await browser.newPage({viewport:{width,height:1000}});
    const errors = [];
    page.on('pageerror',e=>errors.push(e.message));
    const url = `http://localhost:3000/campaigns/${config.campaign_id}/executions/${execution}/`;
    const appResponse = await page.goto(url,{waitUntil:'domcontentloaded',timeout:45000});
    let loadError = null;
    try { await page.waitForFunction(()=>/SavvyCal/.test(document.body.innerText)&&/failed|needs input|needs your answers|échou/i.test(document.body.innerText),null,{timeout:45000}); }
    catch(e) { loadError=e.message; }
    const layout = await page.evaluate(()=>({text:document.body.innerText,scrollWidth:document.documentElement.scrollWidth,width:innerWidth}));
    checks.push({url,status:appResponse.status(),errors,loadError,...layout});
    await page.screenshot({path:path.join(dir,`failed-execution-ui-${width}.png`),fullPage:true});
    await page.screenshot({path:path.join(dir,`failed-execution-viewport-${width}.png`)});
    await page.close();
  }
  fs.writeFileSync(path.join(dir,'failed-ui-check.json'),JSON.stringify({checks},null,2));
  console.log(JSON.stringify({cta:{url:cta.final_url,status:cta.status,title:cta.title},ui:checks.map(({text,...rest})=>rest)}));
})().catch(e=>{console.error(e);process.exitCode=1;}).finally(async()=>{if(browser)await browser.close();});
