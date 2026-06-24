import { useQuery } from "@tanstack/react-query";
import { Link } from "react-router-dom";

import { getApiReadiness } from "../api/health";

export function HomePage() {
  const readiness = useQuery({
    queryKey: ["api-readiness"],
    queryFn: ({ signal }) => getApiReadiness(signal),
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
            <Link className="button button-primary" to="/report">
              Report an issue
            </Link>
            <Link className="button button-secondary" to="/issues">
              View public tracker
            </Link>
          </div>
        </div>
        <aside className="foundation-card" aria-labelledby="foundation-title">
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
                    readiness.isSuccess ? "status-dot-ready" : "status-dot-pending"
                  }`}
                />
                {readiness.isPending && "Checking…"}
                {readiness.isSuccess && `Connected · v${readiness.data.version}`}
                {readiness.isError && "Unavailable"}
              </dd>
            </div>
            <div>
              <dt>Current phase</dt>
              <dd>Phase 1 · Foundation</dd>
            </div>
          </dl>
        </aside>
      </div>
    </section>
  );
}

