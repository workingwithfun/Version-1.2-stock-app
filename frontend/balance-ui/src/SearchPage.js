import React, { useEffect, useState } from "react";
import { ToastContainer, toast } from "react-toastify";
import {
  Search,
  Download,
  FileText,
  ShieldCheck,
  ArrowUpRight,
  Clock3,
  Trash2,
  ChartNoAxesCombined,
  Sparkles,
  RefreshCw,
  FileSpreadsheet,
  CheckCircle2,
  XCircle,
  AlertCircle,
} from "lucide-react";

import "react-toastify/dist/ReactToastify.css";
import "./BalanceSheet.css";

function getCookie(name) {
  const cookies = document.cookie ? document.cookie.split(";") : [];

  for (const cookie of cookies) {
    const trimmedCookie = cookie.trim();

    if (trimmedCookie.startsWith(`${name}=`)) {
      return decodeURIComponent(
        trimmedCookie.substring(name.length + 1)
      );
    }
  }

  return null;
}

const initialRecalculationState = {
  status: "idle",
  total: 0,
  processed: 0,
  current_file: null,
  success: [],
  failed: [],
  started_at: null,
  finished_at: null,
  error: null,
};

export default function SearchPage() {
  const [query, setQuery] = useState("");
  const [history, setHistory] = useState([]);
  const [showDropdown, setShowDropdown] = useState(false);
  const [busy, setBusy] = useState(false);
  const [recalculation, setRecalculation] = useState(
    initialRecalculationState
  );
  const [startingRecalculation, setStartingRecalculation] =
    useState(false);

  const isRecalculating = recalculation.status === "running";

  const progress = recalculation.total > 0
    ? Math.min(
        100,
        Math.round(
          (recalculation.processed / recalculation.total) * 100
        )
      )
    : 0;

  const handleSearch = (event) => {
    event.preventDefault();

    const searchTerm = query.trim();

    if (!searchTerm) {
      toast.info("Enter a company name or stock symbol first.");
      return;
    }

    setHistory((previousHistory) => [
      searchTerm,
      ...previousHistory.filter(
        (item) => item.toLowerCase() !== searchTerm.toLowerCase()
      ),
    ]);

    setQuery("");
    setShowDropdown(false);

    toast.info(
      "Added to recent searches. Live search is not connected yet."
    );
  };

  const handleSelectHistory = (item) => {
    setQuery(item);
    setShowDropdown(false);
  };

  const handleDeleteHistory = (item, event) => {
    event.stopPropagation();

    setHistory((previousHistory) =>
      previousHistory.filter((entry) => entry !== item)
    );
  };

  const handleDownload = async () => {
    if (busy) return;

    setBusy(true);

    try {
      const response = await fetch("http://localhost:8000/api/start-screener-downloads/", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "X-CSRFToken": getCookie("csrftoken") || "",
        },
      });

      const data = await response.json().catch(() => ({}));

      if (!response.ok) {
        throw new Error(
          data.error ||
            data.message ||
            `The server returned HTTP ${response.status}.`
        );
      }

      toast.success(
        data.message || "The Screener download job has started."
      );
    } catch (error) {
      toast.error(
        error.message ||
          "Could not start the download. Check that StocksApplication is running."
      );
    } finally {
      setBusy(false);
    }
  };

  const handleRecalculate = async () => {
    if (startingRecalculation || isRecalculating) return;

    setStartingRecalculation(true);

    try {
      const response = await fetch(
  "http://localhost:8000/api/recalculate-screener-excels/",{
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            "X-CSRFToken": getCookie("csrftoken") || "",
          },
        }
      );

      const data = await response.json().catch(() => ({}));

      if (!response.ok) {
        throw new Error(
          data.message ||
            data.error ||
            `The server returned HTTP ${response.status}.`
        );
      }

      setRecalculation({
        ...initialRecalculationState,
        status: "running",
        started_at: new Date().toISOString(),
      });

      toast.success(
        data.message || "Excel recalculation has started."
      );
    } catch (error) {
      toast.error(
        error.message ||
          "Could not start recalculation. Check the application and Excel installation."
      );
    } finally {
      setStartingRecalculation(false);
    }
  };

  // Poll Django for live progress while recalculation is running.
  useEffect(() => {
    if (!isRecalculating) return undefined;

    let isActive = true;

    const fetchStatus = async () => {
      try {
        const response = await fetch(
  "http://localhost:8000/api/recalculate-screener-excels-status/",
          { method: "GET", cache: "no-store" }
        );

        if (!response.ok) {
          throw new Error(`Status request failed: HTTP ${response.status}`);
        }

        const data = await response.json();

        if (isActive) {
          setRecalculation(data);
        }
      } catch (error) {
        // A temporary polling error should not stop the running job.
        console.error("Could not refresh Excel recalculation status:", error);
      }
    };

    fetchStatus();

    const intervalId = window.setInterval(fetchStatus, 1500);

    return () => {
      isActive = false;
      window.clearInterval(intervalId);
    };
  }, [isRecalculating]);

  // Show a final notification once the backend reports completion.
  useEffect(() => {
    if (recalculation.status === "finished") {
      if (recalculation.total === 0) {
        toast.info(
          "Recalculation finished, but no Excel files were found in the download folder."
        );
      } else {
        toast.success(
          `Recalculation finished: ${recalculation.success.length} successful, ${recalculation.failed.length} failed.`
        );
      }
    } else if (recalculation.status === "finished_with_errors") {
      toast.warning(
        `Recalculation finished with errors: ${recalculation.success.length} successful, ${recalculation.failed.length} failed.`
      );
    } else if (recalculation.status === "failed") {
      toast.error(
        recalculation.error || "Excel recalculation failed."
      );
    }
  }, [
    recalculation.status,
    recalculation.total,
    recalculation.success.length,
    recalculation.failed.length,
    recalculation.error,
  ]);

  return (
    <main className="screener-page">
      <ToastContainer
        position="top-right"
        autoClose={4500}
        newestOnTop
        closeOnClick
        pauseOnHover
        draggable
        theme="light"
      />

      <div className="screener-container">
        <header className="workspace-header">
          <div className="workspace-brand">
            <div className="brand-mark">
              <ChartNoAxesCombined size={25} strokeWidth={2.2} />
            </div>

            <div>
              <p className="brand-eyebrow">STOCKS APPLICATION</p>
              <p className="brand-name">Screener Workspace</p>
            </div>
          </div>

          <div className="workspace-badge">
            <span className="status-dot" />
            Local workspace
          </div>
        </header>

        <section className="screener-hero">
          <div className="hero-copy">
            <div className="hero-eyebrow">
              <Sparkles size={15} />
              YOUR STOCK RESEARCH WORKSPACE
            </div>

            <h1>
              Research smarter.
              <br />
              <span>Work with confidence.</span>
            </h1>

            <p className="hero-description">
              Manage Screener Excel downloads for your mapped companies
              and access your download logs from one place.
            </p>
          </div>

          <div className="hero-decoration" aria-hidden="true">
            <div className="decoration-circle decoration-circle-one" />
            <div className="decoration-circle decoration-circle-two" />
            <ChartNoAxesCombined
              className="decoration-chart"
              size={116}
              strokeWidth={1.1}
            />
          </div>
        </section>

        <section className="search-section">
          <div className="section-heading">
            <div>
              <h2>Find a company</h2>
              <p>
                Keep frequently used company names and symbols handy.
              </p>
            </div>
          </div>

          <form className="company-search" onSubmit={handleSearch}>
            <Search
              className="search-icon"
              size={21}
              strokeWidth={1.8}
            />

            <input
              type="text"
              value={query}
              onChange={(event) => setQuery(event.target.value)}
              onFocus={() => setShowDropdown(true)}
              onBlur={() => {
                setTimeout(() => setShowDropdown(false), 180);
              }}
              placeholder="Enter a company name or symbol..."
              aria-label="Company name or stock symbol"
              autoComplete="off"
            />

            {query && (
              <button
                type="button"
                className="clear-search"
                onClick={() => setQuery("")}
                aria-label="Clear search"
              >
                ×
              </button>
            )}

            <button className="search-submit" type="submit">
              Search
              <ArrowUpRight size={17} />
            </button>

            {showDropdown && history.length > 0 && (
              <div className="search-history">
                <div className="history-heading">
                  <span>Recent searches</span>
                  <Clock3 size={15} />
                </div>

                {history.map((item) => (
                  <div
                    className="history-item"
                    key={item}
                    onMouseDown={(event) => event.preventDefault()}
                  >
                    <button
                      type="button"
                      className="history-select"
                      onClick={() => handleSelectHistory(item)}
                    >
                      <Search size={15} />
                      <span>{item}</span>
                    </button>

                    <button
                      type="button"
                      className="history-delete"
                      onClick={(event) =>
                        handleDeleteHistory(item, event)
                      }
                      aria-label={`Remove ${item} from recent searches`}
                      title="Remove from history"
                    >
                      <Trash2 size={15} />
                    </button>
                  </div>
                ))}
              </div>
            )}
          </form>

          <p className="search-note">
            <ShieldCheck size={15} />
            Search terms are kept in this page's current session only.
          </p>
        </section>

        <section className="actions-section">
          <div className="section-heading">
            <div>
              <h2>Quick actions</h2>
              <p>Choose what you want to do next.</p>
            </div>
          </div>

          <div className="action-grid">
            <article className="action-card download-card">
              <div className="action-card-top">
                <div className="action-icon download-icon">
                  <Download size={23} />
                </div>

                <span className="action-label">AUTOMATION</span>
              </div>

              <h3>Screener Excel downloads</h3>

              <p>
                Start the download job for companies in your Company
                Mapping table and collect their Excel exports.
              </p>

              <button
                type="button"
                className="action-button primary-button"
                onClick={handleDownload}
                disabled={busy}
              >
                {busy ? (
                  <>
                    <span className="loading-spinner" />
                    Starting download...
                  </>
                ) : (
                  <>
                    Download Screener Files
                    <ArrowUpRight size={18} />
                  </>
                )}
              </button>

              <div className="card-footnote">
                <span className="small-status-dot" />
                Runs through your local Django backend
              </div>
            </article>

            <article className="action-card logs-card">
              <div className="action-card-top">
                <div className="action-icon logs-icon">
                  <FileText size={23} />
                </div>

                <span className="action-label">MONITORING</span>
              </div>

              <h3>Download history &amp; logs</h3>

              <p>
                Review recorded download activity and investigate
                companies whose files could not be downloaded.
              </p>

              <button
  type="button"
  className="action-button secondary-button"
  onClick={() =>
    window.open("/logs", "_blank", "noopener,noreferrer")
  }
>
  View Download Logs
  <ArrowUpRight size={18} />
</button>

<button
  type="button"
  className="action-button secondary-button"
  onClick={() =>
    window.open(
      "/recalculation-logs",
      "_blank",
      "noopener,noreferrer"
    )
  }
>
  View Recalculation History
  <ArrowUpRight size={18} />
</button>

              <div className="card-footnote">
                <ShieldCheck size={15} />
                Review recorded results
              </div>
            </article>

            <article className="action-card recalculate-card">
              <div className="action-card-top">
                <div className="action-icon recalculate-icon">
                  <FileSpreadsheet size={23} />
                </div>

                <span className="action-label">EXCEL AUTOMATION</span>
              </div>

              <h3>Recalculate Excel files</h3>

              <p>
                Open downloaded Screener workbooks in desktop Excel,
                recalculate formulas, and save the updated files.
              </p>

              <button
                type="button"
                className="action-button primary-button"
                onClick={handleRecalculate}
                disabled={startingRecalculation || isRecalculating}
              >
                {startingRecalculation || isRecalculating ? (
                  <>
                    <span className="loading-spinner" />
                    {startingRecalculation
                      ? "Starting recalculation..."
                      : "Recalculating files..."}
                  </>
                ) : (
                  <>
                    <RefreshCw size={17} />
                    Recalculate Excel Files
                  </>
                )}
              </button>

              <div className="card-footnote">
                <ShieldCheck size={15} />
                Requires desktop Microsoft Excel on this computer
              </div>

              {(isRecalculating ||
                recalculation.status === "finished" ||
                recalculation.status === "finished_with_errors" ||
                recalculation.status === "failed") && (
                <div className="recalculation-results" aria-live="polite">
                  <div className="recalculation-status-row">
                    <span className="recalculation-status-label">
                      {isRecalculating
                        ? "Processing workbooks"
                        : recalculation.status === "finished"
                          ? "Recalculation complete"
                          : recalculation.status === "finished_with_errors"
                            ? "Completed with errors"
                            : "Recalculation failed"}
                    </span>

                    <span className="recalculation-percentage">
                      {isRecalculating ? `${progress}%` : ""}
                    </span>
                  </div>

                  <div
                    className="recalculation-progress-track"
                    role="progressbar"
                    aria-label="Excel recalculation progress"
                    aria-valuemin={0}
                    aria-valuemax={100}
                    aria-valuenow={progress}
                  >
                    <div
                      className="recalculation-progress-fill"
                      style={{ width: `${progress}%` }}
                    />
                  </div>

                  <p className="recalculation-count">
                    {recalculation.processed} of {recalculation.total} files processed
                  </p>

                  {isRecalculating && recalculation.current_file && (
                    <p className="recalculation-current-file" title={recalculation.current_file}>
                      Current file: {recalculation.current_file}
                    </p>
                  )}

                  <div className="recalculation-counts">
                    <span className="recalculation-success-count">
                      <CheckCircle2 size={15} />
                      {recalculation.success.length} successful
                    </span>

                    <span className="recalculation-failure-count">
                      <XCircle size={15} />
                      {recalculation.failed.length} failed
                    </span>
                  </div>

                  {recalculation.error && (
                    <p className="recalculation-error">
                      <AlertCircle size={15} />
                      {recalculation.error}
                    </p>
                  )}

                  {recalculation.failed.length > 0 && (
                    <div className="recalculation-failed-list">
                      <p>Files needing attention:</p>
                      {recalculation.failed.slice(0, 5).map((item, index) => (
                        <div
                          className="recalculation-failed-item"
                          key={`${item.file}-${index}`}
                        >
                          <strong>{item.file}</strong>
                          <span>{item.error}</span>
                        </div>
                      ))}

                      {recalculation.failed.length > 5 && (
                        <p>
                          And {recalculation.failed.length - 5} more failed file(s).
                        </p>
                      )}
                    </div>
                  )}
                </div>
              )}
            </article>
          </div>
        </section>

        <footer className="workspace-footer">
          <span>StocksApplication</span>
          <span className="footer-separator">·</span>
          <span>Company research and data management</span>
        </footer>
      </div>
    </main>
  );
}