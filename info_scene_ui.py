"""Controller scene tab and black-background choices."""

_CSS = r'''<style>
.infoSceneGrid{display:grid;grid-template-columns:repeat(2,1fr);gap:8px}.infoSceneGrid button{min-height:49px}.infoSceneGrid button.active:after,.backgroundChoice button.active:after,#mirrorButton.active:after{content:"";display:inline-block;width:7px;height:7px;margin-left:7px;background:#5bebb0;border-radius:50%}
.infoSceneCard input,.infoSceneCard select,.infoSceneCard textarea{width:100%;background:#202029;color:white;border:1px solid #444456;border-radius:9px;padding:10px;font:inherit;font-size:16px}.infoSceneCard textarea{min-height:113px;resize:vertical}.infoSceneCard .muted{line-height:1.4;margin:7px 0}.infoSceneCard .row{margin-top:10px}.infoSceneCard .row input{max-width:95px}.infoSceneCard .row select{max-width:155px}.backgroundChoice{display:grid;grid-template-columns:1fr 1fr;gap:8px;margin:7px 0}
</style>'''

_SECTION = r'''<section id="scenes" class="view">
<div class="card infoSceneCard"><h2>Scenes</h2><div class="muted">Switch out the GIF for a dedicated scene. Tap GIFs to return.</div>
<div class="infoSceneGrid"><button data-info-scene="Clock" onclick="selectInfoScene('Clock')">Clock</button><button data-info-scene="Weather" onclick="selectInfoScene('Weather')">Weather</button><button data-info-scene="Set Times" onclick="selectInfoScene('Set Times')">Set Times</button><button data-info-scene="Waveform" onclick="selectInfoScene('Waveform')">Waveform</button></div>
<button style="width:100%;margin-top:8px" onclick="selectInfoScene(null)">Back to GIFs</button>
<div class="muted" id="sceneStatus">Clock needs phone time after each power cycle. Weather is entered below.</div></div>
<div class="card infoSceneCard"><h2>Clock and Weather</h2><div class="muted">Time comes from this phone. The sky follows the time of day; weather is manual and stays available without internet.</div><button onclick="syncTotemClock()">Sync time from phone</button>
<div class="sh" style="margin-top:10px"><span>Clock background</span></div><div class="backgroundChoice"><button data-clock-bg="Black" onclick="setClockBackground('Black')">Black</button><button data-clock-bg="Sky" onclick="setClockBackground('Sky')">Day / Night</button></div>
<div class="row"><input id="weatherTemp" inputmode="numeric" maxlength="4" placeholder="Temp °F" aria-label="Temperature in Fahrenheit"><select id="weatherCondition"><option>Clear</option><option>Cloudy</option><option>Rain</option><option>Snow</option><option>Wind</option></select><button onclick="saveTotemWeather()">Set</button></div></div>
<div class="card infoSceneCard"><h2>Set Times</h2><div class="muted">One act per line, formatted as 9:30 PM | Artist. Save on this phone, then use Previous / Next to cue an act.</div><textarea id="sceneSetTimes" placeholder="9:30 PM | Artist\n11:00 PM | Headliner"></textarea><button onclick="saveTotemSchedule()">Save set times</button><div class="infoSceneGrid" style="margin-top:8px"><button onclick="cmd('schedule_step',-1)">◀ Previous</button><button onclick="cmd('schedule_step',1)">Next ▶</button></div></div>
<div class="card infoSceneCard"><h2>Panels</h2><div class="muted">Mirror renders the front once and copies its image to the back. Independent restores separate playback.</div><button id="mirrorButton" onclick="toggleTotemMirror()">Mirror both panels</button></div>
</section>'''

