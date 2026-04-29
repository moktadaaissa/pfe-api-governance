import { useEffect, useState } from "react";
import "./App.css";
import AnalyzerPage from "./pages/AnalyzerPage";
import AdminPage from "./pages/AdminPage";

const API_BASE = "http://127.0.0.1:8000";
const LOGO_PATH = "/images/biat-it-logo.png";

function BrandLogo({ compact = false }) {
  return (
    <div className={compact ? "brand-logo compact" : "brand-logo"}>
      <img
        src={LOGO_PATH}
        alt="BIAT IT"
        onError={(e) => {
          e.currentTarget.style.display = "none";
        }}
      />
      <div className="brand-fallback">BIAT IT</div>
    </div>
  );
}

function AuthPage({ onAuth }) {
  const [mode, setMode] = useState("login");
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  const submit = async () => {
    setError("");

    if (!username.trim() || !password.trim()) {
      setError("Username and password are required.");
      return;
    }

    setLoading(true);

    try {
      const response = await fetch(`${API_BASE}/auth/${mode}`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          username: username.trim(),
          password,
        }),
      });

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.detail || "Authentication failed.");
      }

      localStorage.setItem("auth_token", data.access_token);
      localStorage.setItem("auth_user", JSON.stringify(data.user));

      onAuth(data.user, data.access_token);
    } catch (err) {
      setError(err.message || "Authentication failed.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="auth-screen">
      <section className="auth-panel">
        <div className="auth-left">
          <BrandLogo />

          <div className="auth-intro">
            <p className="eyebrow">Internal API Governance Platform</p>
            <h1>Control OpenAPI quality before publication.</h1>
            <p>
              Analyze API specifications with validation rules, APRI scoring,
              AI-assisted review, duplicate detection, and role-based publication control.
            </p>
          </div>

          <div className="auth-workflow">
            <div>
              <span>01</span>
              <p>Upload OpenAPI</p>
            </div>
            <div>
              <span>02</span>
              <p>Validate & score</p>
            </div>
            <div>
              <span>03</span>
              <p>Review decision</p>
            </div>
            <div>
              <span>04</span>
              <p>Publish safely</p>
            </div>
          </div>
        </div>

        <div className="auth-card card">
          <div>
            <p className="eyebrow">Secure Access</p>
            <h2>{mode === "login" ? "Welcome back" : "Create developer account"}</h2>
            <p className="muted">
              {mode === "login"
                ? "Sign in to access the governance workbench."
                : "New accounts are created with developer access."}
            </p>
          </div>

          <div className="auth-tabs">
            <button
              className={mode === "login" ? "auth-tab active" : "auth-tab"}
              onClick={() => {
                setMode("login");
                setError("");
              }}
            >
              Login
            </button>
            <button
              className={mode === "register" ? "auth-tab active" : "auth-tab"}
              onClick={() => {
                setMode("register");
                setError("");
              }}
            >
              Create Account
            </button>
          </div>

          <div className="auth-form">
            <label>
              Username
              <input
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                placeholder="admin or developer"
              />
            </label>

            <label>
              Password
              <input
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="••••••••"
                type="password"
              />
            </label>

            {error ? <div className="error-banner">{error}</div> : null}

            <button className="primary-btn" onClick={submit} disabled={loading}>
              {loading ? "Please wait..." : mode === "login" ? "Login" : "Create Account"}
            </button>

            <div className="info-banner">
              Demo users: <strong>admin/admin123</strong> or{" "}
              <strong>developer/dev123</strong>
            </div>
          </div>
        </div>
      </section>
    </div>
  );
}

export default function App() {
  const [activePage, setActivePage] = useState("analyzer");
  const [token, setToken] = useState(localStorage.getItem("auth_token") || "");
  const [user, setUser] = useState(() => {
    const saved = localStorage.getItem("auth_user");
    return saved ? JSON.parse(saved) : null;
  });

  useEffect(() => {
    if (!token) return;

    const verify = async () => {
      try {
        const response = await fetch(`${API_BASE}/auth/me`, {
          headers: {
            Authorization: `Bearer ${token}`,
          },
        });

        if (!response.ok) {
          throw new Error("Session expired");
        }

        const data = await response.json();
        setUser(data);
        localStorage.setItem("auth_user", JSON.stringify(data));
      } catch {
        localStorage.removeItem("auth_token");
        localStorage.removeItem("auth_user");
        setToken("");
        setUser(null);
      }
    };

    verify();
  }, [token]);

  const logout = () => {
    localStorage.removeItem("auth_token");
    localStorage.removeItem("auth_user");
    setToken("");
    setUser(null);
    setActivePage("analyzer");
  };

  if (!token || !user) {
    return (
      <AuthPage
        onAuth={(newUser, newToken) => {
          setUser(newUser);
          setToken(newToken);
        }}
      />
    );
  }

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div className="sidebar-brand">
          <BrandLogo compact />
          <div>
            <p className="brand-kicker">API Governance</p>
            <h2>Workbench</h2>
          </div>
        </div>

        <div className="account-card">
          <p className="mini-label">Signed in as</p>
          <p className="account-name">{user.username}</p>
          <span className={`badge ${user.role === "admin" ? "success" : "neutral"}`}>
            {user.role}
          </span>
        </div>

        <div className="nav-group">
          <button
            className={activePage === "analyzer" ? "nav-btn active" : "nav-btn"}
            onClick={() => setActivePage("analyzer")}
          >
            <span className="nav-title">Analyzer</span>
            <span className="nav-subtitle">Validation, APRI, AI review</span>
          </button>

          {user.role === "admin" ? (
            <button
              className={activePage === "admin" ? "nav-btn active" : "nav-btn"}
              onClick={() => setActivePage("admin")}
            >
              <span className="nav-title">Catalog</span>
              <span className="nav-subtitle">Published API inventory</span>
            </button>
          ) : null}
        </div>

        <div className="sidebar-footer">
          <div className="mini-card">
            <p className="mini-label">Governance Flow</p>
            <p className="mini-value">Import → Validate → Score → Decide → Publish</p>
          </div>

          <button className="ghost-btn logout-btn" onClick={logout}>
            Logout
          </button>
        </div>
      </aside>

      <main className="main-content">
        {activePage === "admin" && user.role === "admin" ? (
          <AdminPage token={token} />
        ) : (
          <AnalyzerPage token={token} user={user} />
        )}
      </main>
    </div>
  );
}