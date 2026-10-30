"""NewsLens India — Streamlit Web Application.

Near-Real-Time Indian News Monitoring and Misinformation Screening
Using Multi-Source Evidence, BM25 Retrieval, and Machine Learning.
"""

import streamlit as st
import pandas as pd
from datetime import datetime

from src.services.news_service import NewsLensService
from src.models import NormalizedArticle

# Page configuration
st.set_page_config(
    page_title="NewsLens India — Misinformation Screening",
    page_icon="🇮🇳",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom Styling
st.markdown("""
<style>
    .metric-card {
        background-color: #f8f9fa;
        border-radius: 8px;
        padding: 16px;
        border-left: 5px solid #ff9933;
        margin-bottom: 12px;
    }
    .status-badge {
        display: inline-block;
        padding: 4px 8px;
        border-radius: 4px;
        font-size: 0.85em;
        font-weight: bold;
    }
    .badge-fake { background-color: #ffebee; color: #c62828; }
    .badge-true { background-color: #e8f5e9; color: #2e7d32; }
    .badge-warn { background-color: #fff8e1; color: #f57f17; }
</style>
""", unsafe_allow_html=True)


@st.cache_resource
def get_service():
    """Initializes service singleton with database and models."""
    return NewsLensService()

service = get_service()

# Sidebar Navigation
st.sidebar.title("🇮🇳 NewsLens India")
st.sidebar.caption("Near-Real-Time News Monitoring & Misinformation Screening")

menu_choice = st.sidebar.radio(
    "Navigation",
    [
        "1. Dashboard",
        "2. News Monitor",
        "3. Article Analysis & Screening",
        "4. Evidence & Fact-Checks",
        "5. Methodology & Limitations"
    ]
)

st.sidebar.divider()
st.sidebar.subheader("Quick Actions")
if st.sidebar.button("🔄 Refresh Indian RSS Feeds", use_container_width=True):
    with st.spinner("Fetching national & regional publisher RSS feeds..."):
        res = service.refresh_rss_feeds()
        st.sidebar.success(f"Fetched {res['total_fetched']} stories ({res['new_stored']} new stored)!")

total_stored = service.db.get_article_count()
st.sidebar.metric("Database Corpus", f"{total_stored} Articles")
st.sidebar.caption(f"Indexed Fact-Checks: {service.retriever.total_records}")


# -------------------------------------------------------------
# PAGE 1: DASHBOARD
# -------------------------------------------------------------
if menu_choice == "1. Dashboard":
    st.title("📡 Indian News Monitoring Dashboard")
    st.markdown(
        "Real-time visibility across Indian mainstream publisher feeds, GDELT document monitoring, "
        "and automated cross-publisher multi-source tracking."
    )

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Total Monitored Articles", total_stored)
    with col2:
        st.metric("Fact-Check Catalog", service.retriever.total_records)
    with col3:
        st.metric("ML Classifier Status", "Active (Joblib)" if service.ml_model.is_ready else "Offline")
    with col4:
        st.metric("Target Geography", "India (IN / English)")

    st.divider()

    # Search and Filter Bar
    s_col1, s_col2 = st.columns([3, 1])
    with s_col1:
        search_kw = st.text_input("Quick Search Filter (across titles/summaries)", placeholder="e.g., Election, Supreme Court, Economy...")
    with s_col2:
        src_filter = st.selectbox("Source Filter", ["All Sources", "rss", "gdelt", "manual"])

    selected_source = None if src_filter == "All Sources" else src_filter
    articles = service.get_recent_articles(query=search_kw, source_type=selected_source, limit=20)

    st.subheader("📰 Recent Headlines")
    if not articles:
        st.info("No articles found matching criteria. Click 'Refresh Indian RSS Feeds' in the sidebar or run a GDELT search in the News Monitor.")
    else:
        for art in articles:
            with st.container():
                st.markdown(f"#### [{art.title}]({art.url})")
                m_col1, m_col2, m_col3, m_col4 = st.columns([2, 2, 2, 2])
                with m_col1:
                    st.caption(f"🏛️ **Publisher:** {art.publisher}")
                with m_col2:
                    st.caption(f"📅 **Published:** {art.published_at[:19] if art.published_at else 'N/A'}")
                with m_col3:
                    st.caption(f"🏷️ **Source:** `{art.source_type.upper()}`")
                with m_col4:
                    if st.button("Analyze Article", key=f"dash_btn_{art.id}"):
                        st.session_state["target_analysis_text"] = art.title
                        st.session_state["target_analysis_url"] = art.url
                        st.info("Article loaded! Navigate to '3. Article Analysis & Screening' to screen.")
                if art.summary:
                    st.write(art.summary[:240] + ("..." if len(art.summary) > 240 else ""))
                st.divider()

    # Source Status Table
    st.subheader("⚙️ Ingestion Source Status & Last Refresh")
    statuses = service.get_source_statuses()
    if statuses:
        df_status = pd.DataFrame(statuses)
        st.dataframe(df_status[["source_name", "source_type", "status", "items_fetched", "last_refresh_at"]], use_container_width=True)
    else:
        st.write("No source executions recorded yet. Run an RSS refresh or GDELT query.")


# -------------------------------------------------------------
# PAGE 2: NEWS MONITOR (GDELT & RSS)
# -------------------------------------------------------------
elif menu_choice == "2. News Monitor":
    st.title("🛰️ Multi-Source News Monitor")
    st.markdown(
        "Explore live stories through the **GDELT 2.0 Doc API** and **National RSS Syndication Feeds**."
    )

    tab_rss, tab_gdelt, tab_manual = st.tabs(["🗞️ Publisher RSS Feeds", "🌐 GDELT Doc Query", "✍️ Manual Headline Submission"])

    with tab_rss:
        st.subheader("Indian Media RSS Feeds")
        st.caption("Aggregates feeds from Times of India, The Hindu, NDTV, Indian Express, and Hindustan Times.")
        if st.button("Fetch Fresh Stories Now", key="fetch_rss_tab"):
            with st.spinner("Parsing active feeds..."):
                res = service.refresh_rss_feeds()
                st.success(f"Retrieved {res['total_fetched']} stories ({res['new_stored']} new entries stored)!")

        rss_articles = service.get_recent_articles(source_type="rss", limit=25)
        if rss_articles:
            for art in rss_articles:
                st.markdown(f"**[{art.title}]({art.url})** — *{art.publisher}* ({art.published_at[:19] if art.published_at else 'Recent'})")
        else:
            st.info("No RSS articles in local cache. Click 'Fetch Fresh Stories Now'.")

    with tab_gdelt:
        st.subheader("Search GDELT 2.0 Doc API (India Focus)")
        st.markdown(
            "Queries GDELT's global document collection with automatic `sourcecountry:IN` and `sourcelang:English` filters. "
            "Includes defensive throttling to respect the GDELT 5-second rate limit."
        )
        with st.form("gdelt_form"):
            gdelt_query = st.text_input("Topic or Keyword", value="India Technology", placeholder="e.g. Chandrayaan, Renewable Energy, RBI...")
            max_rec = st.slider("Max Articles", min_value=5, max_value=50, value=15, step=5)
            submit_gdelt = st.form_submit_button("Query GDELT API")

        if submit_gdelt:
            with st.spinner(f"Querying GDELT Doc API for '{gdelt_query}'..."):
                gdelt_results = service.search_gdelt(gdelt_query, max_records=max_rec)
                if gdelt_results:
                    st.success(f"Found and stored {len(gdelt_results)} GDELT articles!")
                    for art in gdelt_results:
                        st.markdown(f"🔗 **[{art.title}]({art.url})**")
                        st.caption(f"Domain: `{art.publisher}` | Seen Date: `{art.published_at}`")
                else:
                    st.warning("GDELT returned no results or rate-limited (HTTP 429). The system throttles requests safely. Please try again shortly or check your keyword.")

    with tab_manual:
        st.subheader("Manual Article / Claim Submission")
        st.markdown("Manually inject an article headline or claim for system-wide screening, fact-check retrieval, and duplicate tracking.")
        with st.form("manual_article_form"):
            man_title = st.text_input("Article Title / Statement *", placeholder="Enter headline or claim text...")
            man_pub = st.text_input("Source / Publisher", placeholder="e.g., WhatsApp Forward, Social Post, Local Newspaper")
            man_url = st.text_input("Original URL (optional)", placeholder="https://...")
            man_summary = st.text_area("Article Snippet / Description (optional)")
            submit_man = st.form_submit_button("Save and Register Article")

        if submit_man:
            if not man_title.strip():
                st.error("Title or statement is required.")
            else:
                art = service.submit_manual_article(man_title, publisher=man_pub, url=man_url, summary=man_summary)
                st.success(f"Article registered in database with ID: `{art.id}`")
                st.session_state["target_analysis_text"] = art.title
                st.info("Set as active analysis target! Head to '3. Article Analysis & Screening'.")


# -------------------------------------------------------------
# PAGE 3: ARTICLE ANALYSIS & SCREENING
# -------------------------------------------------------------
elif menu_choice == "3. Article Analysis & Screening":
    st.title("🔬 Article Screening & Linguistic Analysis")
    st.markdown(
        "Screen news text using our reproducible, leak-free **TF-IDF + Logistic Regression** machine learning pipeline."
    )

    default_text = st.session_state.get("target_analysis_text", "Government is offering free laptops to all college students under new national education policy.")
    user_input = st.text_area("Headline or Statement to Screen", value=default_text, height=120)

    col_btn1, col_btn2 = st.columns([1, 4])
    with col_btn1:
        run_screening = st.button("🚀 Screen Text", use_container_width=True)

    if run_screening or user_input:
        if not user_input.strip():
            st.warning("Please provide headline or statement text.")
        else:
            with st.spinner("Analyzing linguistic patterns and probability..."):
                res = service.screen_article_text(user_input)

            if res.get("status") == "error":
                st.error(res.get("error"))
            elif res.get("status") in ("empty_input", "short_input"):
                st.warning(res.get("error"))
            else:
                st.divider()
                st.subheader("Model Prediction Output")

                # Visual badge
                pred_label = res["label"]
                prob_fake = res["prob_fake"]
                prob_true = res["prob_true"]
                conf = res["confidence"]

                if "Suspect" in pred_label:
                    st.error(f"⚠️ **Screening Verdict:** `{pred_label}`")
                else:
                    st.success(f"✅ **Screening Verdict:** `{pred_label}`")

                p_col1, p_col2, p_col3 = st.columns(3)
                with p_col1:
                    st.metric("Primary Confidence", f"{conf*100:.1f}%")
                with p_col2:
                    st.metric("P(Misleading / False)", f"{prob_fake*100:.1f}%")
                with p_col3:
                    st.metric("P(Credible / True)", f"{prob_true*100:.1f}%")

                st.progress(prob_fake, text=f"Linguistic Suspect Score: {prob_fake*100:.1f}%")

                # Prominent Uncertainty Warning Box
                st.warning(f"📢 **Uncertainty & Responsible AI Advisory:**\n\n{res['uncertainty_note']}")

                # Corroboration Callout
                st.info("💡 **Next Step:** An ML classifier alone is NEVER proof of factual truth. Check '4. Evidence & Fact-Checks' to inspect genuine verified claims and multi-publisher corroboration.")


# -------------------------------------------------------------
# PAGE 4: EVIDENCE, RETRIEVAL & COVERAGE
# -------------------------------------------------------------
elif menu_choice == "4. Evidence & Fact-Checks":
    st.title("🛡️ Evidence, Retrieval & Cross-Publisher Coverage")
    st.markdown(
        "Corroborate claims through **BM25 Lexical Retrieval** over verified fact-check claims and **TF-IDF Multi-Publisher Duplicate & Cluster Analysis**."
    )

    tab_fc, tab_rel, tab_clusters = st.tabs(["🔎 Fact-Check Candidate Retrieval", "📰 Related News Coverage", "🧩 Multi-Publisher Clusters"])

    with tab_fc:
        st.subheader("Rank-BM25 Fact-Check Claim Matcher")
        st.caption("Indexed authentic fact-check claims from accredited watchdogs (PIB Fact Check, BOOM Live, Alt News).")
        fc_query = st.text_input("Query / Claim Statement", value=st.session_state.get("target_analysis_text", "free laptop scheme for students"))
        
        if st.button("Search Fact-Check Index", key="fc_search_btn"):
            with st.spinner("Executing BM25Okapi retrieval..."):
                matches = service.retrieve_fact_checks(fc_query, top_k=3)
            
            if matches:
                st.success(f"Found {len(matches)} matching fact-check records!")
                for m in matches:
                    with st.container():
                        st.markdown(f"### Claim: \"{m['claim']}\"")
                        f_col1, f_col2, f_col3, f_col4 = st.columns(4)
                        with f_col1:
                            st.markdown(f"**Verdict:** `:red[{m['verdict']}]`")
                        with f_col2:
                            st.markdown(f"**Checker:** `{m['fact_checker']}`")
                        with f_col3:
                            st.markdown(f"**Date:** `{m['review_date']}`")
                        with f_col4:
                            st.markdown(f"**BM25 Score:** `{m['relevance_score']}`")
                        
                        st.write(f"**Origin / Claimant:** {m['claimant']}")
                        st.write(f"**Explanation:** {m['explanation']}")
                        st.markdown(f"🔗 [View Official Verification Record]({m['source_url']})")
                        st.divider()
            else:
                st.info("No matching fact-checks found in the local catalog. This means no accredited watchdog in our index has investigated an identical claim yet.")

    with tab_rel:
        st.subheader("Corroborating Indian News Coverage")
        st.caption("Identifies related news coverage in the monitored database using TF-IDF cosine similarity.")
        rel_query = st.text_input("Headline or Topic to Match", value=st.session_state.get("target_analysis_text", "Supreme Court hearing"))
        if st.button("Find Related Coverage", key="rel_search_btn"):
            rel_items = service.find_related_news(rel_query, top_n=5)
            if rel_items:
                st.success(f"Found {len(rel_items)} related articles in current database!")
                for item in rel_items:
                    art = item["article"]
                    sim = item["similarity"]
                    st.markdown(f"**[{art.title}]({art.url})**")
                    st.caption(f"Publisher: `{art.publisher}` | Similarity Score: `{sim:.2f}` | Source: `{art.source_type}`")
                    st.divider()
            else:
                st.info("No related articles found in current database. Try expanding your search or refreshing news feeds.")

    with tab_clusters:
        st.subheader("Cross-Publisher Story Clusters & Duplicate Detection")
        st.caption("Groups identical or closely related breaking stories reported across multiple outlets.")
        if st.button("Analyze Clusters Across Stored News", key="cluster_btn"):
            with st.spinner("Clustering headlines with cosine similarity..."):
                clusters = service.analyze_coverage_clusters()
            
            multi_clusters = [c for c in clusters if c["total_coverage_count"] > 1]
            st.metric("Total Stories Analyzed", len(clusters))
            st.metric("Multi-Publisher Breaking Clusters", len(multi_clusters))

            if multi_clusters:
                for c in multi_clusters:
                    pri = c["primary_article"]
                    st.markdown(f"#### 📌 Cluster Lead: [{pri.title}]({pri.url})")
                    st.caption(f"Covered by **{len(c['publishers'])} outlets**: {', '.join(c['publishers'])}")
                    with st.expander("View related coverage reports"):
                        for rel in c["related_articles"]:
                            r_art = rel["article"]
                            st.write(f"- [{r_art.title}]({r_art.url}) — *{r_art.publisher}* (Similarity: `{rel['similarity']}`)")
                    st.divider()
            else:
                st.info("No multi-publisher duplicate clusters detected yet. As feeds accumulate stories, cross-publisher groupings will appear here.")


# -------------------------------------------------------------
# PAGE 5: METHODOLOGY & LIMITATIONS
# -------------------------------------------------------------
elif menu_choice == "5. Methodology & Limitations":
    st.title("📚 Methodology, Data Governance & Limitations")
    st.markdown("""
### 1. Data Pipeline Architecture
NewsLens India operates on a decoupled, production-ready ingestion architecture:
- **GDELT 2.0 Ingestion:** Queries GDELT's global document database with automatic `sourcecountry:IN` and `sourcelang:English` filters. Includes strict rate throttling to comply with GDELT's 5-second inter-request limits.
- **National RSS Feeds:** Aggregates live syndicated feeds from premier Indian publishers (The Times of India, The Hindu, NDTV, Indian Express, Hindustan Times, Deccan Herald) with isolated failure recovery.
- **SQLite Persistence:** Stores normalized articles (`NormalizedArticle` schema) with parameterized queries and duplicate prevention.

---

### 2. Machine Learning Screening Pipeline
- **Dataset:** LIAR Benchmark (10,240 training statements, 2,539 held-out test statements).
- **Leakage Elimination:** Explicit string and n-gram collision check eliminates duplicate leakage between train and test splits before vectorization.
- **Feature Extraction:** Sublinear TF-IDF (unigrams + bigrams, 10,000 maximum vocabulary features) fitted exclusively on training statements.
- **Classifier:** L2-regularized Logistic Regression with balanced class weights.
- **Evaluation on Held-Out Test Set:**
  - Accuracy: `61.80%`
  - Macro F1: `0.6158`
  - Misleading Class F1: `0.5869`
- **Model Artifacts:** Modern Joblib persistence (`models/tfidf_vectorizer.joblib`, `models/classifier.joblib`). All legacy binary pickles from research have been discarded for security.

---

### 3. Fact-Check Retrieval via BM25
- **Algorithm:** Okapi BM25 ranking (`rank_bm25`).
- **Data Integrity:** Indexes authentic fact-check claims from accredited watchdogs (PIB Fact Check, BOOM Live, Alt News).
- **Zero Fabrication:** The system displays an honest "No fact-check found" state when queries do not exceed relevance thresholds.

---

### 4. Critical Limitations & Responsible AI Notice
> [!WARNING]
> 1. **Screening vs Fact-Checking:** A machine learning model identifies linguistic cues (sensationalism, emotive wording, stylistic patterns). It **cannot** determine the factual truth of breaking news.
> 2. **Context Shift:** The LIAR training benchmark contains US political statements. Indian news involves distinct local entities, policy nuances, and vernacular translations.
> 3. **Human In The Loop:** Automated flags must be reviewed alongside primary sources and accredited fact-checking organizations.
""")
