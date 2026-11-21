// Real hosted website + RTC + worker/providers. Synthetic silent microphone;
// recognized requests enter the same text lane used by Hey Zara's handoff.
// This measures request-to-status/caption, NOT caller-heard speech latency.
import { chromium } from '@playwright/test';
import { mkdir, writeFile } from 'node:fs/promises';
const target = 'https://food-ease-seven.vercel.app';
const evidence = '../voice-agent/evidence/reply-recovery-2026-11-21';
const report = {target, mode:'hosted_real_providers_synthetic_recognized_requests', errors:[], turns:[]};
const browser = await chromium.launch();
const page = await browser.newPage({permissions:['microphone']});
page.on('pageerror', error => report.errors.push(error.message));
await page.route('**/static/vendor/livekit-client.2.15.4.mjs*', async route => {
  if (new URL(route.request().url()).searchParams.has('native-audit')) return route.continue();
  await route.fulfill({contentType:'text/javascript',body:`
    import * as sdk from '/static/vendor/livekit-client.2.15.4.mjs?native-audit=1';
    export {RoomEvent,Track,LocalAudioTrack} from '/static/vendor/livekit-client.2.15.4.mjs?native-audit=1';
    export class Room extends sdk.Room {
      constructor(...args) {
        super(...args); (window.auditRooms ||= []).push(this);
        const register=this.registerRpcMethod.bind(this);
        this.registerRpcMethod=(method,handler) => register(method,async data => {
          const started=performance.now();
          const result=await handler(data);
          if(method==='foodease.action.v2') {
            try {
              const response=JSON.parse(result);
              (window.auditActions ||= []).push({operation:response.payload.operation,status:response.payload.status,durationMs:Math.round(performance.now()-started)});
            } catch {}
          }
          return result;
        });
        this.on(sdk.RoomEvent.DataReceived, (raw, participant, kind, topic) => {
          if (topic !== 'foodease.events.v2') return;
          try { const event=JSON.parse(new TextDecoder().decode(raw));
            (window.auditEvents ||= []).push({event, at:performance.now()});
          } catch {}
        });
      }

    }
  `});
});
await page.addInitScript(() => {
  navigator.mediaDevices.getUserMedia = async () => {
    const context = new AudioContext();
    const source = context.createOscillator(), gain = context.createGain();
    gain.gain.value = 0;
    const destination = context.createMediaStreamDestination();
    source.connect(gain).connect(destination); source.start();
    await context.resume();
    window.auditAudio = {context, source};
    return destination.stream;
  };
});
try {
  await page.goto(target, {waitUntil:'domcontentloaded',timeout:60000});
  await page.waitForFunction(() => document.documentElement.dataset.foodeaseRevision);
  report.source = await page.locator('script[src*="app.js"]').getAttribute('src');
  await page.locator('[data-voice-launcher]').click();
  await page.locator('[data-voice-use]').click();
  await page.waitForFunction(() => ['voice_active','error'].includes(document.documentElement.dataset.assistanceState), null, {timeout:100000});
  if (await page.locator('html').getAttribute('data-assistance-state') !== 'voice_active') throw new Error('Voice startup failed');
  // Let the direct greeting finish before sending actual questions.
  await page.waitForFunction(() => (window.auditEvents || []).some(({event}) =>
    event.type==='transcript.assistant' && event.payload.phase==='completed' && event.payload.text));
  await page.waitForTimeout(300);
  for (const question of ['السلام علیکم، مینیو میں کون کون سی کیٹیگریز ہیں؟', 'برگر کی تمام اقسام قیمتوں کے ساتھ بتائیں۔']) {
    const sent = await page.evaluate(async question => {
      const sid=sessionStorage.getItem('foodease.shopping-session.v2');
      const response=await fetch('/api/v2/app/context',{headers:{'X-FoodEase-Session':sid}});
      if(!response.ok) throw new Error('Audit could not read the current application context');
      const snapshot=await response.json();
      const context={sid,revision:snapshot.revision};
      const event={schema_version:'2.0',session_id:context.sid,event_id:crypto.randomUUID(),
        turn_id:crypto.randomUUID(),timestamp:new Date().toISOString(),context_revision:context.revision,
        type:'app.text_input',payload:{text:question}};
      const baseline=window.auditEvents.length, actionBaseline=(window.auditActions || []).length, at=performance.now();
      await window.auditRooms[1].localParticipant.publishData(new TextEncoder().encode(JSON.stringify(event)),
        {reliable:true,topic:'foodease.text_input.v2'});
      return {baseline,actionBaseline,at,turnId:event.turn_id};
    }, question);
    await page.waitForFunction(({baseline,turnId}) => (window.auditEvents || []).slice(baseline).some(({event}) =>
      event.type==='agent.error' && (!event.turn_id || event.turn_id===turnId) ||
      event.type==='transcript.assistant' && event.turn_id===turnId &&
      (event.payload.phase==='failed' || event.payload.phase==='completed' && event.payload.text.trim())), sent, {timeout:60000});
    const result = await page.evaluate(({baseline,actionBaseline,at,turnId}) => {
      const events=window.auditEvents.slice(baseline);
      const terminal=events.find(({event}) => event.type==='agent.error' && (!event.turn_id || event.turn_id===turnId) ||
        event.type==='transcript.assistant' && event.turn_id===turnId &&
        (event.payload.phase==='failed' || event.payload.phase==='completed' && event.payload.text.trim()));
      const speaking=events.find(({event}) => event.type==='agent.status' && event.payload.state==='assistant_speaking');
      return {phase:terminal.event.payload.phase || 'error',text:terminal.event.payload.text || terminal.event.payload.message,
        requestToCaptionMs:Math.round(terminal.at-at),requestToSpeakingStatusMs:speaking?Math.round(speaking.at-at):null,
        failures:events.filter(({event}) => event.type==='transcript.assistant' && event.payload.phase==='failed').length,
        actions:(window.auditActions || []).slice(actionBaseline)};
    }, sent);
    report.turns.push({question,...result});
    if (result.phase !== 'completed') throw new Error('Real question failed');
    if (result.text.length < 15) throw new Error('Question received an empty or incomplete answer');
    // Category/navigation facts are already supplied by the verified reasoning context.
    // The explicit price/filter request below should exercise a real application action.
    if (report.turns.length===2 && !result.actions.length) throw new Error('Price request did not exercise application tools');
    if (report.turns.length===1 && (result.text.match(/برگر|بریانی|کڑاہی|رول|مشروبات|میٹھے|ریپ|پلیٹر/g) || []).length < 3)
      throw new Error('Category question did not list category choices');
    if (report.turns.length===2 && !/روپے|روپیہ|PKR/.test(result.text)) throw new Error('Price question did not include prices');
    // Completion follows playout, so the next request does not interrupt this reply.
    await page.waitForTimeout(300);
  }
} catch (error) {
  report.errors.push(error.message); process.exitCode=1;
} finally {
  const wake=page.locator('[data-wake-toggle]');
  if(await wake.isVisible().catch(()=>false)) await wake.click().catch(()=>{});
  const stop=page.locator('[data-voice-end]');
  if(await stop.isVisible().catch(()=>false)) await stop.click().catch(()=>{});
  await page.waitForTimeout(1000).catch(()=>{});
  await browser.close();
  await mkdir(evidence,{recursive:true});
  await writeFile(evidence+'/hosted-questions.json',JSON.stringify(report,null,2));
  console.log(JSON.stringify(report,null,2));
}
