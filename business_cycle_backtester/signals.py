from __future__ import annotations

import math
from typing import Any

import pandas as pd


def _is_missing(value: Any) -> bool:
    return value is None or (isinstance(value, float) and math.isnan(value)) or pd.isna(value)


def classify_business_cycle(score: float | None, delta_3m: float | None) -> str | None:
    """Classify ABCF phase from aggregate score level and 3-month rolling delta.

    The phase map follows the workbook and whitepaper logic:
    positive score + positive delta -> Expansion
    positive score + negative delta -> Slowdown
    negative score + negative delta -> Contraction
    negative score + positive delta -> Recovery
    """
    if _is_missing(score) or _is_missing(delta_3m):
        return None
    if score >= 0 and delta_3m >= 0:
        return "Expansion"
    if score >= 0 and delta_3m < 0:
        return "Slowdown"
    if score < 0 and delta_3m < 0:
        return "Contraction"
    return "Recovery"


def classify_roro(delta_3m: float | None) -> str | None:
    if _is_missing(delta_3m):
        return None
    return "Risk-On" if delta_3m >= 0 else "Risk-Off"


def classify_pivot(previous_roro: str | None, current_roro: str | None) -> str | None:
    if not previous_roro or not current_roro or previous_roro == current_roro:
        return None
    return "Buy" if current_roro == "Risk-On" else "Sell"


def classify_macro_regime(growth_delta_3m: float | None, inflation_delta_3m: float | None) -> str | None:
    """Classify growth/inflation regime from 3-month rolling changes."""
    if _is_missing(growth_delta_3m) or _is_missing(inflation_delta_3m):
        return None
    growth_up = growth_delta_3m > 0
    inflation_up = inflation_delta_3m > 0
    if growth_up and not inflation_up:
        return "Goldilocks"
    if growth_up and inflation_up:
        return "Reflation"
    if not growth_up and inflation_up:
        return "Inflation"
    return "Deflation"


def add_business_cycle_labels(
    df: pd.DataFrame,
    score_col: str = "aggregate_score",
    delta_3m_col: str = "delta_3m",
) -> pd.DataFrame:
    out = df.copy()
    out["phase_calc"] = [
        classify_business_cycle(score, delta)
        for score, delta in zip(out[score_col], out[delta_3m_col], strict=False)
    ]
    out["roro_calc"] = [classify_roro(delta) for delta in out[delta_3m_col]]
    out["pivot_calc"] = [
        classify_pivot(prev, cur)
        for prev, cur in zip(out["roro_calc"].shift(1), out["roro_calc"], strict=False)
    ]
    return out


def add_macro_regime_labels(
    df: pd.DataFrame,
    growth_delta_3m_col: str = "growth_delta_3m",
    inflation_delta_3m_col: str = "inflation_delta_3m",
) -> pd.DataFrame:
    out = df.copy()
    out["regime_calc"] = [
        classify_macro_regime(g, i)
        for g, i in zip(out[growth_delta_3m_col], out[inflation_delta_3m_col], strict=False)
    ]
    return out
