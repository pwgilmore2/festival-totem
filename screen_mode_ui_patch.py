"""Vibe screen-linking control.

Runs after the main performance UI patch. Independent mode starts separate
shuffle sessions for front/back; linked mode keeps the legacy mirrored start.
"""

import phone_server

_CSS = r'''
<style>
.vibeScreenMode{display:grid;grid-template-columns:1fr 1fr;gap:8px;margin:10px 0 2px}.vibeScreenMode button{min-height:44px}.vibeScreenMode button.active{background:linear-gradient(135deg,#6c4cff,#00b8ff);box-shadow:0 0 0 2px #ffffff33 inset}
.vibeScreenHint{font-size:11px;opacity:.62;text-align:center;margin-bottom:9px}
</style>
'''
phone_server.PHONE_HTML = phone_server.PHONE_HTML.replace('</head>', _CSS + '</head>', 1)

_anchor = '<button class="vibeStart" onclick="startVibeRandom()">▶ RANDOM GIFS · BOTH SCREENS</button>'
_controls = _anchor + r'''
<div class="vibeScreenMode"><button id="screenModeIndependent" onclick="setVibeScreenMode(false)">Independent</button><button id="screenModeLinked" onclick="setVibeScreenMode(true)">Linked</button></div>
<div id="vibeScreenHint" class="vibeScreenHint">Independent: each panel gets its own shuffled GIF sequence.</div>
'''
if _anchor in phone_server.PHONE_HTML:
    phone_server.PHONE_HTML = phone_server.PHONE_HTML.replace(_anchor, _controls, 1)

_JS = r'''
<script>
(function(){
 const KEY='festivalTotem.vibeLinkedScreens.v1';
 let vibeLinked=false;
 try{vibeLinked=localStorage.getItem(KEY)==='linked'}catch(_){vibeLinked=false}

 function allVibeIds(){return (state.library||[]).map(x=>x.index).filter(Number.isInteger)}
 function syncScreenModeUI(){
   const i=document.getElementById('screenModeIndependent'),l=document.getElementById('screenModeLinked'),h=document.getElementById('vibeScreenHint');
   if(i)i.classList.toggle('active',!vibeLinked);
   if(l)l.classList.toggle('active',vibeLinked);
   if(h)h.textContent=vibeLinked?'Linked: front and back use the same shuffled sequence.':'Independent: each panel gets its own shuffled GIF sequence.';
 }
 window.setVibeScreenMode=function(linked){vibeLinked=!!linked;try{localStorage.setItem(KEY,vibeLinked?'linked':'independent')}catch(_){ }syncScreenModeUI()}

 window.startVibeRandom=async function(){
   const items=allVibeIds();if(!items.length)return;
   if(vibeLinked){
     await cmd('set_target','both');
     await cmd('slideshow_start',{indices:items,duration:5,shuffle:true,label:'All'});
   }else{
     // Separate requests cause the runtime to independently shuffle each side.
     await cmd('set_target','front');
     await cmd('slideshow_start',{indices:items,duration:5,shuffle:true,label:'All'});
     await cmd('set_target','back');
     await cmd('slideshow_start',{indices:items,duration:5,shuffle:true,label:'All'});
     await cmd('set_target','both');
   }
 }

 // In independent mode, manual stepping is also issued per panel so the two
 // sides remain separate rather than being treated as one mirrored target.
 window.vibeNext=async function(){
   const items=allVibeIds();if(!items.length)return;
   if(vibeLinked){await cmd('set_target','both');await cmd('filtered_step',{indices:items,delta:1})}
   else{await cmd('set_target','front');await cmd('filtered_step',{indices:items,delta:1});await cmd('set_target','back');await cmd('filtered_step',{indices:items,delta:1});await cmd('set_target','both')}
 }
 window.vibePrevious=async function(){
   const items=allVibeIds();if(!items.length)return;
   if(vibeLinked){await cmd('set_target','both');await cmd('filtered_step',{indices:items,delta:-1})}
   else{await cmd('set_target','front');await cmd('filtered_step',{indices:items,delta:-1});await cmd('set_target','back');await cmd('filtered_step',{indices:items,delta:-1});await cmd('set_target','both')}
 }

 setInterval(syncScreenModeUI,500);
 window.addEventListener('load',syncScreenModeUI);
})();
</script>
'''
phone_server.PHONE_HTML = phone_server.PHONE_HTML.replace('</body>', _JS + '</body>', 1)
