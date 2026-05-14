"""Brand CSS injection — supports dark (green) and light (white) themes."""
import streamlit as st

PRIMARY = "#407E3C"
PRIMARY_LIGHT = "#5a9e56"
PRIMARY_DARK = "#2d5a29"
WHITE = "#FFFFFF"
DANGER = "#ef4444"
WARNING = "#f59e0b"

# Per-theme palette
THEMES = {
    "dark": {
        "BG": "#407E3C",
        "SURFACE": "#2d6b29",
        "SURFACE2": "#245c21",
        "TEXT": "#ffffff",
        "TEXT_MUTED": "#c8e6c4",
        "BORDER": "#5a9e56",
        "BTN_BG": "#ffffff",
        "BTN_TEXT": "#407E3C",
        "BTN_HOVER": "#e8f5e9",
        "INPUT_BG": "#245c21",
        "LOGO_PRIMARY": "#ffffff",
        "LOGO_SECONDARY": "#c8e6c4",
    },
    "light": {
        "BG": "#ffffff",
        "SURFACE": "#f4faf4",
        "SURFACE2": "#e8f5e9",
        "TEXT": "#1a3d18",
        "TEXT_MUTED": "#5a7a58",
        "BORDER": "#407E3C",
        "BTN_BG": "#407E3C",
        "BTN_TEXT": "#ffffff",
        "BTN_HOVER": "#2d6b29",
        "INPUT_BG": "#f4faf4",
        "LOGO_PRIMARY": "#407E3C",
        "LOGO_SECONDARY": "#5a9e56",
    },
}

# Expose mutable refs — updated by inject()
TEXT_MUTED = THEMES["dark"]["TEXT_MUTED"]


def get_theme() -> str:
    return st.session_state.get("theme", "dark")


def inject():
    global TEXT_MUTED
    t = THEMES[get_theme()]
    TEXT_MUTED = t["TEXT_MUTED"]

    st.markdown(f"""
<style>
  .stApp {{
    background-color: {t['BG']} !important;
    color: {t['TEXT']} !important;
  }}

  section[data-testid="stSidebar"] {{
    background-color: {t['SURFACE']} !important;
    border-right: 1px solid {t['BORDER']}44;
  }}

  /* All text */
  h1, h2, h3, h4, h5, h6 {{
    color: {t['TEXT']} !important;
  }}
  p, li, span, label, div {{
    color: {t['TEXT']};
  }}

  /* Buttons */
  .stButton > button {{
    background-color: {t['BTN_BG']} !important;
    color: {t['BTN_TEXT']} !important;
    border: 2px solid {t['BORDER']} !important;
    border-radius: 6px;
    font-weight: 700;
    padding: 0.4rem 1rem;
  }}
  .stButton > button:hover {{
    background-color: {t['BTN_HOVER']} !important;
    color: {t['BTN_TEXT']} !important;
  }}

  /* Inputs */
  .stTextInput > div > div > input,
  .stSelectbox > div > div,
  .stTextArea > div > div > textarea {{
    background-color: {t['INPUT_BG']} !important;
    color: {t['TEXT']} !important;
    border: 1px solid {t['BORDER']}66 !important;
    border-radius: 6px;
  }}

  /* Metrics */
  div[data-testid="metric-container"] {{
    background-color: {t['SURFACE']} !important;
    border-left: 4px solid {PRIMARY};
    padding: 0.8rem 1rem;
    border-radius: 8px;
  }}
  div[data-testid="metric-container"] * {{
    color: {t['TEXT']} !important;
  }}

  /* Dataframe */
  .stDataFrame {{ background-color: {t['SURFACE']} !important; }}

  /* Tabs */
  .stTabs [data-baseweb="tab"] {{
    color: {t['TEXT_MUTED']} !important;
  }}
  .stTabs [aria-selected="true"] {{
    color: {t['TEXT']} !important;
    border-bottom: 2px solid {PRIMARY};
  }}

  /* Sidebar nav radio */
  div[data-testid="stSidebarNav"] * {{
    color: {t['TEXT']} !important;
  }}

  hr {{ border-color: {t['BORDER']}44; opacity: 0.5; }}

  /* Badges */
  .status-badge {{
    display: inline-block;
    padding: 2px 10px;
    border-radius: 12px;
    font-size: 0.75rem;
    font-weight: 600;
    text-transform: uppercase;
  }}
  .badge-ok {{ background: {PRIMARY}33; color: {t['TEXT']}; border: 1px solid {PRIMARY}66; }}
  .badge-error {{ background: {DANGER}22; color: {DANGER}; border: 1px solid {DANGER}44; }}
  .badge-pending {{ background: {WARNING}22; color: {WARNING}; border: 1px solid {WARNING}44; }}

  /* Agent cards */
  .agent-card {{
    background: {t['SURFACE']};
    border: 1px solid {t['BORDER']}44;
    border-radius: 8px;
    padding: 1rem;
    margin-bottom: 0.75rem;
  }}

  ::-webkit-scrollbar {{ width: 6px; }}
  ::-webkit-scrollbar-track {{ background: {t['BG']}; }}
  ::-webkit-scrollbar-thumb {{ background: {t['BORDER']}; border-radius: 3px; }}
</style>
""", unsafe_allow_html=True)


def sidebar_logo():
    t = THEMES[get_theme()]
    st.sidebar.markdown(f"""
<div style="padding: 1rem 0.5rem; text-align: center;">
  <div style="font-size: 1.5rem; font-weight: 800; color: {t['LOGO_PRIMARY']}; letter-spacing: 2px;">
    CLAUDE<span style="color: {t['LOGO_SECONDARY']};">OS</span>
  </div>
  <div style="font-size: 0.7rem; color: {t['TEXT_MUTED']}; letter-spacing: 1px;">AI OPERATING SYSTEM</div>
</div>
""", unsafe_allow_html=True)


def theme_toggle():
    """Render dark/light mode toggle in sidebar."""
    current = get_theme()
    label = "☀️ Light mode" if current == "dark" else "🌙 Dark mode"
    if st.sidebar.button(label, use_container_width=True):
        st.session_state.theme = "light" if current == "dark" else "dark"
        st.rerun()


def badge(text: str, kind: str = "ok") -> str:
    return f'<span class="status-badge badge-{kind}">{text}</span>'
