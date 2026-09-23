"""Compose the phone controller in one deterministic transform pipeline.

Nothing in this stack mutates controller HTML merely by being imported. Desktop
and MatrixPortal builds both consume the same finished document.
"""

import phone_server

from audio_phone_server import apply as apply_audio
from performance_phone_server import apply as apply_performance_foundation
from controller_cleanup import apply as apply_cleanup
from controller_state_ui import apply as apply_controller_state
from chaos_layout_patch import apply as apply_chaos_layout
from text_ui_patch import apply as apply_text_ui
from overlay_ui_patch import apply as apply_overlay_ui
from image_processing_ui import apply as apply_image_processing_ui
from safe_controls_patch import apply as apply_safe_controls
from intense_transition_ui import apply as apply_intense_transitions
from transition_ui_patch import apply as apply_transition_labels
from performance_ui_reorg_patch import apply as apply_performance_layout
from screen_mode_ui_patch import apply as apply_screen_mode


BASE_CONTROLLER_HTML = phone_server.PHONE_HTML

CONTROLLER_TRANSFORMS = (
    apply_audio,
    apply_performance_foundation,
    apply_cleanup,
    apply_controller_state,
    apply_chaos_layout,
    apply_text_ui,
    apply_overlay_ui,
    apply_image_processing_ui,
    apply_safe_controls,
    apply_intense_transitions,
    apply_transition_labels,
    apply_performance_layout,
    apply_screen_mode,
)


def build_controller_html(base_html=None):
    html = BASE_CONTROLLER_HTML if base_html is None else base_html
    for transform in CONTROLLER_TRANSFORMS:
        html = transform(html)
    return html


PHONE_HTML = build_controller_html()
# The desktop HTTP server still reads this constant. Assign it once after the
# deterministic build rather than letting feature imports modify it piecemeal.
phone_server.PHONE_HTML = PHONE_HTML

PhoneControlServer = phone_server.PhoneControlServer
