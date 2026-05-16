import { useEffect, useMemo, useState } from "react";

const API_BASE = import.meta.env.VITE_API_BASE ?? "http://127.0.0.1:8000";

const ISSUE_GROUPS = {
  documentation: {
    title: "Documentation",
    description: "Summaries, descriptions, and response descriptions.",
    rules: [
      "missing_summary",
      "missing_description",
      "short_description",
      "missing_response_description",
    ],
  },
  operational_clarity: {
    title: "Operational Clarity",
    description: "Operation IDs and tags for readability and maintainability.",
    rules: [
      "missing_operation_id",
      "invalid_operation_id",
      "missing_tags",
      "empty_tags",
    ],
  },
  response_readiness: {
    title: "Response Readiness",
    description: "Success, error, and request-body readiness for publication.",
    rules: [
      "missing_success_response",
      "missing_error_response",
      "missing_request_body",
    ],
  },
  rest_governance_quality: {
    title: "REST Governance Quality",
    description: "Path naming and REST-oriented governance rules.",
    rules: ["discouraged_verb_in_path", "underscore_in_path"],
  },
};

function getStatusTone(value) {
  const v = String(value || "").toLowerCase();

  if (
    [
      "valid",
      "excellent",
      "good",
      "clean",
      "allow",
      "published",
      "true",
      "test_ready",
      "passed",
      "success",
    ].includes(v)
  ) {
    return "success";
  }

  if (
    [
      "rejected",
      "blocked",
      "poor",
      "false",
      "block",
      "not_ready",
      "error",
      "major",
    ].includes(v)
  ) {
    return "danger";
  }

  return "warning";
}

function getScoreTone(score) {
  const num = Number(score || 0);
  if (num >= 85) return "success";
  if (num >= 50) return "warning";
  return "danger";
}

function labelizeKey(value) {
  return String(value || "")
    .replaceAll("_", " ")
    .replace(/\b\w/g, (c) => c.toUpperCase());
}

function StatusChip({ label, value }) {
  return (
    <span className={`status-chip ${getStatusTone(value)}`}>
      <span>{label}</span>
      <strong>{String(value)}</strong>
    </span>
  );
}

function MetricCard({ label, value, note, tone = "neutral" }) {
  return (
    <div className={`metric-card ${tone}`}>
      <div className="metric-label">{label}</div>
      <div className="metric-value">{value}</div>
      {note ? <div className="metric-note">{note}</div> : null}
    </div>
  );
}

function ScoreBar({ label, value }) {
  const tone = getScoreTone(value);
  const safeValue = Math.max(0, Math.min(Number(value || 0), 100));

  return (
    <div className="score-row">
      <div className="score-top">
        <span>{label}</span>
        <strong>{safeValue}%</strong>
      </div>
      <div className="score-track">
        <div className={`score-fill ${tone}`} style={{ width: `${safeValue}%` }} />
      </div>
    </div>
  );
}

function SectionBlock({ title, subtitle, meta = [], defaultOpen = false, children }) {
  const [open, setOpen] = useState(defaultOpen);

  return (
    <section className={`section-block ${open ? "open" : ""}`}>
      <button
        type="button"
        className="section-trigger"
        onClick={() => setOpen((prev) => !prev)}
      >
        <div className="section-trigger-main">
          <p className="section-kicker">Analysis Module</p>
          <h2>{title}</h2>
          <p>{subtitle}</p>
        </div>

        <div className="section-trigger-side">
          {meta.length > 0 ? (
            <div className="section-meta-list">
              {meta.map((item, index) => (
                <span key={`${item}-${index}`}>{item}</span>
              ))}
            </div>
          ) : null}
          <span className={`section-arrow ${open ? "open" : ""}`}>⌄</span>
        </div>
      </button>

      {open ? <div className="section-content reveal-soft">{children}</div> : null}
    </section>
  );
}

