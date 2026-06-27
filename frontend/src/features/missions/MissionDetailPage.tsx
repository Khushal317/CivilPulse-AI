import { useQuery } from "@tanstack/react-query";
import { Link, useParams } from "react-router-dom";

import { ErrorState } from "../../components/feedback/ErrorState";
import { Spinner } from "../../components/feedback/Loading";
import { Seo } from "../../components/Seo";
import { buttonClassName } from "../../components/ui/buttonStyles";
import { Card } from "../../components/ui/Card";
import { getMission } from "./api";
import type { MissionDetail } from "./types";

function label(value: string) {
  return value.replaceAll("_", " ");
}

function progressPercent(mission: MissionDetail) {
  return Math.min(100, Math.round((mission.progress_count / mission.target_count) * 100));
}

export function MissionDetailPage() {
  const { missionId } = useParams();
  const mission = useQuery({
    enabled: Boolean(missionId),
    queryKey: ["mission", missionId],
    queryFn: ({ signal }) => getMission(missionId ?? "", signal),
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
          <p className="eyebrow">Linked public issues</p>
          <h2>Issue connections</h2>
          {data.linked_issue_ids.length ? (
            <ul className="mission-linked-list">
              {data.linked_issue_ids.map((issueId) => (
                <li key={issueId}>
                  <Link to={`/issues/${issueId}`}>View linked issue</Link>
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
