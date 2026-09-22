"""Final controller organization around the live performance workflow.

This patch intentionally runs last. It changes navigation/presentation only;
existing runtime commands and management screens remain available.
"""

import phone_server

_CSS = r'''
<style>
/* Primary controller = the four things actually used while performing. */
.tabs{gap:7px!important}
.tabs .performancePrimary{min-width:88px!important}
.tabs .managementTab{margin-left:auto;background:#2b2b35!important;color:#ddd!important}
.tabs .managementTab.active{background:#7063d7!important;color:white!important}
#tabLive,#tabLibrary,#tabEdit,#tabSetup{display:none!important}

.vibeLaunch{background:radial-gradient(circle at 10% 0%,#00e5ff2c,transparent 34%),radial-gradient(circle at 95% 0%,#8b5cff30,transparent 38%),#ffffff12}
.vibeLaunch h2{font-size:22px!important;margin-bottom:4px!important}
.vibeLaunch .vibeSub{font-size:12px;opacity:.68;line-height:1.4;margin-bottom:12px}
.vibeStart{width:100%;min-height:66px;font-size:18px;background:linear-gradient(135deg,#6c4cff,#00b8ff);box-shadow:0 8px 24px #0006}
.vibeTransport{display:grid;grid-template-columns:1fr 1fr;gap:8px;margin-top:8px}.vibeTransport button{min-height:48px}

.manageSwitcher{display:grid;grid-template-columns:repeat(3,1fr);gap:7px;margin:2px 0 12px;position:sticky;top:62px;z-index:16;padding:7px;background:#101016ed;backdrop-filter:blur(10px);border-radius:13px}
.manageSwitcher button{min-height:42px;font-size:13px}.manageSwitcher button.active{background:#7063d7}
.manageHint{font-size:11px;opacity:.62;margin:-4px 0 8px;text-align:center}

/* Management screens should feel backstage, not like live-performance tabs. */
body.manageMode #targetCard{display:none!important}
body.manageMode .manageSwitcher{display:grid}
body:not(.manageMode) .manageSwitcher{display:none}

/* The old Overlay naming is fully retired. */
#tabText{}

@media(max-width:520px){
 .tabs button.performancePrimary{min-width:78px!important}
 .tabs .managementTab{min-width:72px!important}
 .manageSwitcher{top:60px}
}
</style>
'''
phone_server.PHONE_HTML = phone_server.PHONE_HTML.replace('</head>', _CSS + '</head>', 1)

# Add the one performance action the user reaches for first directly to Audio/Vibe.
_VIBE_CARD = r'''
<div id="vibeLaunchCard" class="card vibeLaunch">
<h2>Vibe</h2>
<div class="vibeSub">Start with random GIFs on both screens, then bring the phone mic in and shape the music response below.</div>
<button class="vibeStart" onclick="startVibeRandom()">▶ RANDOM GIFS · BOTH SCREENS</button>
<div class="vibeTransport"><button onclick="vibePrevious()">◀ Previous</button><button onclick="vibeNext()">Next ▶</button></div>
</div>
'''
_audio_anchor = '<section id="audio" class="view">'
if _audio_anchor in phone_server.PHONE_HTML:
    phone_server.PHONE_HTML = phone_server.PHONE_HTML.replace(_audio_anchor, _audio_anchor + _VIBE_CARD, 1)

# Shared backstage switcher appears inside all current management surfaces.
_MANAGE_SWITCH = r'''
<div class="manageSwitcher">
<button data-manage="library" onclick="openManage('library')">GIF Library</button>
<button data-manage="edit" onclick="openManage('edit')">Edit / Tags</button>
<button data-manage="setup" onclick="openManage('setup')">Setup</button>
</div>
<div class="manageHint">Backstage tools — hidden from the main performance flow.</div>
'''
for _section in ('library', 'edit', 'setup'):
    _needle = f'<section id="{_section}" class="view">'
    if _needle in phone_server.PHONE_HTML:
        phone_server.PHONE_HTML = phone_server.PHONE_HTML.replace(_needle, _needle + _MANAGE_SWITCH, 1)

