"""Design tokens and centralized CSS injection for NewsLens India.

Follows Stitch DESIGN.md:
- Colors: Primary navy (#183B56), Secondary teal (#167C80), Background (#F6F8FA), Surface (#FFFFFF), Caution amber (#B7791F)
- Typography: Newsreader for editorial serif headings, Inter for clean analytical body/UI.
"""

import streamlit as st

COLOR_BACKGROUND = "#F6F8FA"
COLOR_SURFACE = "#FFFFFF"
COLOR_PRIMARY_NAVY = "#183B56"
COLOR_SECONDARY_TEAL = "#167C80"
COLOR_TEXT_PRIMARY = "#182230"
COLOR_TEXT_SECONDARY = "#667085"
COLOR_BORDER = "#E4E7EC"
COLOR_INFO_BG = "#EEF4F7"
COLOR_TEAL_BG = "#EAF5F3"
COLOR_AMBER = "#B7791F"
COLOR_AMBER_BG = "#FEF7ED"
COLOR_SIDEBAR_ACTIVE = "#183B56"

CUSTOM_CSS = f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=Newsreader:ital,opsz,wght@0,6..72,400;0,6..72,500;0,6..72,600;1,6..72,400&display=swap');

/* Global Font and Canvas */
html, body, [class*="css"] {{
    font-family: 'Inter', -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
    color: {COLOR_TEXT_PRIMARY};
}}

.stApp {{
    background-color: {COLOR_BACKGROUND};
}}

/* Top Masthead & App Chrome */
.nl-top-header {{
    display: flex;
    justify-content: space-between;
    align-items: center;
    background-color: {COLOR_SURFACE};
    border-bottom: 1px solid {COLOR_BORDER};
    padding: 10px 24px;
    margin: -1rem -1rem 1.5rem -1rem;
}}

/* Typography Hierarchy */
h1, .dossier-heading-xl {{
    font-family: 'Newsreader', Georgia, serif !important;
    font-weight: 600 !important;
    color: {COLOR_PRIMARY_NAVY} !important;
    letter-spacing: -0.02em !important;
}}

h2, h3, .dossier-heading-lg {{
    font-family: 'Newsreader', Georgia, serif !important;
    font-weight: 600 !important;
    color: {COLOR_PRIMARY_NAVY} !important;
    letter-spacing: -0.01em !important;
}}

/* Tabular numerals for analytical density */
.tabular-numbers, [data-testid="stMetricValue"] {{
    font-family: 'Inter', monospace !important;
    font-variant-numeric: tabular-nums !important;
    color: {COLOR_PRIMARY_NAVY} !important;
}}

/* Sidebar Refinements */
[data-testid="stSidebar"] {{
    background-color: #FFFFFF !important;
    border-right: 1px solid {COLOR_BORDER} !important;
}}

[data-testid="stSidebar"] h1, [data-testid="stSidebar"] h2, [data-testid="stSidebar"] h3 {{
    font-family: 'Newsreader', Georgia, serif !important;
    color: {COLOR_PRIMARY_NAVY} !important;
}}

/* Sidebar navigation radio styling */
[data-testid="stSidebar"] [data-testid="stRadio"] > div {{
    gap: 2px;
}}

[data-testid="stSidebar"] [data-testid="stRadio"] label {{
    border-radius: 4px;
    padding: 8px 12px;
    font-weight: 500;
    font-size: 0.88rem;
    color: #42474d;
    transition: all 0.15s ease;
}}

[data-testid="stSidebar"] [data-testid="stRadio"] label:hover {{
    background-color: {COLOR_INFO_BG};
    color: {COLOR_PRIMARY_NAVY};
}}

/* Selected Radio State in Sidebar - Solid Navy with white text like screenshot */
[data-testid="stSidebar"] [data-testid="stRadio"] label[data-checked="true"],
[data-testid="stSidebar"] [data-testid="stRadio"] label:has(input:checked) {{
    background-color: {COLOR_PRIMARY_NAVY} !important;
    color: #FFFFFF !important;
    font-weight: 600 !important;
}}

