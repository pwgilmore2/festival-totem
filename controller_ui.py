"""Compose the desktop controller UI in one declared order.

Performance-facing UI modules are pure transforms. Import order no longer
changes the controller document; this module is the single place that defines
how the finished controller is assembled.
"""

import phone_server
import controller_state_ui

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


# ``controller_state_ui`` imports the older performance/cleanup foundation.
# Snapshot that once, before applying the newer feature transforms, so repeated
# builds never start from an already-transformed document.
BASE_CONTROLLER_HTML = phone_server.PHONE_HTML

CONTROLLER_TRANSFORMS = (
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
phone_server.PHONE_HTML = PHONE_HTML

PhoneControlServer = controller_state_ui.PhoneControlServer
