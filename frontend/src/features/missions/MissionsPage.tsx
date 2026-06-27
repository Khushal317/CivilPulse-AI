import { useQuery } from "@tanstack/react-query";
import { Link } from "react-router-dom";

import { EmptyState } from "../../components/feedback/EmptyState";
import { ErrorState } from "../../components/feedback/ErrorState";
import { Skeleton } from "../../components/feedback/Loading";
import { Seo } from "../../components/Seo";
import { Card } from "../../components/ui/Card";
import { getMissions } from "./api";
import type { MissionSummary } from "./types";

function label(value: string) {
  return value.replaceAll("_", " ");
}

function progressPercent(mission: MissionSummary) {
  return Math.min(100, Math.round((mission.progress_count / mission.target_count) * 100));
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
        <span className="mission-status">{label(mission.status)}</span>
      </div>
      <p>{mission.goal_description}</p>
      <div className="mission-progress" aria-label={`${progress}% complete`}>
        <span style={{ width: `${progress}%` }} />
      </div>
      <div className="mission-card-meta">
        <span>
          {mission.progress_count}/{mission.target_count} progress
        </span>
        <span>{mission.joined_count} joined</span>
        <Link to={`/neighborhoods/${mission.area.slug}`}>{mission.area.name}</Link>
      </div>
      <p className="admin-muted">{mission.ai_reason}</p>
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
            <h1>Useful missions for local civic progress</h1>
            <p className="page-copy">
              Missions turn civic signals into clear community actions. Active missions
              will appear here after admins review and publish them.
            </p>
          </div>
        </header>

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
