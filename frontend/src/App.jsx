import { useState } from "react";
import "./App.css";
import AnalyzerPage from "./pages/AnalyzerPage";
import AdminPage from "./pages/AdminPage";

export default function App() {
  const [activePage, setActivePage] = useState("analyzer");

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <h2>API Governance</h2>
        <button
          className={activePage === "analyzer" ? "nav-btn active" : "nav-btn"}
          onClick={() => setActivePage("analyzer")}
        >
          Analyzer
        </button>
        <button
          className={activePage === "admin" ? "nav-btn active" : "nav-btn"}
          onClick={() => setActivePage("admin")}
        >
          Admin Dashboard
        </button>
      </aside>

      <main className="main-content">
        {activePage === "analyzer" ? <AnalyzerPage /> : <AdminPage />}
      </main>
    </div>
  );
}