// Independent browser assessment; no values are supplied to the generator.
const fs = require('node:fs');
const path = require('node:path');
const {chromium} = require('C:/Users/oussa/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright');
let browser;
(async () => {
  const steps = fs.readdirSync(path.join(__dirname, 'steps')).filter(x => x.endsWith('-ingest.json'));
  const documents = JSON.parse(fs.readFileSync(path.join(__dirname, 'steps', steps[0]), 'utf8'));
  const url = documents.find(d => new URL(d.source_url).pathname === '/pricing').source_url;
  browser = await chromium.launch({executablePath:'C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe', headless:true});
  const page = await browser.newPage({viewport:{width:1280,height:1000}});
  const response = await page.goto(url, {waitUntil:'networkidle',timeout:45000});
  const data = {status:response.status(),url:page.url(),text:await page.locator('body').innerText(),
    controls:await page.locator('button,input,label,[role="switch"],[role="tab"]').evaluateAll(nodes => nodes.map(n => ({
      tag:n.tagName,role:n.getAttribute('role'),text:n.innerText,name:n.getAttribute('aria-label'),
      type:n.getAttribute('type'),checked:n.checked,html:n.outerHTML.slice(0,1000)
    })))};
  await page.screenshot({path:path.join(__dirname,'pricing-browser.png'),fullPage:true});
  await page.getByRole('button',{name:'Monthly',exact:true}).click();
  data.monthly_text = await page.locator('body').innerText();
  for(const name of ['Do you offer a free trial?','How does company billing work?','Are there ways to save?','What happens if I cancel?']) {
    await page.getByRole('button',{name,exact:true}).click();
  }
  data.expanded_text = await page.locator('body').innerText();
  await page.screenshot({path:path.join(__dirname,'pricing-monthly-expanded.png'),fullPage:true});
  fs.writeFileSync(path.join(__dirname,'pricing-browser.json'),JSON.stringify(data,null,2));
  console.log(JSON.stringify({status:data.status,monthly:data.monthly_text.slice(0,700),faq:data.expanded_text.slice(data.expanded_text.indexOf('Frequently Asked Questions'),-100)}));
})().catch(e=>{console.error(e);process.exitCode=1;}).finally(async()=>{if(browser)await browser.close();});
