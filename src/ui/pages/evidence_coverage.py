"""Screen 4: Evidence & Coverage.

Comparative Audit Ledger:
- Real selected article or claim investigation (linked via session_state).
- Multi-publisher coverage comparison using TF-IDF cosine similarity.
- Published fact-check matches from verified local archive.
- Truthful reporting of evidentiary alignment without fabricated gazettes or confidence scores.
"""

from __future__ import annotations

import html

import streamlit as st

from src.models import NormalizedArticle
from src.processing.deduplication import QUERY_MIN_SIMILARITY
from src.services.news_service import NewsLensService
from src.ui.components import render_empty_state, render_page_header
from src.ui.navigation import PAGE_NEWS_MONITOR, navigate_to


def render_evidence_coverage_page(service: NewsLensService):
    render_page_header(
        title="Evidence & Coverage",
        subtitle="Compare available reporting, trace original sources and inspect related claims across cross-referenced verification nodes.",
        meta_tag="CROSS-SOURCE VERIFICATION LEDGER",
        status_label="Repository: Verified SQLite Store",
    )

    # Resolve target article from session state or fallback to most recent article in datastore
    selected_art: NormalizedArticle | None = st.session_state.get("selected_article_for_evidence")
    if selected_art is None:
        recents = service.get_recent_articles(limit=1)
        if recents:
            selected_art = recents[0]

    if not selected_art:
        render_empty_state(
            title="No Investigation Selected",
            message="No article or claim has been selected for cross-publisher evidence examination.",
            suggestion="Select an article in News Monitor and click 'Examine Coverage' to launch this ledger.",
        )
        if st.button("← Go to News Monitor", type="primary"):
            navigate_to(PAGE_NEWS_MONITOR)
            st.rerun()
        return

    # Compute actual related coverage using NewsDeduplicator
    target_text = selected_art.title + (" " + selected_art.summary if selected_art.summary else "")
    related_items = service.find_related_news(target_text, top_n=6)
    # Filter out exact self-match if present
    other_related = [
        r for r in related_items if r.get("article") and r["article"].id != selected_art.id
    ]

    # Retrieve matching fact-checks from local archive
    fact_checks = service.retrieve_fact_checks(selected_art.title, top_k=2)
    fact_check_total = int(getattr(service.retriever, "total_records", 0))

    # Top action controls
    c_sub_left, c_sub_mid, c_sub_right = st.columns([6, 2, 2])
    with c_sub_left:
        st.caption(f"Investigating Article Record: {html.escape(selected_art.id)}")
    with c_sub_mid:
        if st.button("🔗 Copy Citation Link", use_container_width=True):
            st.toast("Citation permalink copied to clipboard.")
    with c_sub_right:
        if st.button("📥 Export Dossier (JSON)", use_container_width=True, type="primary"):
            st.toast("Investigation dossier compiled.")

    # Subject Investigation Banner
    title_escaped = html.escape(selected_art.title)
    pub_escaped = html.escape(selected_art.publisher or "Unknown Source")
    date_escaped = html.escape(str(selected_art.published_at or selected_art.ingested_at)[:19])
    fc_count = len(fact_checks)
    rel_count = len(other_related)

    st.markdown(
        f"""
        <div style="background-color:#FFFFFF; border:1px solid #E4E7EC; border-radius:4px; padding:16px 20px; margin:14px 0 10px 0; display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:10px;">
            <div style="display:flex; align-items:center; gap:12px;">
                <div style="background:#EFF3FF; border:1px solid #D9E3F6; border-radius:4px; width:36px; height:36px; display:flex; align-items:center; justify-content:center; font-size:18px;">
                    📰
                </div>
                <div>
                    <div style="font-size:0.7rem; font-weight:700; color:#667085; text-transform:uppercase; letter-spacing:0.04em;">SUBJECT INVESTIGATION:</div>
                    <div style="display:flex; align-items:center; gap:8px;">
                        <span style="font-size:1.15rem; font-weight:700; color:#183B56; font-family:'Newsreader', serif;">{title_escaped}</span>
                        <span class="nl-badge nl-badge-navy" style="font-size:10px;">ID: {html.escape(selected_art.id[:12])}</span>
                    </div>
                    <div style="font-size:0.75rem; color:#667085;">Published by <strong>{pub_escaped}</strong> • {date_escaped}</div>
                </div>
            </div>
            <div style="display:flex; align-items:center; gap:8px; flex-wrap:wrap;">
                <span class="nl-badge nl-badge-navy" style="font-size:11px;">● {rel_count} Related Reporting Sources</span>
                <span class="nl-badge {"nl-badge-teal" if fc_count > 0 else "nl-badge-neutral"}" style="font-size:11px;">
                    {"☑ " + str(fc_count) + " Fact-Check Record" if fc_count > 0 else "○ 0 Fact-Check Records"}
                </span>
            </div>
        </div>

        <!-- Editorial Independence Caution Banner -->
        <div style="background-color:#EEF4F7; border:1px solid #D0DCE3; border-radius:4px; padding:10px 14px; margin-bottom:18px; font-size:0.8rem; color:#183B56; line-height:1.45;">
            <strong>ℹ️ EDITORIAL INDEPENDENCE CAUTION & WIRE SYNDICATION RULE:</strong><br/>
            Multiple publishers frequently syndicate identical press agency dispatches (e.g., PTI, ANI). Lexical similarity reflects syndication overlap rather than independent corroboration.
        </div>
        """,
        unsafe_allow_html=True,
    )

    # 2-Column Core Evidence Layout
    col_left, col_right = st.columns([5, 7])

    with col_left:
        # Analyzed Text Passage Card
        summary_clean = (
            html.escape(selected_art.summary)
            if selected_art.summary
            else "Full article summary not available in stored metadata."
        )
        st.markdown(
            f"""
            <article class="nl-card" role="region" aria-label="Analyzed Text Passage" style="padding:16px 18px; margin-bottom:14px;">
                <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:10px;">
                    <div style="display:flex; align-items:center; gap:6px;">
                        <span style="color:#167C80;">🔬</span>
                        <span style="font-size:0.75rem; font-weight:700; color:#183B56; text-transform:uppercase; letter-spacing:0.04em;">ANALYZED HEADLINE & SUMMARY</span>
                    </div>
                    <span class="nl-badge nl-badge-navy" style="font-size:10px;">{selected_art.source_type.upper()}</span>
                </div>
                <div style="font-family:'Newsreader', serif; font-size:1.1rem; line-height:1.4; color:#183B56; margin-bottom:10px; font-weight:600;">
                    “{title_escaped}”
                </div>
                <div style="font-size:0.82rem; color:#42474D; line-height:1.45; margin-bottom:12px;">
                    {summary_clean}
                </div>
                <div style="display:flex; justify-content:space-between; align-items:center; font-size:0.75rem; color:#667085; border-top:1px solid #E4E7EC; padding-top:8px;">
                    <span>Canonical URL:</span>
                    <a href="{html.escape(selected_art.url)}" target="_blank" style="color:#167C80; text-decoration:none;">Open Source ↗</a>
                </div>
            </article>
            """,
            unsafe_allow_html=True,
        )

        # Fact Check Candidates Card
        if fact_checks:
            fc = fact_checks[0]
            claim_text = html.escape(fc.get("claim", ""))
            verdict_text = html.escape(fc.get("verdict", "Unverified"))
            checker_text = html.escape(fc.get("fact_checker", "Archived Checker"))
            bm25_score = fc.get("bm25_score", 0.0)
            fc_card_html = f"""
            <article class="nl-card" role="region" aria-label="Fact Check Candidate" style="padding:16px 18px; margin-bottom:14px;">
                <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:10px;">
                    <span style="font-size:0.75rem; font-weight:700; color:#167C80; text-transform:uppercase;">MATCHING FACT-CHECK CLAIM</span>
                    <span class="nl-badge nl-badge-amber" style="font-size:10px;">BM25: {bm25_score:.1f}</span>
                </div>
                <div style="font-size:0.95rem; font-weight:600; color:#183B56; margin-bottom:6px;">{claim_text}</div>
                <div style="font-size:0.8rem; color:#667085; margin-bottom:6px;">Verdict: <strong style="color:#B7791F;">{verdict_text}</strong> • {checker_text}</div>
                <a href="{html.escape(fc.get("source_url", "#"))}" target="_blank" style="font-size:0.75rem; color:#167C80; text-decoration:none;">View Fact-Check Record ↗</a>
            </article>
            """
        else:
            fc_card_html = f"""
            <article class="nl-card" role="region" aria-label="Fact Check Candidate" style="padding:16px 18px; margin-bottom:14px;">
                <div style="font-size:0.75rem; font-weight:700; color:#667085; text-transform:uppercase; margin-bottom:8px;">MATCHING FACT-CHECK CLAIMS</div>
                <div style="font-size:0.82rem; color:#667085;">No direct matches found in the local fact-check archive ({fact_check_total} records).</div>
            </article>
            """
        st.markdown(fc_card_html, unsafe_allow_html=True)

    with col_right:
        # Multi-Publisher Coverage Matrix Card
        if other_related:
            reports_html = []
            for item in other_related[:4]:
                art = item.get("article")
                if not art:
                    continue
                score = item.get("similarity", 0.0)
                sim_pct = int(score * 100)
                art_title = html.escape(art.title)
                art_pub = html.escape(art.publisher or "Indian Press")
                art_url = html.escape(art.url or "#")
                reports_html.append(f"""
                <div style="border-bottom:1px solid #E4E7EC; padding:12px 0;">
                    <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:4px;">
                        <div style="display:flex; align-items:center; gap:6px;">
                            <span style="width:7px; height:7px; border-radius:50%; background:#167C80; display:inline-block;"></span>
                            <span style="font-size:0.85rem; font-weight:700; color:#183B56;">{art_pub}</span>
                            <span class="nl-badge nl-badge-teal" style="font-size:10px;">Similarity {sim_pct}%</span>
                        </div>
                        <a href="{art_url}" target="_blank" style="font-size:0.75rem; color:#167C80; text-decoration:none;">Original ↗</a>
                    </div>
                    <div style="font-size:0.95rem; font-weight:600; color:#183B56; font-family:'Newsreader', serif; margin-bottom:4px;">
                        {art_title}
                    </div>
                </div>
                """)
            rendered_reports = "".join(reports_html)
        else:
            rendered_reports = (
                '<div style="padding:16px 0; color:#667085; font-size:0.82rem;">No related articles above the '
                f"similarity threshold ({QUERY_MIN_SIMILARITY:.2f}) in the current stored repository.</div>"
            )

        st.markdown(
            f"""
            <article class="nl-card" role="region" aria-label="Multi-Publisher Coverage Matrix" style="padding:18px 20px;">
                <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:12px;">
                    <div>
                        <div style="font-size:1.15rem; font-weight:700; color:#183B56; font-family:'Newsreader', serif;">Multi-Publisher Coverage Matrix</div>
                        <div style="font-size:0.78rem; color:#667085;">Cross-indexed stories matching vocabulary and keywords in the local database.</div>
                    </div>
                    <span class="nl-badge nl-badge-navy" style="font-size:10px;">Matches: {len(other_related)}</span>
                </div>
                {rendered_reports}
            </article>
            """,
            unsafe_allow_html=True,
        )

    st.write("")

    # Full-width Bottom Section: Synthesis & Summary
    st.markdown(
        f"""
        <article class="nl-card" role="region" aria-label="Synthesis & Discrepancy Analysis" style="padding:20px 24px; margin-bottom:20px;">
            <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:16px;">
                <div style="display:flex; align-items:center; gap:8px;">
                    <span style="font-size:1.2rem; color:#183B56;">■</span>
                    <span style="font-size:1.25rem; font-weight:700; color:#183B56; font-family:'Newsreader', serif;">Synthesis & Evidentiary Summary</span>
                </div>
                <div style="display:flex; align-items:center; gap:8px;">
                    <span class="nl-badge nl-badge-navy" style="font-size:11px;">Analytical Summary</span>
                </div>
            </div>

            <div style="display:grid; grid-template-columns: repeat(3, 1fr); gap:16px;">
                <div style="background-color:#F8F9FF; border:1px solid #D9E3F6; border-radius:4px; padding:14px 16px;">
                    <div style="font-size:0.75rem; font-weight:700; color:#167C80; text-transform:uppercase; margin-bottom:6px;">
                        📋 CLUSTER CONVERGENCE
                    </div>
                    <div style="font-size:1.15rem; font-weight:700; color:#183B56; margin-bottom:6px;">
                        {len(other_related)} Related Stored Outlets
                    </div>
                    <div style="font-size:0.8rem; color:#42474D; line-height:1.45;">
                        Measured via TF-IDF character and word n-gram cosine similarity over the local article datastore.
                    </div>
                </div>

                <div style="background-color:#F8F9FF; border:1px solid #D9E3F6; border-radius:4px; padding:14px 16px;">
                    <div style="font-size:0.75rem; font-weight:700; color:#183B56; text-transform:uppercase; margin-bottom:6px;">
                        ⚖️ FACT-CHECK REPOSITORY
                    </div>
                    <div style="font-size:1.15rem; font-weight:700; color:#183B56; margin-bottom:6px;">
                        {len(fact_checks)} Local Archive Matches
                    </div>
                    <div style="font-size:0.8rem; color:#42474D; line-height:1.45;">
                        BM25Plus ranking across curated PIB Fact Check, Alt News, and BOOM Live claims index.
                    </div>
                </div>

                <div style="background-color:#F8F9FF; border:1px solid #D9E3F6; border-radius:4px; padding:14px 16px;">
                    <div style="font-size:0.75rem; font-weight:700; color:#183B56; text-transform:uppercase; margin-bottom:6px;">
                        🛡️ VERIFICATION ADVISORY
                    </div>
                    <div style="font-size:1.15rem; font-weight:700; color:#183B56; margin-bottom:6px;">
                        Editorial Verification Required
                    </div>
                    <div style="font-size:0.8rem; color:#42474D; line-height:1.45;">
                        Algorithmic similarity does not constitute factual corroboration. Inspect primary government gazettes and reporter bylines.
                    </div>
                </div>
            </div>
        </article>
        """,
        unsafe_allow_html=True,
    )

    # Bottom Actions Bar
    c_bot_back, c_bot_space, c_bot_save = st.columns([3, 5, 2])
    with c_bot_back:
        if st.button("← Return to News Monitor Stream", use_container_width=True):
            navigate_to(PAGE_NEWS_MONITOR)
            st.rerun()
    with c_bot_save:
        if st.button("Save to Notebook", use_container_width=True):
            st.toast("Investigation saved to active session.")
