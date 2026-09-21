import phone_server
import performance_phone_server

# The legacy base poller still writes to these elements. Keep tiny hidden stubs so
# the visible Now Playing card can stay removed without breaking update().
_HIDDEN = '''<div style="display:none" aria-hidden="true"><button id="fav"></button><div id="now"></div><div id="info"></div><div id="summary"></div><div id="show"></div></div>'''
if 'id="now"' not in phone_server.PHONE_HTML:
    phone_server.PHONE_HTML = phone_server.PHONE_HTML.replace('</body>', _HIDDEN + '</body>', 1)

PhoneControlServer = performance_phone_server.PhoneControlServer
