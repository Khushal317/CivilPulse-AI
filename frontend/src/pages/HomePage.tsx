import { useQuery } from "@tanstack/react-query";
import { Link } from "react-router-dom";

import { getApiHealth } from "../api/health";
import { Seo } from "../components/Seo";
import { Card } from "../components/ui/Card";
import { buttonClassName } from "../components/ui/buttonStyles";

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
    title: "Track",
    copy: "Every issue gets a public page with a status, timeline, counts, and administrator updates.",
  },
];

const supportedCategories = [
  "Road damage",
  "Garbage / waste",
  "Streetlights",
  "Water leakage",
  "Drainage / sewage",
  "Public safety",
];

export function HomePage() {
  const apiHealth = useQuery({
    queryKey: ["api-health"],
    queryFn: ({ signal }) => getApiHealth(signal),
  });

  return (
    <>
      <Seo
        description="Report local civic problems, verify them with your community, and track transparent status updates until resolved."
      />
      <section className="hero landing-hero">
        <div className="container hero-grid">
          <div>
            <p className="eyebrow">Civic issues, made visible</p>
            <h1>Report local problems. Verify with your community. Track until resolved.</h1>
            <p className="hero-copy">
              CivicPulse AI is a public issue tracker for neighborhoods: citizens submit
              evidence, AI structures the report, the community verifies it, and everyone
              can follow the lifecycle from first report to final update.
            </p>
            <div className="actions">
              <Link className={buttonClassName("primary")} to="/report">
                Report an issue
              </Link>
              <Link className={buttonClassName("secondary")} to="/issues">
                View public tracker
              </Link>
            </div>
            <p className="hero-disclaimer">
              Independent transparency tool. Not an official government portal unless
              separately partnered with a civic authority.
            </p>
          </div>
          <Card
            as="aside"
            className="landing-pulse-card"
            aria-labelledby="pulse-title"
            padding="large"
          >
            <p className="eyebrow">Live civic loop</p>
            <h2 id="pulse-title">From scattered complaints to trackable public records.</h2>
            <dl className="status-list">
              <div>
                <dt>Report quality</dt>
                <dd>AI structured</dd>
              </div>
              <div>
                <dt>Trust signal</dt>
                <dd>Community verified</dd>
              </div>
              <div>
                <dt>Progress</dt>
                <dd>Timeline tracked</dd>
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

      <section className="landing-section">
        <div className="container landing-two-column">
          <div>
            <p className="eyebrow">The problem</p>
            <h2>Local issues disappear when reporting is scattered.</h2>
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
          </div>
        </div>
      </section>

      <section className="landing-section landing-section-soft">
        <div className="container">
          <div className="landing-section-heading">
            <p className="eyebrow">How it works</p>
            <h2>Three simple steps, one public trail.</h2>
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
        <div className="container landing-category-layout">
          <div>
            <p className="eyebrow">Supported reports</p>
            <h2>Built for common civic problems first.</h2>
            <p className="landing-lead">
              The MVP focuses on everyday local problems that need evidence, prioritization,
              and follow-through.
            </p>
          </div>
          <ul className="landing-category-list">
            {supportedCategories.map((category) => (
              <li key={category}>{category}</li>
            ))}
          </ul>
        </div>
      </section>

      <section className="landing-section landing-section-soft">
        <div className="container landing-feature-grid">
          <Card padding="large">
            <p className="eyebrow">Community verification</p>
            <h2>One report becomes stronger when neighbors confirm it.</h2>
            <p>
              Citizens can mark “I saw this too,” “Still unresolved,” “This is fixed,”
              or “Duplicate / incorrect.” Three distinct confirmations promote a report
              to Community Verified, while final resolution still requires admin review.
            </p>
          </Card>
          <Card padding="large">
            <p className="eyebrow">Transparent tracking</p>
            <h2>Statuses and notes stay visible.</h2>
            <p>
              Public issue pages show the photo, summary, category, severity, community
              counts, and a chronological timeline. Admin notes are public; private
              reporter contact details are not.
            </p>
          </Card>
        </div>
      </section>

      <section className="landing-section landing-final-cta">
        <div className="container narrow">
          <p className="eyebrow">Start with one issue</p>
          <h2>Make a local problem visible in minutes.</h2>
          <p>
            Report what you see, check what others have already shared, and help build
            a public trail that communities can actually follow.
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
