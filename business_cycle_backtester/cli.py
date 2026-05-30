from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

from .io import (
    DEFAULT_BCF_WORKBOOK,
    DEFAULT_INDEX_WORKBOOK,
    DEFAULT_REGIME_WORKBOOK,
    build_asset_class_returns,
    load_business_cycle_model,
    load_index_level_returns,
    load_macro_regime,
)
from .report import write_dashboard, write_index_dashboard, write_summary
from .stats import state_conditioned_stats, top_assets_by_state, transition_matrix


def _safe_name(name: str) -> str:
    return (
        name.strip()
        .replace("+", "plus")
        .replace(" ", "_")
        .replace("(", "")
        .replace(")", "")
        .replace("-", "_")
        .lower()
    )


def _attach_asset_class(stats: pd.DataFrame, asset_classes: dict[str, str] | None) -> pd.DataFrame:
    out = stats.copy()
    out["asset_class"] = out["asset"].map(asset_classes or {}).fillna("Unclassified")
    return out


def run(input_dir: Path, output_dir: Path, min_obs: int, index_workbook: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    bcf_path = input_dir / DEFAULT_BCF_WORKBOOK
    regime_path = input_dir / DEFAULT_REGIME_WORKBOOK

    bcf = load_business_cycle_model(bcf_path)
    bcf.to_csv(output_dir / "business_cycle_signals.csv", index=False)
    bcf[bcf["phase_calc"].notna()].tail(1).to_csv(output_dir / "latest_business_cycle_signal.csv", index=False)

    regime = load_macro_regime(regime_path)
    regime.to_csv(output_dir / "macro_regime_signals.csv", index=False)
    regime[regime["regime_calc"].notna()].tail(1).to_csv(output_dir / "latest_macro_regime_signal.csv", index=False)

    index_returns = load_index_level_returns(index_workbook)
    index_returns.dataframe.to_csv(output_dir / "index_level_returns.csv", index=False)
    asset_map = pd.DataFrame(
        [{"asset": asset, "asset_class": asset_class} for asset, asset_class in index_returns.asset_classes.items()]
    )
    asset_map.to_csv(output_dir / "index_asset_classes.csv", index=False)

    index_stats = state_conditioned_stats(
        index_returns.dataframe,
        index_returns.state_cols,
        index_returns.asset_cols,
        min_obs=min_obs,
    )
    index_stats.insert(0, "source_sheet", "Index Level")
    index_stats = _attach_asset_class(index_stats, index_returns.asset_classes)
    index_stats.to_csv(output_dir / "index_level_state_stats.csv", index=False)

    class_returns = build_asset_class_returns(index_returns)
    class_returns.dataframe.to_csv(output_dir / "asset_class_returns.csv", index=False)
    class_stats = state_conditioned_stats(
        class_returns.dataframe,
        class_returns.state_cols,
        class_returns.asset_cols,
        min_obs=min_obs,
    )
    class_stats.insert(0, "source_sheet", "Asset Class")
    class_stats["asset_class"] = class_stats["asset"]
    class_stats.to_csv(output_dir / "asset_class_state_stats.csv", index=False)

    for state_col in index_returns.state_cols:
        if state_col in index_returns.dataframe.columns:
            transition_matrix(index_returns.dataframe[state_col], normalize=False).to_csv(
                output_dir / f"index_level_{_safe_name(state_col)}_transition_counts.csv"
            )
            transition_matrix(index_returns.dataframe[state_col], normalize=True).to_csv(
                output_dir / f"index_level_{_safe_name(state_col)}_transition_probabilities.csv"
            )

    combined = pd.concat([index_stats, class_stats], ignore_index=True)
    combined.to_csv(output_dir / "all_state_stats.csv", index=False)
    top = top_assets_by_state(combined, n=5) if not combined.empty else pd.DataFrame()
    top.to_csv(output_dir / "top_assets_by_state.csv", index=False)
    write_summary(output_dir, bcf, regime, top)
    write_dashboard(output_dir, bcf, regime, combined, top)
    write_index_dashboard(output_dir, bcf, regime, index_stats, class_stats, top)


def main() -> None:
    parser = argparse.ArgumentParser(description="Run business-cycle and regime backtests.")
    parser.add_argument("--input-dir", type=Path, default=Path("drive_downloads"))
    parser.add_argument("--output-dir", type=Path, default=Path("outputs"))
    parser.add_argument("--index-workbook", type=Path, default=Path(DEFAULT_INDEX_WORKBOOK))
    parser.add_argument("--min-obs", type=int, default=6)
    args = parser.parse_args()
    run(args.input_dir, args.output_dir, args.min_obs, args.index_workbook)


if __name__ == "__main__":
    main()
