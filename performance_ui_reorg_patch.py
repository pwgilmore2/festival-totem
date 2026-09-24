"""Final controller organization around the live performance workflow."""

_CSS = r'''
<style>
.tabs{gap:7px!important}.tabs .performancePrimary{min-width:88px!important}.tabs .managementTab{margin-left:auto;background:#2b2b35!important;color:#ddd!important}
.audioQuickBar{margin:0 0 8px}.audioQuickBar .audioStart,.audioQuickBar .audioStart.active{width:100%;min-height:48px;font-size:14px;background:#343442;box-shadow:none;border:1px solid #ffffff2a}.audioQuickBar .audioStart.active:after{content:'';display:inline-block;width:7px;height:7px;margin-left:8px;background:#5bebb0;border-radius:50%}
.tabs button{position:relative}.tabs button.active,.tabs button.runtimeOn,.tabs button.runtimeChaos,.tabs button.beatHit{background:#343442!important;box-shadow:none!important;filter:none!important}.tabs button.active{border-bottom:2px solid #8b7cff!important}.tabs .managementTab.active{background:#2b2b35!important;color:white!important}
.tabs button.runtimeOn:after,.tabs button.runtimeChaos:after{content:'';display:inline-block;width:7px;height:7px;margin-left:5px;border-radius:50%;vertical-align:middle;background:#5bebb0;box-shadow:0 0 7px #5bebb088}.tabs button.runtimeChaos:after{background:#ff77bd;box-shadow:0 0 7px #ff77bd88}.tabs button.beatHit:after{background:#fff;box-shadow:0 0 7px #fff}
#tabLive,#tabLibrary,#tabEdit,#tabSetup{display:none!important}
.vibeLaunch{background:radial-gradient(circle at 10% 0%,#00e5ff2c,transparent 34%),radial-gradient(circle at 95% 0%,#8b5cff30,transparent 38%),#ffffff12}.vibeLaunch h2{font-size:22px!important;margin-bottom:4px!important}.vibeLaunch .vibeSub{font-size:12px;opacity:.68;line-height:1.4;margin-bottom:12px}.vibeStart{width:100%;min-height:66px;font-size:18px;background:linear-gradient(135deg,#6c4cff,#00b8ff);box-shadow:0 8px 24px #0006}.vibeTransport{display:grid;grid-template-columns:1fr 1fr;gap:8px;margin-top:8px}.vibeTransport button{min-height:48px}
.vibePresetBox{margin:12px 0;padding:12px;border-radius:14px;background:#ffffff0b;border:1px solid #ffffff14}.vibePresetHead{display:flex;justify-content:space-between;align-items:center;gap:8px;margin-bottom:8px}.vibePresetHead strong{font-size:14px}.vibePresetGrid{display:grid;grid-template-columns:repeat(2,1fr);gap:7px;margin-bottom:9px}.vibePresetGrid button{min-height:46px}.vibePresetGrid button.active{background:#343442!important;box-shadow:none!important}.vibePresetGrid button.active:after,[data-overlay-audio].active:after{content:"";display:inline-block;width:7px;height:7px;border-radius:50%;background:#65f2b6;margin-left:8px}.vibeChoose{background:radial-gradient(circle at 95% 5%,#ff4f9e25,transparent 50%),#ffffff12}.vibeEditor{background:radial-gradient(circle at 5% 0%,#734cff1c,transparent 43%),#ffffff12}.overlayAudio{margin-top:12px;padding:12px;background:#ffffff0b;border:1px solid #ffffff18;border-radius:13px}.overlayAudio [data-overlay-audio].active{background:#343442!important;box-shadow:none!important}.vibePresetSave input{width:100%;background:#202029;color:#fff;border:1px solid #444456;border-radius:10px;padding:10px;font-size:16px}.vibePresetActions{display:grid;grid-template-columns:repeat(3,1fr);gap:7px;margin-top:8px}.vibePresetActions button{min-height:46px}.vibePresetStatus{font-size:12px;opacity:.75;min-height:18px;margin-top:8px}.vibePresetHelp{font-size:11px;opacity:.68;line-height:1.4;margin:7px 0}
.manageSwitcher{display:grid;grid-template-columns:repeat(3,1fr);gap:7px;margin:2px 0 12px;position:sticky;top:62px;z-index:16;padding:7px;background:#101016ed;backdrop-filter:blur(10px);border-radius:13px}.manageSwitcher button{min-height:42px;font-size:13px}.manageSwitcher button.active{background:#7063d7}.manageHint{font-size:11px;opacity:.62;margin:-4px 0 8px;text-align:center}
.batchTagBar{display:grid;grid-template-columns:auto 1fr auto;gap:7px;align-items:center;margin:4px 0 10px;padding:9px;background:#ffffff0b;border:1px solid #ffffff12;border-radius:12px}.batchTagBar input{min-width:0;background:#202029;color:#fff;border:1px solid #444456;border-radius:9px;padding:9px;font-size:15px}.batchTagBar button{min-height:40px;padding:7px 10px}.tile.batchSelected{border-color:#53e6a8!important;box-shadow:0 0 0 2px #53e6a855 inset}.batchCount{font-size:11px;opacity:.7;grid-column:1/-1}
body.manageMode .manageSwitcher{display:grid}body:not(.manageMode) .manageSwitcher{display:none}
@media(max-width:520px){.tabs button.performancePrimary{min-width:78px!important}.tabs .managementTab{min-width:72px!important}.manageSwitcher{top:60px}.vibePresetGrid{grid-template-columns:1fr 1fr}.batchTagBar{grid-template-columns:1fr 1fr}.batchTagBar input{grid-column:1/-1}}
</style>
'''

