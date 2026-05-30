from __future__ import annotations

from pathlib import Path
from html import escape

import pandas as pd


def _pct(value: object) -> str:
    if pd.isna(value):
        return ""
    return f"{float(value):.2%}"


def write_summary(
    output_dir: str | Path,
    bcf: pd.DataFrame,
    regime: pd.DataFrame,
    top_assets: pd.DataFrame,
) -> Path:
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)
    path = output / "summary.md"

    latest_bcf = bcf.dropna(subset=["phase_calc"]).tail(1)
    latest_regime = regime.dropna(subset=["regime_calc"]).tail(1)
    lines: list[str] = ["# Business Cycle Backtest Summary", ""]

    if not latest_bcf.empty:
        row = latest_bcf.iloc[0]
        lines.extend(
            [
                "## Latest Business Cycle Signal",
                f"- Date: {row['date'].date()}",
                f"- Phase: {row['phase_calc']}",
                f"- RoRo: {row['roro_calc']}",
                f"- Aggregate score: {row['aggregate_score']:.4f}",
                f"- 3-month rolling delta: {row['delta_3m']:.4f}",
                "",
            ]
        )
    if not latest_regime.empty:
        row = latest_regime.iloc[0]
        lines.extend(
            [
                "## Latest Macro Regime Signal",
                f"- Date: {row['date'].date()}",
                f"- Regime: {row['regime_calc']}",
                f"- Growth 3-month delta: {row['growth_delta_3m']:.4f}",
                f"- Inflation 3-month delta: {row['inflation_delta_3m']:.4f}",
                "",
            ]
        )

    if not top_assets.empty:
        lines.extend(["## Top Historical Assets By State", ""])
        preview = top_assets.head(30)
        lines.append("| Source | State Set | State | Asset | Obs | Ann. Return | Ann. Vol | Sharpe |")
        lines.append("|---|---|---|---:|---:|---:|---:|---:|")
        for _, row in preview.iterrows():
            source = row.get("source_sheet", "")
            lines.append(
                "| "
                f"{source} | {row['state_column']} | {row['state']} | {row['asset']} | "
                f"{int(row['observations'])} | {_pct(row['annualized_return'])} | "
                f"{_pct(row['annualized_volatility'])} | {row['sharpe']:.2f} |"
            )
        lines.append("")

    lines.extend(
        [
            "## Notes",
            "- Returns are normalized to decimal monthly returns before annualization.",
            "- Sharpe ratios use geometric annualized return divided by annualized volatility.",
            "- Use T-1 signal sheets for more conservative no-lookahead research.",
        ]
    )
    path.write_text("\n".join(lines), encoding="utf-8")
    return path


def _num(value: object, digits: int = 2) -> str:
    if pd.isna(value):
        return ""
    return f"{float(value):.{digits}f}"


def _date(value: object) -> str:
    if pd.isna(value):
        return ""
    return pd.to_datetime(value).strftime("%b %d, %Y")


def _class_for_metric(value: object, metric: str) -> str:
    if pd.isna(value):
        return ""
    x = float(value)
    if metric == "sharpe":
        if x >= 1:
            return "good"
        if x <= 0:
            return "bad"
        return "mid"
    if metric in {"return", "drawdown"}:
        if x > 0:
            return "good"
        if x < 0:
            return "bad"
    return ""


def _latest_card(title: str, rows: list[tuple[str, str]], tone: str = "") -> str:
    items = "\n".join(
        f"<div class=\"metric\"><span>{escape(label)}</span><strong>{escape(value)}</strong></div>"
        for label, value in rows
    )
    return f"<section class=\"card {tone}\"><h3>{escape(title)}</h3>{items}</section>"