function IntroExperience({ user }) {
  const workflow = [
    {
      title: "Import",
      description:
        "Upload a YAML or JSON OpenAPI file and let the platform read its structure.",
    },
    {
      title: "Validate",
      description:
        "Run structural checks and best-practice rules, then convert the result into APRI scoring evidence.",
    },
    {
      title: "Decide",
      description:
        "Receive a clear ALLOW, NEEDS_FIX, or BLOCK decision based on governance rules.",
    },
    {
      title: "Publish",
      description:
        "Allow only authorized admins to publish approved APIs into the governance catalog.",
    },
  ];

  return (
    <>
      <section className="landing-hero scroll-reveal">
        <div className="landing-copy">
          <p className="eyebrow">API Governance Gateway for WSO2 API Manager</p>
          <h1>Validate OpenAPI quality before publication.</h1>
          <p>
            Analyze API specifications before they enter the WSO2 lifecycle using structural
            validation, best-practice checks, APRI scoring, AI-assisted review, duplicate
            detection, and controlled publication directly to WSO2 API Manager.
          </p>

          <div className="meta-line">
            <span>{user?.role === "admin" ? "Admin access" : "Developer access"}</span>
            <span>OpenAPI YAML / JSON</span>
            <span>WSO2 API Manager 4.3.0</span>
          </div>
        </div>

        <div className="landing-visual">
          <div className="visual-card main">
            <span>APRI</span>
            <strong>Score</strong>
          </div>
          <div className="visual-card top-left">Validation</div>
          <div className="visual-card top-right">AI Review</div>
          <div className="visual-card bottom-left">Governance Gate</div>
          <div className="visual-card bottom-right" style={{ color: "var(--wso2)", borderColor: "var(--wso2-border)", background: "var(--wso2-bg)" }}>
            WSO2 AM
          </div>
        </div>
      </section>

      <section className="workflow-strip scroll-reveal">
        {workflow.map((item) => (
          <article className="workflow-item" key={item.title}>
            <h3>{item.title}</h3>
            <p>{item.description}</p>
          </article>
        ))}
      </section>

      <section className="editorial-section scroll-reveal">
        <div className="editorial-head">
          <p className="eyebrow">How APRI Works</p>
          <h2>Scoring is based on measurable governance dimensions.</h2>
          <p>
            APRI evaluates documentation quality, operational clarity, response readiness,
            and REST governance quality. Structural errors block the score because the API
            cannot be reliably governed until the OpenAPI format is valid.
          </p>
        </div>

        <div className="dimension-lines">
          <div className="dimension-line">
            <strong>Documentation</strong>
            <span>Summaries, descriptions, response descriptions, and description adequacy.</span>
          </div>
          <div className="dimension-line">
            <strong>Operational Clarity</strong>
            <span>Operation IDs and tags that make APIs easier to understand and maintain.</span>
          </div>
          <div className="dimension-line">
            <strong>Response Readiness</strong>
            <span>Success responses, error responses, and request-body readiness.</span>
          </div>
          <div className="dimension-line">
            <strong>REST Governance</strong>
            <span>Resource-oriented paths, naming consistency, and method-path alignment.</span>
          </div>
        </div>
      </section>

      <section className="decision-section scroll-reveal">
        <div className="editorial-head">
          <p className="eyebrow">Governance Decisions</p>
          <h2>Every result ends with a clear publication decision.</h2>
        </div>

        <div className="decision-row">
          <div className="decision-line success">
            <strong>ALLOW</strong>
            <span>The API passed structural validation and has no blocking governance issue.</span>
          </div>
          <div className="decision-line warning">
            <strong>NEEDS_FIX</strong>
            <span>The API is structurally valid, but important quality issues remain.</span>
          </div>
          <div className="decision-line danger">
            <strong>BLOCK</strong>
            <span>The API has structural blockers.</span>
          </div>
        </div>
      </section>
    </>
  );
}

function ExecutiveSummary({ result, duplicateInfo, governanceDecisionText }) {
  const scoreTone = getScoreTone(result?.apri_score);

  return (
    <>
      <section className="apri-hero-section scroll-reveal" style={{ textAlign: "center", padding: "48px 24px 32px" }}>
        <div style={{ display: "flex", justifyContent: "center", alignItems: "baseline", gap: 20, flexWrap: "wrap" }}>
          <strong className={scoreTone} style={{ fontSize: 88, fontWeight: 800, lineHeight: 1, letterSpacing: "-2px" }}>
            {Number(result.apri_score || 0).toFixed(2)}
          </strong>
          <strong className={scoreTone} style={{ fontSize: 44, fontWeight: 700 }}>
            {result.grade}
          </strong>
        </div>
        <div style={{ marginTop: 20 }}>
          <span className={`status-chip ${getStatusTone(result.governance_decision)}`}>
            <span>Decision</span>
            <strong>{result.governance_decision}</strong>
          </span>
        </div>
      </section>

      <section className="executive-section scroll-reveal">
        <div className="executive-main">
          <p className="eyebrow">Executive View</p>
          <h2>Executive Summary</h2>
          <p>
            <strong>{result.filename}</strong> was analyzed successfully.{" "}
            {governanceDecisionText}
          </p>

          <div className="status-line">
            <StatusChip label="Status" value={result.status} />
            <StatusChip label="Grade" value={result.grade} />
            <StatusChip label="Decision" value={result.governance_decision} />
            <StatusChip label="Publishable" value={result.publishable ? "True" : "False"} />
            {duplicateInfo ? (
              <StatusChip label="Duplicates" value={duplicateInfo.status} />
            ) : null}
          </div>
        </div>

        <div className="executive-score">
          <span>APRI Score</span>
          <strong className={scoreTone}>{Number(result.apri_score || 0).toFixed(2)}</strong>
          <p>Overall governance readiness score.</p>
        </div>
      </section>

      <section className="kpi-grid scroll-reveal">
        <MetricCard
          label="Structure Errors"
          value={result.issue_summary?.structure_errors ?? 0}
          note="Hard blockers in the specification"
          tone={(result.issue_summary?.structure_errors ?? 0) > 0 ? "danger" : "success"}
        />
        <MetricCard
          label="Warnings"
          value={result.issue_summary?.best_practice_warnings ?? 0}
          note="Governance and quality findings"
          tone={(result.issue_summary?.best_practice_warnings ?? 0) > 0 ? "warning" : "success"}
        />
        <MetricCard
          label="Decision"
          value={result.governance_decision || result.status}
          note="Current governance position"
          tone={getStatusTone(result.governance_decision || result.status)}
        />
        <MetricCard
          label="Grade"
          value={result.grade}
          note="Human-readable quality level"
          tone={getStatusTone(result.grade)}
        />
      </section>
    </>
  );
}

