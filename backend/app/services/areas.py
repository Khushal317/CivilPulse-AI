from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Protocol
from uuid import UUID

from app.core.errors import AppError
from app.domain.areas import AreaScoreKey
from app.domain.enums import IssueStatus
from app.models.area import Area
from app.models.area_score_event import AreaScoreEvent
from app.models.issue import Issue
from app.repositories.areas import AreaRecord, AreaRepository
from app.schemas.areas import (
    AreaActiveIssueResponse,
    AreaDetail,
    AreaListResponse,
    AreaScoreBreakdown,
    AreaScoreEventResponse,
    AreaSummary,
)
from app.services.area_scores import (
    SCORE_FIELD_BY_KEY,
    AreaScoreSnapshot,
    compute_area_score_snapshot,
    status_label,
)

ISSUE_TRIGGER_REASONS = {
    "issue_published": "Issue published by a citizen and included in Civic Genome scoring.",
    "community_action_saw_this_too": (
        "Community confirmation accepted and included in Civic Genome scoring."
    ),
    "community_action_still_unresolved": (
        "Community unresolved signal accepted and included in Civic Genome scoring."
    ),
    "community_action_fixed": (
        "Community fixed signal accepted and included in Civic Genome scoring."
    ),
    "admin_resolved": "Administrator marked the issue resolved and updated Civic Genome scoring.",
    "admin_rejected": (
        "Administrator rejected the issue and removed it from Civic Genome scoring."
    ),
    "admin_restored": "Administrator restored the issue and returned it to Civic Genome scoring.",
}


def now_utc() -> datetime:
    return datetime.now(UTC)


def scores(area: Area) -> AreaScoreBreakdown:
    return AreaScoreBreakdown(
        overall=area.overall_score,
        infrastructure=area.infrastructure_score,
        cleanliness=area.cleanliness_score,
        safety=area.safety_score,
        participation=area.participation_score,
        responsiveness=area.responsiveness_score,
        environment=area.environment_score,
    )


def summary(record: AreaRecord) -> AreaSummary:
    area = record.area
    return AreaSummary(
        id=area.id,
        name=area.name,
        slug=area.slug,
        city=area.city,
        rank=area.rank,
        status_label=area.status_label,
        scores=scores(area),
        open_issues=record.open_issues,
        resolved_this_week=record.resolved_this_week,
        active_missions=record.active_missions,
        created_at=area.created_at,
        updated_at=area.updated_at,
    )


def event_response(event: AreaScoreEvent) -> AreaScoreEventResponse:
    return AreaScoreEventResponse.model_validate(event)


def active_issue_response(issue: Issue) -> AreaActiveIssueResponse:
    return AreaActiveIssueResponse(
        id=issue.id,
        public_reference=issue.public_reference,
        title=issue.title,
        category=issue.category,
        severity=issue.severity,
        status=issue.status,
        location=issue.location,
        landmark=issue.landmark,
        updated_at=issue.updated_at,
    )


class AreaScoreTrigger(Protocol):
    def recalculate_issue_area(
        self,
        issue: Issue,
        *,
        event_type: str,
    ) -> AreaSummary | None: ...


@dataclass(slots=True)
class AreaService:
    repository: AreaRepository

    def list_public(self) -> AreaListResponse:
        records = self.repository.list_public(resolved_since=now_utc() - timedelta(days=7))
        return AreaListResponse(items=[summary(record) for record in records])

    def get_public_detail(self, slug: str) -> AreaDetail:
        record = self.repository.get_by_slug(
            slug,
            resolved_since=now_utc() - timedelta(days=7),
        )
        if record is None:
            raise AppError(
                code="area_not_found",
                message="The neighborhood area was not found.",
                status_code=404,
        )
        item = summary(record)
        return AreaDetail(
            **item.model_dump(),
            total_issues=record.total_issues,
            recent_score_events=[
                event_response(event) for event in record.recent_score_events or []
            ],
            active_issues=[active_issue_response(issue) for issue in record.active_issues or []],
        )

    def recalculate_issue_area(
        self,
        issue: Issue,
        *,
        event_type: str,
    ) -> AreaSummary | None:
        if issue.area_id is None:
            return None
        return self.recalculate_area_scores(
            issue.area_id,
            event_type=event_type,
            related_issue_id=issue.id,
            reason=ISSUE_TRIGGER_REASONS.get(event_type),
        )

    def recalculate_area_scores(
        self,
        area_id: UUID,
        *,
        event_type: str = "score_recalculated",
        related_issue_id: UUID | None = None,
        related_mission_id: UUID | None = None,
        reason: str | None = None,
    ) -> AreaSummary:
        area = self.repository.get_for_score_recalculation(area_id)
        if area is None:
            raise AppError(
                code="area_not_found",
                message="The neighborhood area was not found.",
                status_code=404,
            )
        current_time = now_utc()
        self._apply_score_snapshot(
            area,
            compute_area_score_snapshot(area.issues, current_time=current_time),
            event_type=event_type,
            related_issue_id=related_issue_id,
            related_mission_id=related_mission_id,
            reason=reason,
        )
        self.recalculate_ranks(self.repository.list_for_score_recalculation())
        self.repository.flush()
        return summary(
            AreaRecord(
                area=area,
                open_issues=open_issue_count(area.issues),
                resolved_this_week=resolved_issue_count(
                    area.issues,
                    resolved_since=current_time - timedelta(days=7),
                ),
                total_issues=len(area.issues),
            ),
        )

    def recalculate_all_scores(self) -> int:
        areas = self.repository.list_for_score_recalculation()
        for area in areas:
            self._apply_score_snapshot(
                area,
                compute_area_score_snapshot(area.issues, current_time=now_utc()),
            )
        self.recalculate_ranks(areas)
        self.repository.flush()
        return len(areas)

    @staticmethod
    def recalculate_ranks(areas: list[Area]) -> None:
        ranked = sorted(
            areas,
            key=lambda area: (-area.overall_score, area.name.lower(), str(area.id)),
        )
        for index, area in enumerate(ranked, start=1):
            area.rank = index

    def _apply_score_snapshot(
        self,
        area: Area,
        snapshot: AreaScoreSnapshot,
        *,
        event_type: str = "score_recalculated",
        related_issue_id: UUID | None = None,
        related_mission_id: UUID | None = None,
        reason: str | None = None,
    ) -> None:
        for key, field_name in SCORE_FIELD_BY_KEY.items():
            new_score = snapshot.scores[key]
            previous_score = getattr(area, field_name)
            if previous_score == new_score:
                continue
            setattr(area, field_name, new_score)
            self.repository.add_score_event(
                AreaScoreEvent(
                    area_id=area.id,
                    event_type=event_type,
                    related_issue_id=related_issue_id,
                    related_mission_id=related_mission_id,
                    score_key=key,
                    score_change=new_score - previous_score,
                    previous_score=previous_score,
                    new_score=new_score,
                    reason=reason or snapshot.reason,
                ),
            )
        area.status_label = status_label(snapshot.scores[AreaScoreKey.OVERALL]).value
        area.updated_at = now_utc()


def open_issue_count(issues: list[Issue]) -> int:
    return sum(
        1
        for issue in issues
        if issue.status not in (IssueStatus.RESOLVED, IssueStatus.REJECTED)
    )


def resolved_issue_count(issues: list[Issue], *, resolved_since: datetime) -> int:
    return sum(
        1
        for issue in issues
        if issue.status is IssueStatus.RESOLVED and issue.updated_at >= resolved_since
    )
