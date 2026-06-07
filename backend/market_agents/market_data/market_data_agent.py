import numpy as np
from market_agents.ingest.market_api import fetch_alpha_vantage_daily, fetch_fred_series


class MarketDataAgent:
    def __init__(self, prices, volumes=None):
        self.prices = np.array(prices, dtype=float)
        self.volumes = np.array(volumes, dtype=float) if volumes is not None else None

    def momentum(self, lookback=14):
        if len(self.prices) < lookback + 1:
            return 0.0
        prev = self.prices[-(lookback+1)]
        if prev == 0:
            return 0.0
        return float((self.prices[-1] - prev) / prev)

    def rolling_volatility(self, window=14):
        if len(self.prices) < window + 1:
            return 0.0
        returns = np.diff(self.prices) / self.prices[:-1]
        windowed = returns[-window:]
        return float(np.std(windowed, ddof=1))

    def volume_status(self, lookback=14):
        if self.volumes is None or len(self.volumes) < 2:
            return "unknown"
        avg = float(np.mean(self.volumes[-lookback:])) if len(self.volumes) >= lookback else float(np.mean(self.volumes))
        last = float(self.volumes[-1])
        if last > 1.5 * avg:
            return "surge"
        if last < 0.7 * avg:
            return "thin"
        return "normal"

    def snapshot(self):
        return {
            "momentum": self.momentum(),
            "volatility": self.rolling_volatility(),
            "volume": self.volume_status(),
        }

    def ingest_from_alpha(self, symbol: str):
        res = fetch_alpha_vantage_daily(symbol)
        return res

    def ingest_from_fred(self, series_id: str):
        res = fetch_fred_series(series_id)
        return res

    def load_from_cache(self, symbol: str):
        from pathlib import Path
        cache = Path(__file__).resolve().parent.parent / "ingest" / "cache" / f"alphavantage_{symbol}.json"
        if cache.exists():
            import json
            with cache.open("r", encoding="utf-8") as f:
                j = json.load(f)
            if "prices" in j:
                return j["prices"]
            if "dates" in j and "prices" in j:
                return j["prices"]
        return None
