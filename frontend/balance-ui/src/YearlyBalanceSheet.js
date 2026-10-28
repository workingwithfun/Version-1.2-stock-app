import React, {
  Fragment,
  useCallback,
  useEffect,
  useMemo,
  useRef,
  useState,
} from "react";
import "./BalanceSheet.css";

const API_BASE = "http://localhost:8000/api";

const EXPECTED_RETURN_OPTIONS = [
  10, 20, 30, 40, 50, 75, 100, 125, 150, 175, 200, 225, 250,
];

const GROWTH_ROWS = [
  { label: "Sales Growth YoY", key: "sales_growth" },
  { label: "OPM", key: "opm_growth" },
  { label: "NPM", key: "npm_growth" },
  { label: "EPS", key: "eps_growth" },
  { label: "ROE", key: "roe_growth" },
];

const VALUE_TABLE_COLUMNS = [
  "Year",
  "EPS",
  "Target EPS",
  "Target Price",
  "YOY Return",
  "Forecasted Return",
  "Holding Period",
];

const METHODS = ["average", "median", "trimmean"];

const emptyAnalysis = () => ({
  trimmean: [],
  median: [],
  average: [],
});

const initialData = {
  company_name: "",
  symbol: "",
  isin_number: "",
  sector: "",
  sub_sector_1: "",
  sub_sector_2: "",
  industry: "",
  metric_summary: [],
  balance_stats: [],
  value_analysis_10y: emptyAnalysis(),
  value_analysis_5y: emptyAnalysis(),
  growth: [],
  final_analysis_table: [],
  summary_conditions: {},
  mcap: null,
  years: [],
  rows: [],
};

function asArray(value) {
  return Array.isArray(value) ? value : [];
}

function getNumeric(value) {
  if (value === null || value === undefined || value === "") {
    return null;
  }

  if (typeof value === "number") {
    return Number.isFinite(value) ? value : null;
  }

  const cleaned = String(value)
    .trim()
    .replace(/,/g, "")
    .replace(/%$/, "");

  if (!cleaned || cleaned === "—" || cleaned === "-") {
    return null;
  }

  const parsed = Number(cleaned);
  return Number.isFinite(parsed) ? parsed : null;
}

function formatNumber(value) {
  const number = getNumeric(value);

  if (number === null) return "—";

  return number.toLocaleString("en-IN", {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  });
}

function formatFixed(value) {
  const number = getNumeric(value);

  return number === null ? "—" : number.toFixed(2);
}

function formatPercent(value) {
  if (value === null || value === undefined || value === "") {
    return "—";
  }

  const number = getNumeric(value);

  return number === null ? "—" : `${number.toFixed(2)}%`;
}

function formatCellValue(value) {
  const number = getNumeric(value);

  if (number === null) return "—";

  return number.toLocaleString("en-IN", {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  });
}

function valueClass(value) {
  const number = getNumeric(value);

  if (number === null || number === 0) return "";
  return number < 0 ? "negative-value" : "positive-value";
}

function summaryLabel(value) {
  if (value === null || value === undefined || value === "") {
    return "—";
  }

  const labels = {
    positive: "Positive",
    negative: "Negative",
    undervalued: "Undervalued",
    overvalued: "Overvalued",
  };

  return labels[String(value).toLowerCase()] || value;
}

function summaryClass(value) {
  const normalized = String(value || "").toLowerCase();

  if (["positive", "undervalued"].includes(normalized)) {
    return "status-positive";
  }

  if (["negative", "overvalued"].includes(normalized)) {
    return "status-negative";
  }

  return "status-neutral";
}

function normalizeAnalysis(value) {
  if (Array.isArray(value)) {
    return {
      trimmean: [],
      median: [],
      average: [],
    };
  }

  return {
    trimmean: asArray(value?.trimmean),
    median: asArray(value?.median),
    average: asArray(value?.average),
  };
}

/*
 * Accepts the preferred nested response:
 * {
 *   yearly_table: { years: [], rows: [] }
 * }
 *
 * Also supports years/rows at the top level and a few common
 * alternative names. This does not generate missing financial data.
 */

