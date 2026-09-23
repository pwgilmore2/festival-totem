"""Desktop controller presentation for per-GIF processing profiles.

Processing commands are handled by DesktopMediaAdapter through TotemRuntime.
This module only shapes the phone UI.
"""

import phone_server

_CSS = r'''
<style>
.processingProfiles{display:grid;grid-template-columns:repeat(2,1fr);gap:8px;margin:8px 0 12px}
.processingProfiles button{min-height:52px}
.processingProfiles button.active{background:linear-gradient(135deg,#6c4cff,#00b8ff);box-shadow:0 0 0 2px #ffffff33 inset}
.processingHint{font-size:12px;opacity:.7;line-height:1.4;margin:0 0 10px}
.processingReset{width:100%;margin-top:8px;background:#4a3f55}
</style>
'''
phone_server.PHONE_HTML = phone_server.PHONE_HTML.replace('</head>', _CSS + '</head>', 1)

_MARKER = '<div class="card"><h2>Processing</h2>'
_INSERT = r'''<div class="card"><h2>Processing</h2><div class="processingHint">LED cleanup is saved per GIF. Framing stays independent.</div><div id="processingProfiles" class="processingProfiles"><button data-processing-profile="Raw" onclick="setProcessingProfile('Raw')">RAW</button><button data-processing-profile="Clean" onclick="setProcessingProfile('Clean')">CLEAN</button><button data-processing-profile="Detailed" onclick="setProcessingProfile('Detailed')">DETAILED</button><button data-processing-profile="Pixel-Dither" onclick="setProcessingProfile('Pixel-Dither')">PIXEL / DITHER</button></div>'''
phone_server.PHONE_HTML = phone_server.PHONE_HTML.replace(_MARKER, _INSERT, 1)

_OLD_RESET = '<button class="warn" style="width:100%;margin-top:8px" onclick="if(confirm(\'Reset this image?\'))cmd(\'reset_image\')">Reset Image</button>'
_NEW_RESET = '<button class="processingReset" onclick="cmd(\'reset_processing\')">Reset Processing</button><button class="warn" style="width:100%;margin-top:8px" onclick="if(confirm(\'Reset framing and processing for this image?\'))cmd(\'reset_image\')">Reset Entire Image</button>'
phone_server.PHONE_HTML = phone_server.PHONE_HTML.replace(_OLD_RESET, _NEW_RESET, 1)

_JS = r'''
<script>
function setProcessingProfile(name){cmd('set_processing_profile',name)}
function syncProcessingProfile(){
  const s=state.image_settings||{},p=s.processing_profile||'Clean';
  document.querySelectorAll('[data-processing-profile]').forEach(b=>b.classList.toggle('active',b.dataset.processingProfile===p));
}
const _processingUpdate=update;
update=async function(){await _processingUpdate();syncProcessingProfile()};
</script>
'''
phone_server.PHONE_HTML = phone_server.PHONE_HTML.replace('</body>', _JS + '</body>', 1)
