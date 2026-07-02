"""Financial data service — Alpha Vantage + yfinance.

Provides live stock quotes, fundamentals, and news via Alpha Vantage (US + global),
with yfinance as a free fallback for non-US markets. Caches results in Redis.
"""

import logging
from typing import Any, Optional

import httpx
import yfinance as yf

from app.cache import cache

logger = logging.getLogger(__name__)

ALPHA_VANTAGE_BASE = "https://www.alphavantage.co/query"
ALPHA_VANTAGE_KEY: Optional[str] = None


def _load_key():
    global ALPHA_VANTAGE_KEY
    if ALPHA_VANTAGE_KEY is not None:
        return
    import os
    ALPHA_VANTAGE_KEY = os.getenv("ALPHA_VANTAGE_API_KEY") or ""


def _is_us_ticker(ticker: str) -> bool:
    ticker = ticker.upper()
    return not any(ticker.endswith(s) for s in (".TO", ".L", ".DE", ".PA", ".AS", ".MI", ".MC", ".ST", ".CO", ".HK", ".T", ".KS", ".SS", ".SZ", ".NSE", ".BSE"))


def _cache_key(prefix: str, key: str) -> str:
    return f"finsvc:{prefix}:{key.upper()}"


async def _av_get(params: dict[str, str], ttl: int = 300) -> Optional[dict[str, Any]]:
    _load_key()
    if not ALPHA_VANTAGE_KEY:
        return None
    params["apikey"] = ALPHA_VANTAGE_KEY
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.get(ALPHA_VANTAGE_BASE, params=params)
            resp.raise_for_status()
            data = resp.json()
            if "Error Message" in data:
                logger.warning("Alpha Vantage error: %s", data["Error Message"])
                return None
            return data
    except Exception as e:
        logger.warning("Alpha Vantage request failed: %s", e)
        return None


async def get_stock_quote(ticker: str) -> Optional[dict[str, Any]]:
    cached = await cache.get(_cache_key("quote", ticker))
    if cached:
        return cached

    data = await _av_get({"function": "GLOBAL_QUOTE", "symbol": ticker}, ttl=60)
    if data and "Global Quote" in data:
        q = data["Global Quote"]
        result = {
            "symbol": q.get("01. symbol", ticker),
            "price": float(q.get("05. price", 0)),
            "change": float(q.get("09. change", 0)),
            "change_percent": q.get("10. change percent", "0%"),
            "high": float(q.get("03. high", 0)),
            "low": float(q.get("04. low", 0)),
            "volume": int(float(q.get("06. volume", 0))),
            "previous_close": float(q.get("08. previous close", 0)),
            "source": "alphavantage",
        }
        await cache.set(_cache_key("quote", ticker), result, ttl=60)
        return result

    try:
        yf_ticker = yf.Ticker(ticker)
        info = yf_ticker.info
        if info and info.get("regularMarketPrice"):
            result = {
                "symbol": ticker.upper(),
                "price": float(info.get("regularMarketPrice", 0)),
                "change": float(info.get("regularMarketChange", 0)),
                "change_percent": f"{info.get('regularMarketChangePercent', 0):.2f}%",
                "high": float(info.get("regularMarketDayHigh", 0)),
                "low": float(info.get("regularMarketDayLow", 0)),
                "volume": int(info.get("regularMarketVolume", 0)),
                "previous_close": float(info.get("regularMarketPreviousClose", 0)),
                "source": "yfinance",
            }
            await cache.set(_cache_key("quote", ticker), result, ttl=60)
            return result
    except Exception as e:
        logger.warning("yfinance quote failed for %s: %s", ticker, e)

    return None


async def get_company_profile(ticker: str) -> Optional[dict[str, Any]]:
    cached = await cache.get(_cache_key("profile", ticker))
    if cached:
        return cached

    data = await _av_get({"function": "OVERVIEW", "symbol": ticker}, ttl=86400)
    if data and data.get("Symbol"):
        result = {
            "symbol": data.get("Symbol", ticker),
            "name": data.get("Name", ""),
            "description": data.get("Description", ""),
            "sector": data.get("Sector", ""),
            "industry": data.get("Industry", ""),
            "exchange": data.get("Exchange", ""),
            "country": data.get("Country", ""),
            "market_cap": data.get("MarketCapitalization", ""),
            "pe_ratio": data.get("PERatio", ""),
            "eps": data.get("EPS", ""),
            "dividend_yield": data.get("DividendYield", ""),
            "52_week_high": data.get("52WeekHigh", ""),
            "52_week_low": data.get("52WeekLow", ""),
            "beta": data.get("Beta", ""),
            "source": "alphavantage",
        }
        await cache.set(_cache_key("profile", ticker), result, ttl=86400)
        return result

    try:
        yf_ticker = yf.Ticker(ticker)
        info = yf_ticker.info
        if info:
            result = {
                "symbol": ticker.upper(),
                "name": info.get("longName", info.get("shortName", "")),
                "description": info.get("longBusinessSummary", ""),
                "sector": info.get("sector", ""),
                "industry": info.get("industry", ""),
                "exchange": info.get("exchange", ""),
                "country": info.get("country", ""),
                "market_cap": str(info.get("marketCap", "")),
                "pe_ratio": str(info.get("trailingPE", "")),
                "eps": str(info.get("trailingEps", "")),
                "dividend_yield": str(info.get("dividendYield", "")),
                "52_week_high": str(info.get("fiftyTwoWeekHigh", "")),
                "52_week_low": str(info.get("fiftyTwoWeekLow", "")),
                "beta": str(info.get("beta", "")),
                "source": "yfinance",
            }
            await cache.set(_cache_key("profile", ticker), result, ttl=86400)
            return result
    except Exception as e:
        logger.warning("yfinance profile failed for %s: %s", ticker, e)

    return None


