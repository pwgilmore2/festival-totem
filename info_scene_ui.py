"""Controller scene tab and black-background choices."""

_CSS = r'''<style>
.infoSceneGrid{display:grid;grid-template-columns:repeat(2,1fr);gap:8px}.infoSceneGrid button{min-height:49px}.infoSceneGrid button.active,.backgroundChoice button.active,#mirrorButton.active{background:#343442}.infoSceneGrid button.active:after,.backgroundChoice button.active:after,#mirrorButton.active:after{content:"";display:inline-block;width:7px;height:7px;margin-left:7px;background:#5bebb0;border-radius:50%}
.infoSceneCard input,.infoSceneCard select,.infoSceneCard textarea{width:100%;background:#202029;color:white;border:1px solid #444456;border-radius:9px;padding:10px;font:inherit;font-size:16px}.infoSceneCard textarea{min-height:113px;resize:vertical}.infoSceneCard .muted{line-height:1.4;margin:7px 0}.infoSceneCard .row{margin-top:10px}.infoSceneCard .row input{max-width:95px}.infoSceneCard .row select{max-width:155px}.backgroundChoice{display:grid;grid-template-columns:1fr 1fr;gap:8px;margin:7px 0}
</style>'''

_SECTION = r'''<section id="scenes" class="view">
<div class="card infoSceneCard"><h2>Scenes</h2><div class="muted">Switch out the GIF for a dedicated scene. Tap GIFs to return.</div>
<div class="infoSceneGrid"><button data-info-scene="Clock" onclick="selectInfoScene('Clock')">Clock + Weather</button><button data-info-scene="Set Times" onclick="selectInfoScene('Set Times')">Set Times</button><button data-info-scene="Waveform" onclick="selectInfoScene('Waveform')">Waveform</button></div>
<button style="width:100%;margin-top:8px" onclick="selectInfoScene(null)">Back to GIFs</button>
<div class="muted" id="sceneStatus">Clock needs phone time after each power cycle. Refresh weather below when connected.</div></div>
<div class="card infoSceneCard"><h2>Clock + Weather</h2><div class="muted">Tap Clock + Weather above to sync time and refresh festival weather. The last reading stays on screen if the phone is offline.</div>
<div class="sh" style="margin-top:10px"><span>Scene background</span></div><div class="backgroundChoice"><button data-clock-bg="Sky" onclick="setClockBackground('Sky')">Day / Dusk / Night</button><button data-clock-bg="Black" onclick="setClockBackground('Black')">Black</button></div>
<div class="infoSceneGrid"><button onclick="refreshTotemWeather(false)">Refresh festival weather</button><button onclick="refreshTotemWeather(true)">Use phone location</button></div><div class="muted" id="weatherStatus">Festival location is the default. Phone location needs browser location permission and HTTPS.</div>
<div class="row"><input id="weatherTemp" inputmode="numeric" maxlength="4" placeholder="Temp °F" aria-label="Temperature in Fahrenheit"><select id="weatherCondition"><option>Clear</option><option>Cloudy</option><option>Rain</option><option>Snow</option><option>Wind</option></select><button onclick="saveTotemWeather()">Set manually</button></div></div>
<div class="card infoSceneCard"><h2>Set Times</h2><div class="muted">Choose a night. Add an artist per line, optionally with a time: 9:30 PM | Artist. Times remain TBA until entered. The roster below is confirmed for the festival, but days are not assigned yet.</div><div class="infoSceneGrid" id="scheduleDayButtons"><button data-schedule-day="Auto" onclick="selectScheduleDay('Auto')">Auto</button><button data-schedule-day="2026-09-30" onclick="selectScheduleDay('2026-09-30')">Wed 9/30</button><button data-schedule-day="2026-10-01" onclick="selectScheduleDay('2026-10-01')">Thu 10/1</button><button data-schedule-day="2026-10-02" onclick="selectScheduleDay('2026-10-02')">Fri 10/2</button><button data-schedule-day="2026-10-03" onclick="selectScheduleDay('2026-10-03')">Sat 10/3</button></div><div class="muted" id="scheduleEditingDay">Editing Wednesday</div><textarea id="sceneSetTimes" placeholder="Artist name\n9:30 PM | Another artist"></textarea><button onclick="saveTotemSchedule()">Save this night</button><div class="infoSceneGrid" style="margin-top:8px"><button onclick="cmd('schedule_step',-1)">◀ Previous</button><button onclick="cmd('schedule_step',1)">Next ▶</button></div><details><summary>Official 2026 artist roster (days TBA)</summary><div class="muted" id="wakaanRoster"></div></details></div>
<div class="card infoSceneCard"><h2>Panels</h2><div class="muted">Mirror renders the front once and copies its image to the back. Independent restores separate playback.</div><button id="mirrorButton" onclick="toggleTotemMirror()">Mirror both panels</button></div>
</section>'''

