import { useQuery } from "@tanstack/react-query";
import { type FormEvent, useEffect, useMemo, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";

import { EmptyState } from "../../components/feedback/EmptyState";
import { ErrorState } from "../../components/feedback/ErrorState";
import { Skeleton } from "../../components/feedback/Loading";
import { Seo } from "../../components/Seo";
import { Button } from "../../components/ui/Button";
import { buttonClassName } from "../../components/ui/buttonStyles";
import { Card } from "../../components/ui/Card";
import { SelectField, TextField } from "../../components/ui/FormField";
import { getPublicIssues } from "./api";
import {
  categoryFilterOptions,
  severityFilterOptions,
  sortOptions,
  statusFilterOptions,
} from "./constants";
import { IssueCard } from "./IssueCard";
import { trackerFilters } from "./searchParams";

type FilterName = "category" | "severity" | "status" | "sort";

function TrackerSkeleton() {
  return (
    <div aria-label="Loading public issues" className="issue-grid" role="status">
      {[1, 2, 3, 4, 5, 6].map((item) => (
        <Card className="issue-card issue-card-skeleton" key={item} padding="none">
          <Skeleton height="190px" />
          <div className="issue-card-body">
            <Skeleton width="70%" />
            <Skeleton height="2rem" />
            <Skeleton width="45%" />
          </div>
        </Card>
      ))}
    </div>
  );
}

export function TrackerPage() {
  const [searchParams, setSearchParams] = useSearchParams();
  const filters = useMemo(() => trackerFilters(searchParams), [searchParams]);
  const [location, setLocation] = useState(filters.location ?? "");
  const issues = useQuery({
    queryKey: ["public-issues", filters],
    queryFn: ({ signal }) => getPublicIssues(filters, signal),
    placeholderData: (previous) => previous,
  });

  useEffect(() => {
    setLocation(filters.location ?? "");
  }, [filters.location]);

  function setFilter(name: FilterName, value: string) {
    const next = new URLSearchParams(searchParams);
    if (!value || (name === "sort" && value === "newest")) next.delete(name);
    else next.set(name, value);
    next.delete("page");
    setSearchParams(next);
  }

  function submitLocation(event: FormEvent) {
    event.preventDefault();
    const next = new URLSearchParams(searchParams);
    const value = location.trim();
    if (value) next.set("location", value);
    else next.delete("location");
    next.delete("page");
    setSearchParams(next);
  }

  function setPage(page: number) {
    const next = new URLSearchParams(searchParams);
    if (page <= 1) next.delete("page");
    else next.set("page", String(page));
    setSearchParams(next);
    window.scrollTo({ behavior: "smooth", top: 0 });
  }

  const activeFilterCount = [
    filters.category,
    filters.severity,
    filters.status,
    filters.location,
    filters.sort !== "newest" ? filters.sort : undefined,
  ].filter(Boolean).length;
  const result = issues.data;

  return (
    <section className="page-section tracker-page">
      <Seo
        description="Browse public CivicPulse AI reports, filter by category or status, and follow issue progress."
        title="Public tracker"
      />
      <div className="container tracker-layout">
        <header className="tracker-heading">
          <div>
            <p className="eyebrow">Public transparency</p>
            <h1>Public issue tracker</h1>
            <p className="page-copy">
              Explore reported civic problems, see what the community has confirmed, and follow
              issues as their status changes.
            </p>
          </div>
          <Link className={buttonClassName("primary")} to="/report">
            Report an issue
          </Link>
        </header>

        <Card as="aside" className="tracker-controls" padding="large">
          <div className="tracker-filter-heading">
            <div>
              <h2>Find local issues</h2>
              <p>Filters stay in the URL, so this exact view can be bookmarked or shared.</p>
            </div>
            {activeFilterCount > 0 && (
              <Button onClick={() => setSearchParams({})} size="small" variant="ghost">
                Clear filters
              </Button>
            )}
          </div>

          <form className="tracker-search" onSubmit={submitLocation}>
            <TextField
              label="Search by location"
              onChange={(event) => setLocation(event.target.value)}
              placeholder="For example: Sector 12"
              value={location}
            />
            <Button type="submit" variant="secondary">
              Search
            </Button>
          </form>

          <div className="tracker-filter-grid">
            <SelectField
              label="Category"
              onChange={(event) => setFilter("category", event.target.value)}
              value={filters.category ?? ""}
            >
              <option value="">All categories</option>
              {categoryFilterOptions.map((option) => (
                <option key={option.value} value={option.value}>
                  {option.label}
                </option>
              ))}
            </SelectField>
            <SelectField
              label="Severity"
              onChange={(event) => setFilter("severity", event.target.value)}
              value={filters.severity ?? ""}
            >
              <option value="">All severities</option>
              {severityFilterOptions.map((option) => (
                <option key={option.value} value={option.value}>
                  {option.label}
                </option>
              ))}
            </SelectField>
            <SelectField
              label="Status"
              onChange={(event) => setFilter("status", event.target.value)}
              value={filters.status ?? ""}
            >
              <option value="">All statuses</option>
              {statusFilterOptions.map((option) => (
                <option key={option.value} value={option.value}>
                  {option.label}
                </option>
              ))}
            </SelectField>
            <SelectField
              label="Sort by"
              onChange={(event) => setFilter("sort", event.target.value)}
              value={filters.sort}
            >
              {sortOptions.map((option) => (
                <option key={option.value} value={option.value}>
                  {option.label}
                </option>
              ))}
            </SelectField>
          </div>
        </Card>

        <div className="tracker-results-heading" aria-live="polite">
          <div>
            <h2>Community reports</h2>
            <p>
              {result
                ? `${result.total_items} ${result.total_items === 1 ? "issue" : "issues"} found`
                : "Loading current reports…"}
            </p>
          </div>
          {issues.isFetching && result && <span>Updating…</span>}
        </div>

        {issues.isPending && <TrackerSkeleton />}
        {issues.isError && (
          <ErrorState
            description={issues.error.message}
            onRetry={() => void issues.refetch()}
            title="The public tracker could not be loaded"
          />
        )}
        {result && result.items.length === 0 && (
          <EmptyState
            action={
              activeFilterCount > 0 ? (
                <Button onClick={() => setSearchParams({})} variant="secondary">
                  Clear filters
                </Button>
              ) : (
                <Link className={buttonClassName("primary")} to="/report">
                  Report the first issue
                </Link>
              )
            }
            description={
              activeFilterCount > 0
                ? "Try removing a filter or searching another location."
                : "Published civic reports will appear here after citizen review."
            }
            title={activeFilterCount > 0 ? "No issues match these filters" : "No reports yet"}
          />
        )}
        {result && result.items.length > 0 && (
          <>
            <div className="issue-grid">
              {result.items.map((issue) => (
                <IssueCard issue={issue} key={issue.id} />
              ))}
            </div>
            <nav aria-label="Tracker pagination" className="tracker-pagination">
              <Button
                disabled={result.page <= 1}
                onClick={() => setPage(result.page - 1)}
                variant="secondary"
              >
                Previous
              </Button>
              <span>
                Page <strong>{result.page}</strong> of{" "}
                <strong>{Math.max(result.total_pages, 1)}</strong>
              </span>
              <Button
                disabled={result.page >= result.total_pages}
                onClick={() => setPage(result.page + 1)}
                variant="secondary"
              >
                Next
              </Button>
            </nav>
          </>
        )}
      </div>
    </section>
  );
}