function normalizeYearlyTable(json) {
  const table =
    json?.yearly_table ??
    json?.yearlyTable ??
    json?.financial_history ??
    json?.financial_history_table ??
    {};

  const rawYears =
    table.years ??
    table.year_headers ??
    table.columns ??
    json?.years ??
    json?.year_headers ??
    [];

  const years = asArray(rawYears).map((year) => String(year));

  const rawRows =
    table.rows ??
    table.data ??
    json?.yearly_rows ??
    json?.financial_rows ??
    json?.rows ??
    [];

  const sourceRows = Array.isArray(rawRows)
    ? rawRows
    : rawRows && typeof rawRows === "object"
      ? Object.entries(rawRows).map(([key, value]) => ({
          key,
          ...(value && typeof value === "object" ? value : {}),
        }))
      : [];

  const hasTrailing = sourceRows.some((row) => {
    const values =
      row?.values_with_trailing ??
      row?.yearly_values_with_trailing ??
      row?.values ??
      row?.yearly_values ??
      row?.year_values;

    return (
      row?.trailing !== undefined ||
      row?.trailing_value !== undefined ||
      row?.trailingValue !== undefined ||
      row?.trailing_pct !== undefined ||
      (Array.isArray(values) && values.length > years.length)
    );
  });

  // Deduplicate TTM/Trailing headers. Keep TTM if both are present.
  const normalizedYears = [];
  let trailingHeaderAdded = false;

  for (const year of years) {
    const normalized = year.trim().toLowerCase();

    if (normalized === "ttm" || normalized === "trailing") {
      if (!trailingHeaderAdded) {
        normalizedYears.push("TTM");
        trailingHeaderAdded = true;
      }
    } else {
      normalizedYears.push(year);
    }
  }

  if (hasTrailing && !trailingHeaderAdded) {
    normalizedYears.push("TTM");
    trailingHeaderAdded = true;
  }

  // Normalize each row first. Do not reorder rows inside this map.
  const rows = sourceRows.map((row, index) => {
    const key = String(
      row?.key ??
      row?.parameter ??
      row?.base_type ??
      row?.metric ??
      row?.type ??
      row?.name ??
      `Metric ${index + 1}`
    ).trim();

    const rawValues =
      row?.values_with_trailing ??
      row?.yearly_values_with_trailing ??
      row?.values ??
      row?.yearly_values ??
      row?.year_values;

    let values;

    if (Array.isArray(rawValues)) {
      values = [...rawValues];
    } else {
      values = years.map((year) => {
        const candidates = [
          year,
          `y${year}`,
          `y${year.slice(-2)}`,
        ];

        const matchingKey = candidates.find((candidate) =>
          Object.prototype.hasOwnProperty.call(row || {}, candidate)
        );

        return matchingKey !== undefined ? row[matchingKey] : null;
      });
    }

    const trailingValue =
      row?.trailing ??
      row?.trailing_value ??
      row?.trailingValue ??
      null;

    const rawPctValues =
      row?.pct_values_with_trailing ??
      row?.pct_values_with_ttm ??
      row?.pct_values ??
      row?.percentage_values ??
      row?.pctValues ??
      [];

    const pctValues = Array.isArray(rawPctValues)
      ? [...rawPctValues]
      : [];

    // Align values by the original year headers, merging TTM and
    // Trailing into one displayed column.
    const alignedValues = [];
    const alignedPctValues = [];
    let trailingValueAdded = false;

    years.forEach((year, yearIndex) => {
      const normalized = year.trim().toLowerCase();

      if (normalized === "ttm" || normalized === "trailing") {
        if (!trailingValueAdded) {
          const value =
            values[yearIndex] ??
            trailingValue;

          const pct =
            pctValues[yearIndex] ??
            row?.trailing_pct ??
            null;

          alignedValues.push(value);
          alignedPctValues.push(pct);
          trailingValueAdded = true;
        }
      } else {
        alignedValues.push(values[yearIndex] ?? null);
        alignedPctValues.push(pctValues[yearIndex] ?? null);
      }
    });

    // If the API supplies trailing data separately and no TTM header,
    // append it once.
    if (hasTrailing && !trailingValueAdded) {
      alignedValues.push(
        values[years.length] ?? trailingValue
      );

      alignedPctValues.push(
        pctValues[years.length] ??
        row?.trailing_pct ??
        null
      );
    }

    // Keep exactly the number of values needed by the displayed headers.
    while (alignedValues.length < normalizedYears.length) {
      alignedValues.push(null);
    }

    while (alignedPctValues.length < normalizedYears.length) {
      alignedPctValues.push(null);
    }

     return {
      ...row,
      key,
      values: alignedValues,
      pct_values: alignedPctValues,
      stats: row?.stats ?? {},
      pct_stats: row?.pct_stats ?? {},
    };
  });

  // Reorder rows only after rows has been initialized.
  const netProfitIndex = rows.findIndex(
    (row) => row.key.trim().toLowerCase() === "net profit"
  );

  const npmRow = rows.find(
    (row) => row.key.trim().toLowerCase() === "npm"
  );

  const npmChangeRow = rows.find(
    (row) => row.key.trim().toLowerCase() === "npm change"
  );

  if (netProfitIndex !== -1 && (npmRow || npmChangeRow)) {
    const orderedRows = rows.filter(
      (row) =>
        !["npm", "npm change"].includes(
          row.key.trim().toLowerCase()
        )
    );

    const updatedNetProfitIndex = orderedRows.findIndex(
      (row) => row.key.trim().toLowerCase() === "net profit"
    );

    orderedRows.splice(
      updatedNetProfitIndex + 1,
      0,
      ...[npmRow, npmChangeRow].filter(Boolean)
    );

    return {
      years: normalizedYears,
      rows: orderedRows,
    };
  }

  return {
    years: normalizedYears,
    rows,
  };
} // Closes normalizeYearlyTable()

function SectionHeading({ eyebrow, title, description, action }) {
  return (
    <div className="section-heading">
      <div>
        {eyebrow && <div className="section-eyebrow">{eyebrow}</div>}
        <h2>{title}</h2>
        {description && <p>{description}</p>}
      </div>

      {action && <div className="section-heading-action">{action}</div>}
    </div>
  );
}

