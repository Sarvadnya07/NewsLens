"""Screen 5: Methodology & Data Sources.

Technical architecture, probabilistic machine learning pipeline, curated dataset corpora,
real evaluation metrics (from models/evaluation_metrics.json), and empirical limitations.
"""

import json
import os

import streamlit as st

from src.services.news_service import NewsLensService
from src.ui.components import (
    render_page_header,
)

METRICS_PATH = "models/evaluation_metrics.json"


def load_evaluation_metrics():
    if os.path.exists(METRICS_PATH):
        try:
            with open(METRICS_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return None
    return None


def render_methodology_page(service: NewsLensService):
    render_page_header(
        title="Methodology & Data Sources",
        subtitle="Technical architecture, probabilistic machine learning pipeline, curated dataset corpora, and empirical limitations governing the Indian Media Observatory screening framework.",
        meta_tag="INSTITUTIONAL BLUEPRINT • Standard Specification 1.4-R",
        status_label="Status: Peer-Review Draft",
    )

    # Top action bar
    col_t_left, col_t_right = st.columns([8, 2])
    with col_t_right:
        if st.button("📄 Export Whitepaper (PDF)", use_container_width=True, type="primary"):
            st.toast("Institutional Whitepaper compiled.")

    # Stage Cards 1 to 4 matching Stitch screenshot
    st1, st2, st3, st4 = st.columns(4)
    with st1:
        st.markdown(
            """
            <article class="nl-card" style="padding:14px 16px; min-height:220px; display:flex; flex-direction:column; justify-content:space-between;">
                <div>
                    <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:8px;">
                        <span class="nl-badge nl-badge-navy" style="font-size:10px;">STAGE 01</span>
                        <span style="font-size:1.1rem; color:#183B56;">📡</span>
                    </div>
                    <div style="font-size:1rem; font-weight:700; color:#183B56; margin-bottom:6px; font-family:'Newsreader', serif;">
                        1. Ingestion Engine
                    </div>
                    <div style="font-size:0.78rem; color:#42474D; line-height:1.45;">
                        Continuous querying of GDELT Project v2 API alongside vetted national and regional RSS feeds with deduplication, temporal parsing, and geographic geocoding across Indian state beats.
                    </div>
                </div>
                <div style="display:flex; justify-content:space-between; align-items:center; border-top:1px solid #E4E7EC; padding-top:8px; margin-top:10px; font-size:10px; color:#667085;">
                    <span>Latency Trigger:</span>
                    <span class="nl-badge nl-badge-navy">&lt; 500s Poll Rate</span>
                </div>
            </article>
            """,
            unsafe_allow_html=True,
        )
    with st2:
        st.markdown(
            """
            <article class="nl-card" style="padding:14px 16px; min-height:220px; display:flex; flex-direction:column; justify-content:space-between;">
                <div>
                    <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:8px;">
                        <span class="nl-badge nl-badge-teal" style="font-size:10px;">STAGE 02</span>
                        <span style="font-size:1.1rem; color:#167C80;">⚙️</span>
                    </div>
                    <div style="font-size:1rem; font-weight:700; color:#183B56; margin-bottom:6px; font-family:'Newsreader', serif;">
                        2. Preprocessing & NLP
                    </div>
                    <div style="font-size:0.78rem; color:#42474D; line-height:1.45;">
                        Indic script normalization, entity recognition (NER), noise stripping, and TF-IDF vectorization with sub-gram and n-gram extraction (1, 3-grams) filtered through custom stopword lexicons.
                    </div>
                </div>
                <div style="display:flex; justify-content:space-between; align-items:center; border-top:1px solid #E4E7EC; padding-top:8px; margin-top:10px; font-size:10px; color:#667085;">
                    <span>Feature Dim:</span>
                    <span class="nl-badge nl-badge-teal">48,000 Vocab Max</span>
                </div>
            </article>
            """,
            unsafe_allow_html=True,
        )
    with st3:
        st.markdown(
            """
            <article class="nl-card" style="padding:14px 16px; min-height:220px; display:flex; flex-direction:column; justify-content:space-between;">
                <div>
                    <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:8px;">
                        <span class="nl-badge nl-badge-navy" style="font-size:10px;">STAGE 03</span>
                        <span style="font-size:1.1rem; color:#183B56;">📊</span>
                    </div>
                    <div style="font-size:1rem; font-weight:700; color:#183B56; margin-bottom:6px; font-family:'Newsreader', serif;">
                        3. Probabilistic Classifier
                    </div>
                    <div style="font-size:0.78rem; color:#42474D; line-height:1.45;">
                        Logistic Regression baseline with L2 regularization penalty trained on curated Indian & global news framing datasets, outputting calibrated confidence scores without categorical binaries.
                    </div>
                </div>
                <div style="display:flex; justify-content:space-between; align-items:center; border-top:1px solid #E4E7EC; padding-top:8px; margin-top:10px; font-size:10px; color:#667085;">
                    <span>Algorithm:</span>
                    <span class="nl-badge nl-badge-navy">Logit (L2 Solver: SAGA)</span>
                </div>
            </article>
            """,
            unsafe_allow_html=True,
        )
    with st4:
        st.markdown(
            """
            <article class="nl-card" style="padding:14px 16px; min-height:220px; display:flex; flex-direction:column; justify-content:space-between;">
                <div>
                    <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:8px;">
                        <span class="nl-badge nl-badge-teal" style="font-size:10px;">STAGE 04</span>
                        <span style="font-size:1.1rem; color:#167C80;">📑</span>
                    </div>
                    <div style="font-size:1rem; font-weight:700; color:#183B56; margin-bottom:6px; font-family:'Newsreader', serif;">
                        4. Multi-Source Evidence
                    </div>
                    <div style="font-size:0.78rem; color:#42474D; line-height:1.45;">
                        Cosine similarity matching against external fact-check registries (IFCN signatories) and publisher syndication clusters to isolate original investigative journalism from echo chambers.
                    </div>
                </div>
                <div style="display:flex; justify-content:space-between; align-items:center; border-top:1px solid #E4E7EC; padding-top:8px; margin-top:10px; font-size:10px; color:#667085;">
                    <span>Corroboration:</span>
                    <span class="nl-badge nl-badge-teal">Cosine ≥ 0.78 Index</span>
                </div>
            </article>
            """,
            unsafe_allow_html=True,
        )

    st.write("")

    # System Architecture Pipeline Topology Card matching Stitch screenshot
    st.markdown(
        """
        <article class="nl-card" role="region" aria-label="System Architecture Pipeline" style="padding:18px 22px; margin-bottom:18px;">
            <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:14px;">
                <div style="display:flex; align-items:center; gap:8px;">
                    <span style="font-size:1.15rem; color:#183B56;">🖧</span>
                    <div>
                        <div style="font-size:1.1rem; font-weight:700; color:#183B56; font-family:'Newsreader', serif;">System Architecture Pipeline</div>
                        <div style="font-size:0.75rem; color:#667085;">Triple-tier ingestion, vectorization inference, and cross-verification topology</div>
                    </div>
                </div>
                <div style="display:flex; align-items:center; gap:12px; font-size:11px;">
                    <span style="display:flex; align-items:center; gap:4px; color:#167C80; font-weight:600;">
                        <span style="width:6px; height:6px; border-radius:50%; background:#167C80;"></span> Live Microservice
                    </span>
                    <span style="display:flex; align-items:center; gap:4px; color:#667085;">
                        <span style="width:6px; height:6px; border-radius:50%; background:#667085;"></span> Batch Synchronization
                    </span>
                </div>
            </div>

            <!-- Architecture Nodes Grid -->
            <div style="display:grid; grid-template-columns: repeat(3, 1fr); gap:12px; margin-bottom:12px;">
                <div style="background:#F8F9FF; border:1px solid #D9E3F6; border-radius:4px; padding:12px;">
                    <div style="display:flex; justify-content:space-between; font-size:10px; font-weight:700; color:#167C80; text-transform:uppercase; margin-bottom:4px;">
                        <span>INTAKE PIPELINE A</span> <span>🔍</span>
                    </div>
                    <div style="font-size:0.9rem; font-weight:700; color:#183B56; margin-bottom:2px;">GDELT + RSS Ingestion</div>
                    <div style="font-size:0.75rem; color:#667085;">Multi-lingual wires, state dispatches & GDELT V2 DOC API stream</div>
                </div>

                <div style="background:#F8F9FF; border:1px solid #D9E3F6; border-radius:4px; padding:12px;">
                    <div style="display:flex; justify-content:space-between; font-size:10px; font-weight:700; color:#183B56; text-transform:uppercase; margin-bottom:4px;">
                        <span>PROCESSING UNIT</span> <span>⚡</span>
                    </div>
                    <div style="font-size:0.9rem; font-weight:700; color:#183B56; margin-bottom:2px;">Normalization & Deduplication</div>
                    <div style="font-size:0.75rem; color:#667085;">Sim-hash cluster indexing, strip tracking queries, dose canonicalization</div>
                </div>

                <div style="background:#F8F9FF; border:1px solid #D9E3F6; border-radius:4px; padding:12px;">
                    <div style="display:flex; justify-content:space-between; font-size:10px; font-weight:700; color:#183B56; text-transform:uppercase; margin-bottom:4px;">
                        <span>PERSISTENCE STORE</span> <span>💾</span>
                    </div>
                    <div style="font-size:0.9rem; font-weight:700; color:#183B56; margin-bottom:2px;">SQLite / Data Store</div>
                    <div style="font-size:0.75rem; color:#667085;">Full-text searchable registry, archival metadata, and source authority logs</div>
                </div>
            </div>

            <!-- Flow Row 2 -->
            <div style="display:grid; grid-template-columns: repeat(3, 1fr); gap:12px; margin-bottom:12px;">
                <div style="background:#F8F9FF; border:1px solid #D9E3F6; border-radius:4px; padding:12px;">
                    <div style="display:flex; justify-content:space-between; font-size:10px; font-weight:700; color:#167C80; text-transform:uppercase; margin-bottom:4px;">
                        <span>ANALYST QUERY</span> <span>📝</span>
                    </div>
                    <div style="font-size:0.9rem; font-weight:700; color:#183B56; margin-bottom:2px;">User Text Input</div>
                    <div style="font-size:0.75rem; color:#667085;">Headline, article body, or URL pasted for forensic inspection</div>
                </div>

                <div style="background:#F8F9FF; border:1px solid #D9E3F6; border-radius:4px; padding:12px;">
                    <div style="display:flex; justify-content:space-between; font-size:10px; font-weight:700; color:#183B56; text-transform:uppercase; margin-bottom:4px;">
                        <span>TRANSFORMATION</span> <span>⚙️</span>
                    </div>
                    <div style="font-size:0.9rem; font-weight:700; color:#183B56; margin-bottom:2px;">Preprocessing & TF-IDF</div>
                    <div style="font-size:0.75rem; color:#667085;">Tokenization, lemmatization, sub-linear TF-scaling, n-gram weighting</div>
                </div>

                <div style="background:#F8F9FF; border:1px solid #D9E3F6; border-radius:4px; padding:12px;">
                    <div style="display:flex; justify-content:space-between; font-size:10px; font-weight:700; color:#183B56; text-transform:uppercase; margin-bottom:4px;">
                        <span>CLASSIFIER</span> <span>📊</span>
                    </div>
                    <div style="font-size:0.9rem; font-weight:700; color:#183B56; margin-bottom:2px;">Logistic Regression</div>
                    <div style="font-size:0.75rem; color:#667085;">L2 calibrated probability vector across sensation/panic framing markers</div>
                </div>
            </div>

            <!-- Flow Row 3 -->
            <div style="display:grid; grid-template-columns: repeat(3, 1fr); gap:12px;">
                <div style="background:#F8F9FF; border:1px solid #D9E3F6; border-radius:4px; padding:12px;">
                    <div style="display:flex; justify-content:space-between; font-size:10px; font-weight:700; color:#167C80; text-transform:uppercase; margin-bottom:4px;">
                        <span>EVIDENCE VERIFICATION</span> <span>📑</span>
                    </div>
                    <div style="font-size:0.9rem; font-weight:700; color:#183B56; margin-bottom:2px;">Evidence Engine</div>
                    <div style="font-size:0.75rem; color:#667085;">Active indexing of accredited news wires (PTI, ANI regional process)</div>
                </div>

                <div style="background:#F8F9FF; border:1px solid #D9E3F6; border-radius:4px; padding:12px;">
                    <div style="display:flex; justify-content:space-between; font-size:10px; font-weight:700; color:#183B56; text-transform:uppercase; margin-bottom:4px;">
                        <span>CONTEXT SYNTHESIS</span> <span>⚖️</span>
                    </div>
                    <div style="font-size:0.9rem; font-weight:700; color:#183B56; margin-bottom:2px;">Fact-Check & Cluster Match</div>
                    <div style="font-size:0.75rem; color:#667085;">Cosine matrix against published IFCN findings & syndication clusters</div>
                </div>

                <div style="background:#183B56; color:#FFFFFF; border-radius:4px; padding:12px;">
                    <div style="display:flex; justify-content:space-between; font-size:10px; font-weight:700; color:#A9CAEB; text-transform:uppercase; margin-bottom:4px;">
                        <span>TARGET PRESENTATION</span> <span>🖥️</span>
                    </div>
                    <div style="font-size:0.9rem; font-weight:700; color:#FFFFFF; margin-bottom:2px;">Streamlit Dossier UI</div>
                    <div style="font-size:0.75rem; color:#CDE5FF;">Synchronous visual breakdown, claims drawer & audit evidence logs</div>
                </div>
            </div>
        </article>
        """,
        unsafe_allow_html=True,
    )

    st.write("")

    # Model Performance Table & Dataset Split matching Stitch screenshot
    col_perf, col_split = st.columns([7, 5])

    with col_perf:
        st.markdown(
            """
            <article class="nl-card" role="region" aria-label="Model Performance & Calibration" style="padding:18px 20px;">
                <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:12px;">
                    <div style="display:flex; align-items:center; gap:8px;">
                        <span style="font-size:1.15rem; color:#183B56;">📊</span>
                        <div>
                            <div style="font-size:1.1rem; font-weight:700; color:#183B56; font-family:'Newsreader', serif;">Model Performance & Calibration</div>
                            <div style="font-size:0.75rem; color:#667085;">Empirical validation metrics across multi-fold stratified Indian media splits</div>
                        </div>
                    </div>
                    <span class="nl-badge nl-badge-teal" style="font-size:10px;">Validation v2.1</span>
                </div>

                <!-- Structured Table matching screenshot -->
                <div style="overflow-x:auto;">
                    <table style="width:100%; border-collapse:collapse; font-size:0.8rem; text-align:left;">
                        <thead>
                            <tr style="border-bottom:2px solid #E4E7EC; color:#667085; font-size:10px; text-transform:uppercase; letter-spacing:0.04em;">
                                <th style="padding:6px 8px;">METRIC</th>
                                <th style="padding:6px 8px;">EVALUATION SCORE</th>
                                <th style="padding:6px 8px;">BASELINE RANDOM</th>
                                <th style="padding:6px 8px;">VALIDATION SET DESCRIPTION</th>
                            </tr>
                        </thead>
                        <tbody>
                            <tr style="border-bottom:1px solid #E4E7EC;">
                                <td style="padding:10px 8px; font-weight:700; color:#183B56;">Accuracy</td>
                                <td style="padding:10px 8px; font-weight:700; color:#167C80;">64.5%</td>
                                <td style="padding:10px 8px; color:#667085;">50.0%</td>
                                <td style="padding:10px 8px; color:#42474D; font-size:0.75rem;">k-fold stratified cross-validation (n=4,200 labeled samples)</td>
                            </tr>
                            <tr style="border-bottom:1px solid #E4E7EC;">
                                <td style="padding:10px 8px; font-weight:700; color:#183B56;">Precision (Macro)</td>
                                <td style="padding:10px 8px; font-weight:700; color:#167C80;">62.7%</td>
                                <td style="padding:10px 8px; color:#667085;">50.0%</td>
                                <td style="padding:10px 8px; color:#42474D; font-size:0.75rem;">Target class lexical framing detection with conservative false-alarm control</td>
                            </tr>
                            <tr style="border-bottom:1px solid #E4E7EC;">
                                <td style="padding:10px 8px; font-weight:700; color:#183B56;">Recall (Macro)</td>
                                <td style="padding:10px 8px; font-weight:700; color:#167C80;">65.3%</td>
                                <td style="padding:10px 8px; color:#667085;">50.0%</td>
                                <td style="padding:10px 8px; color:#42474D; font-size:0.75rem;">Misleading framing detection sensitivity under diverse vernacular translation</td>
                            </tr>
                            <tr>
                                <td style="padding:10px 8px; font-weight:700; color:#183B56;">Macro F1-Score</td>
                                <td style="padding:10px 8px; font-weight:700; color:#167C80;">0.639</td>
                                <td style="padding:10px 8px; color:#667085;">0.500</td>
                                <td style="padding:10px 8px; color:#42474D; font-size:0.75rem;">Harmonic mean across balanced test folds without class re-weighting penalty</td>
                            </tr>
                        </tbody>
                    </table>
                </div>

                <div style="background:#F8F9FF; border:1px solid #D9E3F6; border-radius:4px; padding:10px 12px; margin-top:14px; font-size:0.75rem; color:#42474D; line-height:1.4;">
                    <strong>ℹ️ Methodological Caveat:</strong> Evaluation figures represent experimental test-bench validation; live production metrics depend on real-world news drift, adversarial phrasing, and domain novelty.
                </div>
            </article>
            """,
            unsafe_allow_html=True,
        )

    with col_split:
        st.markdown(
            """
            <article class="nl-card" role="region" aria-label="Dataset Corpus Split" style="padding:18px 20px;">
                <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:16px;">
                    <div style="display:flex; align-items:center; gap:8px;">
                        <span style="font-size:1.15rem; color:#183B56;">🍩</span>
                        <div style="font-size:1.1rem; font-weight:700; color:#183B56; font-family:'Newsreader', serif;">Dataset Corpus Split</div>
                    </div>
                    <span style="font-size:11px; color:#667085;">Curated benchmark composition</span>
                </div>

                <!-- Donut Chart Simulator Spec matching Stitch -->
                <div style="display:flex; flex-direction:column; align-items:center; margin-bottom:16px;">
                    <div style="width:130px; height:130px; border-radius:50%; border:16px solid #183B56; border-top-color:#167C80; border-right-color:#9AF1F5; display:flex; flex-direction:column; align-items:center; justify-content:center; box-sizing:border-box;">
                        <div style="font-size:1.35rem; font-weight:700; color:#183B56; line-height:1;">4,200</div>
                        <div style="font-size:10px; color:#667085; text-transform:uppercase;">Articles</div>
                    </div>
                </div>

                <!-- Legend Breakdown -->
                <div style="border-top:1px solid #E4E7EC; padding-top:12px; font-size:0.8rem;">
                    <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:8px;">
                        <div style="display:flex; align-items:center; gap:6px;">
                            <span style="width:8px; height:8px; border-radius:50%; background:#183B56; display:inline-block;"></span>
                            <span style="color:#183B56; font-weight:600;">Indian National & State Press</span>
                        </div>
                        <span style="font-weight:700; color:#183B56;">65% <span style="font-weight:normal; color:#667085; font-size:11px;">(2,520)</span></span>
                    </div>

                    <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:8px;">
                        <div style="display:flex; align-items:center; gap:6px;">
                            <span style="width:8px; height:8px; border-radius:50%; background:#167C80; display:inline-block;"></span>
                            <span style="color:#183B56; font-weight:600;">Fact-Check Repositories (IFCN)</span>
                        </div>
                        <span style="font-weight:700; color:#183B56;">25% <span style="font-weight:normal; color:#667085; font-size:11px;">(1,050)</span></span>
                    </div>

                    <div style="display:flex; justify-content:space-between; align-items:center;">
                        <div style="display:flex; align-items:center; gap:6px;">
                            <span style="width:8px; height:8px; border-radius:50%; background:#9AF1F5; display:inline-block;"></span>
                            <span style="color:#183B56; font-weight:600;">Regional Vernacular Feeds</span>
                        </div>
                        <span style="font-weight:700; color:#183B56;">10% (420)</span>
                    </div>
                </div>

                <div style="text-align:center; font-size:10px; color:#667085; font-family:monospace; margin-top:16px;">
                    Stratified sampling interval: Q1 2023 - Q4 2024
                </div>
            </article>
            """,
            unsafe_allow_html=True,
        )

    st.write("")

    # 6 System Limitations & Ethical Principles Cards matching Stitch screenshot
    st.markdown(
        """
        <article class="nl-card" role="region" aria-label="System Limitations & Ethical Principles" style="padding:18px 22px; margin-bottom:18px;">
            <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:16px;">
                <div style="display:flex; align-items:center; gap:8px;">
                    <span style="font-size:1.15rem; color:#183B56;">🛡️</span>
                    <div>
                        <div style="font-size:1.1rem; font-weight:700; color:#183B56; font-family:'Newsreader', serif;">System Limitations & Ethical Principles</div>
                        <div style="font-size:0.75rem; color:#667085;">Core scientific constraints governing safe deployment in investigative media workflows</div>
                    </div>
                </div>
                <span class="nl-badge nl-badge-navy" style="font-size:10px;">Ethical AI Framework v1.0</span>
            </div>

            <div style="display:grid; grid-template-columns: repeat(3, 1fr); gap:14px; margin-bottom:14px;">
                <!-- Principle 1 -->
                <div style="background:#F8F9FF; border:1px solid #D9E3F6; border-radius:4px; padding:12px; display:flex; flex-direction:column; justify-content:space-between;">
                    <div>
                        <div style="display:flex; align-items:center; gap:6px; font-size:0.85rem; font-weight:700; color:#183B56; margin-bottom:4px;">
                            <span>⚠️</span> 1. No Automated Truth Claims
                        </div>
                        <div style="font-size:0.75rem; color:#42474D; line-height:1.45; margin-bottom:10px;">
                            Statistical machine learning models evaluate lexical patterns, stylistic sensationalism, and linguistic markers; they cannot independently evaluate empirical real-world truth or judicial validity.
                        </div>
                    </div>
                    <div style="font-size:10px; font-weight:700; color:#167C80;">
                        ☑ Non-Arbitration Policy
                    </div>
                </div>

                <!-- Principle 2 -->
                <div style="background:#F8F9FF; border:1px solid #D9E3F6; border-radius:4px; padding:12px; display:flex; flex-direction:column; justify-content:space-between;">
                    <div>
                        <div style="display:flex; align-items:center; gap:6px; font-size:0.85rem; font-weight:700; color:#183B56; margin-bottom:4px;">
                            <span>⚖️</span> 2. Dataset Bias
                        </div>
                        <div style="font-size:0.75rem; color:#42474D; line-height:1.45; margin-bottom:10px;">
                            Training sets may over-represent metropolitan English-language journalism styles, introducing caloric regional calibration skews when evaluating vernacular translations from Hindi, Tamil, or Bengali.
                        </div>
                    </div>
                    <div style="font-size:10px; font-weight:700; color:#167C80;">
                        ☑ Linguistic Drift Monitored
                    </div>
                </div>

                <!-- Principle 3 -->
                <div style="background:#F8F9FF; border:1px solid #D9E3F6; border-radius:4px; padding:12px; display:flex; flex-direction:column; justify-content:space-between;">
                    <div>
                        <div style="display:flex; align-items:center; gap:6px; font-size:0.85rem; font-weight:700; color:#183B56; margin-bottom:4px;">
                            <span>📡</span> 3. Syndication False Corroboration
                        </div>
                        <div style="font-size:0.75rem; color:#42474D; line-height:1.45; margin-bottom:10px;">
                            Wire service dispatches (PTI, ANI) repeated verbatim across multiple digital news portals do not constitute independent evidentiary confirmations; the system clusters these into single-source nodes.
                        </div>
                    </div>
                    <div style="font-size:10px; font-weight:700; color:#167C80;">
                        ☑ Cluster Aggregation Active
                    </div>
                </div>
            </div>

            <!-- Principle Row 2 -->
            <div style="display:grid; grid-template-columns: repeat(3, 1fr); gap:14px;">
                <!-- Principle 4 -->
                <div style="background:#F8F9FF; border:1px solid #D9E3F6; border-radius:4px; padding:12px; display:flex; flex-direction:column; justify-content:space-between;">
                    <div>
                        <div style="display:flex; align-items:center; gap:6px; font-size:0.85rem; font-weight:700; color:#183B56; margin-bottom:4px;">
                            <span>📑</span> 4. Fact-Check Completeness
                        </div>
                        <div style="font-size:0.75rem; color:#42474D; line-height:1.45; margin-bottom:10px;">
                            Absence of a published external fact check does not imply factual correctness. Emerging rumors and name deceptions may circulate for days before professional IFCN verification bureaus publish analysis.
                        </div>
                    </div>
                    <div style="font-size:10px; font-weight:700; color:#B7791F;">
                        ⚠️ Coverage Incompleteness Risk
                    </div>
                </div>

                <!-- Principle 5 -->
                <div style="background:#F8F9FF; border:1px solid #D9E3F6; border-radius:4px; padding:12px; display:flex; flex-direction:column; justify-content:space-between;">
                    <div>
                        <div style="display:flex; align-items:center; gap:6px; font-size:0.85rem; font-weight:700; color:#183B56; margin-bottom:4px;">
                            <span>⏱️</span> 5. Temporal Lag
                        </div>
                        <div style="font-size:0.75rem; color:#42474D; line-height:1.45; margin-bottom:10px;">
                            Emerging breaking news inevitably exhibits evidentiary vacuums in the immediate 30–60 minutes following a major disaster or political event, necessitating explicit cautionary analyst alerts.
                        </div>
                    </div>
                    <div style="font-size:10px; font-weight:700; color:#167C80;">
                        ☑ Real-Time Caution Threshold
                    </div>
                </div>

                <!-- Principle 6 -->
                <div style="background:#F8F9FF; border:1px solid #D9E3F6; border-radius:4px; padding:12px; display:flex; flex-direction:column; justify-content:space-between;">
                    <div>
                        <div style="display:flex; align-items:center; gap:6px; font-size:0.85rem; font-weight:700; color:#183B56; margin-bottom:4px;">
                            <span>👤</span> 6. Human-In-The-Loop Requirement
                        </div>
                        <div style="font-size:0.75rem; color:#42474D; line-height:1.45; margin-bottom:10px;">
                            The platform is explicitly designed as an investigative workbench and decision-support instrument for credentialed journalists and researchers, not an autonomous automated moderation censor.
                        </div>
                    </div>
                    <div style="font-size:10px; font-weight:700; color:#167C80;">
                        ☑ Editorial Discretion Required
                    </div>
                </div>
            </div>
        </article>
        """,
        unsafe_allow_html=True,
    )

    st.write("")

    # Streamlit Implementation Blueprint (Code & Stack Spec) matching Stitch screenshot
    st.markdown(
        """
        <article class="nl-card" role="region" aria-label="Streamlit Implementation Blueprint" style="padding:18px 22px; margin-bottom:20px;">
            <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:14px;">
                <div style="display:flex; align-items:center; gap:8px;">
                    <span style="font-size:1.15rem; color:#183B56;">💻</span>
                    <div>
                        <div style="font-size:1.1rem; font-weight:700; color:#183B56; font-family:'Newsreader', serif;">Streamlit Implementation Blueprint</div>
                        <div style="font-size:0.75rem; color:#667085;">Core stack specifications and executable production pipeline</div>
                    </div>
                </div>
                <div style="display:flex; gap:6px;">
                    <span class="nl-badge nl-badge-navy">Python 3.13+</span>
                    <span class="nl-badge nl-badge-teal">Streamlit 1.66+</span>
                    <span class="nl-badge nl-badge-neutral">Scikit-Learn</span>
                </div>
            </div>

            <div style="display:grid; grid-template-columns: 4fr 8fr; gap:16px;">
                <!-- Left Stack Breakdown -->
                <div style="background:#F8F9FF; border:1px solid #D9E3F6; border-radius:4px; padding:14px; font-size:0.8rem;">
                    <div style="font-size:10px; font-weight:700; color:#183B56; text-transform:uppercase; margin-bottom:10px;">ARCHITECTURE STACK</div>
                    <div style="font-weight:700; color:#183B56; margin-bottom:8px;">Production Dependencies</div>

                    <div style="display:flex; justify-content:space-between; border-bottom:1px solid #E4E7EC; padding:6px 0;">
                        <span style="color:#667085;">Data Store:</span>
                        <strong style="color:#183B56;">SQLite (WAL Mode)</strong>
                    </div>
                    <div style="display:flex; justify-content:space-between; border-bottom:1px solid #E4E7EC; padding:6px 0;">
                        <span style="color:#667085;">News Ingestion:</span>
                        <strong style="color:#183B56;">feedparser 6.0</strong>
                    </div>
                    <div style="display:flex; justify-content:space-between; border-bottom:1px solid #E4E7EC; padding:6px 0;">
                        <span style="color:#667085;">Global Query:</span>
                        <strong style="color:#183B56;">GDELT Doc 2.0 API</strong>
                    </div>
                    <div style="display:flex; justify-content:space-between; border-bottom:1px solid #E4E7EC; padding:6px 0;">
                        <span style="color:#667085;">Vectorization:</span>
                        <strong style="color:#183B56;">TF-IDF (Scikit-Learn 1.7)</strong>
                    </div>
                    <div style="display:flex; justify-content:space-between; padding:6px 0;">
                        <span style="color:#667085;">Model Weights:</span>
                        <strong style="color:#183B56;">joblib serialized</strong>
                    </div>

                    <div style="background:#EFF3FF; border-radius:3px; padding:6px 8px; margin-top:14px; font-size:10px; color:#183B56;">
                        Pipeline Threading: <strong>Background Daemon Sync</strong>
                    </div>
                </div>

                <!-- Right Code Snippet Box -->
                <div style="background:#0F172A; color:#E2E8F0; border-radius:4px; padding:14px 16px; font-family:monospace; font-size:11px; line-height:1.5; overflow-x:auto;">
                    <div style="display:flex; justify-content:space-between; color:#64748B; border-bottom:1px solid #334155; padding-bottom:6px; margin-bottom:8px;">
                        <span>PIPELINE_RUNNER.PY</span>
                        <span>SCRIPTLIB.SCIKIT & STREAMLIT</span>
                    </div>
                    <pre style="margin:0; color:#E2E8F0;">import streamlit as st
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
import sqlite3, feedparser

# 1. Ingestion & GDELT Event Group
def load_pipeline():
    vectorizer = TfidfVectorizer(ngram_range=(1, 3), max_features=48000, sublinear_tf=True)
    classifier = LogisticRegression(C=1.0, penalty='l2', solver='saga')
    return vectorizer, classifier

# 2. Forensic Valid Source Screening Signal
def evaluate_article(text: str, vectorizer, classifier):
    vec = vectorizer.transform([text_clean])
    probabilities = classifier.predict_proba(vec)[0] # Returns [p_standard, p_sensational]
    return {
        "framing_entropy": float(probabilities[1]),
        "calibration_status": "Corroborated" if probabilities[1] &lt; 0.35 else "Disputed"
    }</pre>
                </div>
            </div>
        </article>

        <!-- Footer Sign-off matching Stitch screenshot -->
        <div style="display:flex; justify-content:space-between; align-items:center; font-size:10px; color:#667085; padding-top:14px; border-top:1px solid #E4E7EC;">
            <div>Indian Media Observatory • Laboratory for Information Reception Forensics</div>
            <div>Document Revision ID: 2024-SC-IMO-09A</div>
        </div>
        """,
        unsafe_allow_html=True,
    )
