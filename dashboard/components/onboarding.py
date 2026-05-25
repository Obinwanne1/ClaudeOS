"""First-login onboarding modal — 5-slide walkthrough for client/viewer roles.

Shown once per session (not per login — dismissed state lives in session_state).
Only rendered for client/viewer roles; admin/operator skip it.
"""
import streamlit as st
from dashboard.components.brand import get_theme_vars, get_ns_brand

_SLIDES = [
    {
        "icon": "🖥️",
        "title": "Welcome to your AI Workspace",
        "body": (
            "Your intelligent workspace is ready. This platform puts powerful AI agents, "
            "smart memory, and streamlined support at your fingertips — all in one place."
        ),
        "tip": None,
    },
    {
        "icon": "🤖",
        "title": "Chat with AI Agents",
        "body": (
            "Go to **Agents → Chat** to talk with AI agents built for your business. "
            "Ask questions, generate content, analyse data, or automate tasks."
        ),
        "tip": "Tip: agents remember context across your workspace — the more you use them, the smarter they get.",
    },
    {
        "icon": "🧠",
        "title": "Your AI Has Memory",
        "body": (
            "The **Memory** page stores important context your agents use. "
            "Add key facts about your business, clients, or preferences — "
            "agents automatically draw on this when answering."
        ),
        "tip": "Tip: well-structured memory cuts response costs by up to 40%.",
    },
    {
        "icon": "🎫",
        "title": "Need Help? Raise a Ticket",
        "body": (
            "The **Tickets** page is your support channel. "
            "Describe any issue or request — the team will be notified and respond with an SLA."
        ),
        "tip": "Tip: P1 tickets get a 4-hour response guarantee.",
    },
    {
        "icon": "📊",
        "title": "Track Your AI Usage",
        "body": (
            "The **Usage** page shows your AI activity, token costs, quality scores, "
            "and your Namespace Pulse Score — a single number that shows how well your AI workspace is performing."
        ),
        "tip": None,
    },
]

_TOTAL = len(_SLIDES)


def maybe_show_onboarding(role: str) -> None:
    """Call once per render (after auth gate). Renders the modal if needed."""
    if role not in ("client", "viewer"):
        return
    if st.session_state.get("_onboarding_done"):
        return
    _render_modal()


def _render_modal() -> None:
    t = get_theme_vars()
    brand = get_ns_brand()
    _p = (brand.get("color") or "#407E3C").strip()
    _a = (brand.get("accent_color") or "#5a9e56").strip()

    slide_idx = st.session_state.get("_onboarding_slide", 0)
    slide = _SLIDES[slide_idx]

    # Backdrop overlay
    st.markdown(
        f'<div style="position:fixed;top:0;left:0;width:100vw;height:100vh;'
        f'background:rgba(0,0,0,0.55);z-index:9998;pointer-events:none;"></div>',
        unsafe_allow_html=True,
    )

    # Modal card
    st.markdown(
        f'<div style="position:fixed;top:50%;left:50%;transform:translate(-50%,-50%);'
        f'z-index:9999;background:{t["SURFACE"]};border:1px solid {t["BORDER"]};'
        f'border-radius:16px;padding:36px 40px;min-width:380px;max-width:480px;'
        f'box-shadow:0 20px 60px rgba(0,0,0,0.4);">'
        # Progress dots
        f'<div style="display:flex;gap:6px;justify-content:center;margin-bottom:24px;">'
        + "".join(
            f'<div style="width:8px;height:8px;border-radius:50%;'
            f'background:{"" + _p if i == slide_idx else t["BORDER"]};"></div>'
            for i in range(_TOTAL)
        )
        + f'</div>'
        # Icon + content
        f'<div style="text-align:center;">'
        f'<div style="font-size:3rem;margin-bottom:12px;">{slide["icon"]}</div>'
        f'<h2 style="margin:0 0 12px;color:{t["TEXT"]};font-size:1.15rem;'
        f'font-family:Poppins,sans-serif;font-weight:700;">{slide["title"]}</h2>'
        f'<p style="color:{t["TEXT_MUTED"]};font-size:0.9rem;line-height:1.6;margin:0 0 12px;">'
        f'{slide["body"]}</p>'
        + (
            f'<p style="background:{_p}15;border:1px solid {_p}30;border-radius:8px;'
            f'padding:8px 12px;font-size:0.8rem;color:{t["TEXT_MUTED"]};font-style:italic;">'
            f'{slide["tip"]}</p>'
            if slide["tip"] else ""
        )
        + f'</div>'
        f'<div style="font-size:0.72rem;color:{t["TEXT_MUTED"]};text-align:center;margin-top:16px;">'
        f'{slide_idx + 1} of {_TOTAL}</div>'
        f'</div>',
        unsafe_allow_html=True,
    )

    # Navigation buttons
    col_skip, col_prev, col_next = st.columns([2, 1, 1])

    with col_skip:
        if st.button("Skip tour", key="_ob_skip", use_container_width=True):
            st.session_state["_onboarding_done"] = True
            st.session_state.pop("_onboarding_slide", None)
            st.rerun()

    with col_prev:
        if slide_idx > 0:
            if st.button("← Back", key="_ob_prev", use_container_width=True):
                st.session_state["_onboarding_slide"] = slide_idx - 1
                st.rerun()

    with col_next:
        is_last = slide_idx == _TOTAL - 1
        label = "Get started →" if is_last else "Next →"
        if st.button(label, key="_ob_next", use_container_width=True, type="primary"):
            if is_last:
                st.session_state["_onboarding_done"] = True
                st.session_state.pop("_onboarding_slide", None)
            else:
                st.session_state["_onboarding_slide"] = slide_idx + 1
            st.rerun()
