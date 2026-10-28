
import React, { useCallback, useEffect, useMemo, useState } from "react";
import {
  Activity,
  AlertCircle,
  CheckCircle2,
  Clock,
  FileSpreadsheet,
  FolderOpen,
  LoaderCircle,
  RefreshCw,
  Search,
  ShieldCheck,
  SlidersHorizontal,
  X,
} from "lucide-react";
import "./BalanceSheet.css";

const API_URL = "http://localhost:8000/api/screener_logs/";
const PAGE_SIZE = 10;

const DATE_FILTERS = [
  { value: "all", label: "All dates" },
  { value: "today", label: "Today" },
  { value: "yesterday", label: "Yesterday" },
  { value: "7days", label: "Last 7 days" },
  { value: "30days", label: "Last 30 days" },
  { value: "custom", label: "Custom date range" },
];

const STATUS_FILTERS = [
  { value: "all", label: "All statuses" },
  { value: "failed", label: "Failed downloads" },
  { value: "success", label: "Successful downloads" },
  { value: "progress", label: "In progress" },
  { value: "neutral", label: "Other statuses" },
];

function getStatusType(status) {
  const value = String(status ?? "").toLowerCase();

  if (value.includes("fail") || value.includes("error")) {
    return "failed";
  }

  if (value.includes("success") || value.includes("completed")) {
    return "success";
  }

  if (
    value.includes("progress") ||
    value.includes("pending") ||
    value.includes("running")
  ) {
    return "progress";
  }

  return "neutral";
}

function parseLogDate(value) {
  if (!value) return null;

  // Handle YYYY-MM-DD as a local calendar date.
  const dateOnlyMatch = String(value).match(/^(\d{4})-(\d{2})-(\d{2})$/);

  if (dateOnlyMatch) {
    const [, year, month, day] = dateOnlyMatch;
    const date = new Date(
      Number(year),
      Number(month) - 1,
      Number(day)
    );

    return Number.isNaN(date.getTime()) ? null : date;
  }

  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? null : date;
}

function getLocalDateKey(date) {
  const year = date.getFullYear();
  const month = String(date.getMonth() + 1).padStart(2, "0");
  const day = String(date.getDate()).padStart(2, "0");

  return `${year}-${month}-${day}`;
}

function getStatusIcon(status) {
  const type = getStatusType(status);

  if (type === "success") return <CheckCircle2 size={15} />;
  if (type === "failed") return <AlertCircle size={15} />;
  if (type === "progress") return <LoaderCircle size={15} />;

  return <Clock size={15} />;
}

