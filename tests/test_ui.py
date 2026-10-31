"""
Streamlit UI integration and component unit tests for NewsLens India.
"""

import os
import sqlite3
from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

from src.ui.components import (
    render_disclaimer_panel,
    render_empty_state,
    render_fact_check_card,
    render_news_card,
    render_page_header,
)
from src.ui.navigation import (
    PAGE_ANALYZE_ARTICLE,
    init_session_state,
    render_sidebar,
)
from src.ui.pages.article_analysis import render_article_analysis_page
from src.ui.pages.dashboard import render_dashboard_page
from src.ui.pages.evidence_coverage import render_evidence_coverage_page
from src.ui.pages.methodology import render_methodology_page
from src.ui.pages.news_monitor import render_news_monitor_page
from src.ui.theme import apply_theme

APP_PATH = str(Path(__file__).parent.parent / "app.py")


def _stored_article_count() -> int:
    """Read-only check for a seeded datastore (data/*.db is not committed)."""
    db_path = os.environ.get("NEWSLENS_DB_PATH", "data/newslens.db")
    if not os.path.exists(db_path):
        return 0
    try:
        conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
        try:
            return int(conn.execute("SELECT COUNT(*) FROM articles").fetchone()[0])
        finally:
            conn.close()
    except sqlite3.Error:
        return 0


SEEDED_DB = _stored_article_count() > 0
requires_seeded_db = pytest.mark.skipif(
    not SEEDED_DB, reason="no seeded article datastore (data/newslens.db is not committed)"
)


def test_ui_imports():
    """Verify all UI packages and page modules import cleanly and callables are present."""
    assert callable(apply_theme)
    assert callable(render_page_header)
    assert callable(render_disclaimer_panel)
    assert callable(render_news_card)
    assert callable(render_fact_check_card)
    assert callable(render_empty_state)
    assert callable(init_session_state)
    assert callable(render_sidebar)
    assert callable(render_dashboard_page)
    assert callable(render_news_monitor_page)
    assert callable(render_article_analysis_page)
    assert callable(render_evidence_coverage_page)
    assert callable(render_methodology_page)


def test_app_test_initial_load():
    """Test initial app run with Streamlit AppTest."""
    at = AppTest.from_file(APP_PATH, default_timeout=15)
    at.run()
    assert not at.exception
    # Ensure sidebar navigation exists
    assert len(at.sidebar.radio) > 0


def test_app_test_page_navigation():
    """Test switching across all 5 pages via AppTest."""
    at = AppTest.from_file(APP_PATH, default_timeout=15)
    at.run()
    assert not at.exception

    # Visit each page option systematically
    options = list(at.sidebar.radio[0].options)
    for opt in options:
        at.sidebar.radio[0].set_value(opt)
        at.run()
        assert not at.exception


def test_app_test_article_screening_flow():
    """Test entering text and running screening on the Analyze Article page."""
    at = AppTest.from_file(APP_PATH, default_timeout=15)
    at.run()

    # Navigate to Analyze Article
    at.sidebar.radio[0].set_value(PAGE_ANALYZE_ARTICLE).run()
    assert not at.exception

    # Set text area
    assert len(at.text_area) > 0
    at.text_area[0].set_value(
        "Railway Ministry announces passenger fare hike and schedule adjustment."
    ).run()
    assert not at.exception

    # Click Screen Text button
    screen_btn = None
    for btn in at.button:
        if "Screen Text" in btn.label or "Analyze" in btn.label:
            screen_btn = btn
            break

    if screen_btn:
        screen_btn.click().run()
        assert not at.exception


def test_app_test_url_query_param_sync():
    """Test deep linking via URL query parameters."""
    at = AppTest.from_file(APP_PATH, default_timeout=15)
    at.query_params["page"] = "monitor"
    at.query_params["q"] = "railway"
    at.run()
    assert not at.exception
    # Verify page switched to News Monitor via query param
    assert at.session_state["current_page"] == "News Monitor"
    assert at.session_state["monitor_query"] == "railway"