def _stats_table(df: pd.DataFrame, title: str, limit: int = 80) -> str:
    if df.empty:
        return f"<section class=\"panel\"><h2>{escape(title)}</h2><p>No data available.</p></section>"
    rows = []
    for _, row in df.head(limit).iterrows():
        asset_class = row.get("asset_class", "")
        rows.append(
            "<tr>"
            f"<td>{escape(str(row.get('source_sheet', '')))}</td>"
            f"<td>{escape(str(asset_class))}</td>"
            f"<td>{escape(str(row['state_column']))}</td>"
            f"<td>{escape(str(row['state']))}</td>"
            f"<td class=\"asset\">{escape(str(row['asset']))}</td>"
            f"<td>{int(row['observations'])}</td>"
            f"<td class=\"{_class_for_metric(row['annualized_return'], 'return')}\">{_pct(row['annualized_return'])}</td>"
            f"<td>{_pct(row['annualized_volatility'])}</td>"
            f"<td class=\"{_class_for_metric(row['sharpe'], 'sharpe')}\">{_num(row['sharpe'])}</td>"
            f"<td>{_pct(row['hit_rate'])}</td>"
            f"<td class=\"{_class_for_metric(row['max_drawdown'], 'drawdown')}\">{_pct(row['max_drawdown'])}</td>"
            "</tr>"
        )
    return (
        f"<section class=\"panel\"><h2>{escape(title)}</h2>"
        "<div class=\"table-wrap\"><table>"
        "<thead><tr><th>Source</th><th>Asset Class</th><th>State Set</th><th>State</th><th>Asset</th><th>Obs</th>"
        "<th>Ann. Return</th><th>Ann. Vol</th><th>Sharpe</th><th>Hit Rate</th><th>Max DD</th></tr></thead>"
        f"<tbody>{''.join(rows)}</tbody></table></div></section>"
    )


def _pivot_table(stats: pd.DataFrame, state_col: str, metric: str, source: str | None = None) -> pd.DataFrame:
    df = stats[stats["state_column"].eq(state_col)].copy()
    if source:
        df = df[df["source_sheet"].eq(source)]
    if df.empty:
        return pd.DataFrame()
    pivot = df.pivot_table(index="asset", columns="state", values=metric, aggfunc="first")
    ordered_cols = [c for c in ["Expansion", "Slowdown", "Contraction", "Recovery"] if c in pivot.columns]
    ordered_cols += [c for c in pivot.columns if c not in ordered_cols]
    pivot = pivot[ordered_cols]
    return pivot.sort_index()


def _heatmap(pivot: pd.DataFrame, title: str, metric: str, limit: int = 30) -> str:
    if pivot.empty:
        return f"<section class=\"panel\"><h2>{escape(title)}</h2><p>No data available.</p></section>"
    view = pivot.head(limit)
    header = "".join(f"<th>{escape(str(col))}</th>" for col in view.columns)
    rows = []
    for asset, values in view.iterrows():
        cells = []
        for value in values:
            cls = _class_for_metric(value, "sharpe" if metric == "sharpe" else "return")
            text = _num(value) if metric == "sharpe" else _pct(value)
            cells.append(f"<td class=\"heat {cls}\">{text}</td>")
        rows.append(f"<tr><td class=\"asset sticky\">{escape(str(asset))}</td>{''.join(cells)}</tr>")
    label = "Sharpe" if metric == "sharpe" else "Annualized Return"
    return (
        f"<section class=\"panel\"><h2>{escape(title)}</h2><p>{label} by asset and state.</p>"
        "<div class=\"table-wrap\"><table class=\"matrix\">"
        f"<thead><tr><th class=\"sticky\">Asset</th>{header}</tr></thead>"
        f"<tbody>{''.join(rows)}</tbody></table></div></section>"
    )


