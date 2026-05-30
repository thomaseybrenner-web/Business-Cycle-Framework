const data = window.BACKTEST_DATA;

const fmt = new Intl.NumberFormat("en-US", { maximumFractionDigits: 2 });
const pct = (value) => value === null || Number.isNaN(value) ? "--" : `${(value * 100).toFixed(1)}%`;
const num = (value) => value === null || Number.isNaN(value) ? "--" : fmt.format(value);

function metricTone(value) {
  if (value === null || Number.isNaN(value)) return "";
  if (value >= 1) return "good";
  if (value <= 0) return "bad";
  return "mid";
}

function setText(id, value) {
  document.getElementById(id).textContent = value;
}

function rowMetric(label, value) {
  return `<div class="metric-row"><span>${label}</span><b>${value}</b></div>`;
}

function renderClassCards(targetId, rows) {
  const target = document.getElementById(targetId);
  target.innerHTML = rows.map((row) => `
    <article class="class-card">
      <h3>${row.asset}</h3>
      <div class="score ${metricTone(row.sharpe)}">${num(row.sharpe)}</div>
      ${rowMetric("Ann. return", pct(row.annualizedReturn))}
      ${rowMetric("Volatility", pct(row.annualizedVolatility))}
      ${rowMetric("Hit rate", pct(row.hitRate))}
      ${rowMetric("Max drawdown", pct(row.maxDrawdown))}
    </article>
  `).join("");
}

function renderTable(targetId, rows, includeState = false) {
  const target = document.getElementById(targetId);
  target.innerHTML = rows.map((row) => `
    <tr>
      ${includeState ? `<td>${row.state}</td>` : ""}
      <td>${row.asset}</td>
      <td>${row.assetClass}</td>
      <td class="${row.annualizedReturn > 0 ? "good" : "bad"}">${pct(row.annualizedReturn)}</td>
      <td>${pct(row.annualizedVolatility)}</td>
      <td class="${metricTone(row.sharpe)}">${num(row.sharpe)}</td>
      <td>${pct(row.hitRate)}</td>
      <td class="${row.maxDrawdown < -0.25 ? "bad" : "mid"}">${pct(row.maxDrawdown)}</td>
    </tr>
  `).join("");
}

function renderMatrix(targetId, rows, states) {
  const target = document.getElementById(targetId);
  const header = `
    <div class="matrix-row">
      <div class="matrix-label">Asset class</div>
      ${states.map((state) => `<div class="matrix-label">${state}</div>`).join("")}
    </div>`;
  const body = rows.map((row) => `
    <div class="matrix-row">
      <div class="matrix-label">${row.asset}</div>
      ${states.map((state) => {
        const value = row[state];
        return `<div class="matrix-cell ${metricTone(value)}">${num(value)}</div>`;
      }).join("")}
    </div>
  `).join("");
  target.innerHTML = header + body;
}

function renderLineChart() {
  const colors = ["#245f68", "#7c5c2f", "#2f6f3e", "#9b2f25", "#5e4b8b"];
  const series = data.assetClassSeries;
  const allValues = series.flatMap((item) => item.points.map((point) => point.value));
  const min = Math.min(...allValues);
  const max = Math.max(...allValues);
  const width = 980;
  const height = 300;
  const pad = { top: 20, right: 24, bottom: 34, left: 52 };
  const pointCount = Math.max(...series.map((item) => item.points.length));
  const x = (index) => pad.left + (index / (pointCount - 1)) * (width - pad.left - pad.right);
  const y = (value) => pad.top + ((max - value) / (max - min)) * (height - pad.top - pad.bottom);
  const yTicks = [min, min + (max - min) / 2, max];

  const paths = series.map((item, index) => {
    const d = item.points.map((point, pointIndex) => {
      const command = pointIndex === 0 ? "M" : "L";
      return `${command}${x(pointIndex).toFixed(1)},${y(point.value).toFixed(1)}`;
    }).join(" ");
    return `<path d="${d}" fill="none" stroke="${colors[index % colors.length]}" stroke-width="3" stroke-linecap="round"/>`;
  }).join("");

  const ticks = yTicks.map((tick) => `
    <g>
      <line x1="${pad.left}" x2="${width - pad.right}" y1="${y(tick)}" y2="${y(tick)}" stroke="#e4e9e2"/>
      <text x="12" y="${y(tick) + 4}" font-size="12" fill="#68747b">${tick.toFixed(1)}x</text>
    </g>
  `).join("");

  const legend = series.map((item, index) => `
    <span><i class="swatch" style="background:${colors[index % colors.length]}"></i>${item.name}</span>
  `).join("");

  document.getElementById("lineChart").innerHTML = `
    <svg class="chart-svg" viewBox="0 0 ${width} ${height}" preserveAspectRatio="none">
      ${ticks}
      ${paths}
    </svg>
    <div class="legend">${legend}</div>
  `;
}

function initFilters() {
  const select = document.getElementById("stateFilter");
  const states = [...new Set(data.topAssets.map((row) => row.state))].sort();
  select.innerHTML = `<option value="All">All states</option>` + states.map((state) => `<option value="${state}">${state}</option>`).join("");
  const update = () => {
    const selected = select.value;
    const rows = selected === "All" ? data.topAssets : data.topAssets.filter((row) => row.state === selected);
    renderTable("rankingRows", rows.slice(0, 60), true);
  };
  select.addEventListener("change", update);
  update();
}

function initTabs() {
  const buttons = document.querySelectorAll(".nav button");
  const tabs = document.querySelectorAll(".tab");
  buttons.forEach((button) => {
    button.addEventListener("click", () => {
      buttons.forEach((item) => item.classList.remove("active"));
      tabs.forEach((tab) => tab.classList.remove("active"));
      button.classList.add("active");
      document.getElementById(button.dataset.tab).classList.add("active");
    });
  });
}

function init() {
  setText("generatedAt", data.generatedAt);
  setText("cyclePhase", data.latest.cycle.phase);
  setText("cycleDate", data.latest.cycle.date);
  setText("cycleRoro", data.latest.cycle.roro);
  setText("cycleScore", num(data.latest.cycle.score));
  setText("cycleDelta", num(data.latest.cycle.delta3m));
  setText("macroRegime", data.latest.regime.regime);
  setText("regimeDate", data.latest.regime.date);
  setText("growth3m", num(data.latest.regime.growth3m));
  setText("inflation3m", num(data.latest.regime.inflation3m));
  setText("assetCount", `${data.summary.assetCount} indexes`);
  setText("monthCount", data.summary.months);
  setText("classCount", data.summary.assetClasses.length);
  setText("stateCount", data.summary.statesTested);
  setText("phaseTitle", `Asset classes in ${data.latest.cycle.phase}`);
  setText("playbookTitle", `Best indexes in ${data.latest.cycle.phase}`);
  setText("regimePlaybookTitle", `Asset classes in ${data.latest.regime.regime}`);

  renderClassCards("currentClassCards", data.currentPhaseClasses);
  renderClassCards("currentRegimeCards", data.currentRegimeClasses);
  renderTable("currentIndexRows", data.currentPhaseTopIndexes);
  renderMatrix("phaseMatrix", data.phaseClassMatrix, ["Expansion", "Slowdown", "Contraction", "Recovery"]);
  renderMatrix("regimeMatrix", data.regimeClassMatrix, ["Goldilocks", "Reflation", "Inflation", "Deflation"]);
  renderLineChart();
  initFilters();
  initTabs();
}

init();
