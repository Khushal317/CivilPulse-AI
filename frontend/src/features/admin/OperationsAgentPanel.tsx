import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState, type ReactNode } from "react";
import { Link } from "react-router-dom";

import { useNotifications } from "../../app/notificationContext";
import { EmptyState } from "../../components/feedback/EmptyState";
import { ErrorState } from "../../components/feedback/ErrorState";
import { Spinner } from "../../components/feedback/Loading";
import { Badge, SeverityBadge } from "../../components/ui/Badge";
import { Button } from "../../components/ui/Button";
import { Card } from "../../components/ui/Card";
import { analyzeOperationsReport, getLatestOperationsReport } from "./api";
import type {
  OperationsAreaHotspot,
  OperationsDepartmentPriority,
  OperationsDuplicateCluster,
  OperationsEscalationMessage,
  OperationsPredictedRisk,
  OperationsReport,
  OperationsRiskLevel,
  OperationsUrgentIssue,
} from "./types";
import { useAdminSession } from "./useAdminSession";

const ACCOUNTABILITY_NOTE =
  "AI recommendations do not change issue status or contact departments. An administrator must review and act.";

const riskTone: Record<OperationsRiskLevel, "neutral" | "warning" | "danger"> = {
  low: "neutral",
  medium: "warning",
  high: "danger",
  critical: "danger",
};

function formatCategory(category: string) {
  return category.replaceAll("_", " ");
}

