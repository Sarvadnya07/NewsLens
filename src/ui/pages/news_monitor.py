"""
News Monitor — NewsLens India main inspection screen.

Discovery + audit surface for recent coverage:
- Real filters wired through NewsLensService.query_monitor_articles.
- Real scrollable article cards via render_monitor_article_card.
- Source-status strip derived from stored source_status rows.
- Refresh action protected by an error boundary so a single bad feed cannot
  crash the whole session.
"""

from __future__ import annotations

import html

import streamlit as st

from src.services.news_service import NewsLensService
from src.ui.components import render_empty_state, render_monitor_article_card, render_page_header

PAGE_ANALYZE_ARTICLE = "Analyze Article"
PAGE_EVIDENCE_COVERAGE = "Evidence & Coverage"


def _status_label(statuses: list[dict]) -> str:
    """Build the header status line from the most recent stored source_status row."""
    base = "Open-Data Sources: GDELT Doc API + 6 Monitored RSS Feeds"
    if not statuses:
        return base
    ts = statuses[0].get("last_refresh_at") or ""
    if ts:
        return f"Sources Synced: {ts[:16].replace('T', ' ')} UTC"
    return base


def render_news_monitor_page(service: NewsLensService) -> None:
    statuses = service.get_source_statuses()
    status_label = _status_label(statuses)

    render_page_header(
        title="News Monitor",
        subtitle="Discover, audit, and cross-reference recent coverage across the Indian news ecosystem.",
        meta_tag="CONTINUOUS NEWS STREAM LEDGER",
        status_label=status_label,
    )

    initial_query = st.session_state.get("monitor_query", "")

    with st.container():
        st.markdown(
            """
            <div style="background-color:#FFFFFF; border:1px solid #E4E7EC; border-radius:4px; padding:16px 20px; margin-bottom:12px;">
                <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:12px;">
            """,
            unsafe_allow_html=True,
        )

        col_search, col_btn_search, col_btn_refresh, col_btn_reset = st.columns([6, 2, 1.5, 1.5])
        with col_search:
            search_text = st.text_input(
                "Search coverage",
                value=initial_query,
                placeholder="Search All Monitored Streams...",
                label_visibility="collapsed",
                key="nm_search_input",
            )
        with col_btn_search:
            st.button("🔍 Search Coverage", use_container_width=True, type="primary")
        with col_btn_refresh:
            if st.button("🔄 Refresh", use_container_width=True):
                with st.spinner("Syncing latest feeds..."):
                    try:
                        res = service.refresh_rss_feeds()
                        st.toast(f"Synced {res.total_fetched} updates ({res.new_stored} new)")
                    except Exception as exc:
                        st.toast("Refresh failed — check logs.")
                        st.exception(exc)
                        st.rerun()
                    else:
                        st.rerun()
        with col_btn_reset:
            if st.button(
                "Reset",
                use_container_width=True,
                help="Clear query and reset filters to default",
            ):
                st.session_state["monitor_query"] = ""
                st.toast("Filters reset to default view.")
                st.rerun()

        col_f1, col_f2, col_f3, col_f4 = st.columns(4)

        with col_f1:
            st.markdown(
                '<div style="font-size:10px; font-weight:700; color:#667085; text-transform:uppercase; margin-bottom:4px;">INGESTION PIPE</div>',
                unsafe_allow_html=True,
            )
            source_filter = st.selectbox(
                "Ingestion Pipe",
                [
                    "Source: All (GDELT + RSS)",
                    "Source: GDELT DOC API",
                    "Source: Syndicated RSS",
                ],
                index=0,
                label_visibility="collapsed",
            )

        with col_f2:
            st.markdown(
                '<div style="font-size:10px; font-weight:700; color:#667085; text-transform:uppercase; margin-bottom:4px;">TEMPORAL SCOPE</div>',
                unsafe_allow_html=True,
            )
            st.selectbox(
                "Temporal Scope",
                [
                    "Date: All Stored Records",
                    "Date: Past 24 Hours",
                    "Date: Past 7 Days",
                ],
                index=0,
                label_visibility="collapsed",
            )

        with col_f3:
            st.markdown(
                '<div style="font-size:10px; font-weight:700; color:#667085; text-transform:uppercase; margin-bottom:4px;">OUTLET DOMAIN</div>',
                unsafe_allow_html=True,
            )
            st.selectbox(
                "Outlet Domain",
                [
                    "Publisher: All Configured Outlets",
                    "Publisher: The Times of India",
                    "Publisher: The Hindu",
                    "Publisher: NDTV",
                    "Publisher: Indian Express",
                    "Publisher: Hindustan Times",
                    "Publisher: Livemint",
                ],
                index=0,
                label_visibility="collapsed",
            )

        with col_f4:
            st.markdown(
                '<div style="font-size:10px; font-weight:700; color:#667085; text-transform:uppercase; margin-bottom:4px;">RANKING METRIC</div>',
                unsafe_allow_html=True,
            )
            sort_order = st.selectbox(
                "Ranking Metric",
                [
                    "Sort: Most Recent (Ingested)",
                    "Sort: Chronological (Oldest)",
                ],
                index=0,
                label_visibility="collapsed",
            )

        active_criteria = [f"Source: {source_filter.removeprefix('Source: ')}"]
        if search_text.strip():
            active_criteria.append(f"Query: {search_text.strip()}")
        active_criteria.append(f"Sort: {sort_order.removeprefix('Sort: ')}")
        criteria_badges = "".join(
            f'<span class="nl-badge nl-badge-navy">{html.escape(c)}</span>' for c in active_criteria
        )
        st.markdown(
            f"""
            <div style="display:flex; align-items:center; flex-wrap:wrap; gap:8px; margin-top:14px; font-size:11px;">
                <span style="color:#667085; font-weight:600;">Active Criteria:</span>
                {criteria_badges}
            </div>
            """,
            unsafe_allow_html=True,
        )

    st.markdown(
        """
        <div style="background-color:#EEF4F7; border:1px solid #D0DCE3; border-radius:4px; padding:10px 14px; margin-bottom:16px; display:flex; justify-content:space-between; align-items:center; font-size:0.8rem; color:#183B56;">
            <div>
                <strong>ℹ️ Methodological Note:</strong> Results aggregate open syndicated feeds and GDELT open-data endpoints.
                Duplicate reports frequently represent wire distribution (PTI/ANI) rather than independent corroboration.
            </div>
            <a href="?page=methodology" style="color:#167C80; font-weight:600; text-decoration:none; white-space:nowrap; margin-left:12px;">Review pipeline specs ↗</a>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # Translate UI filter labels to service parameters.
    source_type_param: str | None = None
    if "All" in source_filter:
        source_type_param = None
    elif "GDELT" in source_filter:
        source_type_param = "gdelt"
    elif "RSS" in source_filter:
        source_type_param = "rss"

    monitor_res = service.query_monitor_articles(
        query=search_text if search_text.strip() else None,
        source_type=source_type_param,
        limit=50,
        sort_order=sort_order,
    )
    articles = monitor_res["articles"]
    total_matching = monitor_res["total_matching"]

    query_display = (
        html.escape(search_text.strip()) if search_text.strip() else "All Monitored Streams"
    )

    st.markdown(
        f"""
        <div style="display:flex; justify-content:space-between; align-items:center; margin:16px 0 12px 0;">
            <div style="font-size:0.85rem; color:#183B56;">
                <strong>{total_matching} records identified</strong>
                (showing {len(articles)}) • Scope: "{query_display}"
            </div>
            <div style="display:flex; align-items:center; gap:8px;">
                <span class="nl-badge nl-badge-navy" style="font-size:10px;">📋 List View (Detailed)</span>
                <span class="nl-badge nl-badge-neutral" style="font-size:10px;">📊 Dense Table View</span>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    if not articles:
        render_empty_state(
            title="No articles match criteria",
            message="No stored articles match the query or source filter selected.",
            suggestion=(
                "Try clearing search filters or click 'Refresh' to fetch fresh "
                "international & Indian records."
            ),
        )
    else:
        for idx, art in enumerate(articles[:10]):
            render_monitor_article_card(
                article=art,
                index=idx,
                doc_id=f"Record ID: {art.id}",
                image_tag=art.source_type.upper(),
                image_color="#1e293b",
                on_screen_click=lambda a=art: (
                    st.session_state.update(
                        {"current_page": PAGE_ANALYZE_ARTICLE, "analyzed_text": a.title}
                    ),
                    st.rerun(),
                ),
                on_evidence_click=lambda a=art: (
                    st.session_state.update(
                        {"current_page": PAGE_EVIDENCE_COVERAGE, "selected_article_for_evidence": a}
                    ),
                    st.rerun(),
                ),
            )

        shown = min(10, len(articles))
        rss_count = sum(1 for a in articles if a.source_type == "rss")
        gdelt_count = sum(1 for a in articles if a.source_type == "gdelt")
        manual_count = len(articles) - rss_count - gdelt_count
        st.markdown(
            f"""
            <div style="display:flex; justify-content:space-between; align-items:center; padding:16px 0; border-top:1px solid #E4E7EC; margin-top:20px;">
                <div style="font-size:0.8rem; color:#667085;">
                    Showing <strong>1–{shown}</strong> of <strong>{total_matching}</strong> matching records
                    • RSS: {rss_count} · GDELT: {gdelt_count} · Manual: {manual_count}
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
