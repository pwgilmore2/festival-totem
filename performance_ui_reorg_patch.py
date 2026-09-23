"""Final controller organization around the live performance workflow."""

_CSS = r'''
<style>
.tabs{gap:7px!important}.tabs .performancePrimary{min-width:88px!important}.tabs .managementTab{margin-left:auto;background:#2b2b35!important;color:#ddd!important}.tabs .managementTab.active{background:#7063d7!important;color:white!important}
#tabLive,#tabLibrary,#tabEdit,#tabSetup{display:none!important}
.vibeLaunch{background:radial-gradient(circle at 10% 0%,#00e5ff2c,transparent 34%),radial-gradient(circle at 95% 0%,#8b5cff30,transparent 38%),#ffffff12}.vibeLaunch h2{font-size:22px!important;margin-bottom:4px!important}.vibeLaunch .vibeSub{font-size:12px;opacity:.68;line-height:1.4;margin-bottom:12px}.vibeStart{width:100%;min-height:66px;font-size:18px;background:linear-gradient(135deg,#6c4cff,#00b8ff);box-shadow:0 8px 24px #0006}.vibeTransport{display:grid;grid-template-columns:1fr 1fr;gap:8px;margin-top:8px}.vibeTransport button{min-height:48px}
.vibePresetBox{margin:12px 0;padding:12px;border-radius:14px;background:#ffffff0b;border:1px solid #ffffff14}.vibePresetHead{display:flex;justify-content:space-between;align-items:center;gap:8px;margin-bottom:8px}.vibePresetHead strong{font-size:14px}.vibePresetGrid{display:grid;grid-template-columns:repeat(2,1fr);gap:7px;margin-bottom:9px}.vibePresetGrid button{min-height:46px}.vibePresetSave{display:grid;grid-template-columns:1fr auto;gap:8px}.vibePresetSave input{width:100%;background:#202029;color:#fff;border:1px solid #444456;border-radius:10px;padding:10px;font-size:16px}.vibePresetDelete{font-size:11px;opacity:.7;margin-top:7px}
.manageSwitcher{display:grid;grid-template-columns:repeat(3,1fr);gap:7px;margin:2px 0 12px;position:sticky;top:62px;z-index:16;padding:7px;background:#101016ed;backdrop-filter:blur(10px);border-radius:13px}.manageSwitcher button{min-height:42px;font-size:13px}.manageSwitcher button.active{background:#7063d7}.manageHint{font-size:11px;opacity:.62;margin:-4px 0 8px;text-align:center}
.batchTagBar{display:grid;grid-template-columns:auto 1fr auto;gap:7px;align-items:center;margin:4px 0 10px;padding:9px;background:#ffffff0b;border:1px solid #ffffff12;border-radius:12px}.batchTagBar input{min-width:0;background:#202029;color:#fff;border:1px solid #444456;border-radius:9px;padding:9px;font-size:15px}.batchTagBar button{min-height:40px;padding:7px 10px}.tile.batchSelected{border-color:#53e6a8!important;box-shadow:0 0 0 2px #53e6a855 inset}.batchCount{font-size:11px;opacity:.7;grid-column:1/-1}
body.manageMode #targetCard{display:none!important}body.manageMode .manageSwitcher{display:grid}body:not(.manageMode) .manageSwitcher{display:none}
@media(max-width:520px){.tabs button.performancePrimary{min-width:78px!important}.tabs .managementTab{min-width:72px!important}.manageSwitcher{top:60px}.vibePresetGrid{grid-template-columns:1fr 1fr}.batchTagBar{grid-template-columns:1fr 1fr}.batchTagBar input{grid-column:1/-1}}
</style>
'''

_VIBE_CARD = r'''
<div id="vibeLaunchCard" class="card vibeLaunch">
<h2>Vibe</h2>
<div class="vibeSub">Start random GIFs on both screens, then bring the phone mic in and shape the music response below.</div>
<button class="vibeStart" onclick="startVibeRandom()">▶ RANDOM GIFS · BOTH SCREENS</button>
<div class="vibeTransport"><button onclick="vibePrevious()">◀ Previous</button><button onclick="vibeNext()">Next ▶</button></div>
</div>
'''

_VIBE_PRESETS = r'''
<div class="vibePresetBox">
<div class="vibePresetHead"><strong>My Vibes</strong><span class="tiny">audio response only</span></div>
<div id="myVibeButtons" class="vibePresetGrid"></div>
<div class="vibePresetSave"><input id="vibePresetName" maxlength="32" placeholder="Name this vibe"><button onclick="saveCurrentVibe()">Save</button></div>
<div class="vibePresetDelete">Tap a saved vibe to apply it. Hold its button to remove it.</div>
</div>
<div class="sectionHint" style="margin-top:8px">Built-in starting points</div>
'''