_JS = r'''<script>
(function(){
 const SCHEDULE_KEY='festivalTotem.setTimes.v1',WEATHER_KEY='festivalTotem.weather.v1';
 const previousView=view;
 view=function(name){
   if(name==='scenes'){
     document.body.classList.remove('manageMode');
     document.querySelectorAll('.view').forEach(el=>el.classList.toggle('active',el.id==='scenes'));
     document.querySelectorAll('.tabs button').forEach(el=>el.classList.toggle('active',el.id==='tabScenes'));
     const target=document.getElementById('targetCard');if(target)target.style.display='';
     return;
   }
   previousView(name);
   document.getElementById('scenes')?.classList.remove('active');
   document.getElementById('tabScenes')?.classList.remove('active');
 };
 const nav=document.querySelector('.tabs'),manage=document.getElementById('tabManage');
 if(nav){const button=document.createElement('button');button.id='tabScenes';button.textContent='Scenes';button.className='performancePrimary';button.onclick=()=>view('scenes');nav.insertBefore(button,manage)}
 window.syncTotemClock=()=>cmd('clock_sync',Math.floor(Date.now()/1000-new Date().getTimezoneOffset()*60));
 window.selectInfoScene=async function(mode){if(mode==='Clock'||mode==='Weather'||mode==='Set Times')await syncTotemClock();await cmd('info_scene',mode);refreshInfoScenes()};
 window.saveTotemWeather=function(){let data={temperature:document.getElementById('weatherTemp').value.trim(),condition:document.getElementById('weatherCondition').value};try{localStorage.setItem(WEATHER_KEY,JSON.stringify(data))}catch(_){ }cmd('weather_update',data)};
 window.saveTotemSchedule=function(){let raw=document.getElementById('sceneSetTimes').value;let rows=raw.split(/\r?\n/).map(line=>{let p=line.indexOf('|');return p<0?null:{time:line.slice(0,p).trim(),name:line.slice(p+1).trim()}}).filter(x=>x&&x.time&&x.name).slice(0,32);try{localStorage.setItem(SCHEDULE_KEY,JSON.stringify(rows))}catch(_){ }cmd('schedule_update',rows);document.getElementById('sceneStatus').textContent=rows.length+' set times loaded. Save on this phone to restore them after a board restart.'};
 window.toggleTotemMirror=()=>cmd('mirror_displays',!state.mirrored);
 window.setClockBackground=value=>cmd('scene_background',{scene:'Clock',background:value});
 function refreshInfoScenes(){if(typeof state==='undefined'||!state)return;const mode=state.info_scene;document.querySelectorAll('[data-info-scene]').forEach(b=>b.classList.toggle('active',b.dataset.infoScene===mode));document.querySelectorAll('[data-clock-bg]').forEach(b=>b.classList.toggle('active',b.dataset.clockBg===(state.scene_backgrounds?.Clock||'Black')));let mirror=document.getElementById('mirrorButton');if(mirror){mirror.classList.toggle('active',!!state.mirrored);mirror.textContent=state.mirrored?'Mirrored • one rendered image':'Independent • separate images'}}
 setInterval(refreshInfoScenes,400);
 setInterval(()=>{if(typeof state!=='undefined'&&state?.info_scene==='Clock')syncTotemClock()},60000);
 try{
   const saved=JSON.parse(localStorage.getItem(SCHEDULE_KEY)||'[]');if(Array.isArray(saved)){document.getElementById('sceneSetTimes').value=saved.map(x=>x.time+' | '+x.name).join('\n');if(saved.length)cmd('schedule_update',saved)}
   const weather=JSON.parse(localStorage.getItem(WEATHER_KEY)||'null');if(weather){document.getElementById('weatherTemp').value=weather.temperature||'';document.getElementById('weatherCondition').value=weather.condition||'Clear';cmd('weather_update',weather)}
 }catch(_){ }
 syncTotemClock();
})();
</script>'''

_BLACK = r'''<div class="sh"><span>Background</span></div><div class="backgroundChoice"><button data-text-bg="Dimmed GIF" onclick="setTextBackground('Dimmed GIF')">Dimmed GIF</button><button data-text-bg="Black" onclick="setTextBackground('Black')">Black</button></div>'''
_ICON_BLACK = r'''<div class="sh"><span>Background</span></div><div class="backgroundChoice"><button data-icon-bg="GIF" onclick="setIconBackground('GIF')">GIF</button><button data-icon-bg="Black" onclick="setIconBackground('Black')">Black</button></div>'''
_BG_JS = r'''<script>
(function(){
 let textBackground='Dimmed GIF';
 const originalPayload=textPayload;
 textPayload=function(){let value=originalPayload();value.background=textBackground;return value};
 window.setTextBackground=function(value){if(value!=='Black'&&value!=='Dimmed GIF')return;textBackground=value;textChanged();syncBackgrounds()};
 window.setIconBackground=function(value){if(value!=='Black'&&value!=='GIF')return;cmd('icon_background',value)};
 function syncBackgrounds(){if(typeof state==='undefined'||!state)return;const t=state.text||{},i=state.icon||{};if(document.activeElement?.dataset?.textBg===undefined&&t.background)textBackground=t.background;document.querySelectorAll('[data-text-bg]').forEach(b=>b.classList.toggle('active',b.dataset.textBg===textBackground));document.querySelectorAll('[data-icon-bg]').forEach(b=>b.classList.toggle('active',b.dataset.iconBg===(i.background||'GIF')))}
 setInterval(syncBackgrounds,500);
})();
</script>'''


def apply(html):
    html = html.replace('</head>', _CSS + '</head>', 1)
    html = html.replace('<section id="edit" class="view">', _SECTION + '<section id="edit" class="view">', 1)
    html = html.replace('<div class="iconFadeNote">', _ICON_BLACK + '<div class="iconFadeNote">', 1)
    html = html.replace('<div class="card textCard"><h2>Text Engine</h2>', '<div class="card textCard"><h2>Text Engine</h2>' + _BLACK, 1)
    html = html.replace('</body>', _BG_JS + _JS + '</body>', 1)
    return html
