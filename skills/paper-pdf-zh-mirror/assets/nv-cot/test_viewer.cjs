let playwright;try{playwright=require('playwright')}catch{playwright=require('C:/Users/Aaron/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright')};const {chromium}=playwright;
const {pathToFileURL}=require('url');const path=require('path');const fs=require('fs');
(async()=>{
 const out=process.argv[2]||'outputs/NV-CoT_mirror';const browser=await chromium.launch({headless:true,executablePath:process.env.PDF_TEST_BROWSER||'C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe'});
 const page=await browser.newPage({viewport:{width:1600,height:1050},acceptDownloads:true});let errors=[],network=[];page.on('pageerror',e=>errors.push(e.message));page.on('request',r=>{if(/^https?:/.test(r.url()))network.push(r.url())});
 await page.goto(pathToFileURL(path.resolve(out,'双栏阅读器.html')).href);
 await page.waitForFunction(()=>window.viewerReady,{timeout:60000});await page.waitForFunction(()=>document.querySelectorAll('canvas').length>=2,{timeout:60000});
 const checks={offline_load:true};
 await page.selectOption('#page','2');await page.waitForTimeout(1500);await page.screenshot({path:path.join(out,'reader-preview.png')});
 checks.page_jump=await page.evaluate(()=>window.viewerState().page===2);
 await page.locator('#zoom-in').click();await page.waitForTimeout(600);checks.synchronized_zoom=await page.evaluate(()=>window.viewerState().zoom>1&&document.querySelectorAll('.pdf-page')[0].style.width===document.querySelectorAll('.pane')[1].querySelector('.pdf-page').style.width);
 await page.selectOption('#columns','2');await page.waitForTimeout(500);checks.two_page_layout=await page.evaluate(()=>window.viewerState().columns===2);
 await page.selectOption('#columns','1');await page.selectOption('#view','translated');checks.translation_switch=await page.locator('.pane[data-doc="0"]').isHidden();
 await page.selectOption('#view','both');await page.evaluate(()=>{document.querySelector('.pane').scrollTop=1250});await page.waitForTimeout(500);checks.synchronized_scroll=await page.evaluate(()=>Math.abs(document.querySelectorAll('.pane')[0].scrollTop-document.querySelectorAll('.pane')[1].scrollTop)<2);
 await page.locator('#quality').click();checks.quality_dialog=await page.locator('dialog').isVisible();await page.locator('#close-report').click();
 const promise=page.waitForEvent('download');await page.locator('#download').click();const download=await promise;checks.pdf_download=download.suggestedFilename().endsWith('.pdf');
 checks.no_javascript_errors=errors.length===0;checks.no_remote_requests=network.length===0;checks.errors=errors;fs.writeFileSync(path.join(out,'viewer-tests.json'),JSON.stringify(checks,null,2));console.log(checks);
 await browser.close();if(Object.values(checks).some(v=>v===false))process.exit(1);
})().catch(e=>{console.error(e);process.exit(1)});
