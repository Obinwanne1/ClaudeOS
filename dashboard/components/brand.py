"""Brand CSS injection — dark (green) / light (white) themes."""
import streamlit as st

PRIMARY       = "#407E3C"
PRIMARY_LIGHT = "#5a9e56"   # alias kept for page imports
PRIMARY_LT    = "#5a9e56"
PRIMARY_DK    = "#2d5a29"
WHITE         = "#FFFFFF"
DANGER        = "#ef4444"
WARNING       = "#f59e0b"
SURFACE       = "#2d6b29"   # alias kept for page imports

THEMES = {
    "dark": {
        "BG":          "#407E3C",
        "SURFACE":     "#2d6b29",
        "SURFACE2":    "#245c21",
        "TEXT":        "#ffffff",
        "TEXT_MUTED":  "#c8e6c4",
        "BORDER":      "#5a9e56",
        "BTN_BG":      "#ffffff",
        "BTN_TEXT":    "#2d5a29",
        "BTN_HOVER_BG":"#e8f5e9",
        "INPUT_BG":    "#245c21",
        "INPUT_TEXT":  "#ffffff",
        "LOGO1":       "#ffffff",
        "LOGO2":       "#c8e6c4",
    },
    "light": {
        "BG":          "#ffffff",
        "SURFACE":     "#f4faf4",
        "SURFACE2":    "#e8f5e9",
        "TEXT":        "#1a3d18",
        "TEXT_MUTED":  "#4a6e48",
        "BORDER":      "#407E3C",
        "BTN_BG":      "#407E3C",
        "BTN_TEXT":    "#ffffff",
        "BTN_HOVER_BG":"#2d6b29",
        "INPUT_BG":    "#ffffff",
        "INPUT_TEXT":  "#1a3d18",
        "LOGO1":       "#407E3C",
        "LOGO2":       "#5a9e56",
    },
}

# Module-level ref updated on each inject() call
TEXT_MUTED = THEMES["dark"]["TEXT_MUTED"]


def get_theme() -> str:
    return st.session_state.get("theme", "dark")