def _transition_table(path: Path, title: str) -> str:
    if not path.exists():
        return ""
    df = pd.read_csv(path, index_col=0)
    header = "".join(f"<th>{escape(str(col))}</th>" for col in df.columns)
    rows = []
    for idx, values in df.iterrows():
        cells = "".join(f"<td>{_pct(value)}</td>" for value in values)
        rows.append(f"<tr><td class=\"sticky\">{escape(str(idx))}</td>{cells}</tr>")
    return (
        f"<section class=\"panel\"><h2>{escape(title)}</h2>"
        "<div class=\"table-wrap\"><table class=\"matrix\">"
        f"<thead><tr><th class=\"sticky\">From / To</th>{header}</tr></thead>"
        f"<tbody>{''.join(rows)}</tbody></table></div></section>"
    )


def write_dashboard(
    output_dir: str | Path,
    bcf: pd.DataFrame,
    regime: pd.DataFrame,
    all_stats: pd.DataFrame,
    top_assets: pd.DataFrame,
) -> Path:
    output = Path(output_dir)
    path = output / "dashboard.html"
    latest_bcf = bcf.dropna(subset=["phase_calc"]).tail(1)
    latest_regime = regime.dropna(subset=["regime_calc"]).tail(1)

    bcf_rows = [("Date", ""), ("Phase", ""), ("RoRo", ""), ("Score", ""), ("3M Delta", "")]
    if not latest_bcf.empty:
        row = latest_bcf.iloc[0]
        bcf_rows = [
            ("Date", _date(row["date"])),
            ("Phase", str(row["phase_calc"])),
            ("RoRo", str(row["roro_calc"])),
            ("Score", _num(row["aggregate_score"], 4)),
            ("3M Delta", _num(row["delta_3m"], 4)),
        ]
    regime_rows = [("Date", ""), ("Regime", ""), ("Growth 3M", ""), ("Inflation 3M", "")]
    if not latest_regime.empty:
        row = latest_regime.iloc[0]
        regime_rows = [
            ("Date", _date(row["date"])),
            ("Regime", str(row["regime_calc"])),
            ("Growth 3M", _num(row["growth_delta_3m"], 4)),
            ("Inflation 3M", _num(row["inflation_delta_3m"], 4)),
        ]

    source = "BCF + Regime (Benchmarks)"
    phase_sharpe = _pivot_table(all_stats, "Phase", "sharpe", source)
    phase_return = _pivot_table(all_stats, "Phase", "annualized_return", source)
    regime_sharpe = _pivot_table(all_stats, "Regime", "sharpe", source)
    combined_sharpe = _pivot_table(all_stats, "Phase-Regime", "sharpe", source)

    phase_top = top_assets[
        top_assets["source_sheet"].eq(source) & top_assets["state_column"].eq("Phase")
    ]
    regime_top = top_assets[
        top_assets["source_sheet"].eq(source) & top_assets["state_column"].eq("Regime")
    ]
    combined_top = top_assets[
        top_assets["source_sheet"].eq(source) & top_assets["state_column"].eq("Phase-Regime")
    ]

    html = f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Business Cycle Backtest Dashboard</title>
