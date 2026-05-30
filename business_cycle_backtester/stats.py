from __future__ import annotations

import math

import numpy as np
import pandas as pd


def annualized_geometric_return(returns: pd.Series, periods_per_year: int = 12) -> float:
    clean = pd.to_numeric(returns, errors="coerce").dropna()
    if clean.empty:
        return float("nan")
    gross = (1.0 + clean).prod()
    if gross <= 0:
        return float("nan")
    return gross ** (periods_per_year / len(clean)) - 1.0


def max_drawdown(returns: pd.Series) -> float:
    clean = pd.to_numeric(returns, errors="coerce").dropna()
    if clean.empty:
        return float("nan")
    wealth = (1.0 + clean).cumprod()
    peak = wealth.cummax()
    return float((wealth / peak - 1.0).min())


def _series_stats(returns: pd.Series, periods_per_year: int, min_obs: int) -> dict[str, float | int]:
    clean = pd.to_numeric(returns, errors="coerce").dropna()
    obs = int(clean.shape[0])
    if obs < min_obs:
        return {
            "observations": obs,
            "avg_monthly_return": float("nan"),
            "annualized_return": float("nan"),
            "annualized_volatility": float("nan"),
            "sharpe": float("nan"),
            "hit_rate": float("nan"),
            "max_drawdown": float("nan"),
        }

    avg_monthly = float(clean.mean())
    ann_return = annualized_geometric_return(clean, periods_per_year)
    ann_vol = float(clean.std(ddof=1) * math.sqrt(periods_per_year))
    sharpe = ann_return / ann_vol if ann_vol and not np.isnan(ann_vol) else float("nan")
    return {
        "observations": obs,
        "avg_monthly_return": avg_monthly,
        "annualized_return": ann_return,
        "annualized_volatility": ann_vol,
        "sharpe": sharpe,
        "hit_rate": float((clean > 0).mean()),
        "max_drawdown": max_drawdown(clean),
    }


def state_conditioned_stats(
    df: pd.DataFrame,
    state_cols: list[str],
    asset_cols: list[str],
    periods_per_year: int = 12,
    min_obs: int = 6,
) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    for state_col in state_cols:
        if state_col not in df.columns:
            continue
        state_values = df[state_col].dropna().astype(str)
        for state in sorted(state_values.unique()):
            mask = df[state_col].astype(str).eq(state)
            for asset in asset_cols:
                if asset not in df.columns:
                    continue
                stats = _series_stats(df.loc[mask, asset], periods_per_year, min_obs)
                rows.append({"state_column": state_col, "state": state, "asset": asset, **stats})
    return pd.DataFrame(rows)


def transition_matrix(states: pd.Series, normalize: bool = True) -> pd.DataFrame:
    clean = states.dropna().astype(str)
    current = clean.iloc[:-1].reset_index(drop=True)
    nxt = clean.iloc[1:].reset_index(drop=True)
    table = pd.crosstab(current, nxt)
    if normalize:
        denom = table.sum(axis=1).replace(0, np.nan)
        table = table.div(denom, axis=0)
    return table


def top_assets_by_state(stats: pd.DataFrame, metric: str = "sharpe", n: int = 5) -> pd.DataFrame:
    usable = stats.dropna(subset=[metric]).copy()
    group_cols = ["state_column", "state"]
    if "source_sheet" in usable.columns:
        group_cols = ["source_sheet", *group_cols]
    usable = usable.sort_values([*group_cols, metric], ascending=[*[True] * len(group_cols), False])
    return usable.groupby(group_cols, as_index=False, group_keys=False).head(n)
