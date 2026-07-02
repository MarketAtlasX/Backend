import logging
from datetime import datetime

from ..llm.provider import get_llm
from ..models import RiskIndex, RiskRating
from ..utils.metrics import (
    calculate_beta,
    calculate_max_drawdown,
    calculate_sharpe_ratio,
    calculate_sortino_ratio,
    calculate_var,
    calculate_volatility,
    compute_risk_score,
)

logger = logging.getLogger(__name__)

RISK_KEYWORDS = [
    "risk", "volatility", "volatile", "safe", "dangerous",
    "drawdown", "value at risk", "how risky", "risk score",
    "risk assessment", "risk analysis",
]


class RiskAgent:
    def __init__(self):
        self.llm = get_llm()
        self._financial_service = None

    @property
    def financial_service(self):
        if self._financial_service is None:
            from ...services.financial_data_service import FinancialDataService
            self._financial_service = FinancialDataService()
        return self._financial_service

    def _extract_tickers(self, query: str) -> list[str]:
        known = ["AAPL", "MSFT", "GOOGL", "GOOG", "AMZN", "META", "NVDA", "TSLA",
                 "SPY", "QQQ", "XLE", "XLF", "XLK", "IWM", "DIA", "GME", "AMC",
                 "JPM", "BAC", "GS", "V", "MA", "DIS", "NFLX", "BA", "CAT",
                 "XOM", "CVX", "COP", "OXY", "SLB", "XOM", "GE", "F", "GM",
                 "INTC", "AMD", "CRM", "ADBE", "ORCL", "IBM", "CSCO", "QCOM",
                 "T", "VZ", "WMT", "HD", "MCD", "SBUX", "NKE", "COST", "PG",
                 "JNJ", "PFE", "MRK", "ABBV", "UNH", "LLY", "ABT", "MDT",
                 "NIO", "BABA", "JD", "TSM", "SNAP", "UBER", "SQ", "PYPL",
                 "SHOP", "SPOT", "RIVN", "LCID", "PLTR", "SOFI", "HOOD",
                 "OIL", "USO", "GLD", "SLV", "TLT", "HYG", "VNQ", "XLU",
                 "XLI", "XLB", "XLV", "XLY", "XLRE", "SMH", "ITA", "JETS",
                 "GDX", "CIBR", "DBA", "KIE", "PEJ", "XRT", "IBUY",
                 "BTC", "ETH", "COIN", "MSTR"]
        tickers = []
        for word in query.upper().split():
            word = word.strip(".,;:!?$")
            if word in known:
                tickers.append(word)
        return tickers[:3] or ["SPY"]

    async def _compute_risk_index(self, ticker: str) -> RiskIndex:
        profile = await self.financial_service.get_company_profile(ticker)
        price_history = await self.financial_service.get_price_history(ticker, interval="daily", outputsize="full")
        news = await self.financial_service.get_market_news(ticker, limit=10)
        spy_history = await self.financial_service.get_price_history("SPY", interval="daily", outputsize="full")

        company_name = (profile or {}).get("name", ticker)

        if price_history and len(price_history) >= 20:
            closes = [float(r["close"]) for r in price_history]
            returns = [(closes[i] - closes[i-1]) / closes[i-1] for i in range(1, len(closes))]
        else:
            closes = []
            returns = []

        benchmark_closes = [float(r["close"]) for r in spy_history] if spy_history else []

        vol = calculate_volatility(closes) if closes else 0.0
        max_dd = calculate_max_drawdown(closes) if closes else 0.0
        var_95 = calculate_var(closes) if closes else 0.0
        beta = calculate_beta(closes, benchmark_closes) if closes and benchmark_closes else 1.0
        sharpe = calculate_sharpe_ratio(returns) if returns else 0.0
        sortino = calculate_sortino_ratio(returns) if returns else 0.0

        sent_scores = [n.get("sentiment", 0) for n in news if isinstance(n.get("sentiment"), (int, float))]
        avg_sentiment = sum(sent_scores) / len(sent_scores) if sent_scores else 0.0

        overall, factors = compute_risk_score(vol, max_dd, var_95, beta, sharpe, sortino, avg_sentiment)

        if overall < 25:
            rating = RiskRating.LOW
        elif overall < 50:
            rating = RiskRating.MODERATE
        elif overall < 75:
            rating = RiskRating.HIGH
        else:
            rating = RiskRating.VERY_HIGH

        benchmark_vol = calculate_volatility(benchmark_closes) if benchmark_closes else 0.0

        summary = self._generate_summary(ticker, overall, rating, factors, vol, benchmark_vol, beta, avg_sentiment)

        return RiskIndex(
            ticker=ticker,
            company_name=company_name,
            overall_score=overall,
            rating=rating,
            factors=[{"name": f["name"], "value": f["value"], "weight": f["weight"], "score": f["score"], "direction": f["direction"]} for f in factors],
            benchmark={"ticker": "SPY", "volatility": round(benchmark_vol, 2), "beta": 1.0},
            summary=summary,
            timestamp=datetime.utcnow().isoformat(),
        )

    def _generate_summary(self, ticker: str, score: float, rating: RiskRating,
                          factors: list[dict], vol: float, bench_vol: float,
                          beta: float, sentiment: float) -> str:
        vol_comp = "higher than" if vol > bench_vol * 1.1 else "lower than" if vol < bench_vol * 0.9 else "in line with"
        beta_desc = f"Beta of {beta:.2f} suggests {'higher' if beta > 1.1 else 'lower' if beta < 0.9 else 'in-line with'} market correlation."
        sent_desc = f"Recent news sentiment is {'positive' if sentiment > 0.1 else 'negative' if sentiment < -0.1 else 'neutral'}."
        rating_desc = {
            RiskRating.LOW: "Low risk. The stock shows strong stability with below-average volatility and solid risk-adjusted returns.",
            RiskRating.MODERATE: "Moderate risk. The stock carries typical market risk with reasonable diversification benefit.",
            RiskRating.HIGH: "High risk. Elevated volatility and/or drawdown risk. Consider position sizing carefully.",
            RiskRating.VERY_HIGH: "Very high risk. Extreme volatility and downside risk. Only suitable for aggressive investors.",
        }
        return f"{rating_desc[rating]} Volatility ({vol:.1f}%) is {vol_comp} the benchmark ({bench_vol:.1f}%). {beta_desc} {sent_desc}"

    async def process(self, query: str, context: dict = None) -> dict:
        tickers = self._extract_tickers(query)
        results = []
        for t in tickers[:3]:
            try:
                risk = await self._compute_risk_index(t)
                results.append(risk.model_dump())
            except Exception as e:
                logger.warning("RiskAgent failed for %s: %s", t, e)
                continue

        if not results:
            return {"agent": "RiskAgent", "response": "Could not compute risk index.", "risk_indices": []}

        response_lines = []
        for r in results:
            response_lines.append(
                f"### {r['company_name']} ({r['ticker']}) — Risk Rating: {r['rating']}\n"
                f"Overall Risk Score: {r['overall_score']}/100\n\n"
                f"**Risk Factors:**\n" +
                "\n".join(
                    f"- {f['name']}: {f['score']}/100 "
                    f"(raw: {f['value']}, weight: {f['weight']*100:.0f}%) "
                    f"[{'negative' if f['direction'] == 'negative' else 'positive'} impact]"
                    for f in r["factors"]
                ) +
                f"\n\n{r['summary']}"
            )

        return {
            "agent": "RiskAgent",
            "response": "\n\n".join(response_lines),
            "risk_indices": results,
        }
