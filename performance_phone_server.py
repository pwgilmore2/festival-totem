import phone_server
import secure_phone_server


# Audio analysis still runs every animation frame in the browser, so the
# on-screen meters remain smooth. Only network updates are throttled.
html = phone_server.PHONE_HTML
html = html.replace(
    'if(ts-lastAudioSend>65){lastAudioSend=ts;cmd("audio_frame",{volume,bass,mids,highs,beat})}',
    'if(ts-lastAudioSend>110){lastAudioSend=ts;cmd("audio_frame",{volume,bass,mids,highs,beat})}',
)
html = html.replace(
    'demoTimer=setInterval(demoTick,70)',
    'demoTimer=setInterval(demoTick,110)',
)
phone_server.PHONE_HTML = html

PhoneControlServer = secure_phone_server.PhoneControlServer
