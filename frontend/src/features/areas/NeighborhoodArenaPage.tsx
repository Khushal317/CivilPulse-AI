import { useQuery } from "@tanstack/react-query";
import { Link } from "react-router-dom";

import { EmptyState } from "../../components/feedback/EmptyState";
import { ErrorState } from "../../components/feedback/ErrorState";
import { Skeleton } from "../../components/feedback/Loading";
import { Seo } from "../../components/Seo";
import { Card } from "../../components/ui/Card";
import { ScoreMeter } from "../../components/ui/ScoreMeter";
import { TrendPill } from "../../components/ui/TrendPill";
import { getAreas } from "./api";
import { AreaScoreBadge } from "./AreaScoreBadge";
import { statusLabel } from "./areaLabels";
import type { AreaSummary } from "./types";

function titleLabel(value: string) {
  return value.replaceAll("_", " ").replace(/\b\w/g, (letter) => letter.toUpperCase());
}

function areaHighlights(area: AreaSummary) {
  const highlights: string[] = [];
  if (area.rank === 1) highlights.push("City leader");
  if (area.resolved_this_week > 0) highlights.push(`${area.resolved_this_week} resolved this week`);
  if (area.active_missions > 0) highlights.push(`${area.active_missions} active mission${area.active_missions === 1 ? "" : "s"}`);
  if (area.open_issues === 0) highlights.push("No open issues");
  if (area.civic_genome.confidence_level === "high") highlights.push("High confidence");
  return highlights.slice(0, 3);
}

function AreaCard({ area }: { area: AreaSummary }) {
  const highlights = areaHighlights(area);

  return (
    <Card as="article" className="area-card" padding="large">
      <div className="area-card-heading">
        <div>
          <p className="eyebrow">{area.city}</p>
          <h2>{area.name}</h2>
        </div>
        <AreaScoreBadge score={area.civic_genome.civic_health_score} />
      </div>

      <div className="area-card-meta">
        <span>{area.rank ? `Rank #${area.rank}` : "New area"}</span>
        <span>{statusLabel(area.status_label)}</span>
        <span>{titleLabel(area.civic_genome.confidence_level)} confidence</span>
      </div>

      <div className="area-card-score-stack">
        <ScoreMeter
          helper="Overall area condition."
          label="Civic Health"
          tone="civic-health"
          value={area.civic_genome.civic_health_score}
        />
        <ScoreMeter
          helper="Resident participation strength."
          label="Community Power"
          tone="community-power"
          value={area.civic_genome.community_power_score}
        />
      </div>

      <div className="area-card-stats">
        <div>
          <span>Open issues</span>
          <strong>{area.open_issues}</strong>
        </div>
        <div>
          <span>Resolved this week</span>
          <strong>{area.resolved_this_week}</strong>
        </div>
        <div>
          <span>Active missions</span>
          <strong>{area.active_missions}</strong>
        </div>
      </div>
      {highlights.length ? (
        <div className="area-achievement-row" aria-label={`${area.name} highlights`}>
          {highlights.map((highlight) => (
            <TrendPill
              direction={highlight.includes("open") ? "flat" : "up"}
              key={highlight}
            >
              {highlight}
            </TrendPill>
          ))}
        </div>
      ) : null}
      <Link className="area-card-link" to={`/neighborhoods/${area.slug}`}>
        View Civic Genome
      </Link>
    </Card>
  );
}

function ArenaSkeleton() {
  return (
    <div aria-label="Loading neighborhoods" className="area-grid" role="status">
      {[1, 2, 3].map((item) => (
        <Card className="area-card" key={item} padding="large">
          <Skeleton width="50%" />
          <Skeleton height="3rem" />
          <Skeleton width="80%" />
          <Skeleton width="70%" />
        </Card>
      ))}
    </div>
  );
}

export function NeighborhoodArenaPage() {
  const areas = useQuery({
    queryKey: ["areas"],
    queryFn: ({ signal }) => getAreas(signal),
  });

  return (
    <section className="page-section arena-page">
      <Seo
        description="Explore CivicPulse AI neighborhood civic health profiles and area rankings."
        title="Neighborhood Arena"
      />
      <div className="container arena-layout">
        <header className="arena-heading">
          <div>
            <p className="eyebrow">Neighborhood Arena</p>
            <h1>Every neighborhood has a civic character</h1>
            <p className="page-copy">
              Compare Civic Health, Community Power, confidence, and real public signals
              across areas. The goal is not to shame neighborhoods — it is to show where
              people are helping and where the city still needs attention.
            </p>
          </div>
        </header>

        {areas.isPending && <ArenaSkeleton />}
        {areas.isError && (
          <ErrorState
            description={areas.error.message}
            onRetry={() => void areas.refetch()}
            title="Neighborhood Arena could not be loaded"
          />
        )}
        {areas.data && areas.data.items.length === 0 && (
          <EmptyState
            description="Neighborhood profiles will appear after the first public issues are attached to areas."
            title="No neighborhood profiles yet"
          />
        )}
        {areas.data && areas.data.items.length > 0 && (
          <div className="area-grid">
            {areas.data.items.map((area) => (
              <AreaCard area={area} key={area.id} />
            ))}
          </div>
        )}
      </div>
    </section>
  );
}