_JS = r'''
<script>
(function(){
 let _performanceBaseView=view;
 let currentManage='library';

 function tab(id){return document.getElementById(id)}
 function section(id){return document.getElementById(id)}
 function tabsRoot(){return document.querySelector('.tabs')}

 function ensurePerformanceNav(){
   const root=tabsRoot();if(!root)return;
   const audio=tab('tabAudio'),guest=tab('tabGuest'),icons=tab('tabIcons'),text=tab('tabText');
   if(audio){audio.textContent=(state.audio&&state.audio.fresh)?'Vibe ●':'Vibe';audio.classList.add('performancePrimary')}
   if(guest){if(!guest.textContent.includes('●'))guest.textContent='Chaos';else guest.textContent='Chaos ●';guest.classList.add('performancePrimary')}
   if(icons){icons.textContent=(state.icon&&state.icon.icon_enabled)?'Icons ●':'Icons';icons.classList.add('performancePrimary')}
   if(text){text.textContent=(state.text&&state.text.enabled)?'Text ●':'Text';text.classList.add('performancePrimary')}

   // Keep exact live order regardless of which older patch inserted each tab.
   [audio,guest,icons,text].filter(Boolean).forEach(el=>root.appendChild(el));

   let manage=tab('tabManage');
   if(!manage){
     manage=document.createElement('button');manage.id='tabManage';manage.className='managementTab';manage.textContent='Manage';manage.onclick=()=>openManage(currentManage||'library');root.appendChild(manage)
   }else root.appendChild(manage);
 }

 function setManageMode(on){
   document.body.classList.toggle('manageMode',!!on);
   const m=tab('tabManage');if(m)m.classList.toggle('active',!!on);
 }

 window.openManage=function(kind){
   if(!['library','edit','setup'].includes(kind)||!section(kind))kind='library';
   currentManage=kind;
   setManageMode(true);
   _performanceBaseView(kind);
   // Base view activates hidden legacy tab; make Manage the visible active control.
   document.querySelectorAll('.tabs button').forEach(b=>b.classList.remove('active'));
   const m=tab('tabManage');if(m)m.classList.add('active');
   document.querySelectorAll('[data-manage]').forEach(b=>b.classList.toggle('active',b.dataset.manage===kind));
   const tc=document.getElementById('targetCard');if(tc)tc.style.display='none';
 }

 view=function(name){
   if(name==='library'||name==='edit'||name==='setup'){openManage(name);return}
   setManageMode(false);
   _performanceBaseView(name);
   const m=tab('tabManage');if(m)m.classList.remove('active');
 }

 window.startVibeRandom=function(){
   const items=(state.library||[]).map(x=>x.index).filter(x=>Number.isInteger(x));
   if(!items.length)return;
   cmd('set_target','both');
   cmd('slideshow_start',{indices:items,duration:5,shuffle:true,label:'All'});
 }
 window.vibeNext=function(){
   const items=(state.library||[]).map(x=>x.index).filter(x=>Number.isInteger(x));
   if(items.length){cmd('set_target','both');cmd('filtered_step',{indices:items,delta:1})}
 }
 window.vibePrevious=function(){
   const items=(state.library||[]).map(x=>x.index).filter(x=>Number.isInteger(x));
   if(items.length){cmd('set_target','both');cmd('filtered_step',{indices:items,delta:-1})}
 }

 // Older status writers still run; this is the final visible naming/order pass.
 function performanceNavTick(){
   ensurePerformanceNav();
   const text=tab('tabText');if(text)text.textContent=(state.text&&state.text.enabled)?'Text ●':'Text';
   const audio=tab('tabAudio');if(audio)audio.textContent=(state.audio&&state.audio.fresh)?'Vibe ●':'Vibe';
   const guest=tab('tabGuest');if(guest)guest.textContent=(state.guest&&state.guest.active)?'Chaos ●':'Chaos';
   const icons=tab('tabIcons');if(icons)icons.textContent=(state.icon&&state.icon.icon_enabled)?'Icons ●':'Icons';
   document.querySelectorAll('[data-manage]').forEach(b=>b.classList.toggle('active',document.body.classList.contains('manageMode')&&b.dataset.manage===currentManage));
 }
 setInterval(performanceNavTick,250);
 window.addEventListener('load',()=>{
   ensurePerformanceNav();
   // The controller now lands where the real performance workflow begins.
   setTimeout(()=>{if(section('audio'))view('audio')},80);
 });
})();
</script>
'''
phone_server.PHONE_HTML = phone_server.PHONE_HTML.replace('</body>', _JS + '</body>', 1)
