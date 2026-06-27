import { useQuery } from "@tanstack/react-query";
import { Link, useParams } from "react-router-dom";

import { ErrorState } from "../../components/feedback/ErrorState";
import { Spinner } from "../../components/feedback/Loading";
import { Seo } from "../../components/Seo";
import { buttonClassName } from "../../components/ui/buttonStyles";
import { Card } from "../../components/ui/Card";
import { getArea } from "./api";
import { AreaScoreBadge } from "./AreaScoreBadge";
import { statusLabel } from "./areaLabels";
import type { AreaDetail, AreaScoreBreakdown } from "./types";

const scoreLabels: Array<keyof AreaScoreBreakdown> = [
  "infrastructure",
  "cleanliness",
  "safety",
  "participation",
  "responsiveness",
  "environment",
];

const scoreDescriptions: Record<keyof AreaScoreBreakdown, string> = {
  overall: "Weighted Civic Health Score from all Civic Genome categories.",
  infrastructure: "Roads, streetlights, water systems, and public infrastructure signals.",
  cleanliness: "Garbage, waste, sanitation, and repeated cleanliness reports.",
  safety: "High-risk reports, dark areas, unsafe infrastructure, and school-zone hazards.",
  participation: "Useful citizen verification, unresolved, and fixed-confirmation activity.",
  responsiveness: "How quickly serious and older issues move toward resolution.",
  environment: "Water leakage, drainage, sewage, waste, and environmental issue patterns.",
};

const eventLabels: Record<string, string> = {
  issue_published: "Citizen report published",
  community_action_saw_this_too: "Community verification",
  community_action_still_unresolved: "Still unresolved signal",
  community_action_fixed: "Fixed confirmation",
  admin_resolved: "Admin resolved",
  admin_rejected: "Admin rejected",
  admin_restored: "Admin restored",
  score_recalculated: "Score recalculated",
};

function eventLabel(eventType: string) {
  return eventLabels[eventType] ?? eventType.replaceAll("_", " ");
}

function label(value: string) {
  return value.replaceAll("_", " ");
}

function ScoreGrid({ area }: { area: AreaDetail }) {
  return (
    <div className="area-detail-score-grid">
      {scoreLabels.map((key) => (
        <Card as="article" className="area-detail-score-card" key={key}>
          <span>{key.replace("_", " ")}</span>
          <strong>{area.scores[key]}</strong>
          <p>{scoreDescriptions[key]}</p>
        </Card>
      ))}
    </div>
  );
}

export function AreaDetailPage() {
  const { slug } = useParams();
  const area = useQuery({
    enabled: Boolean(slug),
    queryKey: ["area", slug],
    queryFn: ({ signal }) => getArea(slug ?? "", signal),
  });

  if (!slug) {
    return (
      <section className="page-section">
        <ErrorState title="Neighborhood not found" description="The area link is incomplete." />
      </section>
    );
  }

  if (area.isPending) {
    return (
      <section className="page-section">
        <Seo title="Loading neighborhood" />
        <Spinner label="Loading Civic Genome…" />
      </section>
    );
  }

  if (area.isError) {
    return (
      <section className="page-section">
        <Seo title="Neighborhood unavailable" />
        <div className="container">
          <ErrorState
            description={area.error.message}
            onRetry={() => void area.refetch()}
            title="Civic Genome could not be loaded"
          />
        </div>
      </section>
    );
  }

  const data = area.data;

  return (
    <section className="page-section area-detail-page">
      <Seo
        description={`Civic Genome profile for ${data.name}, including health scores and neighborhood signals.`}
        title={`${data.name} Civic Genome`}
      />
      <div className="container area-detail-layout">
        <Link className={buttonClassName("secondary")} to="/neighborhoods">
          ← Back to Neighborhood Arena
        </Link>

        <header className="area-detail-hero">
          <div>
            <p className="eyebrow">{data.city} Civic Genome</p>
            <h1>{data.name}</h1>
            <p className="page-copy">
              This profile shows the current civic health baseline for the area. Score
              events and missions will make this profile more alive in the next phases.
            </p>
            <div className="area-card-meta">
              <span>{data.rank ? `Rank #${data.rank}` : "New area"}</span>
              <span>{statusLabel(data.status_label)}</span>
              <span>{data.total_issues} total reports</span>
            </div>
          </div>
          <AreaScoreBadge score={data.scores.overall} />
        </header>

        <ScoreGrid area={data} />

        <div className="area-detail-grid">
          <Card padding="large">
            <p className="eyebrow">Score activity</p>
            <h2>Recent Civic Genome events</h2>
            {data.recent_score_events.length ? (
              <ul className="area-event-list">
                {data.recent_score_events.map((event) => (
                  <li key={event.id}>
                    <span className="area-event-type">{eventLabel(event.event_type)}</span>
                    <strong>
                      {event.score_key.replace("_", " ")}{" "}
                      {event.score_change > 0 ? "+" : ""}
                      {event.score_change}
                    </strong>
                    <span>
                      {event.previous_score} → {event.new_score}
                    </span>
                    <p>{event.reason}</p>
                  </li>
                ))}
              </ul>
            ) : (
              <p className="admin-muted">
                Score events will appear here as community actions, admin updates, and
                missions affect this area.
              </p>
            )}
          </Card>

          <Card padding="large">
            <p className="eyebrow">Neighborhood signals</p>
            <h2>Current activity</h2>
            <dl className="area-detail-facts">
              <div>
                <dt>Open issues</dt>
                <dd>{data.open_issues}</dd>
              </div>
              <div>
                <dt>Resolved this week</dt>
                <dd>{data.resolved_this_week}</dd>
              </div>
              <div>
                <dt>Active missions</dt>
                <dd>{data.active_missions}</dd>
              </div>
            </dl>
          </Card>
        </div>

        <div className="area-detail-grid">
          <Card padding="large">
            <p className="eyebrow">Active local issues</p>
            <h2>Issues currently shaping this Civic Genome</h2>
            {data.active_issues.length ? (
              <ul className="area-issue-list">
                {data.active_issues.map((issue) => (
                  <li key={issue.id}>
                    <div>
                      <Link to={`/issues/${issue.id}`}>{issue.title}</Link>
                      <span>{issue.public_reference}</span>
                    </div>
                    <div className="area-card-meta">
                      <span>{label(issue.category)}</span>
                      <span>{label(issue.severity)}</span>
                      <span>{label(issue.status)}</span>
                    </div>
                  </li>
                ))}
              </ul>
            ) : (
              <p className="admin-muted">
                No active public issues are currently attached to this area.
              </p>
            )}
          </Card>

          <Card padding="large">
            <p className="eyebrow">Community missions</p>
            <h2>Active missions</h2>
            <p className="admin-muted">
              {data.active_missions > 0
                ? `${data.active_missions} active mission${
                    data.active_missions === 1 ? "" : "s"
                  } are connected to this area.`
                : "Missions will appear here after the mission engine is introduced."}
            </p>
          </Card>
        </div>
      </div>
    </section>
  );
}
