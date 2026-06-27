import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { useNotifications } from "../../app/notificationContext";
import { EmptyState } from "../../components/feedback/EmptyState";
import { ErrorState } from "../../components/feedback/ErrorState";
import { Spinner } from "../../components/feedback/Loading";
import { Badge } from "../../components/ui/Badge";
import { Button } from "../../components/ui/Button";
import { Card } from "../../components/ui/Card";
import type { MissionDetail, MissionStatus } from "../missions/types";
import {
  completeMission,
  expireMission,
  generateMissionDrafts,
  getAdminMissions,
  publishMission,
} from "./api";
import { useAdminSession } from "./useAdminSession";

const statusTone: Record<MissionStatus, "neutral" | "info" | "success" | "warning"> = {
  draft: "neutral",
  active: "info",
  completed: "success",
  expired: "warning",
};

function formatCategory(category: string | null) {
  return category ? category.replaceAll("_", " ") : "all categories";
}

function formatMissionType(value: string) {
  return value.replaceAll("_", " ");
}

function formatStatus(value: MissionStatus) {
  return value.replaceAll("_", " ");
}

function missionActionMessage(action: "publish" | "expire" | "complete") {
  if (action === "publish") return "Mission published";
  if (action === "expire") return "Mission expired";
  return "Mission completed";
}

interface MissionCardProps {
  mission: MissionDetail;
  onComplete: (missionId: string) => void;
  onExpire: (missionId: string) => void;
  onPublish: (missionId: string) => void;
  pendingMissionId: string | null;
}

function MissionCard({
  mission,
  onComplete,
  onExpire,
  onPublish,
  pendingMissionId,
}: MissionCardProps) {
  const isPending = pendingMissionId === mission.id;
  return (
    <article className="operations-list-card">
      <div className="operations-list-card-heading">
        <div>
          <span>{mission.area.name}</span>
          <h4>{mission.title}</h4>
        </div>
        <Badge tone={statusTone[mission.status]}>{formatStatus(mission.status)}</Badge>
      </div>
      <p>{mission.goal_description}</p>
      <dl className="operations-mini-list">
        <div>
          <dt>Type</dt>
          <dd>{formatMissionType(mission.mission_type)}</dd>
        </div>
        <div>
          <dt>Progress</dt>
          <dd>{mission.progress_count} / {mission.target_count}</dd>
        </div>
        <div>
          <dt>Category</dt>
          <dd>{formatCategory(mission.category)}</dd>
        </div>
      </dl>
      <p className="operations-action">{mission.ai_reason}</p>
      {mission.linked_issue_ids.length > 0 && (
        <p className="admin-muted">
          Linked issue IDs: {mission.linked_issue_ids.join(", ")}
        </p>
      )}
      {mission.status === "draft" && (
        <Button
          isLoading={isPending}
          onClick={() => onPublish(mission.id)}
          size="small"
          variant="primary"
        >
          Publish mission
        </Button>
      )}
      {mission.status === "active" && (
        <div className="admin-actions">
          <Button
            isLoading={isPending}
            onClick={() => onComplete(mission.id)}
            size="small"
            variant="primary"
          >
            Mark complete
          </Button>
          <Button
            disabled={isPending}
            onClick={() => onExpire(mission.id)}
            size="small"
            variant="secondary"
          >
            Expire mission
          </Button>
        </div>
      )}
    </article>
  );
}

interface MissionSectionProps {
  emptyMessage: string;
  missions: MissionDetail[];
  onComplete: (missionId: string) => void;
  onExpire: (missionId: string) => void;
  onPublish: (missionId: string) => void;
  pendingMissionId: string | null;
  title: string;
}

function MissionSection({
  emptyMessage,
  missions,
  onComplete,
  onExpire,
  onPublish,
  pendingMissionId,
  title,
}: MissionSectionProps) {
  return (
    <Card as="section" className="operations-section" padding="large">
      <p className="eyebrow">Community missions</p>
      <h3>{title}</h3>
      {missions.length ? (
        <div className="operations-card-list operations-card-list-compact">
          {missions.map((mission) => (
            <MissionCard
              key={mission.id}
              mission={mission}
              onComplete={onComplete}
              onExpire={onExpire}
              onPublish={onPublish}
              pendingMissionId={pendingMissionId}
            />
          ))}
        </div>
      ) : (
        <p className="admin-muted operations-empty-section">{emptyMessage}</p>
      )}
    </Card>
  );
}