function Autocomplete({
  label,
  placeholder,
  value,
  items,
  getLabel,
  getSearchText,
  onChange,
  onSelect,
  open,
  setOpen,
  icon,
}) {
  const wrapperRef = useRef(null);
  const [activeIndex, setActiveIndex] = useState(-1);

  const filtered = useMemo(() => {
    const query = String(value || "").trim().toLowerCase();

    return items
      .filter((item) => {
        return !query || getSearchText(item).toLowerCase().includes(query);
      })
      .slice(0, 100);
  }, [items, value, getLabel, getSearchText]);

  useEffect(() => {
    const handleOutside = (event) => {
      if (
        wrapperRef.current &&
        !wrapperRef.current.contains(event.target)
      ) {
        setOpen(false);
        setActiveIndex(-1);
      }
    };

    document.addEventListener("mousedown", handleOutside);

    return () => {
      document.removeEventListener("mousedown", handleOutside);
    };
  }, [setOpen]);

  const choose = (item) => {
    onSelect(item);
    setOpen(false);
    setActiveIndex(-1);
  };

  return (
    <div className="autocomplete-field" ref={wrapperRef}>
      <label>{label}</label>

      <div className={`autocomplete-control ${open ? "is-open" : ""}`}>
        <span className="field-icon" aria-hidden="true">
          {icon}
        </span>

        <input
          type="text"
          value={value}
          placeholder={placeholder}
          autoComplete="off"
          role="combobox"
          aria-expanded={open}
          onFocus={() => setOpen(true)}
          onChange={(event) => {
            onChange(event.target.value);
            setOpen(true);
            setActiveIndex(-1);
          }}
          onKeyDown={(event) => {
            if (event.key === "ArrowDown") {
              event.preventDefault();
              setOpen(true);

              setActiveIndex((index) =>
                Math.min(index + 1, filtered.length - 1)
              );
            }

            if (event.key === "ArrowUp") {
              event.preventDefault();

              setActiveIndex((index) => Math.max(index - 1, 0));
            }

            if (event.key === "Enter" && open && filtered[activeIndex]) {
              event.preventDefault();
              choose(filtered[activeIndex]);
            }

            if (event.key === "Escape") {
              setOpen(false);
              setActiveIndex(-1);
            }
          }}
        />

        <span className="autocomplete-chevron" aria-hidden="true">
          ⌄
        </span>
      </div>

      {open && (
        <div className="autocomplete-menu" role="listbox">
          {filtered.length > 0 ? (
            filtered.map((item, index) => (
              <button
                type="button"
                role="option"
                aria-selected={index === activeIndex}
                className={`autocomplete-option ${
                  index === activeIndex ? "is-active" : ""
                }`}
                key={`${item.symbol || ""}-${item.name || getLabel(item)}-${index}`}
                onMouseDown={(event) => event.preventDefault()}
                onClick={() => choose(item)}
              >
                <span className="option-main">{getLabel(item)}</span>
                <span className="option-meta">{item.symbol || "Select"}</span>
              </button>
            ))
          ) : (
            <div className="autocomplete-empty">
              No matching companies found
            </div>
          )}
        </div>
      )}
    </div>
  );
}