async def get_market_news(ticker: Optional[str] = None, limit: int = 10) -> list[dict[str, Any]]:
    cached = await cache.get(_cache_key("news", ticker or "market"))
    if cached:
        return cached[:limit]

    params: dict[str, str] = {"function": "NEWS_SENTIMENT"}
    if ticker:
        params["tickers"] = ticker
    params["limit"] = str(min(limit, 50))

    data = await _av_get(params, ttl=300)
    if data and "feed" in data:
        articles = []
        for item in data["feed"][:limit]:
            articles.append({
                "title": item.get("title", ""),
                "summary": item.get("summary", ""),
                "article_source": item.get("source", ""),
                "url": item.get("url", ""),
                "published_at": item.get("time_published", ""),
                "sentiment": item.get("overall_sentiment_score", 0),
                "sentiment_label": item.get("overall_sentiment_label", ""),
                "source": "alphavantage",
            })
        await cache.set(_cache_key("news", ticker or "market"), articles, ttl=300)
        return articles[:limit]

    return []


async def get_price_history(ticker: str, interval: str = "daily", outputsize: str = "compact") -> Optional[list[dict[str, Any]]]:
    cached = await cache.get(_cache_key("history", f"{ticker}_{interval}"))
    if cached:
        return cached

    fn = {"daily": "TIME_SERIES_DAILY", "weekly": "TIME_SERIES_WEEKLY", "monthly": "TIME_SERIES_MONTHLY"}
    func = fn.get(interval, "TIME_SERIES_DAILY")

    data = await _av_get({"function": func, "symbol": ticker, "outputsize": outputsize}, ttl=3600)
    ts_key = f"Time Series ({interval.capitalize()})" if interval != "daily" else "Time Series (Daily)"
    if data and ts_key in data:
        series = data[ts_key]
        records = []
        for date_str, vals in sorted(series.items(), reverse=True)[:100]:
            records.append({
                "date": date_str,
                "open": float(vals.get("1. open", 0)),
                "high": float(vals.get("2. high", 0)),
                "low": float(vals.get("3. low", 0)),
                "close": float(vals.get("4. close", 0)),
                "volume": int(vals.get("5. volume", 0)),
            })
        await cache.set(_cache_key("history", f"{ticker}_{interval}"), records, ttl=3600)
        return records

    try:
        yf_ticker = yf.Ticker(ticker)
        hist = yf_ticker.history(period="6mo")
        if hist is not None and not hist.empty:
            records = []
            for idx, row in hist.iterrows():
                records.append({
                    "date": idx.strftime("%Y-%m-%d"),
                    "open": round(float(row["Open"]), 2),
                    "high": round(float(row["High"]), 2),
                    "low": round(float(row["Low"]), 2),
                    "close": round(float(row["Close"]), 2),
                    "volume": int(row["Volume"]),
                })
            await cache.set(_cache_key("history", f"{ticker}_{interval}"), records, ttl=3600)
            return records
    except Exception as e:
        logger.warning("yfinance history failed for %s: %s", ticker, e)

    return None


async def search_ticker(query: str) -> list[dict[str, Any]]:
    cached = await cache.get(_cache_key("search", query))
    if cached:
        return cached

    data = await _av_get({"function": "SYMBOL_SEARCH", "keywords": query}, ttl=86400)
    if data and "bestMatches" in data:
        results = []
        for match in data["bestMatches"][:10]:
            results.append({
                "symbol": match.get("1. symbol", ""),
                "name": match.get("2. name", ""),
                "type": match.get("3. type", ""),
                "region": match.get("4. region", ""),
                "currency": match.get("8. currency", ""),
            })
        await cache.set(_cache_key("search", query), results, ttl=86400)
        return results

    return []


class FinancialDataService:
    """Class wrapper for backward compatibility with class-based callers."""

    async def get_stock_quote(self, ticker: str) -> Optional[dict[str, Any]]:
        return await get_stock_quote(ticker)

    async def get_company_profile(self, ticker: str) -> Optional[dict[str, Any]]:
        return await get_company_profile(ticker)

    async def get_market_news(self, ticker: Optional[str] = None, limit: int = 10) -> list[dict[str, Any]]:
        return await get_market_news(ticker, limit)

    async def get_price_history(self, ticker: str, interval: str = "daily", outputsize: str = "compact") -> Optional[list[dict[str, Any]]]:
        return await get_price_history(ticker, interval, outputsize)

    async def search_ticker(self, query: str) -> list[dict[str, Any]]:
        return await search_ticker(query)
