"""Unified data ingestion for geopolitical intelligence."""

import logging
import os
from datetime import datetime

import requests

from app.geopolitical.models import NewsArticle

logger = logging.getLogger(__name__)

GNEWS_KEY = os.getenv("GNEWS_KEY", os.getenv("NEWSAPI_KEY"))
GNEWS_URL = os.getenv("GNEWS_URL", "https://gnews.io/api/v4/search")
GDELT_URL = os.getenv("GDELT_BASE_URL", "https://api.gdeltproject.org/api/v2/doc/doc")
ACLED_URL = os.getenv("ACLED_URL", "https://api.acleddata.com/acled/read")
ACLED_EMAIL = os.getenv("ACLED_EMAIL")
ACLED_KEY = os.getenv("ACLED_KEY")
REQUEST_TIMEOUT = int(os.getenv("REQUEST_TIMEOUT", "30"))
MAX_ARTICLES = int(os.getenv("MAX_ARTICLES_PER_SOURCE", "20"))


def fetch_gnews(query: str) -> list[NewsArticle]:
    if not GNEWS_KEY:
        logger.warning("GNEWS_KEY not set — skipping gnews")
        return []
    try:
        resp = requests.get(
            GNEWS_URL,
            params={"q": query, "lang": "en", "max": MAX_ARTICLES, "apikey": GNEWS_KEY},
            timeout=REQUEST_TIMEOUT,
        )
        resp.raise_for_status()
        data = resp.json()
        articles = data.get("articles", [])
        result = []
        for a in articles:
            pub = None
            if a.get("publishedAt"):
                try:
                    pub = datetime.fromisoformat(a["publishedAt"].replace("Z", "+00:00"))
                except Exception:
                    pass
            result.append(NewsArticle(
                title=a.get("title", ""),
                content=a.get("description", "") or a.get("content", ""),
                source="gnews",
                url=a.get("url"),
                published_at=pub,
            ))
        logger.info(f"gnews: fetched {len(result)} articles for '{query}'")
        return result
    except Exception as e:
        logger.warning(f"gnews fetch failed: {e}")
        return []


def fetch_gdelt(query: str) -> list[NewsArticle]:
    try:
        resp = requests.get(
            GDELT_URL,
            params={
                "query": f"{query} (export OR import OR sanctions OR trade OR government)",
                "mode": "artlist",
                "maxrecords": MAX_ARTICLES,
                "format": "json",
            },
            timeout=REQUEST_TIMEOUT,
        )
        resp.raise_for_status()
        data = resp.json()
        articles = data.get("articles", []) if isinstance(data, dict) else []
        result = []
        for a in articles:
            pub = None
            if a.get("seendate"):
                try:
                    pub = datetime.strptime(str(a["seendate"]), "%Y%m%dT%H%M%S")
                except Exception:
                    pass
            result.append(NewsArticle(
                title=a.get("title", ""),
                content=a.get("content", "") or a.get("summary", ""),
                source="gdelt",
                url=a.get("url"),
                published_at=pub,
            ))
        logger.info(f"gdelt: fetched {len(result)} articles for '{query}'")
        return result
    except Exception as e:
        logger.warning(f"gdelt fetch failed: {e}")
        return []


def fetch_acled(query: str) -> list[NewsArticle]:
    if not ACLED_EMAIL or not ACLED_KEY:
        logger.warning("ACLED_EMAIL/ACLED_KEY not set — skipping acled")
        return []
    try:
        resp = requests.get(
            ACLED_URL,
            params={
                "email": ACLED_EMAIL,
                "key": ACLED_KEY,
                "country": query,
                "limit": MAX_ARTICLES,
            },
            timeout=REQUEST_TIMEOUT,
        )
        resp.raise_for_status()
        data = resp.json()
        rows = data.get("data", []) if isinstance(data, dict) else []
        result = []
        for r in rows:
            result.append(NewsArticle(
                title=r.get("event_type", "ACLED Event"),
                content=f"{r.get('actor1', '')} — {r.get('event_type', '')} in {r.get('country', '')}. {r.get('notes', '')}",
                source="acled",
                url=None,
            ))
        logger.info(f"acled: fetched {len(result)} events for '{query}'")
        return result
    except Exception as e:
        logger.warning(f"acled fetch failed: {e}")
        return []


def fetch_news(query: str) -> list[NewsArticle]:
    seen_urls: set[str] = set()
    all_articles: list[NewsArticle] = []

    for fetcher in [fetch_gnews, fetch_gdelt, fetch_acled]:
        try:
            articles = fetcher(query)
            for a in articles:
                dedup_key = a.url or a.title
                if dedup_key and dedup_key not in seen_urls:
                    seen_urls.add(dedup_key)
                    all_articles.append(a)
        except Exception as e:
            logger.warning(f"Fetcher {fetcher.__name__} failed: {e}")

    logger.info(f"fetch_news: {len(all_articles)} unique articles for '{query}'")
    return all_articles
