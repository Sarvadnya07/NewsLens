"""
Streamlit UI integration and component unit tests for NewsLens India.
"""

from pathlib import Path

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