_VIBE_CARD = r'''
<div id="vibeLaunchCard" class="card vibeLaunch">
<h2>Vibe</h2>
<div class="vibeSub">Shape the sound response here. Start phone audio from the button above the tabs.</div>
<button class="vibeStart" onclick="startVibeRandom()">Shuffle</button>
<div class="vibeTransport"><button onclick="vibePrevious()">◀ Previous</button><button onclick="vibeNext()">Next ▶</button></div>
</div>
'''

_VIBE_PRESETS = r'''
<div class="card vibeChoose"><div class="vibePresetHead"><strong>Audio Presets</strong><span class="tiny">tap to play</span></div><div id="myVibeButtons" class="vibePresetGrid"></div></div>
'''

_VIBE_EDITOR = r'''<div class="card vibeEditor"><h2>Audio Preset Management</h2><div class="sectionHint">Choose a preset, adjust the sound mapping, then save, rename, add or delete it. Presets live in this browser.</div><div id="manageVibeButtons" class="vibePresetGrid"></div><div class="vibePresetSave"><input id="vibePresetName" maxlength="32" placeholder="Preset name" aria-label="Preset name"></div><div class="vibePresetActions"><button onclick="saveCurrentVibe()">Save Changes</button><button onclick="addCurrentVibe()">Add New</button><button class="warn" onclick="removeMyVibe()">Delete</button></div><div id="vibePresetStatus" class="vibePresetStatus" role="status" aria-live="polite"></div></div>'''

