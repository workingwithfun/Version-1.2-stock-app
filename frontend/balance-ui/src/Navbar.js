
import React, { useRef, useState } from "react";
import { Link, useLocation } from "react-router-dom";
import {
  FiHome,
  FiChevronDown,
  FiMenu,
  FiX,
  FiBarChart2,
  FiDatabase,
  FiAlertCircle,
} from "react-icons/fi";
import "./BalanceSheet.css";

const navGroups = [
  {
    id: "yearly",
    label: "Yearly Data",
    icon: FiDatabase,
    links: [
      { to: "/instruction", label: "Instructions" },
      { to: "/mapping_table", label: "Mapping Table" },
      { to: "/imports", label: "Imports" },
      { to: "/balances", label: "Yearly Balance Sheet" },
      { to: "/nsedata", label: "NSE Data" },
      { to: "/search", label: "Download Screener Files" },
      { to: "/errorlog", label: "Error Logs", icon: FiAlertCircle },
    ],
  },
  {
    id: "analysis",
    label: "Analysis",
    icon: FiBarChart2,
    links: [
      { to: "/yearly_output", label: "Valuation Analysis" },
      { to: "/filters", label: "Report Analysis" },
    ],
  },
];

const Navbar = () => {
  const [dropdownOpen, setDropdownOpen] = useState(null);
  const [mobileOpen, setMobileOpen] = useState(false);
  const closeTimer = useRef(null);
  const location = useLocation();

  const openDropdown = (id) => {
    clearTimeout(closeTimer.current);
    setDropdownOpen(id);
  };

  const closeDropdown = () => {
    clearTimeout(closeTimer.current);
    closeTimer.current = setTimeout(() => {
      setDropdownOpen(null);
    }, 180);
  };

  const closeMenu = () => {
    setDropdownOpen(null);
    setMobileOpen(false);
    clearTimeout(closeTimer.current);
  };

  const isGroupActive = (group) =>
    group.links.some((link) => location.pathname === link.to);

  return (
    <nav className="navbar">
      <div className="navbar-inner">
        <Link to="/" className="navbar-brand" onClick={closeMenu}>
          <span className="brand-icon">
            <FiBarChart2 />
          </span>
          <span className="brand-copy">
            <span className="brand-title">Financial Insights</span>
            <span className="brand-subtitle">Data &amp; Analysis</span>
          </span>
        </Link>

        <button
          type="button"
          className="mobile-menu-toggle"
          onClick={() => setMobileOpen((open) => !open)}
          aria-label={mobileOpen ? "Close navigation" : "Open navigation"}
          aria-expanded={mobileOpen}
        >
          {mobileOpen ? <FiX /> : <FiMenu />}
        </button>

        <div className={`navbar-content ${mobileOpen ? "mobile-open" : ""}`}>
          <ul className="nav-right">
            <li className="nav-item">
              <Link
                to="/home"
                className={`nav-link nav-home ${
                  location.pathname === "/" ? "active" : ""
                }`}
                onClick={closeMenu}
                aria-label="Home"
                title="Home"
              >
                <FiHome />
                <span className="home-label">Home</span>
              </Link>
            </li>

            {navGroups.map((group) => {
              const GroupIcon = group.icon;
              const isOpen = dropdownOpen === group.id;
              const isActive = isGroupActive(group);

              return (
                <li
                  key={group.id}
                  className={`nav-item ${isOpen ? "dropdown-active" : ""}`}
                  onMouseEnter={() => openDropdown(group.id)}
                  onMouseLeave={closeDropdown}
                >
                  <button
                    type="button"
                    className={`nav-link nav-dropdown-trigger ${
                      isActive ? "active" : ""
                    }`}
                    onClick={() =>
                      setDropdownOpen((current) =>
                        current === group.id ? null : group.id
                      )
                    }
                    aria-expanded={isOpen}
                    aria-haspopup="true"
                  >
                    <GroupIcon className="nav-group-icon" />
                    <span>{group.label}</span>
                    <FiChevronDown
                      className={`dropdown-chevron ${
                        isOpen ? "chevron-open" : ""
                      }`}
                    />
                  </button>

                  {isOpen && (
                    <ul className="dropdown-menu">
                      <li className="dropdown-heading">
                        {group.label}
                      </li>

                      {group.links.map((link) => {
                        const LinkIcon = link.icon;

                        return (
                          <li key={link.to}>
                            <Link
                              to={link.to}
                              className={`dropdown-link ${
                                location.pathname === link.to
                                  ? "dropdown-link-active"
                                  : ""
                              }`}
                              onClick={closeMenu}
                            >
                              {LinkIcon && <LinkIcon className="dropdown-link-icon" />}
                              <span>{link.label}</span>
                            </Link>
                          </li>
                        );
                      })}
                    </ul>
                  )}
                </li>
              );
            })}
          </ul>
        </div>
      </div>
    </nav>
  );
};

export default Navbar;
