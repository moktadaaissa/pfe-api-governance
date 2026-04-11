const mockApis = [
  { name: "user_management_api.yaml", status: "Valid", apri: 100, grade: "Excellent" },
  { name: "account_management_api.yaml", status: "Needs Improvement", apri: 91.31, grade: "Excellent" },
  { name: "loan_application_api.yaml", status: "Needs Improvement", apri: 85, grade: "Good" },
  { name: "notification_service_api.yaml", status: "Needs Improvement", apri: 75, grade: "Acceptable" },
  { name: "broken_missing_openapi.yaml", status: "Rejected", apri: 0, grade: "Rejected" },
];

function OverviewCard({ title, value }) {
  return (
    <div className="card stat-card">
      <h3>{title}</h3>
      <p>{value}</p>
    </div>
  );
}

export default function AdminPage() {
  const total = mockApis.length;
  const valid = mockApis.filter((api) => api.status === "Valid").length;
  const rejected = mockApis.filter((api) => api.status === "Rejected").length;
  const needsImprovement = mockApis.filter((api) => api.status === "Needs Improvement").length;
  const avgApri =
    (mockApis.reduce((sum, api) => sum + api.apri, 0) / total).toFixed(2);

  return (
    <div>
      <div className="card hero-card">
        <div>
          <h1>Admin Dashboard</h1>
          <p>
            Governance overview of analyzed APIs, readiness results, and publication quality.
          </p>
        </div>
      </div>

      <div className="stats-grid">
        <OverviewCard title="Total APIs" value={total} />
        <OverviewCard title="Valid APIs" value={valid} />
        <OverviewCard title="Needs Improvement" value={needsImprovement} />
        <OverviewCard title="Rejected APIs" value={rejected} />
        <OverviewCard title="Average APRI" value={avgApri} />
      </div>

      <div className="card">
        <h2>Analyzed APIs Overview</h2>
        <div className="table-wrapper">
          <table>
            <thead>
              <tr>
                <th>API File</th>
                <th>Status</th>
                <th>APRI</th>
                <th>Grade</th>
              </tr>
            </thead>
            <tbody>
              {mockApis.map((api, index) => (
                <tr key={index}>
                  <td>{api.name}</td>
                  <td>{api.status}</td>
                  <td>{api.apri}</td>
                  <td>{api.grade}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      <div className="card">
        <h2>Platform Vision</h2>
        <ul className="issue-list">
          <li>
            <strong>Analyzer page:</strong> used by developers to upload an API and receive validation and APRI feedback.
          </li>
          <li>
            <strong>Admin dashboard:</strong> used by governance teams to monitor API quality and publication readiness.
          </li>
          <li>
            <strong>Future extension:</strong> duplicate detection, approval workflow, catalog history, and publication decisions.
          </li>
        </ul>
      </div>
    </div>
  );
}