_OVERLAY_AUDIO = r'''<div class="overlayAudio"><div class="vibePresetHead"><strong>Overlay Audio Reactivity</strong><span class="tiny">icons + text</span></div><div class="vibePresetActions"><button data-overlay-audio="Off" onclick="setOverlayAudio('Off')">Off</button><button data-overlay-audio="Subtle" onclick="setOverlayAudio('Subtle')">Subtle</button><button data-overlay-audio="Intense" onclick="setOverlayAudio('Intense')">Intense</button></div></div>'''

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
 const OLD_VIBE_KEY='festivalTotem.vibePresets.v1',VIBE_KEY='festivalTotem.vibePresets.v2';
 const VIBE_LAYERS=['bass_zoom','beat_flash','mids_hue','high_sparkle','volume_brightness','bass_shake','high_rgb_split'];
 const STARTING_VIBES=[
   {id:'starter:pulse',name:'Pulse',strength:1,layers:{bass_zoom:.28,beat_flash:.28,mids_hue:0,high_sparkle:.02,volume_brightness:.10,bass_shake:.08,high_rgb_split:0}},
   {id:'starter:spark',name:'Spark',strength:1,layers:{bass_zoom:.03,beat_flash:.08,mids_hue:.04,high_sparkle:.55,volume_brightness:.05,bass_shake:0,high_rgb_split:.10}},
   {id:'starter:neon',name:'Neon',strength:1,layers:{bass_zoom:.05,beat_flash:.08,mids_hue:.30,high_sparkle:.05,volume_brightness:.08,bass_shake:0,high_rgb_split:.18}},
   {id:'starter:chaos',name:'Chaos',strength:1,layers:{bass_zoom:.26,beat_flash:.35,mids_hue:.32,high_sparkle:.38,volume_brightness:.15,bass_shake:.25,high_rgb_split:.32}}
 ];
 let vibePresets=null,selectedVibeId=null,pendingVibe={},vibeDirty=false,renderedVibes='',renderedSelection=null,applyToken=0,applyingVibe=false;
 let batchMode=false,batchSelected=new Set();
 function tab(id){return document.getElementById(id)}
 function section(id){return document.getElementById(id)}
 function tabsRoot(){return document.querySelector('.tabs')}
 function ensurePerformanceNav(){
   const root=tabsRoot();if(!root)return;
   const audio=tab('tabAudio'),guest=tab('tabGuest'),icons=tab('tabIcons'),text=tab('tabText');
   if(audio)audio.textContent='Vibe';if(guest)guest.textContent='Chaos';if(icons)icons.textContent='Icons';if(text)text.textContent='Text';
   [audio,icons,text,guest].filter(Boolean).forEach(el=>{el.classList.add('performancePrimary');root.appendChild(el)});
   let manage=tab('tabManage');if(!manage){manage=document.createElement('button');manage.id='tabManage';manage.className='managementTab';manage.textContent='Manage';manage.onclick=()=>openManage(currentManage||'library')}root.appendChild(manage)
 }
 function setManageMode(on){document.body.classList.toggle('manageMode',!!on);const m=tab('tabManage');if(m)m.classList.toggle('active',!!on)}
 function markManage(kind){document.querySelectorAll('[data-manage]').forEach(b=>b.classList.toggle('active',b.dataset.manage===kind))}
 function scrollManage(kind){let el=null;if(kind==='library')el=document.getElementById('gallery')?.closest('.card');if(kind==='edit')el=document.getElementById('editname')?.closest('.card');if(kind==='setup')el=document.getElementById('panelCard')||document.getElementById('brightness')?.closest('.card');if(el)setTimeout(()=>el.scrollIntoView({behavior:'smooth',block:'start'}),40)}
 window.openManage=function(kind){if(!['library','edit','setup'].includes(kind))kind='library';currentManage=kind;setManageMode(true);const target=(kind==='library')?'live':'edit';_performanceBaseView(target);document.querySelectorAll('.tabs button').forEach(b=>b.classList.remove('active'));const m=tab('tabManage');if(m)m.classList.add('active');markManage(kind);scrollManage(kind)}
 view=function(name){if(name==='live'||name==='library'){openManage('library');return}if(name==='edit'||name==='setup'){openManage(name==='setup'?'setup':'edit');return}setManageMode(false);_performanceBaseView(name);const m=tab('tabManage');if(m)m.classList.remove('active')}

 function allIds(){return (state.library||[]).map(x=>x.index).filter(Number.isInteger)}
 window.startVibeRandom=function(){const items=allIds();if(!items.length)return;cmd('set_target','both');cmd('slideshow_start',{indices:items,duration:5,shuffle:true,label:'All'})}
 window.vibeNext=function(){const items=allIds();if(items.length){cmd('set_target','both');cmd('filtered_step',{indices:items,delta:1})}}
 window.vibePrevious=function(){const items=allIds();if(items.length){cmd('set_target','both');cmd('filtered_step',{indices:items,delta:-1})}}

 function safeValue(value,fallback=0){const n=Number(value);return Number.isFinite(n)?Math.max(0,Math.min(1.5,n)):fallback}
 function cleanVibe(source,id){
   const layers={};for(const key of VIBE_LAYERS)layers[key]=safeValue(source?.layers?.[key]);
   return {id,name:String(source?.name||'Untitled').trim().slice(0,32)||'Untitled',strength:safeValue(source?.strength,1),layers}
 }
 function vibeStatus(message){const el=tab('vibePresetStatus');if(el)el.textContent=message}
 function saveVibes(){
   try{localStorage.setItem(VIBE_KEY,JSON.stringify({version:2,presets:vibePresets}))}catch(_){vibeStatus('Storage unavailable: changes last until this page closes.')}
   renderedVibes='';renderMyVibes()
 }
 function loadVibes(){
   if(vibePresets)return vibePresets;
   try{
     const saved=JSON.parse(localStorage.getItem(VIBE_KEY)||'null');
     if(saved&&saved.version===2&&Array.isArray(saved.presets)){
       vibePresets=saved.presets.map((v,i)=>cleanVibe(v,String(v.id||'saved:'+i)));
       return vibePresets
     }
   }catch(_){ }
   vibePresets=STARTING_VIBES.map(v=>cleanVibe(v,v.id));
   try{
     const old=JSON.parse(localStorage.getItem(OLD_VIBE_KEY)||'[]');
     if(Array.isArray(old))old.forEach((v,i)=>{
       if(!v||!String(v.name||'').trim())return;
       const match=vibePresets.findIndex(p=>p.name.toLowerCase()===String(v.name).trim().toLowerCase());
       if(match>=0)vibePresets[match]=cleanVibe(v,vibePresets[match].id);
       else vibePresets.push(cleanVibe(v,'imported:'+i))
     })
   }catch(_){ }
   saveVibes();return vibePresets
 }
 function selectedVibe(){return loadVibes().find(p=>p.id===selectedVibeId)}
 function duplicateVibeName(name,exceptId){return loadVibes().some(p=>p.id!==exceptId&&p.name.toLowerCase()===name.toLowerCase())}
 function editedVibe(base,name){
   const r=state.reactive||{},fallback=base||{strength:r.strength??1,layers:r.layers||{}};
   const layers={};for(const key of VIBE_LAYERS)layers[key]=safeValue(pendingVibe[key]??fallback.layers?.[key]);
   return {id:base?.id||('user:'+Date.now()+':'+Math.random().toString(36).slice(2)),name,strength:safeValue(pendingVibe.strength??fallback.strength,1),layers}
 }
 window.markVibeDirty=function(key,value){
   if(key!=='strength'&&!VIBE_LAYERS.includes(key))return;
   pendingVibe[key]=safeValue(value);vibeDirty=true;
   vibeStatus(selectedVibe()?'Unsaved changes to '+selectedVibe().name:'Enter a name and tap Add New to save these settings.')
 }
 window.vibeLayerValue=function(key,value){return pendingVibe[key]??(applyingVibe?selectedVibe()?.layers?.[key]:undefined)??value}
 window.vibeStrengthValue=function(value){return pendingVibe.strength??(applyingVibe?selectedVibe()?.strength:undefined)??value}
 window.saveCurrentVibe=function(){
   const original=selectedVibe(),name=String(tab('vibePresetName')?.value||'').trim();
   if(!original){vibeStatus('Choose a preset first, or use Add New.');return}
   if(!name){vibeStatus('Enter a preset name.');return}
   if(duplicateVibeName(name,original.id)){vibeStatus('That name is already in use.');return}
   vibePresets[vibePresets.findIndex(p=>p.id===original.id)]=editedVibe(original,name);
   pendingVibe={};vibeDirty=false;saveVibes();vibeStatus('Saved '+name+'.')
 }
 window.addCurrentVibe=function(){
   const name=String(tab('vibePresetName')?.value||'').trim();
   if(!name){vibeStatus('Enter a name for the new preset.');return}
   if(duplicateVibeName(name,null)){vibeStatus('That name is already in use.');return}
   if(loadVibes().length>=64){vibeStatus('Preset limit reached (64).');return}
   const added=editedVibe(selectedVibe(),name);added.id='user:'+Date.now()+':'+Math.random().toString(36).slice(2);vibePresets.push(added);
   selectedVibeId=added.id;pendingVibe={};vibeDirty=false;saveVibes();vibeStatus('Added '+name+'.')
 }
 window.removeMyVibe=function(){
   const current=selectedVibe();if(!current){vibeStatus('Choose a preset to delete.');return}
   if(!window.confirm('Delete '+current.name+'?'))return;
   vibePresets=vibePresets.filter(p=>p.id!==current.id);
   selectedVibeId=null;pendingVibe={};vibeDirty=false;applyToken++;applyingVibe=false;
   saveVibes();vibeStatus('Deleted '+current.name+'. Current display settings remain until you choose another preset.')
 }
 window.ensureLiveAudio=async function(){
   if(micStream)return true;
   const started=await startMic();if(!started)return false;
   if(!selectedVibeId){const pulse=loadVibes().find(v=>v.id==='starter:pulse')||loadVibes()[0];if(pulse)await applyMyVibe(pulse.id)}
   return true
 }
 window.toggleLiveAudio=async function(){if(micStream){stopMic();return}await ensureLiveAudio()};
 window.applyMyVibe=async function(id){
   const v=loadVibes().find(p=>p.id===id);if(!v)return;
   selectedVibeId=id;pendingVibe={};vibeDirty=false;applyingVibe=true;
   const token=++applyToken;renderedSelection=null;renderMyVibes();vibeStatus('Loading '+v.name+'…');
   await cmd('reactive_enabled',true);
   if(token!==applyToken)return;
   await cmd('reactive_strength',v.strength);
   for(const name of VIBE_LAYERS){if(token!==applyToken)return;await cmd('reactive_layer',{name,value:v.layers[name]})}
   if(token===applyToken){applyingVibe=false;vibeStatus('Editing '+v.name+'. Change sliders, then Save Changes.')}
 }
 window.renderMyVibes=function(){
   const boxes=[tab('myVibeButtons'),tab('manageVibeButtons')].filter(Boolean);if(!boxes.length)return;
   const presets=loadVibes(),signature=JSON.stringify(presets.map(p=>[p.id,p.name,selectedVibeId]));
   if(signature!==renderedVibes){
     renderedVibes=signature;boxes.forEach(box=>{box.innerHTML='';presets.forEach(p=>{const b=document.createElement('button');b.textContent=p.name;b.classList.toggle('active',p.id===selectedVibeId);b.onclick=()=>applyMyVibe(p.id);box.appendChild(b)});if(!presets.length)box.innerHTML='<div class="muted" style="grid-column:1/-1">No presets. Name the current settings and tap Add New.</div>'})
   }
   if(renderedSelection!==selectedVibeId){renderedSelection=selectedVibeId;const input=tab('vibePresetName');if(input)input.value=selectedVibe()?.name||''}
 }

 function syncBatchUI(){const b=document.getElementById('batchModeButton'),c=document.getElementById('batchCount');if(b){b.classList.toggle('active',batchMode);b.textContent=batchMode?'Done':'Batch Tag'}if(c)c.textContent=batchMode?(batchSelected.size+' selected · tap GIFs to add/remove'):'Batch mode off';document.querySelectorAll('.tile[data-index]').forEach(t=>t.classList.toggle('batchSelected',batchSelected.has(parseInt(t.dataset.index))))}
 window.toggleBatchMode=function(){batchMode=!batchMode;if(!batchMode)batchSelected.clear();syncBatchUI()}
 window.applyBatchTag=async function(){const input=document.getElementById('batchTagInput'),tag=(input?.value||'').trim();if(!tag||!batchSelected.size)return;await cmd('batch_add_tag',{indices:[...batchSelected],tag});batchSelected.clear();if(input)input.value='';syncBatchUI()}
 function installBatchCapture(){const g=document.getElementById('gallery');if(!g||g.dataset.batchCapture==='1')return;g.dataset.batchCapture='1';g.addEventListener('click',e=>{if(!batchMode)return;const tile=e.target.closest('.tile[data-index]');if(!tile)return;e.preventDefault();e.stopPropagation();e.stopImmediatePropagation();const i=parseInt(tile.dataset.index);if(batchSelected.has(i))batchSelected.delete(i);else batchSelected.add(i);syncBatchUI()},true)}

 window.setOverlayAudio=value=>{if(['Off','Subtle','Intense'].includes(value)){try{localStorage.setItem('festivalTotem.overlayAudio.v1',value)}catch(_){}cmd('overlay_audio_reactivity',value)}};
 window.addEventListener('load',()=>{const saved=localStorage.getItem('festivalTotem.overlayAudio.v1');if(['Off','Subtle','Intense'].includes(saved))setOverlayAudio(saved)});
 function syncOverlayAudio(){document.querySelectorAll('[data-overlay-audio]').forEach(b=>b.classList.toggle('active',b.dataset.overlayAudio===(state?.overlay_audio_reactivity||'Off')))}
 function performanceNavTick(){syncOverlayAudio();ensurePerformanceNav();renderMyVibes();markManage(currentManage);installBatchCapture();syncBatchUI()}
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

    # The runtime controls stay on Vibe; all editable mapping sliders live in Setup.
    preset_anchor = '<div id="presetButtons" class="presetGrid"></div>'
    html = html.replace(preset_anchor, '', 1)
    mapping_start = html.find('<div class="card" id="reactiveMappingCard">')
    if mapping_start >= 0:
        mapping_end = html.find('</section>', mapping_start)
        mapping = html[mapping_start:mapping_end]
        html = html[:mapping_start] + html[mapping_end:]
        html = html.replace('<div class="card"><h2>Quick Text Presets</h2>', _VIBE_EDITOR + mapping + '<div class="card"><h2>Quick Text Presets</h2>', 1)
    html = html.replace(_VIBE_CARD, _VIBE_CARD + _VIBE_PRESETS, 1)
    html = html.replace('<div id="beatLamp" class="pulseLamp"></div>', '<div id="beatLamp" class="pulseLamp"></div>' + _OVERLAY_AUDIO, 1)

    for section_id in ('live', 'edit'):
        html = _insert_after_section_start(html, section_id, _MANAGE_SWITCH)

    gallery_anchor = '<div id="gallery" class="gallery"></div>'
    if gallery_anchor in html:
        html = html.replace(gallery_anchor, _BATCH_BAR + gallery_anchor, 1)

    html = html.replace('</body>', _JS + '</body>', 1)
    return html
