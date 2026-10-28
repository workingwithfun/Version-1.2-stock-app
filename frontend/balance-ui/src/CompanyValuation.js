import React, { useState } from "react";
import { toast } from "react-toastify";
import IndustryValuationChart from "./IndustryValuationChart";
  import * as XLSX from "xlsx";
import { saveAs } from "file-saver";
const DEFAULT_YOY = 30;
const EXPECTED_YOY_OPTIONS = [10,20,30,40,50, 75, 100,125,150,175,200,225,250]; // predefined options

const CompanyValuation = () => {
  const [companySearch, setCompanySearch] = useState("");
const [pageSize, setPageSize] = useState(10);

const PAGE_SIZE_OPTIONS = [10, 25, 50, 100];
  const [equities, setEquities] = useState([]);
  const [expectedYOY, setExpectedYOY] = useState(DEFAULT_YOY);
  const [valuation, setValuation] = useState("");
  const [currentPage, setCurrentPage] = useState(1);
  const [loading, setLoading] = useState(false);
  const [hasSearched, setHasSearched] = useState(false);
const [industryStats, setIndustryStats] = useState(null);
const [columnFilters, setColumnFilters] = useState({
  companyName: "",
  companySize: null,
  sector: null,
  industry: null
});

const companyNames = React.useMemo(() => {
  return [...new Set(
    equities
      .map(e => e.company_name)
      .filter(Boolean)
  )].sort();
}, [equities]);

const [activeFilterColumn, setActiveFilterColumn] = useState(null);

const sectors = React.useMemo(() => {
  return [...new Set(equities.map(e => e.sector).filter(Boolean))];
}, [equities]);

const industries = React.useMemo(() => {
  return [...new Set(equities.map(e => e.industry).filter(Boolean))];
}, [equities]);


  // -----------------------
  // Fetch equities with selected filters
  // -----------------------

const fetchEquitiesWithMCAP = async () => {
  if (!valuation) {
    toast.warn("Please select valuation first.");
    return;
  }

  setLoading(true);

  const start = performance.now();

  try {
    const params = new URLSearchParams({
      expected_yoy: String(expectedYOY),
      valuation,
    });

    const response = await fetch(
      `http://localhost:8000/api/equities-with-mcap-filtered/?${params}`
    );

    const headersReceived = performance.now();

    if (!response.ok) {
      throw new Error(`HTTP ${response.status}`);
    }

    // Read the response body as text to measure download separately.
    const responseText = await response.text();
    const bodyDownloaded = performance.now();

    // Measure JSON parsing independently.
    const data = JSON.parse(responseText);
    const jsonParsed = performance.now();

    // Preserve expectedYOY for components that need it.
    const enrichedData = data.map((eq) => ({
      ...eq,
      expectedYOY,
    }));

    const processingDone = performance.now();

    setEquities(enrichedData);
    setCurrentPage(1);
    setHasSearched(true);

    console.table({
      "Time to response headers":
        `${(headersReceived - start).toFixed(0)} ms`,
      "Response body download":
        `${(bodyDownloaded - headersReceived).toFixed(0)} ms`,
      "JSON parsing":
        `${(jsonParsed - bodyDownloaded).toFixed(0)} ms`,
      "Frontend mapping":
        `${(processingDone - jsonParsed).toFixed(0)} ms`,
      "Total elapsed":
        `${(processingDone - start).toFixed(0)} ms`,
      "Response size":
        `${(new Blob([responseText]).size / 1024).toFixed(1)} KB`,
      "Rows returned": data.length,
    });
  } catch (err) {
    console.error("Equities fetch failed:", err);
    toast.error("Failed to fetch equity + MCAP data.");
  } finally {
    setLoading(false);
  }
};

const fetchIndustryStats = async () => {
  try {
    const params = new URLSearchParams({
      expected_yoy: expectedYOY,
    });

    const res = await fetch(
      `http://localhost:8000/api/industry-valuation-stats/?${params}`
    );

    const data = await res.json();
    setIndustryStats(data);
  } catch (err) {
    toast.error("Failed to fetch industry valuation stats");
  }
};

const applyFilters = async () => {
  await fetchEquitiesWithMCAP();
  await fetchIndustryStats();
};

  // -----------------------
  // Pagination
  // -----------------------
const filteredRows = React.useMemo(() => {
  return equities.filter((eq) => {
    // Company name
    if (
      columnFilters.companyName &&
      !eq.company_name?.toLowerCase().includes(
        columnFilters.companyName.toLowerCase()
      )
    ) {
      return false;
    }

    // Company size
    if (columnFilters.companySize) {
      const size = eq.company_size?.toLowerCase();

      if (!size) return false;

      if (
        (columnFilters.companySize === "SMALL" &&
          !size.includes("small")) ||
        (columnFilters.companySize === "MID" &&
          !size.includes("mid")) ||
        (columnFilters.companySize === "LARGE" &&
          !size.includes("large"))
      ) {
        return false;
      }
    }

    // Sector
    if (
      columnFilters.sector &&
      eq.sector !== columnFilters.sector
    ) {
      return false;
    }

    // Industry
    if (
      columnFilters.industry &&
      eq.industry !== columnFilters.industry
    ) {
      return false;
    }

    return true;
  });
}, [equities, columnFilters]);

const totalPages = Math.max(
  1,
  Math.ceil(filteredRows.length / pageSize)
);

// Keep the page valid if filtering reduces the result count.
React.useEffect(() => {
  setCurrentPage((page) => Math.min(page, totalPages));
}, [totalPages]);

// Return to page 1 when the filters or page size change.
React.useEffect(() => {
  setCurrentPage(1);
}, [columnFilters, pageSize]);

const currentRows = React.useMemo(() => {
  const startIndex = (currentPage - 1) * pageSize;

  return filteredRows.slice(startIndex, startIndex + pageSize);
}, [filteredRows, currentPage, pageSize]);

const startItem = filteredRows.length
  ? (currentPage - 1) * pageSize + 1
  : 0;

const endItem = Math.min(
  currentPage * pageSize,
  filteredRows.length
);

const getPageNumbers = () => {
  const pages = [];
  const start = Math.max(1, currentPage - 2);
  const end = Math.min(totalPages, currentPage + 2);

  for (let page = start; page <= end; page++) {
    pages.push(page);
  }

  return pages;
};

const FilterableHeader = ({ label, columnKey }) => (
  <th className="filterable-th">
    <div className="th-filter">
      <span>{label}</span>

      <span
        className="filter-icon-wrapper"
        onClick={(e) => {
          e.stopPropagation();
          setActiveFilterColumn(
            activeFilterColumn === columnKey ? null : columnKey
          );
        }}
      >
        🔍

        <div
          className={`column-filter-popover ${
            activeFilterColumn === columnKey ? "visible" : "hidden"
          }`}
          onClick={(e) => e.stopPropagation()}
        >
          {renderFilterContent(columnKey)}
        </div>
      </span>
    </div>
  </th>
);

const filteredCompanyNames = React.useMemo(() => {
  if (!companySearch) return companyNames;

  return companyNames.filter(name =>
    name.toLowerCase().includes(companySearch.toLowerCase())
  );
}, [companyNames, companySearch]);


const renderFilterContent = (columnKey) => {
  switch (columnKey) {
    case "companyName":
  return (
    <div className="company-filter-dropdown company-filter">
      <input
  type="text"
  placeholder="Search company…"
  value={companySearch}
  autoFocus
  onClick={(e) => e.stopPropagation()}
  onChange={(e) => setCompanySearch(e.target.value)}
/>


      <div className="scrollable">
        {filteredCompanyNames.length === 0 && (
          <div className="filter-option muted">
            No results
          </div>
        )}

        {filteredCompanyNames.map(name => (
          <div
            key={name}
            className="filter-option"
            onClick={() => {
              setColumnFilters({
                ...columnFilters,
                companyName: name
              });
              setCompanySearch("");
              setActiveFilterColumn(null);
            }}
          >
            {name}
          </div>
        ))}
      </div>
    </div>
  );


    case "companySize":
      return (
        <select
          onChange={(e) =>
            setColumnFilters({
              ...columnFilters,
              companySize: e.target.value || null
            })
          }
        >
          <option value="">All</option>
          <option value="SMALL">Small Cap (&lt; 10,000 CR)</option>
          <option value="MID">Mid Cap (10,000 – 50,000 CR)</option>
          <option value="LARGE">Large Cap (&gt; 50,000 CR)</option>
        </select>
      );

    case "sector":
      return (
        <div className="scrollable">
          {sectors.map(sector => (
            <div
              key={sector}
              className="filter-option"
              onClick={() =>
                setColumnFilters({ ...columnFilters, sector })
              }
            >
              {sector}
            </div>
          ))}
        </div>
      );

    case "industry":
      return (
        <div className="scrollable">
          {industries.map(industry => (
            <div
              key={industry}
              className="filter-option"
              onClick={() =>
                setColumnFilters({ ...columnFilters, industry })
              }
            >
              {industry}
            </div>
          ))}
        </div>
      );

    default:
      return null;
  }
};


const exportToExcel = () => {
  if (equities.length === 0) {
    toast.warn("No data to export.");
    return;
  }

  // Prepare data for export
  const exportData = filteredRows.map((eq) => ({
    "Company": eq.company_name ?? "-",
    "Symbol": eq.symbol,
    "Valuation": eq.valuation ?? "-",
    "Share Price": eq.share_price ?? "-",
    "Market Cap": eq.market_cap ?? "-",
    "Sector": eq.sector ?? "-",
    "Sub Sector 1": eq.sub_sector_1 ?? "-",
    "Sub Sector 2": eq.sub_sector_2 ?? "-",
    "Industry": eq.industry ?? "-",
    "Target Price": eq.target_price ?? "-"
  }));

  // Create worksheet and workbook
  const worksheet = XLSX.utils.json_to_sheet(exportData);
  const workbook = XLSX.utils.book_new();
  XLSX.utils.book_append_sheet(workbook, worksheet, "Companies");

  // Write Excel buffer and trigger download
  const excelBuffer = XLSX.write(workbook, { bookType: "xlsx", type: "array" });
  const data = new Blob([excelBuffer], { type: "application/octet-stream" });
  saveAs(data, `company_valuation_${expectedYOY}yoy.xlsx`);
};
React.useEffect(() => {
  const handler = (e) => {
    if (
  !e.target.closest(".column-filter-popover") &&
  !e.target.closest(".filter-icon-wrapper")
) {
  setActiveFilterColumn(null);
}

  };

  window.addEventListener("click", handler);
  return () => window.removeEventListener("click", handler);
}, []);

const handleIndustrySelect = (industry) => {
  setColumnFilters((prev) => ({
    ...prev,
    industry: prev.industry === industry ? null : industry,
  }));
};
React.useEffect(() => {
  if (!hasSearched || !valuation) return;

  fetchEquitiesWithMCAP();
  fetchIndustryStats();
}, [valuation]);

const handleResetFilters = () => {
  setExpectedYOY(DEFAULT_YOY);
  setValuation("");

  setColumnFilters({
    companyName: "",
    companySize: null,
    sector: null,
    industry: null,
  });

  setCompanySearch("");
  setActiveFilterColumn(null);

  setEquities([]);
  setIndustryStats(null);
  setHasSearched(false);
};

return (
  <div className="company-valuation-page">

    {/* ================= FILTER CARD ================= */}
    <div className="card filter-card">
      <h2>Company Valuation Screener</h2>

      <div className="filter-grid">
        <div>
          <label>Expected YOY (%)</label>
          <select
            value={expectedYOY}
            onChange={(e) => setExpectedYOY(Number(e.target.value))}
          >
            {EXPECTED_YOY_OPTIONS.map((v) => (
              <option key={v} value={v}>{v}%</option>
            ))}
          </select>
        </div>

        <div>
          <label>Valuation</label>
          <select
            value={valuation}
            onChange={(e) => setValuation(e.target.value)}
          >
            <option value="">Select</option>
            <option value="overvalued">Overvalued</option>
            <option value="undervalued">Undervalued</option>
          </select>
        </div>

        <div className="filter-action">
  <button onClick={applyFilters}>Apply Filters</button>
  <button
    type="button"
    className="reset-btn"
    onClick={handleResetFilters}
    style={{ marginLeft: "10px" }}
  >
    Reset Filters
  </button>
  <button className="export-btn" onClick={exportToExcel} style={{ marginLeft: "10px" }}>
    Export XLS
  </button>
</div>

      </div>
    </div>

    {/* ================= LOADING ================= */}
    {loading && <p className="muted">Loading data…</p>}

    {!loading && !hasSearched && (
      <p className="muted">Select filters and click Apply.</p>
    )}

    {/* ================= SUMMARY + CHART ================= */}
    {industryStats && (
      <div className="grid-2">
        
        {/* SUMMARY CARDS */}
        <div className="card summary-card">
          <h3>Company Count</h3>

          <div className="kpi-grid">

  <div
    className={`kpi-card kpi-red ${valuation === "overvalued" ? "active" : ""}`}
    onClick={() => setValuation("overvalued")}
    style={{ cursor: "pointer" }}
  >
    <div className="kpi-label">Overvalued Companies</div>
    <div className="kpi-value">
      {industryStats.summary.overvalued}
    </div>
  </div>

  <div
    className={`kpi-card kpi-green ${valuation === "undervalued" ? "active" : ""}`}
    onClick={() => setValuation("undervalued")}
    style={{ cursor: "pointer" }}
  >
    <div className="kpi-label">Undervalued Companies</div>
    <div className="kpi-value">
      {industryStats.summary.undervalued}
    </div>
  </div>

</div>



          <div className="summary-footer">
            Expected YOY: <strong>{industryStats.summary.expected_yoy}%</strong>
          </div>
        </div>

        {/* CHART CARD */}
        <div className="card chart-card">
          <h3>Industry Distribution</h3>
         <IndustryValuationChart
  data={industryStats.industries}
  valuationType={valuation}
  onIndustrySelect={handleIndustrySelect}
/>

        </div>
      </div>
    )}

    {/* ================= TABLE ================= */}
    {!loading && hasSearched && filteredRows.length > 0 && (
      <div className="card table-card">
        <h3>Matching Companies</h3>

        <div className="table-wrap">
          <table className="styled-table">
            <thead>
  <tr>
    <FilterableHeader label="Company" columnKey="companyName" />

    <th>Symbol</th>
    <FilterableHeader label="Sector" columnKey="sector" />
    <th>Sub Sector 1</th>
    <th>Sub Sector 2</th>
    <FilterableHeader label="Industry" columnKey="industry" />
    <th>Valuation</th>
    <th>Share Price</th>
    <th>Market Cap</th>
    <FilterableHeader label="Company Size" columnKey="companySize" />
    <th>Target Price</th>
  </tr>
</thead>

            <tbody>
              {currentRows.map((eq) => (
                <tr key={eq.symbol}>
                  <td>{eq.company_name ?? "-"}</td>
                  <td>{eq.symbol}</td>
                   <td>{eq.sector ?? "-"}</td>
<td>{eq.sub_sector_1 ?? "-"}</td>
<td>{eq.sub_sector_2 ?? "-"}</td>
<td>{eq.industry ?? "-"}</td>
                  <td>
                    <span
                      className={
                        eq.valuation?.toLowerCase() === "undervalued"
                          ? "badge badge-green"
                          : "badge badge-red"
                      }
                    >
                      {eq.valuation}
                    </span>
                  </td>
                  <td>{eq.share_price ?? "-"}</td>
                  <td>{eq.market_cap ?? "-"}</td>
                  <td>{eq.company_size || "-"}</td>
                 
<td>
  {eq.target_price
    ? `₹ ${eq.target_price.toLocaleString()}`
    : "-"}
</td>

                </tr>
              ))}
            </tbody>
          </table>
        


        </div>
        <div className="table-footer">
  <div className="table-results">
    Showing <strong>{startItem}–{endItem}</strong> of{" "}
    <strong>{filteredRows.length}</strong> companies
  </div>

  <div className="pagination-size">
    <label htmlFor="pageSize">Rows per page</label>

    <select
      id="pageSize"
      value={pageSize}
      onChange={(e) => setPageSize(Number(e.target.value))}
    >
      {PAGE_SIZE_OPTIONS.map((size) => (
        <option key={size} value={size}>
          {size}
        </option>
      ))}
    </select>
  </div>

  <nav className="pagination" aria-label="Company table pagination">
    <button
      type="button"
      className="page-btn"
      disabled={currentPage === 1}
      onClick={() => setCurrentPage((page) => page - 1)}
      aria-label="Previous page"
    >
      Previous
    </button>

    {getPageNumbers().map((page) => (
      <button
        type="button"
        key={page}
        className={`page-btn ${
          currentPage === page ? "active" : ""
        }`}
        aria-current={currentPage === page ? "page" : undefined}
        onClick={() => setCurrentPage(page)}
      >
        {page}
      </button>
    ))}

    <button
      type="button"
      className="page-btn"
      disabled={currentPage === totalPages}
      onClick={() => setCurrentPage((page) => page + 1)}
      aria-label="Next page"
    >
      Next
    </button>
  </nav>
</div>
</div>
  
  )}
{!loading && hasSearched && filteredRows.length === 0 && (
  <div className="empty-state">
    <div className="empty-state-icon">⌕</div>
    <h3>No matching companies</h3>
    <p>Try changing your filters or resetting them to see more results.</p>
    <button
      type="button"
      className="primary-btn"
      onClick={() => {
        setColumnFilters({
          companyName: "",
          companySize: null,
          sector: null,
          industry: null,
        });
        setCompanySearch("");
        setActiveFilterColumn(null);
      }}
    >
      Clear column filters
    </button>
  </div>
)}
    {!loading && hasSearched && equities.length === 0 && (
      <p className="muted">No matching companies found.</p>
    )}
  </div>
);

};

export default CompanyValuation;
