import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { type FormEvent, useState } from "react";
import { Link, useParams } from "react-router-dom";

import { useNotifications } from "../../app/notificationContext";
import { ErrorState } from "../../components/feedback/ErrorState";
import { Spinner } from "../../components/feedback/Loading";
import { Seo } from "../../components/Seo";
import { CategoryBadge, SeverityBadge, StatusBadge } from "../../components/ui/Badge";
import { Button } from "../../components/ui/Button";
import { Card } from "../../components/ui/Card";
import { CivicStatCard } from "../../components/ui/CivicStatCard";
import { Dialog } from "../../components/ui/Dialog";
import { SelectField, TextAreaField } from "../../components/ui/FormField";
import { GeminiLabel } from "../../components/ui/GeminiLabel";
import { Timeline } from "../../components/ui/Timeline";
import type { IssueStatus } from "../../types/domain";
import { publicIssueImageUrl } from "../issues/api";
import { getAdminIssue, updateAdminIssueStatus } from "./api";
import type { AdminStatusUpdate } from "./types";
import { useAdminSession } from "./useAdminSession";

const transitions: Record<IssueStatus, IssueStatus[]> = {
  reported: ["community_verified", "escalated", "in_progress", "resolved", "rejected"],
  community_verified: ["escalated", "in_progress", "resolved", "rejected"],
  escalated: ["in_progress", "resolved", "rejected"],
  in_progress: ["escalated", "resolved", "rejected"],
  resolved: ["in_progress"],
  rejected: ["reported"],
  duplicate: [],
};

const labels: Record<IssueStatus, string> = {
  reported: "Reported",
  community_verified: "Community verified",
  escalated: "Escalated",
  in_progress: "In progress",
  resolved: "Resolved",
  rejected: "Rejected",
  duplicate: "Duplicate",
};

const operationStatusLabels: Record<IssueStatus, string> = {
  reported: "New report",
  community_verified: "Verified signal",
  escalated: "Escalated case",
  in_progress: "Action underway",
  resolved: "Resolved case",
  rejected: "Rejected case",
  duplicate: "Duplicate case",
};

const dateFormatter = new Intl.DateTimeFormat(undefined, {
  dateStyle: "medium",
  timeStyle: "short",
});

function isGeminiModel(model: string) {
  return model.toLowerCase().includes("gemini");
}

