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
import logging

import streamlit as st

from src.ingestion.models import STATUS_SUCCESS
from src.services.news_service import NewsLensService
from src.ui.components import render_empty_state, render_monitor_article_card, render_page_header

logger = logging.getLogger(__name__)

PAGE_ANALYZE_ARTICLE = "Analyze Article"
PAGE_EVIDENCE_COVERAGE = "Evidence & Coverage"


def _status_label(statuses: list[dict], feed_count: int) -> str:
    """Build the header status line from the most recent stored source_status row."""
    base = f"Open-Data Sources: GDELT Doc API + {feed_count} Monitored RSS Feeds"
    if not statuses:
        return base
    ts = statuses[0].get("last_refresh_at") or ""
    if ts:
        return f"Sources Synced: {ts[:16].replace('T', ' ')} UTC"
    return base


def render_news_monitor_page(service: NewsLensService) -> None:
    statuses = service.get_source_statuses()
    status_label = _status_label(statuses, len(service.rss.feeds))

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

        col_search, col_btn_search, col_btn_gdelt, col_btn_refresh, col_btn_reset = st.columns(
            [6, 2, 1.6, 1.4, 1.3]
        )
        with col_search:
            search_text = st.text_input(
                "Search coverage",
                value=initial_query,
                placeholder="Search All Monitored Streams...",
                label_visibility="collapsed",
                key="nm_search_input",
            )
        with col_btn_search:
            if st.button("🔍 Search Coverage", use_container_width=True, type="primary"):
                st.session_state["monitor_query"] = search_text.strip()
                st.session_state["nm_page"] = 1
                st.rerun()
        with col_btn_gdelt:
            if st.button(
                "🌐 Query GDELT",
                use_container_width=True,
                help="Run one bounded GDELT 2.0 DOC query for the search text above",
            ):
                gdelt_query = search_text.strip()
                if not gdelt_query:
                    st.toast("Enter a topic above before querying GDELT.")
                else:
                    with st.spinner("Querying the GDELT Doc API (throttled)…"):
                        try:
                            gdelt_res = service.search_gdelt(gdelt_query, max_records=25)
                        except Exception:
                            logger.exception("GDELT query failed")
                            st.toast("GDELT query failed — see logs.")
                        else:
                            if gdelt_res.status == STATUS_SUCCESS:
                                st.toast(
                                    f"GDELT returned {gdelt_res.items_count} records "
                                    f"({gdelt_res.duration_ms / 1000:.1f}s)"
                                )
                            else:
                                st.toast(
                                    "GDELT: " + gdelt_res.status.replace("_", " "),
                                    icon="⚠️",
                                )
                            st.rerun()
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
                st.session_state["nm_search_input"] = ""
                st.session_state["nm_page"] = 1
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
            temporal_filter = st.selectbox(
                "Temporal Scope",
                [
                    "Date: All Stored Records",
                    "Date: Past 24 Hours",
                    "Date: Past 7 Days",
                ],
                index=0,
                label_visibility="collapsed",
                key="nm_temporal_filter",
            )

        with col_f3:
            st.markdown(
                '<div style="font-size:10px; font-weight:700; color:#667085; text-transform:uppercase; margin-bottom:4px;">OUTLET DOMAIN</div>',
                unsafe_allow_html=True,
            )
            publisher_filter = st.selectbox(
                "Outlet Domain",
                ["Publisher: All Configured Outlets"] + service.get_distinct_publishers(),
                index=0,
                label_visibility="collapsed",
                key="nm_publisher_filter",
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
        active_criteria.append(f"{temporal_filter}")
        if not publisher_filter.startswith("Publisher: All"):
            active_criteria.append(f"Publisher: {publisher_filter}")
        active_criteria.append(f"Sort: {sort_order.removeprefix('Sort: ')}")
        criteria_badges = "".join(
            f'<span class="nl-badge nl-badge-navy">{html.escape(c)}</span>' for c in active_criteria
        )
        st.markdown(
            f"""
            <div style="display:flex; align-items:center; flex-wrap:wrap; gap:8px; margin-top:14px; font-size:11px;">
                <span style="color:#667085; font-weight:600;">Active Filters:</span>
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
    if source_filter.startswith("Source: All"):
        source_type_param = None
    elif "GDELT" in source_filter:
        source_type_param = "gdelt"
    elif "RSS" in source_filter:
        source_type_param = "rss"

    publisher_param = None if publisher_filter.startswith("Publisher: All") else publisher_filter
    temporal_days = {
        "Date: Past 24 Hours": 1,
        "Date: Past 7 Days": 7,
    }.get(temporal_filter)

    # Changing any filter restarts pagination so the page index stays valid.
    filter_signature = (
        search_text.strip(),
        source_filter,
        publisher_filter,
        temporal_filter,
        sort_order,
    )
    if st.session_state.get("nm_filter_signature") != filter_signature:
        st.session_state["nm_filter_signature"] = filter_signature
        st.session_state["nm_page"] = 1

    page_size = 10
    page = max(int(st.session_state.get("nm_page", 1)), 1)

    def _fetch_page(page_number: int) -> dict:
        return service.query_monitor_articles(
            query=search_text if search_text.strip() else None,
            source_type=source_type_param,
            publisher=publisher_param,
            days=temporal_days,
            limit=page_size,
            offset=(page_number - 1) * page_size,
            sort_order=sort_order,
        )

    monitor_res = _fetch_page(page)
    total_pages = monitor_res["total_pages"]
    if total_pages and page > total_pages:
        page = total_pages
        st.session_state["nm_page"] = page
        monitor_res = _fetch_page(page)

    articles = monitor_res["articles"]
    total_matching = monitor_res["total_matching"]

    query_display = (
        html.escape(search_text.strip()) if search_text.strip() else "All Monitored Streams"
    )
    first_shown = (page - 1) * page_size + 1 if articles else 0
    last_shown = (page - 1) * page_size + len(articles)

    st.markdown(
        f"""
        <div style="display:flex; justify-content:space-between; align-items:center; margin:16px 0 12px 0;">
            <div style="font-size:0.85rem; color:#183B56;">
                <strong>{total_matching} records identified</strong>
                (page {page} of {max(total_pages, 1)}) • Scope: "{query_display}"
            </div>
            <div style="display:flex; align-items:center; gap:8px;">
                <span class="nl-badge nl-badge-navy" style="font-size:10px;">📋 List View (Detailed)</span>
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
        for idx, art in enumerate(articles):
            render_monitor_article_card(
                article=art,
                index=idx,
                doc_id=f"Record ID: {art.id}",
                image_tag=art.source_type.upper(),
                image_color="#1e293b",
                on_screen_click=lambda a=art: (
                    st.session_state.update(
                        {
                            "current_page": PAGE_ANALYZE_ARTICLE,
                            "pending_article_text": a.title,
                            "nav_origin": "monitor",
                        }
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

        rss_count = sum(1 for a in articles if a.source_type == "rss")
        gdelt_count = sum(1 for a in articles if a.source_type == "gdelt")
        manual_count = len(articles) - rss_count - gdelt_count
        st.markdown(
            f"""
            <div style="display:flex; justify-content:space-between; align-items:center; padding:16px 0; border-top:1px solid #E4E7EC; margin-top:20px;">
                <div style="font-size:0.8rem; color:#667085;">
                    Showing <strong>{first_shown}–{last_shown}</strong> of <strong>{total_matching}</strong> matching records
                    • This page — RSS: {rss_count} · GDELT: {gdelt_count} · Manual: {manual_count}
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    if total_pages > 1:
        nav_prev, nav_info, nav_next = st.columns([1, 3, 1])
        with nav_prev:
            if st.button(
                "← Previous",
                use_container_width=True,
                disabled=page <= 1,
                key="nm_prev_page",
            ):
                st.session_state["nm_page"] = page - 1
                st.rerun()
        with nav_info:
            st.markdown(
                f'<div style="text-align:center; font-size:0.8rem; color:#667085; padding-top:8px;">'
                f"Page {page} of {total_pages}</div>",
                unsafe_allow_html=True,
            )
        with nav_next:
            if st.button(
                "Next →",
                use_container_width=True,
                disabled=page >= total_pages,
                key="nm_next_page",
            ):
                st.session_state["nm_page"] = page + 1
                st.rerun()
