import { useCallback, useEffect, useMemo, useState } from "react";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import { faEdit, faTrash, faPlus, faFileExcel, faSearch, faXmark, faBuilding, faLayerGroup } from "@fortawesome/free-solid-svg-icons";
import Swal from "sweetalert2";
import { toast } from "react-toastify";
import * as XLSX from "xlsx";
import "./BalanceSheet.css";

const API_BASE = "http://localhost:8000/api";
const ENDPOINTS = {
  list: `${API_BASE}/company-symbols/`,
  add: `${API_BASE}/add-mapping/`,
  update: (symbol) => `${API_BASE}/update-mapping/${encodeURIComponent(symbol)}/`,
  remove: (symbol) => `${API_BASE}/delete-mapping/${encodeURIComponent(symbol)}/`,
};

const EMPTY_MAPPING = {
  name: "",
  symbol: "",
  sector: "",
  sub_sector_1: "",
  sub_sector_2: "",
  industry: "",
};

const readJson = async (response) => {
  const text = await response.text();
  let payload = {};
  if (text) {
    try {
      payload = JSON.parse(text);
    } catch {
      payload = { error: text };
    }
  }
  if (!response.ok) {
    throw new Error(payload.error || payload.detail || `Request failed (${response.status}).`);
  }
  return payload;
};

const normalizeMapping = (mapping) => ({
  ...mapping,
  company_name: mapping.company_name ?? mapping.name ?? "",
  symbol: mapping.symbol ?? "",
  sector: mapping.sector ?? "",
  sub_sector_1: mapping.sub_sector_1 ?? "",
  sub_sector_2: mapping.sub_sector_2 ?? "",
  industry: mapping.industry ?? "",
});

