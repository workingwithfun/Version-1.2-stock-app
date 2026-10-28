import React, { useState } from "react";
import "./BalanceSheet.css";

const instructionsData = {
  mapping: {
  title: "Mapping Table",
  content: (
    <>
      <p>
        The Mapping Table serves as the master reference for maintaining
        company-level classification data within the system.
        It links each company and its trading symbol to the corresponding
        sector, sub-sector, and industry.
      </p>

      <h4>Purpose</h4>
      <ul>
        <li>Standardizes company classification across all modules</li>
        <li>Ensures consistency in reporting, analysis, and filtering</li>
        <li>Acts as the foundational dataset for downstream calculations</li>
      </ul>

      <h4>Managing the Mapping Table</h4>
      <ul>
        <li>
          Import mapping data directly from the{" "}
          <a
            href="http://localhost:3000/nsedata"
            target="_blank"
            rel="noopener noreferrer"
          >
            Imports module
          </a>
        </li>
        <li>Add new company-symbol mappings as required</li>
        <li>Edit existing sector, sub-sector, or industry classifications</li>
        <li>Delete obsolete or incorrect entries to keep the data current</li>
      </ul>

      <h4>Exporting Data</h4>
      <ul>
        <li>
          The mapping table can be exported in <strong>XLS format </strong>
          for offline review, validation, or backup purposes
        </li>
      </ul>

      <p>
        Ensure all entries are reviewed for accuracy before saving, as the
        mapping table directly impacts analytical outputs and reports
        generated across the application.
      </p>
    </>
  ),
},


 screener: {
  title: "Downloading Screener",
  content: (
    <>
      <p>
        The Screener Download module is used to automatically retrieve
        financial data files from the Screener platform and prepare them
        for further processing within the system.
      </p>

      <h4>Accessing the Screener Download</h4>
      <ul>
        <li>
          Navigate to the Screener Download page from{" "}
          <a
            href="http://localhost:3000/search"
            target="_blank"
            rel="noopener noreferrer"
          >
            this link
          </a>
        </li>
        <li>
          The module is integrated with an automated process that downloads
          over <strong>2,000+ company files</strong> from{" "}
          <a
            href="https://www.screener.in/"
            target="_blank"
            rel="noopener noreferrer"
          >
            screener.in
          </a>
        </li>
      </ul>

      <h4>Data Usage</h4>
      <ul>
        <li>
          The downloaded Screener files serve as the primary data source
          for the <strong>Balance Sheet Entry</strong> module
        </li>
        <li>
          These files contain company-level financial information required
          for accurate balance sheet processing and analysis
        </li>
      </ul>

      <h4>Monitoring and Logs</h4>
      <ul>
        <li>
          Use the <strong>View Logs</strong> tab to monitor the download process
        </li>
        <li>
          Review failed downloads to identify missing or inaccessible files
        </li>
        <li>
          Logs help ensure data completeness before proceeding to the next step
        </li>
      </ul>

      <p>
        It is recommended to review the download logs after completion and
        address any failed files before initiating balance sheet entry or
        further analysis.
      </p>
    </>
  ),
},

 balance: {
  title: "Balance Sheet Entry",
  content: (
    <>
      <p>
        The Balance Sheet Entry module is responsible for processing and
        managing company-level financial data derived from the Screener files.
        It consolidates yearly financial metrics and stores them in a structured
        format for analysis and reporting.
      </p>

      <h4>Data Source</h4>
      <ul>
        <li>
          Data is automatically mined from the downloaded Screener files for
          each company
        </li>
        <li>
          The system extracts key financial parameters based on company type,
          including:
          <ul>
            <li>Earnings Per Share (EPS)</li>
            <li>Net Profit</li>
            <li>Operating Profit Margin (OPM)</li>
            <li>Return on Capital Employed (ROCE)</li>
            <li>Return on Equity (ROE)</li>
            <li>Sales</li>
          </ul>
        </li>
      </ul>

      <h4>Yearly Data Processing</h4>
      <ul>
        <li>
          All financial values are stored on a <strong>yearly basis</strong>
        </li>
        <li>
          Each import updates the data for the corresponding financial year
        </li>
        <li>
          If newer Screener files become available, the system will indicate
          that an updated import is required
        </li>
      </ul>

      <h4>Import and Export</h4>
      <ul>
        <li>
          Use the <strong>Import</strong> button to extract and store data from
          the Screener files across all companies
        </li>
        <li>
          Existing data can be exported for validation, review, or offline
          analysis
        </li>
        <li>
          Re-importing allows updated financial data to be captured without
          manual entry
        </li>
      </ul>

      <p>
        It is recommended to ensure that all required Screener files are
        successfully downloaded before initiating the import process, as
        incomplete data may impact downstream calculations and reports.
      </p>
    </>
  ),
},


nscEquity: {
  title: "NSE – Equity",
  content: (
    <>
      <p>
        The NSE – Equity module forms a core component of the NSE dataset and
        represents equity-level information required for market classification
        and analysis.
      </p>

      <h4>Prerequisite – Equity Data Import</h4>
      <ul>
        <li>
          Equity data must be imported before NSE processing can begin
        </li>
        <li>
          The equity file is imported through the{" "}
          <a
            href="http://localhost:3000/imports"
            target="_blank"
            rel="noopener noreferrer"
          >
            Imports module
          </a>
        </li>
        <li>
          Upon import, the equity data is stored and managed within the{" "}
          <a
            href="http://localhost:3000/nsedata"
            target="_blank"
            rel="noopener noreferrer"
          >
            NSE Data
          </a>{" "}
          section
        </li>
      </ul>

      <h4>Role in NSE Dataset</h4>
      <ul>
        <li>
          Equity data provides the foundational company-level attributes used in
          NSE calculations
        </li>
        <li>
          It is combined with <strong>Market Capitalization (Mcap)</strong> and
          <strong> Nifty Index</strong> files to form the complete NSE dataset
        </li>
        <li>
          All three components must be available and up to date for accurate
          NSE outputs
        </li>
      </ul>

      <p>
        Ensure that the equity file is successfully imported and validated
        before proceeding with Mcap and Nifty Index data, as missing equity data
        may result in incomplete or incorrect NSE calculations.
      </p>
    </>
  ),
},


nscMcap: {
  title: "NSE – Market Capitalization",
  content: (
    <>
      <p>
        The NSE – Market Capitalization module is responsible for importing and
        processing market capitalization data, which is a critical component
        of the overall NSE dataset.
      </p>

      <h4>Importing Mcap Data</h4>
      <ul>
        <li>
          The Market Capitalization (Mcap) file is imported through the{" "}
          <a
            href="http://localhost:3000/nsedata"
            target="_blank"
            rel="noopener noreferrer"
          >
            Imports module
          </a>
        </li>
        <li>
          Once imported, the Mcap data is stored in the{" "}
          <a
            href="http://localhost:3000/nsedata"
            target="_blank"
            rel="noopener noreferrer"
          >
            NSE table
          </a>{" "}
          along with other NSE components
        </li>
      </ul>

      <h4>Calculated Valuation Metrics</h4>
      <p>
        After successful Mcap import, the system automatically calculates and
        stores key valuation metrics used for analysis and comparison.
      </p>

      <ul>
        <li>
          <strong>P/E Ratio</strong>  
          <br />
          Formula: <em>Share Price / EPS</em>
        </li>

        <li>
          <strong>Stock P/E</strong>  
          <br />
          Formula: <em>Share Price / Last Year EPS</em>
        </li>

        <li>
          <strong>TTM P/E (Trailing Twelve Months)</strong>  
          <br />
          Formula: <em>Share Price / Trailing EPS</em>
        </li>

        <li>
          <strong>Industry P/E</strong>  
          <br />
          Formula: <em>Median of TTM P/E values for companies within the same industry</em>
        </li>
      </ul>

      <p>
        All calculated metrics are stored within the NSE dataset and are
        automatically updated whenever the Mcap data is re-imported or refreshed.
      </p>

      <p>
        Ensure that equity data is available prior to importing the Mcap file,
        as valuation calculations rely on a complete and accurate NSE dataset.
      </p>
    </>
  ),
},
nscNifty: {
  title: "NSE – Nifty Index",
  content: (
    <>
      <p>
        The NSE – Nifty Index module manages the import and storage of Nifty
        Index files, which are essential for NSE calculations and benchmarking
        against market indices.
      </p>

      <h4>Import Sequence</h4>
      <ul>
        <li>
          Nifty Index files must be imported <strong>after the Equity and Mcap</strong> data
          have been successfully processed
        </li>
        <li>
          Files are imported via the{" "}
          <a
            href="http://localhost:3000/nsedata"
            target="_blank"
            rel="noopener noreferrer"
          >
            Imports module
          </a>
        </li>
      </ul>

      <h4>Available Nifty Index Files</h4>
      <p>The module supports multiple Nifty Index files to ensure comprehensive market coverage:</p>
      <ul>
        <li>Nifty 50</li>
        <li>Nifty 100</li>
        <li>Nifty 200</li>
        <li>Nifty 500</li>
        <li>Nifty 750</li>
      </ul>

      <h4>Data Storage</h4>
      <ul>
        <li>
          All imported Nifty Index files are stored within the{" "}
          <a
            href="http://localhost:3000/nsedata"
            target="_blank"
            rel="noopener noreferrer"
          >
            NSE Data section
          </a>
        </li>
        <li>
          Proper sequencing ensures that NSE calculations reflect accurate market benchmarks
        </li>
      </ul>

      <p>
        Ensure that all relevant Nifty Index files are imported and validated
        to maintain consistency across NSE computations and to support
        accurate downstream analysis.
      </p>
    </>
  ),
},

imports: {
  title: "Imports",
  content: (
    <>
      <p>
        The Imports module provides a centralized interface to upload and
        process various data files required for NSE, Balance Sheet, and other
        system calculations. It ensures that all data is standardized and
        ready for analysis.
      </p>

      <h4>Supported File Types</h4>
      <ul>
        <li>
          The module supports <strong>XLSX</strong> and <strong>CSV</strong> file formats
        </li>
        <li>
          File type selection depends on the specific dataset being imported
        </li>
        <li>
          Ensure that files adhere to the required template to avoid errors
        </li>
      </ul>

      <h4>Data Processing</h4>
      <ul>
        <li>
          Imported files are automatically stored and processed in the{" "}
          <a
            href="http://localhost:3000/nsedata"
            target="_blank"
            rel="noopener noreferrer"
          >
            NSE Data section
          </a>
        </li>
        <li>
          The module not only imports raw data but also performs calculations
          required for downstream modules such as Balance Sheet Entry and NSE
        </li>
        <li>
          Each import updates the dataset while maintaining data integrity
        </li>
      </ul>

      <h4>Best Practices</h4>
      <ul>
        <li>Do not modify column headers in the template files</li>
        <li>Verify the completeness and accuracy of the file before importing</li>
        <li>Monitor the import logs to ensure all records are processed successfully</li>
      </ul>

      <p>
        Using the Imports module correctly ensures that all subsequent modules
        have access to accurate and standardized data, enabling reliable
        analysis and reporting.
      </p>
    </>
  ),
},

outputs: {
  title: "Calculated Outputs",
  content: (
    <>
      <p>
        The Calculated Outputs module consolidates all processed data and
        presents it in a structured and systematic manner for analysis and
        reporting.
      </p>

      <h4>Key Features</h4>
      <ul>
        <li>
          <strong>Company Information:</strong> View detailed company profiles
          including sector, sub-sector, and industry classification
        </li>
        <li>
          <strong>Yearly Metrics:</strong> Access annual financial metrics such
          as EPS, Net Profit, OPM, ROCE, ROE, and Sales
        </li>
        <li>
          <strong>Valuation Analysis:</strong> Examine 5-year and 10-year
          summaries for each company, including P/E, TTM P/E, Stock P/E, and
          Industry P/E
        </li>
        <li>
          <strong>Stock Analysis:</strong> Monitor stock performance metrics
          alongside company financials
        </li>
        <li>
          <strong>Growth Summary:</strong> Analyze historical growth trends
          for key financial indicators
        </li>
      </ul>

      <h4>Searching Companies</h4>
      <p>
        You can search for any company to view its calculated outputs using
        the following link:{" "}
        <a
          href="http://localhost:3000/yearly_output"
          target="_blank"
          rel="noopener noreferrer"
        >
          Yearly Output
        </a>
      </p>

      <p>
        The module ensures that all calculated fields are generated automatically
        after validation of imported and processed data, providing accurate and
        reliable insights for decision-making.
      </p>
    </>
  ),
},

filters: {
  title: "Filters and Chart",
  content: (
    <>
      <p>
        The Filters and Chart module provides a powerful interface to refine
        data and visualize trends across companies, industries, and financial
        metrics.
      </p>

      <h4>Filtering Options</h4>
      <ul>
        <li>
          Apply filters to identify companies that are <strong>overvalued</strong> or <strong>undervalued</strong> based on valuation metrics
        </li>
        <li>
          Filter by sector, sub-sector, industry, market capitalization, or
          other financial criteria
        </li>
        <li>
          Filters can be combined to narrow down companies for targeted
          analysis
        </li>
      </ul>

      <h4>Data Visualization</h4>
      <ul>
        <li>
          View the <strong>expected returns</strong> for companies after applying
          filters
        </li>
        <li>
          Explore the <strong>count of companies</strong> that meet the selected
          criteria
        </li>
        <li>
          Analyze industry distribution through an interactive <strong>pie chart</strong> for a quick visual summary
        </li>
      </ul>

      <p>
        Using the Filters and Chart module enables faster decision-making by
        allowing users to focus on specific segments of data while simultaneously
        understanding overall trends and industry distributions.
      </p>
    </>
  ),
},
formulas: {
  title: "Formulas",
  content: (
    <>
      <p>
        The Formulas section explains the valuation metrics used in the
        application to evaluate individual stocks and compare companies
        within the same industry.
      </p>

      <h4>Stock P/E</h4>
      <p>
        Calculates the price-to-earnings ratio using the share price and
        the company's EPS.
      </p>
      <ul>
        <li>
          <strong>Formula:</strong>{" "}
          <em>Share Price / EPS</em>
        </li>
      </ul>

      <h4>TTM P/E</h4>
      <p>
        Calculates the trailing twelve-month price-to-earnings ratio
        using the share price and trailing EPS.
      </p>
      <ul>
        <li>
          <strong>Formula:</strong>{" "}
          <em>Share Price / EPS (Trailing)</em>
        </li>
      </ul>

      <h4>Industry P/E</h4>
      <p>
        Calculates the industry P/E by dividing the TTM P/E by the
        total number of companies in that industry.
      </p>
      <ul>
        <li>
          <strong>Formula:</strong>{" "}
          <em>TTM P/E / Total Number of Companies in the Industry</em>
        </li>
      </ul>
    </>
  ),
},
};


