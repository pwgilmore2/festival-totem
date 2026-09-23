import phone_server

AUDIO_CSS = r"""
<style>
.audioStart{width:100%;min-height:66px;font-size:18px;background:linear-gradient(135deg,#635bff,#00b8ff);box-shadow:0 8px 24px #0006}.audioStart.active{background:linear-gradient(135deg,#ff315f,#ff8a24)}
.audioMeters{display:grid;grid-template-columns:repeat(4,1fr);gap:6px;margin-top:10px}.audioMeter{background:#1d1d26;border-radius:10px;padding:8px 6px;text-align:center}.audioBar{height:62px;background:#0e0e14;border-radius:7px;overflow:hidden;position:relative}.audioFill{position:absolute;left:0;right:0;bottom:0;height:0;background:linear-gradient(#8b7cff,#56d5ff);transition:height .045s linear}.audioLabel{margin-top:5px;font-size:11px;opacity:.65}
.vibePreviewGrid{display:grid;grid-template-columns:repeat(4,1fr);gap:7px;margin:8px 0}.vibePreviewGrid button{min-height:50px;touch-action:manipulation}.vibePreviewGrid button:active{background:#635bff}
.pulseLamp{margin-top:10px;height:12px;border-radius:999px;background:#22222c;transition:background .06s,box-shadow .06s}.pulseLamp.on{background:#fff;box-shadow:0 0 18px #fff}.audioNotice{margin-top:10px;padding:10px;border-radius:11px;background:#ffffff0c;font-size:12px;line-height:1.4}.presetGrid{display:grid;grid-template-columns:repeat(4,1fr);gap:7px}.simpleAudioGrid{display:grid;grid-template-columns:1fr 1fr;gap:8px 12px}.simpleAudioGrid .slider{margin:6px 0}.calStatus{padding:10px 12px;border-radius:12px;background:#ffffff0b;margin-top:10px;font-size:12px}.calStatus strong{display:block;font-size:14px;margin-bottom:2px}.calStatus.active strong{color:#72ffb2}.calStatus.silent strong{color:#9fa6b8}.advancedAudio{margin-top:12px;border-top:1px solid #ffffff15;padding-top:10px}.advancedAudio summary{cursor:pointer;font-weight:700;padding:7px 0}.analyzerCanvas{display:block;width:100%;height:112px;background:#080811;border:1px solid #ffffff18;border-radius:12px;margin:7px 0 12px}.signalCanvas{height:126px}.signalReadout{display:grid;grid-template-columns:repeat(4,1fr);gap:7px;margin:8px 0}.signalStat{background:#ffffff0b;border-radius:10px;padding:8px;text-align:center}.signalStat b{display:block;font-size:17px}.signalStat span{font-size:10px;opacity:.6}.analyzerTitle{display:flex;align-items:center;justify-content:space-between;gap:10px}.analyzerTitle .liveDot{font-size:11px;opacity:.65}.bandKey{display:flex;gap:10px;flex-wrap:wrap;font-size:10px;opacity:.72;margin-top:-5px;margin-bottom:8px}.bandKey i{width:8px;height:8px;border-radius:50%;display:inline-block;margin-right:3px}
@media(max-width:520px){.simpleAudioGrid{grid-template-columns:1fr}.presetGrid,.vibePreviewGrid{grid-template-columns:repeat(2,1fr)}.signalReadout{grid-template-columns:repeat(2,1fr)}}
</style>
"""

AUDIO_TAB = r"""<button id="tabAudio" onclick="view('audio')">Audio</button>"""

