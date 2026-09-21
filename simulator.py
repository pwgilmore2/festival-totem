import io
import math
import random
import time
import pygame
from PIL import Image
from display import VirtualDisplay
from effects import EFFECTS, hsv_to_rgb
from controller import TotemController
from text import draw_scrolling_text
from particles import ParticleSystem
from image_assets import ImageLibrary
from audio_phone_server import PhoneControlServer
W, H, S, GAP, UI = (64, 32, 8, 24, 175)
PW, PH = (W * S, H * S)
pygame.init()
screen = pygame.display.set_mode((PW * 2 + GAP, PH + UI))
pygame.display.set_caption('Festival Totem Simulator')
clock = pygame.time.Clock()
font = pygame.font.SysFont(None, 22)
library = ImageLibrary('assets/images', W, H)
displays = {'front': VirtualDisplay(W, H), 'back': VirtualDisplay(W, H)}
particles = {side: ParticleSystem(W, H, count=60) for side in ('front', 'back')}
MODES = ['crop', 'fit', 'pixel', 'optimize', 'dither']
REACTIVE_PRESETS = ['Pulse', 'Neon', 'Spark', 'Chaos']
active_target = 'both'
audio = {'volume': 0.0, 'bass': 0.0, 'mids': 0.0, 'highs': 0.0, 'beat': False, 'last_update': 0.0}

def slideshow_state():
    return {'active': False, 'indices': [], 'position': 0, 'duration': 5.0, 'elapsed': 0.0, 'shuffle': False, 'label': 'All'}

def reactive_state():
    return {'enabled': False, 'strength': 0.65, 'preset': 'Pulse'}
panels = {side: {'image_index': 0, 'slideshow': slideshow_state(), 'reactive': reactive_state()} for side in ('front', 'back')}

def metadata(asset):
    if asset is None:
        return {'tags': [], 'favorite': False}
    return library.metadata_entry(asset.path.name)

def asset(side):
    if not len(library):
        return None
    return library.get(panels[side]['image_index'])

def target_sides():
    if active_target == 'both':
        return ['front', 'back']
    return [active_target]

def reference_side():
    if active_target == 'back':
        return 'back'
    return 'front'

def reference_asset():
    return asset(reference_side())

def save_asset(current_asset):
    if current_asset is None:
        return
    current_asset.settings.clamp()
    current_asset.clear_cache()
    library.save_asset(current_asset)

def text_fx(display, t):
    draw_scrolling_text(display, 'FESTIVAL MODE', t, color=hsv_to_rgb(t * 80 % 360), scale=1, speed=12)

def party_fx(side, display, t):
    EFFECTS['Plasma'](display, t)
    particles[side].draw(display)

def image_fx(side, display, t):
    current_asset = asset(side)
    if current_asset:
        current_asset.render(display, t, current_asset.settings)
    else:
        display.clear()

def make_effects(side):
    return {**EFFECTS, 'Text': text_fx, 'Party': lambda display, t, s=side: party_fx(s, display, t), 'Image': lambda display, t, s=side: image_fx(s, display, t)}
controllers = {side: TotemController(make_effects(side)) for side in ('front', 'back')}

def clamp01(value):
    return max(0.0, min(1.0, float(value)))

def audio_fresh():
    return time.monotonic() - audio['last_update'] < 1.0

def zoom_pixels(display, amount):
    if amount <= 0.001:
        return
    source = [row[:] for row in display.pixels]
    zoom = 1.0 + amount
    center_x = (display.width - 1) / 2.0
    center_y = (display.height - 1) / 2.0
    for y in range(display.height):
        for x in range(display.width):
            source_x = int(round(center_x + (x - center_x) / zoom))
            source_y = int(round(center_y + (y - center_y) / zoom))
            source_x = max(0, min(display.width - 1, source_x))
            source_y = max(0, min(display.height - 1, source_y))
            display.set_pixel(x, y, source[source_y][source_x])

