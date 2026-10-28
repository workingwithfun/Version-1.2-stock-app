
import React, { useCallback, useEffect, useMemo, useState } from "react";
import {
  ArrowLeft,
  CheckCircle2,
  XCircle,
  RefreshCw,
  Search,
  Clock3,
  FileSpreadsheet,
  AlertCircle,
} from "lucide-react";
import { useNavigate } from "react-router-dom";
import "./BalanceSheet.css";

const API_URL = "http://localhost:8000/api/recalculation-logs/";
const PAGE_SIZE = 15;

function formatDate(value) {
  if (!value) return "—";

  const date = new Date(value);

  if (Number.isNaN(date.getTime())) return "—";

  return date.toLocaleString();
}

function RecalculationLogsPage() {
  const navigate = useNavigate();

  const [logs, setLogs] = useState([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState("");
  const [search, setSearch] = useState("");
  const [statusFilter, setStatusFilter] = useState("all");
  const [page, setPage] = useState(1);
  const [expandedErrors, setExpandedErrors] = useState({});

  const loadLogs = useCallback(async (isRefresh = false) => {
    if (isRefresh) {
      setRefreshing(true);
    } else {
      setLoading(true);
    }

    setError("");

    try {
      const response = await fetch(API_URL);

      if (!response.ok) {
        throw new Error(
          `Unable to load recalculation history (HTTP ${response.status}).`
        );
      }

      const data = await response.json();
      setLogs(Array.isArray(data.results) ? data.results : []);
    } catch (err) {
      setError(
        err.message ||
          "Could not load recalculation history. Check that Django is running."
      );
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, []);

  useEffect(() => {
    loadLogs();
  }, [loadLogs]);

  const filteredLogs = useMemo(() => {
    const query = search.trim().toLowerCase();

    return logs.filter((log) => {
      const matchesStatus =
        statusFilter === "all" || log.status === statusFilter;

      const searchableText = [
        log.company_name,
        log.company_symbol,
        log.file_name,
        log.error,
        log.run_id,
      ]
        .filter(Boolean)
        .join(" ")
        .toLowerCase();

      return matchesStatus && (!query || searchableText.includes(query));
    });
  }, [logs, search, statusFilter]);

  const successCount = logs.filter(
    (log) => log.status === "success"
  ).length;

  const failedCount = logs.filter(
    (log) => log.status === "failed"
  ).length;

  const totalPages = Math.max(
    1,
    Math.ceil(filteredLogs.length / PAGE_SIZE)
  );

  const safePage = Math.min(page, totalPages);

  const visibleLogs = filteredLogs.slice(
    (safePage - 1) * PAGE_SIZE,
    safePage * PAGE_SIZE
  );

  useEffect(() => {
    setPage(1);
  }, [search, statusFilter]);

  const toggleError = (id) => {
    setExpandedErrors((previous) => ({
      ...previous,
      [id]: !previous[id],
    }));
  };

  return (
    <div className="recalc-history-page">
      <div className="recalc-history-header">
        <button
          type="button"
          className="recalc-back-button"
          onClick={() => navigate("/search")}
        >
          <ArrowLeft size={18} />
          Back to Search
        </button>

        <div className="recalc-heading-row">
          <div className="recalc-heading-icon">
            <FileSpreadsheet size={26} />
          </div>

          <div>
            <h1>Excel Recalculation History</h1>
            <p>
              Review saved recalculation results for your Screener Excel files.
            </p>
          </div>

          <button
            type="button"
            className="recalc-refresh-button"
            onClick={() => loadLogs(true)}
            disabled={loading || refreshing}
          >
            <RefreshCw
              size={17}
              className={refreshing ? "recalc-spinning" : ""}
            />
            {refreshing ? "Refreshing..." : "Refresh"}
          </button>
        </div>
      </div>

      <div className="recalc-summary-grid">
        <div className="recalc-summary-card">
          <div className="recalc-summary-icon recalc-total-icon">
            <FileSpreadsheet size={21} />
          </div>
          <div>
            <span>Total records loaded</span>
            <strong>{logs.length}</strong>
          </div>
        </div>

        <div className="recalc-summary-card">
          <div className="recalc-summary-icon recalc-success-icon">
            <CheckCircle2 size={21} />
          </div>
          <div>
            <span>Successful</span>
            <strong>{successCount}</strong>
          </div>
        </div>

        <div className="recalc-summary-card">
          <div className="recalc-summary-icon recalc-failed-icon">
            <XCircle size={21} />
          </div>
          <div>
            <span>Failed</span>
            <strong>{failedCount}</strong>
          </div>
        </div>
      </div>

      <div className="recalc-history-panel">
        <div className="recalc-history-toolbar">
          <div className="recalc-search-box">
            <Search size={18} />
            <input
              type="text"
              placeholder="Search company, symbol, filename or error..."
              value={search}
              onChange={(event) => setSearch(event.target.value)}
            />
          </div>

          <select
            className="recalc-status-select"
            value={statusFilter}
            onChange={(event) => setStatusFilter(event.target.value)}
            aria-label="Filter by recalculation status"
          >
            <option value="all">All statuses</option>
            <option value="success">Successful</option>
            <option value="failed">Failed</option>
          </select>
        </div>

        {error && (
          <div className="recalc-error-banner">
            <AlertCircle size={19} />
            <span>{error}</span>
            <button type="button" onClick={() => loadLogs(true)}>
              Retry
            </button>
          </div>
        )}

        {loading ? (
          <div className="recalc-state-message">
            <RefreshCw size={24} className="recalc-spinning" />
            <p>Loading recalculation history...</p>
          </div>
        ) : !error && visibleLogs.length === 0 ? (
          <div className="recalc-state-message">
            <FileSpreadsheet size={34} />
            <h3>No recalculation records found</h3>
            <p>
              {logs.length === 0
                ? "Run Excel recalculation from the Search page. Completed results will appear here."
                : "Try changing your search or status filter."}
            </p>
          </div>
        ) : (
          <>
            <div className="recalc-table-wrapper">
              <table className="recalc-history-table">
                <thead>
                  <tr>
                    <th>Company</th>
                    <th>Excel file</th>
                    <th>Status</th>
                    <th>Run started</th>
                    <th>Run finished</th>
                    <th>Error details</th>
                  </tr>
                </thead>

                <tbody>
                  {visibleLogs.map((log) => (
                    <tr key={log.id}>
                      <td>
                        <div className="recalc-company-name">
                          {log.company_name || "Company not matched"}
                        </div>
                        <div className="recalc-company-symbol">
                          {log.company_symbol || "No symbol linked"}
                        </div>
                      </td>

                      <td>
                        <div className="recalc-filename">
                          <FileSpreadsheet size={16} />
                          <span>{log.file_name}</span>
                        </div>
                      </td>

                      <td>
                        <span
                          className={`recalc-status-badge ${
                            log.status === "success"
                              ? "recalc-badge-success"
                              : "recalc-badge-failed"
                          }`}
                        >
                          {log.status === "success" ? (
                            <CheckCircle2 size={15} />
                          ) : (
                            <XCircle size={15} />
                          )}
                          {log.status === "success" ? "Success" : "Failed"}
                        </span>
                      </td>

                      <td className="recalc-date-cell">
                        <Clock3 size={14} />
                        {formatDate(log.run_started_at)}
                      </td>

                      <td className="recalc-date-cell">
                        <Clock3 size={14} />
                        {formatDate(log.run_finished_at)}
                      </td>

                      <td className="recalc-error-cell">
                        {log.status === "failed" && log.error ? (
                          <div>
                            <p
                              className={
                                expandedErrors[log.id]
                                  ? "recalc-error-text expanded"
                                  : "recalc-error-text"
                              }
                            >
                              {log.error}
                            </p>
                            {log.error.length > 90 && (
                              <button
                                type="button"
                                className="recalc-error-toggle"
                                onClick={() => toggleError(log.id)}
                              >
                                {expandedErrors[log.id]
                                  ? "Show less"
                                  : "Show full error"}
                              </button>
                            )}
                          </div>
                        ) : (
                          <span className="recalc-no-error">—</span>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            <div className="recalc-pagination">
              <span>
                Showing{" "}
                {filteredLogs.length === 0
                  ? 0
                  : (safePage - 1) * PAGE_SIZE + 1}
                {"–"}
                {Math.min(safePage * PAGE_SIZE, filteredLogs.length)} of{" "}
                {filteredLogs.length} filtered records
              </span>

              <div className="recalc-pagination-buttons">
                <button
                  type="button"
                  disabled={safePage <= 1}
                  onClick={() => setPage((current) => current - 1)}
                >
                  Previous
                </button>

                <span>
                  Page {safePage} of {totalPages}
                </span>

                <button
                  type="button"
                  disabled={safePage >= totalPages}
                  onClick={() => setPage((current) => current + 1)}
                >
                  Next
                </button>
              </div>
            </div>
          </>
        )}
      </div>
    </div>
  );
}

export default RecalculationLogsPage;
