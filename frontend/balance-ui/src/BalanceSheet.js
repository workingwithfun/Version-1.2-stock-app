import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import * as XLSX from "xlsx";
import { saveAs } from "file-saver";
import { ToastContainer, toast } from "react-toastify";
import "react-toastify/dist/ReactToastify.css";
import "./BalanceSheet.css";

const API_URL = "http://localhost:8000/api/balance-entries/";
const UPLOAD_URL = "http://localhost:8000/api/upload/yearly/";
const TYPE_OPTIONS = ["Sales", "OPM", "Net profit", "EPS", "ROC", "ROCE"];
const FALLBACK_YEARS = Array.from({ length: 10 }, (_, index) => 2015 + index);
const IMPORT_YEARS = Array.from({ length: 20 }, (_, index) => 2010 + index);

const getCompanyName = (fileName = "") => fileName.replace(/\.[^/.]+$/, "");
const getCellValue = (row, key) => row?.[key] ?? "";
const formatDecimal = (value) => {
  if (value === null || value === undefined || value === "") {
    return "—";
  }

  const number = Number(value);

  if (!Number.isFinite(number)) {
    return value;
  }

  return number.toFixed(2);
};
function BalanceSheet() {
  const [data, setData] = useState([]);
  const [nextUrl, setNextUrl] = useState(null);
  const [companyFilter, setCompanyFilter] = useState("");
  const [selectedTypes, setSelectedTypes] = useState([]);
  const [typeMenuOpen, setTypeMenuOpen] = useState(false);
  const [companyMenuOpen, setCompanyMenuOpen] = useState(false);
  const [loading, setLoading] = useState(false);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState("");
  const [sortConfig, setSortConfig] = useState({ key: "file_name", direction: "asc" });
  const [pendingFiles, setPendingFiles] = useState([]);
  const [selectedYear, setSelectedYear] = useState("");
  const [yearModalOpen, setYearModalOpen] = useState(false);
  const [importing, setImporting] = useState(false);

  const tableRef = useRef(null);
  const fileInputRef = useRef(null);
const loadingRef = useRef(false);
const nextUrlRef = useRef(null);
const requestIdRef = useRef(0);
const abortControllerRef = useRef(null);
const searchTimerRef = useRef(null);
const searchRef = useRef("");
const [searching, setSearching] = useState(false);

const buildApiUrl = (search = "", type = "") => {
  const url = new URL(API_URL);

  if (search.trim()) {
    url.searchParams.set("search", search.trim());
  }

  if (type) {
    url.searchParams.set("type", type);
  }

  return url.toString();
};

const fetchData = useCallback(
  async ({ reset = false, quiet = false, search } = {}) => {
    const searchTerm = search ?? searchRef.current;
    const url = reset ? buildApiUrl(searchTerm) : nextUrlRef.current;

    if (!url) return;

    // A new search must replace the previous request.
    if (reset) {
      abortControllerRef.current?.abort();
      loadingRef.current = false;
    } else if (loadingRef.current) {
      return;
    }

    const controller = new AbortController();
    abortControllerRef.current = controller;

    const requestId = ++requestIdRef.current;

    loadingRef.current = true;
    setLoading(true);
    setError("");

    try {
      const response = await fetch(url, {
        signal: controller.signal,
      });

      if (!response.ok) {
        throw new Error(`Request failed: ${response.status}`);
      }

      const payload = await response.json();
      if (requestId !== requestIdRef.current) return;

      const results = Array.isArray(payload)
        ? payload
        : payload.results || [];

      setData((previous) => {
        if (reset) return results;

        const existingIds = new Set(previous.map((row) => row.id));

        return [
          ...previous,
          ...results.filter((row) => !existingIds.has(row.id)),
        ];
      });

      const next = Array.isArray(payload) ? null : payload.next || null;

      nextUrlRef.current = next;
      setNextUrl(next);
    } catch (fetchError) {
      if (fetchError.name !== "AbortError" && requestId === requestIdRef.current) {
        console.error("Failed to fetch balance entries:", fetchError);
        setError("Unable to load balance entries. Please try again.");
      }
    } finally {
      if (requestId === requestIdRef.current) {
        loadingRef.current = false;
        setLoading(false);
        setRefreshing(false);
        setSearching(false);
      }
    }
  },
  []
);


  useEffect(() => {
    fetchData({ reset: true });
  }, [fetchData]);

useEffect(() => {
  searchRef.current = companyFilter;

  window.clearTimeout(searchTimerRef.current);

  setSearching(true);

  searchTimerRef.current = window.setTimeout(() => {
    nextUrlRef.current = null;
    setNextUrl(null);

    fetchData({
      reset: true,
      search: companyFilter,
    });
  }, 300);

  return () => {
    window.clearTimeout(searchTimerRef.current);
  };
}, [companyFilter, fetchData]);
const filteredData = useMemo(() => {
  return data.filter((row) => {
    const matchesType =
      selectedTypes.length === 0 ||
      selectedTypes.includes(row?.type);

    return matchesType;
  });
}, [data, selectedTypes]);

const companyNames = useMemo(() => {
  const query = companyFilter.trim().toLowerCase();

  if (!query) return [];

  return [
    ...new Set(
      data
        .map((row) => getCompanyName(row?.file_name))
        .filter(
          (name) => name && name.toLowerCase().includes(query)
        )
    ),
  ]
    .sort((a, b) => a.localeCompare(b))
    .slice(0, 8);
}, [data, companyFilter]);

const years = useMemo(() => {
  const yearSet = new Set();

  // Use only records matching the current filters.
  filteredData.forEach((row) => {
    Object.keys(row?.years || {}).forEach((year) => {
      const parsedYear = Number(year);

      if (Number.isFinite(parsedYear)) {
        yearSet.add(parsedYear);
      }
    });
  });

  return yearSet.size
    ? [...yearSet].sort((a, b) => a - b)
    : FALLBACK_YEARS;
}, [filteredData]);


  const sortedData = useMemo(() => {
    if (!sortConfig.key) return filteredData;
    const { key, direction } = sortConfig;
    const multiplier = direction === "asc" ? 1 : -1;

    return [...filteredData].sort((a, b) => {
      let left;
      let right;
      if (years.includes(Number(key))) {
        left = a?.years?.[key] ?? a?.years?.[Number(key)] ?? "";
        right = b?.years?.[key] ?? b?.years?.[Number(key)] ?? "";
      } else if (key.startsWith("company_name")) {
        left = getCompanyName(a?.file_name);
        right = getCompanyName(b?.file_name);
      } else {
        left = a?.[key] ?? "";
        right = b?.[key] ?? "";
      }

      const leftNumber = Number(left);
      const rightNumber = Number(right);
      if (left !== "" && right !== "" && Number.isFinite(leftNumber) && Number.isFinite(rightNumber)) {
        return (leftNumber - rightNumber) * multiplier;
      }
      return String(left).localeCompare(String(right), undefined, { numeric: true, sensitivity: "base" }) * multiplier;
    });
  }, [filteredData, sortConfig, years]);

  const toggleSort = (key) => {
    setSortConfig((current) => ({
      key,
      direction: current.key === key && current.direction === "asc" ? "desc" : "asc",
    }));
  };

  const sortIndicator = (key) => {
    if (sortConfig.key !== key) return "↕";
    return sortConfig.direction === "asc" ? "↑" : "↓";
  };

  const handleExport = () => {
    if (!sortedData.length) {
      toast.info("There are no rows to export.");
      return;
    }

    const columns = [
      "Company", "Type", ...years.map((year) => String(year)),
      "Trailing", "Audit date", "Aging days", "Aging months", "Aging years", "Reminder",
    ];

    const rows = sortedData.map((row) => {
      const exported = {
        Company: getCompanyName(row.file_name),
        Type: row.type ?? "",
      };
      years.forEach((year) => {
        const value = row?.years?.[year] ?? row?.years?.[String(year)];
exported[String(year)] =
  value === "" || value === null || value === undefined
    ? ""
    : Number.isFinite(Number(value))
      ? Number(Number(value).toFixed(2))
      : value;
      });
      exported["Trailing"] =
  row.trailing === "" || row.trailing === null || row.trailing === undefined
    ? ""
    : Number.isFinite(Number(row.trailing))
      ? Number(Number(row.trailing).toFixed(2))
      : row.trailing;
      exported["Audit date"] = row.audit_date ?? "";
      exported["Aging days"] = row.aging_days ?? "";
      exported["Aging months"] = row.aging_months ?? "";
      exported["Aging years"] = row.aging_years ?? "";
      exported["Reminder"] = row.reminder ?? "";
      return exported;
    });

    const worksheet = XLSX.utils.json_to_sheet(rows, { header: columns });
    worksheet["!cols"] = columns.map((column) => ({
      wch: Math.min(28, Math.max(12, column.length + 2)),
    }));
    const workbook = XLSX.utils.book_new();
    XLSX.utils.book_append_sheet(workbook, worksheet, "Balance Entries");
    const buffer = XLSX.write(workbook, { bookType: "xlsx", type: "array" });
    saveAs(
      new Blob([buffer], { type: "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet" }),
      "BalanceEntries.xlsx",
    );
    toast.success(`${sortedData.length} rows exported.`);
  };

  const handleFileSelection = (event) => {
    const files = Array.from(event.target.files || []);
    if (!files.length) return;
    setPendingFiles(files);
    setSelectedYear("");
    setYearModalOpen(true);
    // Let the same file be selected again after cancelling or importing.
    event.target.value = "";
  };

  const startImport = async () => {
    if (!pendingFiles.length || !selectedYear) return;
    const formData = new FormData();
    pendingFiles.forEach((file) => {
      formData.append("files", file);
      formData.append("lastModified[]", String(file.lastModified));
    });
    formData.append("selectedYear", selectedYear);

    setImporting(true);
    try {
      const response = await fetch(UPLOAD_URL, { method: "POST", body: formData });
      if (!response.ok) {
        const detail = await response.text();
        throw new Error(detail || `Import failed (${response.status}).`);
      }
      toast.success(`${pendingFiles.length} file${pendingFiles.length === 1 ? "" : "s"} imported successfully.`);
      setYearModalOpen(false);
      setPendingFiles([]);
      nextUrlRef.current = null;
      setNextUrl(null);
      await fetchData({ reset: true, quiet: true });
    } catch (importError) {
      toast.error(importError instanceof Error ? importError.message : "Import failed.");
    } finally {
      setImporting(false);
    }
  };

  const handleRefresh = async () => {
    if (loadingRef.current) return;
    setRefreshing(true);
    nextUrlRef.current = null;
    setNextUrl(null);
    await fetchData({ reset: true, quiet: true });
    toast.success("Balance entries refreshed.");
  };

  const handleTableScroll = () => {
    const element = tableRef.current;
    if (!element || loadingRef.current || !nextUrlRef.current) return;
    if (element.scrollTop + element.clientHeight >= element.scrollHeight - 120) {
      fetchData();
    }
  };

  const clearFilters = () => {
    setCompanyFilter("");
    setSelectedTypes([]);
  };

  return (
    <main className="balance-page">
      <ToastContainer position="top-right" autoClose={3000} newestOnTop theme="colored" />

      <header className="page-header">
        <div>
          <p className="eyebrow">FINANCIAL DATA WORKSPACE</p>
          <h1>Balance entries</h1>
          <p className="page-subtitle">Search, review, and export your company financial records.</p>
        </div>
        <div className="header-actions">
          <button className="button button-secondary" type="button" onClick={handleRefresh} disabled={loading || refreshing}>
            <span className={refreshing ? "spin" : ""} aria-hidden="true">↻</span>
            {refreshing ? "Refreshing…" : "Refresh"}
          </button>
          <button className="button button-primary" type="button" onClick={handleExport} disabled={!sortedData.length}>
            <span aria-hidden="true">↓</span> Export Excel
          </button>
        </div>
      </header>

      <section className="summary-grid" aria-label="Balance entry summary">
        <article className="summary-card">
          <span className="summary-icon">▤</span>
          <div><p>Loaded records</p><strong>{data.length.toLocaleString()}</strong></div>
        </article>
        <article className="summary-card">
          <span className="summary-icon summary-icon-blue">⌕</span>
          <div><p>Matching records</p><strong>{sortedData.length.toLocaleString()}</strong></div>
        </article>
        <article className="summary-card">
          <span className="summary-icon summary-icon-violet">▦</span>
          <div><p>Financial years</p><strong>{years.length}</strong></div>
        </article>
        <article className="summary-card">
          <span className="summary-icon summary-icon-green">✓</span>
          <div><p>Selected attributes</p><strong>{selectedTypes.length || "All"}</strong></div>
        </article>
      </section>

      <section className="filter-panel" aria-label="Search and filter records">
        <div className="panel-heading">
          <div><h2>Find records</h2><p>Use filters to narrow the table. Click a column heading to sort.</p></div>
          {(companyFilter || selectedTypes.length > 0) && (
            <button type="button" className="text-button" onClick={clearFilters}>Clear filters</button>
          )}
        </div>

        <div className="filter-grid">
          <div className="field company-field">
            <label htmlFor="company-search">Company</label>
            <div className="input-with-icon">
              <span aria-hidden="true">⌕</span>
              <input
                id="company-search"
                type="search"
                value={companyFilter}
                onChange={(event) => setCompanyFilter(event.target.value)}
                onFocus={() => setCompanyMenuOpen(true)}
                onBlur={() => window.setTimeout(() => setCompanyMenuOpen(false), 120)}
                placeholder="Search company name…"
                autoComplete="off"
              />
              {companyFilter && <button type="button" aria-label="Clear company search" onMouseDown={(event) => event.preventDefault()} onClick={() => setCompanyFilter("")}>×</button>}
            </div>
            {companyMenuOpen && companyFilter.trim() && (
              <div className="suggestion-menu">
                {companyNames.filter((name) => name.toLowerCase().includes(companyFilter.trim().toLowerCase())).slice(0, 8).map((name) => (
                  <button type="button" key={name} onMouseDown={(event) => event.preventDefault()} onClick={() => { setCompanyFilter(name); setCompanyMenuOpen(false); }}>
                    {name}
                  </button>
                ))}
              </div>
            )}
          </div>

          <div className="field type-field">
            <label id="attribute-label">Attributes</label>
            <button
              type="button"
              className={`select-trigger ${typeMenuOpen ? "is-open" : ""}`}
              aria-labelledby="attribute-label"
              aria-expanded={typeMenuOpen}
              onClick={() => setTypeMenuOpen((open) => !open)}
            >
              <span>{selectedTypes.length ? `${selectedTypes.length} selected` : "All attributes"}</span>
              <span aria-hidden="true">{typeMenuOpen ? "⌃" : "⌄"}</span>
            </button>
            {typeMenuOpen && (
              <div className="type-menu">
                <button type="button" className="type-menu-all" onClick={() => setSelectedTypes([])}>
                  {selectedTypes.length === 0 ? "✓ " : ""}All attributes
                </button>
                {TYPE_OPTIONS.map((type) => (
                  <label key={type} className="type-option">
                    <input
                      type="checkbox"
                      checked={selectedTypes.includes(type)}
                      onChange={() => setSelectedTypes((current) => current.includes(type) ? current.filter((item) => item !== type) : [...current, type])}
                    />
                    <span>{type}</span>
                  </label>
                ))}
              </div>
            )}
          </div>

          <div className="field import-field">
            <label>Import spreadsheets</label>
            <button type="button" className="button button-outline import-button" onClick={() => fileInputRef.current?.click()} disabled={importing}>
              <span aria-hidden="true">↑</span> {importing ? "Importing…" : "Choose Excel files"}
            </button>
            <input ref={fileInputRef} className="visually-hidden" type="file" multiple accept=".xlsx,.xls" onChange={handleFileSelection} />
            <span className="field-hint">XLSX or XLS · multiple files supported</span>
          </div>
        </div>
      </section>

      {error && (
        <div className="error-banner" role="alert">
          <span>{error}</span>
          <button type="button" onClick={() => fetchData({ reset: true })}>Try again</button>
        </div>
      )}

      <section className="table-panel">
        <div className="table-heading">
          <div><h2>Financial records</h2><p>{sortedData.length.toLocaleString()} visible {sortedData.length === 1 ? "record" : "records"}</p></div>
          <span className="table-status"><span className={loading ? "status-dot status-loading" : "status-dot"} />{searching || loading
  ? "Searching / loading data"
  : nextUrl
    ? "Scroll to load more"
    : "Data loaded"}</span>
        </div>

        <div className="table-scroll" ref={tableRef} onScroll={handleTableScroll}>
          <table className="balance-table">
            <thead>
              <tr>
                <th className="sticky-company"><button type="button" onClick={() => toggleSort("company_name")}>Company <span>{sortIndicator("company_name")}</span></button></th>
                <th><button type="button" onClick={() => toggleSort("type")}>Attribute <span>{sortIndicator("type")}</span></button></th>
                {years.map((year) => <th key={year} className="numeric-heading"><button type="button" onClick={() => toggleSort(String(year))}>{year} <span>{sortIndicator(String(year))}</span></button></th>)}
                <th><button type="button" onClick={() => toggleSort("trailing")}>Trailing <span>{sortIndicator("trailing")}</span></button></th>
                <th><button type="button" onClick={() => toggleSort("audit_date")}>Audit date <span>{sortIndicator("audit_date")}</span></button></th>
                <th className="numeric-heading"><button type="button" onClick={() => toggleSort("aging_days")}>Days <span>{sortIndicator("aging_days")}</span></button></th>
                <th className="numeric-heading"><button type="button" onClick={() => toggleSort("aging_months")}>Months <span>{sortIndicator("aging_months")}</span></button></th>
                <th className="numeric-heading"><button type="button" onClick={() => toggleSort("aging_years")}>Years <span>{sortIndicator("aging_years")}</span></button></th>
                <th><button type="button" onClick={() => toggleSort("reminder")}>Reminder <span>{sortIndicator("reminder")}</span></button></th>
              </tr>
            </thead>
            <tbody>
              {sortedData.length === 0 && !loading ? (
                <tr><td className="empty-state" colSpan={years.length + 8}><span className="empty-icon">⌕</span><strong>No records found</strong><span>Try changing your search or filters.</span></td></tr>
              ) : sortedData.map((row, index) => (
                <tr key={row.id ?? `${row.file_name}-${row.type}-${index}`}>
                  <td className="sticky-company company-cell" title={getCompanyName(row.file_name)}>{getCompanyName(row.file_name) || "—"}</td>
                  <td><span className="type-pill">{row.type || "—"}</span></td>
                  {years.map((year) => (
  <td key={year} className="numeric-cell">
    {formatDecimal(row?.years?.[year] ?? row?.years?.[String(year)])}
  </td>
))}
                  <td>{formatDecimal(getCellValue(row, "trailing"))}</td>
                  <td>{row.audit_date ? new Date(row.audit_date).toLocaleDateString("en-GB") : "—"}</td>
                  <td className="numeric-cell">{getCellValue(row, "aging_days") || "—"}</td>
                  <td className="numeric-cell">{getCellValue(row, "aging_months") || "—"}</td>
                  <td className="numeric-cell">{getCellValue(row, "aging_years") || "—"}</td>
                  <td>{getCellValue(row, "reminder") || "—"}</td>
                </tr>
              ))}
            </tbody>
          </table>
          {loading && <div className="table-loading"><span className="spinner" />{data.length ? "Loading more records…" : "Loading balance entries…"}</div>}
        </div>
        <footer className="table-footer">
          <span>Showing {sortedData.length.toLocaleString()} of {data.length.toLocaleString()} loaded records</span>
          {nextUrl && <button type="button" className="text-button" disabled={loading} onClick={() => fetchData()}>{loading ? "Loading…" : "Load more"}</button>}
        </footer>
      </section>

      {yearModalOpen && (
        <div className="modal-backdrop" role="presentation" onMouseDown={(event) => { if (event.target === event.currentTarget && !importing) setYearModalOpen(false); }}>
          <section className="import-modal" role="dialog" aria-modal="true" aria-labelledby="import-title">
            <div className="modal-icon">↑</div>
            <h2 id="import-title">Choose reporting year</h2>
            <p>{pendingFiles.length} Excel file{pendingFiles.length === 1 ? "" : "s"} selected. Choose the year to associate with this import.</p>
            <label htmlFor="import-year">Reporting year</label>
            <select id="import-year" value={selectedYear} onChange={(event) => setSelectedYear(event.target.value)}>
              <option value="">Select a year…</option>
              {IMPORT_YEARS.map((year) => <option key={year} value={year}>{year}</option>)}
            </select>
            <div className="selected-files">
              {pendingFiles.slice(0, 3).map((file) => <span key={`${file.name}-${file.lastModified}`}>▤ {file.name}</span>)}
              {pendingFiles.length > 3 && <span>+ {pendingFiles.length - 3} more files</span>}
            </div>
            <div className="modal-actions">
              <button type="button" className="button button-secondary" disabled={importing} onClick={() => { setYearModalOpen(false); setPendingFiles([]); }}>Cancel</button>
              <button type="button" className="button button-primary" disabled={!selectedYear || !pendingFiles.length || importing} onClick={startImport}>
                {importing ? "Importing…" : "Import files"}
              </button>
            </div>
          </section>
        </div>
      )}
    </main>
  );
}

export default BalanceSheet;
