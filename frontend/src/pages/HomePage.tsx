import { useQuery } from "@tanstack/react-query";
import { Link } from "react-router-dom";

import { getApiHealth } from "../api/health";
import { Seo } from "../components/Seo";
import { Card } from "../components/ui/Card";
import { buttonClassName } from "../components/ui/buttonStyles";
import { CivicStatCard } from "../components/ui/CivicStatCard";
import { GeminiLabel } from "../components/ui/GeminiLabel";
import { ScoreMeter } from "../components/ui/ScoreMeter";
import { getAreas } from "../features/areas/api";
import type { AreaSummary } from "../features/areas/types";
import { getPublicIssues } from "../features/issues/api";
import type { PublicIssueListItem } from "../features/issues/types";
import { getMissions } from "../features/missions/api";
import type { MissionSummary } from "../features/missions/types";

const productSteps = [
  {
    title: "Report",
    copy: "Add a photo, location, and short description. Gemini helps turn messy observations into a clean civic report.",
  },
  {
    title: "Verify",
    copy: "Neighbors can confirm, flag duplicates, or say the issue is still unresolved without creating an account.",
  },
  {
    title: "Evolve",
    copy: "Reports, verifications, missions, and resolutions become signals that help neighborhoods level up over time.",
  },
];

const aiFeatures = [
  {
    title: "Structured civic reports",
    copy: "Gemini turns a citizen photo and description into a clearer issue title, category, summary, urgency, and next action.",
  },
  {
    title: "Civic Genome explanations",
    copy: "Neighborhood pages explain why scores are moving, what is limiting progress, and what residents can do next.",
  },
  {
    title: "Operations intelligence",
    copy: "Admins can review AI-assisted hotspots, urgent issues, predicted risks, and mission ideas without auto-publishing them.",
  },
];

const titleLabel = (value: string) =>
  value.replaceAll("_", " ").replace(/\b\w/g, (letter) => letter.toUpperCase());

const average = (values: number[]) => {
  if (values.length === 0) return null;
  return Math.round(values.reduce((total, value) => total + value, 0) / values.length);
};

const topAreas = (areas: AreaSummary[]) =>
  [...areas]
    .sort((left, right) => {
      if (left.rank === null && right.rank === null) return left.name.localeCompare(right.name);
      if (left.rank === null) return 1;
      if (right.rank === null) return -1;
      return left.rank - right.rank;
    })
    .slice(0, 3);

const activeMissions = (missions: MissionSummary[]) =>
  missions.filter((mission) => mission.status === "active").slice(0, 2);

const latestIssues = (issues: PublicIssueListItem[]) => issues.slice(0, 3);

