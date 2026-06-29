import { useQuery } from "@tanstack/react-query";
import { Link, useParams } from "react-router-dom";

import { ErrorState } from "../../components/feedback/ErrorState";
import { Spinner } from "../../components/feedback/Loading";
import { Seo } from "../../components/Seo";
import { buttonClassName } from "../../components/ui/buttonStyles";
import { Card } from "../../components/ui/Card";
import { CivicStatCard } from "../../components/ui/CivicStatCard";
import { GeminiLabel } from "../../components/ui/GeminiLabel";
import { ScoreMeter } from "../../components/ui/ScoreMeter";
import { TrendPill } from "../../components/ui/TrendPill";
import { getArea } from "./api";
import { AreaScoreBadge } from "./AreaScoreBadge";
import { statusLabel } from "./areaLabels";
import type { AreaDetail, AreaInsight, AreaScoreBreakdown } from "./types";

type CivicHealthCategoryKey = Exclude<keyof AreaScoreBreakdown, "overall" | "participation">;

const scoreLabels: CivicHealthCategoryKey[] = [
  "infrastructure",
  "cleanliness",
  "safety",
  "responsiveness",
  "environment",
];

const scoreDescriptions: Record<keyof AreaScoreBreakdown, string> = {
  overall: "Civic Health Score from condition and responsiveness categories.",
  infrastructure: "Roads, streetlights, water systems, and public infrastructure signals.",
  cleanliness: "Garbage, waste, sanitation, and repeated cleanliness reports.",
  safety: "High-risk reports, dark areas, unsafe infrastructure, and school-zone hazards.",
  participation: "Useful citizen verification, unresolved, and fixed-confirmation activity.",
  responsiveness: "How quickly serious and older issues move toward resolution.",
  environment: "Water leakage, drainage, sewage, waste, and environmental issue patterns.",
};

const scoreTones: Record<
  CivicHealthCategoryKey,
  "cleanliness" | "environment" | "infrastructure" | "responsiveness" | "safety"
> = {
  infrastructure: "infrastructure",
  cleanliness: "cleanliness",
  safety: "safety",
  responsiveness: "responsiveness",
  environment: "environment",
};

const eventLabels: Record<string, string> = {
  issue_published: "Citizen report published",
  community_action_saw_this_too: "Community verification",
  community_action_still_unresolved: "Still unresolved signal",
  community_action_fixed: "Fixed confirmation",
  admin_resolved: "Admin resolved",
  admin_rejected: "Admin rejected",
  admin_duplicate: "Duplicate removed",
  admin_restored: "Admin restored",
  mission_completed: "Mission completed",
  score_recalculated: "Score recalculated",
};

function eventLabel(eventType: string) {
  return eventLabels[eventType] ?? eventType.replaceAll("_", " ");
}

function label(value: string) {
  return value.replaceAll("_", " ");
}

function titleLabel(value: string) {
  return label(value).replace(/\b\w/g, (letter) => letter.toUpperCase());
}

function confidenceLabel(value: AreaDetail["civic_genome"]["confidence_level"]) {
  return titleLabel(value);
}

function scoreEventLabel(scoreKey: keyof AreaScoreBreakdown) {
  if (scoreKey === "overall") return "Civic Health";
  if (scoreKey === "participation") return "Community Power";
  return `${titleLabel(scoreKey)} · Civic Health`;
}

function safeInsight(area: AreaDetail): AreaInsight {
  return (
    area.insight ?? {
      explanation:
        "This Civic Genome is being prepared from public area signals. Check current issues, community missions, and score activity for the latest neighborhood context.",
      next_best_actions: [
        "Review active public issues and verify only what can be safely observed.",
        "Check the community missions page for admin-approved local actions.",
      ],
      model_used: "frontend-safe-fallback",
    }
  );
}

function isGeminiInsight(insight: AreaInsight) {
  return insight.model_used.toLowerCase().includes("gemini");
}

function positiveScoreEvents(area: AreaDetail) {
  return area.recent_score_events.filter((event) => event.score_change > 0).slice(0, 3);
}