function formatDate(value) {
  const date = parseLogDate(value);

  if (!date) return value || "—";

  return date.toLocaleString([], {
    day: "2-digit",
    month: "short",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

export default function LogsPage() {
  const [logs, setLogs] = useState([]);
  const [searchTerm, setSearchTerm] = useState("");
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState("");
  const [lastUpdated, setLastUpdated] = useState(null);

  const [dateFilter, setDateFilter] = useState("all");
  const [statusFilter, setStatusFilter] = useState("all");
  const [sortOrder, setSortOrder] = useState("latest");
  const [startDate, setStartDate] = useState("");
  const [endDate, setEndDate] = useState("");

  const [currentPage, setCurrentPage] = useState(1);

  const fetchLogs = useCallback(async (manual = false) => {
    if (manual) setRefreshing(true);

    try {
      const response = await fetch(API_URL);

      if (!response.ok) {
        throw new Error(`Server returned HTTP ${response.status}`);
      }

      const data = await response.json();

      if (!Array.isArray(data.logs)) {
        throw new Error("Unexpected response from the logs API.");
      }

      setLogs(data.logs);
      setError("");
      setLastUpdated(new Date());
    } catch (err) {
      console.error("Error fetching Screener logs:", err);
      setError(
        "Unable to load download logs. Check that the Django server is running."
      );
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, []);

  useEffect(() => {
    fetchLogs();

    const interval = setInterval(() => {
      fetchLogs();
    }, 5000);

    return () => clearInterval(interval);
  }, [fetchLogs]);

  const filteredLogs = useMemo(() => {
    const query = searchTerm.trim().toLowerCase();
    const now = new Date();

    const todayKey = getLocalDateKey(now);
    const yesterday = new Date(now);
    yesterday.setDate(yesterday.getDate() - 1);
    const yesterdayKey = getLocalDateKey(yesterday);

    const todayStart = new Date(now.getFullYear(), now.getMonth(), now.getDate());
    const yesterdayStart = new Date(todayStart);
    yesterdayStart.setDate(yesterdayStart.getDate() - 1);

    const sevenDaysAgo = new Date(todayStart);
    sevenDaysAgo.setDate(sevenDaysAgo.getDate() - 6);

    const thirtyDaysAgo = new Date(todayStart);
    thirtyDaysAgo.setDate(thirtyDaysAgo.getDate() - 29);

    return logs
      .filter((log) => {
        // Search filter
        if (query) {
          const matchesSearch = [
            log.symbol,
            log.company_name,
            log.file_name,
            log.file_path,
            log.status,
            log.date,
            log.screener_url,
          ].some((value) =>
            String(value ?? "").toLowerCase().includes(query)
          );

          if (!matchesSearch) return false;
        }

        // Status filter
        if (
          statusFilter !== "all" &&
          getStatusType(log.status) !== statusFilter
        ) {
          return false;
        }

        // Date filter
        if (dateFilter !== "all") {
          const logDate = parseLogDate(log.date);

          // Records without a valid date cannot match a date filter.
          if (!logDate) return false;

          const logDateKey = getLocalDateKey(logDate);

          if (dateFilter === "today" && logDateKey !== todayKey) {
            return false;
          }

          if (
            dateFilter === "yesterday" &&
            logDateKey !== yesterdayKey
          ) {
            return false;
          }

          if (
            dateFilter === "7days" &&
            (logDate < sevenDaysAgo || logDate >= new Date(todayStart.getTime() + 86400000))
          ) {
            return false;
          }

          if (
            dateFilter === "30days" &&
            (logDate < thirtyDaysAgo || logDate >= new Date(todayStart.getTime() + 86400000))
          ) {
            return false;
          }

          if (dateFilter === "custom") {
            const logDay = getLocalDateKey(logDate);

            if (startDate && logDay < startDate) return false;
            if (endDate && logDay > endDate) return false;
          }
        }

        return true;
      })
      .sort((a, b) => {
        const dateA = parseLogDate(a.date)?.getTime() ?? 0;
        const dateB = parseLogDate(b.date)?.getTime() ?? 0;

        return sortOrder === "latest" ? dateB - dateA : dateA - dateB;
      });
  }, [
    logs,
    searchTerm,
    dateFilter,
    statusFilter,
    sortOrder,
    startDate,
    endDate,
  ]);

  // Keep the page valid when filters change or new logs arrive.
  useEffect(() => {
    setCurrentPage(1);
  }, [searchTerm, dateFilter, statusFilter, sortOrder, startDate, endDate]);

  const totalPages = Math.max(
    1,
    Math.ceil(filteredLogs.length / PAGE_SIZE)
  );

  const safeCurrentPage = Math.min(currentPage, totalPages);
  const startIndex = (safeCurrentPage - 1) * PAGE_SIZE;

  const paginatedLogs = filteredLogs.slice(
    startIndex,
    startIndex + PAGE_SIZE
  );

  const successCount = filteredLogs.filter(
    (log) => getStatusType(log.status) === "success"
  ).length;

  const failedCount = filteredLogs.filter(
    (log) => getStatusType(log.status) === "failed"
  ).length;

  const otherCount = filteredLogs.length - successCount - failedCount;

  const clearFilters = () => {
    setSearchTerm("");
    setDateFilter("all");
    setStatusFilter("all");
    setSortOrder("latest");
    setStartDate("");
    setEndDate("");
    setCurrentPage(1);
  };

  const hasActiveFilters =
    searchTerm.trim() !== "" ||
    dateFilter !== "all" ||
    statusFilter !== "all" ||
    sortOrder !== "latest" ||
    startDate !== "" ||
    endDate !== "";

  const getPageNumbers = () => {
    const pages = [];
    const first = Math.max(1, safeCurrentPage - 2);
    const last = Math.min(totalPages, safeCurrentPage + 2);

    if (first > 1) {
      pages.push(1);
      if (first > 2) pages.push("...");
    }

    for (let page = first; page <= last; page += 1) {
      pages.push(page);
    }

    if (last < totalPages) {
      if (last < totalPages - 1) pages.push("...");
      pages.push(totalPages);
    }

    return pages;
  };

  const openFileLocation = async (filePath) => {
    if (!filePath) return;

    try {
      await navigator.clipboard.writeText(filePath);
    } catch (err) {
      console.error("Could not copy file path:", err);
      window.prompt("Copy this file path:", filePath);
    }
  };

  return (
    <main className="logs-page">
      <div className="logs-container">
        <header className="logs-header">
          <div className="logs-heading">
            <div className="logs-title-icon">
              <Activity size={25} strokeWidth={2.2} />
            </div>

            <div>
              <div className="logs-eyebrow">AUTOMATION CENTER</div>
              <h1>Screener Download Logs</h1>
              <p>
                Monitor downloaded company reports and track failed downloads.
              </p>
            </div>
          </div>

          <button
            type="button"
            className="logs-refresh-button"
            onClick={() => fetchLogs(true)}
            disabled={refreshing}
          >
            <RefreshCw
              size={17}
              className={refreshing ? "logs-spinning" : ""}
            />
            <span>{refreshing ? "Refreshing..." : "Refresh logs"}</span>
          </button>
        </header>

        <section className="logs-summary" aria-label="Download summary">
          <article className="logs-summary-card">
            <div className="logs-summary-icon logs-icon-blue">
              <FileSpreadsheet size={21} />
            </div>
            <div className="logs-summary-content">
              <span className="logs-summary-label">Matching records</span>
              <strong>{filteredLogs.length}</strong>
              <span className="logs-summary-note">After applying filters</span>
            </div>
          </article>

          <article className="logs-summary-card">
            <div className="logs-summary-icon logs-icon-green">
              <CheckCircle2 size={21} />
            </div>
            <div className="logs-summary-content">
              <span className="logs-summary-label">Successful</span>
              <strong>{successCount}</strong>
              <span className="logs-summary-note">In filtered results</span>
            </div>
          </article>

          <article className="logs-summary-card">
            <div className="logs-summary-icon logs-icon-red">
              <AlertCircle size={21} />
            </div>
            <div className="logs-summary-content">
              <span className="logs-summary-label">Failed</span>
              <strong>{failedCount}</strong>
              <span className="logs-summary-note">In filtered results</span>
            </div>
          </article>

          <article className="logs-summary-card">
            <div className="logs-summary-icon logs-icon-amber">
              <Clock size={21} />
            </div>
            <div className="logs-summary-content">
              <span className="logs-summary-label">Other statuses</span>
              <strong>{otherCount}</strong>
              <span className="logs-summary-note">Pending or unclassified</span>
            </div>
          </article>
        </section>

        <section className="logs-table-card">
          <div className="logs-table-header">
            <div>
              <h2>Download history</h2>
              <p>Filter by date and status to find problem downloads quickly.</p>
            </div>

            <div className="logs-live-indicator">
              <span className="logs-live-dot" />
              Auto-refresh · 5 sec
            </div>
          </div>

          <div className="logs-filters">
            <div className="logs-filters-title">
              <SlidersHorizontal size={18} />
              <strong>Filter downloads</strong>
            </div>

            <div className="logs-filter-grid">
              <label className="logs-filter-field">
                <span>Date range</span>
                <select
                  value={dateFilter}
                  onChange={(event) => setDateFilter(event.target.value)}
                >
                  {DATE_FILTERS.map((option) => (
                    <option key={option.value} value={option.value}>
                      {option.label}
                    </option>
                  ))}
                </select>
              </label>

              <label className="logs-filter-field">
                <span>Download status</span>
                <select
                  value={statusFilter}
                  onChange={(event) => setStatusFilter(event.target.value)}
                >
                  {STATUS_FILTERS.map((option) => (
                    <option key={option.value} value={option.value}>
                      {option.label}
                    </option>
                  ))}
                </select>
              </label>

              <label className="logs-filter-field">
                <span>Sort by date</span>
                <select
                  value={sortOrder}
                  onChange={(event) => setSortOrder(event.target.value)}
                >
                  <option value="latest">Latest first</option>
                  <option value="oldest">Oldest first</option>
                </select>
              </label>
            </div>

            {dateFilter === "custom" && (
              <div className="logs-custom-date-row">
                <label className="logs-filter-field">
                  <span>From date</span>
                  <input
                    type="date"
                    value={startDate}
                    max={endDate || undefined}
                    onChange={(event) => setStartDate(event.target.value)}
                  />
                </label>

                <label className="logs-filter-field">
                  <span>To date</span>
                  <input
                    type="date"
                    value={endDate}
                    min={startDate || undefined}
                    onChange={(event) => setEndDate(event.target.value)}
                  />
                </label>
              </div>
            )}

            <div className="logs-filter-bottom">
              <span>
                Showing {filteredLogs.length} of {logs.length} total records
              </span>

              {hasActiveFilters && (
                <button
                  type="button"
                  className="logs-clear-filters"
                  onClick={clearFilters}
                >
                  <X size={15} />
                  Clear all filters
                </button>
              )}
            </div>
          </div>

          <div className="logs-toolbar">
            <div className="logs-search">
              <Search size={18} />
              <input
                type="search"
                placeholder="Search symbol, company, file name or path..."
                value={searchTerm}
                onChange={(event) => setSearchTerm(event.target.value)}
                aria-label="Search download logs"
              />

              {searchTerm && (
                <button
                  type="button"
                  className="logs-clear-search"
                  onClick={() => setSearchTerm("")}
                  aria-label="Clear search"
                >
                  ×
                </button>
              )}
            </div>

            <span className="logs-result-count">
              {filteredLogs.length}{" "}
              {filteredLogs.length === 1 ? "record" : "records"}
            </span>
          </div>

          {error && (
            <div className="logs-error-banner" role="alert">
              <AlertCircle size={18} />
              <span>{error}</span>
              <button type="button" onClick={() => fetchLogs(true)}>
                Try again
              </button>
            </div>
          )}

          <div className="logs-table-scroll">
            <table className="logs-table">
              <thead>
                <tr>
                  <th>Company symbol</th>
                  <th>Company name</th>
                  <th>File name</th>
                  <th>Screener Page</th>
                  <th>File location</th>
                  <th>Status</th>
                  <th>Download date</th>
                </tr>
              </thead>

              <tbody>
                {loading ? (
                  <tr>
                    <td colSpan={7} className="logs-state-cell">
                      <LoaderCircle
                        size={25}
                        className="logs-state-spinner"
                      />
                      <strong>Loading download logs...</strong>
                      <span>Retrieving the latest records.</span>
                    </td>
                  </tr>
                ) : paginatedLogs.length > 0 ? (
                  paginatedLogs.map((log, index) => (
                    <tr
                      key={`${log.symbol || "log"}-${log.file_name || "file"}-${log.date || index}-${index}`}
                    >
                      <td>
                        <span className="logs-symbol">
                          {log.symbol || "—"}
                        </span>
                      </td>

                      <td>
                        <span className="logs-company-name">
                          {log.company_name || "—"}
                        </span>
                      </td>

                      <td>
                        <div className="logs-file-name">
                          <div className="logs-file-icon">
                            <FileSpreadsheet size={17} />
                          </div>
                          <span title={log.file_name || ""}>
                            {log.file_name || "Unnamed file"}
                          </span>
                        </div>
                      </td>

                      <td>
                        {log.screener_url ? (
                          <a
                            href={log.screener_url}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="logs-screener-link"
                          >
                            Open Screener ↗
                          </a>
                        ) : (
                          <span className="logs-muted">Not available</span>
                        )}
                      </td>

                      <td>
                        {log.file_path ? (
                          <button
                            type="button"
                            className="logs-path-button"
                            title="Copy file path"
                            onClick={() => openFileLocation(log.file_path)}
                          >
                            <FolderOpen size={16} />
                            <span>{log.file_path}</span>
                          </button>
                        ) : (
                          <span className="logs-muted">Not available</span>
                        )}
                      </td>

                      <td>
                        <span
                          className={`logs-status logs-status-${getStatusType(
                            log.status
                          )}`}
                        >
                          {getStatusIcon(log.status)}
                          {log.status || "Unknown"}
                        </span>
                      </td>

                      <td>
                        <span className="logs-date">
                          {formatDate(log.date)}
                        </span>
                      </td>
                    </tr>
                  ))
                ) : (
                  <tr>
                    <td colSpan={7} className="logs-state-cell">
                      <div className="logs-empty-icon">
                        <FileSpreadsheet size={26} />
                      </div>

                      <strong>
                        {hasActiveFilters
                          ? "No matching download records"
                          : "No download logs yet"}
                      </strong>

                      <span>
                        {hasActiveFilters
                          ? "Try changing the date or status filters."
                          : "Start a Screener download to see records here."}
                      </span>

                      {hasActiveFilters && (
                        <button
                          type="button"
                          className="logs-reset-button"
                          onClick={clearFilters}
                        >
                          Clear all filters
                        </button>
                      )}
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>

          {!loading && filteredLogs.length > 0 && (
            <div className="logs-pagination">
              <div className="logs-pagination-info">
                Showing{" "}
                <strong>{startIndex + 1}</strong>–
                <strong>
                  {Math.min(startIndex + PAGE_SIZE, filteredLogs.length)}
                </strong>{" "}
                of <strong>{filteredLogs.length}</strong> records
              </div>

              <div className="logs-pagination-controls" aria-label="Pagination">
                <button
                  type="button"
                  className="logs-page-button logs-page-direction"
                  onClick={() =>
                    setCurrentPage((page) => Math.max(1, page - 1))
                  }
                  disabled={safeCurrentPage === 1}
                  aria-label="Previous page"
                >
                  Previous
                </button>

                {getPageNumbers().map((page, index) =>
                  page === "..." ? (
                    <span
                      className="logs-page-ellipsis"
                      key={`ellipsis-${index}`}
                      aria-hidden="true"
                    >
                      …
                    </span>
                  ) : (
                    <button
                      type="button"
                      key={page}
                      className={`logs-page-button ${
                        safeCurrentPage === page ? "active" : ""
                      }`}
                      onClick={() => setCurrentPage(page)}
                      aria-current={
                        safeCurrentPage === page ? "page" : undefined
                      }
                      aria-label={`Page ${page}`}
                    >
                      {page}
                    </button>
                  )
                )}

                <button
                  type="button"
                  className="logs-page-button logs-page-direction"
                  onClick={() =>
                    setCurrentPage((page) =>
                      Math.min(totalPages, page + 1)
                    )
                  }
                  disabled={safeCurrentPage === totalPages}
                  aria-label="Next page"
                >
                  Next
                </button>
              </div>
            </div>
          )}

          <footer className="logs-table-footer">
            <div className="logs-footer-security">
              <ShieldCheck size={16} />
              <span>Local download monitoring</span>
            </div>

            <span className="logs-updated">
              Last updated:{" "}
              {lastUpdated
                ? lastUpdated.toLocaleTimeString([], {
                    hour: "2-digit",
                    minute: "2-digit",
                    second: "2-digit",
                  })
                : "Waiting for data"}
            </span>
          </footer>
        </section>

        <p className="logs-page-note">
          Download history refreshes automatically while this page is open.
        </p>
      </div>
    </main>
  );
}
