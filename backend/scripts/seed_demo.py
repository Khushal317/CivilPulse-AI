from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import NAMESPACE_URL, uuid5

from PIL import Image, ImageDraw
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db.session import get_engine
from app.domain.enums import (
    CommunityActionType,
    IssueCategory,
    IssueSeverity,
    IssueStatus,
    UpdateActorType,
    UrgencyLevel,
)
from app.models.community_action import CommunityAction
from app.models.issue import Issue
from app.models.issue_update import IssueUpdate


@dataclass(frozen=True, slots=True)
class DemoIssue:
    title: str
    category: IssueCategory
    severity: IssueSeverity
    status: IssueStatus
    location: str
    landmark: str
    confirmations: int


DEMO_ISSUES = (
    DemoIssue(
        "Deep pothole beside the school crossing",
        IssueCategory.ROAD_DAMAGE,
        IssueSeverity.HIGH,
        IssueStatus.COMMUNITY_VERIFIED,
        "Sector 12",
        "City Public School",
        6,
    ),
    DemoIssue(
        "Streetlight dark for several nights",
        IssueCategory.STREETLIGHT,
        IssueSeverity.MEDIUM,
        IssueStatus.IN_PROGRESS,
        "Green Park",
        "Community playground",
        4,
    ),
    DemoIssue(
        "Overflowing waste collection point",
        IssueCategory.GARBAGE_WASTE,
        IssueSeverity.HIGH,
        IssueStatus.ESCALATED,
        "Old Market",
        "Gate 2",
        8,
    ),
    DemoIssue(
        "Water leaking across the main road",
        IssueCategory.WATER_LEAKAGE,
        IssueSeverity.CRITICAL,
        IssueStatus.COMMUNITY_VERIFIED,
        "Civil Lines",
        "District hospital",
        3,
    ),
    DemoIssue(
        "Blocked drain causing waterlogging",
        IssueCategory.DRAINAGE_SEWAGE,
        IssueSeverity.HIGH,
        IssueStatus.COMMUNITY_VERIFIED,
        "Lake View Colony",
        "Bus stop",
        7,
    ),
    DemoIssue(
        "Broken railing along pedestrian bridge",
        IssueCategory.PUBLIC_SAFETY,
        IssueSeverity.CRITICAL,
        IssueStatus.IN_PROGRESS,
        "River Road",
        "Footbridge",
        9,
    ),
    DemoIssue(
        "Uneven pavement outside health centre",
        IssueCategory.ROAD_DAMAGE,
        IssueSeverity.MEDIUM,
        IssueStatus.RESOLVED,
        "Sector 8",
        "Primary Health Centre",
        5,
    ),
    DemoIssue(
        "Garbage scattered beside neighborhood park",
        IssueCategory.GARBAGE_WASTE,
        IssueSeverity.MEDIUM,
        IssueStatus.REPORTED,
        "Shanti Nagar",
        "Central park",
        2,
    ),
    DemoIssue(
        "Flickering streetlight at busy junction",
        IssueCategory.STREETLIGHT,
        IssueSeverity.HIGH,
        IssueStatus.ESCALATED,
        "MG Road",
        "Metro entrance",
        5,
    ),
    DemoIssue(
        "Open drain cover near apartment entrance",
        IssueCategory.PUBLIC_SAFETY,
        IssueSeverity.CRITICAL,
        IssueStatus.COMMUNITY_VERIFIED,
        "Rose Garden",
        "Block C",
        11,
    ),
    DemoIssue(
        "Sewage water collecting in service lane",
        IssueCategory.DRAINAGE_SEWAGE,
        IssueSeverity.HIGH,
        IssueStatus.COMMUNITY_VERIFIED,
        "Model Town",
        "Service lane 4",
        3,
    ),
    DemoIssue(
        "Small pipeline leak near public garden",
        IssueCategory.WATER_LEAKAGE,
        IssueSeverity.LOW,
        IssueStatus.RESOLVED,
        "Nehru Enclave",
        "Public garden",
        1,
    ),
    DemoIssue(
        "Damaged road markings at roundabout",
        IssueCategory.ROAD_DAMAGE,
        IssueSeverity.LOW,
        IssueStatus.REJECTED,
        "University Road",
        "North roundabout",
        0,
    ),
    DemoIssue(
        "Abandoned construction debris on footpath",
        IssueCategory.OTHER,
        IssueSeverity.MEDIUM,
        IssueStatus.REPORTED,
        "Central Avenue",
        "Post office",
        2,
    ),
)