function AdvancedDetails({ result }) {
  const ratios = result?.ratios || {};
  const categoryScores = result?.category_scores || {};
  const ratioKeys = Object.keys(ratios);

  return (
    <SectionBlock
      title="Advanced Details"
      subtitle="Scoring evidence, APRI categories, and compliance ratios."
      meta={[`${ratioKeys.length} ratios`, "APRI evidence"]}
    >
      <div className="section-grid">
        <div>
          <h3>Category Scores</h3>
          <div className="clean-list">
            {Object.entries(categoryScores).map(([key, value]) => (
              <div key={key} className="clean-list-row">
                <span>{labelizeKey(key)}</span>
                <strong className={getScoreTone(value)}>{Number(value).toFixed(0)}%</strong>
              </div>
            ))}
          </div>
        </div>

        <div>
          <h3>Compliance Ratios</h3>
          <div className="score-list">
            {ratioKeys.map((key) => (
              <ScoreBar key={key} label={labelizeKey(key)} value={ratios[key]} />
            ))}
          </div>
        </div>
      </div>
    </SectionBlock>
  );
}

function QualityBreakdown({ categoryScores, bestPracticeIssues, structureIssues }) {
  const [activeKey, setActiveKey] = useState("structure");

  const grouped = useMemo(() => {
    const result = {
      documentation: [],
      operational_clarity: [],
      response_readiness: [],
      rest_governance_quality: [],
      uncategorized: [],
    };

    for (const issue of bestPracticeIssues || []) {
      const ruleId = issue?.rule_id;
      let matched = false;

      for (const [groupKey, config] of Object.entries(ISSUE_GROUPS)) {
        if (config.rules.includes(ruleId)) {
          result[groupKey].push(issue);
          matched = true;
          break;
        }
      }

      if (!matched) result.uncategorized.push(issue);
    }

    return result;
  }, [bestPracticeIssues]);

  const dimensions = [
    {
      key: "structure",
      title: "Structure",
      value: (structureIssues?.length || 0) === 0 ? 100 : 0,
      issuesCount: structureIssues?.length || 0,
    },
    {
      key: "documentation",
      title: "Documentation",
      value: categoryScores?.documentation || 0,
      issuesCount: grouped.documentation.length,
    },
    {
      key: "operational_clarity",
      title: "Operational Clarity",
      value: categoryScores?.operational_clarity || 0,
      issuesCount: grouped.operational_clarity.length,
    },
    {
      key: "response_readiness",
      title: "Response Readiness",
      value: categoryScores?.response_readiness || 0,
      issuesCount: grouped.response_readiness.length,
    },
    {
      key: "rest_governance_quality",
      title: "REST Governance",
      value: categoryScores?.rest_governance_quality || 0,
      issuesCount: grouped.rest_governance_quality.length,
    },
  ];

  const activeIssues =
    activeKey === "structure" ? structureIssues || [] : grouped[activeKey] || [];

  return (
    <SectionBlock
      title="Quality Breakdown"
      subtitle="Dimension-level quality view with issue details for the selected part."
      meta={[`${dimensions.length} dimensions`, `${activeIssues.length} selected issues`]}
    >
      <div className="dimension-tabs">
        {dimensions.map((item) => (
          <button
            key={item.key}
            type="button"
            className={activeKey === item.key ? "dimension-tab active" : "dimension-tab"}
            onClick={() => setActiveKey(item.key)}
          >
            <span>{item.title}</span>
            <strong className={getScoreTone(item.value)}>
              {item.key === "structure"
                ? item.issuesCount > 0
                  ? "Block"
                  : "Pass"
                : `${Number(item.value).toFixed(0)}%`}
            </strong>
          </button>
        ))}
      </div>

      <div className="issue-list">
        {activeIssues.length > 0 ? (
          activeIssues.map((issue, index) => (
            <div className="issue-row" key={`${activeKey}-${index}`}>
              <strong>{issue.rule_id ? labelizeKey(issue.rule_id) : "Structure Issue"}</strong>
              <span>{issue.message}</span>
            </div>
          ))
        ) : (
          <div className="empty-line">No issues in this selected dimension.</div>
        )}
      </div>
    </SectionBlock>
  );
}

function IssueActionCenter({ structureIssues, bestPracticeIssues, duplicateInfo, aiReview = [] }) {
  const blockers = [];
  const improvements = [];

  for (const issue of structureIssues || []) {
    blockers.push({
      title: "Structure blocker",
      message: issue.message,
      tone: "danger",
    });
  }

  for (const issue of bestPracticeIssues || []) {
    const isMajor = [
      "missing_error_response",
      "missing_request_body",
      "discouraged_verb_in_path",
    ].includes(issue.rule_id);

    const target = isMajor ? blockers : improvements;

    const aiMatch = aiReview.find(
      (r) => r.endpoint && issue.message.toLowerCase().includes(r.endpoint.toLowerCase())
    );
    const aiHint = aiMatch ? (aiMatch.suggestion?.trim() || aiMatch.comment?.trim() || "") : "";

    target.push({
      title: labelizeKey(issue.rule_id || "best_practice"),
      message: issue.message,
      tone: isMajor ? "danger" : "warning",
      aiHint,
    });
  }

  if (duplicateInfo?.status === "warning") {
    const exactCount = duplicateInfo?.exact_duplicate_count || 0;
    improvements.push({
      title: exactCount > 0
        ? `Exact duplicate detected (${exactCount})`
        : "Potential overlap detected",
      message: duplicateInfo?.note ||
        "Similar endpoints exist in the catalog. Review the Duplicate Detection section before publishing.",
      tone: "warning",
    });
  }

  return (
    <SectionBlock
      title="Action Center"
      subtitle="What blocks publication and what still needs improvement."
      meta={[`${blockers.length} blockers`, `${improvements.length} improvements`]}
    >
      <div className="section-grid">
        <div>
          <h3>Major Issues</h3>
          <div className="issue-list">
            {blockers.length > 0 ? (
              blockers.map((item, index) => (
                <div className={`issue-row ${item.tone}`} key={`blocker-${index}`}>
                  <strong>{item.title}</strong>
                  <span>{item.message}</span>
                  {item.aiHint ? (
                    <span style={{ color: "var(--muted)", fontSize: 13, fontStyle: "italic" }}>
                      AI Suggestion: {item.aiHint}
                    </span>
                  ) : null}
                </div>
              ))
            ) : (
              <div className="empty-line">No blocking issues detected.</div>
            )}
          </div>
        </div>

        <div>
          <h3>Non-Blocking Improvements</h3>
          <div className="issue-list">
            {improvements.length > 0 ? (
              improvements.map((item, index) => (
                <div className={`issue-row ${item.tone}`} key={`improvement-${index}`}>
                  <strong>{item.title}</strong>
                  <span>{item.message}</span>
                  {item.aiHint ? (
                    <span style={{ color: "var(--muted)", fontSize: 13, fontStyle: "italic" }}>
                      AI Suggestion: {item.aiHint}
                    </span>
                  ) : null}
                </div>
              ))
            ) : (
              <div className="empty-line">No additional governance improvements were flagged.</div>
            )}
          </div>
        </div>
      </div>
    </SectionBlock>
  );
}