<style>
:root {{
  --bg: #f7f8f5;
  --ink: #1d2528;
  --muted: #667176;
  --line: #d9ded7;
  --panel: #ffffff;
  --good-bg: #dff2e6;
  --good: #16633a;
  --mid-bg: #fff0c7;
  --mid: #7a5700;
  --bad-bg: #f8d8d4;
  --bad: #9b2f25;
  --accent: #225c68;
}}
* {{ box-sizing: border-box; }}
body {{
  margin: 0;
  font-family: Arial, Helvetica, sans-serif;
  background: var(--bg);
  color: var(--ink);
}}
header {{
  padding: 28px 32px 18px;
  border-bottom: 1px solid var(--line);
  background: #eef3ef;
}}
h1 {{ margin: 0 0 6px; font-size: 28px; letter-spacing: 0; }}
h2 {{ margin: 0 0 12px; font-size: 18px; }}
h3 {{ margin: 0 0 14px; font-size: 14px; color: var(--muted); text-transform: uppercase; }}
p {{ margin: 0 0 14px; color: var(--muted); }}
nav {{
  display: flex;
  gap: 8px;
  padding: 12px 32px;
  border-bottom: 1px solid var(--line);
  background: var(--panel);
  position: sticky;
  top: 0;
  z-index: 5;
  overflow-x: auto;
}}
nav button {{
  border: 1px solid var(--line);
  background: #fff;
  color: var(--ink);
  padding: 8px 12px;
  border-radius: 6px;
  cursor: pointer;
  white-space: nowrap;
}}
nav button.active {{ background: var(--accent); color: white; border-color: var(--accent); }}
main {{ padding: 24px 32px 40px; }}
.tab {{ display: none; }}
.tab.active {{ display: block; }}
.cards {{
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(260px, 1fr));
  gap: 16px;
  margin-bottom: 18px;
}}
.card, .panel {{
  background: var(--panel);
  border: 1px solid var(--line);
  border-radius: 8px;
  padding: 18px;
  margin-bottom: 18px;
}}
.metric {{
  display: flex;
  justify-content: space-between;
  gap: 14px;
  padding: 8px 0;
  border-top: 1px solid #edf0ec;
}}
.metric:first-of-type {{ border-top: 0; }}
.metric span {{ color: var(--muted); }}
.metric strong {{ text-align: right; }}
.table-wrap {{ overflow: auto; border: 1px solid var(--line); border-radius: 6px; }}
table {{ width: 100%; border-collapse: collapse; font-size: 13px; background: white; }}
th, td {{ padding: 9px 10px; border-bottom: 1px solid #edf0ec; text-align: right; white-space: nowrap; }}
th {{ background: #f1f4f0; color: #3f4b50; font-weight: 700; position: sticky; top: 0; z-index: 1; }}
td:first-child, th:first-child, .asset {{ text-align: left; }}
.asset {{ min-width: 240px; }}
.sticky {{ position: sticky; left: 0; background: inherit; z-index: 2; }}
th.sticky {{ background: #f1f4f0; z-index: 3; }}
.good {{ background: var(--good-bg); color: var(--good); font-weight: 700; }}
.mid {{ background: var(--mid-bg); color: var(--mid); font-weight: 700; }}
.bad {{ background: var(--bad-bg); color: var(--bad); font-weight: 700; }}
.heat {{ min-width: 96px; }}
.note {{ color: var(--muted); font-size: 13px; margin-top: 10px; }}
@media (max-width: 720px) {{
  header, main {{ padding-left: 16px; padding-right: 16px; }}
  nav {{ padding-left: 16px; padding-right: 16px; }}
}}
</style>
</head>
<body>
<header>
  <h1>Business Cycle Backtest Dashboard</h1>
  <p>Readable dashboard layer generated from the same model outputs as the CSV files.</p>
</header>
<nav>
  <button class="active" data-tab="overview">Overview</button>
  <button data-tab="phase">Phase</button>
  <button data-tab="regime">Regime</button>
  <button data-tab="combined">Phase + Regime</button>
  <button data-tab="transitions">Transitions</button>
  <button data-tab="tables">Full Tables</button>
</nav>
<main>
  <section id="overview" class="tab active">
    <div class="cards">
      {_latest_card("Current Business Cycle", bcf_rows, "cycle")}
      {_latest_card("Current Macro Regime", regime_rows, "regime")}
      {_latest_card("How To Read This", [("Green", "stronger historical metric"), ("Yellow", "positive but modest"), ("Red", "negative or weak")])}
    </div>
    {_heatmap(phase_sharpe, "Asset-Class Sharpe By Business Cycle Phase", "sharpe")}
    {_stats_table(phase_top, "Top Assets By Business Cycle Phase", 30)}
  </section>
  <section id="phase" class="tab">
    {_heatmap(phase_sharpe, "Sharpe By Phase", "sharpe")}
    {_heatmap(phase_return, "Annualized Return By Phase", "return")}
    {_stats_table(phase_top, "Phase Playbook", 80)}
  </section>
  <section id="regime" class="tab">
    {_heatmap(regime_sharpe, "Sharpe By Growth/Inflation Regime", "sharpe")}
    {_stats_table(regime_top, "Regime Playbook", 80)}
  </section>
  <section id="combined" class="tab">
    {_heatmap(combined_sharpe, "Sharpe By Combined Phase-Regime State", "sharpe", 60)}
    {_stats_table(combined_top, "Combined State Playbook", 120)}
  </section>
  <section id="transitions" class="tab">
    {_transition_table(output / "bcf_plus_regime_benchmarks_phase_transition_probabilities.csv", "Business Cycle Phase Transition Probabilities")}
    {_transition_table(output / "bcf_plus_regime_benchmarks_regime_transition_probabilities.csv", "Macro Regime Transition Probabilities")}
    {_transition_table(output / "bcf_plus_regime_benchmarks_phase_regime_transition_probabilities.csv", "Combined Phase-Regime Transition Probabilities")}
  </section>
  <section id="tables" class="tab">
    {_stats_table(all_stats.sort_values(["source_sheet", "state_column", "state", "sharpe"], ascending=[True, True, True, False]), "All State Statistics", 500)}
  </section>
</main>
<script>
const buttons = Array.from(document.querySelectorAll("nav button"));
const tabs = Array.from(document.querySelectorAll(".tab"));
buttons.forEach(button => {{
  button.addEventListener("click", () => {{
    buttons.forEach(b => b.classList.remove("active"));
    tabs.forEach(t => t.classList.remove("active"));
    button.classList.add("active");
    document.getElementById(button.dataset.tab).classList.add("active");
  }});
}});
</script>
</body>
</html>"""
    path.write_text(html, encoding="utf-8")
    return path


def _asset_class_cards(class_stats: pd.DataFrame, state_col: str = "Phase t-1") -> str:
    if class_stats.empty:
        return ""
    df = class_stats[class_stats["state_column"].eq(state_col)].copy()
    if df.empty:
        return ""
    rows = []
    for state in sorted(df["state"].dropna().unique()):
        subset = df[df["state"].eq(state)].sort_values("sharpe", ascending=False)
        if subset.empty:
            continue
        top = subset.iloc[0]
        rows.append(
            _latest_card(
                str(state),
                [
                    ("Best Class", str(top["asset"])),
                    ("Sharpe", _num(top["sharpe"])),
                    ("Ann. Return", _pct(top["annualized_return"])),
                    ("Ann. Vol", _pct(top["annualized_volatility"])),
                ],
            )
        )
    return f"<div class=\"cards\">{''.join(rows)}</div>"


def write_index_dashboard(
    output_dir: str | Path,
    bcf: pd.DataFrame,
    regime: pd.DataFrame,
    index_stats: pd.DataFrame,
    class_stats: pd.DataFrame,
    top_assets: pd.DataFrame,
) -> Path:
    output = Path(output_dir)
    path = output / "index_dashboard.html"
    latest_bcf = bcf.dropna(subset=["phase_calc"]).tail(1)
    latest_regime = regime.dropna(subset=["regime_calc"]).tail(1)

    bcf_rows = [("Date", ""), ("Phase", ""), ("RoRo", ""), ("Score", ""), ("3M Delta", "")]
    if not latest_bcf.empty:
        row = latest_bcf.iloc[0]
        bcf_rows = [
            ("Date", _date(row["date"])),
            ("Phase", str(row["phase_calc"])),
            ("RoRo", str(row["roro_calc"])),
            ("Score", _num(row["aggregate_score"], 4)),
            ("3M Delta", _num(row["delta_3m"], 4)),
        ]
    regime_rows = [("Date", ""), ("Regime", ""), ("Growth 3M", ""), ("Inflation 3M", "")]
    if not latest_regime.empty:
        row = latest_regime.iloc[0]
        regime_rows = [
            ("Date", _date(row["date"])),
            ("Regime", str(row["regime_calc"])),
            ("Growth 3M", _num(row["growth_delta_3m"], 4)),
            ("Inflation 3M", _num(row["inflation_delta_3m"], 4)),
        ]

    phase_sharpe = _pivot_table(index_stats, "Phase t-1", "sharpe", "Index Level")
    regime_sharpe = _pivot_table(index_stats, "Regime t-1", "sharpe", "Index Level")
    combined_sharpe = _pivot_table(index_stats, "Phase-Regime t-1", "sharpe", "Index Level")
    class_phase = _pivot_table(class_stats, "Phase t-1", "sharpe", "Asset Class")
    class_regime = _pivot_table(class_stats, "Regime t-1", "sharpe", "Asset Class")

    top_index = top_assets[top_assets["source_sheet"].eq("Index Level")]
    top_class = top_assets[top_assets["source_sheet"].eq("Asset Class")]

    css = """
<style>
:root { --bg:#f7f8f5; --ink:#1d2528; --muted:#667176; --line:#d9ded7; --panel:#fff; --good-bg:#dff2e6; --good:#16633a; --mid-bg:#fff0c7; --mid:#7a5700; --bad-bg:#f8d8d4; --bad:#9b2f25; --accent:#225c68; }
* { box-sizing:border-box; }
body { margin:0; font-family:Arial, Helvetica, sans-serif; background:var(--bg); color:var(--ink); }
header { padding:28px 32px 18px; border-bottom:1px solid var(--line); background:#eef3ef; }
h1 { margin:0 0 6px; font-size:28px; letter-spacing:0; }
h2 { margin:0 0 12px; font-size:18px; }
h3 { margin:0 0 14px; font-size:14px; color:var(--muted); text-transform:uppercase; }
p { margin:0 0 14px; color:var(--muted); }
nav { display:flex; gap:8px; padding:12px 32px; border-bottom:1px solid var(--line); background:var(--panel); position:sticky; top:0; z-index:5; overflow-x:auto; }
nav button { border:1px solid var(--line); background:#fff; color:var(--ink); padding:8px 12px; border-radius:6px; cursor:pointer; white-space:nowrap; }
nav button.active { background:var(--accent); color:#fff; border-color:var(--accent); }
main { padding:24px 32px 40px; }
.tab { display:none; } .tab.active { display:block; }
.cards { display:grid; grid-template-columns:repeat(auto-fit,minmax(240px,1fr)); gap:16px; margin-bottom:18px; }
.card,.panel { background:var(--panel); border:1px solid var(--line); border-radius:8px; padding:18px; margin-bottom:18px; }
.metric { display:flex; justify-content:space-between; gap:14px; padding:8px 0; border-top:1px solid #edf0ec; }
.metric:first-of-type { border-top:0; } .metric span { color:var(--muted); } .metric strong { text-align:right; }
.table-wrap { overflow:auto; border:1px solid var(--line); border-radius:6px; }
table { width:100%; border-collapse:collapse; font-size:13px; background:#fff; }
th,td { padding:9px 10px; border-bottom:1px solid #edf0ec; text-align:right; white-space:nowrap; }
th { background:#f1f4f0; color:#3f4b50; font-weight:700; position:sticky; top:0; z-index:1; }
td:first-child,th:first-child,.asset { text-align:left; }
.asset { min-width:240px; }
.sticky { position:sticky; left:0; background:inherit; z-index:2; }
th.sticky { background:#f1f4f0; z-index:3; }
.good { background:var(--good-bg); color:var(--good); font-weight:700; }
.mid { background:var(--mid-bg); color:var(--mid); font-weight:700; }
.bad { background:var(--bad-bg); color:var(--bad); font-weight:700; }
@media (max-width:720px) { header,main,nav { padding-left:16px; padding-right:16px; } }
</style>"""

    html = f"""<!doctype html>
<html lang="en">
<head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>Index-Level Business Cycle Dashboard</title>{css}</head>
<body>
<header>
  <h1>Index-Level Business Cycle Dashboard</h1>
  <p>Backtest universe is restricted to the index-level workbook. Asset-class summaries are equal-weighted across indexes in each class.</p>
</header>
<nav>
  <button class="active" data-tab="overview">Overview</button>
  <button data-tab="classes">Asset Classes</button>
  <button data-tab="phase">Phase</button>
  <button data-tab="regime">Regime</button>
  <button data-tab="combined">Phase + Regime</button>
  <button data-tab="transitions">Transitions</button>
  <button data-tab="tables">Full Tables</button>
</nav>
<main>
  <section id="overview" class="tab active">
    <div class="cards">
      {_latest_card("Current Business Cycle", bcf_rows)}
      {_latest_card("Current Macro Regime", regime_rows)}
      {_latest_card("Universe", [("Source", "Index-level workbook"), ("Return Type", "Monthly index returns"), ("Class Summary", "Equal-weighted")])}
    </div>
    {_asset_class_cards(class_stats)}
    {_heatmap(class_phase, "Asset-Class Sharpe By Business Cycle Phase", "sharpe")}
    {_stats_table(top_index[top_index["state_column"].eq("Phase t-1")], "Top Indexes By Business Cycle Phase", 40)}
  </section>
  <section id="classes" class="tab">
    {_heatmap(class_phase, "Asset-Class Sharpe By Phase", "sharpe")}
    {_heatmap(class_regime, "Asset-Class Sharpe By Regime", "sharpe")}
    {_stats_table(top_class, "Asset-Class Summary Playbook", 120)}
  </section>
  <section id="phase" class="tab">
    {_heatmap(phase_sharpe, "Index Sharpe By Phase", "sharpe", 80)}
    {_stats_table(top_index[top_index["state_column"].eq("Phase t-1")], "Phase Playbook By Index", 120)}
  </section>
  <section id="regime" class="tab">
    {_heatmap(regime_sharpe, "Index Sharpe By Regime", "sharpe", 80)}
    {_stats_table(top_index[top_index["state_column"].eq("Regime t-1")], "Regime Playbook By Index", 120)}
  </section>
  <section id="combined" class="tab">
    {_heatmap(combined_sharpe, "Index Sharpe By Combined Phase-Regime", "sharpe", 120)}
    {_stats_table(top_index[top_index["state_column"].eq("Phase-Regime t-1")], "Combined State Playbook By Index", 200)}
  </section>
  <section id="transitions" class="tab">
    {_transition_table(output / "index_level_phase_t_1_transition_probabilities.csv", "Business Cycle Phase Transition Probabilities")}
    {_transition_table(output / "index_level_regime_t_1_transition_probabilities.csv", "Macro Regime Transition Probabilities")}
    {_transition_table(output / "index_level_phase_regime_t_1_transition_probabilities.csv", "Combined Phase-Regime Transition Probabilities")}
  </section>
  <section id="tables" class="tab">
    {_stats_table(pd.concat([class_stats, index_stats], ignore_index=True).sort_values(["source_sheet", "state_column", "state", "sharpe"], ascending=[True, True, True, False]), "All Index and Asset-Class Statistics", 800)}
  </section>
</main>
<script>
const buttons = Array.from(document.querySelectorAll("nav button"));
const tabs = Array.from(document.querySelectorAll(".tab"));
buttons.forEach(button => {{
  button.addEventListener("click", () => {{
    buttons.forEach(b => b.classList.remove("active"));
    tabs.forEach(t => t.classList.remove("active"));
    button.classList.add("active");
    document.getElementById(button.dataset.tab).classList.add("active");
  }});
}});
</script>
</body></html>"""
    path.write_text(html, encoding="utf-8")
    return path