[data-testid="stSidebar"] [data-testid="stRadio"] label[data-checked="true"] p,
[data-testid="stSidebar"] [data-testid="stRadio"] label:has(input:checked) p {{
    color: #FFFFFF !important;
}}

/* Hide native radio circles in sidebar for pure clean nav tab feel */
[data-testid="stSidebar"] [data-testid="stRadio"] [data-testid="stWidgetLabel"] {{
    display: none;
}}
[data-testid="stSidebar"] [data-testid="stRadio"] input[type="radio"] {{
    display: none;
}}
[data-testid="stSidebar"] [data-testid="stRadio"] div[role="radiogroup"] > label > div:first-child {{
    display: none;
}}

/* Metric Cards matching screenshot (white surface, label top with pill, large num, description bottom) */
.nl-stat-card {{
    background-color: {COLOR_SURFACE};
    border: 1px solid {COLOR_BORDER};
    border-radius: 4px;
    padding: 14px 16px;
    box-shadow: 0 1px 3px rgba(24, 59, 86, 0.03);
    height: 100%;
}}

.nl-stat-header {{
    display: flex;
    justify-content: space-between;
    align-items: flex-start;
    margin-bottom: 8px;
}}

.nl-stat-label {{
    color: {COLOR_TEXT_SECONDARY};
    font-size: 0.72rem;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.04em;
    line-height: 1.2;
}}

.nl-stat-badge {{
    background-color: #e6eeff;
    color: #183b56;
    font-size: 10px;
    font-weight: 600;
    padding: 2px 6px;
    border-radius: 2px;
    text-transform: uppercase;
    letter-spacing: 0.03em;
}}

.nl-stat-value {{
    font-size: 1.75rem;
    font-weight: 700;
    color: {COLOR_PRIMARY_NAVY};
    font-family: 'Inter', sans-serif;
    line-height: 1.1;
    margin-bottom: 6px;
    display: flex;
    align-items: baseline;
    gap: 6px;
}}

.nl-stat-tag {{
    font-size: 0.75rem;
    font-weight: 600;
    color: {COLOR_SECONDARY_TEAL};
}}

.nl-stat-desc {{
    font-size: 0.78rem;
    color: {COLOR_TEXT_SECONDARY};
    line-height: 1.35;
}}

[data-testid="stMetric"] {{
    background-color: {COLOR_SURFACE};
    border: 1px solid {COLOR_BORDER};
    border-radius: 4px;
    padding: 14px 16px;
    box-shadow: 0 1px 3px rgba(24, 59, 86, 0.04);
}}

[data-testid="stMetricLabel"] {{
    color: {COLOR_TEXT_SECONDARY} !important;
    font-size: 0.75rem !important;
    font-weight: 700 !important;
    text-transform: uppercase !important;
    letter-spacing: 0.04em !important;
}}

/* Primary & Secondary Buttons */
.stButton > button {{
    border-radius: 4px !important;
    font-weight: 5px !important;
    font-size: 0.875rem !important;
    transition: all 0.15s ease-in-out !important;
    border: 1px solid {COLOR_BORDER} !important;
}}

.stButton > button[kind="primary"] {{
    background-color: {COLOR_PRIMARY_NAVY} !important;
    color: #FFFFFF !important;
    border: 1px solid {COLOR_PRIMARY_NAVY} !important;
}}

.stButton > button[kind="primary"]:hover {{
    background-color: #122d42 !important;
    border-color: #122d42 !important;
}}

.stButton > button[kind="secondary"] {{
    background-color: {COLOR_SURFACE} !important;
    color: {COLOR_TEXT_PRIMARY} !important;
}}

.stButton > button[kind="secondary"]:hover {{
    background-color: {COLOR_INFO_BG} !important;
    border-color: #d0dce3 !important;
}}

/* Inputs & Textareas */
.stTextInput > div > div > input,
.stTextArea > div > div > textarea,
.stSelectbox > div > div {{
    background-color: {COLOR_SURFACE} !important;
    border: 1px solid {COLOR_BORDER} !important;
    border-radius: 4px !important;
    color: {COLOR_TEXT_PRIMARY} !important;
    font-size: 0.9rem !important;
}}

