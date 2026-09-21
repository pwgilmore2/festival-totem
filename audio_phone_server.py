import phone_server

AUDIO_CSS = r"""
<style>
.audioStart{width:100%;min-height:66px;font-size:18px;background:linear-gradient(135deg,#635bff,#00b8ff);box-shadow:0 8px 24px #0006}.audioStart.active{background:linear-gradient(135deg,#ff315f,#ff8a24)}
.audioMeters{display:grid;grid-template-columns:repeat(4,1fr);gap:6px;margin-top:10px}.audioMeter{background:#1d1d26;border-radius:10px;padding:8px 6px;text-align:center}.audioBar{height:62px;background:#0e0e14;border-radius:7px;overflow:hidden;position:relative}.audioFill{position:absolute;left:0;right:0;bottom:0;height:0;background:linear-gradient(#8b7cff,#56d5ff);transition:height .05s linear}.audioLabel{margin-top:5px;font-size:11px;opacity:.65}
.beatLamp{margin-top:10px;height:12px;border-radius:999px;background:#22222c}.beatLamp.on{background:#fff;box-shadow:0 0 18px #fff}.audioNotice{margin-top:10px;padding:10px;border-radius:11px;background:#ffffff0c;font-size:12px;line-height:1.4}.presetGrid{display:grid;grid-template-columns:repeat(4,1fr);gap:7px}.tuningGrid{display:grid;grid-template-columns:1fr 1fr;gap:7px 12px}.tuningGrid .slider{margin:4px 0}
.analyzerCanvas{display:block;width:100%;height:112px;background:#080811;border:1px solid #ffffff18;border-radius:12px;margin:7px 0 12px}.spectrogramCanvas{height:132px}.beatReadout{display:grid;grid-template-columns:repeat(4,1fr);gap:7px;margin:8px 0}.beatStat{background:#ffffff0b;border-radius:10px;padding:8px;text-align:center}.beatStat b{display:block;font-size:17px}.beatStat span{font-size:10px;opacity:.6}.analyzerTitle{display:flex;align-items:center;justify-content:space-between;gap:10px}.analyzerTitle .liveDot{font-size:11px;opacity:.65}.bandKey{display:flex;gap:10px;flex-wrap:wrap;font-size:10px;opacity:.72;margin-top:-5px;margin-bottom:8px}.bandKey i{width:8px;height:8px;border-radius:50%;display:inline-block;margin-right:3px}
@media(max-width:520px){.tuningGrid{grid-template-columns:1fr}.presetGrid{grid-template-columns:repeat(2,1fr)}.beatReadout{grid-template-columns:repeat(2,1fr)}}
</style>
"""

AUDIO_TAB = r"""<button id="tabAudio" onclick="view('audio')">Audio</button>"""