_MANAGE_SWITCH = r'''
<div class="manageSwitcher">
<button data-manage="library" onclick="openManage('library')">GIF Library</button>
<button data-manage="edit" onclick="openManage('edit')">Edit / Tags</button>
<button data-manage="setup" onclick="openManage('setup')">Setup</button>
</div>
<div class="manageHint">Backstage tools — hidden from the main performance flow.</div>
'''

_BATCH_BAR = r'''
<div class="batchTagBar">
<button id="batchModeButton" onclick="toggleBatchMode()">Batch Tag</button>
<input id="batchTagInput" maxlength="40" placeholder="Tag once, apply to many">
<button id="batchApplyButton" onclick="applyBatchTag()">Apply</button>
<div id="batchCount" class="batchCount">Batch mode off</div>
</div>
'''

_JS = r'''
<script>
(function(){
 let _performanceBaseView=view,currentManage='library';
 const VIBE_KEY='festivalTotem.vibePresets.v1';
 let batchMode=false,batchSelected=new Set();
 function tab(id){return document.getElementById(id)}
 function section(id){return document.getElementById(id)}
 function tabsRoot(){return document.querySelector('.tabs')}
 function ensurePerformanceNav(){
   const root=tabsRoot();if(!root)return;
   const audio=tab('tabAudio'),guest=tab('tabGuest'),icons=tab('tabIcons'),text=tab('tabText');
   [audio,guest,icons,text].filter(Boolean).forEach(el=>{el.classList.add('performancePrimary');root.appendChild(el)});
   let manage=tab('tabManage');if(!manage){manage=document.createElement('button');manage.id='tabManage';manage.className='managementTab';manage.textContent='Manage';manage.onclick=()=>openManage(currentManage||'library')}root.appendChild(manage)
 }
 function setManageMode(on){document.body.classList.toggle('manageMode',!!on);const m=tab('tabManage');if(m)m.classList.toggle('active',!!on)}
 function markManage(kind){document.querySelectorAll('[data-manage]').forEach(b=>b.classList.toggle('active',b.dataset.manage===kind))}
 function scrollManage(kind){let el=null;if(kind==='library')el=document.getElementById('gallery')?.closest('.card');if(kind==='edit')el=document.getElementById('editname')?.closest('.card');if(kind==='setup')el=document.getElementById('brightness')?.closest('.card')||document.getElementById('quickPresetList')?.closest('.card');if(el)setTimeout(()=>el.scrollIntoView({behavior:'smooth',block:'start'}),40)}
 window.openManage=function(kind){if(!['library','edit','setup'].includes(kind))kind='library';currentManage=kind;setManageMode(true);const target=(kind==='library')?'live':'edit';_performanceBaseView(target);document.querySelectorAll('.tabs button').forEach(b=>b.classList.remove('active'));const m=tab('tabManage');if(m)m.classList.add('active');markManage(kind);const tc=document.getElementById('targetCard');if(tc)tc.style.display='none';scrollManage(kind)}
 view=function(name){if(name==='live'||name==='library'){openManage('library');return}if(name==='edit'||name==='setup'){openManage(name==='setup'?'setup':'edit');return}setManageMode(false);_performanceBaseView(name);const m=tab('tabManage');if(m)m.classList.remove('active')}

 function allIds(){return (state.library||[]).map(x=>x.index).filter(Number.isInteger)}
 window.startVibeRandom=function(){const items=allIds();if(!items.length)return;cmd('set_target','both');cmd('slideshow_start',{indices:items,duration:5,shuffle:true,label:'All'})}
 window.vibeNext=function(){const items=allIds();if(items.length){cmd('set_target','both');cmd('filtered_step',{indices:items,delta:1})}}
 window.vibePrevious=function(){const items=allIds();if(items.length){cmd('set_target','both');cmd('filtered_step',{indices:items,delta:-1})}}

 function loadVibes(){try{const v=JSON.parse(localStorage.getItem(VIBE_KEY)||'[]');return Array.isArray(v)?v:[]}catch(_){return[]}}
 function storeVibes(v){localStorage.setItem(VIBE_KEY,JSON.stringify(v));renderMyVibes()}
 function currentVibeSnapshot(name){const r=state.reactive||{};return {name,strength:Number(r.strength??0),layers:{...(r.layers||{})}}}
 window.saveCurrentVibe=function(){const input=document.getElementById('vibePresetName'),name=(input?.value||'').trim();if(!name)return;let vibes=loadVibes(),snap=currentVibeSnapshot(name),i=vibes.findIndex(v=>v.name.toLowerCase()===name.toLowerCase());if(i>=0)vibes[i]=snap;else vibes.push(snap);vibes=vibes.slice(-16);if(input)input.value='';storeVibes(vibes)}
 window.applyMyVibe=function(i){const v=loadVibes()[i];if(!v)return;cmd('reactive_enabled',true);cmd('reactive_strength',Number(v.strength??0));Object.entries(v.layers||{}).forEach(([name,value])=>cmd('reactive_layer',{name,value:Number(value)}))}
 window.removeMyVibe=function(i){let v=loadVibes();v.splice(i,1);storeVibes(v)}
 window.renderMyVibes=function(){const box=document.getElementById('myVibeButtons');if(!box)return;const vibes=loadVibes();box.innerHTML='';vibes.forEach((v,i)=>{let b=document.createElement('button');b.textContent=v.name;b.onclick=()=>applyMyVibe(i);let timer=null;b.onpointerdown=()=>{timer=setTimeout(()=>{removeMyVibe(i);timer=null},700)};['pointerup','pointercancel','pointerleave'].forEach(ev=>b.addEventListener(ev,()=>{if(timer){clearTimeout(timer);timer=null}}));box.appendChild(b)});if(!vibes.length)box.innerHTML='<div class="muted" style="grid-column:1/-1">Tune the sliders below, name it, and save your first vibe.</div>'}

 function syncBatchUI(){const b=document.getElementById('batchModeButton'),c=document.getElementById('batchCount');if(b){b.classList.toggle('active',batchMode);b.textContent=batchMode?'Done':'Batch Tag'}if(c)c.textContent=batchMode?(batchSelected.size+' selected · tap GIFs to add/remove'):'Batch mode off';document.querySelectorAll('.tile[data-index]').forEach(t=>t.classList.toggle('batchSelected',batchSelected.has(parseInt(t.dataset.index))))}
 window.toggleBatchMode=function(){batchMode=!batchMode;if(!batchMode)batchSelected.clear();syncBatchUI()}
 window.applyBatchTag=async function(){const input=document.getElementById('batchTagInput'),tag=(input?.value||'').trim();if(!tag||!batchSelected.size)return;await cmd('batch_add_tag',{indices:[...batchSelected],tag});batchSelected.clear();if(input)input.value='';syncBatchUI()}
 function installBatchCapture(){const g=document.getElementById('gallery');if(!g||g.dataset.batchCapture==='1')return;g.dataset.batchCapture='1';g.addEventListener('click',e=>{if(!batchMode)return;const tile=e.target.closest('.tile[data-index]');if(!tile)return;e.preventDefault();e.stopPropagation();e.stopImmediatePropagation();const i=parseInt(tile.dataset.index);if(batchSelected.has(i))batchSelected.delete(i);else batchSelected.add(i);syncBatchUI()},true)}

 function performanceNavTick(){ensurePerformanceNav();const text=tab('tabText');if(text)text.textContent=(state.text&&state.text.enabled)?'Text ●':'Text';const audio=tab('tabAudio');if(audio)audio.textContent=(state.audio&&state.audio.fresh)?'Vibe ●':'Vibe';const guest=tab('tabGuest');if(guest)guest.textContent=(state.guest&&state.guest.active)?'Chaos ●':'Chaos';const icons=tab('tabIcons');if(icons)icons.textContent=(state.icon&&state.icon.icon_enabled)?'Icons ●':'Icons';markManage(currentManage);installBatchCapture();syncBatchUI()}
 setInterval(performanceNavTick,250);
 window.addEventListener('load',()=>{ensurePerformanceNav();renderMyVibes();installBatchCapture();setTimeout(()=>{if(section('audio'))view('audio')},100)})
})();
</script>
'''


def _insert_after_section_start(html, section_id, block):
    needle = f'<section id="{section_id}" class="view'
    pos = html.find(needle)
    if pos < 0:
        return html
    gt = html.find('>', pos)
    if gt < 0:
        return html
    return html[:gt + 1] + block + html[gt + 1:]


def apply(html):
    html = html.replace('</head>', _CSS + '</head>', 1)

    audio_anchor = '<section id="audio" class="view">'
    if audio_anchor in html:
        html = html.replace(audio_anchor, audio_anchor + _VIBE_CARD, 1)

    preset_anchor = '<div id="presetButtons" class="presetGrid"></div>'
    if preset_anchor in html:
        html = html.replace(preset_anchor, _VIBE_PRESETS + preset_anchor, 1)

    for section_id in ('live', 'edit'):
        html = _insert_after_section_start(html, section_id, _MANAGE_SWITCH)

    gallery_anchor = '<div id="gallery" class="gallery"></div>'
    if gallery_anchor in html:
        html = html.replace(gallery_anchor, _BATCH_BAR + gallery_anchor, 1)

    html = html.replace('</body>', _JS + '</body>', 1)
    return html
