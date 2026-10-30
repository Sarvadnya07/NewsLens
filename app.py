"""NewsLens India — Streamlit Web Application.

Near-Real-Time Indian News Monitoring and Misinformation Screening
Using Multi-Source Evidence, BM25 Retrieval, and Machine Learning.
"""

import streamlit as st

from src.services.news_service import NewsLensService
from src.ui.navigation import (
    PAGE_ANALYZE_ARTICLE,
    PAGE_DASHBOARD,
    PAGE_EVIDENCE_COVERAGE,
    PAGE_METHODOLOGY,
    PAGE_NEWS_MONITOR,
    init_session_state,
    render_sidebar,
)
from src.ui.pages.article_analysis import render_article_analysis_page
from src.ui.pages.dashboard import render_dashboard_page
from src.ui.pages.evidence_coverage import render_evidence_coverage_page
from src.ui.pages.methodology import render_methodology_page
from src.ui.pages.news_monitor import render_news_monitor_page
from src.ui.theme import apply_theme

# Page configuration
st.set_page_config(
    page_title="NewsLens India — Investigative Intelligence",
    page_icon="🇮🇳",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Apply Centralized Theme and Typography
apply_theme()


@st.cache_resource
def get_service() -> NewsLensService:
    """Initializes service singleton with database, ingestion clients, and ML models."""
    return NewsLensService()


def main():
    service = get_service()

    # Initialize standard session state
    init_session_state()

    # Render Sidebar and retrieve current selected page
    current_page = render_sidebar(service)

    # Route to selected page module
    if current_page == PAGE_DASHBOARD:
        render_dashboard_page(service)
    elif current_page == PAGE_NEWS_MONITOR:
        render_news_monitor_page(service)
    elif current_page == PAGE_ANALYZE_ARTICLE:
        render_article_analysis_page(service)
    elif current_page == PAGE_EVIDENCE_COVERAGE:
        render_evidence_coverage_page(service)
    elif current_page == PAGE_METHODOLOGY:
        render_methodology_page(service)
    else:
        render_dashboard_page(service)


if __name__ == "__main__":
    main()
