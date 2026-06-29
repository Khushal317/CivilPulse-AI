import type {
  IssueCategory,
  IssueSeverity,
  IssueSort,
  IssueStatus,
} from "../../types/domain";
import {
  categoryFilterOptions,
  severityFilterOptions,
  sortOptions,
  statusFilterOptions,
} from "./constants";
import type { IssueTrackerFilters, TrackerView } from "./types";

const categories = new Set(categoryFilterOptions.map((option) => option.value));
const severities = new Set(severityFilterOptions.map((option) => option.value));
const statuses = new Set(statusFilterOptions.map((option) => option.value));
const sorts = new Set(sortOptions.map((option) => option.value));

function positiveInteger(value: string | null, fallback: number): number {
  const parsed = Number(value);
  return Number.isInteger(parsed) && parsed > 0 ? parsed : fallback;
}

export function trackerFilters(params: URLSearchParams): IssueTrackerFilters {
  const category = params.get("category") as IssueCategory | null;
  const severity = params.get("severity") as IssueSeverity | null;
  const status = params.get("status") as IssueStatus | null;
  const sort = params.get("sort") as IssueSort | null;
  const location = params.get("location")?.trim();

  return {
    page: positiveInteger(params.get("page"), 1),
    pageSize: 12,
    category: category && categories.has(category) ? category : undefined,
    severity: severity && severities.has(severity) ? severity : undefined,
    status: status && statuses.has(status) ? status : undefined,
    location: location || undefined,
    sort: sort && sorts.has(sort) ? sort : "newest",
  };
}

export function trackerView(params: URLSearchParams): TrackerView {
  return params.get("view") === "map" ? "map" : "list";
}