def hue_shift(display, degrees):
    if abs(degrees) < 0.5:
        return
    for y in range(display.height):
        for x in range(display.width):
            r, g, b = display.get_pixel(x, y)
            color = pygame.Color(r, g, b)
            h, s, v, a = color.hsva
            color.hsva = ((h + degrees) % 360, s, v, a)
            display.set_pixel(x, y, (color.r, color.g, color.b))

def brighten(display, amount):
    if amount <= 0.001:
        return
    multiplier = 1.0 + amount
    for y in range(display.height):
        for x in range(display.width):
            r, g, b = display.get_pixel(x, y)
            display.set_pixel(x, y, (min(255, int(r * multiplier)), min(255, int(g * multiplier)), min(255, int(b * multiplier))))

def beat_flash(display, amount):
    if amount <= 0.001:
        return
    amount = clamp01(amount)
    for y in range(display.height):
        for x in range(display.width):
            r, g, b = display.get_pixel(x, y)
            display.set_pixel(x, y, (int(r + (255 - r) * amount), int(g + (255 - g) * amount), int(b + (255 - b) * amount)))

def sparkle_layer(display, amount, seed):
    if amount <= 0.02:
        return
    rng = random.Random(seed)
    count = int(2 + amount * 50)
    for _ in range(count):
        x = rng.randrange(display.width)
        y = rng.randrange(display.height)
        intensity = int(120 + 135 * rng.random())
        display.set_pixel(x, y, (intensity, intensity, intensity))

def apply_reactive(side, display, frame_number):
    reactive = panels[side]['reactive']
    if not reactive['enabled']:
        return
    if not audio_fresh():
        return
    strength = reactive['strength']
    bass = audio['bass'] * strength
    mids = audio['mids'] * strength
    highs = audio['highs'] * strength
    volume = audio['volume'] * strength
    preset = reactive['preset']
    if preset == 'Pulse':
        zoom_pixels(display, bass * 0.22)
        brighten(display, volume * 0.25)
        if audio['beat']:
            beat_flash(display, 0.22 + strength * 0.18)
    elif preset == 'Neon':
        hue_shift(display, mids * 85 + highs * 45)
        brighten(display, bass * 0.3)
        if audio['beat']:
            beat_flash(display, 0.16)
    elif preset == 'Spark':
        brighten(display, bass * 0.18)
        sparkle_layer(display, highs, frame_number + (1000 if side == 'back' else 0))
        if audio['beat']:
            sparkle_layer(display, min(1.0, 0.5 + strength), frame_number * 17)
    elif preset == 'Chaos':
        zoom_pixels(display, bass * 0.28)
        hue_shift(display, mids * 120 + highs * 90)
        brighten(display, volume * 0.32)
        sparkle_layer(display, highs * 0.9, frame_number * 7 + (500 if side == 'back' else 0))
        if audio['beat']:
            beat_flash(display, 0.35)

def stop_show(side):
    show = panels[side]['slideshow']
    show['active'] = False
    show['elapsed'] = 0.0

def select_for_side(side, index, stop=True):
    if not len(library):
        return
    try:
        index = int(index)
    except (TypeError, ValueError):
        return
    panels[side]['image_index'] = max(0, min(len(library) - 1, index))
    if stop:
        stop_show(side)
    controllers[side].set_effect('Image')

def select_image(index):
    for side in target_sides():
        select_for_side(side, index)

def clean_indices(values):
    result = []
    if not isinstance(values, list):
        return result
    for value in values:
        try:
            index = int(value)
        except (TypeError, ValueError):
            continue
        if 0 <= index < len(library) and index not in result:
            result.append(index)
    return result

