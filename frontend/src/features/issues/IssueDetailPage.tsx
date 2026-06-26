import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Link, useParams } from "react-router-dom";

import { useNotifications } from "../../app/notificationContext";
import { ErrorState } from "../../components/feedback/ErrorState";
import { Spinner } from "../../components/feedback/Loading";
import { Seo } from "../../components/Seo";
import { CategoryBadge, SeverityBadge, StatusBadge } from "../../components/ui/Badge";
import { Button } from "../../components/ui/Button";
import { buttonClassName } from "../../components/ui/buttonStyles";
import { Card } from "../../components/ui/Card";
import { Timeline } from "../../components/ui/Timeline";
import type { CommunityActionType, IssueStatus } from "../../types/domain";
import { getPublicIssue, publicIssueImageUrl, submitCommunityAction } from "./api";
import type { PublicIssueDetail } from "./types";

const dateFormatter = new Intl.DateTimeFormat(undefined, {
  dateStyle: "medium",
  timeStyle: "short",
});

const statusLabels: Record<IssueStatus, string> = {
  reported: "Reported",
  community_verified: "Community verified",
  escalated: "Escalated",
  in_progress: "In progress",
  resolved: "Resolved",
  rejected: "Rejected",
};

const actionContent: Record<
  CommunityActionType,
  { description: string; label: string }
> = {
  saw_this_too: {
    label: "I saw this too",
    description: "Confirm that this issue is present at the reported location.",
  },
  still_unresolved: {
    label: "Still unresolved",
    description: "Share that the problem remains visible or disruptive.",
  },
  fixed: {
    label: "This is fixed",
    description: "Advisory signal only. An administrator must confirm resolution.",
  },
  incorrect: {
    label: "Duplicate / incorrect",
    description: "Flag a possible duplicate, wrong location, or inaccurate report.",
  },
};

function actionCount(issue: PublicIssueDetail, actionType: CommunityActionType): number {
  return issue.community_counts[actionType];
}