def create_demo_image(path: Path, number: int, issue: DemoIssue) -> None:
    if path.exists():
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    colors = ("#dcecdf", "#f4e6bf", "#dbe8f1", "#eadbd8")
    image = Image.new("RGB", (960, 600), color=colors[number % len(colors)])
    draw = ImageDraw.Draw(image)
    draw.rectangle((55, 55, 905, 545), outline="#17643c", width=8)
    draw.text((90, 100), f"CivicPulse demo report {number + 1}", fill="#173226")
    draw.text((90, 160), issue.category.value.replace("_", " ").title(), fill="#17643c")
    draw.text((90, 220), issue.location, fill="#26372f")
    image.save(path, format="PNG")


def ensure_timeline(session: Session, issue: Issue, created_at: datetime) -> None:
    existing_statuses = set(
        session.scalars(
            select(IssueUpdate.to_status).where(IssueUpdate.issue_id == issue.id),
        ).all(),
    )
    if IssueStatus.REPORTED not in existing_statuses:
        session.add(
            IssueUpdate(
                id=uuid5(NAMESPACE_URL, f"civicpulse-demo-update-{issue.id}-reported"),
                issue_id=issue.id,
                from_status=None,
                to_status=IssueStatus.REPORTED,
                note="Issue reported by a citizen.",
                actor_type=UpdateActorType.SYSTEM,
                created_at=created_at,
            ),
        )
    if issue.status is not IssueStatus.REPORTED and issue.status not in existing_statuses:
        session.add(
            IssueUpdate(
                id=uuid5(NAMESPACE_URL, f"civicpulse-demo-update-{issue.id}-{issue.status.value}"),
                issue_id=issue.id,
                from_status=IssueStatus.REPORTED,
                to_status=issue.status,
                note=f"Demo status updated to {issue.status.value.replace('_', ' ')}.",
                actor_type=UpdateActorType.SYSTEM,
                created_at=created_at + timedelta(hours=2),
            ),
        )


def seed(session: Session) -> tuple[int, int]:
    settings = get_settings()
    if settings.storage_backend != "local":
        raise RuntimeError("The demo seeder currently requires STORAGE_BACKEND=local")

    added_issues = 0
    added_actions = 0
    now = datetime.now(UTC)
    for index, sample in enumerate(DEMO_ISSUES):
        reference = f"CP-DEMO-{index + 1:04d}"
        existing = session.scalar(select(Issue).where(Issue.public_reference == reference))
        if existing is not None:
            if (
                existing.status is IssueStatus.REPORTED
                and sample.status is IssueStatus.COMMUNITY_VERIFIED
            ):
                existing.status = IssueStatus.COMMUNITY_VERIFIED
            ensure_timeline(session, existing, existing.created_at)
            continue

        image_key = f"issues/demo-{index + 1:02d}.png"
        create_demo_image(settings.local_storage_path / image_key, index, sample)
        created_at = now - timedelta(days=index, minutes=index * 7)
        issue = Issue(
            id=uuid5(NAMESPACE_URL, f"civicpulse-demo-issue-{index + 1}"),
            public_reference=reference,
            title=sample.title,
            original_description=(
                f"Residents reported: {sample.title.lower()} near {sample.landmark}."
            ),
            ai_summary=(
                f"{sample.title} has been reported in {sample.location} "
                "and requires civic review."
            ),
            category=sample.category,
            severity=sample.severity,
            urgency_level=UrgencyLevel.IMMEDIATE
            if sample.severity is IssueSeverity.CRITICAL
            else UrgencyLevel.SOON,
            urgency_reason="The issue affects regular public use of this area.",
            suggested_department="Municipal Operations",
            safety_risk="Residents may face disruption or injury until the issue is addressed.",
            citizen_explanation="This seeded report demonstrates the public tracker workflow.",
            suggested_next_action="Review the report and coordinate an on-site inspection.",
            location=sample.location,
            landmark=sample.landmark,
            image_key=image_key,
            image_mime="image/png",
            status=sample.status,
            citizen_name=None,
            citizen_contact=None,
            ai_model="demo-seed",
            prompt_version="demo-seed-v1",
            created_at=created_at,
            updated_at=created_at,
        )
        session.add(issue)
        session.flush()
        added_issues += 1

        for actor_number in range(sample.confirmations):
            session.add(
                CommunityAction(
                    id=uuid5(
                        NAMESPACE_URL, f"civicpulse-demo-action-{index + 1}-{actor_number + 1}"
                    ),
                    issue_id=issue.id,
                    action_type=CommunityActionType.SAW_THIS_TOO,
                    actor_hash=f"demo-actor-{index + 1}-{actor_number + 1}",
                    created_at=created_at + timedelta(hours=actor_number + 1),
                ),
            )
            added_actions += 1
        ensure_timeline(session, issue, created_at)

    session.commit()
    return added_issues, added_actions


def main() -> None:
    with Session(get_engine()) as session:
        issue_count, action_count = seed(session)
    print(f"Demo tracker ready: {issue_count} issues and {action_count} confirmations added.")


if __name__ == "__main__":
    main()
