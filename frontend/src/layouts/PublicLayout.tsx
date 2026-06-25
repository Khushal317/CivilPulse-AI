import { Outlet } from "react-router-dom";

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
        <div className="container footer-inner">
          <p>Report local problems. Verify with your community. Track until resolved.</p>
          <span>Built for public transparency.</span>
        </div>
      </footer>
    </div>
  );
}

