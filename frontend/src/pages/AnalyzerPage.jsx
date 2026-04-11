import { useState } from "react";

function StatCard({ title, value, variant = "default" }) {
  return (
    <div className={`card stat-card ${variant}`}>
      <h3>{title}</h3>
      <p>{value}</p>
    </div>
  );
}

function ScoreBar({ label, value }) {
  return (
    <div className="score-row">
      <div className="score-header">
        <span>{label}</span>
        <span>{value}</span>
      </div>
      <div className="score-bar">
        <div className="score-fill" style={{ width: `${value || 0}%` }}></div>
      </div>
    </div>
  );
}

function IssueList({ title, issues }) {
  return (
    <div className="card">
      <h3>{title}</h3>
      {issues.length === 0 ? (
        <p>No issues</p>
      ) : (
        <ul className="issue-list">
          {issues.map((issue, index) => (
            <li key={index}>
              <strong>{issue.rule_id || issue.type}</strong>
              <span>{issue.message}</span>
            </li>
          ))}
        </ul>
      )}
    </div>
      );
}

function getStatusVariant(status) {
  if (status === "Valid") return "success";
  if (status === "Rejected") return "danger";
  return "warning";
}

export default function AnalyzerPage() {
  const [file, setFile] = useState(null);
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const handleUpload = async () => {
    if (!file) {
      setError("Please choose a file first.");
      return;
    }

    setLoading(true);
    setError("");
    setResult(null);

    const formData = new FormData();
    formData.append("file", file);

    try {
      const response = await fetch("http://127.0.0.1:8000/upload-openapi", {
        method: "POST",
        body: formData,
      });

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.detail || "Upload failed");
      }

      setResult(data);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div>
      <div className="card hero-card">
        <div>
          <h1>API Analyzer</h1>
          <p>
            Upload an OpenAPI YAML or JSON file to validate structure, check best
            practices, and compute APRI.
          </p>
        </div>

        <div className="upload-box">
          <input
            type="file"
            accept=".yaml,.yml,.json"
            onChange={(e) => setFile(e.target.files[0])}
          />
          <button onClick={handleUpload} disabled={loading}>
            {loading ? "Analyzing..." : "Upload & Analyze"}
          </button>
        </div>

        {error && <p className="error-text">{error}</p>}
      </div>

      {result && (
        <>
          <div className="card summary-card">
            <h2>Analysis Summary</h2>
            <p>
              <strong>Filename:</strong> {result.filename}
            </p>
            <p>
              <strong>Decision:</strong>{" "}
              {result.status === "Valid"
                ? "This API is ready for publication."
                : result.status === "Rejected"
                ? "This API is rejected due to structural issues."
                : "This API is structurally valid but needs improvement before publication."}
            </p>
          </div>

          <div className="stats-grid">
            <StatCard
              title="Status"
              value={result.status}
              variant={getStatusVariant(result.status)}
            />
            <StatCard title="APRI Score" value={result.apri_score} />
            <StatCard title="Grade" value={result.grade} />
            <StatCard
              title="Publishable"
              value={String(result.publishable)}
              variant={result.publishable ? "success" : "danger"}
            />
          </div>

          <div className="stats-grid">
            <StatCard
              title="Structure Errors"
              value={result.issue_summary?.structure_errors ?? 0}
              variant={(result.issue_summary?.structure_errors ?? 0) > 0 ? "danger" : "success"}
            />
            <StatCard
              title="Warnings"
              value={result.issue_summary?.best_practice_warnings ?? 0}
              variant={(result.issue_summary?.best_practice_warnings ?? 0) > 0 ? "warning" : "success"}
            />
            <StatCard
              title="Total Issues"
              value={result.issue_summary?.total_issues ?? 0}
            />
          </div>

          <div className="card">
            <h2>Category Scores</h2>
            <ScoreBar
              label="Documentation"
              value={result.category_scores?.documentation || 0}
            />
            <ScoreBar
              label="Operational Clarity"
              value={result.category_scores?.operational_clarity || 0}
            />
            <ScoreBar
              label="Response Readiness"
              value={result.category_scores?.response_readiness || 0}
            />
            <ScoreBar
              label="REST Design Quality"
              value={result.category_scores?.rest_design_quality || 0}
            />
          </div>

          <details className="card">
            <summary>Show detailed compliance ratios</summary>
            <div className="stats-grid ratios-grid">
              {result.ratios &&
                Object.entries(result.ratios).map(([key, value]) => (
                  <StatCard key={key} title={key} value={value} />
                ))}
            </div>
          </details>

          <div className="issues-grid">
            <IssueList title="Structure Issues" issues={result.structure_issues || []} />
            <IssueList title="Best Practice Issues" issues={result.best_practice_issues || []} />
          </div>
        </>
      )}
    </div>
  );
}