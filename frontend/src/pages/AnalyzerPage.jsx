import { useMemo, useState } from "react";

const API_BASE = "http://127.0.0.1:8000";

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
          <p className="eyebrow">AI-Driven API Governance Workbench</p>
          <h1>Validate OpenAPI quality before publication.</h1>
          <p>
            Analyze API specifications before they enter the lifecycle using structural
            validation, best-practice checks, APRI scoring, AI-assisted review, duplicate
            detection, prototype readiness simulation, and controlled publication.
          </p>

          <div className="meta-line">
            <span>{user?.role === "admin" ? "Admin access" : "Developer access"}</span>
            <span>OpenAPI YAML / JSON</span>
            <span>Pre-publication governance</span>
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
          <div className="visual-card bottom-right">Catalog</div>
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
            <span>The API has structural blockers or exact duplicate conflicts.</span>
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

function IssueActionCenter({ structureIssues, bestPracticeIssues, duplicateInfo }) {
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

    target.push({
      title: labelizeKey(issue.rule_id || "best_practice"),
      message: issue.message,
      tone: isMajor ? "danger" : "warning",
    });
  }

  if (duplicateInfo?.status === "blocked") {
    blockers.push({
      title: "Exact duplicate detected",
      message: "This API matches an existing catalog entry and is blocked from publication.",
      tone: "danger",
    });
  } else if (duplicateInfo?.status === "warning") {
    improvements.push({
      title: "Potential overlap detected",
      message: "This API is similar to an existing catalog entry and needs review.",
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
          <h3>Blocking Issues</h3>
          <div className="issue-list">
            {blockers.length > 0 ? (
              blockers.map((item, index) => (
                <div className={`issue-row ${item.tone}`} key={`blocker-${index}`}>
                  <strong>{item.title}</strong>
                  <span>{item.message}</span>
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

function AutoImprovementPreview({ simulation, currentScore }) {
  if (!simulation) return null;

  const simulatedScore = simulation.simulated_score ?? currentScore ?? 0;
  const improvement = simulation.score_improvement ?? 0;
  const appliedChanges = Array.isArray(simulation.applied_changes)
    ? simulation.applied_changes
    : [];

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

function ManualActionsRequired({ reviews, simulation }) {
  const excluded = Array.isArray(simulation?.excluded_review_types)
    ? simulation.excluded_review_types
    : [];

  const remaining = Array.isArray(simulation?.remaining_issues)
    ? simulation.remaining_issues
    : [];

  const manualDesignItems = [];

  if (Array.isArray(reviews)) {
    for (const item of reviews) {
      const issues = Array.isArray(item?.issues) ? item.issues : [];
      const issueText = issues.join(" ").toLowerCase();

      const isDesignLevel =
        issueText.includes("verb") ||
        issueText.includes("rest") ||
        issueText.includes("method") ||
        issueText.includes("naming") ||
        issueText.includes("endpoint") ||
        issueText.includes("action");

      if (isDesignLevel) manualDesignItems.push(item);
    }
  }

  return (
    <SectionBlock
      title="Manual Actions Required"
      subtitle="Higher-level design decisions that should be reviewed manually."
      meta={[`${manualDesignItems.length} design items`, `${remaining.length} remaining issues`]}
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
          <h3>Design-Level Review</h3>
          <div className="issue-list">
            {manualDesignItems.length > 0 ? (
              manualDesignItems.map((item, index) => (
                <div className="issue-row warning" key={`${item.endpoint}-${index}`}>
                  <strong>{item.endpoint || "Unknown endpoint"}</strong>
                  <span>{item.suggestion || item.comment || "Manual review required."}</span>
                </div>
              ))
            ) : (
              <div className="empty-line">No design-level manual review items were extracted.</div>
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

  return (
    <SectionBlock
      title="Duplicate Detection"
      subtitle="Similarity checks against APIs already saved in the governance catalog."
      meta={[duplicates.status || "clean", `${duplicates.count || 0} matches`]}
    >
      <div className="duplicate-clean">
        <div>
          <span>Duplicate Status</span>
          <strong>{duplicates.status || "clean"}</strong>
          <p>
            {duplicates.count || 0} potential match{duplicates.count === 1 ? "" : "es"} found.
          </p>
        </div>

        <div className="issue-list">
          {Array.isArray(duplicates.matches) && duplicates.matches.length > 0 ? (
            duplicates.matches.map((match, index) => (
              <div className="issue-row warning" key={`${match.type}-${index}`}>
                <strong>
                  {match.uploaded_endpoint?.method} {match.uploaded_endpoint?.path}
                </strong>
                <span>
                  Similarity: {match.similarity}% · Matched API:{" "}
                  {match.matched_api?.title || match.matched_api?.filename || "Unknown"}
                </span>
              </div>
            ))
          ) : (
            <div className="empty-line">No duplicate matches detected.</div>
          )}
        </div>
      </div>
    </SectionBlock>
  );
}

function PublicationGate({ onPublish, publishLoading, file, publishMessage, publishError, result, user }) {
  return (
    <SectionBlock
      title="Publication Gate"
      subtitle="Final publication control for the governance catalog."
      meta={[result?.governance_decision || "N/A", result?.publishable ? "Publishable" : "Needs Fix"]}
    >
      <div className="publish-row">
        <div>
          <h3>Publish to Governance Catalog</h3>
          <p>
            Publish the API into the governance catalog only when the final result allows it.
          </p>
        </div>

        <button
          className="secondary-btn"
          onClick={onPublish}
          disabled={publishLoading || !file || user?.role !== "admin"}
        >
          {publishLoading ? "Publishing..." : "Publish API"}
        </button>
      </div>

      {user?.role !== "admin" ? (
        <div className="info-banner">
          Publishing is restricted to governance admins. Developers can analyze APIs and review
          improvement actions, but cannot publish to the catalog.
        </div>
      ) : null}

      {publishMessage ? <div className="success-banner">{publishMessage}</div> : null}
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
      a: "Only users with the admin role can publish APIs to the governance catalog.",
    },
  ];

  return (
    <section className="faq-section scroll-reveal">
      <div className="editorial-head">
        <p className="eyebrow">FAQ</p>
        <h2>Common governance questions</h2>
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

export default function AnalyzerPage({ token, user }) {
  const [file, setFile] = useState(null);
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [publishLoading, setPublishLoading] = useState(false);
  const [error, setError] = useState("");
  const [publishMessage, setPublishMessage] = useState("");
  const [publishError, setPublishError] = useState("");

  const duplicateInfo = result?.duplicates;
  const broadReview = Array.isArray(result?.ai_review?.broad_review)
    ? result.ai_review.broad_review
    : [];

  const governanceDecisionText = useMemo(() => {
    if (!result) return "";
    if (result.status === "Rejected") {
      return "This specification has structural errors and cannot proceed to governance approval.";
    }
    if (duplicateInfo?.status === "blocked") {
      return "This API is blocked by exact duplication against an existing catalog entry.";
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

      setPublishMessage(data.message || "API published successfully.");
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
              <strong>.json</strong>
            </p>
            <span>{file ? `Selected: ${file.name}` : "No file selected yet"}</span>
          </div>

          <div className="upload-actions">
            <input
              className="file-input"
              type="file"
              accept=".yaml,.yml,.json"
              onChange={(e) => setFile(e.target.files[0] || null)}
            />
            <button className="primary-btn" onClick={handleAnalyze} disabled={loading}>
              {loading ? "Analyzing..." : "Analyze API"}
            </button>
          </div>
        </div>

        {loading ? <div className="loader-line" /> : null}
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
          />

          <AutoImprovementPreview
            simulation={result.simulation}
            currentScore={result.apri_score}
          />

          <PrototypePipelineSimulation prototype={result.prototype_testing} />

          <ManualActionsRequired
            reviews={broadReview}
            simulation={result.simulation}
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
          />

          <FAQSection />
        </>
      ) : (
        <FAQSection />
      )}
    </div>
  );
}