import { useEffect, useMemo, useState } from "react";
import "./App.css";
import AnalyzerPage from "./pages/AnalyzerPage";
import AdminPage from "./pages/AdminPage";

const API_BASE = import.meta.env.VITE_API_BASE ?? "http://localhost:8000";
const LOGO_PATH = "/images/biat-it-logo.png";
const LOGO_ICON_PATH = "/images/biat-it-logo.png";

// ─── Shared helpers ────────────────────────────────────────────────────────────

function decodeJwtPayload(token) {
  try {
    const b64 = token.split(".")[1].replace(/-/g, "+").replace(/_/g, "/");
    const pad = "=".repeat((4 - (b64.length % 4)) % 4);
    return JSON.parse(atob(b64 + pad));
  } catch {
    return null;
  }
}

function isValidEmail(e) {
  return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(e);
}

function EyeIcon({ open }) {
  if (open) {
    return (
      <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
        <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z" />
        <circle cx="12" cy="12" r="3" />
      </svg>
    );
  }
  return (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
      <path d="M17.94 17.94A10.07 10.07 0 0 1 12 20c-7 0-11-8-11-8a18.45 18.45 0 0 1 5.06-5.94M9.9 4.24A9.12 9.12 0 0 1 12 4c7 0 11 8 11 8a18.5 18.5 0 0 1-2.16 3.19m-6.72-1.07a3 3 0 1 1-4.24-4.24" />
      <line x1="1" y1="1" x2="23" y2="23" />
    </svg>
  );
}

const STRENGTH_LABELS = ["", "Weak", "Fair", "Good", "Strong"];
const STRENGTH_COLORS = ["", "#ef4444", "#f97316", "#eab308", "#22c55e"];

function StrengthBar({ password }) {
  const checks = useMemo(() => ({
    length: password.length >= 8,
    letter: /[A-Za-z]/.test(password),
    number: /[0-9]/.test(password),
    special: /[^A-Za-z0-9]/.test(password),
  }), [password]);

  const level = useMemo(() => {
    if (password.length === 0) return 0;
    if (!checks.length) return 1;
    if (!checks.letter || !checks.number) return 2;
    if (!checks.special) return 3;
    return 4;
  }, [password, checks]);

  if (password.length === 0) return null;

  return (
    <div className="strength-bar">
      <div className="strength-segments">
        {[1, 2, 3, 4].map((i) => (
          <div key={i} className={`strength-segment${level >= i ? ` filled s${i}` : ""}`} />
        ))}
      </div>
      <span className="strength-label" style={{ color: STRENGTH_COLORS[level] }}>
        {STRENGTH_LABELS[level]}
      </span>
    </div>
  );
}

// ─── Brand / layout components (unchanged) ─────────────────────────────────────

function BrandLogo({ compact = false }) {
  if (compact) {
    return (
      <div className="brand-logo compact">
        <img src={LOGO_ICON_PATH} alt="BIAT IT" style={{ height: 52, width: "auto", maxWidth: 200, objectFit: "contain" }} />
      </div>
    );
  }
  return (
    <div className="brand-logo">
      <img src={LOGO_PATH} alt="BIAT IT" style={{ maxHeight: 52, width: "auto", objectFit: "contain" }} />
    </div>
  );
}

function Wso2Mark({ size = "sm" }) {
  const dim = size === "lg" ? 64 : 48;
  return (
    <img
      src="/images/wso2-logo.png"
      alt="WSO2 API Manager"
      width={dim}
      height={dim}
      style={{ borderRadius: size === "lg" ? 18 : 13, flexShrink: 0 }}
    />
  );
}

function saveSession(data) {
  localStorage.setItem("auth_token", data.access_token);
  localStorage.setItem("refresh_token", data.refresh_token || "");
  localStorage.setItem("auth_user", JSON.stringify(data.user));
}

function clearSession() {
  localStorage.removeItem("auth_token");
  localStorage.removeItem("refresh_token");
  localStorage.removeItem("auth_user");
}

