from typing import Any

import numpy as np


def calculate_volatility(prices: list[float], periods: int = 21) -> float:
    if len(prices) < periods + 1:
        return 0.0
    returns = np.diff(prices[-periods-1:]) / np.array(prices[-periods-1:-1])
    return float(np.std(returns) * np.sqrt(252) * 100)


def calculate_momentum(prices: list[float], period: int = 14) -> float:
    if len(prices) < period + 1:
        return 0.0
    return ((prices[-1] - prices[-period-1]) / prices[-period-1]) * 100


def calculate_sharpe_ratio(returns: list[float], risk_free_rate: float = 0.05) -> float:
    if len(returns) < 2:
        return 0.0
    excess = float(np.mean(returns)) - risk_free_rate / 252
    std = float(np.std(returns))
    if std == 0:
        return 0.0
    return float(np.sqrt(252) * excess / std)


def calculate_max_drawdown(prices: list[float]) -> float:
    if len(prices) < 2:
        return 0.0
    peak = prices[0]
    max_dd = 0.0
    for p in prices:
        if p > peak:
            peak = p
        dd = (peak - p) / peak * 100
        if dd > max_dd:
            max_dd = dd
    return round(max_dd, 2)


def calculate_var(prices: list[float], confidence: float = 0.95) -> float:
    if len(prices) < 10:
        return 0.0
    returns = np.diff(prices) / np.array(prices[:-1])
    var = float(np.percentile(returns, (1 - confidence) * 100))
    return round(abs(var) * 100, 2)


def calculate_sortino_ratio(returns: list[float], risk_free_rate: float = 0.05) -> float:
    if len(returns) < 2:
        return 0.0
    excess = float(np.mean(returns)) - risk_free_rate / 252
    downside = float(np.std([r for r in returns if r < 0]))
    if downside == 0:
        return 0.0
    return float(np.sqrt(252) * excess / downside)


def calculate_beta(prices: list[float], benchmark_prices: list[float]) -> float:
    min_len = min(len(prices), len(benchmark_prices))
    if min_len < 2:
        return 1.0
    p = prices[-min_len:]
    b = benchmark_prices[-min_len:]
    stock_returns = np.diff(p) / np.array(p[:-1])
    bench_returns = np.diff(b) / np.array(b[:-1])
    cov = float(np.cov(stock_returns, bench_returns)[0, 1])
    var = float(np.var(bench_returns))
    if var == 0:
        return 1.0
    return round(cov / var, 4)


def compute_risk_score(
    volatility: float,
    max_drawdown: float,
    var_95: float,
    beta: float,
    sharpe: float,
    sortino: float,
    sentiment_score: float = 0.0,
) -> tuple[float, list[dict[str, Any]]]:
    factors = []

    vol_score = min(volatility / 40 * 100, 100) if volatility <= 40 else 100
    factors.append({"name": "Volatility", "value": volatility, "weight": 0.25, "score": round(vol_score, 1), "direction": "negative"})

    dd_score = min(abs(max_drawdown) / 30 * 100, 100) if abs(max_drawdown) <= 30 else 100
    factors.append({"name": "Max Drawdown", "value": max_drawdown, "weight": 0.20, "score": round(dd_score, 1), "direction": "negative"})

    var_score = min(var_95 / 5 * 100, 100) if var_95 <= 5 else 100
    factors.append({"name": "Value at Risk (95%)", "value": var_95, "weight": 0.15, "score": round(var_score, 1), "direction": "negative"})

    beta_deviation = abs(beta - 1.0)
    beta_score = min(beta_deviation / 1.0 * 100, 100)
    factors.append({"name": "Beta", "value": beta, "weight": 0.15, "score": round(beta_score, 1), "direction": "negative"})

    sent_weight = 0.15
    if sentiment_score != 0:
        sent_score = max(0, min((1 - sentiment_score) / 2 * 100, 100))
    else:
        sent_score = 50.0
    factors.append({"name": "News Sentiment", "value": round(sentiment_score, 4), "weight": sent_weight, "score": round(sent_score, 1), "direction": "positive"})

    sharpe_score = max(0, min((2 - min(sharpe, 3)) / 3 * 100, 100))
    sharpe_weight = 0.10
    factors.append({"name": "Sharpe Ratio", "value": sharpe, "weight": sharpe_weight, "score": round(sharpe_score, 1), "direction": "positive"})

    overall = sum(f["score"] * f["weight"] for f in factors)
    overall = round(min(max(overall, 0), 100), 1)

    return overall, factors
