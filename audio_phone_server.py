import phone_server

AUDIO_CSS = r"""
<style>
.audioMeters{display:grid;grid-template-columns:repeat(4,1fr);gap:6px;margin-top:10px}
.audioMeter{background:#1d1d26;border-radius:10px;padding:8px 6px;text-align:center}
.audioBar{height:70px;background:#0e0e14;border-radius:7px;overflow:hidden;position:relative}
.audioFill{position:absolute;left:0;right:0;bottom:0;height:0;background:linear-gradient(#8b7cff,#56d5ff);transition:height .06s linear}
.audioLabel{margin-top:5px;font-size:11px;opacity:.65}
.beatLamp{margin-top:10px;height:11px;border-radius:999px;background:#22222c}
.beatLamp.on{background:#fff;box-shadow:0 0 16px #fff}
.audioNotice{margin-top:10px;padding:10px;border-radius:11px;background:#ffffff0c;font-size:12px;line-height:1.35}
.presetGrid{display:grid;grid-template-columns:repeat(2,1fr);gap:7px}
.tuningGrid{display:grid;grid-template-columns:1fr 1fr;gap:8px 12px}
.tuningGrid .slider{margin:4px 0}
@media(max-width:520px){.tuningGrid{grid-template-columns:1fr}}
</style>
"""

AUDIO_TAB = r"""
<button id="tabAudio" onclick="view('audio')">Audio</button>
"""

AUDIO_SECTION = r"""
<section id="audio" class="view">
<div class="card">
<h2>Audio Input</h2>
<div class="g2">
<button id="micButton" onclick="toggleMic()">Start Phone Mic</button>
<button id="demoButton" onclick="toggleDemo()">Start Demo Beat</button>
</div>
<div id="micNotice" class="audioNotice">Checking microphone support...</div>
<div class="audioMeters">
<div class="audioMeter"><div class="audioBar"><div id="volumeBar" class="audioFill"></div></div><div class="audioLabel">Volume</div></div>
<div class="audioMeter"><div class="audioBar"><div id="bassBar" class="audioFill"></div></div><div class="audioLabel">Bass</div></div>
<div class="audioMeter"><div class="audioBar"><div id="midsBar" class="audioFill"></div></div><div class="audioLabel">Mids</div></div>
<div class="audioMeter"><div class="audioBar"><div id="highsBar" class="audioFill"></div></div><div class="audioLabel">Highs</div></div>
</div>
<div id="beatLamp" class="beatLamp"></div>
</div>
<div class="card">
<h2>Audio Tuning</h2>
<div class="tuningGrid">
<div class="slider"><div class="sh"><span>Overall</span><span id="sensitivityValue">1.00x</span></div><input id="sensitivity" type="range" min=".25" max="2" step=".05" value="1" oninput="num('sensitivityValue',this.value,'x')"></div>
<div class="slider"><div class="sh"><span>Bass</span><span id="bassGainValue">0.75x</span></div><input id="bassGain" type="range" min=".2" max="1.5" step=".05" value=".75" oninput="num('bassGainValue',this.value,'x')"></div>
<div class="slider"><div class="sh"><span>Mids</span><span id="midGainValue">1.00x</span></div><input id="midGain" type="range" min=".2" max="2" step=".05" value="1" oninput="num('midGainValue',this.value,'x')"></div>
<div class="slider"><div class="sh"><span>Highs</span><span id="highGainValue">1.00x</span></div><input id="highGain" type="range" min=".2" max="2" step=".05" value="1" oninput="num('highGainValue',this.value,'x')"></div>
<div class="slider"><div class="sh"><span>Beat trigger</span><span id="beatThresholdValue">1.30x</span></div><input id="beatThreshold" type="range" min="1.05" max="2.2" step=".05" value="1.30" oninput="num('beatThresholdValue',this.value,'x')"></div>
<div class="slider"><div class="sh"><span>Smoothing</span><span id="smoothingValue">50%</span></div><input id="smoothing" type="range" min="0" max=".95" step=".05" value=".50" oninput="pct('smoothingValue',this.value);if(analyser)analyser.smoothingTimeConstant=parseFloat(this.value)"></div>
</div>
<div class="audioNotice"><b>Beat tuning:</b> lower Beat trigger = easier/more frequent hits. Lower Smoothing = faster/snappier response. Start around <b>1.25–1.35×</b> and <b>45–55%</b> smoothing for EDM, then tune Bass so kick peaks are strong without living at the top.</div>
</div>
<div class="card">
<div class="row"><h2>Reactive Layer</h2><button id="reactiveButton" onclick="toggleReactive()">Off</button></div>
<div class="slider">
<div class="sh"><span>Intensity</span><span id="reactiveStrengthValue"></span></div>
<input id="reactiveStrength" type="range" min="0" max="1.5" step=".05" oninput="num('reactiveStrengthValue',this.value,'x');range('reactive_strength',this.value)">
</div>
<div id="presetButtons" class="presetGrid"></div>
<div class="audioNotice"><b>Pulse</b>: bass zoom + beat flash.<br><b>Neon</b>: mids/highs color shift.<br><b>Spark</b>: high-frequency sparkles.<br><b>Chaos</b>: everything stacked.</div>
</div>
</section>
"""

