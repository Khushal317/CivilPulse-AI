import { NavLink, Outlet } from "react-router-dom";

const navItems = [
  { to: "/", label: "Home" },
  { to: "/report", label: "Report issue" },
  { to: "/issues", label: "Public tracker" },
];

export function AppLayout() {
  return (
    <div className="app-shell">
      <header className="site-header">
        <div className="container header-inner">
          <NavLink className="brand" to="/" aria-label="CivicPulse AI home">
            <span className="brand-mark" aria-hidden="true">
              CP
            </span>
            <span>CivicPulse AI</span>
          </NavLink>
          <nav aria-label="Primary navigation">
            <ul className="nav-list">
              {navItems.map((item) => (
                <li key={item.to}>
                  <NavLink
                    className={({ isActive }) => (isActive ? "nav-link active" : "nav-link")}
                    to={item.to}
                  >
                    {item.label}
                  </NavLink>
                </li>
              ))}
            </ul>
          </nav>
        </div>
      </header>
      <main>
        <Outlet />
      </main>
      <footer className="site-footer">
        <div className="container">
          <p>Report local problems. Verify with your community. Track until resolved.</p>
        </div>
      </footer>
    </div>
  );
}

