import { useEffect, useMemo, useState } from "react";

const API_BASE = import.meta.env.VITE_API_BASE ?? "http://127.0.0.1:8000";
const WSO2_PORTAL_BASE = "https://localhost:9443/devportal/apis";
const LAST_SEEN_KEY = "catalog_last_seen_at";

function MetricCard({ label, value, note, tone = "neutral" }) {
  return (
    <div className={`metric-card ${tone}`}>
      <div className="metric-label">{label}</div>
      <div className="metric-value">{value}</div>
      {note ? <div className="metric-note">{note}</div> : null}
    </div>
  );
}

function formatDate(value) {
  if (!value) return "—";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return date.toLocaleString();
}

function isNewApi(api, lastSeenAt) {
  if (!lastSeenAt) return false;

  const publishedValue = api.published_at || api.uploaded_at;
  if (!publishedValue) return false;

  const publishedDate = new Date(publishedValue);
  const lastSeenDate = new Date(lastSeenAt);

  if (Number.isNaN(publishedDate.getTime()) || Number.isNaN(lastSeenDate.getTime())) {
    return false;
  }

  return publishedDate > lastSeenDate;
}

export default function AdminPage({ token, user }) {
  const [apis, setApis] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [deleteLoadingId, setDeleteLoadingId] = useState(null);
  const [deleteMessage, setDeleteMessage] = useState("");
  const [confirmDeleteId, setConfirmDeleteId] = useState(null);
  const [lastSeenAt, setLastSeenAt] = useState(localStorage.getItem(LAST_SEEN_KEY));

  const isAdmin = user?.role === "admin";

  const loadCatalog = async () => {
    setLoading(true);
    setError("");
    setDeleteMessage("");

    try {
      const previousSeenAt = localStorage.getItem(LAST_SEEN_KEY);
      setLastSeenAt(previousSeenAt);

      const response = await fetch(`${API_BASE}/catalog`, {
        headers: {
          Authorization: `Bearer ${token}`,
        },
      });

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.detail || "Failed to load catalog.");
      }

      setApis(Array.isArray(data.apis) ? data.apis : []);

      setTimeout(() => {
        const now = new Date().toISOString();
        localStorage.setItem(LAST_SEEN_KEY, now);
        setLastSeenAt(now);
      }, 1200);
    } catch (err) {
      setError(err.message || "Failed to load catalog.");
    } finally {
      setLoading(false);
    }
  };

  const deleteApi = async (apiId) => {
    if (!isAdmin) return;

    setDeleteLoadingId(apiId);
    setConfirmDeleteId(null);
    setError("");
    setDeleteMessage("");

    try {
      const response = await fetch(`${API_BASE}/catalog/${apiId}`, {
        method: "DELETE",
        headers: {
          Authorization: `Bearer ${token}`,
        },
      });

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.detail || "Failed to delete API.");
      }

      setDeleteMessage(data.message || "API removed from catalog.");
      await loadCatalog();
    } catch (err) {
      setError(err.message || "Failed to delete API.");
    } finally {
      setDeleteLoadingId(null);
    }
  };

  useEffect(() => {
    loadCatalog();
  }, []);

  const stats = useMemo(() => {
    const total = apis.length;
    const versioned = apis.filter((api) => api.version && String(api.version).trim()).length;
    const newCount = apis.filter((api) => isNewApi(api, lastSeenAt)).length;
    const wso2Published = apis.filter((api) => api.wso2_api_id).length;

    return {
      total,
      versioned,
      newCount,
      wso2Published,
      latest: total ? formatDate(apis[0]?.published_at || apis[0]?.uploaded_at) : "—",
    };
  }, [apis, lastSeenAt]);

  return (
    <div className="page-stack">
      <section className="hero-card compact-hero">
        <div className="hero-copy">
          <p className="eyebrow">Governance Catalog</p>
          <h1 className="hero-title">Published API Inventory</h1>
          <p className="hero-subtitle">
            {isAdmin
              ? "Monitor, audit, and manage APIs that passed the governance publication gate and were pushed to WSO2 API Manager."
              : "Browse published APIs in read-only mode, including who published each API and when."}
          </p>
        </div>

        <div className="hero-actions">
          <button className="secondary-btn" onClick={loadCatalog} disabled={loading}>
            {loading ? "Refreshing..." : "Refresh Catalog"}
          </button>
        </div>
      </section>

      {/* WSO2 Integration explanation */}
      <div className="wso2-integration-card">
        <img src="/images/wso2-logo.png" alt="WSO2 API Manager" width="64" height="64" style={{ objectFit: "contain", flexShrink: 0 }} />
        <div className="wso2-integration-body">
          <p className="eyebrow">WSO2 API Manager Integration</p>
          <h3>APIs published here are automatically pushed to WSO2</h3>
          <p>
            When an admin publishes an API that passes the governance gate, it is simultaneously
            saved to this catalog <strong>and</strong> imported into WSO2 API Manager, where it
            becomes available in the Developer Portal. The WSO2 API ID is stored alongside each
            catalog entry for traceability.
          </p>
          <div className="wso2-flow">
            <span className="wso2-flow-step">Upload OpenAPI</span>
            <span className="wso2-flow-arrow">→</span>
            <span className="wso2-flow-step">Validate &amp; Score</span>
            <span className="wso2-flow-arrow">→</span>
            <span className="wso2-flow-step">Governance Gate (ALLOW)</span>
            <span className="wso2-flow-arrow">→</span>
            <span className="wso2-flow-step destination">WSO2 API Manager</span>
          </div>
        </div>
      </div>

      <section className="catalog-grid">
        <MetricCard
          label="Published APIs"
          value={stats.total}
          note="Entries saved to catalog"
          tone="neutral"
        />
        <MetricCard
          label="On WSO2"
          value={stats.wso2Published}
          note="Pushed to WSO2 API Manager"
          tone={stats.wso2Published === stats.total && stats.total > 0 ? "success" : stats.wso2Published > 0 ? "warning" : "neutral"}
        />
        <MetricCard
          label="New Since Last Visit"
          value={stats.newCount}
          note="Marked as new this session"
          tone={stats.newCount > 0 ? "success" : "neutral"}
        />
        <MetricCard
          label="Latest Entry"
          value={stats.latest}
          note="Most recent publication"
          tone="neutral"
        />
      </section>

      <section>
        <div className="section-header">
          <div>
            <p className="eyebrow">{isAdmin ? "Admin Catalog Control" : "Read-Only Catalog"}</p>
            <h2>Accepted APIs</h2>
            <p>
              {isAdmin
                ? "Admins can view governance details, WSO2 status, and remove APIs from the catalog."
                : "Developers can view published APIs to support reuse and avoid duplication."}
            </p>
          </div>
        </div>

        {loading ? <div className="loader-line" /> : null}
        {error ? <div className="error-banner">{error}</div> : null}
        {deleteMessage ? <div className="success-banner">{deleteMessage}</div> : null}

        {!loading && !error && apis.length === 0 ? (
          <div className="empty-state">
            <h3>No APIs have been published yet.</h3>
            <p>Approved APIs will appear here once they pass the governance gate.</p>
          </div>
        ) : null}

        {!loading && !error && apis.length > 0 ? (
          <div className="table-wrap">
            <table className="catalog-table">
              <thead>
                <tr>
                  <th>ID</th>
                  <th>Filename</th>
                  <th>Title</th>
                  <th>Version</th>
                  <th>Published By</th>
                  <th>Published At</th>

                  {isAdmin ? <th>APRI</th> : null}
                  {isAdmin ? <th>Grade</th> : null}
                  {isAdmin ? <th>Decision</th> : null}
                  <th>WSO2</th>
                  {isAdmin ? <th>Actions</th> : null}
                </tr>
              </thead>

              <tbody>
                {apis.map((api) => {
                  const isNew = isNewApi(api, lastSeenAt);

                  return (
                    <tr key={api.id}>
                      <td>{api.id}</td>
                      <td className="catalog-file">
                        {api.filename || "—"}{" "}
                        {isNew ? <span className="badge success">New</span> : null}
                      </td>
                      <td>{api.title || "—"}</td>
                      <td>{api.version || "—"}</td>
                      <td>
                        {api.published_by_username || "—"}
                        {api.published_by_role ? ` (${api.published_by_role})` : ""}
                      </td>
                      <td>{formatDate(api.published_at || api.uploaded_at)}</td>

                      {isAdmin ? <td>{api.apri_score ?? "—"}</td> : null}
                      {isAdmin ? <td>{api.grade || "—"}</td> : null}
                      {isAdmin ? <td>{api.governance_decision || "—"}</td> : null}

                      <td>
                        {api.wso2_api_id ? (
                          <a
                            className="wso2-badge-pill published"
                            href={`${WSO2_PORTAL_BASE}/${api.wso2_api_id}/overview`}
                            target="_blank"
                            rel="noopener noreferrer"
                            title={`WSO2 API ID: ${api.wso2_api_id}`}
                          >
                            ↗ WSO2 Published
                          </a>
                        ) : (
                          <span className="wso2-badge-pill local">Local only</span>
                        )}
                      </td>

                      {isAdmin ? (
                        <td style={{ display: "flex", gap: 4, alignItems: "center" }}>
                          {confirmDeleteId === api.id ? (
                            <>
                              <button
                                className="ghost-btn"
                                style={{ color: "var(--danger, #ef4444)", borderColor: "var(--danger, #ef4444)" }}
                                onClick={() => deleteApi(api.id)}
                                onBlur={() => setConfirmDeleteId(null)}
                                disabled={deleteLoadingId === api.id}
                              >
                                {deleteLoadingId === api.id ? "Deleting..." : "Confirm?"}
                              </button>
                              <button className="ghost-btn" onClick={() => setConfirmDeleteId(null)}>
                                Cancel
                              </button>
                            </>
                          ) : (
                            <button
                              className="ghost-btn"
                              onClick={() => setConfirmDeleteId(api.id)}
                              disabled={deleteLoadingId === api.id}
                            >
                              {deleteLoadingId === api.id ? "Deleting..." : "Delete"}
                            </button>
                          )}
                        </td>
                      ) : null}
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        ) : null}
      </section>
    </div>
  );
}