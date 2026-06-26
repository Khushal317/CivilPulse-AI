import { Link } from "react-router-dom";

import { CategoryBadge, SeverityBadge, StatusBadge } from "../../components/ui/Badge";
import type { AdminIssueSummary } from "./types";

const dateFormatter = new Intl.DateTimeFormat(undefined, {
  day: "numeric",
  month: "short",
  year: "numeric",
});

export function AdminIssueTable({
  issues,
  label,
}: {
  issues: AdminIssueSummary[];
  label: string;
}) {
  return (
    <div className="admin-table-wrap">
      <table className="admin-table">
        <caption className="sr-only">{label}</caption>
        <thead>
          <tr>
            <th scope="col">Issue</th>
            <th scope="col">Category</th>
            <th scope="col">Severity</th>
            <th scope="col">Status</th>
            <th scope="col">Confirmed</th>
            <th scope="col">Reported</th>
          </tr>
        </thead>
        <tbody>
          {issues.map((issue) => (
            <tr key={issue.id}>
              <td>
                <Link to={`/admin/issues/${issue.id}`}>{issue.title}</Link>
                <span>{issue.public_reference} · {issue.location}</span>
              </td>
              <td><CategoryBadge category={issue.category} /></td>
              <td><SeverityBadge severity={issue.severity} /></td>
              <td><StatusBadge status={issue.status} /></td>
              <td>{issue.verification_count}</td>
              <td>{dateFormatter.format(new Date(issue.created_at))}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
