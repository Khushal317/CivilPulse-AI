import { Link, Outlet } from "react-router-dom";

import { PublicNavigation } from "../components/navigation/PublicNavigation";
import { SiteBrand } from "../components/navigation/SiteBrand";
import { SkipLink } from "../components/navigation/SkipLink";

export function PublicLayout() {
  return (
    <div className="app-shell">
      <SkipLink />
      <header className="site-header">
        <div className="container header-inner">
          <SiteBrand />
          <PublicNavigation />
        </div>
      </header>
      <main id="main-content">
        <Outlet />
      </main>
      <footer className="site-footer">
        <div className="container footer-grid">
          <div>
            <SiteBrand />
            <p>
              Level up your neighborhood with AI-assisted reports, community
              verification, Civic Genome scores, and local missions.
            </p>
          </div>
          <nav aria-label="Footer navigation">
            <Link to="/report">Report an issue</Link>
            <Link to="/issues">Live tracker</Link>
            <Link to="/neighborhoods">Neighborhood Arena</Link>
            <Link to="/rankings">Rankings</Link>
            <Link to="/missions">Community Missions</Link>
            <Link to="/admin">Admin</Link>
          </nav>
          <p className="footer-disclaimer">
            CivicPulse AI is an independent transparency tool. It does not
            claim an official government partnership unless one is explicitly
            announced by the relevant authority.
          </p>
        </div>
      </footer>
    </div>
  );
}
