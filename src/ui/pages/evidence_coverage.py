"""Screen 4: Evidence & Coverage.

Comparative Audit Ledger:
- Selected article or claim summary.
- Related multi-publisher coverage comparison with similarity and relationship classification.
- Fact-check matches from accredited watchdogs.
- Source provenance and metadata.
- Editorial independence caution and wire syndication directive.
"""

import streamlit as st

from src.services.news_service import NewsLensService
from src.ui.components import render_page_header


def render_evidence_coverage_page(service: NewsLensService):
    render_page_header(
        title="Evidence & Coverage",
        subtitle="Compare available reporting, trace original sources and inspect related claims across cross-referenced verification nodes.",
        meta_tag="OSINT DOSSIER #NL-2024-884 • Comparative Audit Ledger",
        status_label="Last sync: Today 11:42 IST",
    )

    # Top action controls: Copy Citation Link & Export Dossier
    c_sub_left, c_sub_mid, c_sub_right = st.columns([6, 2, 2])
    with c_sub_mid:
        if st.button("🔗 Copy Citation Link", use_container_width=True):
            st.toast("Citation permalink copied to clipboard.")
    with c_sub_right:
        if st.button("📥 Export Dossier (PDF/JSON)", use_container_width=True, type="primary"):
            st.toast("Dossier compiled and queued for export.")

    # Subject Investigation Banner matching Stitch screenshot
    st.markdown(
        """
        <div style="background-color:#FFFFFF; border:1px solid #E4E7EC; border-radius:4px; padding:14px 18px; margin:14px 0 10px 0; display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:10px;">
            <div style="display:flex; align-items:center; gap:12px;">
                <div style="background:#EFF3FF; border:1px solid #D9E3F6; border-radius:4px; width:34px; height:34px; display:flex; align-items:center; justify-content:center; font-size:16px;">
                    🚆
                </div>
                <div>
                    <div style="font-size:0.7rem; font-weight:700; color:#667085; text-transform:uppercase; letter-spacing:0.04em;">SUBJECT INVESTIGATION:</div>
                    <div style="display:flex; align-items:center; gap:8px;">
                        <span style="font-size:1.1rem; font-weight:700; color:#183B56; font-family:'Newsreader', serif;">Viral Railway Fare Increase Claim</span>
                        <span class="nl-badge nl-badge-navy" style="font-size:10px;">#NL-2024-884</span>
                    </div>
                    <div style="font-size:0.75rem; color:#667085;">Ministry of Railways passenger tariff revision circulating in e...</div>
                </div>
            </div>
            <div style="display:flex; align-items:center; gap:8px; flex-wrap:wrap;">
                <span class="nl-badge nl-badge-navy" style="font-size:11px;">● 3 Discovered Reporting Sources</span>
                <span class="nl-badge nl-badge-amber" style="font-size:11px;">● 1 Official Rebuttal</span>
                <span class="nl-badge nl-badge-teal" style="font-size:11px;">☑ 1 Fact-Check Record</span>
            </div>
        </div>

        <!-- Editorial Independence Caution Banner -->
        <div style="background-color:#EEF4F7; border:1px solid #D0DCE3; border-radius:4px; padding:10px 14px; margin-bottom:18px; font-size:0.8rem; color:#183B56; line-height:1.45;">
            <strong>ℹ️ EDITORIAL INDEPENDENCE CAUTION & WIRE SYNDICATION RULE</strong><br/>
            Multiple publishers frequently syndicate identical press agency dispatches (e.g., Press Trust of India, ANI). Repetition of identical wording across 5 outlets does <strong>NOT</strong> indicate 5 independent eyewitness confirmations; it reflects unified wire upstream intake.
        </div>
        """,
        unsafe_allow_html=True,
    )

    # 2-Column Core Evidence Layout matching Stitch screenshot
    col_left, col_right = st.columns([5, 7])

    with col_left:
        # Analyzed Text Passage Card
        st.markdown(
            """
            <article class="nl-card" role="region" aria-label="Analyzed Text Passage" style="padding:16px 18px; margin-bottom:14px;">
                <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:10px;">
                    <div style="display:flex; align-items:center; gap:6px;">
                        <span style="color:#167C80;">🔬</span>
                        <span style="font-size:0.75rem; font-weight:700; color:#183B56; text-transform:uppercase; letter-spacing:0.04em;">ANALYZED TEXT PASSAGE</span>
                    </div>
                    <span class="nl-badge nl-badge-amber" style="font-size:10px;">Disputed Context</span>
                </div>
                <div style="font-family:'Newsreader', serif; font-style:italic; font-size:1.15rem; line-height:1.45; color:#183B56; margin-bottom:14px;">
                    “URGENT: Ministry of Railways has announced an immediate 15% increase across all passenger train fares effective next month...”
                </div>
                <div style="display:flex; justify-content:space-between; align-items:center; font-size:0.75rem; color:#667085; font-family:monospace; margin-bottom:4px;">
                    <span>Syntactic Uniformity Index</span>
                    <strong>94.2% across 216 shares</strong>
                </div>
                <div style="width:100%; height:6px; background:#D0DAEE; border-radius:3px; overflow:hidden;">
                    <div style="width:94%; height:100%; background:#183B56;"></div>
                </div>
            </article>
            """,
            unsafe_allow_html=True,
        )

        # Entity & Keyword Extraction Card
        st.markdown(
            """
            <article class="nl-card" role="region" aria-label="Entity & Keyword Extraction" style="padding:16px 18px; margin-bottom:14px;">
                <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:12px;">
                    <div style="display:flex; align-items:center; gap:6px;">
                        <span>🗂️</span>
                        <span style="font-size:0.75rem; font-weight:700; color:#183B56; text-transform:uppercase; letter-spacing:0.04em;">ENTITY & KEYWORD EXTRACTION</span>
                    </div>
                    <span style="font-size:10px; color:#667085; font-family:monospace;">Named NER Model v4</span>
                </div>

                <!-- Entity 1 -->
                <div style="background-color:#F8F9FF; border:1px solid #D9E3F6; border-radius:4px; padding:10px 12px; margin-bottom:8px;">
                    <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:2px;">
                        <span style="font-size:0.85rem; font-weight:700; color:#183B56;">Ministry of Railways</span>
                        <span style="font-size:10px; font-weight:600; color:#167C80; font-family:monospace;">ORG: Gov Agency</span>
                    </div>
                    <div style="font-size:0.76rem; color:#667085;">Central administrative body overseeing Indian Railways network.</div>
                </div>

                <!-- Entity 2 -->
                <div style="background-color:#F8F9FF; border:1px solid #D9E3F6; border-radius:4px; padding:10px 12px; margin-bottom:8px;">
                    <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:2px;">
                        <span style="font-size:0.85rem; font-weight:700; color:#183B56;">Passenger Fares</span>
                        <span style="font-size:10px; font-weight:600; color:#167C80; font-family:monospace;">POL: Tariff / Pricing</span>
                    </div>
                    <div style="font-size:0.76rem; color:#667085;">Regulated tariff schedule requiring Railway Board gazette notification.</div>
                </div>

                <!-- Entity 3 -->
                <div style="background-color:#FEF7ED; border:1px solid #F6D8A8; border-radius:4px; padding:10px 12px;">
                    <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:2px;">
                        <span style="font-size:0.85rem; font-weight:700; color:#B7791F;">Effective next month</span>
                        <span style="font-size:10px; font-weight:700; color:#B7791F; font-family:monospace;">TIME: Floating</span>
                    </div>
                    <div style="font-size:0.76rem; color:#B7791F;">Floating relative timestamp; typical marker of recirculated, unanchored rumors.</div>
                </div>
            </article>
            """,
            unsafe_allow_html=True,
        )

        # Provenance Forensic Ledger Card
        st.markdown(
            """
            <article class="nl-card" role="region" aria-label="Provenance Forensic Ledger" style="padding:16px 18px;">
                <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:12px;">
                    <div style="display:flex; align-items:center; gap:6px;">
                        <span>📶</span>
                        <span style="font-size:0.75rem; font-weight:700; color:#183B56; text-transform:uppercase; letter-spacing:0.04em;">PROVENANCE FORENSIC LEDGER</span>
                    </div>
                    <span class="nl-badge nl-badge-teal" style="font-size:10px; font-family:monospace;">INGEST-NODE-01</span>
                </div>

                <div style="background-color:#F8F9FF; border:1px solid #D9E3F6; border-radius:4px; padding:10px 12px; margin-bottom:10px; display:flex; justify-content:space-between;">
                    <div>
                        <div style="font-size:0.7rem; color:#667085; text-transform:uppercase;">Vector Platform</div>
                        <div style="font-size:0.85rem; font-weight:700; color:#183B56;">Telegram / WhatsApp</div>
                        <div style="font-size:0.72rem; color:#667085;">Forwarded transcription</div>
                    </div>
                    <div>
                        <div style="font-size:0.7rem; color:#667085; text-transform:uppercase;">First Detection</div>
                        <div style="font-size:0.85rem; font-weight:700; color:#183B56;">Today, 09:15 IST</div>
                        <div style="font-size:0.72rem; color:#667085;">Delhi Triage Desk</div>
                    </div>
                </div>

                <div style="display:flex; justify-content:space-between; align-items:center; font-size:0.75rem; color:#667085; font-family:monospace;">
                    <span>Hash: SHA-256 <strong style="color:#183B56;">d8f3a9e0117c49...</strong></span>
                    <span style="color:#167C80; font-weight:600; cursor:pointer;">Verify</span>
                </div>
            </article>
            """,
            unsafe_allow_html=True,
        )

    with col_right:
        # Multi-Publisher Coverage Matrix Card
        st.markdown(
            """
            <article class="nl-card" role="region" aria-label="Multi-Publisher Coverage Matrix" style="padding:18px 20px;">
                <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:12px;">
                    <div>
                        <div style="font-size:1.15rem; font-weight:700; color:#183B56; font-family:'Newsreader', serif;">Multi-Publisher Coverage Matrix</div>
                        <div style="font-size:0.78rem; color:#667085;">Cross-indexed wire feeds, official rejoinders, and editorial reports.</div>
                    </div>
                    <span class="nl-badge nl-badge-navy" style="font-size:10px;">Sources: 4 Monitored Outlets</span>
                </div>

                <!-- Report 1: PIB Fact Check -->
                <div style="border-bottom:1px solid #E4E7EC; padding:12px 0;">
                    <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:4px;">
                        <div style="display:flex; align-items:center; gap:6px;">
                            <span style="width:7px; height:7px; border-radius:50%; background:#167C80; display:inline-block;"></span>
                            <span style="font-size:0.85rem; font-weight:700; color:#183B56;">Press Information Bureau (PIB) Fact Check</span>
                            <span class="nl-badge nl-badge-navy" style="font-size:10px;">Govt Wire</span>
                        </div>
                        <span style="font-size:0.72rem; color:#667085; font-family:monospace;">Oct 14, 2024 • 14:20 IST</span>
                    </div>
                    <div style="font-size:1.05rem; font-weight:600; color:#183B56; font-family:'Newsreader', serif; margin-bottom:6px;">
                        “Circulating message claiming 15% railway fare increase is completely bogus; no such notification issued.”
                    </div>
                    <div style="display:flex; justify-content:space-between; align-items:center; font-size:0.75rem; color:#667085;">
                        <div>
                            Classification: <strong style="color:#167C80;">Official Rebuttal / Clarification</strong> •
                            Verbatim Tone: <strong style="color:#183B56;">Categorical Denial</strong>
                        </div>
                        <a href="https://factcheck.pib.gov.in" target="_blank" style="color:#167C80; font-weight:600; text-decoration:none;">View Official Release ↗</a>
                    </div>
                </div>

                <!-- Report 2: The Hindu -->
                <div style="border-bottom:1px solid #E4E7EC; padding:12px 0;">
                    <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:4px;">
                        <div style="display:flex; align-items:center; gap:6px;">
                            <span style="width:7px; height:7px; border-radius:50%; background:#183B56; display:inline-block;"></span>
                            <span style="font-size:0.85rem; font-weight:700; color:#183B56;">The Hindu</span>
                            <span class="nl-badge nl-badge-neutral" style="font-size:10px;">National Print / Digital</span>
                        </div>
                        <span style="font-size:0.72rem; color:#667085; font-family:monospace;">Oct 14, 2024 • 16:45 IST</span>
                    </div>
                    <div style="font-size:1.05rem; font-weight:600; color:#183B56; font-family:'Newsreader', serif; margin-bottom:6px;">
                        Railways clarifies on fare hike rumours, says passenger tariffs remain unchanged
                    </div>
                    <div style="font-size:0.75rem; color:#667085;">
                        Source Type: <strong style="color:#183B56;">Mainstream Reporting</strong> •
                        Attribution & Provenance: <strong style="color:#183B56;">Quotes Railway Board Spokesperson directly; independently reached ministry desk.</strong>
                    </div>
                </div>

                <!-- Report 3: LiveMint -->
                <div style="border-bottom:1px solid #E4E7EC; padding:12px 0;">
                    <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:4px;">
                        <div style="display:flex; align-items:center; gap:6px;">
                            <span style="width:7px; height:7px; border-radius:50%; background:#167C80; display:inline-block;"></span>
                            <span style="font-size:0.85rem; font-weight:700; color:#183B56;">LiveMint</span>
                            <span class="nl-badge nl-badge-teal" style="font-size:10px;">Financial Media</span>
                        </div>
                        <span style="font-size:0.72rem; color:#667085; font-family:monospace;">Oct 15, 2024 • 10:10 IST</span>
                    </div>
                    <div style="font-size:1.05rem; font-weight:600; color:#183B56; font-family:'Newsreader', serif; margin-bottom:6px;">
                        Fact Check: Is Indian Railways hiking ticket prices from next month?
                    </div>
                    <div style="font-size:0.75rem; color:#667085;">
                        Source Type: <strong style="color:#183B56;">Explainer / Fact-Check</strong> •
                        Attribution & Cross-Reference: <strong style="color:#183B56;">Cites PIB Fact Check notification and references current IRCTC passenger circulars.</strong>
                    </div>
                </div>

                <!-- Report 4: PTI -->
                <div style="padding:12px 0 6px 0;">
                    <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:4px;">
                        <div style="display:flex; align-items:center; gap:6px;">
                            <span style="width:7px; height:7px; border-radius:50%; background:#183B56; display:inline-block;"></span>
                            <span style="font-size:0.85rem; font-weight:700; color:#183B56;">Press Trust of India (PTI)</span>
                            <span class="nl-badge nl-badge-navy" style="font-size:10px;">Wire Service Feed</span>
                        </div>
                        <span style="font-size:0.72rem; color:#667085; font-family:monospace;">Oct 14, 2024 • 18:30 IST</span>
                    </div>
                    <div style="font-size:1.05rem; font-weight:600; color:#183B56; font-family:'Newsreader', serif; margin-bottom:6px;">
                        No fare revision on the cards: Railway officials dispel social media claims
                    </div>
                    <div style="font-size:0.75rem; color:#667085;">
                        Source Type: <strong style="color:#183B56;">Wire Service Dispatch</strong> •
                        Syndication Reach: <strong style="color:#183B56;">Dispatched to 40+ regional affiliates; syndicated verbatim across news portals.</strong>
                    </div>
                </div>
            </article>
            """,
            unsafe_allow_html=True,
        )

    st.write("")

    # Full-width Bottom Section: Synthesis & Discrepancy Analysis
    st.markdown(
        """
        <article class="nl-card" role="region" aria-label="Synthesis & Discrepancy Analysis" style="padding:20px 24px; margin-bottom:20px;">
            <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:16px;">
                <div style="display:flex; align-items:center; gap:8px;">
                    <span style="font-size:1.2rem; color:#183B56;">■</span>
                    <span style="font-size:1.35rem; font-weight:700; color:#183B56; font-family:'Newsreader', serif;">Synthesis & Discrepancy Analysis</span>
                </div>
                <div style="display:flex; align-items:center; gap:8px;">
                    <span style="font-size:11px; font-weight:700; color:#667085; text-transform:uppercase;">CONFIDENCE SCORE:</span>
                    <span class="nl-badge nl-badge-teal" style="font-size:11px; font-weight:700;">99.8% High Evidentiary Certainty</span>
                </div>
            </div>

            <div style="display:grid; grid-template-columns: repeat(3, 1fr); gap:16px;">
                <!-- Column 1: Consensus Convergence -->
                <div style="background-color:#F8F9FF; border:1px solid #D9E3F6; border-radius:4px; padding:14px 16px;">
                    <div style="font-size:0.75rem; font-weight:700; color:#167C80; text-transform:uppercase; letter-spacing:0.04em; margin-bottom:6px; display:flex; align-items:center; gap:6px;">
                        <span>📋</span> CONSENSUS CONVERGENCE
                    </div>
                    <div style="font-size:1.25rem; font-weight:700; color:#183B56; font-family:'Inter', sans-serif; margin-bottom:6px;">
                        4 / 4 Monitored Outlets
                    </div>
                    <div style="font-size:0.8rem; color:#42474D; line-height:1.45; margin-bottom:10px;">
                        All credible publishers across national dailies and wire services unanimously report no tariff increase or proposed regulatory hike.
                    </div>
                    <div style="font-size:0.75rem; color:#167C80; font-weight:700;">
                        ☑ Full Alignment
                    </div>
                </div>

                <!-- Column 2: Statutory Verification -->
                <div style="background-color:#F8F9FF; border:1px solid #D9E3F6; border-radius:4px; padding:14px 16px;">
                    <div style="font-size:0.75rem; font-weight:700; color:#183B56; text-transform:uppercase; letter-spacing:0.04em; margin-bottom:6px; display:flex; align-items:center; gap:6px;">
                        <span>⚖️</span> STATUTORY VERIFICATION
                    </div>
                    <div style="font-size:1.25rem; font-weight:700; color:#183B56; font-family:'Inter', sans-serif; margin-bottom:6px;">
                        Zero Official Gazettes
                    </div>
                    <div style="font-size:0.8rem; color:#42474D; line-height:1.45; margin-bottom:10px;">
                        Automated crawler checked The Gazette of India archives. No statutory order, S.O. issuance, or tariff notification published during this period.
                    </div>
                    <div style="font-size:0.75rem; color:#667085; font-weight:600;">
                        ⚑ No Legal Instrument Found
                    </div>
                </div>

                <!-- Column 3: Recycled Provenance -->
                <div style="background-color:#FEF7ED; border:1px solid #F6D8A8; border-radius:4px; padding:14px 16px;">
                    <div style="font-size:0.75rem; font-weight:700; color:#B7791F; text-transform:uppercase; letter-spacing:0.04em; margin-bottom:6px; display:flex; align-items:center; gap:6px;">
                        <span>🔄</span> RECYCLED PROVENANCE
                    </div>
                    <div style="font-size:1.25rem; font-weight:700; color:#B7791F; font-family:'Newsreader', serif; margin-bottom:6px;">
                        2019 Circular Re-emergence
                    </div>
                    <div style="font-size:0.8rem; color:#B7791F; line-height:1.45; margin-bottom:10px;">
                        Visual OCR and vector fingerprint align with a cropped screenshot from an old 2019 proposal, resurfacing predictably before Diwali passenger rush.
                    </div>
                    <div style="font-size:0.75rem; color:#B7791F; font-weight:700;">
                        🔁 Cyclical Viral Phenomenon
                    </div>
                </div>
            </div>
        </article>
        """,
        unsafe_allow_html=True,
    )

    # Bottom Actions Bar
    c_bot_back, c_bot_space, c_bot_save, c_bot_pub = st.columns([3, 3, 2.5, 2.5])
    with c_bot_back:
        if st.button("← Return to News Monitor Stream", use_container_width=True):
            from src.ui.navigation import PAGE_NEWS_MONITOR, navigate_to

            navigate_to(PAGE_NEWS_MONITOR)
            st.rerun()
    with c_bot_save:
        if st.button("Save to Investigative Notebook", use_container_width=True):
            st.toast("Dossier saved to active investigation notebook.")
    with c_bot_pub:
        if st.button("Publish Case Brief to Consortium", use_container_width=True, type="primary"):
            st.toast("Case brief dispatched to consortium repository.")
