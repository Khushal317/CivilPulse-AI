import { NavLink } from "react-router-dom";

const adminItems = [
  { to: "/admin", label: "Overview", end: true },
  { to: "/admin/issues", label: "Issues", end: false },
];

export function AdminNavigation() {
  return (
    <nav aria-label="Admin navigation">
      <ul className="admin-nav-list">
        {adminItems.map((item) => (
          <li key={item.to}>
            <NavLink
              className={({ isActive }) =>
                isActive ? "admin-nav-link active" : "admin-nav-link"
              }
              end={item.end}
              to={item.to}
            >
              {item.label}
            </NavLink>
          </li>
        ))}
      </ul>
    </nav>
  );
}

