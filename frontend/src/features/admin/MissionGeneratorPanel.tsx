import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { useNotifications } from "../../app/notificationContext";
import { EmptyState } from "../../components/feedback/EmptyState";
import { ErrorState } from "../../components/feedback/ErrorState";
import { Spinner } from "../../components/feedback/Loading";
import { Badge } from "../../components/ui/Badge";
import { Button } from "../../components/ui/Button";
import { Card } from "../../components/ui/Card";
import { SelectField, TextAreaField, TextField } from "../../components/ui/FormField";
import { getAreas } from "../areas/api";
import type { MissionDetail, MissionStatus } from "../missions/types";
import {
  completeMission,
  createManualMission,
  deleteMission,
  expireMission,
  generateMissionDrafts,
  getAdminMissions,
  publishMission,
  refineManualMission,
} from "./api";
import type { ManualMissionCreate, ManualMissionDraft } from "./types";
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

const missionTypes = [
  "verification",
  "fix_confirmation",
  "hotspot",
  "category",
  "volunteer",
] as const;

const missionCategories = [
  "road_damage",
  "garbage_waste",
  "streetlight",
  "water_leakage",
  "drainage_sewage",
  "public_safety",
  "other",
] as const;

const rewardScoreKeys = [
  "infrastructure",
  "cleanliness",
  "safety",
  "participation",
  "responsiveness",
  "environment",
] as const;

const emptyManualDraft: ManualMissionDraft = {
  title: "",
  area_id: "",
  mission_type: "verification",
  goal_description: "",
  target_count: 5,
  category: "road_damage",
  reward_points: 20,
  reward_score_key: "participation",
  ai_reason: "",
  linked_issue_ids: [],
  expires_in_days: 7,
};

function parseLinkedIssueIds(value: string): string[] {
  return value
    .split(",")
    .map((item) => item.trim())
    .filter(Boolean);
}

function missionActionMessage(action: "publish" | "expire" | "complete" | "delete") {
  if (action === "publish") return "Mission published";
  if (action === "expire") return "Mission expired";
  if (action === "delete") return "Mission deleted";
  return "Mission completed";
}

interface MissionCardProps {
  mission: MissionDetail;
  onComplete: (missionId: string) => void;
  onDelete: (missionId: string) => void;
  onExpire: (missionId: string) => void;
  onPublish: (missionId: string) => void;
  pendingMissionId: string | null;
}

function MissionCard({
  mission,
  onComplete,
  onDelete,
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
        <div className="admin-actions">
          <Button
            isLoading={isPending}
            onClick={() => onPublish(mission.id)}
            size="small"
            variant="primary"
          >
            Publish mission
          </Button>
          <Button
            disabled={isPending}
            onClick={() => onDelete(mission.id)}
            size="small"
            variant="danger"
          >
            Delete draft
          </Button>
        </div>
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
      {mission.status === "expired" && (
        <Button
          isLoading={isPending}
          onClick={() => onDelete(mission.id)}
          size="small"
          variant="danger"
        >
          Delete expired mission
        </Button>
      )}
    </article>
  );
}

interface MissionSectionProps {
  emptyMessage: string;
  missions: MissionDetail[];
  onComplete: (missionId: string) => void;
  onDelete: (missionId: string) => void;
  onExpire: (missionId: string) => void;
  onPublish: (missionId: string) => void;
  pendingMissionId: string | null;
  title: string;
}

