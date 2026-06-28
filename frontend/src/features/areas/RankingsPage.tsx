import { useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Link } from "react-router-dom";

import { EmptyState } from "../../components/feedback/EmptyState";
import { ErrorState } from "../../components/feedback/ErrorState";
import { Spinner } from "../../components/feedback/Loading";
import { Seo } from "../../components/Seo";
import { Card } from "../../components/ui/Card";
import { getAreas } from "./api";
import { AreaScoreBadge } from "./AreaScoreBadge";
import { statusLabel } from "./areaLabels";
import type { AreaScoreBreakdown, AreaSummary } from "./types";

type RankingKey =
  | "civic_health"
  | "community_power"
  | Extract<keyof AreaScoreBreakdown, "safety" | "cleanliness" | "responsiveness">;

interface RankingTab {
  key: RankingKey;
  label: string;
  description: string;
}

const rankingTabs: RankingTab[] = [
  {
    key: "civic_health",
    label: "Civic Health",
    description: "Area condition across infrastructure, cleanliness, safety, environment, and responsiveness.",
  },
  {
    key: "safety",
    label: "Safety",
    description: "Highlights neighborhoods with stronger safety-related signals.",
  },
  {
    key: "cleanliness",
    label: "Cleanliness",
    description: "Highlights sanitation, waste, and cleanliness progress.",
  },
  {
    key: "community_power",
    label: "Community Power",
    description: "Highlights areas where residents are actively verifying, joining missions, and helping progress.",
  },
  {
    key: "responsiveness",
    label: "Responsiveness",
    description: "Highlights areas where issues are moving toward timely resolution.",
  },
];

function scoreValue(area: AreaSummary, key: RankingKey) {
  if (key === "civic_health") return area.civic_genome.civic_health_score;
  if (key === "community_power") return area.civic_genome.community_power_score;
  return area.scores[key];
}

function sortedAreas(areas: AreaSummary[], key: RankingKey) {
  return [...areas].sort((left, right) => {
    const scoreDifference = scoreValue(right, key) - scoreValue(left, key);
    if (scoreDifference !== 0) {
      return scoreDifference;
    }
    return left.name.localeCompare(right.name);
  });
}

export function RankingsPage() {
  const [activeKey, setActiveKey] = useState<RankingKey>("civic_health");
  const areas = useQuery({
    queryKey: ["areas"],
    queryFn: ({ signal }) => getAreas(signal),
  });

  const activeTab = rankingTabs.find((tab) => tab.key === activeKey) ?? rankingTabs[0];
  const rankedAreas = useMemo(
    () => sortedAreas(areas.data?.items ?? [], activeKey),
    [activeKey, areas.data?.items],
  );

  return (
    <section className="page-section rankings-page">
      <Seo
        description="Browse positive Civic Genome rankings by Civic Health, Community Power, safety, cleanliness, and responsiveness signals."
        title="City Rankings"
      />
      <div className="container rankings-layout">
        <header className="arena-heading">
          <div>
            <p className="eyebrow">City Rankings</p>
            <h1>Positive Civic Genome rankings</h1>
            <p className="page-copy">
              Compare neighborhoods by their strongest public civic signals. These
              rankings are designed to highlight progress and guide community missions.
            </p>
          </div>
        </header>

        {areas.isPending && <Spinner label="Loading city rankings…" />}
        {areas.isError && (
          <ErrorState
            description={areas.error.message}
            onRetry={() => void areas.refetch()}
            title="City rankings could not be loaded"
          />
        )}
        {areas.data && areas.data.items.length === 0 && (
          <EmptyState
            description="Rankings will appear after the first neighborhood profiles are created."
            title="No rankings yet"
          />
        )}
        {areas.data && areas.data.items.length > 0 && (
          <>
            <div aria-label="Ranking categories" className="ranking-tabs" role="tablist">
              {rankingTabs.map((tab) => (
                <button
                  aria-selected={activeKey === tab.key}
                  className={activeKey === tab.key ? "ranking-tab active" : "ranking-tab"}
                  key={tab.key}
                  onClick={() => setActiveKey(tab.key)}
                  role="tab"
                  type="button"
                >
                  {tab.label}
                </button>
              ))}
            </div>

            <Card className="ranking-panel" padding="large">
              <div className="ranking-panel-heading">
                <div>
                  <p className="eyebrow">{activeTab.label} ranking</p>
                  <h2>{activeTab.label} leaders</h2>
                  <p>{activeTab.description}</p>
                </div>
              </div>
              <ol className="ranking-list">
                {rankedAreas.map((area, index) => (
                  <li key={area.id}>
                    <span className="ranking-position">#{index + 1}</span>
                    <div className="ranking-main">
                      <Link to={`/neighborhoods/${area.slug}`}>{area.name}</Link>
                      <span>
                        {statusLabel(area.status_label)} · {area.open_issues} open issues ·{" "}
                        {area.resolved_this_week} resolved this week
                      </span>
                    </div>
                    <AreaScoreBadge score={scoreValue(area, activeKey)} />
                  </li>
                ))}
              </ol>
            </Card>
          </>
        )}
      </div>
    </section>
  );
}
