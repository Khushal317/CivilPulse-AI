from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from math import ceil
from uuid import UUID

from app.core.config import Settings
from app.core.errors import AppError
from app.domain.enums import CommunityActionType, IssueStatus, UpdateActorType
from app.models.issue import Issue
from app.models.issue_update import IssueUpdate
from app.repositories.issues import IssueRepository
from app.schemas.issues import (
    CommunityActionResponse,
    CommunityCounts,
    IssueListItem,
    IssueListQuery,
    IssueListResponse,
    IssuePublicDetail,
    IssueUpdatePublic,
)
from app.services.areas import AreaScoreTrigger


def image_url(key: str) -> str:
    return f"/api/v1/media/{key}"


def now_utc() -> datetime:
    return datetime.now(UTC)


def _community_counts(values: dict[CommunityActionType, int]) -> CommunityCounts:
    return CommunityCounts(
        saw_this_too=values.get(CommunityActionType.SAW_THIS_TOO, 0),
        still_unresolved=values.get(CommunityActionType.STILL_UNRESOLVED, 0),
        fixed=values.get(CommunityActionType.FIXED, 0),
        incorrect=values.get(CommunityActionType.INCORRECT, 0),
    )


SCORE_TRIGGER_ACTIONS = {
    CommunityActionType.SAW_THIS_TOO,
    CommunityActionType.STILL_UNRESOLVED,
    CommunityActionType.FIXED,
}


@dataclass(slots=True)
class IssueService:
    repository: IssueRepository
    settings: Settings
    area_score_trigger: AreaScoreTrigger | None = None

    def list_public(self, query: IssueListQuery) -> IssueListResponse:
        records, total_items = self.repository.list_public(query)
        return IssueListResponse(
            items=[
                IssueListItem(
                    id=record.issue.id,
                    public_reference=record.issue.public_reference,
                    title=record.issue.title,
                    category=record.issue.category,
                    severity=record.issue.severity,
                    location=record.issue.location,
                    landmark=record.issue.landmark,
                    image_url=image_url(record.issue.image_key),
                    status=record.issue.status,
                    created_at=record.issue.created_at,
                    updated_at=record.issue.updated_at,
                    verification_count=record.verification_count,
                )
                for record in records
            ],
            page=query.page,
            page_size=query.page_size,
            total_items=total_items,
            total_pages=ceil(total_items / query.page_size) if total_items else 0,
        )

    def get_public_detail(self, issue_id: UUID, actor_hash: str) -> IssuePublicDetail:
        issue = self.repository.get_public_detail(issue_id)
        if issue is None:
            raise AppError(
                code="issue_not_found",
                message="The public issue was not found.",
                status_code=404,
            )
        return self._detail_response(issue, actor_hash)

    def submit_community_action(
        self,
        issue_id: UUID,
        action_type: CommunityActionType,
        actor_hash: str,
    ) -> CommunityActionResponse:
        issue = self.repository.get_for_update(issue_id)
        if issue is None:
            raise AppError(
                code="issue_not_found",
                message="The public issue was not found.",
                status_code=404,
            )
        if issue.status is IssueStatus.REJECTED:
            raise AppError(
                code="community_actions_unavailable",
                message="Community actions are unavailable for rejected issues.",
                status_code=409,
            )

        existing_actions = self.repository.viewer_actions(issue_id, actor_hash)
        if action_type in existing_actions:
            return self._action_response(issue, action_type, actor_hash, accepted=False)

        window_start = now_utc() - timedelta(
            minutes=self.settings.community_action_rate_window_minutes,
        )
        if (
            self.repository.count_actor_actions_since(actor_hash, window_start)
            >= self.settings.community_action_rate_limit
        ):
            raise AppError(
                code="community_action_rate_limited",
                message="Too many community actions were submitted. Please try again later.",
                status_code=429,
            )

        accepted = self.repository.add_action_if_absent(issue_id, action_type, actor_hash)
        if accepted:
            if (
                action_type is CommunityActionType.SAW_THIS_TOO
                and issue.status is IssueStatus.REPORTED
            ):
                confirmations = self.repository.community_counts(issue_id).get(
                    CommunityActionType.SAW_THIS_TOO,
                    0,
                )
                if confirmations >= 3:
                    issue.status = IssueStatus.COMMUNITY_VERIFIED
                    self.repository.add_update(
                        IssueUpdate(
                            issue_id=issue.id,
                            from_status=IssueStatus.REPORTED,
                            to_status=IssueStatus.COMMUNITY_VERIFIED,
                            note=(
                                "Automatically promoted after three distinct community "
                                "confirmations."
                            ),
                            actor_type=UpdateActorType.SYSTEM,
                        ),
                    )
                    self.repository.flush()
            if action_type in SCORE_TRIGGER_ACTIONS:
                self._recalculate_issue_area(
                    issue,
                    event_type=f"community_action_{action_type.value}",
                )

        return self._action_response(issue, action_type, actor_hash, accepted=accepted)

    def _action_response(
        self,
        issue: Issue,
        action_type: CommunityActionType,
        actor_hash: str,
        *,
        accepted: bool,
    ) -> CommunityActionResponse:
        return CommunityActionResponse(
            action_type=action_type,
            accepted=accepted,
            issue_status=issue.status,
            community_counts=_community_counts(self.repository.community_counts(issue.id)),
            viewer_actions=self.repository.viewer_actions(issue.id, actor_hash),
        )

    def _recalculate_issue_area(self, issue: Issue, *, event_type: str) -> None:
        if self.area_score_trigger is not None:
            self.area_score_trigger.recalculate_issue_area(issue, event_type=event_type)

    def _detail_response(self, issue: Issue, actor_hash: str) -> IssuePublicDetail:
        counts = _community_counts(self.repository.community_counts(issue.id))
        return IssuePublicDetail(
            id=issue.id,
            public_reference=issue.public_reference,
            title=issue.title,
            original_description=issue.original_description,
            ai_summary=issue.ai_summary,
            category=issue.category,
            severity=issue.severity,
            urgency_level=issue.urgency_level,
            urgency_reason=issue.urgency_reason,
            suggested_department=issue.suggested_department,
            safety_risk=issue.safety_risk,
            citizen_explanation=issue.citizen_explanation,
            suggested_next_action=issue.suggested_next_action,
            location=issue.location,
            landmark=issue.landmark,
            image_url=image_url(issue.image_key),
            status=issue.status,
            created_at=issue.created_at,
            updated_at=issue.updated_at,
            verification_count=counts.saw_this_too,
            community_counts=counts,
            updates=[
                IssueUpdatePublic.model_validate(update)
                for update in sorted(issue.updates, key=lambda item: item.created_at)
            ],
            viewer_actions=self.repository.viewer_actions(issue.id, actor_hash),
        )