def step_filtered(value):
    if not isinstance(value, dict):
        return
    indices = clean_indices(value.get('indices', []))
    if not indices:
        return
    try:
        delta = int(value.get('delta', 1))
    except (TypeError, ValueError):
        delta = 1
    for side in target_sides():
        current = panels[side]['image_index']
        try:
            position = indices.index(current)
        except ValueError:
            position = -1 if delta > 0 else 0
        select_for_side(side, indices[(position + delta) % len(indices)])

def start_show(value):
    if not isinstance(value, dict):
        return
    indices = clean_indices(value.get('indices', []))
    if not indices:
        return
    try:
        duration = max(1.0, min(120.0, float(value.get('duration', 5))))
    except (TypeError, ValueError):
        duration = 5.0
    shuffle = bool(value.get('shuffle', False))
    label = str(value.get('label', 'Selection'))[:80]
    order = list(indices)
    if shuffle:
        random.shuffle(order)
    for side in target_sides():
        panels[side]['slideshow'].update(active=True, indices=list(order), position=0, duration=duration, elapsed=0.0, shuffle=shuffle, label=label)
        select_for_side(side, order[0], stop=False)

def update_shows(dt):
    for side in ('front', 'back'):
        show = panels[side]['slideshow']
        if not show['active'] or not show['indices']:
            continue
        show['elapsed'] += dt
        if show['elapsed'] < show['duration']:
            continue
        show['elapsed'] %= show['duration']
        show['position'] = (show['position'] + 1) % len(show['indices'])
        if show['shuffle'] and show['position'] == 0 and (len(show['indices']) > 1):
            random.shuffle(show['indices'])
        select_for_side(side, show['indices'][show['position']], stop=False)

def thumbnail(index):
    try:
        index = int(index)
        current_asset = library.get(index)
    except Exception:
        return None
    if not current_asset or not current_asset.frames:
        return None
    try:
        preview = current_asset.prepare_frame(current_asset.frames[0], current_asset.settings).resize((256, 128), Image.Resampling.NEAREST)
        output = io.BytesIO()
        preview.save(output, format='JPEG', quality=82, optimize=True)
        return output.getvalue()
    except Exception as error:
        print('Thumbnail error:', error)
        return None
server = PhoneControlServer(8765)
server.set_thumbnail_provider(thumbnail)
phone_url = server.start()

def set_target(value):
    global active_target
    if value in ('front', 'back', 'both'):
        active_target = value

def set_effect(value):
    for side in target_sides():
        if value in controllers[side].effects:
            controllers[side].set_effect(value)

def master(attribute, value, minimum, maximum):
    try:
        value = max(minimum, min(maximum, float(value)))
    except (TypeError, ValueError):
        return
    for side in target_sides():
        setattr(controllers[side], attribute, value)

def toggle_pause():
    pause = not all((controllers[side].paused for side in target_sides()))
    for side in target_sides():
        controllers[side].paused = pause

def reload_library():
    old_names = {side: asset(side).path.name if asset(side) else None for side in ('front', 'back')}
    library.load()
    for side in ('front', 'back'):
        panels[side]['image_index'] = 0
        stop_show(side)
        if old_names[side]:
            for index, item in enumerate(library.assets):
                if item.path.name == old_names[side]:
                    panels[side]['image_index'] = index
                    break

def update_audio(value):
    if not isinstance(value, dict):
        return
    for key in ('volume', 'bass', 'mids', 'highs'):
        if key in value:
            try:
                audio[key] = clamp01(value[key])
            except Exception:
                pass
    audio['beat'] = bool(value.get('beat', False))
    audio['last_update'] = time.monotonic()

def set_reactive_enabled(value):
    enabled = bool(value)
    for side in target_sides():
        panels[side]['reactive']['enabled'] = enabled

def set_reactive_strength(value):
    try:
        value = max(0.0, min(1.5, float(value)))
    except (TypeError, ValueError):
        return
    for side in target_sides():
        panels[side]['reactive']['strength'] = value

def set_reactive_preset(value):
    if value not in REACTIVE_PRESETS:
        return
    for side in target_sides():
        panels[side]['reactive']['preset'] = value

