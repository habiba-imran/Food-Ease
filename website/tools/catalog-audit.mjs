import { chromium } from 'playwright';
import { writeFile } from 'node:fs/promises';
const browser=await chromium.launch({args:['--enable-unsafe-swiftshader']});
const page=await browser.newPage({viewport:{width:1440,height:1000},reducedMotion:'reduce'});
const errors=[]; const missing=[];
page.on('pageerror',e=>errors.push(e.message));
page.on('response',r=>{if(r.status()>=400&&r.url().includes('/static/img/'))missing.push({url:r.url(),status:r.status()});});
await page.goto('http://127.0.0.1:8193/?design=delivery-7');
await page.locator('html[data-foodease-revision]').waitFor();
await page.evaluate(()=>{document.querySelectorAll('img').forEach(i=>i.loading='eager')});
await page.evaluate(()=>Promise.all([...document.images].map(i=>i.decode().catch(()=>{}))));
const broken=await page.locator('img').evaluateAll(images=>images.filter(i=>i.getAttribute('src')&&!i.naturalWidth).map(i=>i.src));
const responsive=[];
for(const width of [320,375,768,1024,1440]) {
 await page.setViewportSize({width,height:1000});
 responsive.push({width,overflow:await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth),photos:await page.locator('.menu-art img').evaluateAll(els=>els.every(i=>getComputedStyle(i).objectFit==='contain'))});
}
await page.locator('.spotlight-gallery').screenshot({path:'../artifacts/lower-section/after-preview.png'});
await page.locator('#popular').evaluate(el=>scrollTo({top:el.offsetTop-140,behavior:'instant'}));
await page.screenshot({path:'../artifacts/lower-section/after-menu.png'});
for(const [id,name] of [['drink-lassi-small','detail-drink'],['biryani-chicken','detail-biryani']]) {
 await page.locator(`[data-id="${id}"] [data-detail-item]`).click();
 await page.locator('[data-item-dialog]').screenshot({path:`../artifacts/lower-section/${name}.png`});
 await page.keyboard.press('Escape');
}
await page.locator('.ar-runway').screenshot({path:'../artifacts/lower-section/tabletop-section.png'});
await page.locator('.assistant-section').screenshot({path:'../artifacts/lower-section/assistant-section.png'});
await page.setViewportSize({width:375,height:812});
await page.locator('.spotlight-gallery').screenshot({path:'../artifacts/lower-section/after-phone-preview.png'});
await page.locator('#popular').evaluate(el=>scrollTo({top:el.offsetTop-140,behavior:'instant'}));
await page.screenshot({path:'../artifacts/lower-section/phone-menu.png'});
await writeFile('../artifacts/lower-section/image-audit.json',JSON.stringify({errors,missing,broken,responsive},null,2));
console.log(JSON.stringify({errors,missing,broken,responsive}));
await browser.close();
if(errors.length||missing.length||broken.length||responsive.some(r=>r.overflow||!r.photos))process.exitCode=1;
