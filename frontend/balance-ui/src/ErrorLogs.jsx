
import React, { useEffect, useMemo, useState } from "react";
import axios from "axios";
import "./BalanceSheet.css";

const API_URL = "http://localhost:8000/api/error-logs/";

const errorLabels = [
  "Missing in NSC",
  "Missing in mapping",
  "Missing in MCAP",
  "Calculation failed",
  "Screener download failed",
  "Missing TTM P/E",
  "Missing Stock P/E",
  "Missing Industry P/E",
];

const getErrorStyle = (label = "") => {
  switch (label) {
    case "Calculation failed":
    case "Screener download failed":
      return { className: "error-badge--danger", dot: "danger" };

    case "Missing in NSC":
    case "Missing in mapping":
    case "Missing in MCAP":
      return { className: "error-badge--warning", dot: "warning" };

    case "Missing TTM P/E":
    case "Missing Stock P/E":
    case "Missing Industry P/E":
      return { className: "error-badge--info", dot: "info" };

    default:
      return { className: "error-badge--neutral", dot: "neutral" };
  }
};

const formatDate = (value) => {
  if (!value) return "—";

  const date = new Date(value);

  if (Number.isNaN(date.getTime())) return "—";

  return new Intl.DateTimeFormat(undefined, {
    year: "numeric",
    month: "short",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
    hour12: true,
  }).format(date);
};

