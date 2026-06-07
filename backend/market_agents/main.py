"""Top-level runner for MarketAtlas agents (demo)."""
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from market_agents.market_data.market_data_agent import MarketDataAgent
from market_agents.impact.impact_agent import ImpactAgent
from market_agents.recommendation.recommendation_agent import RecommendationAgent

import numpy as np


def run_demo():
    rng = np.random.default_rng(42)
    prices = np.cumsum(rng.normal(loc=0.1, scale=1.0, size=60)) + 100
    volumes = rng.integers(1000, 5000, size=60)

    market = MarketDataAgent(prices, volumes)
    snapshot = market.snapshot()

    text = (
        "CountryA launched a strike on FactoryB. "
        "CountryC faces new sanctions. "
        "Markets watch potential supply chain disruptions."
    )

    ag = ImpactAgent()
    state = {"text": text}
    state = ag.ingest(state)
    state = ag.extract(state)
    state = ag.store(state)
    state = ag.propagate(state)
    state = ag.output(state)

    rec = RecommendationAgent()
    decision = rec.decide(state, snapshot)

    out = {
        "snapshot": snapshot,
        "impact": {
            "local_severity": state.get("local_severity"),
            "composite_risk": state.get("composite_risk"),
        },
        "recommendation": decision,
    }
    return out


def main():
    r = run_demo()
    print("--- Market Snapshot ---")
    print(r["snapshot"])
    print()
    print("--- Impact ---")
    print(r["impact"])
    print()
    print("--- Recommendation ---")
    print(r["recommendation"])


if __name__ == "__main__":
    main()
