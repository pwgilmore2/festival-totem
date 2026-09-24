"""Presentation transform for Vibe screen-linking controls."""

_CSS = r'''
<style>
.vibeScreenMode{display:grid;grid-template-columns:1fr 1fr;gap:8px;margin:10px 0 2px}.vibeScreenMode button{min-height:44px}.vibeScreenMode button.active{background:#343442;box-shadow:none}.vibeScreenMode button.active:after{content:'';display:inline-block;width:7px;height:7px;margin-left:7px;background:#5bebb0;border-radius:50%}
.vibeScreenHint{font-size:11px;opacity:.62;text-align:center;margin-bottom:9px}
#panelCard{scroll-margin-top:120px}.panelTarget{margin-top:13px;padding-top:13px;border-top:1px solid #ffffff22}.panelTarget[hidden]{display:none}.panelTarget h3{font-size:14px;margin:0 0 8px}.panelTarget button.active{background:#343442}.panelTarget button.active:after{content:'';display:inline-block;width:7px;height:7px;margin-left:7px;background:#5bebb0;border-radius:50%}
</style>
'''

_PANEL_CARD = r'''<div id="panelCard" class="card"><h2>Panels</h2><div class="muted">Choose how the two sides play. Front / Both / Back appears when they run independently.</div>
<div class="vibeScreenMode"><button id="screenModeIndependent" onclick="setVibeScreenMode(false)">Independent</button><button id="screenModeLinked" onclick="setVibeScreenMode(true)">Linked</button></div>
<div id="vibeScreenHint" class="vibeScreenHint"></div><button id="mirrorButton" onclick="toggleTotemMirror()">Mirror both panels</button>'''

_JS = r'''
<script>
(function(){
 const KEY='festivalTotem.vibeLinkedScreens.v1';
 let vibeLinked=false;
 try{vibeLinked=localStorage.getItem(KEY)==='linked'}catch(_){vibeLinked=false}

 function allVibeIds(){return (state.library||[]).map(x=>x.index).filter(Number.isInteger)}
 function syncScreenModeUI(){
   const i=document.getElementById('screenModeIndependent'),l=document.getElementById('screenModeLinked'),h=document.getElementById('vibeScreenHint');
   const linked=vibeLinked||!!state?.mirrored;
   if(i){i.classList.toggle('active',!linked);i.disabled=!!state?.mirrored}
   if(l)l.classList.toggle('active',linked);
   if(h)h.textContent=state?.mirrored?'Mirrored: one rendered image is shown on both panels.':(linked?'Linked: front and back use the same shuffled sequence.':'Independent: each panel gets its own shuffled GIF sequence.');
   const target=document.getElementById('targetCard');if(target)target.hidden=linked;
 }
 window.setVibeScreenMode=function(linked){vibeLinked=!!linked;try{localStorage.setItem(KEY,vibeLinked?'linked':'independent')}catch(_){ }if(vibeLinked)cmd('set_target','both');syncScreenModeUI()}

 window.startVibeRandom=async function(){
   const items=allVibeIds();if(!items.length)return;
   if(vibeLinked||!!state?.mirrored){
     await cmd('set_target','both');
     await cmd('slideshow_start',{indices:items,duration:5,shuffle:true,label:'All'});
   }else{
     await cmd('set_target','front');
     await cmd('slideshow_start',{indices:items,duration:5,shuffle:true,label:'All'});
     await cmd('set_target','back');
     await cmd('slideshow_start',{indices:items,duration:5,shuffle:true,label:'All'});
     await cmd('set_target','both');
   }
 }

 window.vibeNext=async function(){
   const items=allVibeIds();if(!items.length)return;
   if(vibeLinked||!!state?.mirrored){await cmd('set_target','both');await cmd('filtered_step',{indices:items,delta:1})}
   else{await cmd('set_target','front');await cmd('filtered_step',{indices:items,delta:1});await cmd('set_target','back');await cmd('filtered_step',{indices:items,delta:1});await cmd('set_target','both')}
 }
 window.vibePrevious=async function(){
   const items=allVibeIds();if(!items.length)return;
   if(vibeLinked||!!state?.mirrored){await cmd('set_target','both');await cmd('filtered_step',{indices:items,delta:-1})}
   else{await cmd('set_target','front');await cmd('filtered_step',{indices:items,delta:-1});await cmd('set_target','back');await cmd('filtered_step',{indices:items,delta:-1});await cmd('set_target','both')}
 }

 setInterval(syncScreenModeUI,500);
 window.addEventListener('load',()=>{if(vibeLinked)cmd('set_target','both');syncScreenModeUI()});
})();
</script>
'''


def apply(html):
    html = html.replace('</head>', _CSS + '</head>', 1)
    start = html.find('<div id="targetCard" class="card">')
    if start >= 0:
        end = html.find('</div></div>', start) + len('</div></div>')
        target = html[start:end].replace('class="card"', 'class="panelTarget"', 1).replace('<h2>Target</h2>', '<h3>Target</h3>', 1)
        html = html[:start] + html[end:]
        edit = html.find('<section id="edit" class="view">')
        hint = '<div class="manageHint">Backstage tools — hidden from the main performance flow.</div>'
        if edit >= 0:
            before, after = html[:edit], html[edit:]
            html = before + after.replace(hint, hint + _PANEL_CARD + target + '</div>', 1)
    html = html.replace('</body>', _JS + '</body>', 1)
    return html