export function IssueDetailPage() {
  const { issueId } = useParams();
  const queryClient = useQueryClient();
  const { notify } = useNotifications();
  const issueQuery = useQuery({
    enabled: Boolean(issueId),
    queryKey: ["public-issue", issueId],
    queryFn: ({ signal }) => getPublicIssue(issueId!, signal),
    retry: false,
  });
  const action = useMutation({
    mutationFn: (actionType: CommunityActionType) =>
      submitCommunityAction(issueId!, actionType),
    onSuccess: (result) => {
      queryClient.setQueryData<PublicIssueDetail>(
        ["public-issue", issueId],
        (current) =>
          current
            ? {
                ...current,
                status: result.issue_status,
                verification_count: result.community_counts.saw_this_too,
                community_counts: result.community_counts,
                viewer_actions: result.viewer_actions,
              }
            : current,
      );
      void queryClient.invalidateQueries({ queryKey: ["public-issue", issueId] });
      void queryClient.invalidateQueries({ queryKey: ["public-issues"] });
      notify({
        title: result.accepted ? "Community signal recorded" : "Already recorded",
        message: result.accepted
          ? "Thank you. The public counts have been updated."
          : "This browser already submitted that signal for this issue.",
        tone: result.accepted ? "success" : "info",
      });
    },
  });

  if (!issueId) {
    return (
      <section className="page-section">
        <Seo title="Issue unavailable" />
        <div className="container narrow">
          <ErrorState title="The issue link is incomplete" />
        </div>
      </section>
    );
  }

  if (issueQuery.isPending) {
    return (
      <section className="page-section">
        <Seo title="Issue details" />
        <div className="container narrow">
          <Spinner label="Loading public issue…" />
        </div>
      </section>
    );
  }

  if (issueQuery.isError) {
    return (
      <section className="page-section">
        <Seo
          description="This CivicPulse AI issue could not be loaded."
          title="Issue unavailable"
        />
        <div className="container narrow">
          <ErrorState
            description={issueQuery.error.message}
            onRetry={() => void issueQuery.refetch()}
            title="The public issue could not be loaded"
          />
          <div className="state-followup">
            <Link className={buttonClassName("secondary")} to="/issues">
              Return to tracker
            </Link>
          </div>
        </div>
      </section>
    );
  }

  const issue = issueQuery.data;
  const actionsUnavailable = issue.status === "rejected";
  const timelineItems = issue.updates.map((update, index) => ({
    id: update.id,
    title: statusLabels[update.to_status],
    description: update.note,
    meta: dateFormatter.format(new Date(update.created_at)),
    state: index === issue.updates.length - 1 ? ("current" as const) : ("complete" as const),
  }));

  return (
    <section className="page-section issue-detail-page">
      <Seo
        description={`${issue.title} in ${issue.location}. View status, community signals, and timeline updates.`}
        title={issue.title}
      />
      <div className="container issue-detail-layout">
        <Link className="back-link" to="/issues">
          ← Back to public tracker
        </Link>

        <header className="issue-detail-heading">
          <div>
            <p className="issue-reference">{issue.public_reference}</p>
            <h1>{issue.title}</h1>
            <p className="page-copy">
              {issue.location}
              {issue.landmark ? ` · ${issue.landmark}` : ""}
            </p>
          </div>
          <div className="issue-card-badges">
            <CategoryBadge category={issue.category} />
            <SeverityBadge severity={issue.severity} />
            <StatusBadge status={issue.status} />
          </div>
        </header>

        <div className="issue-detail-grid">
          <main className="issue-detail-main">
            <Card className="issue-hero-image" padding="none">
              <img
                alt={`Reported civic issue: ${issue.title}`}
                src={publicIssueImageUrl(issue.image_url)}
              />
            </Card>

            <Card padding="large">
              <p className="eyebrow">Citizen report</p>
              <h2>What was originally observed</h2>
              <p className="detail-copy">{issue.original_description}</p>
            </Card>

            <Card padding="large">
              <p className="eyebrow">AI-structured complaint</p>
              <h2>Public complaint summary</h2>
              <p className="detail-copy">{issue.ai_summary}</p>
              <dl className="detail-facts">
                <div>
                  <dt>Suggested department</dt>
                  <dd>{issue.suggested_department}</dd>
                </div>
                <div>
                  <dt>Urgency</dt>
                  <dd>{issue.urgency_level}</dd>
                </div>
                <div>
                  <dt>Urgency reason</dt>
                  <dd>{issue.urgency_reason}</dd>
                </div>
                <div>
                  <dt>Safety risk</dt>
                  <dd>{issue.safety_risk}</dd>
                </div>
                <div>
                  <dt>Suggested next action</dt>
                  <dd>{issue.suggested_next_action}</dd>
                </div>
              </dl>
            </Card>

            <Card padding="large">
              <p className="eyebrow">Public progress</p>
              <h2>Status timeline</h2>
              {timelineItems.length > 0 ? (
                <Timeline items={timelineItems} label="Public issue status history" />
              ) : (
                <p className="detail-copy">No public status updates are available yet.</p>
              )}
            </Card>
          </main>

          <aside className="issue-detail-sidebar">
            <Card padding="large">
              <p className="eyebrow">Community signals</p>
              <h2>What are residents seeing?</h2>
              <p className="community-guidance">
                One signal of each type is counted per browser. Signals help verification but do
                not replace official civic decisions.
              </p>
              <div className="community-actions">
                {(Object.keys(actionContent) as CommunityActionType[]).map((actionType) => {
                  const submitted = issue.viewer_actions.includes(actionType);
                  const content = actionContent[actionType];
                  return (
                    <div className="community-action" key={actionType}>
                      <div>
                        <strong>
                          {content.label} <span>{actionCount(issue, actionType)}</span>
                        </strong>
                        <p>{content.description}</p>
                      </div>
                      <Button
                        disabled={actionsUnavailable || submitted}
                        isLoading={action.isPending && action.variables === actionType}
                        onClick={() => action.mutate(actionType)}
                        size="small"
                        variant={submitted ? "ghost" : "secondary"}
                      >
                        {submitted ? "Submitted" : "Add signal"}
                      </Button>
                    </div>
                  );
                })}
              </div>
              {actionsUnavailable && (
                <p className="community-unavailable" role="status">
                  Community signals are unavailable because this issue was rejected.
                </p>
              )}
              {action.isError && (
                <p className="community-error" role="alert">
                  {action.error.message}
                </p>
              )}
            </Card>

            <Card padding="large">
              <p className="eyebrow">Transparency note</p>
              <h2>How to read this page</h2>
              <p className="community-guidance">
                AI organizes the citizen submission. Community signals show local observations.
                Only authorized administrators can make official status decisions.
              </p>
            </Card>
          </aside>
        </div>
      </div>
    </section>
  );
}