function AutoImprovementPreview({ simulation, currentScore, file, token }) {
  const [downloadLoading, setDownloadLoading] = useState(false);
  const [downloadError, setDownloadError] = useState("");

  if (!simulation) return null;

  const simulatedScore = simulation.simulated_score ?? currentScore ?? 0;
  const improvement = simulation.score_improvement ?? 0;
  const appliedChanges = Array.isArray(simulation.applied_changes)
    ? simulation.applied_changes
    : [];

  const handleDownload = async () => {
    if (!file) return;
    setDownloadLoading(true);
    setDownloadError("");
    try {
      const formData = new FormData();
      formData.append("file", file);
      const response = await fetch(`${API_BASE}/download-fixed`, {
        method: "POST",
        headers: { Authorization: `Bearer ${token}` },
        body: formData,
      });
      if (!response.ok) {
        const err = await response.json().catch(() => ({}));
        throw new Error(err.detail || "Download failed.");
      }
      const blob = await response.blob();
      const url = URL.createObjectURL(blob);
      const stem = file.name.replace(/\.[^.]+$/, "");
      const a = document.createElement("a");
      a.href = url;
      a.download = `${stem}_fixed.yaml`;
      a.click();
      URL.revokeObjectURL(url);
    } catch (err) {
      setDownloadError(err.message || "Download failed.");
    } finally {
      setDownloadLoading(false);
    }
  };

  const showDownload = simulation.enabled === true && appliedChanges.length > 0;

  return (
    <SectionBlock
      title="AI Auto-Improvement Preview"
      subtitle="Safe AI changes simulated on an internal copy to show measurable improvement."
      meta={[
        `${improvement >= 0 ? "+" : ""}${Number(improvement || 0).toFixed(2)} APRI`,
        `${appliedChanges.length} auto-fixes`,
      ]}
    >
      <div className="before-after-clean">
        <div>
          <span>Current APRI</span>
          <strong>{Number(currentScore || 0).toFixed(2)}</strong>
        </div>
        <div>
          <span>Simulated APRI</span>
          <strong>{Number(simulatedScore || 0).toFixed(2)}</strong>
        </div>
      </div>

      {simulation.message ? <div className="info-banner">{simulation.message}</div> : null}
      {simulation.error ? <div className="error-banner">{simulation.error}</div> : null}

      <div className="issue-list">
        {appliedChanges.length > 0 ? (
          appliedChanges.map((change, index) => (
            <div className="issue-row success" key={`${change.path}-${change.field}-${index}`}>
              <strong>
                {labelizeKey(change.field)} · {change.method} {change.path}
              </strong>
              <span>
                New value:{" "}
                {Array.isArray(change.new_value)
                  ? change.new_value.join(", ")
                  : String(change.new_value)}
              </span>
            </div>
          ))
        ) : (
          <div className="empty-line">No safe changes were applied in simulation.</div>
        )}
      </div>

      {showDownload ? (
        <div style={{ marginTop: 24, borderTop: "1px solid var(--border)", paddingTop: 20, display: "flex", flexDirection: "column", gap: 10, alignItems: "flex-start" }}>
          <button className="secondary-btn" onClick={handleDownload} disabled={downloadLoading}>
            {downloadLoading ? "Generating…" : "Download Fixed Spec"}
          </button>
          <p style={{ margin: 0, fontSize: 13, color: "var(--muted)" }}>
            This file reflects only safe documentation fixes. Its APRI score should match the simulated score above.
          </p>
          {downloadError ? <div className="error-banner">{downloadError}</div> : null}
        </div>
      ) : null}
    </SectionBlock>
  );
}

