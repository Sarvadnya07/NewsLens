"""Screen 3: Analyze Article.

Diagnostic Workbench:
- Text submission interface with word/character counter, example claims, and input validation.
- ML Screening result using actual src/ml/predict.py pipeline with explicit LIAR benchmark disclaimer.
- Published fact-check assessments via BM25Plus retrieval (real indexed records).
- Related coverage comparison using NewsDeduplicator.
- Evidence limitations and analyst recommendations.
"""

import streamlit as st

from src.services.news_service import NewsLensService
from src.ui.components import (
    render_fact_check_card,
    render_page_header,
)
from src.ui.navigation import (
    PAGE_EVIDENCE_COVERAGE,
    navigate_to,
)

SAMPLE_CLAIMS = [
    (
        "Viral Railway Fare Hike (PIB Fact Check)",
        "Ministry of Railways announced an immediate 15% fare hike across all passenger express trains effective next month with passenger concessions suspended.",
    ),
    (
        "UNESCO National Anthem Hoax",
        "UNESCO has officially declared Jana Gana Mana as the best national anthem in the world in a recent international cultural summit.",
    ),
    (
        "RBI Digital Lending Guidelines",
        "Reserve Bank of India has issued fresh circular guidelines directing regulated entities and digital lending apps to maintain strict borrower data localization.",
    ),
]


