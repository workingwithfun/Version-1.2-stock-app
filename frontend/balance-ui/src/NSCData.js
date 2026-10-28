
import React, { useCallback, useEffect, useMemo, useState } from "react";
import {
  FaUpload,
  FaSearch,
  FaTable,
  FaSlidersH,
  FaChartLine,
  FaFileCsv,
  FaFileExcel,
  FaSyncAlt,
  FaCalculator,
  FaTimes,
  FaCheckCircle,
} from "react-icons/fa";
import { ToastContainer, toast } from "react-toastify";
import "react-toastify/dist/ReactToastify.css";
import "./BalanceSheet";

const API = "http://localhost:8000/api/";

const INITIAL_STATUS = {
  nifty50: false,
  nifty100: false,
  nifty200: false,
  nifty500: false,
  nifty750: false,
};

const INDEXES = [
  { label: "Nifty 50", key: "nifty50", api: "NIFTY50" },
  { label: "Nifty 100", key: "nifty100", api: "NIFTY100" },
  { label: "Nifty 200", key: "nifty200", api: "NIFTY200" },
  { label: "Nifty 500", key: "nifty500", api: "NIFTY500" },
  { label: "Nifty 750", key: "nifty750", api: "NIFTY750" },
];

const RETURN_OPTIONS = [
  10, 20, 30, 40, 50, 75, 90, 100, 125, 150, 175, 200, 225, 250,
];

const companyName = (eq) =>
  eq?.mcap?.company_name || eq?.name_of_company || eq?.name || "-";

const formatNumber = (value, digits = 2) => {
  if (value === null || value === undefined || value === "") return "-";
  const number = Number(value);

  return Number.isFinite(number)
    ? number.toLocaleString("en-IN", {
        minimumFractionDigits: digits,
        maximumFractionDigits: digits,
      })
    : value;
};

const errorMessage = (error, fallback) =>
  error instanceof Error && error.message ? error.message : fallback;