function PrototypePipelineSimulation({ prototype }) {
  if (!prototype) return null;

  const summary = prototype.summary || {};
  const stages = Array.isArray(prototype.pipeline_stages)
    ? prototype.pipeline_stages
    : [];
  const endpointResults = Array.isArray(prototype.endpoint_results)
    ? prototype.endpoint_results
    : [];

  return (
    <SectionBlock
      title="Prototype / Pipeline Simulation"
      subtitle="Non-blocking readiness analysis for mock testing before publication."
      meta={[
        prototype.status || "unknown",
        `${Number(prototype.readiness_score || 0).toFixed(2)} readiness`,
      ]}
    >
      <div className="kpi-grid compact">
        <MetricCard
          label="Readiness Score"
          value={Number(prototype.readiness_score || 0).toFixed(2)}
          note="Prototype testability estimate"
          tone={getScoreTone(prototype.readiness_score)}
        />
        <MetricCard label="Test Ready" value={summary.test_ready || 0} note="Ready endpoints" tone="success" />
        <MetricCard label="Partial" value={summary.partial || 0} note="Needs improvement" tone="warning" />
        <MetricCard label="Not Ready" value={summary.not_ready || 0} note="Missing testing information" tone={(summary.not_ready || 0) > 0 ? "danger" : "success"} />
      </div>

      {prototype.message ? <div className="info-banner">{prototype.message}</div> : null}

      <div className="section-grid">
        <div>
          <h3>Pipeline Stages</h3>
          <div className="clean-list">
            {stages.map((stage, index) => (
              <div className="clean-list-row stacked" key={`${stage.stage}-${index}`}>
                <strong>{stage.stage}</strong>
                <span>{stage.description}</span>
              </div>
            ))}
          </div>
        </div>

        <div>
          <h3>Generated Mock Scenarios</h3>
          <div className="clean-list">
            {endpointResults.length > 0 ? (
              endpointResults.slice(0, 4).map((item, index) => (
                <div className="clean-list-row stacked" key={`${item.endpoint}-${index}`}>
                  <strong>{item.endpoint}</strong>
                  <span>{item.mock_scenario?.description || "No scenario generated."}</span>
                </div>
              ))
            ) : (
              <div className="empty-line">No endpoint scenarios were generated.</div>
            )}
          </div>
        </div>
      </div>
    </SectionBlock>
  );
}

function ManualActionsRequired({ reviews, simulation, appliedChanges = [], bestPracticeIssues = [] }) {
  const excluded = Array.isArray(simulation?.excluded_review_types)
    ? simulation.excluded_review_types
    : [];

  const remaining = Array.isArray(simulation?.remaining_issues)
    ? simulation.remaining_issues
    : [];

  const coveredEndpoints = new Set(
    Array.isArray(appliedChanges)
      ? appliedChanges.map((c) => `${String(c.method).toUpperCase()} ${c.path}`)
      : []
  );

  const manualDesignItems = Array.isArray(reviews)
    ? reviews.filter(
        (item) => item.status === "needs_improvement" && !coveredEndpoints.has(item.endpoint)
      )
    : [];

  return (
    <SectionBlock
      title="Manual Actions Required"
      subtitle="Higher-level design decisions that should be reviewed manually."
      meta={[`${manualDesignItems.length} uncovered`, `${remaining.length} remaining issues`]}
    >
      {excluded.length > 0 ? (
        <div className="meta-line standalone">
          {excluded.map((type) => (
            <span key={type}>{type.replaceAll("_", " ")}</span>
          ))}
        </div>
      ) : null}

      <div className="section-grid">
        <div>
          <h3>AI Flagged — Not Auto-Fixed</h3>
          <div className="issue-list">
            {manualDesignItems.length > 0 ? (
              manualDesignItems.map((item, index) => (
                <div className="issue-row warning" key={`${item.endpoint}-${index}`}>
                  <strong>{item.endpoint || "Unknown endpoint"}</strong>
                  {Array.isArray(item.issues) && item.issues.length > 0 ? (
                    <ul style={{ margin: "4px 0 0 16px", padding: 0, fontSize: 13 }}>
                      {item.issues.map((iss, i) => <li key={i}>{iss}</li>)}
                    </ul>
                  ) : null}
                  {(item.suggestion?.trim() || item.comment?.trim()) ? (
                    <span style={{ color: "var(--muted)", fontSize: 13, fontStyle: "italic" }}>
                      Suggestion: {item.suggestion?.trim() || item.comment?.trim()}
                    </span>
                  ) : null}
                </div>
              ))
            ) : (
              <div className="empty-line">No uncovered AI findings — the simulation handled all flagged endpoints.</div>
            )}
          </div>
        </div>

        <div>
          <h3>Remaining Governance Issues</h3>
          <div className="issue-list">
            {remaining.length > 0 ? (
              remaining.map((issue, index) => (
                <div className="issue-row warning" key={`remaining-${index}`}>
                  <strong>
                    {typeof issue === "string"
                      ? "Remaining issue"
                      : issue.rule_id
                      ? labelizeKey(issue.rule_id)
                      : "Remaining issue"}
                  </strong>
                  <span>{typeof issue === "string" ? issue : issue.message}</span>
                </div>
              ))
            ) : (
              <div className="empty-line">No remaining governance issues were reported.</div>
            )}
          </div>
        </div>
      </div>
    </SectionBlock>
  );
}

