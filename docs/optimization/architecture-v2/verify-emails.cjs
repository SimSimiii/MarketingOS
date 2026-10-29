const fs=require('node:fs');
const path=require('node:path');
const {pathToFileURL}=require('node:url');
const {chromium}=require('C:/Users/oussa/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright');
(async()=>{
 const browser=await chromium.launch({executablePath:'C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe',headless:true});
 const root=path.resolve('docs/optimization/architecture-v2');
 const checks=[];
 try {
  for(const name of ['activation','consumer-offer']){
   for(const width of [1280,390]){
    const page=await browser.newPage({viewport:{width,height:1000}});
    await page.goto(pathToFileURL(path.join(root,'comparisons/production-direct',name,'direct/email-1.html')).href);
    const data=await page.evaluate(()=>({width:innerWidth,scroll:document.documentElement.scrollWidth,links:[...document.querySelectorAll('a')].map(a=>({text:a.textContent.trim(),href:a.getAttribute('href')})),text:document.body.innerText}));
    if(data.scroll>data.width)throw Error('Horizontal overflow: '+name);
    const destination=name==='activation'?'https://portway.example/connect':'https://clayroom.example/programme';
    if(!data.links.some(a=>a.href===destination))throw Error('Wrong CTA destination: '+name+' '+JSON.stringify(data.links));
    await page.screenshot({path:path.join(root,'ui',name+'-'+width+'.png'),fullPage:true});
    checks.push({name,width,scroll:data.scroll,links:data.links});
    await page.close();
   }
  }
  fs.writeFileSync(path.join(root,'ui/email-verification.json'),JSON.stringify(checks,null,2));
  console.log(JSON.stringify(checks,null,2));
 } finally {await browser.close();}
})().catch(e=>{console.error(e);process.exitCode=1;});