function NSCData() {
  const [equities, setEquities] = useState([]);
  const [activeTab, setActiveTab] = useState("table");
  const [companyFilter, setCompanyFilter] = useState("");
  const [showDropdown, setShowDropdown] = useState(false);
  const [showModal, setShowModal] = useState(false);
  const [importStatus, setImportStatus] = useState(INITIAL_STATUS);
  const [loading, setLoading] = useState(false);
  const [isCalculating, setIsCalculating] = useState(false);
  const [expectedReturn, setExpectedReturn] = useState(30);

  const fetchEquities = useCallback(async () => {
    setLoading(true);

    try {
      const response = await fetch(`${API}equities-with-mcap/`);

      if (!response.ok) {
        throw new Error(`Request failed (${response.status})`);
      }

      const result = await response.json();
      setEquities(Array.isArray(result) ? result : result.results || []);
    } catch (error) {
      console.error("Failed to fetch equity data:", error);
      toast.error("Failed to fetch equity and market-cap data.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchEquities();
  }, [fetchEquities]);

  const filteredEquities = useMemo(() => {
    const query = companyFilter.trim().toLowerCase();

    if (!query) return equities;

    return equities.filter((eq) =>
      [
        eq?.mcap?.company_name,
        eq?.name_of_company,
        eq?.name,
        eq?.symbol,
      ]
        .filter(Boolean)
        .some((value) => String(value).toLowerCase().includes(query))
    );
  }, [equities, companyFilter]);

  const companyNames = useMemo(() => {
    const query = companyFilter.trim().toLowerCase();

    if (!query) return [];

    return [
      ...new Set(
        equities
          .map(companyName)
          .filter(
            (name) =>
              name !== "-" && name.toLowerCase().includes(query)
          )
      ),
    ]
      .sort((a, b) => a.localeCompare(b))
      .slice(0, 8);
  }, [equities, companyFilter]);

  const uploadFile = async (endpoint, file, extraFields = {}) => {
    const formData = new FormData();
    formData.append("file", file);

    Object.entries(extraFields).forEach(([key, value]) => {
      formData.append(key, value);
    });

    const response = await fetch(`${API}${endpoint}`, {
      method: "POST",
      body: formData,
    });

    const result = await response.json().catch(() => ({}));

    if (!response.ok) {
      throw new Error(
        result.error || result.detail || `Request failed (${response.status})`
      );
    }

    return result;
  };

  const [uploading, setUploading] = useState({
  equityL: false,
  mcap: false,
  mapping: false,
});


const handleImportEquityL = async (event) => {
  const input = event.target;
  const file = input.files?.[0];
  if (!file) return;

  if (!/\.csv$/i.test(file.name)) {
    toast.error("Only CSV files are supported.");
    input.value = "";
    return;
  }

  setUploading((prev) => ({ ...prev, equityL: true }));

  try {
    const result = await uploadFile("import_equity_l/", file);

    toast.success(
      `Imported successfully. Created: ${result.created ?? 0}, Updated: ${
        result.updated ?? 0
      }, Total: ${result.total ?? 0}`
    );

    await fetchEquities();
  } catch (error) {
    console.error("Equity L import error:", error);
    toast.error(errorMessage(error, "Equity L import failed."));
  } finally {
    setUploading((prev) => ({ ...prev, equityL: false }));
    input.value = "";
  }
};

const handleImportMCAP = async (event) => {
  const input = event.target;
  const file = input.files?.[0];
  if (!file) return;

  if (!/\.csv$/i.test(file.name)) {
    toast.error("Only CSV files are supported.");
    input.value = "";
    return;
  }

  setUploading((prev) => ({ ...prev, mcap: true }));

  try {
    const result = await uploadFile("import-mcap/", file);

    toast.success(
      `${result.success || "MCAP import completed"} (Skipped: ${
        result.skipped ?? 0
      })`
    );

    await fetchEquities();
  } catch (error) {
    console.error("MCAP import error:", error);
    toast.error(errorMessage(error, "MCAP import failed."));
  } finally {
    setUploading((prev) => ({ ...prev, mcap: false }));
    input.value = "";
  }
};

const handleImportMapping = async (event) => {
  const input = event.target;
  const file = input.files?.[0];
  if (!file) return;

  if (!/\.(xlsx|xls)$/i.test(file.name)) {
    toast.error("Only Excel files (.xlsx or .xls) are supported.");
    input.value = "";
    return;
  }

  setUploading((prev) => ({ ...prev, mapping: true }));

  try {
    const result = await uploadFile("import-mapping/", file);

    toast.success(
      `${result.success || "Mapping import completed"} (Skipped: ${
        result.skipped ?? 0
      })`
    );

    await fetchEquities();
  } catch (error) {
    console.error("Mapping import error:", error);
    toast.error(errorMessage(error, "Mapping import failed."));
  } finally {
    setUploading((prev) => ({ ...prev, mapping: false }));
    input.value = "";
  }
};

  const handleImportNifty = async (file, index) => {
    try {
      const result = await uploadFile("import-nifty-index/", file, {
        index_type: index.api,
      });

      toast.success(result.message || `${index.label} imported successfully.`);

      setImportStatus((previous) => ({
        ...previous,
        [index.key]: true,
      }));

      await fetchEquities();
      return true;
    } catch (error) {
      console.error(`${index.label} import error:`, error);
      toast.error(errorMessage(error, `${index.label} import failed.`));
      return false;
    }
  };

  const handleCalculateAll = async () => {
    const confirmed = window.confirm(
      `Calculate metrics for ALL companies using Expected YoY Return = ${expectedReturn}%?`
    );

    if (!confirmed) return;

    try {
      setIsCalculating(true);
      toast.info(`Started calculation using ${expectedReturn}% expected YoY return.`);

      const response = await fetch(`${API}metrics/calculate-all/`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ expected_return: expectedReturn }),
      });

      const result = await response.json().catch(() => ({}));

      if (!response.ok) {
        throw new Error(
          result.error || result.detail || "Bulk calculation failed."
        );
      }

      if (result.success_count === 0) {
        toast.error("Calculation failed for all companies. Check backend logs.");
      } else {
        toast.success(
          `Calculated ${result.success_count} companies successfully.`
        );
      }

      if (result.failed_count > 0) {
        toast.warning(`${result.failed_count} companies failed during calculation.`);
      }
    } catch (error) {
      console.error("Bulk calculation error:", error);
      toast.error(errorMessage(error, "Error during bulk calculation."));
    } finally {
      setIsCalculating(false);
    }
  };

  return (
    <main className="nsc-page">
      <ToastContainer position="top-right" autoClose={3500} newestOnTop />

      <header className="nsc-hero">
        <div>
          <div className="nsc-eyebrow">
            <span className="nsc-live-dot" />
            FINANCIAL DATA WORKSPACE
          </div>
          <h1>NSE Data</h1>
          <p>
            Manage equity listings, market capitalization, index membership,
            and company mappings in one workspace.
          </p>
        </div>

        <button
          className="nsc-button nsc-button-light"
          type="button"
          onClick={fetchEquities}
          disabled={loading}
        >
          <FaSyncAlt className={loading ? "nsc-spin" : ""} />
          {loading ? "Refreshing..." : "Refresh data"}
        </button>
      </header>

      <section className="nsc-stat-grid">
        <article className="nsc-stat-card">
          <span className="nsc-stat-icon"><FaTable /></span>
          <div>
            <span>Equity records loaded</span>
            <strong>{equities.length.toLocaleString("en-IN")}</strong>
          </div>
        </article>

        <article className="nsc-stat-card">
          <span className="nsc-stat-icon nsc-teal"><FaSearch /></span>
          <div>
            <span>Matching records</span>
            <strong>{filteredEquities.length.toLocaleString("en-IN")}</strong>
          </div>
        </article>

        <article className="nsc-stat-card">
          <span className="nsc-stat-icon nsc-purple"><FaChartLine /></span>
          <div>
            <span>Nifty imports completed</span>
            <strong>{Object.values(importStatus).filter(Boolean).length} / 5</strong>
          </div>
        </article>
      </section>

      <nav className="nsc-tabs" aria-label="NSC data sections">
        <button
          type="button"
          className={`nsc-tab ${activeTab === "table" ? "active" : ""}`}
          onClick={() => setActiveTab("table")}
        >
          <FaTable /> NSE table
        </button>

        <button
          type="button"
          className={`nsc-tab ${activeTab === "action" ? "active" : ""}`}
          onClick={() => setActiveTab("action")}
        >
          <FaSlidersH /> Data management
        </button>
      </nav>

      {activeTab === "table" && (
        <section className="nsc-panel">
          <div className="nsc-panel-heading">
            <div>
              <h2>Equity master</h2>
              <p>Search and review company listing, valuation, and market-cap information.</p>
            </div>
            <span className="nsc-count">
              {filteredEquities.length.toLocaleString("en-IN")} records
            </span>
          </div>

          <div className="nsc-toolbar">
            <div className="nsc-search">
              <FaSearch />
              <input
                type="search"
                value={companyFilter}
                onChange={(event) => setCompanyFilter(event.target.value)}
                onFocus={() => setShowDropdown(true)}
                onBlur={() => window.setTimeout(() => setShowDropdown(false), 150)}
                placeholder="Search company name or symbol..."
                autoComplete="off"
                aria-label="Search company name or symbol"
              />

              {companyFilter && (
                <button
                  type="button"
                  aria-label="Clear search"
                  onMouseDown={(event) => event.preventDefault()}
                  onClick={() => setCompanyFilter("")}
                >
                  <FaTimes />
                </button>
              )}

              {showDropdown && companyNames.length > 0 && (
                <ul className="nsc-suggestions">
                  {companyNames.map((name) => (
                    <li key={name}>
                      <button
                        type="button"
                        onMouseDown={(event) => event.preventDefault()}
                        onClick={() => {
                          setCompanyFilter(name);
                          setShowDropdown(false);
                        }}
                      >
                        <FaSearch />
                        {name}
                      </button>
                    </li>
                  ))}
                </ul>
              )}
            </div>

            <span className="nsc-toolbar-note">
              {loading ? "Loading equity data..." : "Results update as you type"}
            </span>
          </div>

          <div className="nsc-table-wrap">
            <table className="nsc-table">
              <thead>
                <tr>
                  <th>Name of company</th>
                  <th>Symbol</th>
                  <th>Series</th>
                  <th>Date of listing</th>
                  <th>ISIN number</th>
                  <th>Issue size</th>
                  <th>Share price</th>
                  <th>Market cap</th>
                  <th>Company size</th>
                  <th>EPS (Y24)</th>
                  <th>EPS (TTM)</th>
                  <th>Sector</th>
                  <th>Sub sector 1</th>
                  <th>Sub sector 2</th>
                  <th>Industry name</th>
                  <th>Stock P/E</th>
                  <th>TTM P/E</th>
                  <th>Industry P/E</th>
                  <th>Nifty index</th>
                </tr>
              </thead>

              <tbody>
                {loading && equities.length === 0 ? (
                  <tr>
                    <td colSpan={19} className="nsc-empty">
                      Loading equity records...
                    </td>
                  </tr>
                ) : filteredEquities.length > 0 ? (
                  filteredEquities.map((eq, index) => (
                    <tr key={eq.symbol || `${companyName(eq)}-${index}`}>
                      <td className="nsc-company" title={companyName(eq)}>
                        {companyName(eq)}
                      </td>
                      <td><span className="nsc-symbol">{eq.symbol || "-"}</span></td>
                      <td>{eq.series || "-"}</td>
                      <td>{eq.date_of_listing || "-"}</td>
                      <td>{eq.isin_number || "-"}</td>
                      <td>{formatNumber(eq.mcap?.issue_size, 0)}</td>
                      <td>{formatNumber(eq.mcap?.share_price)}</td>
                      <td>{formatNumber(eq.mcap?.market_cap)}</td>
                      <td>{eq.mcap?.company_size || "-"}</td>
                      <td>{formatNumber(eq.mcap?.eps_y24)}</td>
                      <td>{formatNumber(eq.mcap?.eps_trailing)}</td>
                      <td>{eq.mcap?.sector || "-"}</td>
                      <td>{eq.mcap?.sub_sector_1 || "-"}</td>
                      <td>{eq.mcap?.sub_sector_2 || "-"}</td>
                      <td>{eq.mcap?.industry_name || "-"}</td>
                      <td>{formatNumber(eq.mcap?.stock_pe)}</td>
                      <td>{formatNumber(eq.mcap?.ttm_pe)}</td>
                      <td>{formatNumber(eq.mcap?.industry_pe)}</td>
                      <td>
                        {eq.mcap?.nifty_index && eq.mcap.nifty_index !== "NONE"
                          ? eq.mcap.nifty_index
                          : "-"}
                      </td>
                    </tr>
                  ))
                ) : (
                  <tr>
                    <td colSpan={19} className="nsc-empty">
                      <strong>No companies found</strong>
                      <span>Try another company name or symbol.</span>
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>

          <footer className="nsc-table-footer">
            <span>
              Showing <strong>{filteredEquities.length.toLocaleString("en-IN")}</strong>
              {" "}of <strong>{equities.length.toLocaleString("en-IN")}</strong> loaded records
            </span>
            <span>Scroll horizontally to view all columns</span>
          </footer>
        </section>
      )}

      {activeTab === "action" && (
        <div className="nsc-management">
          <section className="nsc-panel">
            <div className="nsc-panel-heading">
              <div>
                <h2>Import data files</h2>
                <p>Upload source files to update equity, market-cap, and mapping data.</p>
              </div>
            </div>

            <div className="nsc-import-grid">
              <ImportCard
                icon={<FaFileCsv />}
                title="Equity L file"
                description="Update company listings from the Equity L CSV file."
                buttonText="Upload Equity L"
                accept=".csv"
                helper="CSV file"
                onChange={handleImportEquityL}
                uploading={uploading.equityL}
              />

              <ImportCard
                icon={<FaChartLine />}
                title="Market capitalization"
                description="Refresh share price, market cap, EPS, and valuation metrics."
                buttonText="Upload MCAP"
                accept=".csv"
                helper="CSV file"
                onChange={handleImportMCAP}
                uploading={uploading.mcap}
              />

              <ImportCard
                icon={<FaFileExcel />}
                title="Company mapping"
                description="Synchronize company names and mapping data from a spreadsheet."
                buttonText="Upload mapping"
                accept=".xlsx,.xls"
                helper="XLSX or XLS file"
                onChange={handleImportMapping}
                uploading={uploading.mapping}
              />

              <article className="nsc-import-card">
                <span className="nsc-import-icon nsc-purple"><FaUpload /></span>
                <div className="nsc-import-content">
                  <h3>Nifty index files</h3>
                  <p>Import index membership files in sequence, from Nifty 50 through Nifty 750.</p>
                  <button
                    className="nsc-button nsc-button-outline"
                    type="button"
                    onClick={() => setShowModal(true)}
                  >
                    <FaUpload /> Manage index imports
                  </button>
                  <small>
                    {Object.values(importStatus).filter(Boolean).length} of 5 imports completed this session
                  </small>
                </div>
              </article>
            </div>
          </section>

          <section className="nsc-panel nsc-calculation-panel">
            <div className="nsc-panel-heading">
              <div>
                <span className="nsc-kicker">VALUATION TOOLS</span>
                <h2>Equity master calculations</h2>
                <p>Recalculate metrics for all companies using your expected year-on-year return.</p>
              </div>
              <span className="nsc-calculation-icon"><FaCalculator /></span>
            </div>

            <div className="nsc-calculation-controls">
              <div className="nsc-field">
                <label htmlFor="expected-return">Expected YoY return</label>
                <select
                  id="expected-return"
                  value={expectedReturn}
                  onChange={(event) => setExpectedReturn(Number(event.target.value))}
                  disabled={isCalculating}
                >
                  {RETURN_OPTIONS.map((value) => (
                    <option key={value} value={value}>{value}%</option>
                  ))}
                </select>
                <small>Applied to the bulk calculation request.</small>
              </div>

              <div className="nsc-assumption">
                <span>Selected assumption</span>
                <strong>{expectedReturn}% <small>YoY</small></strong>
              </div>

              <button
                className="nsc-button nsc-button-primary nsc-calculate"
                type="button"
                onClick={handleCalculateAll}
                disabled={isCalculating}
              >
                {isCalculating ? (
                  <><span className="nsc-spinner" /> Calculating all companies...</>
                ) : (
                  <><FaCalculator /> Calculate all companies</>
                )}
              </button>
            </div>

            <p className="nsc-warning">
              This action calculates metrics for all companies. You will be asked to confirm before it starts.
            </p>
          </section>
        </div>
      )}

      {showModal && (
        <div
          className="nsc-modal-backdrop"
          role="presentation"
          onMouseDown={(event) => {
            if (event.target === event.currentTarget) setShowModal(false);
          }}
        >
          <section
            className="nsc-modal"
            role="dialog"
            aria-modal="true"
            aria-labelledby="nsc-modal-title"
          >
            <div className="nsc-modal-top">
              <span className="nsc-modal-icon"><FaUpload /></span>
              <button
                type="button"
                className="nsc-close"
                aria-label="Close modal"
                onClick={() => setShowModal(false)}
              >
                <FaTimes />
              </button>
            </div>

            <h2 id="nsc-modal-title">Import Nifty index files</h2>
            <p className="nsc-modal-description">
              Import each index in sequence. The next index becomes available after the previous import succeeds.
            </p>

            <div className="nsc-index-list">
              {INDEXES.map((index, position) => {
                const previousKey = INDEXES[position - 1]?.key;
                const enabled = position === 0 || importStatus[previousKey];

                return (
                  <ImportRow
                    key={index.key}
                    label={index.label}
                    step={position + 1}
                    enabled={enabled}
                    imported={importStatus[index.key]}
                    onImport={(file) => handleImportNifty(file, index)}
                  />
                );
              })}
            </div>

            <div className="nsc-modal-footer">
              <span><FaCheckCircle /> {Object.values(importStatus).filter(Boolean).length} of 5 completed</span>
              <button
                type="button"
                className="nsc-button nsc-button-primary"
                onClick={() => setShowModal(false)}
              >
                Done
              </button>
            </div>
          </section>
        </div>
      )}
    </main>
  );
}

function ImportCard({
  icon,
  title,
  description,
  buttonText,
  accept,
  helper,
  onChange,
  uploading = false,
}) {
  return (
    <article className="nsc-import-card">
      <span className="nsc-import-icon">{icon}</span>

      <div className="nsc-import-content">
        <h3>{title}</h3>
        <p>{description}</p>

        <label
          className={`nsc-button nsc-button-outline nsc-file-button ${
            uploading ? "is-uploading" : ""
          }`}
        >
          {uploading ? (
            <span className="nsc-spinner" />
          ) : (
            <FaUpload />
          )}

          {uploading ? "Importing..." : buttonText}

          <input
            type="file"
            accept={accept}
            disabled={uploading}
            onChange={onChange}
          />
        </label>

        <small>
          {uploading ? "Please wait while your file is processed..." : helper}
        </small>
      </div>
    </article>
  );
}

function ImportRow({ label, step, enabled, imported, onImport }) {
  const [file, setFile] = useState(null);
  const [uploading, setUploading] = useState(false);

  const submit = async () => {
    if (!file || !enabled || imported || uploading) return;

    setUploading(true);
    try {
      const success = await onImport(file);
      if (success) setFile(null);
    } finally {
      setUploading(false);
    }
  };

  return (
    <div className={`nsc-index-row ${imported ? "is-imported" : ""} ${!enabled ? "is-disabled" : ""}`}>
      <span className="nsc-step">{imported ? <FaCheckCircle /> : String(step).padStart(2, "0")}</span>

      <div className="nsc-index-info">
        <strong>{label}</strong>
        <span>
          {imported
            ? "Imported successfully"
            : enabled
              ? "Ready to import"
              : "Complete the previous index first"}
        </span>
      </div>

      <label className={`nsc-button nsc-button-outline nsc-index-file ${!enabled || imported ? "is-disabled" : ""}`}>
        <FaFileCsv />
        <span>{file ? file.name : "Choose file"}</span>
        <input
          type="file"
          accept=".csv,.xlsx"
          disabled={!enabled || imported || uploading}
          onChange={(event) => setFile(event.target.files?.[0] || null)}
        />
      </label>

      <button
        type="button"
        className={`nsc-button ${imported ? "nsc-button-success" : "nsc-button-primary"} nsc-index-submit`}
        disabled={!enabled || !file || imported || uploading}
        onClick={submit}
      >
        {imported ? "Imported" : uploading ? "Importing..." : "Import"}
      </button>
    </div>
  );
}

export default NSCData;
