import { isRouteErrorResponse, Link, useRouteError } from "react-router-dom";

import { ErrorState } from "../components/feedback/ErrorState";
import { buttonClassName } from "../components/ui/buttonStyles";

export function RouteErrorPage() {
  const error = useRouteError();
  const notFound = isRouteErrorResponse(error) && error.status === 404;

  return (
    <main className="page-section">
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
