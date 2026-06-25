import { NavLink } from "react-router-dom";

export function SiteBrand({ compact = false }: { compact?: boolean }) {
  return (
    <NavLink className="brand" to="/" aria-label="CivicPulse AI home">
      <span className="brand-mark" aria-hidden="true">
        CP
      </span>
      {!compact && <span>CivicPulse AI</span>}
    </NavLink>
  );
}

