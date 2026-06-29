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
import { CivicStatCard } from "../../components/ui/CivicStatCard";
import { SelectField, TextField } from "../../components/ui/FormField";
import { getPublicIssueMap, getPublicIssues } from "./api";
import {
  categoryFilterOptions,
  severityFilterOptions,
  sortOptions,
  statusFilterOptions,
} from "./constants";
import { IssueCard } from "./IssueCard";
import { IssueMapView } from "./IssueMapView";
import { trackerFilters, trackerView } from "./searchParams";
import type { TrackerView } from "./types";

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

function clearFiltersForView(view: TrackerView): URLSearchParams {
  const next = new URLSearchParams();
  if (view === "map") next.set("view", "map");
  return next;
}

export function TrackerPage() {
  const [searchParams, setSearchParams] = useSearchParams();
  const filters = useMemo(() => trackerFilters(searchParams), [searchParams]);
  const view = useMemo(() => trackerView(searchParams), [searchParams]);
  const [location, setLocation] = useState(filters.location ?? "");
  const issues = useQuery({
    queryKey: ["public-issues", filters],
    queryFn: ({ signal }) => getPublicIssues(filters, signal),
    enabled: view === "list",
    placeholderData: (previous) => previous,
  });
  const issueMap = useQuery({
    queryKey: ["public-issue-map", filters],
    queryFn: ({ signal }) => getPublicIssueMap(filters, signal),
    enabled: view === "map",
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

  function setView(nextView: TrackerView) {
    const next = new URLSearchParams(searchParams);
    if (nextView === "list") next.delete("view");
    else next.set("view", "map");
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
  const mapResult = issueMap.data;
  const currentTotal =
    view === "map" ? mapResult?.total_items : result?.total_items;
  const isUpdating =
    view === "map" ? issueMap.isFetching && Boolean(mapResult) : issues.isFetching && Boolean(result);

  return (
    <section className="page-section tracker-page">
      <Seo
        description="Browse public CivicPulse AI reports, filter by category or status, and follow issue progress."
        title="Public tracker"
      />
      <div className="container tracker-layout">
        <header className="tracker-heading">
          <div>
            <p className="eyebrow">Live tracker</p>
            <h1>Public issue tracker</h1>
            <p className="page-copy">
              A living feed of reported civic problems, community confirmations, and status
              changes. Every public issue is a signal that can help a neighborhood evolve.
            </p>
          </div>
          <Link className={buttonClassName("primary")} to="/report">
            Report an issue
          </Link>
        </header>

        <div className="tracker-signal-grid" aria-label="Tracker snapshot">
          <CivicStatCard
            description={view === "map" ? "Coordinate-ready reports in this view." : "Reports matching this view."}
            eyebrow={view === "map" ? "Mappable Signals" : "Visible Signals"}
            icon={view === "map" ? "🗺️" : "📡"}
            value={typeof currentTotal === "number" ? currentTotal : "—"}
          />
          <CivicStatCard
            description="Filters are shareable because they stay in the URL."
            eyebrow="Active Filters"
            icon="⌁"
            tone={activeFilterCount > 0 ? "warning" : "neutral"}
            value={activeFilterCount}
          />
          <CivicStatCard
            description="Use List for detail, Map for location context."
            eyebrow="Current View"
            icon={view === "map" ? "📍" : "≡"}
            tone="ai"
            value={view === "map" ? "Map" : "List"}
          />
        </div>

        <Card as="aside" className="tracker-controls" padding="large">
          <div className="tracker-filter-heading">
            <div>
              <h2>Find local civic signals</h2>
              <p>Filter the feed by category, severity, status, or neighborhood context.</p>
            </div>
            {activeFilterCount > 0 && (
              <Button
                onClick={() => setSearchParams(clearFiltersForView(view))}
                size="small"
                variant="ghost"
              >
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

        <div aria-label="Tracker view" className="tracker-view-toggle" role="tablist">
          <button
            aria-selected={view === "list"}
            className={view === "list" ? "active" : undefined}
            onClick={() => setView("list")}
            role="tab"
            type="button"
          >
            List
          </button>
          <button
            aria-selected={view === "map"}
            className={view === "map" ? "active" : undefined}
            onClick={() => setView("map")}
            role="tab"
            type="button"
          >
            Map
          </button>
        </div>

        <div className="tracker-results-heading" aria-live="polite">
          <div>
            <h2>{view === "map" ? "Issue map" : "Community reports"}</h2>
            <p>
              {typeof currentTotal === "number"
                ? `${currentTotal} ${currentTotal === 1 ? "issue" : "issues"} found`
                : "Loading current reports…"}
              {view === "map" && mapResult && mapResult.unmapped_items > 0
                ? ` · ${mapResult.unmapped_items} without coordinates`
                : ""}
            </p>
          </div>
          {isUpdating && <span>Updating…</span>}
        </div>

        {view === "list" && issues.isPending && <TrackerSkeleton />}
        {view === "list" && issues.isError && (
          <ErrorState
            description={issues.error.message}
            onRetry={() => void issues.refetch()}
            title="The public tracker could not be loaded"
          />
        )}
        {view === "list" && result && result.items.length === 0 && (
          <EmptyState
            action={
              activeFilterCount > 0 ? (
                <Button
                  onClick={() => setSearchParams(clearFiltersForView(view))}
                  variant="secondary"
                >
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
        {view === "list" && result && result.items.length > 0 && (
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

        {view === "map" && issueMap.isPending && (
          <Card className="tracker-map-preview" padding="large">
            <Skeleton height="360px" />
          </Card>
        )}
        {view === "map" && issueMap.isError && (
          <ErrorState
            description={issueMap.error.message}
            onRetry={() => void issueMap.refetch()}
            title="The map view could not be loaded"
          />
        )}
        {view === "map" && mapResult && mapResult.items.length === 0 && (
          <EmptyState
            action={
              activeFilterCount > 0 ? (
                <Button
                  onClick={() => setSearchParams(clearFiltersForView(view))}
                  variant="secondary"
                >
                  Clear filters
                </Button>
              ) : (
                <Link className={buttonClassName("primary")} to="/report">
                  Report a mappable issue
                </Link>
              )
            }
            description={
              activeFilterCount > 0
                ? "Try removing a filter or searching another location."
                : "Map markers appear after reports include coordinates from Google Places."
            }
            title={
              activeFilterCount > 0
                ? "No mappable issues match these filters"
                : "No mappable reports yet"
            }
          />
        )}
        {view === "map" && mapResult && mapResult.items.length > 0 && (
          <IssueMapView result={mapResult} />
        )}
      </div>
    </section>
  );
}