export function HomePage() {
  const apiHealth = useQuery({
    queryKey: ["api-health"],
    queryFn: ({ signal }) => getApiHealth(signal),
  });
  const areas = useQuery({
    queryKey: ["home-areas"],
    queryFn: ({ signal }) => getAreas(signal),
  });
  const missions = useQuery({
    queryKey: ["home-missions"],
    queryFn: ({ signal }) => getMissions(signal),
  });
  const issues = useQuery({
    queryKey: ["home-issues"],
    queryFn: ({ signal }) =>
      getPublicIssues(
        {
          page: 1,
          pageSize: 3,
          sort: "newest",
        },
        signal,
      ),
  });

  const areaItems = areas.data?.items ?? [];
  const missionItems = missions.data?.items ?? [];
  const issueItems = issues.data?.items ?? [];
  const rankedAreas = topAreas(areaItems);
  const missionPreview = activeMissions(missionItems);
  const issuePreview = latestIssues(issueItems);
  const civicHealth = average(
    areaItems.map((area) => area.civic_genome.civic_health_score),
  );
  const communityPower = average(
    areaItems.map((area) => area.civic_genome.community_power_score),
  );
  const openIssues = areaItems.reduce((total, area) => total + area.open_issues, 0);
  const resolvedThisWeek = areaItems.reduce(
    (total, area) => total + area.resolved_this_week,
    0,
  );

  return (
    <>
      <Seo
        description="Level up your neighborhood with AI-assisted civic reporting, community verification, Civic Genome scores, and community missions."
      />
      <section className="hero landing-hero landing-city-hero">
        <div className="container hero-grid">
          <div>
            <p className="eyebrow">Level Up Your Neighborhood</p>
            <h1>Your neighborhood is alive. Help it evolve.</h1>
            <p className="hero-copy">
              CivicPulse AI turns local reports, community verification, and civic
              missions into a living picture of neighborhood progress. You are not
              just filing complaints — you are helping your area get better.
            </p>
            <div className="actions">
              <Link className={buttonClassName("primary")} to="/report">
                Report an issue
              </Link>
              <Link className={buttonClassName("secondary")} to="/issues">
                Explore the live tracker
              </Link>
              <Link className={buttonClassName("ghost")} to="/neighborhoods">
                View Neighborhood Arena
              </Link>
            </div>
            <p className="hero-disclaimer">
              Independent transparency tool. Not an official government portal unless
              separately partnered with a civic authority.
            </p>
          </div>
          <Card
            as="aside"
            className="landing-pulse-card landing-city-card"
            aria-labelledby="pulse-title"
            padding="large"
          >
            <div className="city-visual" aria-hidden="true">
              <span />
              <span />
              <span />
              <span />
              <span />
            </div>
            <p className="eyebrow">Current civic pulse</p>
            <h2 id="pulse-title">A city snapshot from public CivicPulse signals.</h2>
            <dl className="status-list">
              <div>
                <dt>Civic Health</dt>
                <dd>{civicHealth === null ? "Gathering signals" : `${civicHealth}/100`}</dd>
              </div>
              <div>
                <dt>Community Power</dt>
                <dd>
                  {communityPower === null ? "Gathering signals" : `${communityPower}/100`}
                </dd>
              </div>
              <div>
                <dt>Open issues</dt>
                <dd>{areaItems.length === 0 ? "No area data yet" : openIssues}</dd>
              </div>
              <div>
                <dt>Resolved this week</dt>
                <dd>{areaItems.length === 0 ? "No area data yet" : resolvedThisWeek}</dd>
              </div>
              <div>
                <dt>System</dt>
                <dd aria-live="polite">
                  <span
                    className={`status-dot ${
                      apiHealth.isSuccess ? "status-dot-ready" : "status-dot-pending"
                    }`}
                  />
                  {apiHealth.isPending && "Checking"}
                  {apiHealth.isSuccess && "Connected"}
                  {apiHealth.isError && "Unavailable"}
                </dd>
              </div>
            </dl>
          </Card>
        </div>
      </section>

      <section className="landing-section landing-snapshot-section">
        <div className="container">
          <div className="landing-section-heading">
            <p className="eyebrow">City snapshot</p>
            <h2>One glance at how the city is moving.</h2>
            <p className="landing-lead">
              These are current CivicPulse signals from existing public reports,
              neighborhoods, and missions. No fake live data — just the latest snapshot
              the app already knows.
            </p>
          </div>
          <div className="landing-stat-grid">
            <CivicStatCard
              description="Overall area condition across neighborhoods currently tracked."
              eyebrow="Civic Health"
              icon="🏙️"
              value={civicHealth === null ? "—" : `${civicHealth}/100`}
            />
            <CivicStatCard
              description="How strongly residents are verifying, joining, and helping."
              eyebrow="Community Power"
              icon="⚡"
              tone="ai"
              value={communityPower === null ? "—" : `${communityPower}/100`}
            />
            <CivicStatCard
              description="Public reports still waiting for progress."
              eyebrow="Open Issues"
              icon="📍"
              tone={openIssues > 0 ? "warning" : "success"}
              value={areaItems.length === 0 ? "—" : openIssues}
            />
            <CivicStatCard
              description="Issues recently moved into a better state."
              eyebrow="Resolved This Week"
              icon="✓"
              tone="success"
              value={areaItems.length === 0 ? "—" : resolvedThisWeek}
            />
          </div>
        </div>
      </section>

      <section className="landing-section">
        <div className="container landing-two-column">
          <div>
            <p className="eyebrow">The feeling</p>
            <h2>This is not a complaint website. It is a neighborhood evolution loop.</h2>
          </div>
          <div className="landing-copy-stack">
            <p>
              People notice potholes, garbage piles, broken lights, water leaks, unsafe
              drains, and damaged public spaces every day. The hard part is knowing how
              to write the complaint, whether someone else already reported it, and
              whether any action followed.
            </p>
            <p>
              CivicPulse AI keeps the report public, structured, and community-verifiable
              so the issue is easier to trust and harder to lose.
            </p>
            <p>
              Then Civic Genome scores, score-change timelines, and community missions
              turn those signals into a simple question: what should this neighborhood
              do next?
            </p>
          </div>
        </div>
      </section>

      <section className="landing-section landing-section-soft">
        <div className="container">
          <div className="landing-section-heading">
            <p className="eyebrow">How it works</p>
            <h2>Report. Verify. Evolve.</h2>
          </div>
          <div className="landing-step-grid">
            {productSteps.map((step, index) => (
              <Card className="landing-step-card" key={step.title} padding="large">
                <span>{index + 1}</span>
                <h3>{step.title}</h3>
                <p>{step.copy}</p>
              </Card>
            ))}
          </div>
        </div>
      </section>

      <section className="landing-section">
        <div className="container landing-preview-grid">
          <Card className="landing-preview-card" padding="large">
            <div className="landing-preview-heading">
              <div>
                <p className="eyebrow">Neighborhood Arena</p>
                <h2>Top neighborhoods are already becoming characters.</h2>
              </div>
              <Link to="/neighborhoods">View all</Link>
            </div>
            {rankedAreas.length > 0 ? (
              <div className="landing-area-list">
                {rankedAreas.map((area) => (
                  <Link
                    className="landing-area-row"
                    key={area.id}
                    to={`/neighborhoods/${area.slug}`}
                  >
                    <span>{area.rank ? `#${area.rank}` : "New"}</span>
                    <div>
                      <strong>{area.name}</strong>
                      <small>{area.city}</small>
                    </div>
                  </Link>
                ))}
              </div>
            ) : (
              <p className="landing-muted">
                Neighborhood rankings will appear once areas have public Civic Genome signals.
              </p>
            )}
          </Card>

          <Card className="landing-preview-card" padding="large">
            <div className="landing-preview-heading">
              <div>
                <p className="eyebrow">Active community missions</p>
                <h2>Quests turn attention into action.</h2>
              </div>
              <Link to="/missions">View missions</Link>
            </div>
            {missionPreview.length > 0 ? (
              <div className="landing-mission-list">
                {missionPreview.map((mission) => {
                  const progress =
                    mission.target_count > 0
                      ? Math.round((mission.progress_count / mission.target_count) * 100)
                      : 0;
                  return (
                    <Link
                      className="landing-mission-row"
                      key={mission.id}
                      to={`/missions/${mission.id}`}
                    >
                      <div>
                        <strong>{mission.title}</strong>
                        <small>{mission.area.name}</small>
                      </div>
                      <ScoreMeter
                        label="Progress"
                        max={mission.target_count}
                        tone="community-power"
                        value={mission.progress_count}
                      />
                      <span>{progress}%</span>
                    </Link>
                  );
                })}
              </div>
            ) : (
              <p className="landing-muted">
                Active missions will appear here after admins publish community quests.
              </p>
            )}
          </Card>
        </div>
      </section>

      <section className="landing-section landing-section-soft">
        <div className="container">
          <div className="landing-section-heading">
            <GeminiLabel>AI powered by Gemini</GeminiLabel>
            <h2>AI is the civic intelligence layer, not an autopilot.</h2>
            <p className="landing-lead">
              Gemini helps structure, explain, and recommend — but citizens and admins
              stay in control of what gets published.
            </p>
          </div>
          <div className="landing-feature-grid">
            {aiFeatures.map((feature) => (
              <Card className="landing-ai-card" key={feature.title} padding="large">
                <GeminiLabel>Gemini assisted</GeminiLabel>
                <h3>{feature.title}</h3>
                <p>{feature.copy}</p>
              </Card>
            ))}
          </div>
        </div>
      </section>

      <section className="landing-section">
        <div className="container landing-two-column">
          <div>
            <p className="eyebrow">Public tracker</p>
            <h2>A living feed of what residents are seeing.</h2>
            <p className="landing-lead">
              The tracker stays useful even without maps: List View, Map View fallback,
              issue detail pages, timelines, and verification counts all remain public.
            </p>
            <div className="actions">
              <Link className={buttonClassName("primary")} to="/issues">
                Open public tracker
              </Link>
              <Link className={buttonClassName("secondary")} to="/report">
                Report a local issue
              </Link>
            </div>
          </div>
          <Card className="landing-feed-card" padding="large">
            <p className="eyebrow">Latest reports</p>
            {issuePreview.length > 0 ? (
              <div className="landing-feed-list">
                {issuePreview.map((issue) => (
                  <Link
                    className="landing-feed-row"
                    key={issue.id}
                    to={`/issues/${issue.id}`}
                  >
                    <span>{titleLabel(issue.severity)}</span>
                    <div>
                      <strong>{issue.title}</strong>
                      <small>
                        {issue.location}
                        {issue.landmark ? ` · ${issue.landmark}` : ""}
                      </small>
                    </div>
                  </Link>
                ))}
              </div>
            ) : (
              <p className="landing-muted">
                New public reports will appear here after citizens publish reviewed issues.
              </p>
            )}
          </Card>
        </div>
      </section>

      <section className="landing-section landing-final-cta">
        <div className="container narrow">
          <p className="eyebrow">Start the evolution loop</p>
          <h2>One clear report can become a public signal, a mission, and a better neighborhood.</h2>
          <p>
            Report what you see, verify what you know, and help your neighborhood move
            from unresolved problems toward visible progress.
          </p>
          <div className="actions">
            <Link className={buttonClassName("primary")} to="/report">
              Report an issue
            </Link>
            <Link className={buttonClassName("secondary")} to="/issues">
              Explore tracker
            </Link>
          </div>
        </div>
      </section>
    </>
  );
}
