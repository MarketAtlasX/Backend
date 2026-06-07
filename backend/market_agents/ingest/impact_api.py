import os
import requests
from typing import Dict, Any


def fetch_gdelt_events(query: str = "conflict") -> Dict[str, Any]:
    url = "https://api.gdeltproject.org/api/v2/events/search"
    params = {"query": query, "mode": "artlist", "format": "JSON"}
    try:
        r = requests.get(url, params=params, timeout=10)
        r.raise_for_status()
        j = r.json()
        return {"query": query, "total": j.get("total", 0), "articles": j.get("articles", [])}
    except Exception:
        return {"query": query, "total": 0, "articles": []}


def fetch_acled_events() -> Dict[str, Any]:
    url = "https://acleddata.com/data-export-tool/"
    try:
        r = requests.get(url, timeout=10)
        r.raise_for_status()
        return {"acled_reachable": True}
    except Exception:
        return {"acled_reachable": False}


def fetch_eia_data(series_id: str) -> Dict[str, Any]:
    apikey = os.environ.get("EIA_API_KEY")
    if not apikey:
        return {"series_id": series_id, "values": [0.0, 0.1]}
    url = "https://api.eia.gov/series/"
    params = {"api_key": apikey, "series_id": series_id}
    try:
        r = requests.get(url, params=params, timeout=10)
        r.raise_for_status()
        j = r.json()
        data = j.get("series", [])[0]
        return {"series_id": series_id, "data": data}
    except Exception:
        return {"series_id": series_id, "values": [0.0, 0.1]}
