from dataclasses import dataclass
from datetime import UTC, datetime

from app.domain.areas import BASELINE_AREA_SCORE, AreaScoreKey, AreaStatusLabel
from app.domain.enums import CommunityActionType, IssueCategory, IssueSeverity, IssueStatus
from app.models.issue import Issue
from app.models.mission import Mission

COMPONENT_SCORE_KEYS = (
    AreaScoreKey.INFRASTRUCTURE,
    AreaScoreKey.CLEANLINESS,
    AreaScoreKey.SAFETY,
    AreaScoreKey.PARTICIPATION,
    AreaScoreKey.RESPONSIVENESS,
    AreaScoreKey.ENVIRONMENT,
)

SCORE_WEIGHTS = {
    AreaScoreKey.INFRASTRUCTURE: 0.20,
    AreaScoreKey.CLEANLINESS: 0.15,
    AreaScoreKey.SAFETY: 0.20,
    AreaScoreKey.PARTICIPATION: 0.15,
    AreaScoreKey.RESPONSIVENESS: 0.20,
    AreaScoreKey.ENVIRONMENT: 0.10,
}

SCORE_FIELD_BY_KEY = {
    AreaScoreKey.OVERALL: "overall_score",
    AreaScoreKey.INFRASTRUCTURE: "infrastructure_score",
    AreaScoreKey.CLEANLINESS: "cleanliness_score",
    AreaScoreKey.SAFETY: "safety_score",
    AreaScoreKey.PARTICIPATION: "participation_score",
    AreaScoreKey.RESPONSIVENESS: "responsiveness_score",
    AreaScoreKey.ENVIRONMENT: "environment_score",
}

SEVERITY_PENALTIES = {
    IssueSeverity.LOW: 1,
    IssueSeverity.MEDIUM: 2,
    IssueSeverity.HIGH: 4,
    IssueSeverity.CRITICAL: 6,
}

RESOLUTION_BONUSES = {
    IssueSeverity.LOW: 1,
    IssueSeverity.MEDIUM: 2,
    IssueSeverity.HIGH: 3,
    IssueSeverity.CRITICAL: 4,
}

ACTIVE_STATUSES = {
    IssueStatus.REPORTED,
    IssueStatus.COMMUNITY_VERIFIED,
    IssueStatus.ESCALATED,
    IssueStatus.IN_PROGRESS,
}


@dataclass(frozen=True, slots=True)
class AreaScoreSnapshot:
    scores: dict[AreaScoreKey, int]
    reason: str


def clamp_score(value: float | int) -> int:
    return max(0, min(100, round(value)))


def overall_score(component_scores: dict[AreaScoreKey, int]) -> int:
    return clamp_score(
        sum(component_scores[key] * weight for key, weight in SCORE_WEIGHTS.items()),
    )


def status_label(score: int) -> AreaStatusLabel:
    if score >= 85:
        return AreaStatusLabel.THRIVING
    if score >= 70:
        return AreaStatusLabel.IMPROVING
    if score >= 55:
        return AreaStatusLabel.STABLE
    if score >= 40:
        return AreaStatusLabel.NEEDS_ATTENTION
    return AreaStatusLabel.AT_RISK


def category_score_weights(category: IssueCategory) -> dict[AreaScoreKey, float]:
    if category is IssueCategory.ROAD_DAMAGE:
        return {AreaScoreKey.INFRASTRUCTURE: 1.0, AreaScoreKey.SAFETY: 0.5}
    if category is IssueCategory.GARBAGE_WASTE:
        return {AreaScoreKey.CLEANLINESS: 1.0, AreaScoreKey.ENVIRONMENT: 0.5}
    if category is IssueCategory.STREETLIGHT:
        return {AreaScoreKey.SAFETY: 1.0, AreaScoreKey.INFRASTRUCTURE: 0.5}
    if category is IssueCategory.WATER_LEAKAGE:
        return {AreaScoreKey.ENVIRONMENT: 1.0, AreaScoreKey.INFRASTRUCTURE: 0.5}
    if category is IssueCategory.DRAINAGE_SEWAGE:
        return {AreaScoreKey.ENVIRONMENT: 1.0, AreaScoreKey.SAFETY: 0.5}
    if category is IssueCategory.PUBLIC_SAFETY:
        return {AreaScoreKey.SAFETY: 1.0}
    return {}