def command(data):
    command_name = data.get('command')
    value = data.get('value')
    if command_name == 'set_target':
        set_target(value)
        return
    if command_name == 'effect':
        set_effect(value)
        return
    if command_name == 'select_image':
        select_image(value)
        return
    if command_name == 'filtered_step':
        step_filtered(value)
        return
    if command_name == 'slideshow_start':
        start_show(value)
        return
    if command_name == 'slideshow_stop':
        for side in target_sides():
            stop_show(side)
        return
    if command_name == 'brightness':
        master('brightness', value, 0.1, 1.0)
        return
    if command_name == 'speed':
        master('speed', value, 0.1, 5.0)
        return
    if command_name == 'toggle_pause':
        toggle_pause()
        return
    if command_name == 'reload_library':
        reload_library()
        return
    if command_name == 'audio_frame':
        update_audio(value)
        return
    if command_name == 'reactive_enabled':
        set_reactive_enabled(value)
        return
    if command_name == 'reactive_strength':
        set_reactive_strength(value)
        return
    if command_name == 'reactive_preset':
        set_reactive_preset(value)
        return
    if command_name in ('mode_prev', 'mode_next'):
        current_asset = reference_asset()
        if current_asset:
            try:
                index = MODES.index(current_asset.settings.mode)
            except ValueError:
                index = 0
            if command_name == 'mode_prev':
                index -= 1
            else:
                index += 1
            current_asset.settings.mode = MODES[index % len(MODES)]
            save_asset(current_asset)
        return
    current_asset = reference_asset()
    if command_name == 'toggle_favorite':
        if current_asset:
            library.set_favorite(current_asset, not bool(metadata(current_asset).get('favorite', False)))
        return
    if command_name == 'set_favorite_index' and isinstance(value, dict):
        try:
            target_asset = library.get(int(value.get('index')))
        except Exception:
            target_asset = None
        if target_asset:
            library.set_favorite(target_asset, bool(value.get('favorite', False)))
        return
    if command_name == 'set_tags':
        if current_asset and isinstance(value, list):
            cleaned = list(dict.fromkeys((str(item).strip() for item in value if str(item).strip())))
            library.set_tags(current_asset, cleaned)
        return
    if current_asset is None:
        return
    settings = current_asset.settings
    changed = False
    if command_name in ('zoom', 'crop_x', 'crop_y', 'contrast', 'saturation', 'gamma'):
        try:
            setattr(settings, command_name, float(value))
            changed = True
        except (TypeError, ValueError):
            pass
    elif command_name == 'toggle_sharpen':
        settings.sharpen = not settings.sharpen
        changed = True
    elif command_name == 'toggle_dither':
        settings.dither = not settings.dither
        changed = True
    elif command_name == 'reset_image':
        settings.reset()
        changed = True
    if changed:
        save_asset(current_asset)

def phone_panel(side):
    controller = controllers[side]
    current_asset = asset(side)
    show = panels[side]['slideshow']
    reactive = panels[side]['reactive']
    result = {'effect': controller.effect_name, 'speed': controller.speed, 'brightness': controller.brightness, 'paused': controller.paused, 'image_index_zero': panels[side]['image_index'], 'image_index': 0, 'image_name': None, 'image_mode': None, 'image_settings': None, 'image_tags': [], 'image_favorite': False, 'slideshow': {'active': show['active'], 'duration': show['duration'], 'shuffle': show['shuffle'], 'label': show['label'], 'count': len(show['indices'])}, 'reactive': {'enabled': reactive['enabled'], 'strength': reactive['strength'], 'preset': reactive['preset']}}
    if current_asset:
        item_metadata = metadata(current_asset)
        result.update(image_index=panels[side]['image_index'] + 1, image_name=current_asset.path.name, image_mode=current_asset.settings.mode, image_settings=current_asset.settings.to_dict(), image_tags=item_metadata.get('tags', []), image_favorite=bool(item_metadata.get('favorite', False)))
    return result