function MissionSection({
  emptyMessage,
  missions,
  onComplete,
  onDelete,
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
              onDelete={onDelete}
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
  const [manualDraft, setManualDraft] = useState<ManualMissionDraft>(emptyManualDraft);
  const [linkedIssueIdsText, setLinkedIssueIdsText] = useState("");
  const missions = useQuery({
    queryKey: ["admin-missions"],
    queryFn: ({ signal }) => getAdminMissions(signal),
  });
  const areas = useQuery({
    queryKey: ["areas"],
    queryFn: ({ signal }) => getAreas(signal),
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
  const refineManual = useMutation({
    mutationFn: () =>
      refineManualMission(
        {
          ...manualDraft,
          linked_issue_ids: parseLinkedIssueIds(linkedIssueIdsText),
        },
        session.data?.csrf_token ?? "",
      ),
    onSuccess: (result) => {
      setManualDraft(result);
      setLinkedIssueIdsText(result.linked_issue_ids.join(", "));
      notify({
        title: "Mission refined with AI",
        message: "Review the improved draft, then save or publish when ready.",
        tone: "success",
      });
    },
  });
  const createManual = useMutation({
    mutationFn: (publish: boolean) => {
      const payload: ManualMissionCreate = {
        ...manualDraft,
        publish,
        linked_issue_ids: parseLinkedIssueIds(linkedIssueIdsText),
      };
      return createManualMission(payload, session.data?.csrf_token ?? "");
    },
    onSuccess: (mission) => {
      void queryClient.invalidateQueries({ queryKey: ["admin-missions"] });
      void queryClient.invalidateQueries({ queryKey: ["missions"] });
      setManualDraft(emptyManualDraft);
      setLinkedIssueIdsText("");
      notify({
        title: mission.status === "active" ? "Manual mission published" : "Draft saved",
        message: "The admin mission console has been refreshed.",
        tone: "success",
      });
    },
  });
  const missionAction = useMutation({
    mutationFn: async ({
      action,
      missionId,
    }: {
      action: "publish" | "expire" | "complete" | "delete";
      missionId: string;
    }) => {
      const csrf = session.data?.csrf_token ?? "";
      if (action === "publish") return publishMission(missionId, csrf);
      if (action === "expire") return expireMission(missionId, csrf);
      if (action === "delete") return deleteMission(missionId, csrf);
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
  const canSubmitManual =
    Boolean(session.data?.csrf_token) &&
    Boolean(manualDraft.area_id) &&
    manualDraft.title.trim().length >= 8 &&
    manualDraft.goal_description.trim().length >= 20 &&
    manualDraft.ai_reason.trim().length >= 20;
  const setManualField = <Key extends keyof ManualMissionDraft>(
    key: Key,
    value: ManualMissionDraft[Key],
  ) => {
    setManualDraft((current) => ({ ...current, [key]: value }));
  };

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

      {refineManual.isError && (
        <ErrorState
          description={refineManual.error.message}
          title="Mission refinement failed"
        />
      )}

      {createManual.isError && (
        <ErrorState
          description={createManual.error.message}
          title="Manual mission could not be saved"
        />
      )}

      <Card as="section" className="operations-section" padding="large">
        <p className="eyebrow">Manual mission builder</p>
        <h3>Create a community mission manually</h3>
        <p className="admin-muted">
          Write the mission yourself, optionally refine the wording with AI, then save it
          as an admin-review draft or publish it immediately.
        </p>
        <div className="operations-manual-form">
          <TextField
            label="Mission heading"
            onChange={(event) => setManualField("title", event.target.value)}
            placeholder="Verify road damage near DMART"
            value={manualDraft.title}
          />
          <SelectField
            label="Neighborhood area"
            onChange={(event) => setManualField("area_id", event.target.value)}
            value={manualDraft.area_id}
          >
            <option value="">Select an area</option>
            {areas.data?.items?.map((area) => (
              <option key={area.id} value={area.id}>
                {area.name} · {area.city}
              </option>
            ))}
          </SelectField>
          <SelectField
            label="Mission type"
            onChange={(event) =>
              setManualField("mission_type", event.target.value as ManualMissionDraft["mission_type"])
            }
            value={manualDraft.mission_type}
          >
            {missionTypes.map((type) => (
              <option key={type} value={type}>
                {formatMissionType(type)}
              </option>
            ))}
          </SelectField>
          <SelectField
            label="Category"
            onChange={(event) =>
              setManualField("category", event.target.value || null)
            }
            value={manualDraft.category ?? ""}
          >
            <option value="">All categories</option>
            {missionCategories.map((category) => (
              <option key={category} value={category}>
                {formatCategory(category)}
              </option>
            ))}
          </SelectField>
          <TextField
            label="Target count"
            min={1}
            max={500}
            onChange={(event) =>
              setManualField("target_count", Number(event.target.value))
            }
            type="number"
            value={manualDraft.target_count}
          />
          <TextField
            label="Expires in days"
            min={1}
            max={30}
            onChange={(event) =>
              setManualField("expires_in_days", Number(event.target.value))
            }
            type="number"
            value={manualDraft.expires_in_days}
          />
          <TextField
            label="Reward points"
            min={0}
            max={100}
            onChange={(event) =>
              setManualField("reward_points", Number(event.target.value))
            }
            type="number"
            value={manualDraft.reward_points}
          />
          <SelectField
            label="Reward score"
            onChange={(event) => setManualField("reward_score_key", event.target.value)}
            value={manualDraft.reward_score_key}
          >
            {rewardScoreKeys.map((scoreKey) => (
              <option key={scoreKey} value={scoreKey}>
                {formatMissionType(scoreKey)}
              </option>
            ))}
          </SelectField>
          <TextAreaField
            label="Goal description"
            onChange={(event) => setManualField("goal_description", event.target.value)}
            placeholder="Ask nearby residents to safely confirm whether this issue is visible from public space."
            value={manualDraft.goal_description}
          />
          <TextAreaField
            label="Admin reason"
            onChange={(event) => setManualField("ai_reason", event.target.value)}
            placeholder="Explain why this mission matters right now."
            value={manualDraft.ai_reason}
          />
          <TextAreaField
            hint="Optional comma-separated UUIDs for issues this mission should reference."
            label="Linked issue IDs"
            onChange={(event) => setLinkedIssueIdsText(event.target.value)}
            optional
            value={linkedIssueIdsText}
          />
        </div>
        <div className="admin-actions">
          <Button
            disabled={!canSubmitManual}
            isLoading={refineManual.isPending}
            onClick={() => refineManual.mutate()}
            variant="secondary"
          >
            Refine with AI
          </Button>
          <Button
            disabled={!canSubmitManual}
            isLoading={createManual.isPending && createManual.variables === false}
            onClick={() => createManual.mutate(false)}
            variant="secondary"
          >
            Save draft
          </Button>
          <Button
            disabled={!canSubmitManual}
            isLoading={createManual.isPending && createManual.variables === true}
            onClick={() => createManual.mutate(true)}
          >
            Publish manually
          </Button>
        </div>
      </Card>

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
            onDelete={(missionId) => missionAction.mutate({ action: "delete", missionId })}
            onExpire={(missionId) => missionAction.mutate({ action: "expire", missionId })}
            onPublish={(missionId) => missionAction.mutate({ action: "publish", missionId })}
            pendingMissionId={pendingMissionId}
            title="Draft mission review"
          />
          <MissionSection
            emptyMessage="No active missions are currently public."
            missions={missions.data.active}
            onComplete={(missionId) => missionAction.mutate({ action: "complete", missionId })}
            onDelete={(missionId) => missionAction.mutate({ action: "delete", missionId })}
            onExpire={(missionId) => missionAction.mutate({ action: "expire", missionId })}
            onPublish={(missionId) => missionAction.mutate({ action: "publish", missionId })}
            pendingMissionId={pendingMissionId}
            title="Active missions"
          />
          <MissionSection
            emptyMessage="No missions have been completed yet."
            missions={missions.data.completed}
            onComplete={(missionId) => missionAction.mutate({ action: "complete", missionId })}
            onDelete={(missionId) => missionAction.mutate({ action: "delete", missionId })}
            onExpire={(missionId) => missionAction.mutate({ action: "expire", missionId })}
            onPublish={(missionId) => missionAction.mutate({ action: "publish", missionId })}
            pendingMissionId={pendingMissionId}
            title="Completed missions"
          />
          <MissionSection
            emptyMessage="No missions have expired yet."
            missions={missions.data.expired}
            onComplete={(missionId) => missionAction.mutate({ action: "complete", missionId })}
            onDelete={(missionId) => missionAction.mutate({ action: "delete", missionId })}
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
