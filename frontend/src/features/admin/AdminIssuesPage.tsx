import { useQuery } from "@tanstack/react-query";
import { type FormEvent, useEffect, useMemo, useState } from "react";
import { useSearchParams } from "react-router-dom";

import { EmptyState } from "../../components/feedback/EmptyState";
import { ErrorState } from "../../components/feedback/ErrorState";
import { Spinner } from "../../components/feedback/Loading";
import { Seo } from "../../components/Seo";
import { Button } from "../../components/ui/Button";
import { Card } from "../../components/ui/Card";
import { SelectField, TextField } from "../../components/ui/FormField";
import type { IssueCategory, IssueSeverity, IssueStatus } from "../../types/domain";
import {
  categoryFilterOptions,
  severityFilterOptions,
  statusFilterOptions,
} from "../issues/constants";
import { getAdminIssues } from "./api";
import { AdminIssueTable } from "./AdminIssueTable";

function positivePage(value: string | null) {
  const parsed = Number(value);
  return Number.isInteger(parsed) && parsed > 0 ? parsed : 1;
}

export function AdminIssuesPage() {
  const [params, setParams] = useSearchParams();
  const filters = useMemo(
    () => ({
      page: positivePage(params.get("page")),
      search: params.get("search")?.trim() || undefined,
      category: (params.get("category") as IssueCategory | null) ?? undefined,
      severity: (params.get("severity") as IssueSeverity | null) ?? undefined,
      status: (params.get("status") as IssueStatus | null) ?? undefined,
    }),
    [params],
  );
  const [search, setSearch] = useState(filters.search ?? "");
  const issues = useQuery({
    queryKey: ["admin-issues", filters],
    queryFn: ({ signal }) => getAdminIssues(filters, signal),
    placeholderData: (previous) => previous,
  });

  useEffect(() => setSearch(filters.search ?? ""), [filters.search]);

  function setFilter(name: string, value: string) {
    const next = new URLSearchParams(params);
    if (value) next.set(name, value);
    else next.delete(name);
    next.delete("page");
    setParams(next);
  }

  function submitSearch(event: FormEvent) {
    event.preventDefault();
    setFilter("search", search.trim());
  }

  function setPage(page: number) {
    const next = new URLSearchParams(params);
    if (page <= 1) next.delete("page");
    else next.set("page", String(page));
    setParams(next);
  }

  return (
    <section className="admin-page">
      <Seo
        description="Search, filter, and manage CivicPulse AI issue records."
        title="Admin issue queue"
      />
      <header className="admin-page-heading">
        <div>
          <p className="eyebrow">Admin issue queue</p>
          <h1>Manage reported issues</h1>
          <p>Search private records and update the official public lifecycle.</p>
        </div>
      </header>

      <Card className="admin-filters" padding="large">
        <form className="admin-search" onSubmit={submitSearch}>
          <TextField
            label="Search issues"
            onChange={(event) => setSearch(event.target.value)}
            placeholder="Title, location, or public reference"
            value={search}
          />
          <Button type="submit" variant="secondary">Search</Button>
        </form>
        <div className="admin-filter-grid">
          <SelectField
            label="Category"
            onChange={(event) => setFilter("category", event.target.value)}
            value={filters.category ?? ""}
          >
            <option value="">All categories</option>
            {categoryFilterOptions.map((option) => (
              <option key={option.value} value={option.value}>{option.label}</option>
            ))}
          </SelectField>
          <SelectField
            label="Severity"
            onChange={(event) => setFilter("severity", event.target.value)}
            value={filters.severity ?? ""}
          >
            <option value="">All severities</option>
            {severityFilterOptions.map((option) => (
              <option key={option.value} value={option.value}>{option.label}</option>
            ))}
          </SelectField>
          <SelectField
            label="Status"
            onChange={(event) => setFilter("status", event.target.value)}
            value={filters.status ?? ""}
          >
            <option value="">All statuses</option>
            {statusFilterOptions.map((option) => (
              <option key={option.value} value={option.value}>{option.label}</option>
            ))}
          </SelectField>
          <Button onClick={() => setParams({})} variant="ghost">Clear filters</Button>
        </div>
      </Card>

      {issues.isPending && <Spinner label="Loading administrator issue queue…" />}
      {issues.isError && (
        <ErrorState
          description={issues.error.message}
          onRetry={() => void issues.refetch()}
          title="The issue queue could not be loaded"
        />
      )}
      {issues.data && issues.data.items.length === 0 && (
        <EmptyState
          action={<Button onClick={() => setParams({})}>Clear filters</Button>}
          description="Try a broader search or remove a filter."
          title="No issues match this view"
        />
      )}
      {issues.data && issues.data.items.length > 0 && (
        <Card padding="large">
          <div className="admin-section-heading">
            <div>
              <h2>
                {issues.data.total_items} {issues.data.total_items === 1 ? "issue" : "issues"}
              </h2>
              <p className="admin-muted">Private contact details appear only inside an issue.</p>
            </div>
          </div>
          <AdminIssueTable issues={issues.data.items} label="Administrator issue queue" />
          <nav aria-label="Admin issue pagination" className="tracker-pagination">
            <Button
              disabled={issues.data.page <= 1}
              onClick={() => setPage(issues.data.page - 1)}
              variant="secondary"
            >Previous</Button>
            <span>Page {issues.data.page} of {Math.max(issues.data.total_pages, 1)}</span>
            <Button
              disabled={issues.data.page >= issues.data.total_pages}
              onClick={() => setPage(issues.data.page + 1)}
              variant="secondary"
            >Next</Button>
          </nav>
        </Card>
      )}
    </section>
  );
}