function MappingTable() {
  const [mappingData, setMappingData] = useState([]);
  const [companyFilter, setCompanyFilter] = useState("");
  const [showAddForm, setShowAddForm] = useState(false);
  const [newMapping, setNewMapping] = useState(EMPTY_MAPPING);
  const [editingRow, setEditingRow] = useState(null);
  const [newName, setNewName] = useState("");
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [deletingSymbol, setDeletingSymbol] = useState("");
  const [error, setError] = useState("");
  const [sortConfig, setSortConfig] = useState({ key: "company_name", direction: "asc" });

  const fetchMappingData = useCallback(async ({ quiet = false } = {}) => {
    if (!quiet) setLoading(true);
    setError("");
    try {
      const response = await fetch(ENDPOINTS.list);
      const payload = await readJson(response);
      const rows = Array.isArray(payload) ? payload : payload.results;
      if (!Array.isArray(rows)) {
        throw new Error("The mapping API did not return a list of companies.");
      }
      setMappingData(rows.map(normalizeMapping));
    } catch (fetchError) {
      const message = fetchError instanceof Error ? fetchError.message : "Failed to fetch mapping table.";
      setError(message);
      toast.error(message);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchMappingData();
  }, [fetchMappingData]);

  const filteredRows = useMemo(() => {
    const query = companyFilter.trim().toLocaleLowerCase();
    const rows = mappingData.filter((row) => {
      return (
        (row.company_name || "").toLocaleLowerCase().includes(query) ||
        (row.symbol || "").toLocaleLowerCase().includes(query) ||
        (row.sector || "").toLocaleLowerCase().includes(query) ||
        (row.industry || "").toLocaleLowerCase().includes(query)
      );
    });

    const { key, direction } = sortConfig;
    const multiplier = direction === "asc" ? 1 : -1;
    return [...rows].sort((a, b) =>
      String(a[key] ?? "").localeCompare(String(b[key] ?? ""), undefined, {
        numeric: true,
        sensitivity: "base",
      }) * multiplier
    );
  }, [mappingData, companyFilter, sortConfig]);

  const toggleSort = (key) => {
    setSortConfig((current) => ({
      key,
      direction: current.key === key && current.direction === "asc" ? "desc" : "asc",
    }));
  };

  const sortMark = (key) => sortConfig.key !== key ? "↕" : sortConfig.direction === "asc" ? "↑" : "↓";

  const handleAddMapping = async (event) => {
    event?.preventDefault();
    const name = newMapping.name.trim();
    const symbol = newMapping.symbol.trim();
    if (!name || !symbol) {
      toast.warning("Please enter both a company name and symbol.");
      return;
    }

    setSaving(true);
    try {
      const response = await fetch(ENDPOINTS.add, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ ...newMapping, name, symbol }),
      });
      const result = await readJson(response);
      toast.success(result.success || "Mapping added successfully.");
      setMappingData((previous) => [
        normalizeMapping({
          company_name: name,
          symbol,
          sector: newMapping.sector,
          sub_sector_1: newMapping.sub_sector_1,
          sub_sector_2: newMapping.sub_sector_2,
          industry: newMapping.industry,
        }),
        ...previous.filter((row) => row.symbol !== symbol),
      ]);
      setShowAddForm(false);
      setNewMapping(EMPTY_MAPPING);
    } catch (saveError) {
      toast.error(saveError instanceof Error ? saveError.message : "Failed to add mapping.");
    } finally {
      setSaving(false);
    }
  };

  const handleEdit = (row) => {
    setEditingRow({ ...row });
    setNewName(row.company_name || "");
  };

  const saveEdit = async (event) => {
    event?.preventDefault();
    if (!editingRow) return;
    const name = newName.trim();
    if (!name) {
      toast.warning("Company name cannot be empty.");
      return;
    }

    setSaving(true);
    try {
      const response = await fetch(ENDPOINTS.update(editingRow.symbol), {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          name,
          sector: editingRow.sector || "",
          sub_sector_1: editingRow.sub_sector_1 || "",
          sub_sector_2: editingRow.sub_sector_2 || "",
          industry: editingRow.industry || "",
        }),
      });
      const result = await readJson(response);
      toast.success(result.success || "Mapping updated successfully.");
      setMappingData((previous) => previous.map((row) =>
        row.symbol === editingRow.symbol
          ? normalizeMapping({ ...row, company_name: name, sector: editingRow.sector, sub_sector_1: editingRow.sub_sector_1, sub_sector_2: editingRow.sub_sector_2, industry: editingRow.industry })
          : row
      ));
      setEditingRow(null);
    } catch (saveError) {
      toast.error(saveError instanceof Error ? saveError.message : "Failed to update mapping.");
    } finally {
      setSaving(false);
    }
  };

  const handleDelete = async (symbol) => {
    const confirmation = await Swal.fire({
      title: "Delete this mapping?",
      text: `The mapping for ${symbol} will be permanently deleted.`,
      icon: "warning",
      showCancelButton: true,
      confirmButtonColor: "#dc3545",
      cancelButtonColor: "#64748b",
      confirmButtonText: "Yes, delete",
      cancelButtonText: "Keep mapping",
      reverseButtons: true,
      focusCancel: true,
    });
    if (!confirmation.isConfirmed) return;

    setDeletingSymbol(symbol);
    try {
      const response = await fetch(ENDPOINTS.remove(symbol), { method: "DELETE" });
      const result = await readJson(response);
      setMappingData((previous) => previous.filter((row) => row.symbol !== symbol));
      await Swal.fire("Deleted", result.success || "Mapping deleted successfully.", "success");
    } catch (deleteError) {
      await Swal.fire("Unable to delete", deleteError instanceof Error ? deleteError.message : "Something went wrong while deleting.", "error");
    } finally {
      setDeletingSymbol("");
    }
  };

  const handleExportExcel = () => {
    if (!filteredRows.length) {
      toast.warning("No data available to export.");
      return;
    }

    const exportData = filteredRows.map((row) => ({
      "Company Name": row.company_name || "",
      Symbol: row.symbol || "",
      Sector: row.sector || "",
      "Sub-Sector 1": row.sub_sector_1 || "",
      "Sub-Sector 2": row.sub_sector_2 || "",
      Industry: row.industry || "",
    }));
    const worksheet = XLSX.utils.json_to_sheet(exportData);
    worksheet["!cols"] = [
      { wch: 30 }, { wch: 16 }, { wch: 22 }, { wch: 22 }, { wch: 22 }, { wch: 24 },
    ];
    const workbook = XLSX.utils.book_new();
    XLSX.utils.book_append_sheet(workbook, worksheet, "Mapping Table");
    XLSX.writeFile(workbook, "Company_Mapping_Table.xlsx");
    toast.success(`${filteredRows.length} mappings exported.`);
  };

  const closeAdd = () => {
    if (saving) return;
    setShowAddForm(false);
    setNewMapping(EMPTY_MAPPING);
  };

  const renderMappingFields = (values, onChange, includeSymbol = false) => (
    <div className="mapping-form-grid">
      <label className="mapping-field mapping-field-wide">
        <span>Company name{includeSymbol ? " *" : " *"}</span>
        <input
          autoFocus
          required
          value={includeSymbol ? values.name : values.company_name}
          onChange={(event) => onChange("name", event.target.value)}
          placeholder="e.g. Example Industries Ltd."
        />
      </label>
      {includeSymbol && (
        <label className="mapping-field">
          <span>Stock symbol *</span>
          <input required value={values.symbol} onChange={(event) => onChange("symbol", event.target.value)} placeholder="e.g. EXAMPLE" />
        </label>
      )}
      {[
        ["sector", "Sector", "e.g. Financial Services"],
        ["sub_sector_1", "Sub-sector 1", "Enter sub-sector"],
        ["sub_sector_2", "Sub-sector 2", "Enter sub-sector"],
        ["industry", "Industry", "Enter industry"],
      ].map(([key, label, placeholder]) => (
        <label className="mapping-field" key={key}>
          <span>{label}</span>
          <input value={values[key] || ""} onChange={(event) => onChange(key, event.target.value)} placeholder={placeholder} />
        </label>
      ))}
    </div>
  );

  return (
    <main className="mapping-page">
      <header className="mapping-header">
        <div className="mapping-heading">
          <span className="mapping-kicker">REFERENCE DATA</span>
          <h1>Company mapping</h1>
          <p>Manage company names, stock symbols, sectors, and industry classifications.</p>
        </div>
        <div className="mapping-header-actions">
          <button type="button" className="mapping-btn mapping-btn-secondary" onClick={handleExportExcel} disabled={!filteredRows.length}>
            <FontAwesomeIcon icon={faFileExcel} /> Export Excel
          </button>
          <button type="button" className="mapping-btn mapping-btn-primary" onClick={() => setShowAddForm(true)}>
            <FontAwesomeIcon icon={faPlus} /> Add mapping
          </button>
        </div>
      </header>

      <section className="mapping-stats">
        <article className="mapping-stat-card">
          <span className="mapping-stat-icon"><FontAwesomeIcon icon={faBuilding} /></span>
          <div><span>Total mappings</span><strong>{mappingData.length.toLocaleString()}</strong></div>
        </article>
        <article className="mapping-stat-card">
          <span className="mapping-stat-icon mapping-stat-icon-blue"><FontAwesomeIcon icon={faSearch} /></span>
          <div><span>Matching results</span><strong>{filteredRows.length.toLocaleString()}</strong></div>
        </article>
        <article className="mapping-stat-card">
          <span className="mapping-stat-icon mapping-stat-icon-violet"><FontAwesomeIcon icon={faLayerGroup} /></span>
          <div><span>Classified sectors</span><strong>{new Set(mappingData.map((row) => row.sector).filter(Boolean)).size.toLocaleString()}</strong></div>
        </article>
      </section>

      <section className="mapping-content">
        <div className="mapping-toolbar">
          <div>
            <h2>Company directory</h2>
            <p>Search by company, symbol, sector, or industry.</p>
          </div>
          <label className="mapping-search">
            <FontAwesomeIcon icon={faSearch} aria-hidden="true" />
            <input value={companyFilter} onChange={(event) => setCompanyFilter(event.target.value)} placeholder="Search mappings…" aria-label="Search mappings" />
            {companyFilter && <button type="button" onClick={() => setCompanyFilter("")} aria-label="Clear search"><FontAwesomeIcon icon={faXmark} /></button>}
          </label>
        </div>

        {error && (
          <div className="mapping-error" role="alert">
            <span>{error}</span>
            <button type="button" onClick={() => fetchMappingData()}>Retry</button>
          </div>
        )}

        <div className="mapping-table-wrap">
          <table className="mapping-table">
            <thead>
              <tr>
                {[
                  ["company_name", "Company name"],
                  ["symbol", "Symbol"],
                  ["sector", "Sector"],
                  ["sub_sector_1", "Sub-sector 1"],
                  ["sub_sector_2", "Sub-sector 2"],
                  ["industry", "Industry"],
                ].map(([key, label]) => (
                  <th key={key}><button type="button" onClick={() => toggleSort(key)}>{label}<span>{sortMark(key)}</span></button></th>
                ))}
                <th className="mapping-actions-heading">Actions</th>
              </tr>
            </thead>
            <tbody>
              {loading ? (
                <tr><td colSpan={7} className="mapping-empty"><span className="mapping-spinner" /><strong>Loading company mappings…</strong></td></tr>
              ) : filteredRows.length ? filteredRows.map((row) => (
                <tr key={row.symbol || row.company_name}>
                  <td className="mapping-company-cell"><span className="company-avatar">{(row.company_name || "?").trim().charAt(0).toUpperCase()}</span><span title={row.company_name}>{row.company_name || "—"}</span></td>
                  <td><span className="mapping-symbol">{row.symbol || "—"}</span></td>
                  <td>{row.sector || <span className="mapping-muted">Not set</span>}</td>
                  <td>{row.sub_sector_1 || <span className="mapping-muted">—</span>}</td>
                  <td>{row.sub_sector_2 || <span className="mapping-muted">—</span>}</td>
                  <td>{row.industry || <span className="mapping-muted">—</span>}</td>
                  <td>
                    <div className="mapping-row-actions">
                      <button type="button" className="mapping-icon-btn mapping-edit" title="Edit mapping" aria-label={`Edit ${row.company_name}`} onClick={() => handleEdit(row)}>
                        <FontAwesomeIcon icon={faEdit} />
                      </button>
                      <button type="button" className="mapping-icon-btn mapping-delete" title="Delete mapping" aria-label={`Delete ${row.company_name}`} disabled={deletingSymbol === row.symbol} onClick={() => handleDelete(row.symbol)}>
                        <FontAwesomeIcon icon={faTrash} />
                      </button>
                    </div>
                  </td>
                </tr>
              )) : (
                <tr><td colSpan={7} className="mapping-empty"><span className="mapping-empty-icon"><FontAwesomeIcon icon={faSearch} /></span><strong>No mapping data found</strong><span>Try a different search or add a new mapping.</span>{companyFilter && <button type="button" className="mapping-link-btn" onClick={() => setCompanyFilter("")}>Clear search</button>}</td></tr>
              )}
            </tbody>
          </table>
        </div>
        <footer className="mapping-footer"><span>Showing {filteredRows.length.toLocaleString()} of {mappingData.length.toLocaleString()} mappings</span><span>Sorted by {sortConfig.key.replaceAll("_", " ")}</span></footer>
      </section>

      {showAddForm && (
        <div className="mapping-modal-backdrop" role="presentation" onMouseDown={(event) => { if (event.target === event.currentTarget) closeAdd(); }}>
          <section className="mapping-modal" role="dialog" aria-modal="true" aria-labelledby="mapping-add-title">
            <div className="mapping-modal-heading"><div><span className="mapping-modal-kicker">NEW RECORD</span><h2 id="mapping-add-title">Add company mapping</h2><p>Enter the company details and classification.</p></div><button type="button" className="mapping-close" onClick={closeAdd} aria-label="Close dialog"><FontAwesomeIcon icon={faXmark} /></button></div>
            <form onSubmit={handleAddMapping}>
              {renderMappingFields(newMapping, (key, value) => setNewMapping((current) => ({ ...current, [key]: value })), true)}
              <div className="mapping-modal-actions"><button type="button" className="mapping-btn mapping-btn-secondary" onClick={closeAdd} disabled={saving}>Cancel</button><button type="submit" className="mapping-btn mapping-btn-primary" disabled={saving}>{saving ? "Saving…" : "Save mapping"}</button></div>
            </form>
          </section>
        </div>
      )}

      {editingRow && (
        <div className="mapping-modal-backdrop" role="presentation" onMouseDown={(event) => { if (event.target === event.currentTarget && !saving) setEditingRow(null); }}>
          <section className="mapping-modal" role="dialog" aria-modal="true" aria-labelledby="mapping-edit-title">
            <div className="mapping-modal-heading"><div><span className="mapping-modal-kicker">UPDATE RECORD</span><h2 id="mapping-edit-title">Edit company mapping</h2><p>Update the company name and classification fields.</p></div><button type="button" className="mapping-close" onClick={() => setEditingRow(null)} disabled={saving} aria-label="Close dialog"><FontAwesomeIcon icon={faXmark} /></button></div>
            <div className="mapping-locked-symbol"><span>Stock symbol</span><strong>{editingRow.symbol}</strong><small>The symbol is used to identify this mapping and cannot be changed here.</small></div>
            <form onSubmit={saveEdit}>
              {renderMappingFields({ ...editingRow, company_name: newName }, (key, value) => {
                if (key === "name") setNewName(value);
                else setEditingRow((current) => ({ ...current, [key]: value }));
              }, false)}
              <div className="mapping-modal-actions"><button type="button" className="mapping-btn mapping-btn-secondary" onClick={() => setEditingRow(null)} disabled={saving}>Cancel</button><button type="submit" className="mapping-btn mapping-btn-primary" disabled={saving}>{saving ? "Saving…" : "Save changes"}</button></div>
            </form>
          </section>
        </div>
      )}
    </main>
  );
}

export default MappingTable;
