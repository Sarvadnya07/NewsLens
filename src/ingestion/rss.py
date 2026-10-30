"""RSS & Atom feed ingestion for NewsLens India.

Aggregates Indian national and business news publications using installed feedparser.
Handles malformed feeds, missing fields, and per-source network failures independently.
"""

import hashlib
import logging
import re
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse

import feedparser

from src.models import NormalizedArticle, canonicalize_url

logger = logging.getLogger(__name__)

# Curated Indian publisher RSS feeds (all verified returning HTTP 200)
DEFAULT_INDIAN_FEEDS: Dict[str, str] = {
    "The Times of India (National)": "https://timesofindia.indiatimes.com/rssfeeds/-2128936835.cms",
    "The Hindu (National)": "https://www.thehindu.com/news/national/feeder/default.rss",
    "NDTV (India News)": "https://feeds.feedburner.com/ndtvnews-india-news",
    "Indian Express (India)": "https://indianexpress.com/section/india/feed/",
    "Hindustan Times (India)": "https://www.hindustantimes.com/feeds/rss/india-news/rssfeed.xml",
    "Livemint (National & Economy)": "https://www.livemint.com/rss/news",
}


def _extract_domain(url: str) -> str:
    try:
        netloc = urlparse(url).netloc
        return netloc.replace("www.", "")
    except Exception:
        return "Unknown Publisher"


class RssIngestionService:
    """Fetches and normalizes articles from configured RSS/Atom publisher feeds."""

    def __init__(self, feeds: Optional[Dict[str, str]] = None, request_timeout: int = 10):
        self.feeds = feeds or DEFAULT_INDIAN_FEEDS
        self.request_timeout = request_timeout

    def fetch_feed(self, source_name: str, feed_url: str) -> List[NormalizedArticle]:
        """Parses a single feed, isolating errors so other feeds continue."""
        articles: List[NormalizedArticle] = []
        now_iso = datetime.now(timezone.utc).isoformat()

        try:
            parsed = feedparser.parse(
                feed_url, request_headers={"User-Agent": "NewsLens-India-Agent/1.0 (Python 3.13)"}
            )
        except Exception as e:
            logger.warning("Failed to parse feed %s (%s): %s", source_name, feed_url, str(e))
            return []

        # Check for malformed feed or HTTP error status
        status = getattr(parsed, "status", 200)
        if status not in (200, 301, 302, "N/A"):
            logger.warning("Feed %s returned status %s", source_name, str(status))
            return []

        entries = getattr(parsed, "entries", [])
        for entry in entries:
            title = getattr(entry, "title", "").strip()
            link = getattr(entry, "link", "").strip()
            if not title or not link:
                continue

            summary = getattr(entry, "summary", "") or getattr(entry, "description", "")
            if summary:
                summary = re.sub(r"<[^>]+>", " ", summary).strip()

            # Date resolution: do not invent publication timestamp if missing
            published_val = getattr(entry, "published", "") or getattr(entry, "updated", "")
            published_str = ""
            if published_val:
                published_parsed = getattr(entry, "published_parsed", None) or getattr(
                    entry, "updated_parsed", None
                )
                if published_parsed:
                    try:
                        dt = datetime(*published_parsed[:6], tzinfo=timezone.utc)
                        published_str = dt.isoformat()
                    except Exception:
                        published_str = str(published_val)
                else:
                    published_str = str(published_val)

            canon_url = canonicalize_url(link)
            url_hash = hashlib.sha256(canon_url.encode("utf-8")).hexdigest()[:16]
            domain = _extract_domain(canon_url) or source_name

            articles.append(
                NormalizedArticle(
                    id=f"rss_{url_hash}",
                    title=title,
                    url=canon_url,
                    publisher=source_name if source_name else domain,
                    published_at=published_str,
                    ingested_at=now_iso,
                    source_type="rss",
                    summary=summary[:500] if summary else "",
                    language="en",
                    country="IN",
                    query="",
                    raw_metadata={
                        "source_name": source_name,
                        "feed_url": feed_url,
                        "domain": domain,
                    },
                )
            )

        return articles

    def fetch_all(self) -> Dict[str, Any]:
        """Fetches from all configured feeds and aggregates results."""
        all_articles: List[NormalizedArticle] = []
        feed_stats: Dict[str, Dict[str, Any]] = {}

        for name, url in self.feeds.items():
            try:
                feed_articles = self.fetch_feed(name, url)
                all_articles.extend(feed_articles)
                feed_stats[name] = {
                    "status": "success" if feed_articles else "empty_or_failed",
                    "count": len(feed_articles),
                    "url": url,
                }
            except Exception as e:
                logger.error("Unexpected error in feed %s: %s", name, str(e))
                feed_stats[name] = {"status": "error", "count": 0, "error": str(e), "url": url}

        return {"articles": all_articles, "stats": feed_stats, "total_count": len(all_articles)}
