import { useQuery } from "@tanstack/react-query";
import { Link } from "react-router-dom";

import { EmptyState } from "../../components/feedback/EmptyState";
import { ErrorState } from "../../components/feedback/ErrorState";
import { Skeleton } from "../../components/feedback/Loading";
import { Seo } from "../../components/Seo";
import { Card } from "../../components/ui/Card";
import { CivicStatCard } from "../../components/ui/CivicStatCard";
import { GeminiLabel } from "../../components/ui/GeminiLabel";
import { TrendPill } from "../../components/ui/TrendPill";
import { getMissions } from "./api";
import type { MissionStatus, MissionSummary } from "./types";

function label(value: string) {
  return value.replaceAll("_", " ");
}

function titleLabel(value: string) {
  return label(value).replace(/\b\w/g, (letter) => letter.toUpperCase());
}

function progressPercent(mission: MissionSummary) {
  if (mission.target_count <= 0) return 0;
  return Math.min(100, Math.round((mission.progress_count / mission.target_count) * 100));
}

function rewardLabel(reward: Record<string, unknown>) {
  const points = typeof reward.points === "number" ? reward.points : null;
  const scoreKey = typeof reward.score_key === "string" ? label(reward.score_key) : null;
  if (points !== null && scoreKey) return `${points} ${scoreKey} points`;
  if (points !== null) return `${points} points`;
  if (scoreKey) return `${scoreKey} score reward`;
  return "Reward pending";
}

function missionStatusClass(status: MissionStatus) {
  return `mission-status mission-status-${status}`;
}

function statusDirection(status: MissionStatus) {
  if (status === "completed") return "up";
  if (status === "expired") return "down";
  return "flat";
}

function MissionCard({ mission }: { mission: MissionSummary }) {
  const progress = progressPercent(mission);
  return (
    <Card as="article" className="mission-card" padding="large">
      <div className="mission-card-heading">
        <div>
          <p className="eyebrow">{label(mission.mission_type)} mission</p>
          <h2>{mission.title}</h2>
        </div>
        <span className={missionStatusClass(mission.status)}>{label(mission.status)}</span>
      </div>
      <p>{mission.goal_description}</p>

      <div className="mission-quest-panel">
        <div className="mission-progress-heading">
          <span>Quest progress</span>
          <strong>
            {mission.progress_count}/{mission.target_count}
          </strong>
        </div>
        <div className="mission-progress" aria-label={`${progress}% complete`}>
          <span style={{ width: `${progress}%` }} />
        </div>
        <div className="mission-quest-pills">
          <TrendPill direction={statusDirection(mission.status)}>
            {titleLabel(mission.status)}
          </TrendPill>
          <TrendPill direction={mission.joined_count > 0 ? "up" : "flat"}>
            {mission.joined_count} joined
          </TrendPill>
          <TrendPill direction="up">{rewardLabel(mission.reward)}</TrendPill>
        </div>
      </div>

      <div className="mission-card-meta">
        <span>
          {mission.progress_count}/{mission.target_count} progress
        </span>
        <span>{mission.joined_count} joined</span>
        <Link to={`/neighborhoods/${mission.area.slug}`}>{mission.area.name}</Link>
      </div>
      <div className="mission-ai-reason">
        <GeminiLabel>AI-assisted reason</GeminiLabel>
        <p>{mission.ai_reason}</p>
      </div>
      <Link className="area-card-link" to={`/missions/${mission.id}`}>
        View mission
      </Link>
    </Card>
  );
}

function MissionSkeleton() {
  return (
    <div aria-label="Loading missions" className="mission-grid" role="status">
      {[1, 2, 3].map((item) => (
        <Card className="mission-card" key={item} padding="large">
          <Skeleton width="45%" />
          <Skeleton height="2.5rem" />
          <Skeleton width="80%" />
          <Skeleton width="100%" />
        </Card>
      ))}
    </div>
  );
}

export function MissionsPage() {
  const missions = useQuery({
    queryKey: ["missions"],
    queryFn: ({ signal }) => getMissions(signal),
  });
  const missionItems = missions.data?.items ?? [];
  const activeCount = missionItems.filter((mission) => mission.status === "active").length;
  const joinedCount = missionItems.reduce((total, mission) => total + mission.joined_count, 0);
  const completedCount = missionItems.filter((mission) => mission.status === "completed").length;

  return (
    <section className="page-section missions-page">
      <Seo
        description="Explore active CivicPulse AI community missions that help residents verify, improve, and track local civic progress."
        title="Community Missions"
      />
      <div className="container mission-layout">
        <header className="arena-heading">
          <div>
            <p className="eyebrow">Community Missions</p>
            <h1>Community quests for local civic progress</h1>
            <p className="page-copy">
              Missions turn public civic signals into safe, admin-approved quests residents
              can join. Each mission is tied to a neighborhood, a visible goal, and a clear
              progress target.
            </p>
          </div>
        </header>

        {missionItems.length > 0 && (
          <div className="mission-summary-grid" aria-label="Mission snapshot">
            <CivicStatCard
              description="Published missions residents can act on now."
              eyebrow="Active Quests"
              icon="⚑"
              value={activeCount}
            />
            <CivicStatCard
              description="Total resident joins across visible missions."
              eyebrow="Residents Joined"
              icon="🤝"
              tone="success"
              value={joinedCount}
            />
            <CivicStatCard
              description="Missions that already reached completion."
              eyebrow="Completed"
              icon="✓"
              tone="ai"
              value={completedCount}
            />
          </div>
        )}

        {missions.isPending && <MissionSkeleton />}
        {missions.isError && (
          <ErrorState
            description={missions.error.message}
            onRetry={() => void missions.refetch()}
            title="Community missions could not be loaded"
          />
        )}
        {missions.data && missions.data.items.length === 0 && (
          <EmptyState
            description="Community missions will appear after the first admin-approved mission is published."
            title="No active missions yet"
          />
        )}
        {missions.data && missions.data.items.length > 0 && (
          <div className="mission-grid">
            {missions.data.items.map((mission) => (
              <MissionCard key={mission.id} mission={mission} />
            ))}
          </div>
        )}
      </div>
    </section>
  );
}
