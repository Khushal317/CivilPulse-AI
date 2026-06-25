import { useQuery } from "@tanstack/react-query";
import { Link } from "react-router-dom";

import { getApiHealth } from "../api/health";
import { Card } from "../components/ui/Card";
import { buttonClassName } from "../components/ui/buttonStyles";

export function HomePage() {
  const apiHealth = useQuery({
    queryKey: ["api-health"],
    queryFn: ({ signal }) => getApiHealth(signal),
  });

  return (
    <section className="hero">
      <div className="container hero-grid">
        <div>
          <p className="eyebrow">Civic issues, made visible</p>
          <h1>Your city has problems. Now they can’t disappear.</h1>
          <p className="hero-copy">
            CivicPulse AI turns local reports into clear, community-verified issues that can be
            tracked from first report to resolution.
          </p>
          <div className="actions">
            <Link className={buttonClassName("primary")} to="/report">
              Report an issue
            </Link>
            <Link className={buttonClassName("secondary")} to="/issues">
              View public tracker
            </Link>
          </div>
        </div>
        <Card
          as="aside"
          className="foundation-card"
          aria-labelledby="foundation-title"
          padding="large"
        >
          <p className="eyebrow">Foundation status</p>
          <h2 id="foundation-title">The product core is connected.</h2>
          <dl className="status-list">
            <div>
              <dt>Web app</dt>
              <dd>
                <span className="status-dot status-dot-ready" /> Ready
              </dd>
            </div>
            <div>
              <dt>FastAPI</dt>
              <dd aria-live="polite">
                <span
                  className={`status-dot ${
                    apiHealth.isSuccess ? "status-dot-ready" : "status-dot-pending"
                  }`}
                />
                {apiHealth.isPending && "Checking…"}
                {apiHealth.isSuccess && `Connected · v${apiHealth.data.version}`}
                {apiHealth.isError && "Unavailable"}
              </dd>
            </div>
            <div>
              <dt>Current phase</dt>
              <dd>Phase 4 · AI-assisted reporting</dd>
            </div>
          </dl>
        </Card>
      </div>
    </section>
  );
}
