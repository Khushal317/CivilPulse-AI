import { useQuery } from "@tanstack/react-query";
import { Link } from "react-router-dom";

import { EmptyState } from "../../components/feedback/EmptyState";
import { ErrorState } from "../../components/feedback/ErrorState";
import { Spinner } from "../../components/feedback/Loading";
import { Seo } from "../../components/Seo";
import { buttonClassName } from "../../components/ui/buttonStyles";
import { Card } from "../../components/ui/Card";
import { CivicStatCard } from "../../components/ui/CivicStatCard";
import { TrendPill } from "../../components/ui/TrendPill";
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

const metricIcons: Record<keyof typeof metricLabels, string> = {
  total_reports: "📥",
  high_severity: "⚠",
  verified: "✓",
  pending: "⏱",
  resolved: "↗",
};

const metricTones: Record<
  keyof typeof metricLabels,
  "brand" | "danger" | "neutral" | "success" | "warning"
> = {
  total_reports: "brand",
  high_severity: "danger",
  verified: "success",
  pending: "warning",
  resolved: "neutral",
};

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
          <p className="eyebrow">Civic Operations</p>
          <h1>Administrator dashboard</h1>
          <p>
            Monitor civic signals, prioritize unresolved risks, and coordinate AI-assisted
            operations from one protected control room.
          </p>
        </div>
        <Link className={buttonClassName("primary")} to="/admin/issues">
          Manage all issues
        </Link>
      </header>

      <div className="admin-metric-grid">
        {Object.entries(data.metrics).map(([key, value]) => (
          <CivicStatCard
            className="admin-metric"
            description={
              key === "pending"
                ? "Reports still needing admin movement."
                : key === "high_severity"
                  ? "High-severity reports in the queue."
                  : undefined
            }
            eyebrow={metricLabels[key as keyof typeof metricLabels]}
            icon={metricIcons[key as keyof typeof metricLabels]}
            key={key}
            tone={metricTones[key as keyof typeof metricLabels]}
            value={value}
          />
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
            <div className="admin-signal-row" aria-label="Dashboard signals">
              <TrendPill direction={data.latest_reports.length ? "up" : "flat"}>
                {data.latest_reports.length} latest
              </TrendPill>
              <TrendPill direction={data.priority_issues.length ? "up" : "flat"}>
                {data.priority_issues.length} priority
              </TrendPill>
            </div>
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
