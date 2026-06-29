import { CategoryBadge, SeverityBadge, StatusBadge } from "../../components/ui/Badge";
import { Card } from "../../components/ui/Card";
import { Link } from "react-router-dom";
import { publicIssueImageUrl } from "./api";
import type { PublicIssueListItem } from "./types";

const dateFormatter = new Intl.DateTimeFormat(undefined, {
  day: "numeric",
  month: "short",
  year: "numeric",
});

export function IssueCard({ issue }: { issue: PublicIssueListItem }) {
  return (
    <Card as="article" className="issue-card" padding="none">
      <img
        alt={`Reported civic issue: ${issue.title}`}
        className="issue-card-image"
        loading="lazy"
        src={publicIssueImageUrl(issue.image_url)}
      />
      <div className="issue-card-body">
        <div className="issue-card-badges">
          <CategoryBadge category={issue.category} />
          <SeverityBadge severity={issue.severity} />
          <StatusBadge status={issue.status} />
        </div>
        <div>
          <p className="issue-reference">{issue.public_reference}</p>
          <h2>
            <Link to={`/issues/${issue.id}`}>{issue.title}</Link>
          </h2>
          <p className="issue-location">
            {issue.location}
            {issue.landmark ? ` · ${issue.landmark}` : ""}
          </p>
        </div>
        <div className="issue-card-signal">
          <strong>Public signal</strong>
          <span>
            {issue.verification_count > 0
              ? `${issue.verification_count} community confirmation${
                  issue.verification_count === 1 ? "" : "s"
                }`
              : "Waiting for community verification"}
          </span>
        </div>
        <dl className="issue-card-meta">
          <div>
            <dt>Community confirmations</dt>
            <dd>{issue.verification_count}</dd>
          </div>
          <div>
            <dt>Reported</dt>
            <dd>{dateFormatter.format(new Date(issue.created_at))}</dd>
          </div>
        </dl>
      </div>
    </Card>
  );
}