.stButton > button:focus-visible,
.stTextInput > div > div > input:focus-visible,
.stTextArea > div > div > textarea:focus-visible,
.stSelectbox > div > div:focus-visible,
[data-testid="stRadio"] label:focus-within {{
    outline: 2px solid {COLOR_SECONDARY_TEAL} !important;
    outline-offset: 2px !important;
}}

@media (prefers-reduced-motion: reduce) {{
    *, ::before, ::after {{
        animation-duration: 0.01ms !important;
        animation-iteration-count: 1 !important;
        transition-duration: 0.01ms !important;
        scroll-behavior: auto !important;
    }}
}}

/* Custom Dossier & Card Containers */
.nl-card {{
    background-color: {COLOR_SURFACE};
    border: 1px solid {COLOR_BORDER};
    border-radius: 4px;
    padding: 18px 20px;
    margin-bottom: 16px;
    box-shadow: 0 1px 3px rgba(24, 59, 86, 0.03);
}}

.nl-subcard {{
    background-color: {COLOR_INFO_BG};
    border: 1px solid #D0DCE3;
    border-radius: 4px;
    padding: 12px 14px;
    margin-top: 10px;
}}

.nl-subcard-teal {{
    background-color: {COLOR_TEAL_BG};
    border: 1px solid #C4E3DF;
    border-radius: 4px;
    padding: 12px 14px;
    margin-top: 10px;
}}

.nl-subcard-amber {{
    background-color: {COLOR_AMBER_BG};
    border: 1px solid #F6D8A8;
    border-radius: 4px;
    padding: 12px 14px;
    margin-top: 10px;
}}

/* Badges & Tags */
.nl-badge {{
    display: inline-block;
    padding: 2px 8px;
    border-radius: 4px;
    font-size: 11px;
    font-weight: 600;
    letter-spacing: 0.03em;
    text-transform: uppercase;
}}

.nl-badge-navy {{
    background-color: {COLOR_INFO_BG};
    color: {COLOR_PRIMARY_NAVY};
    border: 1px solid #D0DCE3;
}}

.nl-badge-teal {{
    background-color: {COLOR_TEAL_BG};
    color: {COLOR_SECONDARY_TEAL};
    border: 1px solid #C4E3DF;
}}

.nl-badge-amber {{
    background-color: {COLOR_AMBER_BG};
    color: {COLOR_AMBER};
    border: 1px solid #F6D8A8;
}}

.nl-badge-neutral {{
    background-color: #F0F2F5;
    color: {COLOR_TEXT_SECONDARY};
    border: 1px solid {COLOR_BORDER};
}}

/* Header Banner */
.nl-page-header {{
    background-color: {COLOR_SURFACE};
    border: 1px solid {COLOR_BORDER};
    border-radius: 4px;
    padding: 20px 24px;
    margin-bottom: 20px;
    box-shadow: 0 1px 3px rgba(24, 59, 86, 0.03);
}}

.nl-page-subtitle {{
    color: {COLOR_TEXT_SECONDARY};
    font-size: 0.95rem;
    margin-top: 4px;
    line-height: 1.5;
}}

.nl-meta-strip {{
    display: flex;
    align-items: center;
    gap: 8px;
    font-size: 11px;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.04em;
    color: {COLOR_SECONDARY_TEAL};
    margin-bottom: 6px;
}}

/* Responsive Fluid Adjustments */
@media (max-width: 768px) {{
    .nl-page-header {{
        padding: 14px 16px !important;
    }}
    .nl-card {{
        padding: 14px 14px !important;
    }}
    .stButton > button {{
        min-height: 44px !important; /* Touch target minimum */
    }}
}}
</style>
"""


def apply_theme():
    """Injects centralized CSS stylesheet into Streamlit."""
    st.markdown(CUSTOM_CSS, unsafe_allow_html=True)
