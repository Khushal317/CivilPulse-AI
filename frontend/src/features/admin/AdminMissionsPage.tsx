import { Link } from "react-router-dom";

import { Seo } from "../../components/Seo";
import { buttonClassName } from "../../components/ui/buttonStyles";
import { MissionGeneratorPanel } from "./MissionGeneratorPanel";

export function AdminMissionsPage() {
  return (
    <section className="admin-page">
      <Seo
        description="Protected CivicPulse AI administrator console for community mission drafting, review, publishing, and lifecycle controls."
        title="Civic Mission Console"
      />
      <header className="admin-page-heading">
        <div>
          <p className="eyebrow">Community missions</p>
          <h1>Civic Mission Console</h1>
          <p>
            Create, refine, review, publish, and retire community missions without
            crowding the administrator overview.
          </p>
        </div>
        <Link className={buttonClassName("secondary")} to="/admin">
          ← Back to overview
        </Link>
      </header>

      <MissionGeneratorPanel />
    </section>
  );
}
