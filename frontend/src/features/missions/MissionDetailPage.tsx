import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Link, useParams } from "react-router-dom";

import { useNotifications } from "../../app/notificationContext";
import { ErrorState } from "../../components/feedback/ErrorState";
import { Spinner } from "../../components/feedback/Loading";
import { Seo } from "../../components/Seo";
import { Button } from "../../components/ui/Button";
import { buttonClassName } from "../../components/ui/buttonStyles";
import { Card } from "../../components/ui/Card";
import { getMission, submitMissionAction } from "./api";
import type { MissionActionType, MissionDetail } from "./types";

function label(value: string) {
  return value.replaceAll("_", " ");
}

function progressPercent(mission: MissionDetail) {
  return Math.min(100, Math.round((mission.progress_count / mission.target_count) * 100));
}

function rewardLabel(reward: Record<string, unknown>) {
  const points = typeof reward.points === "number" ? reward.points : null;
  const scoreKey = typeof reward.score_key === "string" ? label(reward.score_key) : null;
  if (points !== null && scoreKey) return `${points} ${scoreKey} points when completed`;
  if (points !== null) return `${points} points when completed`;
  if (scoreKey) return `${scoreKey} score reward when completed`;
  return "Reward details will appear after mission completion rules are finalized.";
}

const actionLabels: Record<MissionActionType, string> = {
  joined: "Join mission",
  verified_issue: "Verify linked issue",
  confirmed_unresolved: "Still unresolved",
  confirmed_fixed: "Confirm fixed",
  volunteered: "Volunteer",
};

export function MissionDetailPage() {
  const { missionId } = useParams();
  const queryClient = useQueryClient();
  const { notify } = useNotifications();
  const mission = useQuery({
    enabled: Boolean(missionId),
    queryKey: ["mission", missionId],
    queryFn: ({ signal }) => getMission(missionId ?? "", signal),
  });
  const action = useMutation({
    mutationFn: ({
      actionType,
      issueId,
    }: {
      actionType: MissionActionType;
      issueId?: string;
    }) => submitMissionAction(missionId ?? "", actionType, issueId),
    onSuccess: (response) => {
      queryClient.setQueryData<MissionDetail>(["mission", missionId], (current) =>
        current
          ? {
              ...current,
              progress_count: response.progress_count,
              target_count: response.target_count,
              status: response.mission_status,
              joined_count: response.joined_count,
              viewer_actions: response.viewer_actions,
            }
          : current,
      );
      void queryClient.invalidateQueries({ queryKey: ["missions"] });
      notify({
        title: response.accepted ? "Mission action recorded" : "Already recorded",
        message: response.accepted
          ? "Thanks — your mission contribution was added."
          : "You already submitted this mission action.",
        tone: response.accepted ? "success" : "info",
      });
    },
  });

  if (!missionId) {
    return (
      <section className="page-section">
        <ErrorState title="Mission not found" description="The mission link is incomplete." />
      </section>
    );
  }

  if (mission.isPending) {
    return (
      <section className="page-section">
        <Seo title="Loading mission" />
        <Spinner label="Loading community mission…" />
      </section>
    );
  }

  if (mission.isError) {
    return (
      <section className="page-section">
        <Seo title="Mission unavailable" />
        <div className="container">
          <ErrorState
            description={mission.error.message}
            onRetry={() => void mission.refetch()}
            title="Community mission could not be loaded"
          />
        </div>
      </section>
    );
  }

  const data = mission.data;
  const progress = progressPercent(data);
  const canAct = data.status === "active";
  const viewerActions = new Set(data.viewer_actions);
  const actionButton = (
    actionType: MissionActionType,
    issueId?: string,
  ) => (
    <Button
      disabled={!canAct || viewerActions.has(actionType)}
      isLoading={action.isPending && action.variables?.actionType === actionType}
      onClick={() => action.mutate({ actionType, issueId })}
      size="small"
      variant={viewerActions.has(actionType) ? "secondary" : "primary"}
    >
      {viewerActions.has(actionType) ? "Recorded" : actionLabels[actionType]}
    </Button>
  );

  return (
    <section className="page-section mission-detail-page">
      <Seo
        description={`Community mission for ${data.area.name}: ${data.goal_description}`}
        title={data.title}
      />
      <div className="container mission-detail-layout">
        <Link className={buttonClassName("secondary")} to="/missions">
          ← Back to Community Missions
        </Link>

        <header className="area-detail-hero">
          <div>
            <p className="eyebrow">{label(data.mission_type)} mission</p>
            <h1>{data.title}</h1>
            <p className="page-copy">{data.goal_description}</p>
            <div className="area-card-meta">
              <span>{label(data.status)}</span>
              <span>{data.area.name}</span>
              {data.category && <span>{label(data.category)}</span>}
            </div>
          </div>
        </header>

        <div className="area-detail-grid">
          <Card padding="large">
            <p className="eyebrow">Mission progress</p>
            <h2>
              {data.progress_count}/{data.target_count} actions completed
            </h2>
            <div className="mission-progress" aria-label={`${progress}% complete`}>
              <span style={{ width: `${progress}%` }} />
            </div>
            <p className="admin-muted">{data.ai_reason}</p>
            <p className="admin-muted">{data.joined_count} citizen(s) joined this mission.</p>
            {data.status === "completed" && (
              <p className="operations-action">
                Mission completed — the reward impact has been applied to this area’s Civic
                Genome.
              </p>
            )}
          </Card>

          <Card padding="large">
            <p className="eyebrow">Mission area</p>
            <h2>{data.area.name}</h2>
            <p className="admin-muted">
              This mission is connected to the public Civic Genome profile for this area.
            </p>
            <Link className="area-card-link" to={`/neighborhoods/${data.area.slug}`}>
              View Civic Genome
            </Link>
          </Card>
        </div>

        <Card padding="large">
          <p className="eyebrow">Mission reward</p>
          <h2>Reward impact</h2>
          <p className="admin-muted">{rewardLabel(data.reward)}</p>
        </Card>

        <Card padding="large">
          <p className="eyebrow">Participate</p>
          <h2>Take a safe public action</h2>
          {canAct ? (
            <>
              <p className="admin-muted">
                Use these actions only for things you can safely observe in public. Do not
                enter dangerous areas or replace official repair work.
              </p>
              <div className="admin-actions">
                {actionButton("joined")}
                {actionButton("volunteered")}
              </div>
            </>
          ) : (
            <p className="admin-muted">
              This mission is {label(data.status)} and is not accepting new actions.
            </p>
          )}
          {action.isError && (
            <ErrorState
              description={action.error.message}
              title="Mission action could not be recorded"
            />
          )}
        </Card>

        <Card padding="large">
          <p className="eyebrow">Linked public issues</p>
          <h2>Issue connections</h2>
          {data.linked_issue_ids.length ? (
            <ul className="mission-linked-list">
              {data.linked_issue_ids.map((issueId) => (
                <li key={issueId}>
                  <Link to={`/issues/${issueId}`}>View linked issue</Link>
                  {canAct && (
                    <div className="admin-actions">
                      {actionButton("verified_issue", issueId)}
                      {actionButton("confirmed_unresolved", issueId)}
                      {actionButton("confirmed_fixed", issueId)}
                    </div>
                  )}
                </li>
              ))}
            </ul>
          ) : (
            <p className="admin-muted">
              This mission is area-based and does not link to a specific public issue yet.
            </p>
          )}
        </Card>
      </div>
    </section>
  );
}