const ErrorLogs = () => {
  const [selectedLabel, setSelectedLabel] = useState("");
  const [logs, setLogs] = useState([]);
  const [searchTerm, setSearchTerm] = useState("");
  const [sortOrder, setSortOrder] = useState("newest");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    if (!selectedLabel) {
      setLogs([]);
      setError("");
      setLoading(false);
      return;
    }

    const controller = new AbortController();

    const fetchLogs = async () => {
      setLoading(true);
      setError("");

      try {
        const response = await axios.get(API_URL, {
          params: { error_type: selectedLabel },
          signal: controller.signal,
        });

        if (!Array.isArray(response.data)) {
          throw new Error("The API returned an unexpected response.");
        }

        setLogs(response.data);
      } catch (err) {
        if (
          err.code === "ERR_CANCELED" ||
          axios.isCancel(err)
        ) {
          return;
        }

        console.error("Failed to fetch error logs:", err);
        setLogs([]);
        setError(
          err.response
            ? `Unable to load logs (HTTP ${err.response.status}).`
            : "Unable to connect to the server. Please try again."
        );
      } finally {
        if (!controller.signal.aborted) {
          setLoading(false);
        }
      }
    };

    fetchLogs();

    return () => controller.abort();
  }, [selectedLabel]);

  const filteredLogs = useMemo(() => {
    const query = searchTerm.trim().toLowerCase();

    return [...logs]
      .filter((log) => {
        if (!query) return true;

        return [
          log.equity_symbol,
          log.company_name,
          log.source,
          log.error_type_display,
        ].some((value) =>
          String(value ?? "").toLowerCase().includes(query)
        );
      })
      .sort((a, b) => {
        const dateA = new Date(a.created_at).getTime() || 0;
        const dateB = new Date(b.created_at).getTime() || 0;

        return sortOrder === "newest"
          ? dateB - dateA
          : dateA - dateB;
      });
  }, [logs, searchTerm, sortOrder]);

  const uniqueCompanies = useMemo(() => {
    return new Set(
      logs.map((log) => log.equity_symbol).filter(Boolean)
    ).size;
  }, [logs]);

  const latestLog = useMemo(() => {
    return logs.reduce((latest, log) => {
      const timestamp = new Date(log.created_at).getTime();

      if (!Number.isFinite(timestamp)) return latest;

      return timestamp > latest ? timestamp : latest;
    }, 0);
  }, [logs]);

  const handleRetry = () => {
    // Re-trigger the effect without changing the selected filter.
    setError("");
    setSelectedLabel((current) => {
      if (!current) return current;
      return current;
    });

    // Fetch directly so Retry works for the currently selected label.
    if (!selectedLabel) return;

    const controller = new AbortController();

    setLoading(true);
    axios
      .get(API_URL, {
        params: { error_type: selectedLabel },
        signal: controller.signal,
      })
      .then((response) => {
        if (!Array.isArray(response.data)) {
          throw new Error("The API returned an unexpected response.");
        }
        setLogs(response.data);
        setError("");
      })
      .catch((err) => {
        if (axios.isCancel(err) || err.code === "ERR_CANCELED") return;

        setLogs([]);
        setError("Unable to reload logs. Please try again.");
      })
      .finally(() => setLoading(false));
  };

  return (
    <main className="error-dashboard">
      <header className="dashboard-header">
        <div className="dashboard-heading">
          <div className="dashboard-icon" aria-hidden="true">
            <svg
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="1.8"
            >
              <path d="M12 3 2.8 20h18.4L12 3Z" />
              <path d="M12 9v4.5M12 17h.01" />
            </svg>
          </div>

          <div>
            <p className="eyebrow">SYSTEM MONITORING</p>
            <h1>Error Logs</h1>
            <p className="dashboard-subtitle">
              Monitor data quality issues and investigate failed operations.
            </p>
          </div>
        </div>

        <div className="connection-indicator">
          <span className="connection-dot" />
          Error monitoring
        </div>
      </header>

      <section className="error-summary" aria-label="Log summary">
        <article className="summary-card">
          <div className="summary-card-top">
            <span className="summary-label">Total log entries</span>
            <span className="summary-icon summary-icon--blue">#</span>
          </div>
          <strong className="summary-value">
            {selectedLabel && !loading && !error
              ? filteredLogs.length.toLocaleString()
              : "—"}
          </strong>
          <span className="summary-caption">
            {searchTerm ? "Matching search results" : "Current filter"}
          </span>
        </article>

        <article className="summary-card">
          <div className="summary-card-top">
            <span className="summary-label">Unique equities</span>
            <span className="summary-icon summary-icon--purple">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8">
                <circle cx="9" cy="8" r="3" />
                <path d="M3.5 19v-1.5a5.5 5.5 0 0 1 11 0V19M16 5.5a3 3 0 0 1 0 5.8M17 14a4.5 4.5 0 0 1 3.5 4.5V19" />
              </svg>
            </span>
          </div>
          <strong className="summary-value">
            {selectedLabel && !loading && !error
              ? uniqueCompanies.toLocaleString()
              : "—"}
          </strong>
          <span className="summary-caption">Symbols represented in logs</span>
        </article>

        <article className="summary-card">
          <div className="summary-card-top">
            <span className="summary-label">Error categories</span>
            <span className="summary-icon summary-icon--amber">!</span>
          </div>
          <strong className="summary-value">{errorLabels.length}</strong>
          <span className="summary-caption">Available filters</span>
        </article>

        <article className="summary-card">
          <div className="summary-card-top">
            <span className="summary-label">Latest occurrence</span>
            <span className="summary-icon summary-icon--green">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8">
                <circle cx="12" cy="12" r="9" />
                <path d="M12 7v5l3.5 2" />
              </svg>
            </span>
          </div>
          <strong className="summary-date">
            {selectedLabel && latestLog && !loading && !error
              ? formatDate(latestLog)
              : "—"}
          </strong>
          <span className="summary-caption">Based on loaded records</span>
        </article>
      </section>

      <section className="logs-panel">
        <div className="panel-header">
          <div>
            <h2>Log explorer</h2>
            <p>Filter, search, and review recorded errors.</p>
          </div>

          {selectedLabel && (
            <span className="selected-count">
              {loading ? "Loading…" : `${filteredLogs.length} records`}
            </span>
          )}
        </div>

        <div className="filters-toolbar">
          <div className="filter-field">
            <label htmlFor="error-type">Error category</label>
            <select
              id="error-type"
              value={selectedLabel}
              onChange={(e) => {
                setSelectedLabel(e.target.value);
                setSearchTerm("");
              }}
            >
              <option value="">Select an error type</option>
              {errorLabels.map((label) => (
                <option key={label} value={label}>
                  {label}
                </option>
              ))}
            </select>
          </div>

          <div className="search-field">
            <label htmlFor="log-search">Search records</label>
            <div className="search-input-wrap">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8">
                <circle cx="10.8" cy="10.8" r="6.8" />
                <path d="m16 16 4.5 4.5" />
              </svg>
              <input
                id="log-search"
                type="search"
                placeholder="Search symbol, company, source…"
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                disabled={!selectedLabel || loading || !!error}
              />
            </div>
          </div>

          <div className="sort-field">
            <label htmlFor="log-sort">Sort by date</label>
            <select
              id="log-sort"
              value={sortOrder}
              onChange={(e) => setSortOrder(e.target.value)}
              disabled={!selectedLabel || loading || !!error}
            >
              <option value="newest">Newest first</option>
              <option value="oldest">Oldest first</option>
            </select>
          </div>

          <button
            className="refresh-button"
            type="button"
            onClick={handleRetry}
            disabled={!selectedLabel || loading}
          >
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8">
              <path d="M20 7v5h-5M4 17v-5h5" />
              <path d="M5.5 9a7 7 0 0 1 12-2L20 12M4 12l2.5 5a7 7 0 0 0 12-2" />
            </svg>
            Refresh
          </button>
        </div>

        {loading && (
          <div className="state-container" role="status" aria-live="polite">
            <span className="loading-spinner" />
            <strong>Loading error logs</strong>
            <p>Retrieving records for the selected category…</p>
          </div>
        )}

        {!loading && error && (
          <div className="state-container state-container--error" role="alert">
            <div className="state-icon state-icon--error">!</div>
            <strong>Unable to load logs</strong>
            <p>{error}</p>
            <button className="retry-button" onClick={handleRetry} type="button">
              Try again
            </button>
          </div>
        )}

        {!loading && !error && !selectedLabel && (
          <div className="state-container">
            <div className="state-icon">⌕</div>
            <strong>Select an error category</strong>
            <p>Choose a category above to inspect its log entries.</p>
          </div>
        )}

        {!loading && !error && selectedLabel && filteredLogs.length === 0 && (
          <div className="state-container">
            <div className="state-icon state-icon--success">✓</div>
            <strong>{logs.length ? "No matching records" : "No logs found"}</strong>
            <p>
              {logs.length
                ? "Try another search term."
                : `No logs were returned for "${selectedLabel}".`}
            </p>
            {searchTerm && (
              <button
                className="retry-button"
                onClick={() => setSearchTerm("")}
                type="button"
              >
                Clear search
              </button>
            )}
          </div>
        )}

        {!loading && !error && filteredLogs.length > 0 && (
          <>
            <div className="table-scroll">
              <table className="logs-table">
                <thead>
                  <tr>
                    <th>Equity</th>
                    <th>Company</th>
                    <th>Source</th>
                    <th>Created at</th>
                    <th>Error category</th>
                  </tr>
                </thead>
                <tbody>
                  {filteredLogs.map((log) => {
                    const style = getErrorStyle(log.error_type_display);

                    return (
                      <tr key={log.id}>
                        <td>
                          <span className="equity-symbol">
                            {log.equity_symbol || "—"}
                          </span>
                        </td>
                        <td>
                          <span className="company-name">
                            {log.company_name || "Unknown company"}
                          </span>
                        </td>
                        <td>
                          <span className="source-label">
                            {log.source || "—"}
                          </span>
                        </td>
                        <td>
                          <time
                            className="created-at"
                            dateTime={log.created_at || undefined}
                          >
                            {formatDate(log.created_at)}
                          </time>
                        </td>
                        <td>
                          <span className={`error-badge ${style.className}`}>
                            <span className={`badge-dot badge-dot--${style.dot}`} />
                            {log.error_type_display || "Unknown"}
                          </span>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>

            <footer className="table-footer">
              <span>
                Showing <strong>{filteredLogs.length.toLocaleString()}</strong>
                {filteredLogs.length !== logs.length && (
                  <> of <strong>{logs.length.toLocaleString()}</strong></>
                )}{" "}
                records
              </span>
              <span className="footer-category">
                Category: <strong>{selectedLabel}</strong>
              </span>
            </footer>
          </>
        )}
      </section>

      <footer className="dashboard-footer">
        Error Logs Dashboard <span>·</span> Data quality monitoring
      </footer>
    </main>
  );
};

export default ErrorLogs;