_JS = r'''<script>
(function(){
 const SCHEDULE_KEY='festivalTotem.setTimes.v2',OLD_SCHEDULE_KEY='festivalTotem.setTimes.v1',WEATHER_KEY='festivalTotem.weather.v1',CLOCK_BG_KEY='festivalTotem.clockBackground.v1';
 const DAYS=[['2026-09-30','Wednesday'],['2026-10-01','Thursday'],['2026-10-02','Friday'],['2026-10-03','Saturday']];
 // Official 2026 Wakaan alphabetical poster: wakaanfestival.com/wp-content/uploads/2026/08/Wakaan_MusicFestival_2026_Lineup_Final.png
 const ARTISTS='AHEE|ARTIFAKTS|ASHEZ|AYCH|CANABLISS|CANVAS|CAPOCHINO|CASEY CLUB|CHAMPAGNE DRIP|CHOZEN|CYCLOPS|DARK MATTER|DEBBIE CHECK|DETOX UNIT|DEV|DIRTYSNATCHA|DISTINCT MOTIVE|DOCTOR P|EAZYBAKED|FLOZONE|FLUX PAVILION|FLY|GALLIUM|GARDELLA|GETTER|HAIRTAGE|HERSHE|HOSTAGE SITUATION|JANTSEN|JILLI|JON CASEY|LIQUID STRANGER (2 SETS)|MACHINEDRUM|MEDUSO|MINDSET|MLOTIK|NOETIKA|NOSTALGIX|OF THE TREES|OVEREAZY|OZZTIN|PRETTY SWEET|RSUN|SATURNA|SHLUMP|SMOAKLAND|SPOONE|STVSH|STYLUST|SULLY|SUPER FUTURE|THE WIDDLER|TRUTH (2 SETS)|TVBOO|TWOPERCENT|VYHARA|WHETHAN|WONKYWILLA|WRAZ|XOTIX|YOOKIE|ZOUTH'.split('|');
 let schedule=[],editingDay=DAYS[0][0];
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
 window.syncTotemClock=()=>{const now=new Date(),epoch=Math.floor(now.getTime()/1000),parts=Object.fromEntries(new Intl.DateTimeFormat('en-US',{timeZone:'America/Chicago',year:'numeric',month:'2-digit',day:'2-digit',hour:'2-digit',minute:'2-digit',second:'2-digit',hourCycle:'h23'}).formatToParts(now).filter(p=>p.type!=='literal').map(p=>[p.type,Number(p.value)]));const festivalWall=Date.UTC(parts.year,parts.month-1,parts.day,parts.hour,parts.minute,parts.second);return cmd('clock_sync',{epoch:epoch,offset_seconds:Math.round(festivalWall/1000)-epoch})};
 window.selectInfoScene=async function(mode){if(mode==='Clock'||mode==='Set Times')await syncTotemClock();await cmd('info_scene',mode);refreshInfoScenes();if(mode==='Clock')refreshTotemWeather(false)};
 window.saveTotemWeather=function(){let data={temperature:document.getElementById('weatherTemp').value.trim(),condition:document.getElementById('weatherCondition').value};try{localStorage.setItem(WEATHER_KEY,JSON.stringify(data))}catch(_){ }return cmd('weather_update',data)};
 window.refreshTotemWeather=async function(usePhone){const status=document.getElementById('weatherStatus');status.textContent='Getting current conditions…';try{let latitude=35.70987,longitude=-93.79483;if(usePhone){if(!navigator.geolocation)throw Error('Phone location needs HTTPS and browser location permission. Use Festival location instead.');const position=await new Promise((resolve,reject)=>navigator.geolocation.getCurrentPosition(resolve,reject,{timeout:12000,maximumAge:300000}));latitude=position.coords.latitude;longitude=position.coords.longitude}const url='https://api.open-meteo.com/v1/forecast?latitude='+encodeURIComponent(latitude)+'&longitude='+encodeURIComponent(longitude)+'&current=temperature_2m,weather_code,wind_speed_10m&temperature_unit=fahrenheit&wind_speed_unit=mph';const response=await fetch(url);if(!response.ok)throw Error('Weather service returned '+response.status);const data=(await response.json()).current;if(!data||!Number.isFinite(data.temperature_2m))throw Error('Weather service returned no current temperature');const code=Number(data.weather_code);let condition=code>=71&&code<=77||code>=85&&code<=86?'Snow':code>=51&&code<=67||code>=80&&code<=82||code>=95?'Rain':code>=2&&code<=3||code===45||code===48?'Cloudy':Number(data.wind_speed_10m)>=20?'Wind':'Clear';document.getElementById('weatherTemp').value=String(Math.round(data.temperature_2m));document.getElementById('weatherCondition').value=condition;await saveTotemWeather();status.textContent=condition+' · '+Math.round(data.temperature_2m)+'°F, updated '+new Date().toLocaleTimeString()+(usePhone?' near phone':' near festival')}catch(error){status.textContent='Could not refresh: '+(error.message||'location unavailable')+'. Last saved reading remains available.'}};
 function renderScheduleEditor(){document.getElementById('scheduleEditingDay').textContent='Editing '+(DAYS.find(x=>x[0]===editingDay)||DAYS[0])[1];document.getElementById('sceneSetTimes').value=schedule.filter(x=>x.day===editingDay).map(x=>(x.time?x.time+' | ':'')+x.name).join('\n')}
 async function sendSchedule(){await cmd('schedule_update',schedule.slice(0,8));for(let i=8;i<schedule.length;i+=8)await cmd('schedule_append',schedule.slice(i,i+8))}
 window.selectScheduleDay=async function(day){if(day!=='Auto'&&!DAYS.some(x=>x[0]===day))return;if(day!==editingDay&&document.getElementById('sceneSetTimes').value!==schedule.filter(x=>x.day===editingDay).map(x=>(x.time?x.time+' | ':'')+x.name).join('\n'))await saveTotemSchedule();if(day!=='Auto'){editingDay=day;renderScheduleEditor()}await cmd('schedule_day',day);refreshInfoScenes()};
 window.saveTotemSchedule=function(){const raw=document.getElementById('sceneSetTimes').value;const rows=raw.split(/\r?\n/).map(line=>{const p=line.indexOf('|');return {day:editingDay,time:p<0?'':line.slice(0,p).trim(),name:(p<0?line:line.slice(p+1)).trim()}}).filter(x=>x.name).slice(0,32);schedule=schedule.filter(x=>x.day!==editingDay).concat(rows).slice(0,128);try{localStorage.setItem(SCHEDULE_KEY,JSON.stringify(schedule))}catch(_){ }document.getElementById('sceneStatus').textContent=rows.length+' acts saved for '+(DAYS.find(x=>x[0]===editingDay)||DAYS[0])[1]+'. Times may be added later.';return sendSchedule()};
 window.toggleTotemMirror=()=>cmd('mirror_displays',!state.mirrored);
 window.setClockBackground=value=>{if(value!=='Black'&&value!=='Sky')return;try{localStorage.setItem(CLOCK_BG_KEY,value)}catch(_){ }return cmd('scene_background',{scene:'Clock',background:value})};
 function refreshInfoScenes(){if(typeof state==='undefined'||!state)return;const mode=state.info_scene;document.querySelectorAll('[data-info-scene]').forEach(b=>b.classList.toggle('active',b.dataset.infoScene===mode));document.querySelectorAll('[data-schedule-day]').forEach(b=>b.classList.toggle('active',b.dataset.scheduleDay===(state.schedule_day||'Auto')));document.querySelectorAll('[data-clock-bg]').forEach(b=>b.classList.toggle('active',b.dataset.clockBg===(state.scene_backgrounds?.Clock||'Sky')));let mirror=document.getElementById('mirrorButton');if(mirror){mirror.classList.toggle('active',!!state.mirrored);mirror.textContent=state.mirrored?'Mirrored • one rendered image':'Independent • separate images'}}
 setInterval(refreshInfoScenes,400);
 setInterval(()=>{if(typeof state!=='undefined'&&['Clock','Set Times'].includes(state?.info_scene))syncTotemClock()},60000);
 try{
   const saved=JSON.parse(localStorage.getItem(SCHEDULE_KEY)||localStorage.getItem(OLD_SCHEDULE_KEY)||'[]');if(Array.isArray(saved)){schedule=saved.map(x=>({day:x.day||DAYS[0][0],time:x.time||'',name:x.name||''})).filter(x=>DAYS.some(d=>d[0]===x.day)&&x.name);if(schedule.length)sendSchedule()}
   const weather=JSON.parse(localStorage.getItem(WEATHER_KEY)||'null');if(weather){document.getElementById('weatherTemp').value=weather.temperature||'';document.getElementById('weatherCondition').value=weather.condition||'Clear';cmd('weather_update',weather)}
   const bg=localStorage.getItem(CLOCK_BG_KEY);if(bg==='Black'||bg==='Sky')setClockBackground(bg);
 }catch(_){ }
 document.getElementById('wakaanRoster').textContent=ARTISTS.join(' · ');
 renderScheduleEditor();
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