def inject():
    global TEXT_MUTED
    t = THEMES[get_theme()]
    TEXT_MUTED = t["TEXT_MUTED"]

    st.markdown(f"""
<style>
/* ── App shell ── */
html, body, .stApp, [data-testid="stAppViewContainer"],
[data-testid="stAppViewBlockContainer"] {{
    background-color: {t['BG']} !important;
    color: {t['TEXT']} !important;
}}

/* ── Sidebar ── */
section[data-testid="stSidebar"],
section[data-testid="stSidebar"] > div {{
    background-color: {t['SURFACE']} !important;
    border-right: 1px solid {t['BORDER']}55 !important;
}}

/* ── Text — semantic elements only, never bare div/span ── */
.stApp h1, .stApp h2, .stApp h3, .stApp h4, .stApp h5, .stApp h6 {{
    color: {t['TEXT']} !important;
}}
.stApp p, .stApp li, .stApp label {{
    color: {t['TEXT']} !important;
}}
[data-testid="stMarkdownContainer"] p,
[data-testid="stMarkdownContainer"] li,
[data-testid="stMarkdownContainer"] span,
[data-testid="stText"] {{
    color: {t['TEXT']} !important;
}}
[data-testid="stCaptionContainer"] p {{
    color: {t['TEXT_MUTED']} !important;
}}

/* ── Metric values ── */
[data-testid="metric-container"],
[data-testid="metric-container"] * {{
    background-color: {t['SURFACE']} !important;
    color: {t['TEXT']} !important;
}}
[data-testid="metric-container"] {{
    border-left: 4px solid {PRIMARY} !important;
    padding: 0.8rem 1rem !important;
    border-radius: 8px !important;
}}
label[data-testid="stMetricLabel"],
label[data-testid="stMetricLabel"] *,
div[data-testid="stMetricLabel"],
div[data-testid="stMetricLabel"] *,
[data-testid="stMetricLabel"],
[data-testid="stMetricLabel"] * {{
    color: {t['TEXT']} !important;
    opacity: 1 !important;
    filter: none !important;
    -webkit-text-fill-color: {t['TEXT']} !important;
}}
[data-testid="stMetricValue"],
[data-testid="stMetricValue"] *,
div[data-testid="stMetricValue"],
div[data-testid="stMetricValue"] * {{
    color: {t['TEXT']} !important;
    opacity: 1 !important;
    -webkit-text-fill-color: {t['TEXT']} !important;
}}

/* ── Input placeholders ── */
input::placeholder, textarea::placeholder {{
    color: {t['TEXT_MUTED']} !important;
    opacity: 0.8 !important;
}}

/* ── Buttons ── */
.stButton > button,
.stButton > button:focus,
.stButton > button:active,
button[data-testid="baseButton-secondary"],
button[data-testid="baseButton-primary"],
button[kind="primary"],
button[kind="secondary"] {{
    background-color: {t['BTN_BG']} !important;
    color: {t['BTN_TEXT']} !important;
    border: 2px solid {t['BORDER']} !important;
    border-radius: 6px !important;
    font-weight: 700 !important;
}}
.stButton > button p,
.stButton > button span,
button[data-testid="baseButton-secondary"] p,
button[data-testid="baseButton-primary"] p {{
    color: {t['BTN_TEXT']} !important;
}}
.stButton > button:hover,
button[data-testid="baseButton-secondary"]:hover,
button[data-testid="baseButton-primary"]:hover {{
    background-color: {t['BTN_HOVER_BG']} !important;
    color: {t['BTN_TEXT']} !important;
    border-color: {t['BORDER']} !important;
}}

/* ── Inputs / selects / textareas ── */
input, textarea,
.stTextInput input,
.stTextArea textarea,
div[data-baseweb="select"] > div,
div[data-baseweb="input"] > div {{
    background-color: {t['INPUT_BG']} !important;
    color: {t['INPUT_TEXT']} !important;
    border-color: {t['BORDER']}66 !important;
}}

/* ── Selectbox dropdown options ── */
ul[data-testid="stSelectboxVirtualDropdown"] li,
li[role="option"] {{
    background-color: {t['SURFACE']} !important;
    color: {t['TEXT']} !important;
}}

/* ── Tabs ── */
button[data-baseweb="tab"] {{
    color: {t['TEXT_MUTED']} !important;
    background: transparent !important;
}}
button[data-baseweb="tab"][aria-selected="true"] {{
    color: {t['TEXT']} !important;
    border-bottom: 3px solid {PRIMARY} !important;
}}

/* ── DataFrames / tables ── */
.stDataFrame, iframe {{
    background-color: {t['SURFACE']} !important;
}}

/* ── Dividers ── */
hr {{ border-color: {t['BORDER']}44 !important; }}

/* ── Badges / cards ── */
.status-badge {{
    display: inline-block;
    padding: 2px 10px;
    border-radius: 12px;
    font-size: 0.75rem;
    font-weight: 600;
    text-transform: uppercase;
}}
.badge-ok      {{ background: {PRIMARY}33; color: {t['TEXT']}; border: 1px solid {PRIMARY}66; }}
.badge-error   {{ background: {DANGER}22;  color: {DANGER};    border: 1px solid {DANGER}44; }}
.badge-pending {{ background: {WARNING}22; color: {WARNING};   border: 1px solid {WARNING}44; }}
.agent-card {{
    background: {t['SURFACE']};
    border: 1px solid {t['BORDER']}44;
    border-radius: 8px;
    padding: 1rem;
    margin-bottom: 0.75rem;
}}

/* ── Scrollbar ── */
::-webkit-scrollbar {{ width: 6px; }}
::-webkit-scrollbar-track {{ background: {t['BG']}; }}
::-webkit-scrollbar-thumb {{ background: {t['BORDER']}; border-radius: 3px; }}
</style>
""", unsafe_allow_html=True)


def sidebar_logo():
    t = THEMES[get_theme()]
    st.sidebar.markdown(f"""
<div style="padding:1rem 0.5rem;text-align:center;">
  <div style="font-size:1.5rem;font-weight:800;color:{t['LOGO1']};letter-spacing:2px;">
    CLAUDE<span style="color:{t['LOGO2']};">OS</span>
  </div>
  <div style="font-size:0.7rem;color:{t['TEXT_MUTED']};letter-spacing:1px;">AI OPERATING SYSTEM</div>
</div>
""", unsafe_allow_html=True)


def theme_toggle():
    current = get_theme()
    label = "☀️  Light mode" if current == "dark" else "🌙  Dark mode"
    if st.sidebar.button(label, use_container_width=True):
        st.session_state.theme = "light" if current == "dark" else "dark"
        st.rerun()


def badge(text: str, kind: str = "ok") -> str:
    return f'<span class="status-badge badge-{kind}">{text}</span>'