AUDIO_SECTION = r"""
<section id="audio" class="view">
<div class="card">
<h2>Phone Audio</h2>
<button id="micButton" class="audioStart" onclick="toggleMic()">🎙 START PHONE AUDIO</button>
<div id="micNotice" class="audioNotice">Checking microphone support...</div>
<div id="calStatus" class="calStatus silent"><strong id="calibrationState">Waiting for mic</strong><span id="calibrationDetail">Start audio and the controller will learn the room floor automatically.</span></div>
<div class="audioMeters">
<div class="audioMeter"><div class="audioBar"><div id="volumeBar" class="audioFill"></div></div><div class="audioLabel">Energy</div></div>
<div class="audioMeter"><div class="audioBar"><div id="bassBar" class="audioFill"></div></div><div class="audioLabel">Low</div></div>
<div class="audioMeter"><div class="audioBar"><div id="midsBar" class="audioFill"></div></div><div class="audioLabel">Body</div></div>
<div class="audioMeter"><div class="audioBar"><div id="highsBar" class="audioFill"></div></div><div class="audioLabel">Bright</div></div>
</div>
<div id="beatLamp" class="pulseLamp"></div>
<div class="simpleAudioGrid">
<div class="slider"><div class="sh"><span>Input gain</span><span id="inputGainValue">1.00x</span></div><input id="inputGain" type="range" min=".4" max="3" step=".05" value="1" oninput="num('inputGainValue',this.value,'x')" onchange="beginCalibration()"></div>
<div class="slider"><div class="sh"><span>Pulse sensitivity</span><span id="beatSensitivityValue">55%</span></div><input id="beatSensitivity" type="range" min="0" max="1" step=".05" value=".55" oninput="pct('beatSensitivityValue',this.value)"></div>
</div>
<button style="width:100%" onclick="beginCalibration()">↻ Reset Room Floor</button>
<div class="audioNotice">The raw spectrum is diagnostic only. Vibe uses a silence gate plus slow per-band baselines, so ordinary bass-heavy spectral slope should not keep every effect active.</div>
<details class="advancedAudio"><summary>Signal analyzer</summary>
<div class="analyzerTitle"><h2>Audio Analyzer</h2><div id="analyzerLive" class="liveDot">MIC OFF</div></div>
<div class="audioLabel">Waveform</div><canvas id="waveformCanvas" class="analyzerCanvas"></canvas>
<div class="audioLabel">Raw frequency spectrum</div><canvas id="spectrumCanvas" class="analyzerCanvas"></canvas>
<div class="bandKey"><span><i style="background:#866cff"></i>Low 35–180 Hz</span><span><i style="background:#ff58c8"></i>Body 180–2200 Hz</span><span><i style="background:#ffd34f"></i>Bright 2.2–9 kHz</span></div>
<div class="audioLabel">Reactive signals — fixed 0–100% scale</div><canvas id="signalCanvas" class="analyzerCanvas signalCanvas"></canvas>
<div class="signalReadout">
<div class="signalStat"><b id="rmsValue">0.000</b><span>RMS</span></div>
<div class="signalStat"><b id="noiseValue">0.000</b><span>NOISE FLOOR</span></div>
<div class="signalStat"><b id="lowBaseValue">0.000</b><span>LOW BASE</span></div>
<div class="signalStat"><b id="brightBaseValue">0.000</b><span>BRIGHT BASE</span></div>
</div>
<div class="audioNotice">A healthy idle state is boring: Energy, Low, Body, and Bright should settle to zero and Pulse should stay off. The raw spectrum may still show microphone and room noise.</div>
</details>
</div>

<div class="card" id="reactiveMappingCard">
<h2>Sound → Visuals</h2>
<div class="slider"><div class="sh"><span>Reactive intensity</span><span id="reactiveStrengthValue"></span></div><input id="reactiveStrength" type="range" min="0" max="1.5" step=".05" oninput="num('reactiveStrengthValue',this.value,'x');range('reactive_strength',this.value)"></div>
<div id="presetButtons" class="presetGrid"></div>
<div id="vibePresetHint" class="audioNotice" aria-live="polite"></div>
<div class="audioLabel" style="margin-top:12px">Try a signal without the microphone</div>
<div class="vibePreviewGrid"><button onclick="previewVibe('low')">Low hit</button><button onclick="previewVibe('pulse')">Pulse</button><button onclick="previewVibe('body')">Body</button><button onclick="previewVibe('bright')">Bright</button></div>
<div class="tiny">Tap while the mic is off. Each button briefly drives the selected Vibe preset on the simulator.</div>
<div id="reactiveLayerMount"></div>
</div>
</section>
"""

