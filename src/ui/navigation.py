"""
NewsLens India — sidebar navigation.

Keeps the persistent left rail in sync with session state, shows a real
operational-status strip from the database, and protects ingestion actions with
error boundaries so a single failed refresh cannot crash the whole session.
"""

from __future__ import annotations

import logging
from typing import Any, Dict

import streamlit as st

from src.services.news_service import NewsLensService

logger = logging.getLogger(__name__)

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


def init_session_state() -> None:
    """Safely initializes session-state defaults and mirrors URL params on first load."""
    defaults: Dict[str, Any] = {
        "current_page": PAGE_DASHBOARD,
        "analyzed_text": "",
        "selected_article_for_evidence": None,
        "monitor_query": "",
        "dash_search_input": "",
        "dash_quick_screen_text": "",
        "nm_search_input": "",
        "article_input_area": "",
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value

    try:
        if hasattr(st, "query_params") and st.query_params:
            page_slug_map = {
                "dashboard": PAGE_DASHBOARD,
                "monitor": PAGE_NEWS_MONITOR,
                "analyze": PAGE_ANALYZE_ARTICLE,
                "evidence": PAGE_EVIDENCE_COVERAGE,
                "methodology": PAGE_METHODOLOGY,
            }
            url_page = st.query_params.get("page")
            if url_page and url_page in page_slug_map:
                st.session_state["current_page"] = page_slug_map[url_page]

            url_q = st.query_params.get("q")
            if url_q:
                st.session_state["monitor_query"] = url_q
    except Exception as e:
        logger.debug("URL param initialization error: %s", e)


def update_url_params() -> None:
    """Mirror the current page and monitor query into browser URL params."""
    try:
        if not hasattr(st, "query_params"):
            return

        page_to_slug = {
            PAGE_DASHBOARD: "dashboard",
            PAGE_NEWS_MONITOR: "monitor",
            PAGE_ANALYZE_ARTICLE: "analyze",
            PAGE_EVIDENCE_COVERAGE: "evidence",
            PAGE_METHODOLOGY: "methodology",
        }
        current_page = st.session_state.get("current_page", PAGE_DASHBOARD)
        slug = page_to_slug.get(current_page, "dashboard")
        st.query_params["page"] = slug

        monitor_q = st.session_state.get("monitor_query", "")
        if monitor_q:
            st.query_params["q"] = monitor_q
        elif "q" in st.query_params:
            del st.query_params["q"]
    except Exception as e:
        logger.debug("URL param update error: %s", e)


def navigate_to(page_name: str, payload: Dict[str, Any] | None = None) -> None:
    """Navigate to *page_name* and optionally stash a payload in session state."""
    if page_name in PAGES:
        st.session_state["current_page"] = page_name
    if payload:
        for key, value in payload.items():
            st.session_state[key] = value
    update_url_params()


def render_sidebar(service: NewsLensService) -> str:
    """Render the persistent investigation-desk sidebar and return the current page."""
    with st.sidebar:
        st.markdown(
            """
            <div style="padding: 12px 0 20px 0; border-bottom: 1px solid #E4E7EC; margin-bottom: 16px;">
                <div style="display:flex; align-items:flex-start; gap:10px;">
                    <div style="background:#183B56; color:#FFFFFF; border-radius:4px; width:34px; height:34px; display:flex; align-items:center; justify-content:center; font-size:18px;">
                        🔍
                    </div>
                    <div>
                        <div style="font-family:'Newsreader', Georgia, serif; font-size:1.35rem; font-weight:700; color:#183B56; line-height:1.15;">
                            NewsLens India
                        </div>
                        <div style="font-size:0.75rem; color:#667085; margin-top:3px; line-height:1.3;">
                            See the coverage. Examine the evidence.
                        </div>
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

        page_icons = {
            PAGE_DASHBOARD: "⊞  Overview",
            PAGE_NEWS_MONITOR: "◎  News Monitor",
            PAGE_ANALYZE_ARTICLE: "🔬 Analyze Article",
            PAGE_EVIDENCE_COVERAGE: "⚖  Evidence & Coverage",
            PAGE_METHODOLOGY: "📖 Methodology",
        }

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

        # Operational status strip — only real data from the database.
        total_arts = int(service.db.get_article_count())
        fc_count = int(getattr(service.retriever, "total_records", 0))
        statuses = service.get_source_statuses()
        last_refresh = "Not measured"
        if statuses:
            ts = statuses[0].get("last_refresh_at") or ""
            if ts:
                last_refresh = ts[:16].replace("T", " ") + " UTC"

        st.markdown(
            f"""
            <div style="background-color:#F8F9FF; border:1px solid #D9E3F6; border-radius:4px; padding:12px; margin-bottom:12px;">
                <div style="display:flex; justify-content:space-between; align-items:center;">
                    <span style="font-size:10px; font-weight:700; color:#183B56; text-transform:uppercase; letter-spacing:0.03em;">Verified Datastore</span>
                    <span class="nl-badge nl-badge-teal" style="font-size:10px;">SQLite WAL</span>
                </div>
                <div style="font-size:1.4rem; font-weight:700; color:#183B56; font-family:'Inter', sans-serif; margin-top:4px;">
                    {total_arts:,} <span style="font-size:0.75rem; color:#667085; font-weight:normal;">Articles</span>
                </div>
                <div style="font-size:0.76rem; color:#667085; margin-top:4px;">
                    Fact-Check Archives:
                    <strong style="color:#183B56;">{fc_count:,} indexed</strong>
                </div>
                <div style="font-size:0.72rem; color:#667085; margin-top:2px;">
                    Last Ingestion:
                    <span style="color:#183B56;">{last_refresh}</span>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        # Ingestion actions — wrapped so one failed refresh cannot crash the session.
        if st.button("🔄 Refresh Sources", use_container_width=True):
            with st.spinner("Polling configured Indian news feeds..."):
                try:
                    res = service.refresh_rss_feeds()
                    st.toast(f"Fetched {res.total_fetched} items ({res.new_stored} new stored)")
                except Exception as exc:
                    st.toast("Refresh failed — check logs.")
                    st.exception(exc)
            st.rerun()

        st.markdown(
            """
            <div style="margin-top:16px; padding:8px 0; font-size:0.72rem; color:#667085; border-top:1px solid #E4E7EC; line-height:1.4;">
                <div style="font-weight:600; color:#183B56;">Indian Media Observatory</div>
                <div>Near-Real-Time OSINT Research</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    return st.session_state["current_page"]
