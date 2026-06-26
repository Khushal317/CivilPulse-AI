import { isRouteErrorResponse, Link, useRouteError } from "react-router-dom";

import { Seo } from "../components/Seo";
import { ErrorState } from "../components/feedback/ErrorState";
import { buttonClassName } from "../components/ui/buttonStyles";

export function RouteErrorPage() {
  const error = useRouteError();
  const notFound = isRouteErrorResponse(error) && error.status === 404;

  return (
    <main className="page-section">
      <Seo
        description="CivicPulse AI could not load this page. Return home or try again."
        title={notFound ? "Page not found" : "Page unavailable"}
      />
      <div className="container narrow">
        <ErrorState
          description={
            notFound
              ? "The link may be incomplete or the page may have moved."
              : "This page could not be loaded. Return home and try again."
          }
          title={notFound ? "That page could not be found" : "This page is unavailable"}
        />
        <div className="state-followup">
          <Link className={buttonClassName("secondary")} to="/">
            Return home
          </Link>
        </div>
      </div>
    </main>
  );
}
