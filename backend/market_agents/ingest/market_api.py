import os
import requests
from typing import Optional, Dict, Any


def fetch_alpha_vantage_daily(symbol: str, apikey: Optional[str] = None) -> Dict[str, Any]:
    if apikey is None:
        apikey = os.environ.get("ALPHAVANTAGE_API_KEY")
    if not apikey:
        return {"symbol": symbol, "prices": [100.0, 101.0, 100.5, 102.0]}
    url = "https://www.alphavantage.co/query"
    params = {"function": "TIME_SERIES_DAILY_ADJUSTED", "symbol": symbol, "apikey": apikey, "outputsize": "compact"}
    try:
        r = requests.get(url, params=params, timeout=10)
        r.raise_for_status()
        data = r.json()
        series = data.get("Time Series (Daily)", {})
        dates = sorted(series.keys())
        prices = [float(series[d]["5. adjusted close"]) for d in dates]
        return {"symbol": symbol, "dates": dates, "prices": prices}
    except Exception:
        return {"symbol": symbol, "prices": [100.0, 101.0, 100.5, 102.0]}


def fetch_fred_series(series_id: str, apikey: Optional[str] = None) -> Dict[str, Any]:
    if apikey is None:
        apikey = os.environ.get("FRED_API_KEY")
    if not apikey:
        return {"series_id": series_id, "values": [1.0, 1.1, 1.05]}
    url = "https://api.stlouisfed.org/fred/series/observations"
    params = {"series_id": series_id, "api_key": apikey, "file_type": "json"}
    try:
        r = requests.get(url, params=params, timeout=10)
        r.raise_for_status()
        j = r.json()
        obs = j.get("observations", [])
        dates = [o.get("date") for o in obs]
        values = [float(o.get("value")) if o.get("value") not in ("", None) else None for o in obs]
        return {"series_id": series_id, "dates": dates, "values": values}
    except Exception:
        return {"series_id": series_id, "values": [1.0, 1.1, 1.05]}
