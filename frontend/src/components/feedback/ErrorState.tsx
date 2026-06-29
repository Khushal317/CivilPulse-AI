import { Button } from "../ui/Button";
import { Card } from "../ui/Card";

interface ErrorStateProps {
  description?: string;
  onRetry?: () => void;
  title?: string;
}

export function ErrorState({
  description = "Please try again. If the problem continues, return to the previous page.",
  onRetry,
  title = "Something went wrong",
}: ErrorStateProps) {
  return (
    <Card className="state-card state-card-error" padding="large" role="alert">
      <span className="state-icon" aria-hidden="true">
        !
      </span>
      <div className="state-copy">
        <h2>{title}</h2>
        <p>{description}</p>
      </div>
      {onRetry && (
        <div className="state-action">
          <Button onClick={onRetry}>Try again</Button>
        </div>
      )}
    </Card>
  );
}