export function MissionGeneratorPanel() {
  const session = useAdminSession();
  const queryClient = useQueryClient();
  const { notify } = useNotifications();
  const missions = useQuery({
    queryKey: ["admin-missions"],
    queryFn: ({ signal }) => getAdminMissions(signal),
  });
  const generate = useMutation({
    mutationFn: () => generateMissionDrafts(session.data?.csrf_token ?? ""),
    onSuccess: (result) => {
      void queryClient.invalidateQueries({ queryKey: ["admin-missions"] });
      void queryClient.invalidateQueries({ queryKey: ["missions"] });
      notify({
        title: "Mission drafts created",
        message: `${result.created_drafts.length} draft mission${
          result.created_drafts.length === 1 ? "" : "s"
        } generated for admin review.`,
        tone: "success",
      });
    },
  });
  const missionAction = useMutation({
    mutationFn: async ({
      action,
      missionId,
    }: {
      action: "publish" | "expire" | "complete";
      missionId: string;
    }) => {
      const csrf = session.data?.csrf_token ?? "";
      if (action === "publish") return publishMission(missionId, csrf);
      if (action === "expire") return expireMission(missionId, csrf);
      return completeMission(missionId, csrf);
    },
    onSuccess: (_mission, variables) => {
      void queryClient.invalidateQueries({ queryKey: ["admin-missions"] });
      void queryClient.invalidateQueries({ queryKey: ["missions"] });
      notify({
        title: missionActionMessage(variables.action),
        message: "The admin mission console has been refreshed.",
        tone: "success",
      });
    },
  });
  const pendingMissionId = missionAction.isPending
    ? missionAction.variables.missionId
    : null;

  return (
    <Card as="section" className="operations-agent-panel" padding="large">
      <div className="operations-agent-heading">
        <div>
          <p className="eyebrow">Civic Mission Console</p>
          <h2>Review and publish community missions</h2>
          <p>
            Generate draft missions, review them before public visibility, and manage active
            mission lifecycle states from one admin-only console.
          </p>
        </div>
        <Button
          disabled={!session.data?.csrf_token}
          isLoading={generate.isPending}
          onClick={() => generate.mutate()}
        >
          Generate Community Missions
        </Button>
      </div>

      {generate.isPending && (
        <div className="operations-inline-state">
          <Spinner label="The Civic Mission Generator is creating draft missions…" />
        </div>
      )}

      {generate.isError && (
        <ErrorState
          description={generate.error.message}
          onRetry={() => generate.mutate()}
          title="Mission generation failed"
        />
      )}

      {missionAction.isError && (
        <ErrorState
          description={missionAction.error.message}
          title="Mission update failed"
        />
      )}

      {missions.isPending && (
        <div className="operations-inline-state">
          <Spinner label="Loading mission console…" />
        </div>
      )}

      {missions.isError && (
        <ErrorState
          description={missions.error.message}
          onRetry={() => void missions.refetch()}
          title="Mission console could not be loaded"
        />
      )}

      {missions.data && (
        <div className="operations-report-grid">
          <MissionSection
            emptyMessage="No draft missions are waiting for review."
            missions={missions.data.drafts}
            onComplete={(missionId) => missionAction.mutate({ action: "complete", missionId })}
            onExpire={(missionId) => missionAction.mutate({ action: "expire", missionId })}
            onPublish={(missionId) => missionAction.mutate({ action: "publish", missionId })}
            pendingMissionId={pendingMissionId}
            title="Draft mission review"
          />
          <MissionSection
            emptyMessage="No active missions are currently public."
            missions={missions.data.active}
            onComplete={(missionId) => missionAction.mutate({ action: "complete", missionId })}
            onExpire={(missionId) => missionAction.mutate({ action: "expire", missionId })}
            onPublish={(missionId) => missionAction.mutate({ action: "publish", missionId })}
            pendingMissionId={pendingMissionId}
            title="Active missions"
          />
          <MissionSection
            emptyMessage="No missions have been completed yet."
            missions={missions.data.completed}
            onComplete={(missionId) => missionAction.mutate({ action: "complete", missionId })}
            onExpire={(missionId) => missionAction.mutate({ action: "expire", missionId })}
            onPublish={(missionId) => missionAction.mutate({ action: "publish", missionId })}
            pendingMissionId={pendingMissionId}
            title="Completed missions"
          />
          <MissionSection
            emptyMessage="No missions have expired yet."
            missions={missions.data.expired}
            onComplete={(missionId) => missionAction.mutate({ action: "complete", missionId })}
            onExpire={(missionId) => missionAction.mutate({ action: "expire", missionId })}
            onPublish={(missionId) => missionAction.mutate({ action: "publish", missionId })}
            pendingMissionId={pendingMissionId}
            title="Expired missions"
          />
        </div>
      )}

      {missions.data &&
        !missions.data.drafts.length &&
        !missions.data.active.length &&
        !missions.data.completed.length &&
        !missions.data.expired.length && (
          <EmptyState
            description="Generate community missions to create the first admin-review drafts."
            title="No missions in the console yet"
          />
        )}
    </Card>
  );
}
