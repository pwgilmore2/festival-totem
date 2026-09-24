"""Presentation transform for Vibe screen-linking controls."""

_CSS = r'''
<style>
.vibeScreenMode{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:8px;margin:10px 0 2px}.vibeScreenMode button{min-height:52px;padding:8px 5px;font-size:12px}.vibeScreenMode button:nth-child(1){background:linear-gradient(145deg,#333f69,#295779)}.vibeScreenMode button:nth-child(2){background:linear-gradient(145deg,#58409a,#356192)}.vibeScreenMode button:nth-child(3){background:linear-gradient(145deg,#80438a,#493d8c)}.vibeScreenMode button.active{background:#343442;box-shadow:none}.vibeScreenMode button.active:after{content:'';display:inline-block;width:7px;height:7px;margin-left:7px;background:#5bebb0;border-radius:50%}
.vibeScreenHint{font-size:11px;opacity:.62;text-align:center;margin-bottom:9px}
#panelCard{scroll-margin-top:120px}.panelTarget{margin-top:13px;padding-top:13px;border-top:1px solid #ffffff22}.panelTarget[hidden]{display:none}.panelTarget h3{font-size:14px;margin:0 0 8px}.panelTarget button.active{background:#343442}.panelTarget button.active:after{content:'';display:inline-block;width:7px;height:7px;margin-left:7px;background:#5bebb0;border-radius:50%}
</style>
'''

_PANEL_CARD = r'''<div id="panelCard" class="card"><h2>Panels</h2><div class="muted">Choose how the two sides play. Front / Both / Back appears when they run independently.</div>
<div class="vibeScreenMode"><button id="screenModeIndependent" onclick="setVibeScreenMode('independent')">Independent</button><button id="screenModeLinked" onclick="setVibeScreenMode('linked')">Linked</button><button id="screenModeMirrored" onclick="setVibeScreenMode('mirrored')">Mirrored</button></div>
<div id="vibeScreenHint" class="vibeScreenHint"></div>'''

_JS = r'''
<script>
(function(){
 const KEY='festivalTotem.vibeLinkedScreens.v1';
 let vibeLinked=false;
 try{vibeLinked=localStorage.getItem(KEY)==='linked'}catch(_){vibeLinked=false}

 function allVibeIds(){return (state.library||[]).map(x=>x.index).filter(Number.isInteger)}
 function syncScreenModeUI(){
   const i=document.getElementById('screenModeIndependent'),l=document.getElementById('screenModeLinked'),m=document.getElementById('screenModeMirrored'),h=document.getElementById('vibeScreenHint');
   const mirrored=!!state?.mirrored,linked=vibeLinked&&!mirrored;
   if(i)i.classList.toggle('active',!linked&&!mirrored);
   if(l)l.classList.toggle('active',linked);
   if(m)m.classList.toggle('active',mirrored);
   if(h)h.textContent=mirrored?'Mirrored: one rendered image is copied to both panels.':(linked?'Linked: both panels start together, each rendered separately.':'Independent: each panel gets its own shuffled GIF sequence.');
   const target=document.getElementById('targetCard');if(target)target.hidden=linked||mirrored;
 }
 window.setVibeScreenMode=async function(mode){if(!['independent','linked','mirrored'].includes(mode))return;
   vibeLinked=mode==='linked';try{localStorage.setItem(KEY,vibeLinked?'linked':'independent')}catch(_){ }
   if(mode==='mirrored'){await cmd('mirror_displays',true)}
   else if(state?.mirrored){await cmd('mirror_displays',false)}
   if(mode!=='independent')await cmd('set_target','both');
   syncScreenModeUI()
 }

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
 window.addEventListener('load',()=>{if(vibeLinked&&!state?.mirrored)cmd('set_target','both');syncScreenModeUI()});
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
