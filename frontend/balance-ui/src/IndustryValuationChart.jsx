
import React, { useMemo, useState, useEffect } from "react";
import {
  PieChart,
  Pie,
  Cell,
  Tooltip,
  ResponsiveContainer,
} from "recharts";
import "./BalanceSheet.css";

const COLORS = [
  "#2457C5", "#193F98", "#4775D1", "#0E65D8",
  "#648BE0", "#3262B8", "#83A3EA", "#4267A9",
  "#9BB5ED", "#5B7DBD", "#244779", "#7892C4",
  "#102B5E", "#ABC2F2", "#35518A", "#6B87B8",
  "#D1DDF7", "#3C5F9D", "#5478B7", "#8CA5D6",
];

const formatCount = (value) =>
  new Intl.NumberFormat("en-IN").format(Number(value) || 0);

const IndustryValuationChart = ({
  data,
  valuationType,
  onIndustrySelect,
}) => {
  const [activeIndustry, setActiveIndustry] = useState(null);

  const isOvervalued = valuationType === "overvalued";

  const chartData = useMemo(() => {
    if (!Array.isArray(data)) return [];

    const sorted = data
      .map((item) => ({
        name: item.industry,
        value: Number(
          isOvervalued ? item.overvalued : item.undervalued
        ) || 0,
      }))
      .filter((item) => item.name && item.value > 0)
      .sort((a, b) => b.value - a.value);

    const top = sorted.slice(0, 12);
    const othersValue = sorted
      .slice(12)
      .reduce((sum, item) => sum + item.value, 0);

    if (othersValue > 0) {
      top.push({ name: "Others", value: othersValue });
    }

    return top;
  }, [data, isOvervalued]);

  useEffect(() => {
    setActiveIndustry(null);
  }, [valuationType]);

  const total = chartData.reduce((sum, item) => sum + item.value, 0);
  const selected = chartData.find(
    (item) => item.name === activeIndustry
  );

  const handleSelect = (name) => {
    if (!name || name === "Others") return;

    const nextIndustry = activeIndustry === name ? null : name;
    setActiveIndustry(nextIndustry);
    onIndustrySelect?.(name);
  };

  const clearSelection = () => {
    const previousIndustry = activeIndustry;
    setActiveIndustry(null);

    if (previousIndustry) {
      onIndustrySelect?.(previousIndustry);
    }
  };

  if (chartData.length === 0) {
    return (
      <div className="industry-chart-empty" role="status">
        <div className="industry-chart-empty-icon" aria-hidden="true">
          ◌
        </div>
        <strong>No industry data available</strong>
        <span>
          Try changing your screening criteria to see the distribution.
        </span>
      </div>
    );
  }

  return (
    <section
      className={`industry-chart ${
        isOvervalued ? "is-overvalued" : "is-undervalued"
      }`}
      aria-label={`${
        isOvervalued ? "Overvalued" : "Undervalued"
      } industry distribution`}
    >
      <header className="industry-chart-heading">
        <div className="industry-chart-heading-copy">
          <span className="industry-chart-eyebrow">
            INDUSTRY DISTRIBUTION
          </span>
          <h4>
            {isOvervalued ? "Overvalued" : "Undervalued"} companies
          </h4>
          <p>Select an industry to filter the company list.</p>
        </div>

        <span
          className={`industry-chart-status ${
            isOvervalued ? "status-red" : "status-blue"
          }`}
        >
          <span className="industry-chart-status-dot" />
          {isOvervalued ? "Overvalued" : "Undervalued"}
        </span>
      </header>

      <div className="industry-chart-layout">
        <div className="industry-chart-donut">
          <ResponsiveContainer width="100%" height="100%">
            <PieChart>
              <Pie
                data={chartData}
                dataKey="value"
                nameKey="name"
                cx="50%"
                cy="50%"
                innerRadius="64%"
                outerRadius="88%"
                paddingAngle={2}
                stroke="#FFFFFF"
                strokeWidth={3}
                onClick={(entry) => handleSelect(entry?.name)}
                isAnimationActive
                animationDuration={350}
              >
                {chartData.map((entry, index) => (
                  <Cell
                    key={entry.name}
                    fill={
                      entry.name === "Others"
                        ? "#DCE5F5"
                        : COLORS[index % COLORS.length]
                    }
                    opacity={
                      activeIndustry &&
                      activeIndustry !== entry.name
                        ? 0.3
                        : 1
                    }
                    style={{ cursor: entry.name === "Others" ? "default" : "pointer" }}
                  />
                ))}
              </Pie>

              <Tooltip
                formatter={(value, name) => [
                  `${formatCount(value)} companies`,
                  name,
                ]}
                contentStyle={{
                  border: "1px solid #DCE5F2",
                  borderRadius: 10,
                  boxShadow: "0 8px 24px rgba(31, 61, 115, 0.12)",
                  fontSize: 12,
                }}
              />
            </PieChart>
          </ResponsiveContainer>

          <div className="industry-chart-center" aria-live="polite">
            <span>{selected ? "SELECTED INDUSTRY" : "TOTAL COMPANIES"}</span>
            <strong>
              {formatCount(selected ? selected.value : total)}
            </strong>
            <small title={selected?.name}>
              {selected ? selected.name : "Across industries"}
            </small>
          </div>
        </div>

        <aside className="industry-chart-legend-panel">
          <div className="industry-chart-legend-heading">
            <span>Industry</span>
            <span>Count</span>
          </div>

          <div className="industry-chart-legend-list">
            {chartData.map((entry, index) => {
              const isSelected = activeIndustry === entry.name;
              const isDimmed =
                activeIndustry && !isSelected;

              return (
                <button
                  key={entry.name}
                  type="button"
                  className={`industry-chart-legend-item ${
                    isSelected ? "selected" : ""
                  } ${isDimmed ? "dimmed" : ""}`}
                  onClick={() => handleSelect(entry.name)}
                  disabled={entry.name === "Others"}
                  title={
                    entry.name === "Others"
                      ? "Grouped remaining industries"
                      : `Filter by ${entry.name}`
                  }
                  aria-pressed={
                    entry.name === "Others" ? undefined : isSelected
                  }
                >
                  <span className="industry-chart-legend-name">
                    <span
                      className="industry-chart-swatch"
                      style={{
                        background:
                          entry.name === "Others"
                            ? "#DCE5F5"
                            : COLORS[index % COLORS.length],
                      }}
                    />
                    <span className="industry-chart-legend-text">
                      {entry.name}
                    </span>
                  </span>
                  <strong>{formatCount(entry.value)}</strong>
                </button>
              );
            })}
          </div>
        </aside>
      </div>

      <footer className="industry-chart-footer">
        <div className="industry-chart-total">
          <span className="industry-chart-total-mark" />
          <span>{chartData.length} categories shown</span>
        </div>

        {activeIndustry && (
          <button
            type="button"
            className="industry-chart-clear"
            onClick={clearSelection}
          >
            Clear selection
          </button>
        )}
      </footer>
    </section>
  );
};

export default IndustryValuationChart;
