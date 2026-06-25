import { Link } from "react-router-dom";

import { buttonClassName } from "../components/ui/buttonStyles";

export function NotFoundPage() {
  return (
    <section className="page-section">
      <div className="container narrow">
        <p className="eyebrow">404</p>
        <h1>That page could not be found.</h1>
        <p className="page-copy">The link may be incomplete or the page may have moved.</p>
        <Link className={buttonClassName("primary")} to="/">
          Return home
        </Link>
      </div>
    </section>
  );
}