@requires_seeded_db
def test_app_test_news_monitor_default_displays_records():
    """Verify that News Monitor displays stored records under default 'All' filters."""
    at = AppTest.from_file(APP_PATH, default_timeout=15)
    at.run()
    at.sidebar.radio[0].set_value("News Monitor").run()
    assert not at.exception

    # Locate markdown stating records identified
    record_lines = [
        line for m in at.markdown for line in m.value.splitlines() if "records identified" in line
    ]
    assert len(record_lines) > 0, "Expected 'records identified' header in News Monitor"
    # Ensure it did not match 0 records when the datastore has stored articles
    assert (
        " 0 records identified" not in record_lines[0]
        and "<strong>0 records identified" not in record_lines[0]
    )
    # The monitor renders "X records identified" on its own line, then a
    # separate "(showing N)" summary further down; accept the header line
    # containing "records identified" with a non-zero count.
    header = record_lines[0]
    assert "records identified" in header
    assert "<strong>" in header and "</strong>" in header


def test_app_test_evidence_coverage_page():
    """Verify Evidence & Cross-Coverage page renders cleanly with live datastore data."""
    at = AppTest.from_file(APP_PATH, default_timeout=15)
    at.run()
    # Option index 3 is Evidence & Coverage (options formatted via lambda)
    evidence_opt = at.sidebar.radio[0].options[3]
    at.sidebar.radio[0].set_value(evidence_opt).run()
    assert not at.exception
    # Verify title or header is present (HTML-escaped in page header)
    headers = [
        m.value
        for m in at.markdown
        if "Evidence &amp; Coverage" in m.value or "Evidence & Coverage" in m.value
    ]
    assert len(headers) > 0


def test_app_test_methodology_page():
    """Verify Methodology & Data Sources page renders metrics and specs cleanly."""
    at = AppTest.from_file(APP_PATH, default_timeout=15)
    at.run()
    # Option index 4 is Methodology
    methodology_opt = at.sidebar.radio[0].options[4]
    at.sidebar.radio[0].set_value(methodology_opt).run()
    assert not at.exception
    markdown_content = " ".join(m.value for m in at.markdown)
    assert "Methodology" in markdown_content
    assert "10,000 Vocab Max" in markdown_content
    assert "L-BFGS" in markdown_content


# --- Regression tests for the remediation pass -----------------------------


def _monitor_app():
    at = AppTest.from_file(APP_PATH, default_timeout=15)
    at.run()
    at.sidebar.radio[0].set_value("News Monitor").run()
    assert not at.exception
    return at


def _selectbox_by_label(at, label):
    matches = [sb for sb in at.selectbox if sb.label == label]
    assert matches, f"selectbox labelled {label!r} not found"
    return matches[0]


def _header_text(at):
    for m in at.markdown:
        if "records identified" in m.value:
            return m.value
    return ""


@requires_seeded_db
def test_news_monitor_source_filter_is_applied():
    """Regression: the default 'All (GDELT + RSS)' label used to trigger GIS-style
    substring matching on 'GDELT' and filter the dashboard down to GDELT-only."""
    at = _monitor_app()
    assert "0 records identified" not in _header_text(at)

    _selectbox_by_label(at, "Ingestion Pipe").set_value("Source: Syndicated RSS").run()
    assert not at.exception
    rss_total = _header_text(at)
    assert "0 records identified" not in rss_total

    _selectbox_by_label(at, "Ingestion Pipe").set_value("Source: GDELT DOC API").run()
    assert not at.exception
    assert "0 records identified" in _header_text(at)


@requires_seeded_db
def test_news_monitor_publisher_filter_changes_results():
    at = _monitor_app()
    baseline = _header_text(at)

    publisher_select = _selectbox_by_label(at, "Outlet Domain")
    options = [opt for opt in publisher_select.options if not opt.startswith("Publisher: All")]
    assert options, "expected at least one stored publisher option"
    publisher_select.set_value(options[0]).run()
    assert not at.exception

    filtered = _header_text(at)
    assert filtered and filtered != baseline


@requires_seeded_db
def test_news_monitor_pagination_controls_exist():
    at = _monitor_app()
    labels = [b.label for b in at.button]
    assert any("Next" in lbl for lbl in labels)
    assert any("Previous" in lbl for lbl in labels)


def test_article_analysis_does_not_prefill_fabricated_article():
    at = AppTest.from_file(APP_PATH, default_timeout=15)
    at.run()
    at.sidebar.radio[0].set_value(PAGE_ANALYZE_ARTICLE).run()
    assert not at.exception
    assert at.text_area[0].value == ""

    # The example loader must stay available and clearly synthetic.
    load_buttons = [b for b in at.button if "Load Example" in b.label]
    assert load_buttons
    load_buttons[0].click().run()
    assert not at.exception
    assert at.text_area[0].value