function DuplicateSection({ duplicates }) {
  if (!duplicates) return null;

  const matches = Array.isArray(duplicates.matches) ? duplicates.matches : [];
  const exactCount = duplicates.exact_duplicate_count || 0;
  const isClean = duplicates.status === "clean";

  function matchTypeTone(type) {
    if (type === "exact_duplicate") return "danger";
    if (type === "strong_overlap") return "warning";
    return "warning";
  }

  function matchTypeLabel(type) {
    if (type === "exact_duplicate") return "Exact duplicate";
    if (type === "strong_overlap") return "Strong overlap";
    return "Potential overlap";
  }

  function aiDecisionLabel(decision) {
    if (!decision || decision === "unavailable" || decision === "unknown") return null;
    return decision.charAt(0).toUpperCase() + decision.slice(1);
  }

  return (
    <SectionBlock
      title="Duplicate Detection"
      subtitle="Multi-signal similarity checks against APIs already saved in the governance catalog."
      meta={[duplicates.status || "clean", `${duplicates.count || 0} matches`]}
    >
      {/* Summary row */}
      <div className="duplicate-clean">
        <div>
          <span>Duplicate Status</span>
          <strong className={isClean ? "success" : "warning"}>
            {duplicates.status || "clean"}
          </strong>
          <p>
            {duplicates.count || 0} match{duplicates.count === 1 ? "" : "es"} found
            {exactCount > 0 ? ` (${exactCount} exact)` : ""}.
          </p>
        </div>
        <div>
          {isClean ? (
            <div className="info-banner">
              No duplicate or overlapping endpoints were detected in the catalog.
            </div>
          ) : (
            <div className="info-banner">
              {duplicates.note ||
                "These matches are informational. As admin, you can still publish after reviewing."}
            </div>
          )}
        </div>
      </div>

      {/* Match list */}
      {matches.length > 0 && (
        <div className="issue-list" style={{ marginTop: 24 }}>
          {matches.map((match, index) => {
            const signals = match.signal_scores || {};
            const aiDecision = aiDecisionLabel(match.ai_review?.ai_duplicate_decision);
            const aiConfidence = match.ai_review?.confidence;

            return (
              <div
                className={`issue-row ${matchTypeTone(match.type)}`}
                key={`${match.type}-${index}`}
                style={{ display: "flex", flexDirection: "column", gap: 8, padding: "16px 0" }}
              >
                {/* Header row */}
                <div style={{ display: "flex", alignItems: "center", gap: 12, flexWrap: "wrap" }}>
                  <strong style={{ fontSize: 17 }}>
                    {match.uploaded_endpoint?.method} {match.uploaded_endpoint?.path}
                  </strong>
                  <span className={`badge ${matchTypeTone(match.type)}`}>
                    {matchTypeLabel(match.type)}
                  </span>
                  {aiDecision && (
                    <span className="badge neutral">
                      AI: {aiDecision}
                      {aiConfidence != null ? ` (${aiConfidence}%)` : ""}
                    </span>
                  )}
                </div>

                {/* Matched API info */}
                <div style={{ fontSize: 14, color: "var(--text)" }}>
                  Matched:{" "}
                  <strong>
                    {match.matched_endpoint?.method} {match.matched_endpoint?.path}
                  </strong>
                  {" in "}
                  <strong>
                    {match.matched_api?.title || match.matched_api?.filename || "Unknown API"}
                  </strong>
                  {match.matched_api?.version ? ` v${match.matched_api.version}` : ""}
                </div>

                {/* Score breakdown */}
                <div style={{ display: "flex", flexWrap: "wrap", gap: 10, fontSize: 13, color: "var(--muted)" }}>
                  <span>Combined: <strong style={{ color: "var(--ink)" }}>{match.combined_score ?? "—"}%</strong></span>
                  {signals.path_similarity != null && (
                    <span>Path: <strong style={{ color: "var(--ink)" }}>{signals.path_similarity}%</strong></span>
                  )}
                  {signals.summary_similarity != null && (
                    <span>Summary: <strong style={{ color: "var(--ink)" }}>{signals.summary_similarity}%</strong></span>
                  )}
                  {signals.tags_similarity != null && (
                    <span>Tags: <strong style={{ color: "var(--ink)" }}>{signals.tags_similarity}%</strong></span>
                  )}
                  {match.method_match != null && (
                    <span>Method: <strong style={{ color: match.method_match ? "var(--success)" : "var(--danger)" }}>
                      {match.method_match ? "same" : "different"}
                    </strong></span>
                  )}
                </div>

                {/* AI reasoning */}
                {match.ai_review?.reason && (
                  <div style={{ fontSize: 13, color: "var(--text)", fontStyle: "italic" }}>
                    "{match.ai_review.reason}"
                  </div>
                )}

                {/* AI recommendation */}
                {match.ai_review?.recommendation && (
                  <div style={{ fontSize: 13, color: "var(--blue-dark)", fontWeight: 600 }}>
                    → {match.ai_review.recommendation}
                  </div>
                )}
              </div>
            );
          })}
        </div>
      )}
    </SectionBlock>
  );
}