export function AdminIssueDetailPage() {
  const { issueId } = useParams();
  const session = useAdminSession();
  const queryClient = useQueryClient();
  const { notify } = useNotifications();
  const [toStatus, setToStatus] = useState<IssueStatus | "">("");
  const [note, setNote] = useState("");
  const [rejectionReason, setRejectionReason] = useState("");
  const [pendingUpdate, setPendingUpdate] = useState<AdminStatusUpdate | null>(null);
  const issue = useQuery({
    enabled: Boolean(issueId),
    queryKey: ["admin-issue", issueId],
    queryFn: ({ signal }) => getAdminIssue(issueId!, signal),
  });
  const updateStatus = useMutation({
    mutationFn: (update: AdminStatusUpdate) =>
      updateAdminIssueStatus(issueId!, update, session.data!.csrf_token),
    onSuccess: (updated) => {
      queryClient.setQueryData(["admin-issue", issueId], updated);
      void queryClient.invalidateQueries({ queryKey: ["admin-dashboard"] });
      void queryClient.invalidateQueries({ queryKey: ["admin-issues"] });
      void queryClient.invalidateQueries({ queryKey: ["public-issue", issueId] });
      void queryClient.invalidateQueries({ queryKey: ["public-issues"] });
      setToStatus("");
      setNote("");
      setRejectionReason("");
      setPendingUpdate(null);
      notify({
        message: "The public status and timeline have been updated.",
        title: "Issue status updated",
        tone: "success",
      });
    },
  });

  if (issue.isPending || session.isPending) {
    return (
      <div className="admin-page">
        <Seo title="Admin issue detail" />
        <Spinner label="Loading issue record…" />
      </div>
    );
  }
  if (issue.isError || session.isError || !issueId) {
    return (
      <div className="admin-page">
        <Seo title="Admin issue unavailable" />
        <ErrorState
          description={issue.error?.message ?? session.error?.message}
          title="The administrator issue record is unavailable"
        />
      </div>
    );
  }

  const data = issue.data;
  const submitUpdate = (update: AdminStatusUpdate) => {
    if (update.to_status === "resolved" || update.to_status === "rejected") {
      setPendingUpdate(update);
    } else {
      updateStatus.mutate(update);
    }
  };

  function submit(event: FormEvent) {
    event.preventDefault();
    if (!toStatus) return;
    submitUpdate({
      to_status: toStatus,
      note: toStatus !== "rejected" ? note.trim() || undefined : undefined,
      rejection_reason:
        toStatus === "rejected" ? rejectionReason.trim() || undefined : undefined,
    });
  }

  return (
    <section className="admin-page">
      <Seo
        description={`Protected administrator record for ${data.title}.`}
        title={`Admin · ${data.public_reference}`}
      />
      <Link className="back-link" to="/admin/issues">← Back to issue queue</Link>
      <header className="admin-page-heading">
        <div>
          <p className="issue-reference">{data.public_reference}</p>
          <h1>{data.title}</h1>
          <p>{data.location}{data.landmark ? ` · ${data.landmark}` : ""}</p>
        </div>
        <div className="issue-card-badges">
          <CategoryBadge category={data.category} />
          <SeverityBadge severity={data.severity} />
          <StatusBadge status={data.status} />
        </div>
      </header>

      <div className="admin-queue-summary-grid" aria-label="Issue operations snapshot">
        <CivicStatCard
          description="Current public lifecycle state."
          eyebrow="Status"
          icon="●"
          tone={data.status === "resolved" ? "success" : data.status === "rejected" ? "danger" : "brand"}
          value={operationStatusLabels[data.status]}
        />
        <CivicStatCard
          description="Resident confirmations visible to admins."
          eyebrow="Community Signals"
          icon="👥"
          tone={data.verification_count > 0 ? "success" : "neutral"}
          value={data.verification_count}
        />
        <CivicStatCard
          description="Valid transitions available from this state."
          eyebrow="Next Transitions"
          icon="↪"
          tone="ai"
          value={transitions[data.status].length}
        />
      </div>

      <div className="admin-detail-grid">
        <main className="admin-detail-main">
          <Card className="issue-hero-image" padding="none">
            <img alt={`Reported civic issue: ${data.title}`} src={publicIssueImageUrl(data.image_url)} />
          </Card>
          <Card padding="large">
            <p className="eyebrow">Report content</p>
            <h2>Citizen observation</h2>
            <p className="detail-copy">{data.original_description}</p>
            <div className="detail-section-heading admin-ai-heading">
              <h3>AI complaint summary</h3>
              <GeminiLabel>
                {isGeminiModel(data.ai_model) ? "Generated by Gemini" : "AI-assisted summary"}
              </GeminiLabel>
            </div>
            <p className="detail-copy">{data.ai_summary}</p>
            <dl className="detail-facts">
              <div><dt>Department</dt><dd>{data.suggested_department}</dd></div>
              <div><dt>Urgency</dt><dd>{data.urgency_level}</dd></div>
              <div><dt>Urgency reason</dt><dd>{data.urgency_reason}</dd></div>
              <div><dt>Safety risk</dt><dd>{data.safety_risk}</dd></div>
              <div><dt>Suggested next action</dt><dd>{data.suggested_next_action}</dd></div>
            </dl>
          </Card>
          <Card padding="large">
            <p className="eyebrow">Public history</p>
            <h2>Status timeline and notes</h2>
            <Timeline
              items={data.updates.map((update, index) => ({
                id: update.id,
                title: labels[update.to_status],
                description: update.note,
                meta: dateFormatter.format(new Date(update.created_at)),
                state: index === data.updates.length - 1 ? "current" : "complete",
              }))}
              label="Administrator issue status history"
            />
          </Card>
        </main>

        <aside className="admin-detail-sidebar">
          <Card padding="large">
            <p className="eyebrow">Private reporter details</p>
            <h2>Authorized contact access</h2>
            <dl className="private-details">
              <div><dt>Name</dt><dd>{data.citizen_name || "Not provided"}</dd></div>
              <div><dt>Contact</dt><dd>{data.citizen_contact || "Not provided"}</dd></div>
            </dl>
            <p className="admin-muted">These fields never appear in public APIs.</p>
          </Card>

          <Card padding="large">
            <p className="eyebrow">Lifecycle control</p>
            <h2>Update public status</h2>
            {transitions[data.status].length ? (
              <form className="form-stack" onSubmit={submit}>
                <SelectField
                  label="New status"
                  onChange={(event) => setToStatus(event.target.value as IssueStatus)}
                  required
                  value={toStatus}
                >
                  <option value="">Choose a valid transition</option>
                  {transitions[data.status].map((status) => (
                    <option key={status} value={status}>{labels[status]}</option>
                  ))}
                </SelectField>
                {toStatus === "rejected" ? (
                  <TextAreaField
                    label="Rejection reason"
                    onChange={(event) => setRejectionReason(event.target.value)}
                    required
                    rows={4}
                    value={rejectionReason}
                  />
                ) : (
                  <TextAreaField
                    label="Public update note"
                    onChange={(event) => setNote(event.target.value)}
                    optional
                    rows={4}
                    value={note}
                  />
                )}
                {updateStatus.isError && (
                  <p className="community-error" role="alert">{updateStatus.error.message}</p>
                )}
                <Button disabled={!toStatus} isLoading={updateStatus.isPending} type="submit">
                  Update status
                </Button>
              </form>
            ) : (
              <p className="admin-muted">No transitions are available from this status.</p>
            )}
          </Card>

          <Card padding="large">
            <p className="eyebrow">Analysis audit</p>
            <dl className="private-details">
              <div><dt>AI model</dt><dd>{data.ai_model}</dd></div>
              <div><dt>Prompt version</dt><dd>{data.prompt_version}</dd></div>
              <div><dt>Image type</dt><dd>{data.image_mime}</dd></div>
            </dl>
          </Card>
        </aside>
      </div>

      <Dialog
        confirmLabel={pendingUpdate?.to_status === "rejected" ? "Reject issue" : "Mark resolved"}
        isOpen={pendingUpdate !== null}
        onClose={() => setPendingUpdate(null)}
        onConfirm={() => pendingUpdate && updateStatus.mutate(pendingUpdate)}
        title={
          pendingUpdate?.to_status === "rejected"
            ? "Reject this public issue?"
            : "Mark this issue as resolved?"
        }
        variant="danger"
      >
        This changes the public status and adds a permanent timeline entry.
      </Dialog>
    </section>
  );
}