// ─── Verify Email page ────────────────────────────────────────────────────────

function VerifyEmailPage() {
  const [status, setStatus] = useState("loading");

  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    const token = params.get("token");
    if (!token) { setStatus("error"); return; }

    fetch(`${API_BASE}/auth/verify-email?token=${encodeURIComponent(token)}`)
      .then((r) => r.json())
      .then((d) => setStatus(d.verified ? "success" : "error"))
      .catch(() => setStatus("error"));
  }, []);

  const goLogin = () => {
    window.history.replaceState({}, "", "/");
    window.location.reload();
  };

  return (
    <div className="verify-page">
      <div className="verify-card">
        {status === "loading" && <p>Verifying your email…</p>}
        {status === "success" && (
          <>
            <h2>Email verified!</h2>
            <p>Your account is now active. You can sign in.</p>
            <button className="primary-btn" onClick={goLogin}>Go to login</button>
          </>
        )}
        {status === "error" && (
          <>
            <h2>Invalid link</h2>
            <p>This verification link is invalid or has expired. Request a new one by registering again or contacting support.</p>
            <button className="primary-btn" onClick={goLogin}>Go to login</button>
          </>
        )}
      </div>
    </div>
  );
}

// ─── Reset Password page ──────────────────────────────────────────────────────

function ResetPasswordPage() {
  const [password, setPassword] = useState("");
  const [confirm, setConfirm] = useState("");
  const [showPw, setShowPw] = useState(false);
  const [status, setStatus] = useState("idle");
  const [error, setError] = useState("");

  const token = new URLSearchParams(window.location.search).get("token") || "";

  const handleSubmit = async () => {
    setError("");
    if (!password || !confirm) { setError("Both fields are required."); return; }
    if (password !== confirm) { setError("Passwords do not match."); return; }
    if (password.length < 8 || !/[A-Za-z]/.test(password) || !/[0-9]/.test(password)) {
      setError("Password must be 8+ characters with letters and numbers.");
      return;
    }
    setStatus("loading");
    try {
      const r = await fetch(`${API_BASE}/auth/reset-password`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ token, new_password: password }),
      });
      const d = await r.json();
      if (!r.ok) throw new Error(d.detail || "Reset failed.");
      setStatus("success");
      setTimeout(() => { window.history.replaceState({}, "", "/"); window.location.reload(); }, 2500);
    } catch (e) {
      setError(e.message);
      setStatus("idle");
    }
  };

  return (
    <div className="reset-page">
      <div className="reset-card">
        <h2>Reset password</h2>
        {status === "success" ? (
          <p>Password reset! Redirecting to login…</p>
        ) : (
          <>
            <p>Choose a new password for your account.</p>
            <div className="auth-form" style={{ textAlign: "left" }}>
              <label>
                New password
                <div className="input-field-wrap">
                  <input
                    type={showPw ? "text" : "password"}
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    placeholder="••••••••"
                  />
                  <button type="button" className="eye-btn" onClick={() => setShowPw((v) => !v)}>
                    <EyeIcon open={showPw} />
                  </button>
                </div>
                <StrengthBar password={password} />
              </label>
              <label>
                Confirm password
                <div className="input-field-wrap">
                  <input
                    type="password"
                    value={confirm}
                    onChange={(e) => setConfirm(e.target.value)}
                    placeholder="••••••••"
                    onKeyDown={(e) => e.key === "Enter" && handleSubmit()}
                  />
                </div>
              </label>
              {error ? <div className="error-banner reveal-shake">{error}</div> : null}
              <button className="primary-btn" onClick={handleSubmit} disabled={status === "loading"}>
                {status === "loading" ? <span className="btn-spinner" /> : "Reset password"}
              </button>
            </div>
          </>
        )}
      </div>
    </div>
  );
}

// ─── Profile section ──────────────────────────────────────────────────────────