def issue_category_score_impact(
    category: IssueCategory,
    severity: IssueSeverity,
) -> dict[AreaScoreKey, int]:
    penalty = SEVERITY_PENALTIES[severity]
    return {
        key: max(1, round(penalty * weight))
        for key, weight in category_score_weights(category).items()
    }


def resolved_category_score_impact(
    category: IssueCategory,
    severity: IssueSeverity,
) -> dict[AreaScoreKey, int]:
    bonus = RESOLUTION_BONUSES[severity]
    return {
        key: max(1, round(bonus * weight))
        for key, weight in category_score_weights(category).items()
    }


def compute_area_score_snapshot(
    issues: list[Issue],
    *,
    completed_missions: list[Mission] | None = None,
    current_time: datetime,
) -> AreaScoreSnapshot:
    if current_time.tzinfo is None:
        current_time = current_time.replace(tzinfo=UTC)
    components = {key: BASELINE_AREA_SCORE for key in COMPONENT_SCORE_KEYS}

    for issue in issues:
        if issue.status in (IssueStatus.REJECTED, IssueStatus.DUPLICATE):
            continue

        _apply_participation_signal(components, issue)

        if issue.status is IssueStatus.RESOLVED:
            _apply_resolved_issue_signal(components, issue)
        elif issue.status in ACTIVE_STATUSES:
            _apply_active_issue_signal(components, issue, current_time=current_time)

    for mission in completed_missions or []:
        _apply_completed_mission_reward(components, mission)

    clamped_components = {key: clamp_score(value) for key, value in components.items()}
    clamped_components[AreaScoreKey.OVERALL] = overall_score(clamped_components)
    return AreaScoreSnapshot(
        scores=clamped_components,
        reason="Recalculated from current issue status, severity, age, and community activity.",
    )


def _apply_participation_signal(
    components: dict[AreaScoreKey, int],
    issue: Issue,
) -> None:
    useful_actions = [
        action
        for action in issue.community_actions
        if action.action_type
        in {
            CommunityActionType.SAW_THIS_TOO,
            CommunityActionType.STILL_UNRESOLVED,
            CommunityActionType.FIXED,
        }
    ]
    components[AreaScoreKey.PARTICIPATION] += min(len(useful_actions), 5)


def _apply_resolved_issue_signal(
    components: dict[AreaScoreKey, int],
    issue: Issue,
) -> None:
    for key, bonus in resolved_category_score_impact(issue.category, issue.severity).items():
        components[key] += bonus
    components[AreaScoreKey.RESPONSIVENESS] += 1
    if issue.severity in (IssueSeverity.HIGH, IssueSeverity.CRITICAL):
        components[AreaScoreKey.SAFETY] += 1


def _apply_active_issue_signal(
    components: dict[AreaScoreKey, int],
    issue: Issue,
    *,
    current_time: datetime,
) -> None:
    for key, penalty in issue_category_score_impact(issue.category, issue.severity).items():
        components[key] -= penalty

    created_at = issue.created_at
    if created_at.tzinfo is None:
        created_at = created_at.replace(tzinfo=UTC)
    age_days = max(0, (current_time - created_at).days)
    if age_days >= 7:
        components[AreaScoreKey.RESPONSIVENESS] -= 2
    if age_days >= 3 and issue.severity in (IssueSeverity.HIGH, IssueSeverity.CRITICAL):
        components[AreaScoreKey.RESPONSIVENESS] -= 2


def mission_reward_score_impact(mission: Mission) -> dict[AreaScoreKey, int]:
    raw_score_key = mission.reward_json.get("score_key")
    raw_points = mission.reward_json.get("points")
    if not isinstance(raw_score_key, str) or raw_score_key == AreaScoreKey.OVERALL.value:
        return {}
    if not isinstance(raw_points, int) or raw_points <= 0:
        return {}
    try:
        score_key = AreaScoreKey(raw_score_key)
    except ValueError:
        return {}
    return {score_key: min(raw_points, 20)}


def _apply_completed_mission_reward(
    components: dict[AreaScoreKey, int],
    mission: Mission,
) -> None:
    for key, points in mission_reward_score_impact(mission).items():
        components[key] += points