const Instructions = () => {
  const [activeKey, setActiveKey] = useState("mapping");
  const [nscOpen, setNscOpen] = useState(false);
  const [search, setSearch] = useState("");

  const activeInstruction = instructionsData[activeKey];

  const navigation = [
    { key: "mapping", label: "Mapping Table", icon: "▦" },
    { key: "screener", label: "Downloading Screener", icon: "↓" },
    { key: "balance", label: "Balance Sheet Entry", icon: "▤" },
    {
      key: "nsc",
      label: "NSE",
      icon: "▣",
      children: [
        { key: "nscEquity", label: "Equity" },
        { key: "nscMcap", label: "Market Capitalization" },
        { key: "nscNifty", label: "Nifty Index" },
      ],
    },
    { key: "imports", label: "Imports", icon: "⇧" },
{ key: "outputs", label: "Calculated Outputs", icon: "▥" },
{ key: "filters", label: "Filters and Chart", icon: "⌁" },
{ key: "formulas", label: "Formulas", icon: "ƒ" },
  ];

  const filteredNavigation = navigation
    .map((item) => {
      if (!item.children) return item;

      const matchingChildren = item.children.filter((child) =>
        child.label.toLowerCase().includes(search.trim().toLowerCase())
      );

      if (
        item.label.toLowerCase().includes(search.trim().toLowerCase())
      ) {
        return item;
      }

      return { ...item, children: matchingChildren };
    })
    .filter((item) => {
      if (!search.trim()) return true;

      return (
        item.label.toLowerCase().includes(search.trim().toLowerCase()) ||
        (item.children && item.children.length > 0)
      );
    });

  const selectSection = (key) => {
    setActiveKey(key);
    if (key.startsWith("nsc")) setNscOpen(true);
  };

  return (
    <div className="instructions-container">
      <header className="instructions-topbar">
        <div className="instructions-brand">
          <div className="instructions-brand-logo">E</div>
          <div>
            <h1>EquityLens</h1>
            <p>Financial Research Workspace</p>
          </div>
        </div>

        <div className="instructions-topbar-right">
          <span className="instructions-status">
            <span className="instructions-status-dot" />
            Documentation
          </span>
        </div>
      </header>

      <div className="instructions-layout">
        <aside className="instructions-sidebar">
          <div className="instructions-sidebar-heading">
            <span>KNOWLEDGE CENTER</span>
            <span className="instructions-count">
              {Object.keys(instructionsData).length}
            </span>
          </div>

          <div className="instructions-search">
            <span aria-hidden="true">⌕</span>
            <input
              type="search"
              value={search}
              onChange={(event) => setSearch(event.target.value)}
              placeholder="Search instructions..."
              aria-label="Search instructions"
            />
          </div>

          <div className="instructions-nav-label">
            DOCUMENTATION
          </div>

          <nav className="instructions-nav" aria-label="Instruction sections">
            {filteredNavigation.map((item) => {
              if (item.children) {
                const childIsActive = item.children.some(
                  (child) => child.key === activeKey
                );

                return (
                  <div key={item.key} className="instructions-nav-group">
                    <button
                      type="button"
                      className={`instructions-nav-item ${
                        childIsActive ? "parent-active" : ""
                      }`}
                      onClick={() => setNscOpen(!nscOpen)}
                    >
                      <span className="instructions-nav-icon">
                        {item.icon}
                      </span>
                      <span className="instructions-nav-text">
                        {item.label}
                      </span>
                      <span className="instructions-nav-chevron">
                        {nscOpen ? "⌄" : "›"}
                      </span>
                    </button>

                    {nscOpen && (
                      <div className="instructions-subnav">
                        {item.children.map((child) => (
                          <button
                            key={child.key}
                            type="button"
                            className={`instructions-subnav-item ${
                              activeKey === child.key ? "active" : ""
                            }`}
                            onClick={() => selectSection(child.key)}
                          >
                            <span className="instructions-subnav-dot" />
                            {child.label}
                          </button>
                        ))}
                      </div>
                    )}
                  </div>
                );
              }

              return (
                <button
                  key={item.key}
                  type="button"
                  className={`instructions-nav-item ${
                    activeKey === item.key ? "active" : ""
                  }`}
                  onClick={() => selectSection(item.key)}
                >
                  <span className="instructions-nav-icon">
                    {item.icon}
                  </span>
                  <span className="instructions-nav-text">
                    {item.label}
                  </span>
                  {activeKey === item.key && (
                    <span className="instructions-nav-active-mark" />
                  )}
                </button>
              );
            })}

            {filteredNavigation.length === 0 && (
              <p className="instructions-no-results">
                No matching sections found.
              </p>
            )}
          </nav>

          <div className="instructions-sidebar-footer">
            <div className="instructions-footer-avatar">EL</div>
            <div>
              <strong>EquityLens Guide</strong>
              <span>Application documentation</span>
            </div>
          </div>
        </aside>

        <main className="instructions-content">
          <div className="instructions-breadcrumb">
            <span>Knowledge Center</span>
            <span className="instructions-breadcrumb-separator">/</span>
            <strong>{activeInstruction.title}</strong>
          </div>

          <article className="instructions-document">
            <div className="instructions-document-header">
              <div>
                <span className="instructions-eyebrow">
                  USER DOCUMENTATION
                </span>
                <h2>{activeInstruction.title}</h2>
                <p>
                  Reference guide for using this module in your
                  financial research workflow.
                </p>
              </div>

              <div className="instructions-document-icon">
                <span>▤</span>
              </div>
            </div>

            <div className="instructions-divider" />

            {/* All original instruction content is rendered unchanged. */}
            <div className="instruction-body">
              {activeInstruction.content}
            </div>

            <div className="instructions-document-footer">
              <span>
                <span className="instructions-footer-check">✓</span>
                You have reached the end of this section.
              </span>
              <span>EquityLens · User Guide</span>
            </div>
          </article>
        </main>
      </div>
    </div>
  );
};

export default Instructions;