function ProfileSection({ token, user, sessionVerified }) {
  const AVATAR_COLORS = ["#245fe6", "#7c3aed", "#0891b2", "#059669", "#d97706", "#dc2626"];
  const charSum = (user.username || "").split("").reduce((a, c) => a + c.charCodeAt(0), 0);
  const avatarColor = AVATAR_COLORS[charSum % 6];
  const initials = (user.username || "?").slice(0, 2).toUpperCase();

  const [history, setHistory] = useState([]);
  const [historyLoading, setHistoryLoading] = useState(true);

  const [currentPw, setCurrentPw] = useState("");
  const [newPw, setNewPw] = useState("");
  const [confirmPw, setConfirmPw] = useState("");
  const [showNewPw, setShowNewPw] = useState(false);
  const [pwError, setPwError] = useState("");
  const [pwSuccess, setPwSuccess] = useState("");
  const [pwLoading, setPwLoading] = useState(false);

  useEffect(() => {
    fetch(`${API_BASE}/auth/login-history`, { headers: { Authorization: `Bearer ${token}` } })
      .then((r) => r.json())
      .then((d) => setHistory(d.history || []))
      .catch(() => {})
      .finally(() => setHistoryLoading(false));
  }, [token]);

  const handleChangePassword = async () => {
    setPwError(""); setPwSuccess("");
    if (!currentPw || !newPw || !confirmPw) { setPwError("All fields are required."); return; }
    if (newPw !== confirmPw) { setPwError("New passwords do not match."); return; }
    if (newPw.length < 8 || !/[A-Za-z]/.test(newPw) || !/[0-9]/.test(newPw)) {
      setPwError("Password must be 8+ characters with letters and numbers.");
      return;
    }
    setPwLoading(true);
    try {
      const r = await fetch(`${API_BASE}/auth/change-password`, {
        method: "POST",
        headers: { "Content-Type": "application/json", Authorization: `Bearer ${token}` },
        body: JSON.stringify({ current_password: currentPw, new_password: newPw }),
      });
      const d = await r.json();
      if (!r.ok) throw new Error(d.detail || "Failed to change password.");
      setPwSuccess("Password changed successfully.");
      setCurrentPw(""); setNewPw(""); setConfirmPw("");
    } catch (e) {
      setPwError(e.message);
    } finally {
      setPwLoading(false);
    }
  };

  return (
    <div className="profile-grid">

      {/* Account info */}
      <div className="profile-card">
        <h3>Account</h3>
        <div className="profile-identity">
          <div className="avatar-circle" style={{ background: avatarColor }}>{initials}</div>
          <div className="profile-meta">
            <p className="profile-username">{user.username}</p>
            <div>
              {user.email_verified ? (
                <span className="verified-badge">✓ {user.email}</span>
              ) : user.email ? (
                <span className="unverified-badge">⚠ {user.email} — Not verified</span>
              ) : (
                <span className="unverified-badge">⚠ No email set</span>
              )}
            </div>
            <span className={`badge ${sessionVerified && user.role === "admin" ? "success" : "neutral"}`}>{sessionVerified ? user.role : "…"}</span>
            {user.oauth_provider ? <p className="mini-value">OAuth: {user.oauth_provider}</p> : null}
            {user.created_at ? (
              <p style={{ fontSize: 12, color: "var(--muted)", margin: 0 }}>
                Member since {new Date(user.created_at).toLocaleDateString()}
              </p>
            ) : null}
          </div>
        </div>
      </div>

      {/* Change password — only for non-OAuth users */}
      {!user.oauth_provider ? (
        <div className="profile-card">
          <h3>Change Password</h3>
          <div className="auth-form">
            <label>
              Current password
              <div className="input-field-wrap">
                <input type="password" value={currentPw} onChange={(e) => setCurrentPw(e.target.value)} placeholder="••••••••" />
              </div>
            </label>
            <label>
              New password
              <div className="input-field-wrap">
                <input
                  type={showNewPw ? "text" : "password"}
                  value={newPw}
                  onChange={(e) => setNewPw(e.target.value)}
                  placeholder="••••••••"
                />
                <button type="button" className="eye-btn" onClick={() => setShowNewPw((v) => !v)}>
                  <EyeIcon open={showNewPw} />
                </button>
              </div>
              <StrengthBar password={newPw} />
            </label>
            <label>
              Confirm new password
              <div className="input-field-wrap">
                <input type="password" value={confirmPw} onChange={(e) => setConfirmPw(e.target.value)} placeholder="••••••••" />
              </div>
            </label>
            {pwError ? <div className="error-banner reveal-shake">{pwError}</div> : null}
            {pwSuccess ? <div className="success-banner">{pwSuccess}</div> : null}
            <button className="primary-btn" onClick={handleChangePassword} disabled={pwLoading}>
              {pwLoading ? <span className="btn-spinner" /> : "Change Password"}
            </button>
          </div>
        </div>
      ) : null}

      {/* Login history */}
      <div className="profile-card">
        <h3>Login History</h3>
        {historyLoading ? (
          <p style={{ color: "var(--muted)", fontSize: 14 }}>Loading…</p>
        ) : history.length === 0 ? (
          <p style={{ color: "var(--muted)", fontSize: 14 }}>No login history available.</p>
        ) : (
          <table className="history-table">
            <thead>
              <tr>
                <th>Date &amp; Time</th>
                <th>Status</th>
              </tr>
            </thead>
            <tbody>
              {history.map((h, i) => (
                <tr key={i}>
                  <td>{new Date(h.attempted_at).toLocaleString()}</td>
                  <td className={h.success ? "status-success" : "status-failed"}>
                    {h.success ? "✓ Success" : "✗ Failed"}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

    </div>
  );
}

// ─── Auth page ────────────────────────────────────────────────────────────────

function AuthPage({ onAuth }) {
  const [mode, setMode] = useState("login"); // "login" | "register" | "forgot"
  const [username, setUsername] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [rememberMe, setRememberMe] = useState(false);
  const [showPassword, setShowPassword] = useState(false);
  const [error, setError] = useState("");
  const [successMsg, setSuccessMsg] = useState("");
  const [loading, setLoading] = useState(false);

  const passwordChecks = useMemo(() => ({
    length: password.length >= 8,
    letter: /[A-Za-z]/.test(password),
    number: /[0-9]/.test(password),
    special: /[^A-Za-z0-9]/.test(password),
  }), [password]);

  const oauthLogin = (provider) => {
    window.location.href = `${API_BASE}/auth/${provider}`;
  };

  const switchMode = (m) => { setMode(m); setError(""); setSuccessMsg(""); };

  const submit = async () => {
    setError(""); setSuccessMsg("");

    if (mode === "forgot") {
      if (!email.trim() || !isValidEmail(email.trim())) {
        setError("Please enter a valid email address.");
        return;
      }
      setLoading(true);
      try {
        const r = await fetch(`${API_BASE}/auth/forgot-password`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ email: email.trim() }),
        });
        const d = await r.json();
        setSuccessMsg(d.message || "If this email is registered, you will receive a reset link.");
      } catch {
        setError("Request failed. Please try again.");
      } finally {
        setLoading(false);
      }
      return;
    }

    if (!username.trim() || !password.trim()) {
      setError("Username and password are required.");
      return;
    }

    if (mode === "register") {
      if (!email.trim() || !isValidEmail(email.trim())) {
        setError("A valid email address is required.");
        return;
      }
      if (!passwordChecks.length || !passwordChecks.letter || !passwordChecks.number) {
        setError("Password must be at least 8 characters and contain letters and numbers.");
        return;
      }
    }

    setLoading(true);
    try {
      const body = mode === "register"
        ? { username: username.trim(), password, email: email.trim() }
        : { username: username.trim(), password, remember_me: rememberMe };

      const response = await fetch(`${API_BASE}/auth/${mode}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      });

      const data = await response.json();

      if (!response.ok) {
        throw new Error(Array.isArray(data.detail) ? data.detail[0]?.msg : data.detail || "Authentication failed.");
      }

      if (mode === "register") {
        setSuccessMsg(data.message || "Check your email to verify your account.");
      } else {
        saveSession(data);
        onAuth(data.user, data.access_token);
      }
    } catch (err) {
      setError(err.message || "Authentication failed.");
    } finally {
      setLoading(false);
    }
  };

  const emailValid = email.trim().length > 0 && isValidEmail(email.trim());
  const emailInvalid = email.trim().length > 0 && !isValidEmail(email.trim());

  return (
    <div className="auth-screen">
      <section className="auth-panel">
        <div className="auth-left">
          <BrandLogo />
          <div className="auth-intro">
            <p className="eyebrow">Internal API Governance Platform</p>
            <h1>Control OpenAPI quality before publication.</h1>
            <p>
              Analyze API specifications with validation rules, APRI scoring, AI-assisted review,
              duplicate detection, OAuth access, and role-based publication control.
            </p>
          </div>
          <div className="auth-workflow">
            <div><span>01</span><p>Upload OpenAPI</p></div>
            <div><span>02</span><p>Validate &amp; score</p></div>
            <div><span>03</span><p>Governance decision</p></div>
            <div><span>04</span><p>Publish to WSO2 AM</p></div>
          </div>
        </div>

        <div className="auth-card card" style={{ maxHeight: "calc(100vh - 80px)", overflowY: "auto", scrollBehavior: "smooth" }}>
          <div>
            <p className="eyebrow">Secure Access</p>
            <h2>
              {mode === "login" ? "Welcome back" :
               mode === "register" ? "Create developer account" :
               "Reset your password"}
            </h2>
            <p className="muted">
              {mode === "login" ? "Sign in with your account or continue with OAuth." :
               mode === "register" ? "New accounts are created with developer access by default." :
               "Enter your email and we'll send you a reset link."}
            </p>
          </div>

          {mode !== "forgot" ? (
            <>
              <div className="oauth-grid">
                <button className="oauth-btn" onClick={() => oauthLogin("google")}>
                  <img src="/images/google.svg" alt="Google" />
                  Continue with Google
                </button>
                <button className="oauth-btn" onClick={() => oauthLogin("github")}>
                  <img src="/images/github.svg" alt="GitHub" />
                  Continue with GitHub
                </button>
              </div>

              <div className="security-notice">
                <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
                  <rect x="3" y="11" width="18" height="11" rx="2" ry="2" />
                  <path d="M7 11V7a5 5 0 0 1 10 0v4" />
                </svg>
                <span>Secured with PBKDF2-HMAC-SHA256 · JWT · Rate limited</span>
              </div>

              <div className="auth-divider"><span>or use username and password</span></div>

              <div className="auth-tabs">
                <div className={`tab-slider${mode === "register" ? " right" : ""}`} />
                <button className={mode === "login" ? "auth-tab active" : "auth-tab"} onClick={() => switchMode("login")}>
                  Login
                </button>
                <button className={mode === "register" ? "auth-tab active" : "auth-tab"} onClick={() => switchMode("register")}>
                  Create Account
                </button>
              </div>
            </>
          ) : null}

          <div className="auth-form">
            {/* Forgot-password mode: email only */}
            {mode === "forgot" ? (
              <>
                <label>
                  Email
                  <div className="input-field-wrap">
                    <input
                      value={email}
                      onChange={(e) => setEmail(e.target.value)}
                      placeholder="you@company.com"
                      onKeyDown={(e) => e.key === "Enter" && submit()}
                    />
                    {emailValid ? <span className="email-check valid">✓</span> : null}
                    {emailInvalid ? <span className="email-check invalid">✗</span> : null}
                  </div>
                </label>
                {error ? <div className="error-banner reveal-shake">{error}</div> : null}
                {successMsg ? <div className="success-banner">{successMsg}</div> : null}
                {!successMsg ? (
                  <button className="primary-btn" onClick={submit} disabled={loading}>
                    {loading ? <span className="btn-spinner" /> : "Send reset link"}
                  </button>
                ) : null}
                <button className="forgot-link" onClick={() => switchMode("login")}>
                  ← Back to login
                </button>
              </>
            ) : (
              <>
                <label>
                  Username
                  <div className="input-field-wrap">
                    <input value={username} onChange={(e) => setUsername(e.target.value)} placeholder="mohamed-dev" />
                  </div>
                </label>

                {mode === "register" ? (
                  <label>
                    Email
                    <div className="input-field-wrap">
                      <input
                        value={email}
                        onChange={(e) => setEmail(e.target.value)}
                        placeholder="developer@company.com"
                      />
                      {emailValid ? <span className="email-check valid">✓</span> : null}
                      {emailInvalid ? <span className="email-check invalid">✗</span> : null}
                    </div>
                  </label>
                ) : null}

                <label>
                  Password
                  <div className="input-field-wrap">
                    <input
                      value={password}
                      onChange={(e) => setPassword(e.target.value)}
                      placeholder="••••••••"
                      type={showPassword ? "text" : "password"}
                      onKeyDown={(e) => e.key === "Enter" && submit()}
                    />
                    <button type="button" className="eye-btn" onClick={() => setShowPassword((v) => !v)}>
                      <EyeIcon open={showPassword} />
                    </button>
                  </div>
                  {mode === "register" ? <StrengthBar password={password} /> : null}
                </label>

                {mode === "login" ? (
                  <>
                    <button className="forgot-link" onClick={() => switchMode("forgot")}>
                      Forgot password?
                    </button>
                    <label className="remember-me">
                      <input type="checkbox" checked={rememberMe} onChange={(e) => setRememberMe(e.target.checked)} />
                      Keep me signed in for 30 days
                    </label>
                  </>
                ) : null}

                {error ? <div className="error-banner reveal-shake">{error}</div> : null}
                {successMsg ? <div className="success-banner">{successMsg}</div> : null}

                {!successMsg ? (
                  <button className="primary-btn" onClick={submit} disabled={loading}>
                    {loading ? <span className="btn-spinner" /> : mode === "login" ? "Login" : "Create Account"}
                  </button>
                ) : null}
              </>
            )}
          </div>
        </div>
      </section>
    </div>
  );
}

// ─── Main App ─────────────────────────────────────────────────────────────────

export default function App() {
  const pathname = window.location.pathname;

  const [activePage, setActivePage] = useState("analyzer");
  const [token, setToken] = useState(localStorage.getItem("auth_token") || "");
  const [user, setUser] = useState(() => {
    const saved = localStorage.getItem("auth_user");
    return saved ? JSON.parse(saved) : null;
  });
  const [sessionExpiring, setSessionExpiring] = useState(false);
  const [sessionVerified, setSessionVerified] = useState(false);

  // Handle special route pages before any auth logic
  if (pathname === "/verify-email") return <VerifyEmailPage />;
  if (pathname === "/reset-password") return <ResetPasswordPage />;

  // OAuth callback token extraction
  useEffect(() => {
    const hash = new URLSearchParams(window.location.hash.slice(1));
    const oauthAccess = hash.get("access_token");
    const oauthRefresh = hash.get("refresh_token");

    if (pathname === "/oauth-callback" && oauthAccess) {
      localStorage.setItem("auth_token", oauthAccess);
      localStorage.setItem("refresh_token", oauthRefresh || "");

      try {
        const decoded = decodeJwtPayload(oauthAccess);
        const bootstrapUser = { id: parseInt(decoded.sub, 10), username: decoded.username, role: decoded.role };
        localStorage.setItem("auth_user", JSON.stringify(bootstrapUser));
        setUser(bootstrapUser);
      } catch { /* /auth/me will hydrate the user */ }

      window.history.replaceState({}, document.title, "/");
      setToken(oauthAccess);
    }
  }, []);

  // Verify session on token change
  useEffect(() => {
    if (!token) return;
    const verify = async () => {
      try {
        const response = await fetch(`${API_BASE}/auth/me`, { headers: { Authorization: `Bearer ${token}` } });
        if (!response.ok) throw new Error("Session expired");
        const data = await response.json();
        setUser(data);
        setSessionVerified(true);
        localStorage.setItem("auth_user", JSON.stringify(data));
      } catch {
        clearSession();
        setToken("");
        setUser(null);
      }
    };
    verify();
  }, [token]);

  // Session expiry monitor — checks every 30 s, warns at < 5 min
  useEffect(() => {
    if (!token) return;
    const check = () => {
      const payload = decodeJwtPayload(token);
      if (!payload) return;
      const remaining = (payload.exp || 0) - Math.floor(Date.now() / 1000);
      setSessionExpiring(remaining > 0 && remaining < 300);
    };
    check();
    const id = setInterval(check, 30000);
    return () => clearInterval(id);
  }, [token]);

  const renewSession = async () => {
    const refreshToken = localStorage.getItem("refresh_token");
    if (!refreshToken) return;
    try {
      const r = await fetch(`${API_BASE}/auth/refresh`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ refresh_token: refreshToken }),
      });
      const d = await r.json();
      if (!r.ok) throw new Error();
      localStorage.setItem("auth_token", d.access_token);
      localStorage.setItem("refresh_token", d.refresh_token || refreshToken);
      setToken(d.access_token);
      setSessionExpiring(false);
    } catch { /* silent */ }
  };

  const logout = async () => {
    const refreshToken = localStorage.getItem("refresh_token");
    try {
      if (refreshToken && token) {
        await fetch(`${API_BASE}/auth/logout`, {
          method: "POST",
          headers: { "Content-Type": "application/json", Authorization: `Bearer ${token}` },
          body: JSON.stringify({ refresh_token: refreshToken }),
        });
      }
    } catch { /* Local logout still happens */ }
    clearSession();
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
      {sessionExpiring ? (
        <div className="session-expiry-banner">
          Your session expires soon.
          <button className="session-renew-btn" onClick={renewSession}>Renew session</button>
        </div>
      ) : null}

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
          <span className={`badge ${sessionVerified && user.role === "admin" ? "success" : "neutral"}`}>{sessionVerified ? user.role : "…"}</span>
          {user.oauth_provider ? <p className="mini-value">OAuth: {user.oauth_provider}</p> : null}
        </div>

        <button className="ghost-btn logout-btn" onClick={logout}>Logout</button>

        <div className="nav-group">
          <button className={activePage === "analyzer" ? "nav-btn active" : "nav-btn"} onClick={() => setActivePage("analyzer")}>
            <span className="nav-title">Analyzer</span>
            <span className="nav-subtitle">Validation, APRI, AI review</span>
          </button>

          <button className={activePage === "admin" ? "nav-btn active" : "nav-btn"} onClick={() => setActivePage("admin")}>
            <span className="nav-title">Catalog</span>
            <span className="nav-subtitle">
              {user.role === "admin" ? "Inventory and governance control" : "Read-only API inventory"}
            </span>
          </button>

          <button className={activePage === "profile" ? "nav-btn active" : "nav-btn"} onClick={() => setActivePage("profile")}>
            <span className="nav-title">Profile</span>
            <span className="nav-subtitle">Account settings &amp; security</span>
          </button>
        </div>

        <div className="sidebar-footer">
          <div className="wso2-sidebar-card">
            <Wso2Mark size="sm" />
            <div>
              <p className="wso2-sidebar-label">WSO2 API Manager</p>
              <p className="wso2-sidebar-value">
                <span className="wso2-dot" style={{ display: "inline-block", marginRight: 6, verticalAlign: "middle" }} />
                Connected · localhost:9443
              </p>
            </div>
          </div>
        </div>
      </aside>

      <main className="main-content">
        {activePage === "admin" ? (
          <AdminPage token={token} user={user} />
        ) : activePage === "profile" ? (
          <ProfileSection token={token} user={user} sessionVerified={sessionVerified} />
        ) : (
          <AnalyzerPage token={token} user={user} />
        )}
      </main>
    </div>
  );
}
