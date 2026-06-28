import { useQuery } from "@tanstack/react-query";
import { Link } from "react-router-dom";

import { EmptyState } from "../../components/feedback/EmptyState";
import { ErrorState } from "../../components/feedback/ErrorState";
import { Spinner } from "../../components/feedback/Loading";
import { Seo } from "../../components/Seo";
import { buttonClassName } from "../../components/ui/buttonStyles";
import { Card } from "../../components/ui/Card";
import { getAdminDashboard } from "./api";
import { AdminIssueTable } from "./AdminIssueTable";
import { OperationsAgentPanel } from "./OperationsAgentPanel";

const metricLabels = {
  total_reports: "Total reports",
  high_severity: "High severity",
  verified: "Community verified",
  pending: "Pending action",
  resolved: "Resolved",
} as const;

export function AdminDashboardPage() {
  const dashboard = useQuery({
    queryKey: ["admin-dashboard"],
    queryFn: ({ signal }) => getAdminDashboard(signal),
  });

  if (dashboard.isPending) {
    return (
      <div className="admin-page">
        <Seo title="Admin dashboard" />
        <Spinner label="Loading dashboard…" />
      </div>
    );
  }
  if (dashboard.isError) {
    return (
      <div className="admin-page">
        <Seo title="Admin dashboard unavailable" />
        <ErrorState
          description={dashboard.error.message}
          onRetry={() => void dashboard.refetch()}
          title="The dashboard could not be loaded"
        />
      </div>
    );
  }

  const data = dashboard.data;
  return (
    <section className="admin-page">
      <Seo
        description="Protected CivicPulse AI administrator dashboard for issue metrics and prioritization."
        title="Admin dashboard"
      />
      <header className="admin-page-heading">
        <div>
          <p className="eyebrow">Issue management</p>
          <h1>Administrator dashboard</h1>
          <p>Monitor civic reports and prioritize the issues requiring attention.</p>
        </div>
        <Link className={buttonClassName("primary")} to="/admin/issues">
          Manage all issues
        </Link>
      </header>

      <div className="admin-metric-grid">
        {Object.entries(data.metrics).map(([key, value]) => (
          <Card className="admin-metric" key={key}>
            <span>{metricLabels[key as keyof typeof metricLabels]}</span>
            <strong>{value}</strong>
          </Card>
        ))}
      </div>

      <OperationsAgentPanel />

      <Card padding="large">
        <div className="admin-section-heading">
          <div>
            <p className="eyebrow">Community missions</p>
            <h2>Civic Mission Console</h2>
            <p className="admin-muted">
              Generate AI draft missions, remove duplicates, create manual missions,
              refine with AI, and publish approved missions from a dedicated workspace.
            </p>
          </div>
          <Link className={buttonClassName("secondary")} to="/admin/missions">
            Open mission console
          </Link>
        </div>
      </Card>

      <div className="admin-dashboard-grid">
        <Card padding="large">
          <p className="eyebrow">Distribution</p>
          <h2>Reports by category</h2>
          <dl className="category-breakdown">
            {data.category_breakdown.map((item) => (
              <div key={item.category}>
                <dt>{item.category.replaceAll("_", " ")}</dt>
                <dd>{item.count}</dd>
              </div>
            ))}
          </dl>
        </Card>
        <Card padding="large">
          <p className="eyebrow">Priority queue</p>
          <h2>High-impact open issues</h2>
          {data.priority_issues.length ? (
            <ul className="admin-priority-list">
              {data.priority_issues.map((issue) => (
                <li key={issue.id}>
                  <Link to={`/admin/issues/${issue.id}`}>{issue.title}</Link>
                  <span>{issue.severity} · {issue.verification_count} confirmations</span>
                </li>
              ))}
            </ul>
          ) : (
            <p className="admin-muted">No high-priority open issues.</p>
          )}
        </Card>
      </div>

      <Card padding="large">
        <div className="admin-section-heading">
          <div>
            <p className="eyebrow">Latest reports</p>
            <h2>Recently submitted issues</h2>
          </div>
          <Link to="/admin/issues">View all</Link>
        </div>
        {data.latest_reports.length ? (
          <AdminIssueTable issues={data.latest_reports} label="Latest reports" />
        ) : (
          <EmptyState
            description="Citizen reports will appear here after publication."
            title="No reports yet"
          />
        )}
      </Card>
    </section>
  );
}