function PublicationGate({ onPublish, publishLoading, file, publishMessage, publishError, result, user, onReset }) {
  return (
    <SectionBlock
      title="Publication Gate"
      subtitle="Publish approved APIs to the governance catalog and WSO2 API Manager."
      meta={[result?.governance_decision || "N/A", result?.publishable ? "Publishable" : "Needs Fix"]}
    >
      {/* WSO2 destination indicator */}
      <div className="wso2-publish-target">
        <img src="/images/wso2-logo.png" alt="WSO2" width="48" height="48" style={{ objectFit: "contain", flexShrink: 0 }} />
        <div className="wso2-publish-target-body">
          <strong>Publish destination: WSO2 API Manager</strong>
          <p>
            Clicking Publish will save this API to the local governance catalog <em>and</em> import it
            into WSO2 API Manager (localhost:9443) where it will be available in the Developer Portal.
          </p>
        </div>
      </div>

      <div className="publish-row">
        <div>
          <h3>Publish to WSO2 API Manager</h3>
          <p>
            Only APIs with a governance decision of <strong>ALLOW</strong> can be published.
          </p>
        </div>

        <button
          className="secondary-btn"
          onClick={onPublish}
          disabled={publishLoading || !file || result?.governance_decision !== "ALLOW"}
          style={{ background: "var(--wso2)", boxShadow: "0 14px 30px rgba(255,120,0,0.22)" }}
        >
          {publishLoading ? "Publishing…" : "Publish to WSO2"}
        </button>
      </div>

      {result?.governance_decision !== "ALLOW" ? (
        <div className="info-banner">This API must reach an ALLOW decision before it can be published.</div>
      ) : null}
      {publishMessage && !publishError ? (
        <div style={{ background: "var(--success-bg, #f0fdf4)", border: "1.5px solid var(--success-border, #bbf7d0)", borderRadius: 12, padding: "24px 28px", marginTop: 16, display: "flex", flexDirection: "column", gap: 12 }}>
          <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
            <span style={{ color: "var(--success, #22c55e)", fontSize: 22, fontWeight: 700 }}>✓</span>
            <p style={{ margin: 0, fontWeight: 600 }}>{publishMessage}</p>
          </div>
          {publishMessage.includes("ID: ") ? (
            <a href="https://localhost:9443/devportal/apis" target="_blank" rel="noopener noreferrer" style={{ color: "var(--blue, #2563eb)", textDecoration: "underline" }}>
              View in WSO2 Developer Portal →
            </a>
          ) : null}
          <button className="ghost-btn" onClick={onReset}>Analyze another API</button>
        </div>
      ) : null}
      {publishError ? <div className="error-banner">{publishError}</div> : null}
    </SectionBlock>
  );
}

function FAQSection() {
  const questions = [
    {
      q: "What is APRI?",
      a: "APRI is the API Publication Readiness Indicator. It summarizes OpenAPI quality using documentation, operational clarity, response readiness, and REST governance quality.",
    },
    {
      q: "Why can an API have a good score but still not be publishable?",
      a: "Publication depends on governance rules, not score alone. Major issues, structure errors, or exact duplicates can block publication.",
    },
    {
      q: "Does AI automatically modify my file?",
      a: "No. AI suggestions are simulated on an internal copy only. The original uploaded file is not modified.",
    },
    {
      q: "What does prototype simulation mean?",
      a: "It estimates whether the OpenAPI definition is ready for mock testing by checking responses, request bodies, schemas, and endpoint readiness.",
    },
    {
      q: "Who can publish APIs?",
      a: "Any authenticated user can publish APIs that pass the governance gate.",
    },
    {
      q: "What happens when an API is published?",
      a: "The API is saved to the local governance catalog and simultaneously pushed to WSO2 API Manager via its Publisher REST API. It then appears in the WSO2 Developer Portal as a Published API. The WSO2 API ID is stored in the catalog for traceability.",
    },
    {
      q: "What if the WSO2 push fails?",
      a: "The local governance catalog entry is always saved first. If the WSO2 push fails, the API remains in the catalog marked as 'Local only' and the error reason is shown in the publish result. The admin can retry by re-publishing.",
    },
  ];

  return (
    <section className="faq-section scroll-reveal">
      <div className="editorial-head">
        <p className="eyebrow">FAQ</p>
        <h2>Frequently Asked Questions</h2>
        <p>Short explanations to help users understand the platform behavior.</p>
      </div>

      <div className="faq-list">
        {questions.map((item, index) => (
          <details className="faq-item" key={index}>
            <summary>{item.q}</summary>
            <p>{item.a}</p>
          </details>
        ))}
      </div>
    </section>
  );
}

function AnalysisProgress() {
  const messages = [
    "Validating structure…",
    "Running APRI scoring…",
    "AI governance review in progress…",
    "Checking for duplicate APIs…",
    "Running prototype simulation…",
  ];
  const [index, setIndex] = useState(0);

  useEffect(() => {
    const id = setInterval(() => setIndex((i) => (i + 1) % messages.length), 2000);
    return () => clearInterval(id);
  }, []);

  return <p className="analysis-progress-msg" style={{ textAlign: "center", color: "var(--muted)", fontSize: 14, marginTop: 10 }}>{messages[index]}</p>;
}

