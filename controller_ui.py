"""Compose the desktop controller UI in one declared order.

Legacy base UI modules still establish the controller/server foundation, but the
remaining presentation layers are applied explicitly here instead of relying on
import order as behavior. This is the bridge toward a checked-in static
controller asset for MatrixPortal.
"""

import phone_server
import controller_state_ui

from chaos_layout_patch import apply as apply_chaos_layout
from text_ui_patch import apply as apply_text_ui
from safe_controls_patch import apply as apply_safe_controls
from intense_transition_ui import apply as apply_intense_transitions
from transition_ui_patch import apply as apply_transition_labels
from screen_mode_ui_patch import apply as apply_screen_mode


# The current icon, desktop image-processing, and final performance-navigation
# modules still use import-time HTML transforms. Keep those three imports at the
# exact points where their transforms historically ran while the rest of the
# stack moves to explicit functions.
phone_server.PHONE_HTML = apply_chaos_layout(phone_server.PHONE_HTML)
phone_server.PHONE_HTML = apply_text_ui(phone_server.PHONE_HTML)

import overlay_ui_patch  # noqa: E402,F401
import image_processing_ui  # noqa: E402,F401

phone_server.PHONE_HTML = apply_safe_controls(phone_server.PHONE_HTML)
phone_server.PHONE_HTML = apply_intense_transitions(phone_server.PHONE_HTML)
phone_server.PHONE_HTML = apply_transition_labels(phone_server.PHONE_HTML)

import performance_ui_reorg_patch  # noqa: E402,F401

phone_server.PHONE_HTML = apply_screen_mode(phone_server.PHONE_HTML)


PhoneControlServer = controller_state_ui.PhoneControlServer
PHONE_HTML = phone_server.PHONE_HTML