function formatDate(value: string) {
  return new Intl.DateTimeFormat(undefined, {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(new Date(value));
}

function EmptyOperationsSection({ message }: { message: string }) {
  return <p className="admin-muted operations-empty-section">{message}</p>;
}

function ReportSection({
  children,
  eyebrow,
  title,
}: {
  children: ReactNode;
  eyebrow: string;
  title: string;
}) {
  return (
    <Card as="section" className="operations-section" padding="large">
      <p className="eyebrow">{eyebrow}</p>
      <h3>{title}</h3>
      {children}
    </Card>
  );
}

function UrgentIssues({ issues }: { issues: OperationsUrgentIssue[] }) {
  if (!issues.length) {
    return <EmptyOperationsSection message="No urgent issue recommendations in this report." />;
  }
  return (
    <div className="operations-card-list">
      {issues.map((issue) => (
        <article className="operations-list-card" key={issue.issue_id}>
          <div className="operations-list-card-heading">
            <div>
              <span>{issue.public_reference}</span>
              <h4>{issue.title}</h4>
            </div>
            <SeverityBadge severity={issue.severity} />
          </div>
          <p>{issue.priority_reason}</p>
          <dl className="operations-mini-list">
            <div>
              <dt>Location</dt>
              <dd>{issue.location}</dd>
            </div>
            <div>
              <dt>Department</dt>
              <dd>{issue.department}</dd>
            </div>
            <div>
              <dt>Time window</dt>
              <dd>{issue.suggested_time_window}</dd>
            </div>
          </dl>
          <p className="operations-action">{issue.recommended_action}</p>
          <Link to={`/admin/issues/${issue.issue_id}`}>Open issue</Link>
        </article>
      ))}
    </div>
  );
}

function DuplicateClusters({ clusters }: { clusters: OperationsDuplicateCluster[] }) {
  if (!clusters.length) {
    return <EmptyOperationsSection message="No possible duplicate clusters found." />;
  }
  return (
    <div className="operations-card-list">
      {clusters.map((cluster) => (
        <article className="operations-list-card" key={cluster.cluster_title}>
          <h4>{cluster.cluster_title}</h4>
          <p>{cluster.reason}</p>
          <ul className="operations-link-list">
            {cluster.issues.map((issue) => (
              <li key={issue.issue_id}>
                <Link to={`/admin/issues/${issue.issue_id}`}>
                  {issue.public_reference} · {issue.title}
                </Link>
              </li>
            ))}
          </ul>
          <p className="operations-action">{cluster.recommended_action}</p>
        </article>
      ))}
    </div>
  );
}

function AreaHotspots({ hotspots }: { hotspots: OperationsAreaHotspot[] }) {
  if (!hotspots.length) {
    return <EmptyOperationsSection message="No area hotspots found." />;
  }
  return (
    <div className="operations-card-list operations-card-list-compact">
      {hotspots.map((hotspot) => (
        <article className="operations-list-card" key={hotspot.area}>
          <div className="operations-list-card-heading">
            <h4>{hotspot.area}</h4>
            <Badge tone={riskTone[hotspot.risk_level]}>{hotspot.risk_level} risk</Badge>
          </div>
          <p>{hotspot.insight}</p>
          <p className="admin-muted">
            {hotspot.issue_count} active issue{hotspot.issue_count === 1 ? "" : "s"} ·{" "}
            {hotspot.main_categories.map(formatCategory).join(", ")}
          </p>
        </article>
      ))}
    </div>
  );
}

function DepartmentPriorities({
  priorities,
}: {
  priorities: OperationsDepartmentPriority[];
}) {
  if (!priorities.length) {
    return <EmptyOperationsSection message="No department workload recommendations." />;
  }
  return (
    <div className="operations-department-grid">
      {priorities.map((priority) => (
        <article className="operations-department-card" key={priority.department}>
          <span>{priority.department}</span>
          <strong>{priority.open_issues}</strong>
          <p>
            {priority.high_priority_count} high-priority issue
            {priority.high_priority_count === 1 ? "" : "s"}
          </p>
          <p>{priority.recommended_focus}</p>
        </article>
      ))}
    </div>
  );
}

function EscalationMessages({
  messages,
}: {
  messages: OperationsEscalationMessage[];
}) {
  const { notify } = useNotifications();
  const [copiedId, setCopiedId] = useState<string | null>(null);

  async function copyMessage(message: OperationsEscalationMessage) {
    if (!navigator.clipboard?.writeText) {
      notify({
        title: "Copy unavailable",
        message: "Your browser blocked clipboard access. Select and copy the draft manually.",
        tone: "error",
      });
      return;
    }
    try {
      await navigator.clipboard.writeText(message.message);
      setCopiedId(message.issue_id);
      notify({
        title: "Message copied",
        message: `${message.public_reference} escalation draft copied.`,
        tone: "success",
      });
    } catch {
      notify({
        title: "Copy failed",
        message: "Your browser could not copy the draft. Select and copy it manually.",
        tone: "error",
      });
    }
  }

  if (!messages.length) {
    return <EmptyOperationsSection message="No escalation drafts in this report." />;
  }
  return (
    <div className="operations-card-list">
      {messages.map((message) => (
        <article className="operations-list-card" key={message.issue_id}>
          <div className="operations-list-card-heading">
            <div>
              <span>{message.department}</span>
              <h4>{message.issue_title}</h4>
            </div>
            <Link to={`/admin/issues/${message.issue_id}`}>{message.public_reference}</Link>
          </div>
          <blockquote>{message.message}</blockquote>
          <Button
            onClick={() => void copyMessage(message)}
            size="small"
            variant="secondary"
          >
            {copiedId === message.issue_id ? "Copied" : "Copy message"}
          </Button>
        </article>
      ))}
    </div>
  );
}

function PredictedRisks({ risks }: { risks: OperationsPredictedRisk[] }) {
  if (!risks.length) {
    return <EmptyOperationsSection message="No predicted risk warnings in this report." />;
  }
  return (
    <div className="operations-card-list">
      {risks.map((risk) => (
        <article className="operations-list-card operations-risk-card" key={risk.issue_id}>
          <div className="operations-list-card-heading">
            <div>
              <span>{risk.public_reference}</span>
              <h4>{risk.issue_title}</h4>
            </div>
            <Badge tone={riskTone[risk.risk_level]}>{risk.risk_level}</Badge>
          </div>
          <p>{risk.risk}</p>
          <p className="operations-action">{risk.preventive_action}</p>
          <Link to={`/admin/issues/${risk.issue_id}`}>Open issue</Link>
        </article>
      ))}
    </div>
  );
}

function OperationsReportView({ report }: { report: OperationsReport }) {
  return (
    <div className="operations-report">
      <Card className="operations-summary-card" padding="large">
        <div>
          <p className="eyebrow">Latest operations report</p>
          <h3>Executive summary</h3>
          <p>{report.executive_summary}</p>
        </div>
        <dl className="operations-report-meta">
          <div>
            <dt>Generated</dt>
            <dd>{formatDate(report.generated_at)}</dd>
          </div>
          <div>
            <dt>Issues analyzed</dt>
            <dd>{report.total_issues_analyzed}</dd>
          </div>
          <div>
            <dt>Model</dt>
            <dd>{report.model_used}</dd>
          </div>
        </dl>
      </Card>

      <p className="operations-accountability-note">{ACCOUNTABILITY_NOTE}</p>

      <div className="operations-report-grid">
        <ReportSection eyebrow="Priority" title="Top urgent issues">
          <UrgentIssues issues={report.urgent_issues} />
        </ReportSection>
        <ReportSection eyebrow="Patterns" title="Possible duplicate clusters">
          <DuplicateClusters clusters={report.duplicate_clusters} />
        </ReportSection>
        <ReportSection eyebrow="Geography" title="Area hotspots">
          <AreaHotspots hotspots={report.area_hotspots} />
        </ReportSection>
        <ReportSection eyebrow="Workload" title="Department priorities">
          <DepartmentPriorities priorities={report.department_priorities} />
        </ReportSection>
        <ReportSection eyebrow="Drafts" title="Escalation messages">
          <EscalationMessages messages={report.escalation_messages} />
        </ReportSection>
        <ReportSection eyebrow="Risk" title="Predicted risks">
          <PredictedRisks risks={report.predicted_risks} />
        </ReportSection>
      </div>
    </div>
  );
}

export function OperationsAgentPanel() {
  const session = useAdminSession();
  const queryClient = useQueryClient();
  const { notify } = useNotifications();
  const latestReport = useQuery({
    queryKey: ["admin-operations-report"],
    queryFn: ({ signal }) => getLatestOperationsReport(signal),
  });
  const analyze = useMutation({
    mutationFn: () => analyzeOperationsReport(session.data?.csrf_token ?? ""),
    onSuccess: (report) => {
      queryClient.setQueryData(["admin-operations-report"], report);
      notify({
        title: "Operations report ready",
        message: "The Civic Operations Agent finished analyzing active issues.",
        tone: "success",
      });
    },
  });
  const report = analyze.data ?? latestReport.data ?? null;

  return (
    <Card as="section" className="operations-agent-panel" padding="large">
      <div className="operations-agent-heading">
        <div>
          <p className="eyebrow">Civic Operations Agent</p>
          <h2>Analyze active city issues</h2>
          <p>
            Generate an advisory operations report from active reports, community signals,
            department workload, and unresolved risk patterns.
          </p>
        </div>
        <Button
          disabled={!session.data?.csrf_token}
          isLoading={analyze.isPending}
          onClick={() => analyze.mutate()}
        >
          Analyze City Issues
        </Button>
      </div>

      {analyze.isPending && (
        <div className="operations-inline-state">
          <Spinner label="The Civic Operations Agent is analyzing active issues…" />
        </div>
      )}

      {analyze.isError && (
        <ErrorState
          description={analyze.error.message}
          onRetry={() => analyze.mutate()}
          title="Operations analysis failed"
        />
      )}

      {latestReport.isPending && !report && (
        <div className="operations-inline-state">
          <Spinner label="Loading latest operations report…" />
        </div>
      )}

      {latestReport.isError && !report && (
        <ErrorState
          description={latestReport.error.message}
          onRetry={() => void latestReport.refetch()}
          title="Latest operations report could not be loaded"
        />
      )}

      {!latestReport.isPending && !latestReport.isError && !report && (
        <EmptyState
          description="Run the Civic Operations Agent to create the first saved operations report."
          title="No operations report yet"
        />
      )}

      {report && <OperationsReportView report={report} />}
    </Card>
  );
}
