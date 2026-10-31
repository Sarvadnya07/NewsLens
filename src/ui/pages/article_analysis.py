"""Screen 3: Analyze Article.

Diagnostic Workbench:
- Text submission interface with word/character counter, example claims, and input validation.
- ML Screening result using actual src/ml/predict.py pipeline with explicit LIAR benchmark disclaimer.
- Published fact-check assessments via BM25Plus retrieval (real indexed records).
- Related coverage comparison using NewsDeduplicator.
- Evidence limitations and analyst recommendations.
"""

import html

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

# Illustrative, clearly-labelled synthetic inputs for trying the workbench.
# They are demonstration strings, not scraped news and not real fact-check cases.
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
    model_ready = service.ml_model.is_ready
    status_label = "Model: LIAR Baseline Ready" if model_ready else "Model: Not Loaded"

    render_page_header(
        title="Analyze Article",
        subtitle="Screen submitted news text and examine supporting evidence using lexical pattern analysis and indexed verification registers.",
        meta_tag="DIAGNOSTIC WORKBENCH",
        status_label=status_label,
    )

    # Return pathway banner only when the session actually arrived from the monitor.
    if st.session_state.get("nav_origin") == "monitor":
        c_nav_left, c_nav_right = st.columns([8, 2])
        with c_nav_left:
            st.caption("Active Investigation Session")
        with c_nav_right:
            if st.button("← Return to Monitor", use_container_width=True):
                st.session_state["nav_origin"] = None
                navigate_to("News Monitor")
                st.rerun()

    # Text arriving from another page (or from the example/clear buttons) is
    # staged in ``pending_article_text``. A widget's value cannot be rewritten
    # after it is created in the same run, so the staged text is applied to the
    # text-area key before the widget is instantiated.
    pending_text = st.session_state.pop("pending_article_text", None)
    if pending_text is not None:
        st.session_state["article_input_area"] = pending_text
        st.session_state["analyzed_text"] = pending_text
        st.session_state.pop("current_analysis_result", None)

    example_claim = SAMPLE_CLAIMS[0][1]

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
                    <span style="color:#167C80; font-weight:600;">🔒 Escaped before rendering</span>
                </div>
                """,
                unsafe_allow_html=True,
            )
        with c_btn_load:
            if st.button(
                "📄 Load Example Claim",
                use_container_width=True,
                help="Loads a synthetic demonstration claim (not a real report).",
            ):
                st.session_state["pending_article_text"] = example_claim
                st.rerun()
        with c_btn_clear:
            if st.button("🗑️ Clear Input", use_container_width=True):
                st.session_state["pending_article_text"] = ""
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
                import time

                t0 = time.perf_counter()
                ml_result = service.screen_article_text(user_text)
                inference_ms = (time.perf_counter() - t0) * 1000

                t1 = time.perf_counter()
                fc_results = service.retrieve_fact_checks(user_text, top_k=3)
                retrieval_ms = (time.perf_counter() - t1) * 1000

                related_coverage = service.find_related_news(user_text, top_n=4)

                st.session_state["current_analysis_result"] = {
                    "ml": ml_result,
                    "fact_checks": fc_results,
                    "related": related_coverage,
                    "analyzed_query": user_text,
                    "inference_ms": inference_ms,
                    "retrieval_ms": retrieval_ms,
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
            related_items = res.get("related") or []
            if related_items:
                cards_html = []
                for rel in related_items[:3]:
                    art_obj = rel.get("article")
                    score_val = rel.get("similarity", 0.0)
                    sim_pct = int(score_val * 100)
                    title_clean = html.escape(art_obj.title if art_obj else "Related Story")
                    pub_clean = html.escape(art_obj.publisher if art_obj else "Indian Press")
                    url_clean = html.escape(art_obj.url if art_obj else "#")
                    cards_html.append(f"""
                    <div style="border-bottom:1px solid #E4E7EC; padding-bottom:10px; margin-bottom:10px;">
                        <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:4px;">
                            <div>
                                <span class="nl-badge nl-badge-teal" style="font-size:10px;">Similarity {sim_pct}%</span>
                                <span style="font-size:0.8rem; font-weight:600; color:#183B56; margin-left:6px;">{pub_clean}</span>
                            </div>
                            <a href="{url_clean}" target="_blank" style="font-size:0.75rem; color:#167C80; text-decoration:none;">View ↗</a>
                        </div>
                        <div style="font-size:0.95rem; font-weight:600; color:#183B56; font-family:'Newsreader', serif; margin-bottom:4px;">
                            {title_clean}
                        </div>
                    </div>
                    """)
                items_rendered = "".join(cards_html)
            else:
                items_rendered = '<div style="font-size:0.82rem; color:#667085; padding:12px 0;">No matching coverage clusters identified in the current stored sample.</div>'

            st.markdown(
                f"""
                <article class="nl-card" role="region" aria-label="Related External Coverage" style="padding:18px 20px;">
                    <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:12px;">
                        <div style="display:flex; align-items:center; gap:8px;">
                            <span style="font-size:1.15rem; color:#183B56;">📡</span>
                            <span style="font-size:1.1rem; font-weight:700; color:#183B56; font-family:'Newsreader', serif;">Related External Coverage</span>
                        </div>
                        <span class="nl-badge nl-badge-navy" style="font-size:10px;">TF-IDF Cosine Cluster</span>
                    </div>

                    <div style="background-color:#EFF3FF; border:1px solid #D9E3F6; border-radius:4px; padding:10px 12px; margin-bottom:14px; font-size:0.78rem; color:#183B56;">
                        <span style="color:#167C80;">▼</span> {len(related_items)} related articles retrieved from local repository matching query vocabulary.
                    </div>

                    {items_rendered}
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
                from src.ui.components import render_empty_state

                render_empty_state(
                    title="No Relevant Fact-Check Found",
                    message="The local fact-check index (8 curated cases) contains no claims matching the queried vocabulary.",
                    suggestion="Absence of an external fact check does not verify or disprove real-world claims. Check primary sources.",
                )

        with row2_col2:
            st.markdown(
                """
                <article class="nl-card" role="region" aria-label="Evidence Checklist & Limitations" style="padding:18px 20px;">
                    <div style="display:flex; align-items:center; gap:8px; margin-bottom:14px;">
                        <span style="font-size:1.15rem; color:#183B56;">⚖️</span>
                        <span style="font-size:1.1rem; font-weight:700; color:#183B56; font-family:'Newsreader', serif;">Evidence Synthesis & Limitations</span>
                    </div>

                    <!-- Evaluation Safeguards -->
                    <div style="margin-bottom:14px;">
                        <div style="font-size:0.75rem; font-weight:700; color:#167C80; text-transform:uppercase; letter-spacing:0.04em; margin-bottom:8px; display:flex; align-items:center; gap:6px;">
                            <span>✔</span> SYSTEM BOUNDARIES & PROVENANCE
                        </div>
                        <div style="display:flex; align-items:flex-start; gap:8px; font-size:0.8rem; color:#182230; margin-bottom:6px;">
                            <span style="color:#167C80;">✔</span>
                            <span>Model operates as a lexical screening filter, not an automated tribunal of truth.</span>
                        </div>
                        <div style="display:flex; align-items:flex-start; gap:8px; font-size:0.8rem; color:#182230;">
                            <span style="color:#167C80;">✔</span>
                            <span>Local fact-check retrieval is limited to 8 indexed public cases with verified source URLs.</span>
                        </div>
                    </div>

                    <!-- Known Constraints -->
                    <div style="margin-bottom:14px;">
                        <div style="font-size:0.75rem; font-weight:700; color:#B7791F; text-transform:uppercase; letter-spacing:0.04em; margin-bottom:8px; display:flex; align-items:center; gap:6px;">
                            <span>⚠️</span> METHODOLOGICAL CONSTRAINTS
                        </div>
                        <div style="display:flex; align-items:flex-start; gap:8px; font-size:0.8rem; color:#42474D; margin-bottom:6px;">
                            <span style="color:#667085;">○</span>
                            <span>Uncalibrated model scores must not be interpreted as posterior probabilities of empirical truth.</span>
                        </div>
                        <div style="display:flex; align-items:flex-start; gap:8px; font-size:0.8rem; color:#42474D;">
                            <span style="color:#667085;">○</span>
                            <span>Absence of a matching indexed fact check does not imply authenticity or veracity.</span>
                        </div>
                    </div>

                    <!-- Analytical Recommendation -->
                    <div style="background-color:#EFF3FF; border:1px solid #D9E3F6; border-radius:4px; padding:12px; font-size:0.78rem; color:#183B56; line-height:1.45;">
                        <div style="font-weight:700; color:#183B56; margin-bottom:4px; text-transform:uppercase; font-size:0.72rem; letter-spacing:0.03em;">
                            ☑ EDITORIAL DISCRETION REQUIRED
                        </div>
                        Human researcher judgment required. Trace statements to primary sources, certified publisher reporting, or statutory gazettes before reaching editorial conclusions.
                    </div>
                </article>
                """,
                unsafe_allow_html=True,
            )
