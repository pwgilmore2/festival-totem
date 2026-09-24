"""Group the completed controller's Manage cards without duplicating their controls."""

_CSS = r'''<style>
.manageFold{margin:12px 0;border:1px solid #ffffff25;border-radius:16px;background:#171723;overflow:hidden;scroll-margin-top:124px}
.manageFold[hidden]{display:none!important}.manageFold>summary{display:flex;align-items:center;justify-content:space-between;gap:10px;min-height:63px;padding:13px 15px;cursor:pointer;list-style:none;font-size:15px;font-weight:800;letter-spacing:.015em;background:linear-gradient(120deg,#27263e,#282e43);touch-action:manipulation}
.manageFold>summary::-webkit-details-marker{display:none}.manageFold>summary:after{content:'⌄';font-size:23px;line-height:16px;color:#b0aecb}.manageFold[open]>summary:after{content:'⌃'}
.manageFold:nth-of-type(3n+1)>summary{background:linear-gradient(120deg,#362646,#283d54)}.manageFold:nth-of-type(3n+2)>summary{background:linear-gradient(120deg,#253f50,#37305b)}
.manageFoldBody{padding:4px 12px 12px}.manageFoldBody>.card{margin:9px 0 0;background:#ffffff0b}.manageFoldBody>.card+ .card{border-top:1px solid #ffffff21}
.manageFold summary:focus-visible,.sceneChooser summary:focus-visible{outline:2px solid #71d9fb;outline-offset:-3px}
</style>'''

_JS = r'''<script>
(function(){
 const sections={library:document.getElementById('live'),edit:document.getElementById('edit'),setup:document.getElementById('edit')};
 const definitions=[
   ['library','🎞️ GIF Library',['Library'],true],
   ['library','🎛️ Slideshow & transitions',['Slideshow + Background Transitions'],false],
   ['edit','🏷️ Selected GIF & tags',['Selected Asset'],true],
   ['edit','🔍 Framing',['Framing'],false],
   ['edit','🎨 Image processing',['Processing'],false],
   ['setup','🖥️ Panels',['Panels'],true],
   ['setup','🎚️ Audio presets & mappings',['Audio Preset Management','Audio Style','Sound → Visuals'],false],
   ['setup','✨ Overlay behavior',['Overlay Behavior'],false],
   ['setup','🌤 Clock & weather',['Clock + Weather Settings'],false],
   ['setup','📜 Set times',['Set Time Management'],false],
   ['setup','💬 Quick text presets',['Quick Text Presets'],false],
   ['setup','🔆 Display & playback',['Display'],false]
 ];
 const known=new Set();
 for(const [kind,label,names,initiallyOpen] of definitions){
   const root=sections[kind],cards=[...root.children].filter(el=>el.classList.contains('card')&&names.includes(el.querySelector('h2')?.textContent.trim()));
   if(!cards.length)continue;
   const fold=document.createElement('details');fold.className='manageFold';fold.dataset.manageGroup=kind;fold.open=initiallyOpen;
   const summary=document.createElement('summary');summary.textContent=label;
   const body=document.createElement('div');body.className='manageFoldBody';
   fold.append(summary,body);root.appendChild(fold);
   for(const card of cards){known.add(card);body.appendChild(card)}
 }
 // If another transform adds a card later, keep it reachable under Manage.
 for(const root of [sections.library,sections.edit])for(const card of [...root.children].filter(el=>el.classList.contains('card')&&!known.has(el))){
   const fold=document.createElement('details');fold.className='manageFold';fold.dataset.manageGroup=root===sections.library?'library':'setup';
   const summary=document.createElement('summary');summary.textContent=card.querySelector('h2')?.textContent.trim()||'More settings';
   const body=document.createElement('div');body.className='manageFoldBody';fold.append(summary,body);root.appendChild(fold);body.appendChild(card)
 }
 window.selectManageGroup=function(kind){document.querySelectorAll('.manageFold').forEach(fold=>{fold.hidden=fold.dataset.manageGroup!==kind})};
 selectManageGroup('library');
})();
</script>'''


def apply(html):
    return html.replace('</head>', _CSS + '</head>', 1).replace('</body>', _JS + '</body>', 1)
