
import React, { useState } from "react";
import { useNavigate } from "react-router-dom";
import {
  Search,
  Building2,
  FileSpreadsheet,
  ChartNoAxesCombined,
  Database,
  ArrowUpRight,
  BriefcaseBusiness,
  ChevronRight,
  X,
} from "lucide-react";
import "./BalanceSheet.css";

const features = [
  {
    title: "Companies",
    description: "Browse company names, symbols, and mapped company data.",
    icon: Building2,
    color: "blue",
    route: "/mapping_table",
  },
  {
    title: "Balance Sheets",
    description: "Review historical financial statements and yearly values.",
    icon: FileSpreadsheet,
    color: "green",
    route: "/balances",
  },
  {
    title: "Financial Analysis",
    description: "Analyze sales, profitability, growth, and return metrics.",
    icon: ChartNoAxesCombined,
    color: "purple",
    route: "/yearly_output",
  },
  {
    title: "Data Management",
    description: "Import company data and manage financial datasets.",
    icon: Database,
    color: "orange",
    route: "/imports",
  },
];

export default function Home() {
  const navigate = useNavigate();
  const [search, setSearch] = useState("");

  const handleSearch = (event) => {
    event.preventDefault();

    const query = search.trim();

    if (!query) return;

    // Open the company mapping page.
    // The search term is passed through the URL for future filtering.
    navigate(
      `/mapping_table?search=${encodeURIComponent(query)}`
    );
  };

  const openPage = (route) => {
    navigate(route);
  };

  return (
    <main className="home-page">
      {/* Hero section */}
      <section className="home-hero">
        <nav className="home-navbar">
          <button
            type="button"
            className="home-brand"
            onClick={() => navigate("/")}
            aria-label="Go to home page"
          >
            <span className="brand-icon">
              <ChartNoAxesCombined size={23} />
            </span>

            <span>EquityLens</span>
          </button>

          <span className="home-nav-label">
            Financial Intelligence
          </span>
        </nav>

        <div className="hero-content">
          <span className="hero-eyebrow">
            YOUR FINANCIAL RESEARCH WORKSPACE
          </span>

          <h1>
            Understand companies.
            <br />
            <span>Analyze with confidence.</span>
          </h1>

          <p className="hero-description">
            Explore listed companies, analyze financial statements,
            and understand business performance through historical data.
          </p>

          {/* Company search */}
          <form
            className="company-search"
            onSubmit={handleSearch}
          >
            <Search size={21} />

            <input
              type="text"
              value={search}
              onChange={(event) => setSearch(event.target.value)}
              placeholder="Search company name or stock symbol..."
              aria-label="Search companies"
            />

            {search && (
              <button
                type="button"
                className="search-clear"
                onClick={() => setSearch("")}
                aria-label="Clear search"
              >
                <X size={17} />
              </button>
            )}

            <button type="submit">
              Search
              <ArrowUpRight size={17} />
            </button>
          </form>

          {/* Quick navigation */}
          <div className="hero-links">
            <button
              type="button"
              onClick={() => openPage("/mapping_table")}
            >
              Explore companies
              <ChevronRight size={17} />
            </button>

            <button
              type="button"
              onClick={() => openPage("/yearly_output")}
            >
              View financial analysis
              <ChevronRight size={17} />
            </button>
          </div>
        </div>

        <div className="hero-decoration" aria-hidden="true">
          <ChartNoAxesCombined
            size={190}
            strokeWidth={0.65}
          />
        </div>
      </section>

      {/* Main workspace */}
      <section className="home-content">
        <div className="section-heading">
          <div>
            <span className="section-eyebrow">
              WORKSPACE
            </span>

            <h2>Your financial toolkit</h2>

            <p>
              Access your company database, financial statements,
              analysis tools, and data imports.
            </p>
          </div>
        </div>

        <div className="feature-grid">
          {features.map((feature) => {
            const Icon = feature.icon;

            return (
              <button
                type="button"
                className="feature-card"
                key={feature.route}
                onClick={() => openPage(feature.route)}
              >
                <span className={`feature-icon ${feature.color}`}>
                  <Icon size={23} />
                </span>

                <span className="feature-title">
                  {feature.title}
                </span>

                <span className="feature-description">
                  {feature.description}
                </span>

                <span className="feature-link">
                  Open section
                  <ArrowUpRight size={16} />
                </span>
              </button>
            );
          })}
        </div>

        {/* Financial research shortcut */}
        <div className="home-info-panel">
          <div className="info-icon">
            <BriefcaseBusiness size={23} />
          </div>

          <div>
            <h3>Research beyond stock prices</h3>

            <p>
              Explore sales growth, profitability, return ratios,
              and historical financial performance to better
              understand the businesses behind the stocks.
            </p>
          </div>

          <button
            type="button"
            onClick={() => openPage("/yearly_output")}
          >
            Start exploring
            <ChevronRight size={18} />
          </button>
        </div>

        <footer className="home-footer">
          <span>
            EquityLens · Financial Research Workspace
          </span>

          <span>Data-driven company analysis</span>
        </footer>
      </section>
    </main>
  );
}
