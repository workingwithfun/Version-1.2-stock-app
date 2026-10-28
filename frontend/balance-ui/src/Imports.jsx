
import React, { useState } from "react";
import {
  FaUpload,
  FaChartLine,
  FaFileCsv,
  FaFileExcel,
  FaCalculator,
  FaTimes,
  FaCheckCircle,
} from "react-icons/fa";
import { toast } from "react-toastify";
import "./BalanceSheet.css";

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

const errorMessage = (error, fallback) =>
  error instanceof Error && error.message
    ? error.message
    : fallback;

function Import({ onImportComplete }) {
  const [showModal, setShowModal] = useState(false);
  const [importStatus, setImportStatus] = useState(INITIAL_STATUS);
  const [isCalculating, setIsCalculating] = useState(false);
  const [expectedReturn, setExpectedReturn] = useState(30);

  const [uploading, setUploading] = useState({
    equityL: false,
    mcap: false,
    mapping: false,
  });

  // Upload a file to the specified Django API endpoint.
  const uploadFile = async (endpoint, file, extraFields = {}) => {
    const formData = new FormData();
    formData.append("file", file);

    Object.entries(extraFields).forEach(([key, value]) => {
      formData.append(key, String(value));
    });

    const response = await fetch(`${API}${endpoint}`, {
      method: "POST",
      body: formData,
    });

    const result = await response.json().catch(() => ({}));

    if (!response.ok) {
      throw new Error(
        result.error ||
          result.detail ||
          `Request failed (${response.status})`
      );
    }

    return result;
  };

  // Refresh the NSE table after a successful import.
  const refreshParent = async () => {
    if (onImportComplete) {
      await onImportComplete();
    }
  };

  const handleImportEquityL = async (event) => {
    const input = event.target;
    const file = input.files?.[0];

    if (!file) return;

    if (!/\.csv$/i.test(file.name)) {
      toast.error("Only CSV files are supported.");
      input.value = "";
      return;
    }

    setUploading((previous) => ({
      ...previous,
      equityL: true,
    }));

    try {
      const result = await uploadFile("import_equity_l/", file);

      toast.success(
        `Imported successfully. Created: ${result.created ?? 0}, Updated: ${
          result.updated ?? 0
        }, Total: ${result.total ?? 0}`
      );

      await refreshParent();
    } catch (error) {
      console.error("Equity L import error:", error);
      toast.error(errorMessage(error, "Equity L import failed."));
    } finally {
      setUploading((previous) => ({
        ...previous,
        equityL: false,
      }));
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

    setUploading((previous) => ({
      ...previous,
      mcap: true,
    }));

    try {
      const result = await uploadFile("import-mcap/", file);

      toast.success(
        `${result.success || "MCAP import completed"} (Skipped: ${
          result.skipped ?? 0
        })`
      );

      await refreshParent();
    } catch (error) {
      console.error("MCAP import error:", error);
      toast.error(errorMessage(error, "MCAP import failed."));
    } finally {
      setUploading((previous) => ({
        ...previous,
        mcap: false,
      }));
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

    setUploading((previous) => ({
      ...previous,
      mapping: true,
    }));

    try {
      const result = await uploadFile("import-mapping/", file);

      toast.success(
        `${result.success || "Mapping import completed"} (Skipped: ${
          result.skipped ?? 0
        })`
      );

      await refreshParent();
    } catch (error) {
      console.error("Mapping import error:", error);
      toast.error(errorMessage(error, "Mapping import failed."));
    } finally {
      setUploading((previous) => ({
        ...previous,
        mapping: false,
      }));
      input.value = "";
    }
  };

  const handleImportNifty = async (file, index) => {
    try {
      const result = await uploadFile("import-nifty-index/", file, {
        index_type: index.api,
      });

      toast.success(
        result.message || `${index.label} imported successfully.`
      );

      setImportStatus((previous) => ({
        ...previous,
        [index.key]: true,
      }));

      await refreshParent();
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

      toast.info(
        `Started calculation using ${expectedReturn}% expected YoY return.`
      );

      const response = await fetch(`${API}metrics/calculate-all/`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          expected_return: expectedReturn,
        }),
      });

      const result = await response.json().catch(() => ({}));

      if (!response.ok) {
        throw new Error(
          result.error ||
            result.detail ||
            "Bulk calculation failed."
        );
      }

      if (result.success_count === 0) {
        toast.error(
          "Calculation failed for all companies. Check backend logs."
        );
      } else {
        toast.success(
          `Calculated ${result.success_count} companies successfully.`
        );
      }

      if (result.failed_count > 0) {
        toast.warning(
          `${result.failed_count} companies failed during calculation.`
        );
      }

      await refreshParent();
    } catch (error) {
      console.error("Bulk calculation error:", error);
      toast.error(
        errorMessage(error, "Error during bulk calculation.")
      );
    } finally {
      setIsCalculating(false);
    }
  };

  const completedImports =
    Object.values(importStatus).filter(Boolean).length;

  return (
    <div className="nsc-management">
      <section className="nsc-panel">
        <div className="nsc-panel-heading">
          <div>
            <h2>Import data files</h2>
            <p>
              Upload source files to update equity, market-cap, and mapping data.
            </p>
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
            <span className="nsc-import-icon nsc-purple">
              <FaUpload />
            </span>

            <div className="nsc-import-content">
              <h3>Nifty index files</h3>
              <p>
                Import index membership files in sequence, from Nifty 50
                through Nifty 750.
              </p>

              <button
                className="nsc-button nsc-button-outline"
                type="button"
                onClick={() => setShowModal(true)}
              >
                <FaUpload /> Manage index imports
              </button>

              <small>
                {completedImports} of 5 imports completed this session
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
            <p>
              Recalculate metrics for all companies using your expected
              year-on-year return.
            </p>
          </div>

          <span className="nsc-calculation-icon">
            <FaCalculator />
          </span>
        </div>

        <div className="nsc-calculation-controls">
          <div className="nsc-field">
            <label htmlFor="expected-return">Expected YoY return</label>

            <select
              id="expected-return"
              value={expectedReturn}
              onChange={(event) =>
                setExpectedReturn(Number(event.target.value))
              }
              disabled={isCalculating}
            >
              {RETURN_OPTIONS.map((value) => (
                <option key={value} value={value}>
                  {value}%
                </option>
              ))}
            </select>

            <small>Applied to the bulk calculation request.</small>
          </div>

          <div className="nsc-assumption">
            <span>Selected assumption</span>
            <strong>
              {expectedReturn}% <small>YoY</small>
            </strong>
          </div>

          <button
            className="nsc-button nsc-button-primary nsc-calculate"
            type="button"
            onClick={handleCalculateAll}
            disabled={isCalculating}
          >
            {isCalculating ? (
              <>
                <span className="nsc-spinner" />
                Calculating all companies...
              </>
            ) : (
              <>
                <FaCalculator /> Calculate all companies
              </>
            )}
          </button>
        </div>

        <p className="nsc-warning">
          This action calculates metrics for all companies. You will be asked
          to confirm before it starts.
        </p>
      </section>

      {showModal && (
        <div
          className="nsc-modal-backdrop"
          role="presentation"
          onMouseDown={(event) => {
            if (event.target === event.currentTarget) {
              setShowModal(false);
            }
          }}
        >
          <section
            className="nsc-modal"
            role="dialog"
            aria-modal="true"
            aria-labelledby="nsc-modal-title"
          >
            <div className="nsc-modal-top">
              <span className="nsc-modal-icon">
                <FaUpload />
              </span>

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
              Import each index in sequence. The next index becomes available
              after the previous import succeeds.
            </p>

            <div className="nsc-index-list">
              {INDEXES.map((index, position) => {
                const previousKey = INDEXES[position - 1]?.key;
                const enabled =
                  position === 0 || importStatus[previousKey];

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
              <span>
                <FaCheckCircle /> {completedImports} of 5 completed
              </span>

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
    </div>
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
          {uploading ? <span className="nsc-spinner" /> : <FaUpload />}

          {uploading ? "Importing..." : buttonText}

          <input
            type="file"
            accept={accept}
            disabled={uploading}
            onChange={onChange}
          />
        </label>

        <small>
          {uploading
            ? "Please wait while your file is processed..."
            : helper}
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

      if (success) {
        setFile(null);
      }
    } finally {
      setUploading(false);
    }
  };

  return (
    <div
      className={`nsc-index-row ${
        imported ? "is-imported" : ""
      } ${!enabled ? "is-disabled" : ""}`}
    >
      <span className="nsc-step">
        {imported ? (
          <FaCheckCircle />
        ) : (
          String(step).padStart(2, "0")
        )}
      </span>

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

      <label
        className={`nsc-button nsc-button-outline nsc-index-file ${
          !enabled || imported ? "is-disabled" : ""
        }`}
      >
        <FaFileCsv />
        <span>{file ? file.name : "Choose file"}</span>

        <input
          type="file"
          accept=".csv,.xlsx"
          disabled={!enabled || imported || uploading}
          onChange={(event) =>
            setFile(event.target.files?.[0] || null)
          }
        />
      </label>

      <button
        type="button"
        className={`nsc-button ${
          imported ? "nsc-button-success" : "nsc-button-primary"
        } nsc-index-submit`}
        disabled={!enabled || !file || imported || uploading}
        onClick={submit}
      >
        {imported ? "Imported" : uploading ? "Importing..." : "Import"}
      </button>
    </div>
  );
}

export default Import;