AUDIO_SECTION = r"""
<section id="audio" class="view">
<div class="card">
<h2>Phone Audio</h2>
<button id="micButton" class="audioStart" onclick="toggleMic()">🎙 START PHONE AUDIO</button>
<div id="micNotice" class="audioNotice">Checking microphone support...</div>
<div class="audioMeters">
<div class="audioMeter"><div class="audioBar"><div id="volumeBar" class="audioFill"></div></div><div class="audioLabel">Volume</div></div>
<div class="audioMeter"><div class="audioBar"><div id="bassBar" class="audioFill"></div></div><div class="audioLabel">Bass</div></div>
<div class="audioMeter"><div class="audioBar"><div id="midsBar" class="audioFill"></div></div><div class="audioLabel">Mids</div></div>
<div class="audioMeter"><div class="audioBar"><div id="highsBar" class="audioFill"></div></div><div class="audioLabel">Highs</div></div>
</div><div id="beatLamp" class="beatLamp"></div>
</div>

<div class="card">
<div class="analyzerTitle"><h2>Audio Analyzer</h2><div id="analyzerLive" class="liveDot">MIC OFF</div></div>
<div class="audioLabel">Waveform</div><canvas id="waveformCanvas" class="analyzerCanvas"></canvas>
<div class="audioLabel">Frequency Spectrum</div><canvas id="spectrumCanvas" class="analyzerCanvas"></canvas>
<div class="bandKey"><span><i style="background:#43d6ff"></i>Beat pickup</span><span><i style="background:#866cff"></i>Bass</span><span><i style="background:#ff58c8"></i>Mids</span><span><i style="background:#ffd34f"></i>Highs</span></div>
<div class="audioLabel">Spectrogram — newest audio on the right</div><canvas id="spectrogramCanvas" class="analyzerCanvas spectrogramCanvas"></canvas>
<div class="audioLabel">Beat detector history</div><canvas id="beatCanvas" class="analyzerCanvas"></canvas>
<div class="beatReadout">
<div class="beatStat"><b id="beatEnergyValue">0.000</b><span>BEAT ENERGY</span></div>
<div class="beatStat"><b id="fastValue">0.000</b><span>FAST</span></div>
<div class="beatStat"><b id="slowValue">0.000</b><span>BASELINE</span></div>
<div class="beatStat"><b id="confidenceValue">0%</b><span>CONFIDENCE</span></div>
</div>
</div>

<div class="card">
<h2>Beat Pickup</h2>
<div class="tuningGrid">
<div class="slider"><div class="sh"><span>Beat low</span><span id="beatLowValue">40 Hz</span></div><input id="beatLow" type="range" min="25" max="180" step="5" value="40" oninput="beatLowValue.textContent=this.value+' Hz';if(+this.value>=+beatHigh.value)beatHigh.value=+this.value+20"></div>
<div class="slider"><div class="sh"><span>Beat high</span><span id="beatHighValue">160 Hz</span></div><input id="beatHigh" type="range" min="60" max="320" step="5" value="160" oninput="beatHighValue.textContent=this.value+' Hz';if(+this.value<=+beatLow.value)beatLow.value=+this.value-20"></div>
<div class="slider"><div class="sh"><span>Beat trigger</span><span id="beatThresholdValue">1.28x</span></div><input id="beatThreshold" type="range" min="1.03" max="2.2" step=".01" value="1.28" oninput="num('beatThresholdValue',this.value,'x')"></div>
<div class="slider"><div class="sh"><span>Noise floor</span><span id="noiseFloorValue">0.035</span></div><input id="noiseFloor" type="range" min=".005" max=".20" step=".005" value=".035" oninput="document.getElementById('noiseFloorValue').textContent=parseFloat(this.value).toFixed(3)"></div>
<div class="slider"><div class="sh"><span>Fast response</span><span id="fastResponseValue">45%</span></div><input id="fastResponse" type="range" min=".05" max=".9" step=".05" value=".45" oninput="pct('fastResponseValue',this.value)"></div>
<div class="slider"><div class="sh"><span>Baseline response</span><span id="slowResponseValue">3%</span></div><input id="slowResponse" type="range" min=".005" max=".18" step=".005" value=".03" oninput="pct('slowResponseValue',this.value)"></div>
<div class="slider"><div class="sh"><span>Cooldown</span><span id="cooldownValue">180 ms</span></div><input id="cooldown" type="range" min="90" max="600" step="10" value="180" oninput="cooldownValue.textContent=this.value+' ms'"></div>
<div class="slider"><div class="sh"><span>FFT smoothing</span><span id="smoothingValue">45%</span></div><input id="smoothing" type="range" min="0" max=".9" step=".05" value=".45" oninput="pct('smoothingValue',this.value);if(analyser)analyser.smoothingTimeConstant=parseFloat(this.value)"></div>
</div>
<button style="width:100%" onclick="resetBandState()">Reset Analyzer Calibration</button>
<div class="audioNotice">Tune the cyan beat-pickup band around the kick. Lower <b>Beat trigger</b> to make detection easier. Faster <b>Fast response</b> catches sharper kicks; slower <b>Baseline response</b> keeps the reference from chasing each hit.</div>
</div>

<div class="card" id="reactiveMappingCard">
<h2>Sound → Visuals</h2>
<div class="slider"><div class="sh"><span>Overall intensity</span><span id="reactiveStrengthValue"></span></div><input id="reactiveStrength" type="range" min="0" max="1.5" step=".05" oninput="num('reactiveStrengthValue',this.value,'x');range('reactive_strength',this.value)"></div>
<div id="presetButtons" class="presetGrid"></div>
<div id="reactiveLayerMount"></div>
</div>
</section>
"""

