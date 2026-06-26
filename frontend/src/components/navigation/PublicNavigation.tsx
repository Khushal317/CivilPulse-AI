import { useState } from "react";
import { NavLink } from "react-router-dom";

import { Button } from "../ui/Button";

const navItems = [
  { to: "/", label: "Home", end: true },
  { to: "/report", label: "Report issue", end: false },
  { to: "/issues", label: "Public tracker", end: false },
];

export function PublicNavigation() {
  const [open, setOpen] = useState(false);

  return (
    <nav aria-label="Primary navigation" className="public-nav">
      <Button
        aria-controls="primary-navigation"
        aria-expanded={open}
        className="nav-toggle"
        onClick={() => setOpen((value) => !value)}
        size="small"
        type="button"
        variant="secondary"
      >
        Menu
      </Button>
      <ul className={open ? "nav-list nav-list-open" : "nav-list"} id="primary-navigation">
        {navItems.map((item) => (
          <li key={item.to}>
            <NavLink
              className={({ isActive }) => (isActive ? "nav-link active" : "nav-link")}
              end={item.end}
              onClick={() => setOpen(false)}
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