def update_phone():
    items = []
    for index, item in enumerate(library.assets):
        item_metadata = metadata(item)
        items.append({'index': index, 'name': item.path.name, 'tags': item_metadata.get('tags', []), 'favorite': bool(item_metadata.get('favorite', False))})
    reference = phone_panel(reference_side())
    server.update_state({'target': active_target, 'reference_side': reference_side(), 'image_count': len(library), 'library': items, 'effects': list(controllers['front'].effects), 'reactive_presets': REACTIVE_PRESETS, 'audio': {'volume': audio['volume'], 'bass': audio['bass'], 'mids': audio['mids'], 'highs': audio['highs'], 'beat': audio['beat'], 'fresh': audio_fresh()}, 'panels': {'front': phone_panel('front'), 'back': phone_panel('back')}, **reference})

def draw_panel(side, offset_x):
    display = displays[side]
    controller = controllers[side]
    for y in range(H):
        for x in range(W):
            color = display.get_pixel(x, y)
            brightness = controller.brightness
            pygame.draw.rect(screen, (int(color[0] * brightness), int(color[1] * brightness), int(color[2] * brightness)), (offset_x + x * S, y * S, S - 1, S - 1))

def draw_ui():
    front = phone_panel('front')
    back = phone_panel('back')
    audio_text = f"AUDIO B:{audio['bass']:.2f} M:{audio['mids']:.2f} H:{audio['highs']:.2f} V:{audio['volume']:.2f}"
    if not audio_fresh():
        audio_text += '  (idle)'
    screen.blit(font.render(f"FRONT: {front['effect']} | {front['image_name'] or '-'} | {front['reactive']['preset']}{(' ON' if front['reactive']['enabled'] else ' OFF')}", True, (220, 220, 220)), (10, PH + 10))
    screen.blit(font.render(f"BACK: {back['effect']} | {back['image_name'] or '-'} | {back['reactive']['preset']}{(' ON' if back['reactive']['enabled'] else ' OFF')}", True, (220, 220, 220)), (10, PH + 36))
    screen.blit(font.render(f'Target: {active_target.upper()}   {audio_text}', True, (190, 190, 190)), (10, PH + 62))
    screen.blit(font.render(phone_url, True, (170, 170, 170)), (10, PH + 88))

def handle_key(key):
    if key == pygame.K_ESCAPE:
        return False
    mapping = {pygame.K_1: 'Rainbow', pygame.K_2: 'Waves', pygame.K_3: 'Plasma', pygame.K_4: 'Stars', pygame.K_5: 'Text', pygame.K_6: 'Party', pygame.K_7: 'Image'}
    if key in mapping:
        set_effect(mapping[key])
    elif key == pygame.K_f:
        set_target('front')
    elif key == pygame.K_b:
        set_target('back')
    elif key == pygame.K_m:
        set_target('both')
    elif key == pygame.K_SPACE:
        toggle_pause()
    return True
update_phone()
running = True
frame_number = 0
while running:
    dt = clock.tick(60) / 1000.0
    frame_number += 1
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
        elif event.type == pygame.KEYDOWN:
            running = handle_key(event.key)
    for data in server.get_commands():
        command(data)
    for side in ('front', 'back'):
        controllers[side].update(dt)
        if not controllers[side].paused:
            particles[side].update(dt)
    update_shows(dt)
    for side in ('front', 'back'):
        controllers[side].effect(displays[side], controllers[side].time)
        apply_reactive(side, displays[side], frame_number)
    audio['beat'] = False
    screen.fill((15, 15, 18))
    draw_panel('front', 0)
    draw_panel('back', PW + GAP)
    draw_ui()
    update_phone()
    pygame.display.flip()
server.stop()
pygame.quit()
