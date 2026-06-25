import { Link, Outlet } from "react-router-dom";

import { AdminNavigation } from "../components/navigation/AdminNavigation";
import { SiteBrand } from "../components/navigation/SiteBrand";
import { SkipLink } from "../components/navigation/SkipLink";
import { buttonClassName } from "../components/ui/buttonStyles";

export function AdminLayout() {
  return (
    <div className="admin-shell">
      <SkipLink />
      <aside className="admin-sidebar">
        <div className="admin-brand">
          <SiteBrand />
          <span className="badge badge-neutral">Admin</span>
        </div>
        <AdminNavigation />
        <Link className={buttonClassName("ghost", "small")} to="/">
          ← Public site
        </Link>
      </aside>
      <div className="admin-main">
        <header className="admin-mobile-header">
          <SiteBrand compact />
          <span>Administration</span>
        </header>
        <main id="main-content">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
