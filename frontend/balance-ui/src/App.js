
import React from "react";
import {
  BrowserRouter as Router,
  Routes,
  Route,
} from "react-router-dom";

import BalanceSheet from "./BalanceSheet";
import NSCData from "./NSCData";
import SearchPage from "./SearchPage";
import LogsPage from "./Logspage";
import YearlyBalanceSheet from "./YearlyBalanceSheet";
import Navbar from "./Navbar";
import CompanyValuation from "./CompanyValuation";
import Instructions from "./Instructions";
import MappingTable from "./MappingTable";
import Imports from "./Imports";
import ErrorLogs from "./ErrorLogs";
import Home from "./Home";
import RecalculationLogsPage from "./RecalculationLogsPage";

function App() {
  return (
    <Router>
      <div>
        <Navbar />

        <Routes>
          <Route path="/" element={<Home />} />
          <Route path="/home" element={<Home />} />

          <Route path="/balances" element={<BalanceSheet />} />
          <Route path="/errorlog" element={<ErrorLogs />} />
          <Route path="/instruction" element={<Instructions />} />
          <Route path="/mapping_table" element={<MappingTable />} />
          <Route path="/imports" element={<Imports />} />
          <Route path="/yearly_output" element={<YearlyBalanceSheet />} />
          <Route path="/nsedata" element={<NSCData />} />
          <Route path="/search" element={<SearchPage />} />
          <Route path="/logs" element={<LogsPage />} />
          <Route
            path="/recalculation-logs"
            element={<RecalculationLogsPage />}
          />
          <Route path="/filters" element={<CompanyValuation />} />
        </Routes>
      </div>
    </Router>
  );
}

export default App;