function ValueAnalysisTable({ title, tenure, rows = [] }) {
  if (!Array.isArray(rows) || rows.length === 0) return null;

  return (
    <section className={`data-card value-analysis-card ${tenure}`}>
      <SectionHeading title={title} />

      <div className="table-scroll">
        <table className="data-table value-analysis-table">
          <thead>
            <tr>
              {VALUE_TABLE_COLUMNS.map((column) => (
                <th key={column}>{column}</th>
              ))}
            </tr>
          </thead>

          <tbody>
            {rows.map((row, index) => (
              <tr key={`${row.year ?? "year"}-${index}`}>
                <td>{row.year ?? "—"}</td>
                <td className={valueClass(row.eps)}>
                  {formatFixed(row.eps)}
                </td>
                <td className={valueClass(row.target_eps)}>
                  {formatFixed(row.target_eps)}
                </td>
                <td className={valueClass(row.target_price)}>
                  {formatFixed(row.target_price)}
                </td>
                <td className={valueClass(row.yoy_return)}>
                  {formatPercent(row.yoy_return)}
                </td>
                <td className={valueClass(row.forecasted_return)}>
                  {formatPercent(row.forecasted_return)}
                </td>
                <td>{row.holding_period ?? "—"}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
}

function getStatistic(stats, period, method) {
  return stats?.[period]?.[method] ?? null;
}

function FinancialHistoryTable({ years = [], rows = [] }) {
  const [showPercentages, setShowPercentages] = useState(true);

  const safeYears = asArray(years);
  const safeRows = asArray(rows);

  // Supports common API variants without calculating new statistics.
  const getStats = (row, isPercentage = false) => {
    if (isPercentage) {
      return (
        row?.pct_stats ??
        row?.percentage_stats ??
        row?.pctStats ??
        {}
      );
    }

    return (
      row?.stats ??
      row?.summary_stats ??
      row?.statistics ??
      {}
    );
  };

const formatMetricValue = (value, isPercent) => {
  const number = getNumeric(value);

  if (number === null) return "—";

  return isPercent
    ? `${number.toFixed(2)}%`
    : formatNumber(number);
};

  const getSummaryValue = (stats, period, method) => {
    // The expected format is stats["5y"].average, etc.
    // Do not manufacture statistics when the API omits them.
    return (
      stats?.[period]?.[method] ??
      stats?.[period === "10y" ? "10_years" : "5_years"]?.[method] ??
      null
    );
  };

  return (
    <section className="data-card yearly-metrics-card">
      <SectionHeading
        eyebrow="FINANCIAL HISTORY"
        title="Yearly balance sheet metrics"
        description="Annual reported values, percentage changes, and 5-year / 10-year summary statistics."
        action={
          <span className="table-count">
            {safeYears.length} columns
          </span>
        }
      />

      <div className="financial-history-controls">
        <span>
          {safeRows.length} financial metrics · {safeYears.length} columns
        </span>

        <label className="percentage-toggle">
          <input
            type="checkbox"
            checked={showPercentages}
            onChange={(event) =>
              setShowPercentages(event.target.checked)
            }
          />
          Show percentage changes
        </label>
      </div>

      {safeYears.length === 0 ? (
        <div className="inline-empty">
          No years were returned by the yearly metrics API.
        </div>
      ) : safeRows.length === 0 ? (
        <div className="inline-empty">
          Years were received, but no financial metric rows were received.
          Check the structure of yearly_table.rows in the API response.
        </div>
      ) : (
        <div className="table-scroll yearly-table-scroll">
          <table className="data-table yearly-table">
            <thead>
              <tr>
                <th className="sticky-first-col">Parameters</th>

                {safeYears.map((year, index) => (
                  <th
                    key={`${year}-${index}`}
                    className={
                      String(year).toLowerCase() === "trailing"
                        ? "trailing-col"
                        : ""
                    }
                  >
                    {year}
                  </th>
                ))}

                <th colSpan={3} className="ten-year-heading">
                  10 year
                </th>

                <th colSpan={3} className="five-year-heading">
                  5 year
                </th>
              </tr>

              <tr>
                <th className="sticky-first-col">Metric / statistic</th>

                {safeYears.map((year, index) => (
                  <th
                    key={`value-${year}-${index}`}
                    className={
                      String(year).toLowerCase() === "trailing"
                        ? "trailing-col"
                        : ""
                    }
                  >
                    Value
                  </th>
                ))}

                {METHODS.map((method) => (
                  <th key={`10-${method}`} className="ten-year-col">
                    {method === "trimmean"
                      ? "Trim mean"
                      : method.charAt(0).toUpperCase() + method.slice(1)}
                  </th>
                ))}

                {METHODS.map((method) => (
                  <th key={`5-${method}`} className="five-year-col">
                    {method === "trimmean"
                      ? "Trim mean"
                      : method.charAt(0).toUpperCase() + method.slice(1)}
                  </th>
                ))}
              </tr>
            </thead>

            <tbody>
              {safeRows.map((row, rowIndex) => {
                const key = String(
                  row?.key || `Metric ${rowIndex + 1}`
                ).trim();

                const normalizedKey = key.toLowerCase();

                // Continue hiding ROCE, as in your original component.
                if (normalizedKey === "roce") {
                  return null;
                }

                // NPM change duplicates the NPM % change row.
                // Keep the NPM metric and its percentage-change row only.
                
                const isPercentRow = [
                  "opm",
                  "npm",
                  "roe",
                ].includes(normalizedKey);

                const isNetProfit = normalizedKey === "net profit";

                const values = safeYears.map(
                  (_, index) => row?.values?.[index] ?? null
                );

                const pctValues = safeYears.map(
                  (_, index) => row?.pct_values?.[index] ?? null
                );

                const stats = getStats(row, false);
                const pctStats = getStats(row, true);

                const renderSummaryCells = (
                  statsObject,
                  isPercent
                ) => (
                  <>
                    {METHODS.map((method) => {
                      const value = getSummaryValue(
                        statsObject,
                        "10y",
                        method
                      );

                      return (
                        <td
                          key={`10-${method}`}
                          className={`ten-year-col ${valueClass(value)}`}
                        >
                          {formatMetricValue(value, isPercent)}
                        </td>
                      );
                    })}

                    {METHODS.map((method) => {
                      const value = getSummaryValue(
                        statsObject,
                        "5y",
                        method
                      );

                      return (
                        <td
                          key={`5-${method}`}
                          className={`five-year-col ${valueClass(value)}`}
                        >
                          {formatMetricValue(value, isPercent)}
                        </td>
                      );
                    })}
                  </>
                );

                return (
                  <Fragment key={`${key}-${rowIndex}`}>
                    <tr className="metric-row">
                      <td className="sticky-first-col metric-name">
                        {key}
                      </td>

                      {values.map((value, index) => (
                        <td
                          key={`value-${index}`}
                          className={[
                            valueClass(value),
                            String(safeYears[index]).toLowerCase() ===
                            "trailing"
                              ? "trailing-col"
                              : "",
                          ].join(" ")}
                        >
                          {formatMetricValue(value, isPercentRow)}
                        </td>
                      ))}

                      {renderSummaryCells(stats, isPercentRow)}
                    </tr>

                    {showPercentages &&
  !isNetProfit &&
  !["npm", "npm change"].includes(normalizedKey) && (
                      <tr className="percentage-row">
                        <td className="sticky-first-col">
                          {key} % change
                        </td>

                        {pctValues.map((value, index) => (
                          <td
                            key={`pct-${index}`}
                            className={[
                              valueClass(value),
                              String(safeYears[index]).toLowerCase() ===
                              "trailing"
                                ? "trailing-col"
                                : "",
                            ].join(" ")}
                          >
                            {formatMetricValue(value, true)}
                          </td>
                        ))}

                        {renderSummaryCells(pctStats, true)}
                      </tr>
                    )}
                  </Fragment>
                );
              })}
            </tbody>
          </table>
        </div>
      )}
    </section>
  );
}

export default function YearlyBalanceSheet() {
  const [company, setCompany] = useState("");
  const [symbol, setSymbol] = useState("");
  const [companies, setCompanies] = useState([]);
  const [expectedReturn, setExpectedReturn] = useState(30);

  const [loading, setLoading] = useState(false);
  const [companiesLoading, setCompaniesLoading] = useState(true);

  const [showCompanyList, setShowCompanyList] = useState(false);
  const [showSymbolList, setShowSymbolList] = useState(false);

  const [error, setError] = useState("");
  const [data, setData] = useState(initialData);

  const requestId = useRef(0);

  useEffect(() => {
    const controller = new AbortController();

    async function loadCompanies() {
      setCompaniesLoading(true);

      try {
        const response = await fetch(`${API_BASE}/companies/`, {
          signal: controller.signal,
        });

        if (!response.ok) {
          throw new Error(`Could not load companies (${response.status})`);
        }

        const json = await response.json();

        const list = Array.isArray(json) ? json : json.results || [];
        setCompanies(list);
      } catch (fetchError) {
        if (fetchError.name !== "AbortError") {
          setError(
            `Unable to load the company list. ${fetchError.message}`
          );
        }
      } finally {
        if (!controller.signal.aborted) {
          setCompaniesLoading(false);
        }
      }
    }

    loadCompanies();

    return () => controller.abort();
  }, []);

  const selectedCompany = useMemo(
    () =>
      companies.find(
        (item) => item.symbol === symbol && item.name === company
      ),
    [companies, company, symbol]
  );

  const fetchMetrics = useCallback(async () => {
    if (!company.trim() || !symbol.trim()) {
      setError(
        "Select a company and symbol from the suggestions before loading data."
      );
      return;
    }

    const currentRequest = ++requestId.current;

    setLoading(true);
    setError("");

    try {
      const metricsUrl =
        `${API_BASE}/yearly-metrics/` +
        `?symbol=${encodeURIComponent(symbol)}` +
        `&expected_return=${expectedReturn}`;

      const mcapUrl =
        `${API_BASE}/equities-with-mcap/` +
        `?symbol=${encodeURIComponent(symbol)}`;

      const [metricsResponse, mcapResponse] = await Promise.all([
        fetch(metricsUrl),
        fetch(mcapUrl),
      ]);

      if (!metricsResponse.ok) {
        throw new Error(
          `Yearly metrics request failed (${metricsResponse.status})`
        );
      }

      if (!mcapResponse.ok) {
        throw new Error(
          `Market-cap request failed (${mcapResponse.status})`
        );
      }

      const [metricsJson, mcapJson] = await Promise.all([
        metricsResponse.json(),
        mcapResponse.json(),
      ]);

      if (currentRequest !== requestId.current) return;

      console.log("Yearly metrics API response:", metricsJson);

      const mcapList = Array.isArray(mcapJson)
        ? mcapJson
        : mcapJson.results || [];

      const mcapData =
        mcapList.find((item) => item.symbol === symbol)?.mcap || null;

      const info = metricsJson.company_info || {};

      const companyInfo = selectedCompany
        ? {
            company_name: selectedCompany.name,
            symbol: selectedCompany.symbol,
            isin_number: selectedCompany.isin,
            sector: selectedCompany.sector,
            sub_sector_1: selectedCompany.sub_sector_1,
            sub_sector_2: selectedCompany.sub_sector_2,
            industry: selectedCompany.industry,
          }
        : {};

      const yearlyTable = normalizeYearlyTable(metricsJson);

      console.log("Normalized financial history:", yearlyTable);
      console.log("Year headings:", yearlyTable.years);
      console.log("Financial history rows:", yearlyTable.rows);

      setData({
        ...initialData,
        ...companyInfo,
        ...info,

        company_name:
          info.company_name || companyInfo.company_name || company,
        symbol: info.symbol || companyInfo.symbol || symbol,

        mcap: mcapData,

        metric_summary: asArray(metricsJson.metric_summary),
        balance_stats: asArray(metricsJson.balance_stats),

        value_analysis_10y: normalizeAnalysis(
          metricsJson.value_analysis_10y
        ),

        value_analysis_5y: normalizeAnalysis(
          metricsJson.value_analysis_5y
        ),

        growth: asArray(metricsJson.growth),
        final_analysis_table: asArray(metricsJson.final_analysis_table),

        summary_conditions: metricsJson.summary_conditions || {},

        years: yearlyTable.years,
        rows: yearlyTable.rows,
      });
    } catch (fetchError) {
      if (currentRequest === requestId.current) {
        setError(`Unable to load stock analysis. ${fetchError.message}`);
      }
    } finally {
      if (currentRequest === requestId.current) {
        setLoading(false);
      }
    }
  }, [company, symbol, expectedReturn, selectedCompany]);

  useEffect(() => {
    if (selectedCompany) {
      fetchMetrics();
    }
  }, [selectedCompany, expectedReturn, fetchMetrics]);

  const growthAnalysis = useMemo(() => {
    const growthData = data.summary_conditions?.growth_analysis || {};

    return Object.fromEntries(
      Object.entries(growthData).map(([key, metric]) => [
        key,
        {
          trimmean: { status: metric?.trimmean },
          median: { status: metric?.median },
          average: { status: metric?.average },
        },
      ])
    );
  }, [data.summary_conditions]);

  const valueAnalysisConclusion = useMemo(
    () =>
      data.final_analysis_table.find(
        (row) => row.Analysis_Tenure === "Value Analysis Conclusion"
      ),
    [data.final_analysis_table]
  );

  const targetPriceFromAnalysis = useMemo(() => {
    const row = data.final_analysis_table.find(
      (item) => item.Analysis_Tenure === "Target"
    );

    return getNumeric(row?.Recommendation);
  }, [data.final_analysis_table]);

  const hasData = Boolean(
    data.company_name ||
      data.rows.length ||
      data.final_analysis_table.length
  );

  const handleCompanySelect = (item) => {
    setCompany(item.name || "");
    setSymbol(item.symbol || "");
    setShowCompanyList(false);
    setShowSymbolList(false);
  };

  const handleCompanyChange = (value) => {
    setCompany(value);

    const exact = companies.find(
      (item) => item.name?.toLowerCase() === value.trim().toLowerCase()
    );

    setSymbol(exact?.symbol || "");
  };

  const handleSymbolChange = (value) => {
    const normalized = value.toUpperCase();

    setSymbol(normalized);

    const exact = companies.find(
      (item) => item.symbol?.toLowerCase() === value.trim().toLowerCase()
    );

    setCompany(exact?.name || "");
  };

  return (
    <main className="yearly-container">
      <header className="dashboard-hero">
        <div className="hero-copy">
          <div className="hero-eyebrow">
            <span className="hero-dot" />
            EQUITY RESEARCH WORKSPACE
          </div>

          <h1>Yearly Balance Sheet</h1>

          <p>
            Review financial performance, growth trends, valuation signals,
            and price targets in one place.
          </p>
        </div>

        <div className="hero-mark" aria-hidden="true">
          <span>₹</span>
          <i>↗</i>
        </div>
      </header>

      <section className="filter-panel">
        <div className="filter-panel-heading">
          <div>
            <span className="panel-kicker">ANALYSIS SETUP</span>
            <h2>Find a company</h2>
          </div>

          <span className="data-source-note">
            <span className="status-dot" />
            Local market data
          </span>
        </div>

        <div className="filter-grid">
          <Autocomplete
            label="Company name"
            placeholder="Search by company name"
            value={company}
            items={companies}
            getLabel={(item) => item.name || ""}
            getSearchText={(item) =>
              `${item.name || ""} ${item.symbol || ""}`
            }
            onChange={handleCompanyChange}
            onSelect={handleCompanySelect}
            open={showCompanyList}
            setOpen={setShowCompanyList}
            icon="⌕"
          />

          <Autocomplete
            label="Trading symbol"
            placeholder="Search by symbol"
            value={symbol}
            items={companies}
            getLabel={(item) => item.symbol || ""}
            getSearchText={(item) =>
              `${item.symbol || ""} ${item.name || ""}`
            }
            onChange={handleSymbolChange}
            onSelect={handleCompanySelect}
            open={showSymbolList}
            setOpen={setShowSymbolList}
            icon="#"
          />

          <div className="return-field">
            <label htmlFor="expected-return">Expected return (YoY)</label>

            <div className="select-control">
              <span className="field-icon">%</span>

              <select
                id="expected-return"
                value={expectedReturn}
                onChange={(event) =>
                  setExpectedReturn(Number(event.target.value))
                }
              >
                {EXPECTED_RETURN_OPTIONS.map((value) => (
                  <option key={value} value={value}>
                    {value}%
                  </option>
                ))}
              </select>

              <span className="select-chevron">⌄</span>
            </div>
          </div>

          <button
            className="primary-button"
            type="button"
            onClick={fetchMetrics}
            disabled={loading || companiesLoading}
          >
            {loading ? (
              <>
                <span className="button-spinner" />
                Loading
              </>
            ) : (
              <>
                <span aria-hidden="true">↗</span>
                Load analysis
              </>
            )}
          </button>
        </div>

        <div className="filter-footer">
          <span>
            {companiesLoading
              ? "Loading company directory…"
              : `${companies.length.toLocaleString("en-IN")} companies available`}
          </span>

          <span>
            Changing expected return refreshes the analysis automatically.
          </span>
        </div>
      </section>

      {error && (
        <div className="feedback-message error-message" role="alert">
          <span>!</span>

          <div>
            <strong>Something went wrong</strong>
            <p>{error}</p>
          </div>

          <button
            type="button"
            onClick={() => setError("")}
            aria-label="Dismiss error"
          >
            ×
          </button>
        </div>
      )}

      {loading && (
        <div className="loading-panel">
          <span className="loading-spinner" />

          <div>
            <strong>Preparing your analysis</strong>
            <p>Retrieving yearly metrics and market data…</p>
          </div>
        </div>
      )}

      {!hasData && !loading && !error && (
        <div className="empty-state">
          <div className="empty-icon">⌕</div>
          <h2>Your analysis will appear here</h2>
          <p>
            Select a company and trading symbol, then load the data to view
            financial metrics and valuation tables.
          </p>
        </div>
      )}

      {hasData && (
        <>
          <section className="overview-section">
            <SectionHeading
              eyebrow="COMPANY OVERVIEW"
              title={data.company_name || company}
              description="Company profile and key market indicators."
            />

            <div className="overview-grid">
              <div className="data-card company-profile-card">
                <div className="company-identity">
                  <div className="company-avatar">
                    {(data.company_name || company || "C")
                      .trim()
                      .charAt(0)
                      .toUpperCase()}
                  </div>

                  <div>
                    <h3>{data.company_name || company || "—"}</h3>
                    <span className="symbol-chip">
                      {data.symbol || symbol || "—"}
                    </span>
                  </div>
                </div>

                <div className="profile-list">
                  <div>
                    <span>ISIN number</span>
                    <strong>{data.isin_number || "—"}</strong>
                  </div>

                  <div>
                    <span>Sector</span>
                    <strong>{data.sector || "—"}</strong>
                  </div>

                  <div>
                    <span>Sub-sector 1</span>
                    <strong>{data.sub_sector_1 || "—"}</strong>
                  </div>

                  <div>
                    <span>Sub-sector 2</span>
                    <strong>{data.sub_sector_2 || "—"}</strong>
                  </div>

                  <div>
                    <span>Industry</span>
                    <strong>{data.industry || "—"}</strong>
                  </div>
                </div>
              </div>

              <div className="data-card market-card">
                <div className="market-card-heading">
                  <div>
                    <span className="panel-kicker">MARKET SNAPSHOT</span>
                    <h3>Trading metrics</h3>
                  </div>

                  <span className="market-icon">◈</span>
                </div>

                {data.mcap ? (
                  <div className="market-metrics">
                    <div className="market-metric featured-metric">
                      <span>Market capitalisation</span>

                      <strong>
                        {formatNumber(data.mcap.market_cap)}
                      </strong>

                      <small>
                        {data.mcap.company_size || "Company size unavailable"}
                      </small>
                    </div>

                    <div className="market-metric">
                      <span>Stock P/E</span>
                      <strong>{formatNumber(data.mcap.stock_pe)}</strong>
                    </div>

                    <div className="market-metric">
                      <span>Industry P/E</span>
                      <strong>{formatNumber(data.mcap.industry_pe)}</strong>
                    </div>

                    <div className="market-metric">
                      <span>Stock price</span>
                      <strong>
                        {data.mcap.share_price != null
                          ? `₹${formatNumber(data.mcap.share_price)}`
                          : "—"}
                      </strong>
                    </div>

                    <div className="market-metric">
                      <span>Expected return</span>
                      <strong>
                        {expectedReturn}% <small>YoY</small>
                      </strong>
                    </div>

                    <div className="market-metric">
                      <span>Value analysis</span>
                      <strong
                        className={summaryClass(
                          valueAnalysisConclusion?.Recommendation
                        )}
                      >
                        {summaryLabel(
                          valueAnalysisConclusion?.Recommendation
                        )}
                      </strong>
                    </div>
                  </div>
                ) : (
                  <div className="market-empty">
                    Market-cap data is not available for this symbol.
                  </div>
                )}
              </div>
            </div>
          </section>

          {Object.keys(data.summary_conditions || {}).length > 0 && (
            <section className="summary-section">
              <SectionHeading
                eyebrow="AT A GLANCE"
                title="Analysis summary"
                description="A concise view of valuation conditions and growth signals."
              />

              <div className="summary-grid">
                <div className="data-card summary-card">
                  <div className="card-heading">
                    <div>
                      <span className="card-icon">◉</span>
                      <h3>Valuation summary</h3>
                    </div>
                  </div>

                  <div className="table-scroll">
                    <table className="data-table summary-table">
                      <thead>
                        <tr>
                          <th>Parameter</th>
                          <th>Result</th>
                        </tr>
                      </thead>

                      <tbody>
                        <tr>
                          <td>Valuation</td>
                          <td>
                            <span
                              className={`status-pill ${summaryClass(
                                data.summary_conditions.valuation
                              )}`}
                            >
                              {summaryLabel(
                                data.summary_conditions.valuation
                              )}
                            </span>
                          </td>
                        </tr>

                        <tr>
                          <td>Valuation analysis conclusion</td>
                          <td>
                            <span
                              className={`status-pill ${summaryClass(
                                data.summary_conditions.value_analysis_conclusion
                              )}`}
                            >
                              {summaryLabel(
                                data.summary_conditions.value_analysis_conclusion
                              )}
                            </span>
                          </td>
                        </tr>

                        <tr>
                          <td>Target price for entry</td>
                          <td>
                            <div className="target-entry">
                              <span
                                className={`status-pill ${summaryClass(
                                  data.summary_conditions
                                    ?.target_price_for_entry?.status
                                )}`}
                              >
                                {summaryLabel(
                                  data.summary_conditions
                                    ?.target_price_for_entry?.status
                                )}
                              </span>

                              <strong>
                                {targetPriceFromAnalysis != null
                                  ? `₹${targetPriceFromAnalysis.toFixed(2)}`
                                  : "—"}
                              </strong>
                            </div>
                          </td>
                        </tr>

                        <tr>
                          <td>Stock P/E vs industry P/E</td>
                          <td>
                            <span
                              className={`status-pill ${summaryClass(
                                data.summary_conditions.stock_pe_vs_industry_pe
                              )}`}
                            >
                              {summaryLabel(
                                data.summary_conditions.stock_pe_vs_industry_pe
                              )}
                            </span>
                          </td>
                        </tr>
                      </tbody>
                    </table>
                  </div>
                </div>

                <div className="data-card growth-summary-card">
                  <div className="card-heading">
                    <div>
                      <span className="card-icon">↗</span>
                      <h3>
                        Growth summary <span>(YoY)</span>
                      </h3>
                    </div>
                  </div>

                  <div className="table-scroll">
                    <table className="data-table summary-table centered-table">
                      <thead>
                        <tr>
                          <th>Parameter</th>
                          <th>Trim mean</th>
                          <th>Median</th>
                          <th>Average</th>
                        </tr>
                      </thead>

                      <tbody>
                        {GROWTH_ROWS.map((row) => {
                          const metric = growthAnalysis[row.key] || {};

                          return (
                            <tr key={row.key}>
                              <td>{row.label}</td>

                              {METHODS.map((method) => (
                                <td key={method}>
                                  <span
                                    className={`status-pill ${summaryClass(
                                      metric[method]?.status
                                    )}`}
                                  >
                                    {summaryLabel(
                                      metric[method]?.status
                                    )}
                                  </span>
                                </td>
                              ))}
                            </tr>
                          );
                        })}
                      </tbody>
                    </table>
                  </div>
                </div>
              </div>
            </section>
          )}

          {data.final_analysis_table.length > 0 && (
            <section className="data-card analysis-card">
              <SectionHeading
                eyebrow="VALUATION MODEL"
                title="Stock analysis & price targets"
                description="Recommendations grouped by analysis tenure and method."
              />

              <div className="table-scroll">
                <table className="data-table recommendation-table">
                  <thead>
                    <tr>
                      <th>Analysis tenure</th>
                      <th>Method</th>
                      <th>Recommendation</th>
                      <th>Target price for entry</th>
                      <th>Average tenure-wise</th>
                    </tr>
                  </thead>

                  <tbody>
                    {(() => {
                      const rows = data.final_analysis_table;

                      const conclusion = rows.find(
                        (row) =>
                          row.Analysis_Tenure === "Value Analysis Conclusion"
                      );

                      const target = rows.find(
                        (row) => row.Analysis_Tenure === "Target"
                      );

                      const normalRows = rows.filter(
                        (row) =>
                          ![
                            "Value Analysis Conclusion",
                            "Target",
                          ].includes(row.Analysis_Tenure)
                      );

                      const groups = new Map();

                      normalRows.forEach((row) => {
                        const tenure = row.Analysis_Tenure || "Unknown";

                        if (!groups.has(tenure)) {
                          groups.set(tenure, []);
                        }

                        groups.get(tenure).push(row);
                      });

                      const rendered = [];

                      groups.forEach((groupRows, tenure) => {
                        groupRows.forEach((row, index) => {
                          rendered.push(
                            <tr
                              key={`${expectedReturn}-${tenure}-${index}`}
                            >
                              {index === 0 && (
                                <td
                                  rowSpan={groupRows.length}
                                  className="grouped-cell"
                                >
                                  {tenure}
                                </td>
                              )}

                              <td>{row.Method || "—"}</td>
                              <td>{row.Recommendation ?? "—"}</td>

                              <td
                                className={valueClass(
                                  row.Target_Price_for_Entry
                                )}
                              >
                                {row.Target_Price_for_Entry != null
                                  ? formatFixed(row.Target_Price_for_Entry)
                                  : "—"}
                              </td>

                              {index === 0 && (
                                <td
                                  rowSpan={groupRows.length}
                                  className={`grouped-cell ${valueClass(
                                    row.Average_Tenure_wise
                                  )}`}
                                >
                                  {formatFixed(row.Average_Tenure_wise)}
                                </td>
                              )}
                            </tr>
                          );
                        });
                      });

                      if (conclusion) {
                        rendered.push(
                          <tr className="conclusion-row" key="conclusion">
                            <td colSpan={2}>Value Analysis Conclusion</td>
                            <td>{conclusion.Recommendation ?? "—"}</td>

                            <td
                              className={valueClass(
                                conclusion.Target_Price_for_Entry
                              )}
                            >
                              {formatFixed(
                                conclusion.Target_Price_for_Entry
                              )}
                            </td>

                            <td
                              className={valueClass(
                                conclusion.Average_Tenure_wise
                              )}
                            >
                              {formatFixed(conclusion.Average_Tenure_wise)}
                            </td>
                          </tr>
                        );
                      }

                      if (target) {
                        rendered.push(
                          <tr className="target-row" key="target">
                            <td colSpan={2}>Target</td>

                            <td>
                              {getNumeric(target.Recommendation) !== null
                                ? `₹${formatFixed(target.Recommendation)}`
                                : "—"}
                            </td>

                            <td>—</td>
                            <td>—</td>
                          </tr>
                        );
                      }

                      return rendered;
                    })()}
                  </tbody>
                </table>
              </div>
            </section>
          )}

          {data.growth.length > 0 && (
            <section className="data-card growth-detail-card">
              <SectionHeading
                eyebrow="HISTORICAL PERFORMANCE"
                title="Growth analysis"
                description="5-year, 10-year, and total-average growth statistics."
              />

              <div className="table-scroll">
                <table className="data-table growth-detail-table">
                  <thead>
                    <tr>
                      <th rowSpan={2}>Parameter</th>
                      <th colSpan={3}>5 years</th>
                      <th colSpan={3}>10 years</th>
                      <th colSpan={3}>Total average</th>
                    </tr>

                    <tr>
                      {[
                        "Trim mean",
                        "Median",
                        "Average",
                        "Trim mean",
                        "Median",
                        "Average",
                        "Trim mean",
                        "Median",
                        "Average",
                      ].map((heading, index) => (
                        <th key={`${heading}-${index}`}>{heading}</th>
                      ))}
                    </tr>
                  </thead>

                  <tbody>
                    {data.growth
                      .filter(
                        (row) =>
                          String(row.parameter || "").toLowerCase() !==
                          "net profit"
                      )
                      .map((row, index) => (
                        <tr key={`${row.parameter}-${index}`}>
                          <td>{row.parameter || "—"}</td>

                          {[
                            ["5y", "trimmean"],
                            ["5y", "median"],
                            ["5y", "average"],
                            ["10y", "trimmean"],
                            ["10y", "median"],
                            ["10y", "average"],
                            ["total_average", "trimmean"],
                            ["total_average", "median"],
                            ["total_average", "average"],
                          ].map(([period, method]) => {
                            const value = row[period]?.[method];

                            return (
                              <td
                                key={`${period}-${method}`}
                                className={valueClass(value)}
                              >
                                {value == null
                                  ? "—"
                                  : formatPercent(value)}
                              </td>
                            );
                          })}
                        </tr>
                      ))}
                  </tbody>
                </table>
              </div>
            </section>
          )}

          <FinancialHistoryTable
            years={data.years}
            rows={data.rows}
          />

          <section className="value-analysis-section">
            <div className="value-analysis-section-heading">
              <SectionHeading
                eyebrow="PRICE FORECASTS"
                title="Value analysis tables"
                description={`Forecast calculations using the selected ${expectedReturn}% expected yearly return.`}
              />
            </div>

            <div className="value-analysis-grid">
              <ValueAnalysisTable
                title="Trim mean · 10 years"
                tenure="ten-year"
                rows={data.value_analysis_10y.trimmean}
              />

              <ValueAnalysisTable
                title="Median · 10 years"
                tenure="ten-year"
                rows={data.value_analysis_10y.median}
              />

              <ValueAnalysisTable
                title="Average · 10 years"
                tenure="ten-year"
                rows={data.value_analysis_10y.average}
              />

              <ValueAnalysisTable
                title="Trim mean · 5 years"
                tenure="five-year"
                rows={data.value_analysis_5y.trimmean}
              />

              <ValueAnalysisTable
                title="Median · 5 years"
                tenure="five-year"
                rows={data.value_analysis_5y.median}
              />

              <ValueAnalysisTable
                title="Average · 5 years"
                tenure="five-year"
                rows={data.value_analysis_5y.average}
              />
            </div>

            {!data.value_analysis_10y.trimmean.length &&
              !data.value_analysis_10y.median.length &&
              !data.value_analysis_10y.average.length &&
              !data.value_analysis_5y.trimmean.length &&
              !data.value_analysis_5y.median.length &&
              !data.value_analysis_5y.average.length && (
                <div className="inline-empty">
                  No value-analysis forecast rows are available for this
                  selection.
                </div>
              )}
          </section>
        </>
      )}

      <footer className="dashboard-footer">
        <span>Equity Research Workspace</span>
        <span>
          Review source data before making investment decisions.
        </span>
      </footer>
    </main>
  );
}