AUDIO_JS = r"""
let audioContext=null,analyser=null,micStream=null,audioAnimation=null,lastAudioSend=0,lastBeatTime=0;
let bandState={bass:{floor:.02,ceiling:.28},mids:{floor:.02,ceiling:.24},highs:{floor:.01,ceiling:.18}};
let beatFast=.05,beatSlow=.05,beatHistory=[],spectrogramImage=null;
function micSupported(){return !!(window.isSecureContext&&navigator.mediaDevices&&navigator.mediaDevices.getUserMedia)}
function updateMicNotice(){if(micStream){micNotice.textContent="Phone microphone is live. Reactive visuals are enabled automatically; analyzer rendering stays on this phone.";return}micNotice.textContent=micSupported()?"Tap Start Phone Audio and allow microphone access.":"Phone microphone requires the HTTPS controller."}
function averageBand(data,sampleRate,fftSize,lo,hi){const hz=sampleRate/fftSize,first=Math.max(0,Math.floor(lo/hz)),last=Math.min(data.length-1,Math.ceil(hi/hz));let sum=0,count=0;for(let i=first;i<=last;i++){sum+=data[i];count++}return count?sum/count/255:0}
function normBand(v,name){const s=bandState[name];s.floor=Math.min(s.floor*.995+v*.005,v);s.ceiling=Math.max(s.ceiling*.992+v*.008,v);if(s.ceiling-s.floor<.06)s.ceiling=s.floor+.06;return Math.max(0,Math.min(1,(v-s.floor)/(s.ceiling-s.floor)))}
function resetBandState(){bandState={bass:{floor:.02,ceiling:.28},mids:{floor:.02,ceiling:.24},highs:{floor:.01,ceiling:.18}};beatFast=.05;beatSlow=.05;beatHistory=[]}
function setMeters(v,b,m,h,beat){volumeBar.style.height=(v*100)+"%";bassBar.style.height=(b*100)+"%";midsBar.style.height=(m*100)+"%";highsBar.style.height=(h*100)+"%";beatLamp.classList.toggle("on",beat)}
function fitCanvas(c){const dpr=Math.min(2,window.devicePixelRatio||1),w=Math.max(280,c.clientWidth),h=Math.max(80,c.clientHeight);if(c.width!==Math.floor(w*dpr)||c.height!==Math.floor(h*dpr)){c.width=Math.floor(w*dpr);c.height=Math.floor(h*dpr)}const ctx=c.getContext('2d');ctx.setTransform(dpr,0,0,dpr,0,0);return [ctx,w,h]}
function drawWave(td){let [ctx,w,h]=fitCanvas(waveformCanvas);ctx.clearRect(0,0,w,h);ctx.strokeStyle='#5ee7ff';ctx.lineWidth=1.5;ctx.beginPath();for(let i=0;i<td.length;i++){let x=i/(td.length-1)*w,y=(td[i]/255)*h;if(i===0)ctx.moveTo(x,y);else ctx.lineTo(x,y)}ctx.stroke();ctx.strokeStyle='#ffffff18';ctx.beginPath();ctx.moveTo(0,h/2);ctx.lineTo(w,h/2);ctx.stroke()}
function freqX(hz,maxHz,w){const min=20,max=Math.max(10000,maxHz);return Math.log(Math.max(min,hz)/min)/Math.log(max/min)*w}
function drawSpectrum(freq,sr,fft){let [ctx,w,h]=fitCanvas(spectrumCanvas);ctx.clearRect(0,0,w,h);const ny=sr/2,maxHz=Math.min(12000,ny);const lo=+beatLow.value,hi=+beatHigh.value;ctx.fillStyle='#43d6ff18';ctx.fillRect(freqX(lo,maxHz,w),0,freqX(hi,maxHz,w)-freqX(lo,maxHz,w),h);[[35,180,'#866cff16'],[180,2200,'#ff58c816'],[2200,9000,'#ffd34f12']].forEach(([a,b,c])=>{ctx.fillStyle=c;ctx.fillRect(freqX(a,maxHz,w),0,freqX(Math.min(b,maxHz),maxHz,w)-freqX(a,maxHz,w),h)});ctx.strokeStyle='#8df2ff';ctx.lineWidth=1.2;ctx.beginPath();let hzPer=sr/fft;for(let i=1;i<freq.length;i++){let hz=i*hzPer;if(hz>maxHz)break;let x=freqX(hz,maxHz,w),y=h-(freq[i]/255)*h;if(i===1)ctx.moveTo(x,y);else ctx.lineTo(x,y)}ctx.stroke();ctx.fillStyle='#ffffff88';ctx.font='10px sans-serif';[40,80,160,320,1000,3000,8000].forEach(hz=>{if(hz<maxHz)ctx.fillText(hz>=1000?(hz/1000)+'k':hz,freqX(hz,maxHz,w)+2,h-4)})}
function drawSpectrogram(freq,sr,fft){let [ctx,w,h]=fitCanvas(spectrogramCanvas);let dpr=Math.min(2,window.devicePixelRatio||1),pxW=spectrogramCanvas.width,pxH=spectrogramCanvas.height;if(!spectrogramImage||spectrogramImage.width!==pxW||spectrogramImage.height!==pxH){ctx.clearRect(0,0,w,h);spectrogramImage={width:pxW,height:pxH}}ctx.drawImage(spectrogramCanvas,-1,0,w,h);let maxHz=Math.min(10000,sr/2),hzPer=sr/fft;for(let y=0;y<Math.floor(h);y++){let norm=1-y/Math.max(1,h-1),hz=20*Math.pow(maxHz/20,norm),bin=Math.max(0,Math.min(freq.length-1,Math.round(hz/hzPer))),v=freq[bin]/255;let hue=245-v*200,light=8+v*58;ctx.fillStyle=`hsl(${hue} 95% ${light}%)`;ctx.fillRect(w-1,y,1,1)}}
function drawBeatHistory(raw,fast,slow,threshold,beat){beatHistory.push({raw,fast,slow,trigger:Math.max(+noiseFloor.value,slow*threshold),beat});if(beatHistory.length>180)beatHistory.shift();let [ctx,w,h]=fitCanvas(beatCanvas);ctx.clearRect(0,0,w,h);let max=.001;beatHistory.forEach(p=>max=Math.max(max,p.raw,p.fast,p.slow,p.trigger));function line(key,color){ctx.strokeStyle=color;ctx.lineWidth=1.4;ctx.beginPath();beatHistory.forEach((p,i)=>{let x=i/Math.max(1,beatHistory.length-1)*w,y=h-(p[key]/max)*(h-8)-4;if(i===0)ctx.moveTo(x,y);else ctx.lineTo(x,y)});ctx.stroke()}line('raw','#43d6ff');line('fast','#ffffff');line('slow','#ff58c8');line('trigger','#ffd34f');beatHistory.forEach((p,i)=>{if(p.beat){let x=i/Math.max(1,beatHistory.length-1)*w;ctx.strokeStyle='#64ff86';ctx.beginPath();ctx.moveTo(x,0);ctx.lineTo(x,h);ctx.stroke()}})}
function audioLoop(ts){if(!analyser)return;const freq=new Uint8Array(analyser.frequencyBinCount),td=new Uint8Array(analyser.fftSize);analyser.getByteFrequencyData(freq);analyser.getByteTimeDomainData(td);let sq=0;for(let i=0;i<td.length;i++){let s=(td[i]-128)/128;sq+=s*s}const sr=audioContext.sampleRate,fft=analyser.fftSize,sens=1;const volume=Math.min(1,Math.sqrt(sq/td.length)*2.8);const sub=averageBand(freq,sr,fft,35,90),low=averageBand(freq,sr,fft,90,180),rawBass=sub*.62+low*.38;const rawMids=averageBand(freq,sr,fft,180,2200),rawHighs=averageBand(freq,sr,fft,2200,9000);const bass=normBand(rawBass,'bass'),mids=normBand(rawMids,'mids'),highs=normBand(rawHighs,'highs');const rawBeat=averageBand(freq,sr,fft,+beatLow.value,+beatHigh.value);const fastMix=+fastResponse.value,slowMix=+slowResponse.value;beatFast=beatFast*(1-fastMix)+rawBeat*fastMix;beatSlow=beatSlow*(1-slowMix)+rawBeat*slowMix;const threshold=+beatThreshold.value,trigger=Math.max(+noiseFloor.value,beatSlow*threshold),now=performance.now();const confidence=Math.max(0,Math.min(2,beatFast/Math.max(.0001,trigger)));const beat=beatFast>trigger&&(beatFast-beatSlow)>.004&&now-lastBeatTime>+cooldown.value;if(beat)lastBeatTime=now;setMeters(volume,bass,mids,highs,beat);beatEnergyValue.textContent=rawBeat.toFixed(3);fastValue.textContent=beatFast.toFixed(3);slowValue.textContent=beatSlow.toFixed(3);confidenceValue.textContent=Math.round(Math.min(1,confidence)*100)+'%';drawWave(td);drawSpectrum(freq,sr,fft);drawSpectrogram(freq,sr,fft);drawBeatHistory(rawBeat,beatFast,beatSlow,threshold,beat);if(ts-lastAudioSend>110){lastAudioSend=ts;cmd('audio_frame',{volume,bass,mids,highs,beat})}audioAnimation=requestAnimationFrame(audioLoop)}
async function startMic(){if(!micSupported()){updateMicNotice();return}try{micStream=await navigator.mediaDevices.getUserMedia({audio:{echoCancellation:false,noiseSuppression:false,autoGainControl:false},video:false});audioContext=new(window.AudioContext||window.webkitAudioContext)();await audioContext.resume();analyser=audioContext.createAnalyser();analyser.fftSize=2048;analyser.smoothingTimeConstant=+smoothing.value;audioContext.createMediaStreamSource(micStream).connect(analyser);resetBandState();micButton.textContent='■ STOP PHONE AUDIO';micButton.classList.add('active');analyzerLive.textContent='● ANALYZING';cmd('reactive_enabled',true);updateMicNotice();audioAnimation=requestAnimationFrame(audioLoop)}catch(e){micNotice.textContent='Microphone could not start: '+e.message;micStream=null}}
function stopMic(){if(audioAnimation)cancelAnimationFrame(audioAnimation);audioAnimation=null;if(micStream)micStream.getTracks().forEach(t=>t.stop());micStream=null;if(audioContext)audioContext.close();audioContext=null;analyser=null;micButton.textContent='🎙 START PHONE AUDIO';micButton.classList.remove('active');analyzerLive.textContent='MIC OFF';cmd('reactive_enabled',false);updateMicNotice()}
function toggleMic(){micStream?stopMic():startMic()}
function renderPresets(){const presets=state.reactive_presets||[],sig=presets.join('|');if(presetButtons.dataset.sig!==sig){presetButtons.dataset.sig=sig;presetButtons.innerHTML='';presets.forEach(n=>{let b=document.createElement('button');b.dataset.preset=n;b.textContent=n;b.onclick=()=>cmd('reactive_preset',n);presetButtons.appendChild(b)})}const r=state.reactive||{};document.querySelectorAll('[data-preset]').forEach(b=>b.classList.toggle('active',b.dataset.preset===r.preset))}
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

phone_server.PHONE_HTML=enhanced_html(phone_server.PHONE_HTML)
PhoneControlServer=phone_server.PhoneControlServer