export default function AnalyzerPage({ token, user }) {
  const [file, setFile] = useState(null);
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [publishLoading, setPublishLoading] = useState(false);
  const [error, setError] = useState("");
  const [publishMessage, setPublishMessage] = useState("");
  const [publishError, setPublishError] = useState("");
  const [isDragging, setIsDragging] = useState(false);
  const duplicateInfo = result?.duplicates;
  const broadReview = Array.isArray(result?.ai_review?.broad_review)
    ? result.ai_review.broad_review
    : [];

  const governanceDecisionText = useMemo(() => {
    if (!result) return "";
    if (result.status === "Rejected") {
      return "This specification has structural errors and cannot proceed to governance approval.";
    }
    if (result.status === "Needs Improvement") {
      return "The API is structurally valid, but governance issues still need to be resolved.";
    }
    return "This API passed validation and is positioned well for publication review.";
  }, [result, duplicateInfo]);

  const handleAnalyze = async () => {
    if (!file) {
      setError("Please choose an OpenAPI YAML or JSON file first.");
      return;
    }

    setLoading(true);
    setError("");
    setResult(null);
    setPublishMessage("");
    setPublishError("");

    const formData = new FormData();
    formData.append("file", file);

    try {
      const response = await fetch(`${API_BASE}/upload-openapi`, {
        method: "POST",
        headers: {
          Authorization: `Bearer ${token}`,
        },
        body: formData,
      });

      const data = await response.json();

      if (!response.ok) {
        throw new Error(
          typeof data.detail === "string"
            ? data.detail
            : data.detail?.message || "Analysis failed."
        );
      }

      setResult(data);
    } catch (err) {
      setError(err.message || "Something went wrong during analysis.");
    } finally {
      setLoading(false);
    }
  };

  const handleReset = () => {
    setFile(null);
    setResult(null);
    setPublishMessage("");
    setPublishError("");
  };

  const handlePublish = async () => {
    if (!file) {
      setPublishError("No file selected for publishing.");
      return;
    }

    setPublishLoading(true);
    setPublishMessage("");
    setPublishError("");

    const formData = new FormData();
    formData.append("file", file);

    try {
      const response = await fetch(`${API_BASE}/publish-openapi`, {
        method: "POST",
        headers: {
          Authorization: `Bearer ${token}`,
        },
        body: formData,
      });

      const data = await response.json();

      if (!response.ok) {
        const detail = data.detail;
        if (typeof detail === "string") {
          throw new Error(detail);
        }
        throw new Error(detail?.message || "Publishing was blocked.");
      }

      const wso2Msg = data.wso2?.success
        ? ` Also pushed to WSO2 API Manager (ID: ${data.wso2.wso2_api_id}).`
        : data.wso2?.error
        ? ` Note: WSO2 push failed — ${data.wso2.error}`
        : "";
      setPublishMessage((data.message || "API published successfully.") + wso2Msg);
    } catch (err) {
      setPublishError(err.message || "Publishing failed.");
    } finally {
      setPublishLoading(false);
    }
  };

  return (
    <div className="page-stack">
      <IntroExperience user={user} />

      <section className="analyzer-workspace scroll-reveal">
        <div className="workspace-copy">
          <p className="eyebrow">Analyzer Workspace</p>
          <h2>Run a governance review</h2>
          <p>
            Upload an OpenAPI specification to validate structure, assess governance quality,
            preview safe AI improvements, review manual design issues, and decide whether the
            API is ready to publish.
          </p>
        </div>

        <div className="upload-panel">
          <div>
            <h3>Upload specification file</h3>
            <p>
              Accepted formats: <strong>.yaml</strong>, <strong>.yml</strong>,{" "}
              <strong>.json</strong> · Max 5 MB
            </p>
          </div>

          <div className="upload-actions">
            <label
              className={`upload-trigger-label${file ? " has-file" : ""}${isDragging ? " drag-over" : ""}`}
              onDragOver={(e) => { e.preventDefault(); setIsDragging(true); }}
              onDragLeave={() => setIsDragging(false)}
              onDrop={(e) => {
                e.preventDefault();
                setIsDragging(false);
                const dropped = e.dataTransfer.files[0];
                if (dropped && /\.(yaml|yml|json)$/i.test(dropped.name)) setFile(dropped);
              }}
            >
              <svg width="16" height="16" viewBox="0 0 20 20" fill="currentColor">
                <path d="M16.88 9.94A5 5 0 1 0 9 4.06V4a1 1 0 1 0-2 0v.06A5 5 0 1 0 3.12 9.94 3.5 3.5 0 0 0 4 17h12a3.5 3.5 0 0 0 .88-6.88zM11 11v3a1 1 0 1 1-2 0v-3H7.41l2.29-2.29a1 1 0 0 1 1.42 0L13.6 11H11z"/>
              </svg>
              {file ? file.name : "Choose file…"}
              <input
                type="file"
                accept=".yaml,.yml,.json"
                onChange={(e) => setFile(e.target.files[0] || null)}
              />
            </label>
            <button className="primary-btn" onClick={handleAnalyze} disabled={loading || !file}>
              {loading ? "Analyzing…" : "Analyze API"}
            </button>
          </div>
        </div>

        {loading ? (
          <>
            <div className="loader-line" />
            <AnalysisProgress />
          </>
        ) : null}
        {error ? <div className="error-banner">{error}</div> : null}
      </section>

      {result ? (
        <>
          <ExecutiveSummary
            result={result}
            duplicateInfo={duplicateInfo}
            governanceDecisionText={governanceDecisionText}
          />

          <AdvancedDetails result={result} />

          <QualityBreakdown
            categoryScores={result.category_scores || {}}
            bestPracticeIssues={result.best_practice_issues || []}
            structureIssues={result.structure_issues || []}
          />

          <IssueActionCenter
            structureIssues={result.structure_issues || []}
            bestPracticeIssues={result.best_practice_issues || []}
            duplicateInfo={duplicateInfo}
            aiReview={result.ai_review?.broad_review || []}
          />

          <AutoImprovementPreview
            simulation={result.simulation}
            currentScore={result.apri_score}
            file={file}
            token={token}
          />

          <PrototypePipelineSimulation prototype={result.prototype_testing} />

          <ManualActionsRequired
            reviews={broadReview}
            simulation={result.simulation}
            appliedChanges={result.simulation?.applied_changes || []}
            bestPracticeIssues={result.best_practice_issues || []}
          />

          <DuplicateSection duplicates={duplicateInfo} />

          <PublicationGate
            onPublish={handlePublish}
            publishLoading={publishLoading}
            file={file}
            publishMessage={publishMessage}
            publishError={publishError}
            result={result}
            user={user}
            onReset={handleReset}
          />
        </>
      ) : (
        <FAQSection />
      )}
    </div>
  );
}