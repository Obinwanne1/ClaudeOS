"""Brand CSS injection — #407E3C green + white theme."""
import streamlit as st

PRIMARY = "#407E3C"
PRIMARY_LIGHT = "#5a9e56"
PRIMARY_DARK = "#2d5a29"
WHITE = "#FFFFFF"
BG = "#407E3C"
SURFACE = "#2d6b29"
SURFACE2 = "#245c21"
TEXT = "#ffffff"
TEXT_MUTED = "#c8e6c4"
DANGER = "#ef4444"
WARNING = "#f59e0b"


def inject():
    st.markdown(f"""
<style>
  :root {{
    --primary: {PRIMARY};
    --primary-light: {PRIMARY_LIGHT};
    --primary-dark: {PRIMARY_DARK};
    --bg: {BG};
    --surface: {SURFACE};
    --surface2: {SURFACE2};
    --text: {TEXT};
    --text-muted: {TEXT_MUTED};
  }}

  .stApp {{ background-color: var(--bg); color: var(--text); }}

  section[data-testid="stSidebar"] {{
    background-color: var(--surface);
    border-right: 1px solid {PRIMARY_DARK};
  }}

  .stButton > button {{
    background-color: var(--primary);
    color: {WHITE};
    border: none;
    border-radius: 6px;
    font-weight: 600;
    padding: 0.4rem 1rem;
    transition: background-color 0.2s;
  }}
  .stButton > button:hover {{
    background-color: var(--primary-light);
    border: none;
  }}

  h1, h2, h3, h4 {{ color: var(--text); }}
  p, li, span {{ color: var(--text); }}

  .stTextInput > div > div > input,
  .stSelectbox > div > div,
  .stTextArea > div > div > textarea {{
    background-color: var(--surface2);
    color: var(--text);
    border: 1px solid {PRIMARY_DARK};
    border-radius: 6px;
  }}

  .stDataFrame {{ background-color: var(--surface); }}

  div[data-testid="metric-container"] {{
    background-color: var(--surface);
    border-left: 4px solid var(--primary);
    padding: 0.8rem 1rem;
    border-radius: 8px;
  }}

  .status-badge {{
    display: inline-block;
    padding: 2px 10px;
    border-radius: 12px;
    font-size: 0.75rem;
    font-weight: 600;
    text-transform: uppercase;
  }}
  .badge-ok {{ background: {PRIMARY}22; color: {PRIMARY_LIGHT}; border: 1px solid {PRIMARY}44; }}
  .badge-error {{ background: {DANGER}22; color: {DANGER}; border: 1px solid {DANGER}44; }}
  .badge-pending {{ background: {WARNING}22; color: {WARNING}; border: 1px solid {WARNING}44; }}
  .badge-running {{ background: #3b82f622; color: #60a5fa; border: 1px solid #3b82f644; }}

  .agent-card {{
    background: var(--surface);
    border: 1px solid {PRIMARY_DARK};
    border-radius: 8px;
    padding: 1rem;
    margin-bottom: 0.75rem;
    transition: border-color 0.2s;
  }}
  .agent-card:hover {{ border-color: var(--primary); }}

  hr {{ border-color: {PRIMARY_DARK}; opacity: 0.3; }}

  ::-webkit-scrollbar {{ width: 6px; }}
  ::-webkit-scrollbar-track {{ background: var(--bg); }}
  ::-webkit-scrollbar-thumb {{ background: {PRIMARY_DARK}; border-radius: 3px; }}
</style>
""", unsafe_allow_html=True)


def sidebar_logo():
    st.sidebar.markdown(f"""
<div style="padding: 1rem 0.5rem; text-align: center;">
  <div style="font-size: 1.5rem; font-weight: 800; color: {PRIMARY_LIGHT}; letter-spacing: 2px;">
    CLAUDE<span style="color: {WHITE};">OS</span>
  </div>
  <div style="font-size: 0.7rem; color: {TEXT_MUTED}; letter-spacing: 1px;">AI OPERATING SYSTEM</div>
</div>
""", unsafe_allow_html=True)


def badge(text: str, kind: str = "ok") -> str:
    return f'<span class="status-badge badge-{kind}">{text}</span>'