function ScoreGrid({ area }: { area: AreaDetail }) {
  return (
    <div className="area-detail-score-grid">
      {scoreLabels.map((key) => (
        <Card as="article" className="area-detail-score-card" key={key}>
          <ScoreMeter
            helper={scoreDescriptions[key]}
            label={titleLabel(key)}
            tone={scoreTones[key]}
            value={area.scores[key]}
          />
        </Card>
      ))}
      <Card as="article" className="area-detail-score-card area-community-score-card">
        <ScoreMeter
          helper="Resident verification, unresolved/fixed confirmations, mission participation, and volunteer action signals."
          label="Community Power"
          tone="community-power"
          value={area.civic_genome.community_power_score}
        />
      </Card>
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
  const insight = safeInsight(data);
  const improvements = positiveScoreEvents(data);

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
              A transparent civic profile showing where the area is healthy, where
              problems remain, and how residents are helping move the score.
            </p>
            <div className="area-card-meta">
              <span>{data.rank ? `Rank #${data.rank}` : "New area"}</span>
              <span>{statusLabel(data.status_label)}</span>
              <span>{data.total_issues} total reports</span>
            </div>
          </div>
          <AreaScoreBadge score={data.civic_genome.civic_health_score} />
        </header>

        <div className="area-genome-summary-grid">
          <CivicStatCard
            description="Overall area condition from infrastructure, cleanliness, safety, environment, and responsiveness."
            eyebrow="Civic Health Score"
            icon="🏙️"
            tone="brand"
            value={`${data.civic_genome.civic_health_score}/100`}
          />
          <CivicStatCard
            description="Resident activity through verifications, missions, and useful public signals."
            eyebrow="Community Power Score"
            icon="🤝"
            tone="success"
            value={`${data.civic_genome.community_power_score}/100`}
          />
          <CivicStatCard
            description={data.civic_genome.confidence_reason}
            eyebrow="Confidence"
            icon="◎"
            tone={data.civic_genome.confidence_level === "high" ? "success" : data.civic_genome.confidence_level === "low" ? "warning" : "ai"}
            value={confidenceLabel(data.civic_genome.confidence_level)}
          />
        </div>

        {data.civic_genome.score_limit_reasons.length ? (
          <Card className="area-score-limit-card" padding="large">
            <p className="eyebrow">Score limited because</p>
            <ul className="mission-linked-list">
              {data.civic_genome.score_limit_reasons.map((reason) => (
                <li key={reason}>{reason}</li>
              ))}
            </ul>
          </Card>
        ) : null}

        <ScoreGrid area={data} />

        <Card className="area-insight-card" padding="large">
          <div className="detail-section-heading">
            <div>
              <p className="eyebrow">Civic explanation</p>
              <h2>What this Civic Genome means</h2>
            </div>
            <GeminiLabel>
              {isGeminiInsight(insight) ? "Generated by Gemini" : "AI-assisted insight"}
            </GeminiLabel>
          </div>
          <p className="page-copy">{insight.explanation}</p>
          <dl className="operations-report-meta">
            <div>
              <dt>Insight model</dt>
              <dd>{insight.model_used}</dd>
            </div>
          </dl>
          <h3>Next best actions</h3>
          <ul className="mission-linked-list">
            {insight.next_best_actions.map((action) => (
              <li key={action}>{action}</li>
            ))}
          </ul>
        </Card>

        <div className="area-detail-grid">
          <Card padding="large">
            <p className="eyebrow">Score activity</p>
            <h2>Why this score changed</h2>
            {data.recent_score_events.length ? (
              <ul className="area-event-list">
                {data.recent_score_events.map((event) => (
                  <li key={event.id}>
                    <span className="area-event-type">{eventLabel(event.event_type)}</span>
                    <strong>
                      {scoreEventLabel(event.score_key)}{" "}
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
            <p className="eyebrow">Recent improvements</p>
            <h2>What is getting better?</h2>
            {improvements.length ? (
              <ul className="area-improvement-list">
                {improvements.map((event) => (
                  <li key={event.id}>
                    <TrendPill direction="up">
                      {scoreEventLabel(event.score_key)} +{event.score_change}
                    </TrendPill>
                    <p>{event.reason}</p>
                  </li>
                ))}
              </ul>
            ) : (
              <p className="admin-muted">
                {data.resolved_this_week > 0
                  ? `${data.resolved_this_week} issue${
                      data.resolved_this_week === 1 ? " was" : "s were"
                    } resolved this week. Positive score events will appear here as they are recorded.`
                  : "No recent improvement events are attached to this area yet. Resolved issues and completed missions will make this section come alive."}
              </p>
            )}
            <div className="area-card-meta">
              <span>
                {data.active_missions} active mission{data.active_missions === 1 ? "" : "s"}
              </span>
              <span>{data.resolved_this_week} resolved this week</span>
            </div>
            <Link className="area-card-link" to="/missions">
              Browse community missions
            </Link>
          </Card>
        </div>
      </div>
    </section>
  );
}