AUDIO_JS = r"""
let audioContext=null,analyser=null,micStream=null,audioAnimation=null,lastAudioSend=0,lastBeatTime=0;
let signalHistory=[],pulseLatch=false;
let vibePreviewTimer=null,vibePreviewSerial=0,vibePreviewWasEnabled=false;
const vibePresetDescriptions={Pulse:'Low hits zoom the image; pulse flashes it.',Neon:'Body shifts the colors; bright sounds split the edges.',Spark:'Bright details make sparkles; pulse adds a gentle flash.',Chaos:'Low, body, bright, and pulse all move the image.'};
let vibeAudio={
  active:false,
  noise:.014,
  typical:.11,
  bandNoise:{low:.025,body:.018,bright:.012},
  bandBase:{low:.03,body:.025,bright:.018},
  baseReady:false,
  pulseFast:.02,
  pulseSlow:.02,
  env:{energy:0,low:0,body:0,bright:0,pulse:0},
  calibration:null
};
function clamp01(v){return Math.max(0,Math.min(1,Number(v)||0))}
function micSupported(){return !!(window.isSecureContext&&navigator.mediaDevices&&navigator.mediaDevices.getUserMedia)}
function updateMicNotice(){if(micStream){micNotice.textContent="Phone microphone is live. Vibe ignores the learned room floor and reacts to changes above each frequency band's recent normal.";return}micNotice.textContent=micSupported()?"Tap Start Phone Audio and allow microphone access.":"Phone microphone requires the HTTPS controller."}
function averageBand(data,sampleRate,fftSize,lo,hi){const hz=sampleRate/fftSize,first=Math.max(0,Math.floor(lo/hz)),last=Math.min(data.length-1,Math.ceil(hi/hz));let sum=0,count=0;for(let i=first;i<=last;i++){sum+=data[i];count++}return count?sum/count/255:0}
function setMeters(energy,low,body,bright,pulse){volumeBar.style.height=(clamp01(energy)*100)+"%";bassBar.style.height=(clamp01(low)*100)+"%";midsBar.style.height=(clamp01(body)*100)+"%";highsBar.style.height=(clamp01(bright)*100)+"%";beatLamp.classList.toggle("on",!!pulse)}
function setStatus(kind,title,detail){calStatus.classList.toggle('active',kind==='active');calStatus.classList.toggle('silent',kind==='silent');calibrationState.textContent=title;calibrationDetail.textContent=detail}
async function previewVibe(kind){
  if(micStream)return;
  const frames={low:{volume:.65,bass:.95,mids:0,highs:0,beat:false},pulse:{volume:.7,bass:.55,mids:0,highs:0,beat:true},body:{volume:.65,bass:0,mids:.95,highs:0,beat:false},bright:{volume:.65,bass:0,mids:0,highs:.95,beat:false}};
  if(!frames[kind])return;
  clearTimeout(vibePreviewTimer);const serial=++vibePreviewSerial;
  if(!vibePreviewTimer)vibePreviewWasEnabled=!!(state.reactive||{}).enabled;
  vibePreviewTimer=-1;
  if(!vibePreviewWasEnabled)await cmd('reactive_enabled',true);
  if(serial!==vibePreviewSerial||micStream)return;
  await cmd('audio_frame',frames[kind]);
  if(serial!==vibePreviewSerial||micStream)return;
  setMeters(frames[kind].volume,frames[kind].bass,frames[kind].mids,frames[kind].highs,frames[kind].beat);
  vibePreviewTimer=setTimeout(async()=>{
    if(serial!==vibePreviewSerial||micStream)return;
    await cmd('audio_frame',{volume:0,bass:0,mids:0,highs:0,beat:false});
    if(serial!==vibePreviewSerial||micStream)return;
    if(!vibePreviewWasEnabled)await cmd('reactive_enabled',false);
    if(serial===vibePreviewSerial){vibePreviewTimer=null;setMeters(0,0,0,0,false)}
  },650);
}
function beginCalibration(){
  if(!micStream){setStatus('silent','Waiting for mic','Start audio before resetting the room floor.');return}
  const now=performance.now();
  vibeAudio.calibration={start:now,duration:1800,samples:0,minRms:1,minLow:1,minBody:1,minBright:1};
  vibeAudio.active=false;vibeAudio.baseReady=false;vibeAudio.pulseFast=.02;vibeAudio.pulseSlow=.02;vibeAudio.env={energy:0,low:0,body:0,bright:0,pulse:0};pulseLatch=false;signalHistory=[];
  setMeters(0,0,0,0,false);setStatus('silent','Learning room floor…','About 2 seconds. A quieter moment gives the cleanest gate, but it will keep adapting afterward.');
  cmd('audio_frame',{volume:0,bass:0,mids:0,highs:0,beat:false});
}
function finishCalibration(){
  const c=vibeAudio.calibration;if(!c||!c.samples)return;
  vibeAudio.noise=Math.max(.004,Math.min(.08,c.minRms*1.55));
  vibeAudio.bandNoise.low=Math.max(.002,Math.min(.35,c.minLow*1.18));
  vibeAudio.bandNoise.body=Math.max(.002,Math.min(.30,c.minBody*1.18));
  vibeAudio.bandNoise.bright=Math.max(.002,Math.min(.25,c.minBright*1.18));
  vibeAudio.typical=Math.max(vibeAudio.noise*2.8,.08);
  vibeAudio.calibration=null;vibeAudio.baseReady=false;
}
function updateCalibration(rms,low,body,bright){
  const c=vibeAudio.calibration;if(!c)return false;
  c.samples++;c.minRms=Math.min(c.minRms,rms);c.minLow=Math.min(c.minLow,low);c.minBody=Math.min(c.minBody,body);c.minBright=Math.min(c.minBright,bright);
  const remain=Math.max(0,Math.ceil((c.duration-(performance.now()-c.start))/1000));
  calibrationDetail.textContent=`Learning the quiet floor… ${remain}s`;
  if(performance.now()-c.start>=c.duration)finishCalibration();
  return true;
}
function updateNoiseFloor(rms,rawLow,rawBody,rawBright){
  const a=vibeAudio;
  if(a.active)return;
  const down=rms<a.noise?0.045:0.0012;
  a.noise+=(Math.min(rms,a.noise*1.35)-a.noise)*down;
  function follow(key,value){const current=a.bandNoise[key],rate=value<current?0.035:0.001;a.bandNoise[key]+=(Math.min(value,current*1.45)-current)*rate}
  follow('low',rawLow);follow('body',rawBody);follow('bright',rawBright)
}
function followBaseline(base,value){if(!Number.isFinite(base)||base<=.0001)return Math.max(.002,value);const rate=value<base?.018:.0025;return base+(value-base)*rate}
function novelty(value,base){const dead=Math.max(.006,base*.12),span=Math.max(.018,base*.62);return clamp01((value-base-dead)/span)}
function envelope(current,target,attack,release){return current+(target-current)*(target>current?attack:release)}
function fitCanvas(c){const dpr=Math.min(2,window.devicePixelRatio||1),w=Math.max(280,c.clientWidth),h=Math.max(80,c.clientHeight);if(c.width!==Math.floor(w*dpr)||c.height!==Math.floor(h*dpr)){c.width=Math.floor(w*dpr);c.height=Math.floor(h*dpr)}const ctx=c.getContext('2d');ctx.setTransform(dpr,0,0,dpr,0,0);return [ctx,w,h]}
function drawWave(td){let [ctx,w,h]=fitCanvas(waveformCanvas);ctx.clearRect(0,0,w,h);ctx.strokeStyle='#5ee7ff';ctx.lineWidth=1.5;ctx.beginPath();for(let i=0;i<td.length;i++){let x=i/(td.length-1)*w,y=(td[i]/255)*h;if(i===0)ctx.moveTo(x,y);else ctx.lineTo(x,y)}ctx.stroke();ctx.strokeStyle='#ffffff18';ctx.beginPath();ctx.moveTo(0,h/2);ctx.lineTo(w,h/2);ctx.stroke()}
function freqX(hz,maxHz,w){const min=20,max=Math.max(10000,maxHz);return Math.log(Math.max(min,hz)/min)/Math.log(max/min)*w}
function drawSpectrum(freq,sr,fft){let [ctx,w,h]=fitCanvas(spectrumCanvas);ctx.clearRect(0,0,w,h);const maxHz=Math.min(12000,sr/2);[[35,180,'#866cff16'],[180,2200,'#ff58c816'],[2200,9000,'#ffd34f12']].forEach(([a,b,c])=>{ctx.fillStyle=c;ctx.fillRect(freqX(a,maxHz,w),0,freqX(Math.min(b,maxHz),maxHz,w)-freqX(a,maxHz,w),h)});ctx.strokeStyle='#8df2ff';ctx.lineWidth=1.2;ctx.beginPath();let hzPer=sr/fft;for(let i=1;i<freq.length;i++){let hz=i*hzPer;if(hz>maxHz)break;let x=freqX(hz,maxHz,w),y=h-(freq[i]/255)*h;if(i===1)ctx.moveTo(x,y);else ctx.lineTo(x,y)}ctx.stroke()}
function drawSignalHistory(energy,low,body,bright,pulse){
  signalHistory.push({energy,low,body,bright,pulse:pulse?1:0});if(signalHistory.length>180)signalHistory.shift();
  let [ctx,w,h]=fitCanvas(signalCanvas);ctx.clearRect(0,0,w,h);
  for(let q=.25;q<1;q+=.25){ctx.strokeStyle='#ffffff10';ctx.beginPath();ctx.moveTo(0,h*(1-q));ctx.lineTo(w,h*(1-q));ctx.stroke()}
  function line(key,color){ctx.strokeStyle=color;ctx.lineWidth=1.5;ctx.beginPath();signalHistory.forEach((p,i)=>{let x=i/Math.max(1,signalHistory.length-1)*w,y=h-clamp01(p[key])*(h-4)-2;if(i===0)ctx.moveTo(x,y);else ctx.lineTo(x,y)});ctx.stroke()}
  line('energy','#ffffff');line('low','#866cff');line('body','#ff58c8');line('bright','#ffd34f');
  signalHistory.forEach((p,i)=>{if(p.pulse){let x=i/Math.max(1,signalHistory.length-1)*w;ctx.strokeStyle='#64ff86';ctx.beginPath();ctx.moveTo(x,0);ctx.lineTo(x,h);ctx.stroke()}})
}
function audioLoop(ts){
  if(!analyser)return;
  const freq=new Uint8Array(analyser.frequencyBinCount),td=new Uint8Array(analyser.fftSize);
  analyser.getByteFrequencyData(freq);analyser.getByteTimeDomainData(td);
  let sq=0;for(let i=0;i<td.length;i++){let s=(td[i]-128)/128;sq+=s*s}
  const sr=audioContext.sampleRate,fft=analyser.fftSize,gain=+inputGain.value;
  const rms=Math.sqrt(sq/td.length)*gain;
  const rawLow=(averageBand(freq,sr,fft,35,90)*.58+averageBand(freq,sr,fft,90,180)*.42)*gain;
  const rawBody=averageBand(freq,sr,fft,180,2200)*gain;
  const rawBright=averageBand(freq,sr,fft,2200,9000)*gain;
  const calibrating=updateCalibration(rms,rawLow,rawBody,rawBright);
  if(!calibrating){
    const enter=Math.max(.012,vibeAudio.noise*2.15),leave=Math.max(.008,vibeAudio.noise*1.5);
    if(!vibeAudio.active&&rms>enter)vibeAudio.active=true;
    else if(vibeAudio.active&&rms<leave)vibeAudio.active=false;
    updateNoiseFloor(rms,rawLow,rawBody,rawBright);
    if(vibeAudio.active){
      vibeAudio.typical+=(rms-vibeAudio.typical)*(rms<vibeAudio.typical?.008:.003);
      vibeAudio.typical=Math.max(enter*1.45,vibeAudio.typical);
      const energyTarget=clamp01((rms-enter)/Math.max(.025,(vibeAudio.typical-enter)*1.55));
      const low=Math.max(0,rawLow-vibeAudio.bandNoise.low),body=Math.max(0,rawBody-vibeAudio.bandNoise.body),bright=Math.max(0,rawBright-vibeAudio.bandNoise.bright);
      if(!vibeAudio.baseReady){vibeAudio.bandBase={low:Math.max(.004,low),body:Math.max(.004,body),bright:Math.max(.004,bright)};vibeAudio.baseReady=true}
      const lowTarget=novelty(low,vibeAudio.bandBase.low),bodyTarget=novelty(body,vibeAudio.bandBase.body),brightTarget=novelty(bright,vibeAudio.bandBase.bright);
      vibeAudio.bandBase.low=followBaseline(vibeAudio.bandBase.low,low);vibeAudio.bandBase.body=followBaseline(vibeAudio.bandBase.body,body);vibeAudio.bandBase.bright=followBaseline(vibeAudio.bandBase.bright,bright);
      vibeAudio.pulseFast=vibeAudio.pulseFast*.54+low*.46;vibeAudio.pulseSlow=vibeAudio.pulseSlow*.968+low*.032;
      const sensitivity=+beatSensitivity.value,ratio=1.52-sensitivity*.30,deltaFloor=Math.max(.006,vibeAudio.pulseSlow*(.28-sensitivity*.12)),now=performance.now();
      const pulse=vibeAudio.env.energy>.05&&vibeAudio.pulseFast>vibeAudio.pulseSlow*ratio&&(vibeAudio.pulseFast-vibeAudio.pulseSlow)>deltaFloor&&now-lastBeatTime>(260-sensitivity*70);
      if(pulse){lastBeatTime=now;pulseLatch=true}
      vibeAudio.env.energy=envelope(vibeAudio.env.energy,energyTarget,.28,.065);
      vibeAudio.env.low=envelope(vibeAudio.env.low,lowTarget,.48,.11);
      vibeAudio.env.body=envelope(vibeAudio.env.body,bodyTarget,.34,.075);
      vibeAudio.env.bright=envelope(vibeAudio.env.bright,brightTarget,.45,.10);
      vibeAudio.env.pulse=pulse?1:vibeAudio.env.pulse*.72;
      setStatus('active','Music active',`Gate ${leave.toFixed(3)}–${enter.toFixed(3)} · baselines adapt slowly`);
    }else{
      vibeAudio.env={energy:0,low:0,body:0,bright:0,pulse:0};vibeAudio.baseReady=false;vibeAudio.pulseFast*=.82;vibeAudio.pulseSlow*=.90;pulseLatch=false;
      setStatus('silent','Silent — gate closed',`Noise ${vibeAudio.noise.toFixed(3)} · waiting for meaningful audio`);
    }
  }else{
    vibeAudio.env={energy:0,low:0,body:0,bright:0,pulse:0};pulseLatch=false;
  }
  const e=vibeAudio.env;
  setMeters(e.energy,e.low,e.body,e.bright,e.pulse>.35);
  rmsValue.textContent=rms.toFixed(3);noiseValue.textContent=vibeAudio.noise.toFixed(3);lowBaseValue.textContent=vibeAudio.bandBase.low.toFixed(3);brightBaseValue.textContent=vibeAudio.bandBase.bright.toFixed(3);
  if(waveformCanvas.offsetParent!==null){drawWave(td);drawSpectrum(freq,sr,fft);drawSignalHistory(e.energy,e.low,e.body,e.bright,e.pulse>.35)}
  if(ts-lastAudioSend>110){
    lastAudioSend=ts;
    const pulse=pulseLatch;
    cmd('audio_frame',{volume:e.energy,bass:e.low,mids:e.body,highs:e.bright,beat:pulse});
    pulseLatch=false;
  }
  audioAnimation=requestAnimationFrame(audioLoop)
}
async function startMic(){if(!micSupported()){updateMicNotice();return}try{micStream=await navigator.mediaDevices.getUserMedia({audio:{echoCancellation:false,noiseSuppression:false,autoGainControl:false},video:false});clearTimeout(vibePreviewTimer);vibePreviewTimer=null;vibePreviewSerial++;audioContext=new(window.AudioContext||window.webkitAudioContext)();await audioContext.resume();analyser=audioContext.createAnalyser();analyser.fftSize=2048;analyser.smoothingTimeConstant=.16;analyser.minDecibels=-90;analyser.maxDecibels=-10;audioContext.createMediaStreamSource(micStream).connect(analyser);micButton.textContent='■ STOP PHONE AUDIO';micButton.classList.add('active');analyzerLive.textContent='● ANALYZING';cmd('reactive_enabled',true);updateMicNotice();beginCalibration();audioAnimation=requestAnimationFrame(audioLoop)}catch(e){micNotice.textContent='Microphone could not start: '+e.message;micStream=null}}
function stopMic(){if(audioAnimation)cancelAnimationFrame(audioAnimation);audioAnimation=null;if(micStream)micStream.getTracks().forEach(t=>t.stop());micStream=null;if(audioContext)audioContext.close();audioContext=null;analyser=null;pulseLatch=false;vibeAudio.active=false;vibeAudio.env={energy:0,low:0,body:0,bright:0,pulse:0};setMeters(0,0,0,0,false);setStatus('silent','Mic off','Start audio when you want Vibe to react.');cmd('audio_frame',{volume:0,bass:0,mids:0,highs:0,beat:false});micButton.textContent='🎙 START PHONE AUDIO';micButton.classList.remove('active');analyzerLive.textContent='MIC OFF';cmd('reactive_enabled',false);updateMicNotice()}
function toggleMic(){micStream?stopMic():startMic()}
function renderPresets(){const presets=state.reactive_presets||[],sig=presets.join('|');if(presetButtons.dataset.sig!==sig){presetButtons.dataset.sig=sig;presetButtons.innerHTML='';presets.forEach(n=>{let b=document.createElement('button');b.dataset.preset=n;b.textContent=n;b.onclick=()=>cmd('reactive_preset',n);presetButtons.appendChild(b)})}const r=state.reactive||{};document.querySelectorAll('[data-preset]').forEach(b=>b.classList.toggle('active',b.dataset.preset===r.preset));vibePresetHint.textContent=vibePresetDescriptions[r.preset]||'Custom signal mapping.'}
function syncAudioUI(){if(typeof state==='undefined')return;const r=state.reactive||{};sync('reactiveStrength',r.strength);num('reactiveStrengthValue',r.strength||0,'x');renderPresets();if(!micStream&&state.audio)setMeters(state.audio.volume||0,state.audio.bass||0,state.audio.mids||0,state.audio.highs||0,state.audio.beat||false)}
updateMicNotice();setInterval(syncAudioUI,300);
"""


def enhanced_html(source):
    html=source.replace("</head>",AUDIO_CSS+"\n</head>",1)
    html=html.replace('<button id="tabEdit" onclick="view(\'edit\')">Edit</button>',AUDIO_TAB+'<button id="tabEdit" onclick="view(\'edit\')">Edit</button>',1)
    html=html.replace('<section id="edit" class="view">',AUDIO_SECTION+'\n<section id="edit" class="view">',1)
    html=html.replace('["live","library","edit"]','["live","library","audio","edit"]')
    html=html.replace('<input id="zoom" type="range" min="1" max="5" step=".05"','<input id="zoom" type="range" min=".55" max="5" step=".05"',1)
    html=html.replace('<span>Crop X</span>','<span>Position X</span>').replace('<span>Crop Y</span>','<span>Position Y</span>')
    html=html.replace('async function update(){',AUDIO_JS+'\nasync function update(){',1)
    return html


def apply(html):
    return enhanced_html(html)


PhoneControlServer=phone_server.PhoneControlServer