AUDIO_JS = r"""
let audioContext=null,analyser=null,micStream=null,audioAnimation=null,lastAudioSend=0,lastBeatTime=0,demoTimer=null,demoPhase=0;
let bandState={
 bass:{floor:.02,ceiling:.28},
 mids:{floor:.02,ceiling:.24},
 highs:{floor:.01,ceiling:.18}
};
let bassFast=.10,bassSlow=.10;

function micSupported(){return !!(window.isSecureContext&&navigator.mediaDevices&&navigator.mediaDevices.getUserMedia)}
function updateMicNotice(){
 if(micStream){micNotice.textContent="Phone microphone is live. Audio is analyzed locally; only band/beat values are sent.";return}
 micNotice.textContent=micSupported()
 ?"Microphone access is available. Tap Start Phone Mic and allow permission."
 :"Phone mic needs HTTPS. Demo Beat works now; real phone mic will work once this controller is served securely."
}
function averageBand(data,sampleRate,fftSize,lo,hi){
 const hz=sampleRate/fftSize,first=Math.max(0,Math.floor(lo/hz)),last=Math.min(data.length-1,Math.ceil(hi/hz));let sum=0,count=0;
 for(let i=first;i<=last;i++){sum+=data[i];count++}return count?sum/count/255:0
}
function normBand(v,name){
 const s=bandState[name];
 s.floor=Math.min(s.floor*.995+v*.005,v);
 s.ceiling=Math.max(s.ceiling*.992+v*.008,v);
 if(s.ceiling-s.floor<.06)s.ceiling=s.floor+.06;
 return Math.max(0,Math.min(1,(v-s.floor)/(s.ceiling-s.floor)))
}
function resetBandState(){
 bandState={bass:{floor:.02,ceiling:.28},mids:{floor:.02,ceiling:.24},highs:{floor:.01,ceiling:.18}};
 bassFast=.10;bassSlow=.10
}
function setMeters(v,b,m,h,beat){
 volumeBar.style.height=(v*100)+"%";bassBar.style.height=(b*100)+"%";midsBar.style.height=(m*100)+"%";highsBar.style.height=(h*100)+"%";beatLamp.classList.toggle("on",beat)
}
function audioLoop(ts){
 if(!analyser)return;
 const freq=new Uint8Array(analyser.frequencyBinCount),td=new Uint8Array(analyser.fftSize);
 analyser.getByteFrequencyData(freq);analyser.getByteTimeDomainData(td);
 let sq=0;for(let i=0;i<td.length;i++){let s=(td[i]-128)/128;sq+=s*s}
 const sens=parseFloat(sensitivity.value),bg=parseFloat(bassGain.value),mg=parseFloat(midGain.value),hg=parseFloat(highGain.value),sr=audioContext.sampleRate,fft=analyser.fftSize;
 const volume=Math.min(1,Math.sqrt(sq/td.length)*2.8*sens);
 const sub=averageBand(freq,sr,fft,35,90),low=averageBand(freq,sr,fft,90,180),rawBass=(sub*.62+low*.38)*bg*sens;
 const rawMids=averageBand(freq,sr,fft,180,2200)*mg*sens;
 const rawHighs=averageBand(freq,sr,fft,2200,9000)*hg*sens;
 const bass=normBand(rawBass,"bass"),mids=normBand(rawMids,"mids"),highs=normBand(rawHighs,"highs");
 bassFast=bassFast*.55+bass*.45;bassSlow=bassSlow*.97+bass*.03;
 const now=performance.now(),threshold=parseFloat(beatThreshold.value);
 const onset=bassFast>Math.max(.18,bassSlow*threshold)&&(bassFast-bassSlow)>.035;
 const beat=onset&&now-lastBeatTime>180;if(beat)lastBeatTime=now;
 setMeters(volume,bass,mids,highs,beat);
 if(ts-lastAudioSend>110){lastAudioSend=ts;cmd("audio_frame",{volume,bass,mids,highs,beat})}
 audioAnimation=requestAnimationFrame(audioLoop)
}
async function startMic(){
 if(!micSupported()){updateMicNotice();return}
 try{
  micStream=await navigator.mediaDevices.getUserMedia({audio:{echoCancellation:false,noiseSuppression:false,autoGainControl:false},video:false});
  audioContext=new(window.AudioContext||window.webkitAudioContext)();await audioContext.resume();
  analyser=audioContext.createAnalyser();analyser.fftSize=1024;analyser.smoothingTimeConstant=parseFloat(smoothing.value);
  audioContext.createMediaStreamSource(micStream).connect(analyser);
  resetBandState();
  micButton.textContent="Stop Phone Mic";micButton.classList.add("active");updateMicNotice();audioAnimation=requestAnimationFrame(audioLoop)
 }catch(e){micNotice.textContent="Microphone could not start: "+e.message;micStream=null}
}
function stopMic(){
 if(audioAnimation)cancelAnimationFrame(audioAnimation);audioAnimation=null;
 if(micStream)micStream.getTracks().forEach(t=>t.stop());micStream=null;
 if(audioContext)audioContext.close();audioContext=null;analyser=null;
 micButton.textContent="Start Phone Mic";micButton.classList.remove("active");updateMicNotice()
}
function toggleMic(){if(micStream)stopMic();else{stopDemo();startMic()}}
function demoTick(){
 demoPhase+=.14;const p=(Math.sin(demoPhase)+1)/2,beat=p>.96,bass=.10+p*.72;
 const mids=.18+(Math.sin(demoPhase*.63+1)+1)*.20,highs=.12+(Math.sin(demoPhase*1.7+2)+1)*.24,volume=Math.min(1,.25+bass*.45);
 setMeters(volume,bass,mids,highs,beat);cmd("audio_frame",{volume,bass,mids,highs,beat})
}
function startDemo(){stopMic();if(demoTimer)return;demoButton.textContent="Stop Demo Beat";demoButton.classList.add("active");demoTimer=setInterval(demoTick,110)}
function stopDemo(){if(demoTimer)clearInterval(demoTimer);demoTimer=null;demoButton.textContent="Start Demo Beat";demoButton.classList.remove("active")}
function toggleDemo(){demoTimer?stopDemo():startDemo()}
function toggleReactive(){const r=state.reactive||{};cmd("reactive_enabled",!r.enabled)}
function renderPresets(){
 const presets=state.reactive_presets||[],sig=presets.join("|");
 if(presetButtons.dataset.sig!==sig){presetButtons.dataset.sig=sig;presetButtons.innerHTML="";presets.forEach(n=>{let b=document.createElement("button");b.dataset.preset=n;b.textContent=n;b.onclick=()=>cmd("reactive_preset",n);presetButtons.appendChild(b)})}
 const r=state.reactive||{};document.querySelectorAll("[data-preset]").forEach(b=>b.classList.toggle("active",b.dataset.preset===r.preset))
}
function syncAudioUI(){
 if(typeof state==="undefined")return;
 const r=state.reactive||{};
 reactiveButton.textContent=r.enabled?"On":"Off";reactiveButton.classList.toggle("active",!!r.enabled);
 sync("reactiveStrength",r.strength);num("reactiveStrengthValue",r.strength||0,"x");renderPresets();
 if(!micStream&&!demoTimer&&state.audio)setMeters(state.audio.volume||0,state.audio.bass||0,state.audio.mids||0,state.audio.highs||0,state.audio.beat||false)
}
updateMicNotice();setInterval(syncAudioUI,300);
"""


def enhanced_html(source):
    html = source
    html = html.replace("</head>", AUDIO_CSS + "\n</head>", 1)
    html = html.replace(
        '<button id="tabEdit" onclick="view(\'edit\')">Edit</button>',
        AUDIO_TAB + '<button id="tabEdit" onclick="view(\'edit\')">Edit</button>',
        1,
    )
    html = html.replace(
        '<section id="edit" class="view">',
        AUDIO_SECTION + '\n<section id="edit" class="view">',
        1,
    )
    html = html.replace(
        '["live","library","edit"]',
        '["live","library","audio","edit"]',
    )
    html = html.replace(
        '<input id="zoom" type="range" min="1" max="5" step=".05"',
        '<input id="zoom" type="range" min=".55" max="5" step=".05"',
    )
    html = html.replace('<span>Crop X</span>', '<span>Position X</span>')
    html = html.replace('<span>Crop Y</span>', '<span>Position Y</span>')
    html = html.replace(
        "async function update(){",
        AUDIO_JS + "\nasync function update(){",
        1,
    )
    return html


phone_server.PHONE_HTML = enhanced_html(phone_server.PHONE_HTML)
PhoneControlServer = phone_server.PhoneControlServer
