import { useEffect, useMemo, useState } from "react";

const API_BASE = "http://127.0.0.1:8000";

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

export default function AdminPage({ token }) {
  const [apis, setApis] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const loadCatalog = async () => {
    setLoading(true);
    setError("");

    try {
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
    } catch (err) {
      setError(err.message || "Failed to load catalog.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadCatalog();
  }, []);

  const stats = useMemo(() => {
    const total = apis.length;
    const titled = apis.filter((api) => api.title && String(api.title).trim()).length;
    const versioned = apis.filter((api) => api.version && String(api.version).trim()).length;

    return {
      total,
      titled,
      versioned,
      latest: total ? formatDate(apis[0]?.uploaded_at) : "—",
    };
  }, [apis]);

  return (
    <div className="page-stack">
      <section className="card hero-card product-hero compact-hero">
        <div className="hero-copy">
          <p className="eyebrow">Governance Catalog</p>
          <h1 className="hero-title">Published API Inventory</h1>
          <p className="hero-subtitle">
            Monitor APIs that successfully passed the publication gate and were saved into
            the governance catalog.
          </p>
        </div>

        <div className="hero-actions">
          <button className="secondary-btn" onClick={loadCatalog} disabled={loading}>
            {loading ? "Refreshing..." : "Refresh Catalog"}
          </button>
        </div>
      </section>

      <section className="catalog-grid">
        <MetricCard
          label="Published APIs"
          value={stats.total}
          note="Entries saved to catalog"
          tone="neutral"
        />
        <MetricCard
          label="With Titles"
          value={stats.titled}
          note="Catalog items with info.title"
          tone={stats.titled === stats.total && stats.total > 0 ? "success" : "warning"}
        />
        <MetricCard
          label="With Versions"
          value={stats.versioned}
          note="Catalog items with info.version"
          tone={stats.versioned === stats.total && stats.total > 0 ? "success" : "warning"}
        />
        <MetricCard
          label="Latest Entry"
          value={stats.latest}
          note="Most recent publication timestamp"
          tone="neutral"
        />
      </section>

      <section className="card">
        <div className="section-header">
          <div>
            <p className="eyebrow">Catalog Records</p>
            <h2>Accepted APIs</h2>
            <p>Published APIs returned by the protected backend catalog endpoint.</p>
          </div>
        </div>

        {loading ? <div className="loader-line" /> : null}
        {error ? <div className="error-banner">{error}</div> : null}

        {!loading && !error && apis.length === 0 ? (
          <div className="empty-state">
            <h3>No APIs have been published yet.</h3>
            <p>Approved APIs will appear here once an admin publishes them.</p>
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
                  <th>Uploaded At</th>
                </tr>
              </thead>
              <tbody>
                {apis.map((api) => (
                  <tr key={api.id}>
                    <td>{api.id}</td>
                    <td className="catalog-file">{api.filename || "—"}</td>
                    <td>{api.title || "—"}</td>
                    <td>{api.version || "—"}</td>
                    <td>{formatDate(api.uploaded_at)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : null}
      </section>
    </div>
  );
}