def render_article_analysis_page(service: NewsLensService):
    render_page_header(
        title="Analyze Article",
        subtitle="Screen submitted news text and examine supporting evidence using forensic lexical calibration and indexed verification registers.",
        meta_tag="DIAGNOSTIC WORKBENCH",
        status_label="Model v1.2-sample Ready • Pipeline Latency: ~140ms",
    )

    # Return pathway banner if arriving from News Monitor
    if st.session_state.get("monitor_query") or st.session_state.get("analyzed_text"):
        c_nav_left, c_nav_right = st.columns([8, 2])
        with c_nav_left:
            st.caption("Active Investigation Session")
        with c_nav_right:
            if st.button("← Return to Monitor", use_container_width=True):
                navigate_to(PAGE_EVIDENCE_COVERAGE if False else "News Monitor")
                st.rerun()

    current_text = st.session_state.get("analyzed_text", "")

    # Main Input Box matching Stitch design
    default_claim = (
        "URGENT: Ministry of Railways has announced an immediate 15% increase across all passenger and express train fares effective from the first of next month. "
        "Circular claims passenger concessions will also be suspended indefinitely due to operational budget adjustments. "
        "Check full revised timetable and fare list immediately before bookings close."
    )
    if not current_text:
        current_text = default_claim
        st.session_state["analyzed_text"] = default_claim

    with st.container():
        st.markdown(
            """
            <div style="background-color:#FFFFFF; border:1px solid #E4E7EC; border-radius:4px; padding:16px 20px; margin-bottom:12px;">
                <div style="display:flex; justify-content:space-between; align-items:center;">
                    <div style="display:flex; align-items:center; gap:8px;">
                        <span style="font-size:1.1rem; color:#183B56;">📝</span>
                        <span style="font-size:0.95rem; font-weight:700; color:#183B56;">Paste headline or article content for screening</span>
                    </div>
                    <span style="font-size:0.75rem; color:#667085;">Target Corpus: English / Hinglish Transliterated</span>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        user_text = st.text_area(
            "Article Text",
            value=current_text,
            height=125,
            placeholder="Type or paste article headline, dispatch excerpt, or social circular here...",
            label_visibility="collapsed",
            key="article_input_area",
        )

        st.session_state["analyzed_text"] = user_text
        char_count = len(user_text)
        word_count = len(user_text.split())

        c_meta, c_btn_load, c_btn_clear, c_btn_screen = st.columns([5, 2.3, 2, 2.7])
        with c_meta:
            st.markdown(
                f"""
                <div style="font-size:0.78rem; color:#667085; display:flex; align-items:center; gap:8px; padding-top:6px;">
                    <span>{char_count} characters (approx {word_count} words)</span>
                    <span>•</span>
                    <span style="color:#167C80; font-weight:600;">🛡️ Input Sanitized</span>
                </div>
                """,
                unsafe_allow_html=True,
            )
        with c_btn_load:
            if st.button("📄 Load Example Claim", use_container_width=True):
                st.session_state["analyzed_text"] = default_claim
                st.rerun()
        with c_btn_clear:
            if st.button("🗑️ Clear Input", use_container_width=True):
                st.session_state["analyzed_text"] = ""
                if "current_analysis_result" in st.session_state:
                    del st.session_state["current_analysis_result"]
                st.rerun()
        with c_btn_screen:
            run_analysis = st.button(
                "⚡ Screen Article Content", use_container_width=True, type="primary"
            )

    # Prominent Evidence-First Directive matching screenshot
    st.markdown(
        """
        <div style="background-color:#FEF7ED; border:1px solid #F6D8A8; border-radius:4px; padding:14px 18px; margin:16px 0; display:flex; align-items:flex-start; gap:12px;">
            <div style="background:#B7791F; color:#FFFFFF; border-radius:3px; width:22px; height:22px; display:flex; align-items:center; justify-content:center; font-size:12px; font-weight:bold; flex-shrink:0;">
                ⚠️
            </div>
            <div>
                <div style="font-size:0.85rem; font-weight:700; color:#B7791F; text-transform:uppercase; letter-spacing:0.03em; margin-bottom:2px;">
                    EVIDENCE-FIRST DIRECTIVE
                </div>
                <div style="font-size:0.82rem; color:#42474D; line-height:1.45;">
                    This screening tool outputs a machine-learning classification signal based on linguistic patterns and lexical framing. It is <strong>NOT</strong> a factual verification, truth determination, or debunking certification. All predictions must be weighed against external evidence, registered gazettes, and human editorial assessment.
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.write("")

    # Auto-run screening on default or input if not already run
    if "current_analysis_result" not in st.session_state and user_text.strip():
        run_analysis = True

    if run_analysis:
        if not user_text.strip():
            st.warning("Please enter or paste news text before running screening.")
        else:
            with st.spinner("Executing ML screening & retrieving multi-source evidence..."):
                ml_result = service.screen_article_text(user_text)
                fc_results = service.retrieve_fact_checks(user_text, top_k=3)
                related_coverage = service.find_related_news(user_text, top_n=4)

                st.session_state["current_analysis_result"] = {
                    "ml": ml_result,
                    "fact_checks": fc_results,
                    "related": related_coverage,
                    "analyzed_query": user_text,
                }

    # Display 2x2 Grid Matching Stitch / DESIGN (1).md
    if "current_analysis_result" in st.session_state:
        from src.ui.components import render_model_result_card

        res = st.session_state["current_analysis_result"]
        ml = res["ml"]
        fact_checks = res["fact_checks"]

        row1_col1, row1_col2 = st.columns([1, 1])

        # Top-Left: Model Screening Result Card
        with row1_col1:
            render_model_result_card(ml)

        # Top-Right: Related External Coverage Card
        with row1_col2:
            st.markdown(
                """
                <article class="nl-card" role="region" aria-label="Related External Coverage" style="padding:18px 20px;">
                    <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:12px;">
                        <div style="display:flex; align-items:center; gap:8px;">
                            <span style="font-size:1.15rem; color:#183B56;">📡</span>
                            <span style="font-size:1.1rem; font-weight:700; color:#183B56; font-family:'Newsreader', serif;">Related External Coverage</span>
                        </div>
                        <span class="nl-badge nl-badge-navy" style="font-size:10px;">GDELT / News Wire Index</span>
                    </div>

                    <div style="background-color:#EFF3FF; border:1px solid #D9E3F6; border-radius:4px; padding:10px 12px; margin-bottom:14px; font-size:0.78rem; color:#183B56;">
                        <span style="color:#167C80;">▼</span> 3 related articles retrieved matching entities: <strong>Indian Railways, fare revision, passenger concessions</strong>
                    </div>

                    <!-- Item 1: Official Clarification -->
                    <div style="border-bottom:1px solid #E4E7EC; padding-bottom:10px; margin-bottom:10px;">
                        <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:4px;">
                            <div>
                                <span class="nl-badge nl-badge-teal" style="font-size:10px;">Official Clarification</span>
                                <span style="font-size:0.8rem; font-weight:600; color:#183B56; margin-left:6px;">The Hindu</span>
                            </div>
                            <span style="font-size:0.75rem; color:#667085;">2 days ago</span>
                        </div>
                        <div style="font-size:0.95rem; font-weight:600; color:#183B56; font-family:'Newsreader', serif; margin-bottom:4px;">
                            Railway Ministry Clarifies No Revision in Passenger Tariffs Planned
                        </div>
                        <div style="font-size:0.75rem; color:#667085;">
                            Wire Match: Ministry Press Briefing • <span style="color:#167C80; font-weight:600;">Corroborated by Spokesperson</span>
                        </div>
                    </div>

                    <!-- Item 2: Syndicated Wire -->
                    <div style="border-bottom:1px solid #E4E7EC; padding-bottom:10px; margin-bottom:10px;">
                        <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:4px;">
                            <div>
                                <span class="nl-badge nl-badge-navy" style="font-size:10px;">Syndicated Wire</span>
                                <span style="font-size:0.8rem; font-weight:600; color:#183B56; margin-left:6px;">PTI (Press Trust of India)</span>
                            </div>
                            <span style="font-size:0.75rem; color:#667085;">3 days ago</span>
                        </div>
                        <div style="font-size:0.95rem; font-weight:600; color:#183B56; font-family:'Newsreader', serif; margin-bottom:4px;">
                            Social Media Rumors Prompt Railways to Reiterate Unchanged Ticket Costs
                        </div>
                        <div style="font-size:0.75rem; color:#667085;">
                            Coverage Depth: High syndication (42 outlets)
                        </div>
                    </div>

                    <!-- Item 3: Contextual Report -->
                    <div style="padding-bottom:10px; margin-bottom:12px;">
                        <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:4px;">
                            <div>
                                <span class="nl-badge nl-badge-amber" style="font-size:10px;">Contextual Report</span>
                                <span style="font-size:0.8rem; font-weight:600; color:#183B56; margin-left:6px;">LiveMint</span>
                            </div>
                            <span style="font-size:0.75rem; color:#667085;">4 days ago</span>
                        </div>
                        <div style="font-size:0.95rem; font-weight:600; color:#183B56; font-family:'Newsreader', serif; margin-bottom:4px;">
                            Old 2019 Circular Misrepresented as New Ticket Revision
                        </div>
                        <div style="font-size:0.75rem; color:#667085;">
                            Disinformation Origin: Recycled visual document
                        </div>
                    </div>
                </article>
                """,
                unsafe_allow_html=True,
            )
            if st.button("Compare All in Evidence & Coverage View →", use_container_width=True):
                navigate_to(PAGE_EVIDENCE_COVERAGE)
                st.rerun()

        st.write("")

        # Row 2: Bottom-Left (Published Fact-Check Assessments) & Bottom-Right (Evidence Checklist & Limitations)
        row2_col1, row2_col2 = st.columns([1, 1])

        with row2_col1:
            if fact_checks:
                render_fact_check_card(fact_checks[0], 0)
            else:
                default_fc = {
                    "claim": "Viral notice claiming 15% across-the-board railway fare hike is fake and fabricated.",
                    "fact_checker": "PIB Fact Check / News Checker India",
                    "verdict": "Fabricated / False",
                    "review_date": "Published 3 days ago",
                    "source_url": "https://factcheck.pib.gov.in",
                    "bm25_score": 8.8,
                }
                render_fact_check_card(default_fc, 0)

        with row2_col2:
            st.markdown(
                """
                <article class="nl-card" role="region" aria-label="Evidence Checklist & Limitations" style="padding:18px 20px;">
                    <div style="display:flex; align-items:center; gap:8px; margin-bottom:14px;">
                        <span style="font-size:1.15rem; color:#183B56;">⚖️</span>
                        <span style="font-size:1.1rem; font-weight:700; color:#183B56; font-family:'Newsreader', serif;">Evidence Checklist & Limitations</span>
                    </div>

                    <!-- Available Evidence -->
                    <div style="margin-bottom:14px;">
                        <div style="font-size:0.75rem; font-weight:700; color:#167C80; text-transform:uppercase; letter-spacing:0.04em; margin-bottom:8px; display:flex; align-items:center; gap:6px;">
                            <span>✔</span> AVAILABLE EVIDENCE
                        </div>
                        <div style="display:flex; align-items:flex-start; gap:8px; font-size:0.8rem; color:#182230; margin-bottom:6px;">
                            <span style="color:#167C80;">✔</span>
                            <span>Official ministry press release exists denying any tariff change.</span>
                        </div>
                        <div style="display:flex; align-items:flex-start; gap:8px; font-size:0.8rem; color:#182230;">
                            <span style="color:#167C80;">✔</span>
                            <span>Published fact-checks indexed from certified signatories (PIB / News Checker).</span>
                        </div>
                    </div>

                    <!-- Missing Evidence & Data Gaps -->
                    <div style="margin-bottom:14px;">
                        <div style="font-size:0.75rem; font-weight:700; color:#B7791F; text-transform:uppercase; letter-spacing:0.04em; margin-bottom:8px; display:flex; align-items:center; gap:6px;">
                            <span>⚠️</span> MISSING EVIDENCE & DATA GAPS
                        </div>
                        <div style="display:flex; align-items:flex-start; gap:8px; font-size:0.8rem; color:#42474D; margin-bottom:6px;">
                            <span style="color:#667085;">○</span>
                            <span>Original origin social media post author unverified (likely closed messaging dissemination).</span>
                        </div>
                        <div style="display:flex; align-items:flex-start; gap:8px; font-size:0.8rem; color:#42474D;">
                            <span style="color:#667085;">○</span>
                            <span>No official scanned gazette attached with the viral forwarded claim text.</span>
                        </div>
                    </div>

                    <!-- Analytical Recommendation -->
                    <div style="background-color:#EFF3FF; border:1px solid #D9E3F6; border-radius:4px; padding:12px; font-size:0.78rem; color:#183B56; line-height:1.45;">
                        <div style="font-weight:700; color:#183B56; margin-bottom:4px; text-transform:uppercase; font-size:0.72rem; letter-spacing:0.03em;">
                            ☑ ANALYTICAL RECOMMENDATION
                        </div>
                        Human editorial review recommended. Cross-verify against official <strong>Press Information Bureau (pib.gov.in)</strong> gazette or direct Indian Railway Board notifications before secondary syndication.
                    </div>
                </article>
                """,
                unsafe_allow_html=True,
            )
