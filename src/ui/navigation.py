"""Navigation, persistent sidebar, and session state management for NewsLens India."""

from typing import Dict

import streamlit as st

from src.services.news_service import NewsLensService

PAGE_DASHBOARD = "Overview Dashboard"
PAGE_NEWS_MONITOR = "News Monitor"
PAGE_ANALYZE_ARTICLE = "Analyze Article"
PAGE_EVIDENCE_COVERAGE = "Evidence & Coverage"
PAGE_METHODOLOGY = "Methodology & Sources"

PAGES = [
    PAGE_DASHBOARD,
    PAGE_NEWS_MONITOR,
    PAGE_ANALYZE_ARTICLE,
    PAGE_EVIDENCE_COVERAGE,
    PAGE_METHODOLOGY,
]


def init_session_state():
    """Initializes standard session state keys safely and checks URL parameters."""
    defaults = {
        "current_page": PAGE_DASHBOARD,
        "analyzed_text": "",
        "selected_article_for_evidence": None,
        "monitor_query": "",
        "dash_search_input": "",
        "dash_quick_screen_text": "",
        "nm_search_input": "",
        "article_input_area": "",
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v

    # URL query parameter synchronization on initial load
    try:
        if hasattr(st, "query_params") and st.query_params:
            url_page = st.query_params.get("page")
            if url_page:
                page_slug_map = {
                    "dashboard": PAGE_DASHBOARD,
                    "monitor": PAGE_NEWS_MONITOR,
                    "analyze": PAGE_ANALYZE_ARTICLE,
                    "evidence": PAGE_EVIDENCE_COVERAGE,
                    "methodology": PAGE_METHODOLOGY,
                }
                if url_page in page_slug_map:
                    st.session_state["current_page"] = page_slug_map[url_page]
            url_q = st.query_params.get("q")
            if url_q:
                st.session_state["monitor_query"] = url_q
    except Exception:
        pass


def update_url_params():
    """Sync current page and search state to browser URL params for shareability."""
    try:
        if hasattr(st, "query_params"):
            page_to_slug = {
                PAGE_DASHBOARD: "dashboard",
                PAGE_NEWS_MONITOR: "monitor",
                PAGE_ANALYZE_ARTICLE: "analyze",
                PAGE_EVIDENCE_COVERAGE: "evidence",
                PAGE_METHODOLOGY: "methodology",
            }
            slug = page_to_slug.get(
                st.session_state.get("current_page", PAGE_DASHBOARD), "dashboard"
            )
            st.query_params["page"] = slug
            monitor_q = st.session_state.get("monitor_query", "")
            if monitor_q:
                st.query_params["q"] = monitor_q
            elif "q" in st.query_params:
                del st.query_params["q"]
    except Exception:
        pass


def navigate_to(page_name: str, payload: Dict = None):
    """Programmatically shifts current page and optional payload."""
    if page_name in PAGES:
        st.session_state["current_page"] = page_name
    if payload:
        for k, v in payload.items():
            st.session_state[k] = v
    update_url_params()


def render_sidebar(service: NewsLensService) -> str:
    """Renders the left research navigation panel matching Stitch design."""
    with st.sidebar:
        st.markdown(
            """
            <div style="padding: 12px 0 20px 0; border-bottom: 1px solid #E4E7EC; margin-bottom: 16px;">
                <div style="display:flex; align-items:flex-start; gap:10px;">
                    <div style="background:#183B56; color:#FFFFFF; border-radius:4px; width:34px; height:34px; display:flex; align-items:center; justify-content:center; font-size:18px;">
                        🔍
                    </div>
                    <div>
                        <div style="font-family:'Newsreader', Georgia, serif; font-size:1.35rem; font-weight:700; color:#183B56; line-height:1.15;">NewsLens India</div>
                        <div style="font-size:0.75rem; color:#667085; margin-top:3px; line-height:1.3;">See the coverage. Examine the evidence.</div>
                    </div>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        st.markdown(
            '<div style="font-size:0.72rem; font-weight:700; color:#667085; text-transform:uppercase; letter-spacing:0.04em; margin-bottom:8px;">INVESTIGATION DESK</div>',
            unsafe_allow_html=True,
        )

        # Map display labels with icons matching screenshot
        page_icons = {
            PAGE_DASHBOARD: "⊞  Overview",
            PAGE_NEWS_MONITOR: "◎  News Monitor",
            PAGE_ANALYZE_ARTICLE: "🔬 Analyze Article",
            PAGE_EVIDENCE_COVERAGE: "⚖  Evidence & Coverage",
            PAGE_METHODOLOGY: "📖 Methodology",
        }

        # Keep current selection in sync with session state
        current_idx = (
            PAGES.index(st.session_state["current_page"])
            if st.session_state["current_page"] in PAGES
            else 0
        )

        selected_page = st.radio(
            "Navigation Menu",
            PAGES,
            index=current_idx,
            format_func=lambda p: page_icons.get(p, p),
            label_visibility="collapsed",
        )

        if selected_page != st.session_state["current_page"]:
            st.session_state["current_page"] = selected_page
            update_url_params()

        st.markdown("<div style='margin-top:24px;'></div>", unsafe_allow_html=True)
        st.divider()

        # Operational Status Block (Real data only)
        st.markdown(
            f"""
            <div style="background-color:#F8F9FF; border:1px solid #D9E3F6; border-radius:4px; padding:12px; margin-bottom:12px;">
                <div style="display:flex; justify-content:space-between; align-items:center;">
                    <span style="font-size:10px; font-weight:700; color:#183B56; text-transform:uppercase; letter-spacing:0.03em;">Verified Datastore</span>
                    <span class="nl-badge nl-badge-teal" style="font-size:10px;">Live Sync</span>
                </div>
                <div style="font-size:1.4rem; font-weight:700; color:#183B56; font-family:'Inter', sans-serif; margin-top:4px;">
                    {service.db.get_article_count():,} <span style="font-size:0.75rem; color:#667085; font-weight:normal;">Articles</span>
                </div>
                <div style="font-size:0.76rem; color:#667085; margin-top:4px;">
                    Fact-Check Archives: <strong style="color:#183B56;">{service.retriever.total_records}</strong>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        # Ingestion actions
        if st.button("🔄 Refresh Sources", use_container_width=True):
            with st.spinner("Polling configured Indian news feeds..."):
                res = service.refresh_rss_feeds()
                st.toast(f"Fetched {res['total_fetched']} items ({res['new_stored']} new)")
                st.rerun()

        st.markdown(
            """
            <div style="margin-top:16px; padding:8px 0; font-size:0.72rem; color:#667085; border-top:1px solid #E4E7EC; line-height:1.4;">
                <div style="font-weight:600; color:#183B56;">Indian Media Observatory</div>
                <div>Near-Real-Time OSINT Research v0.8.2</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    return st.session_state["current_page"]
