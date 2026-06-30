from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import NAMESPACE_URL, UUID, uuid5

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
from app.models.area import Area
from app.models.community_action import CommunityAction
from app.models.issue import Issue
from app.models.issue_update import IssueUpdate
from app.models.mission import Mission
from app.repositories.areas import SQLAlchemyAreaRepository, get_or_create_area_for_location
from app.services.areas import AreaService


@dataclass(frozen=True, slots=True)
class DemoIssue:
    title: str
    category: IssueCategory
    severity: IssueSeverity
    status: IssueStatus
    location: str
    landmark: str
    latitude: float
    longitude: float
    confirmations: int
    department: str
    description: str


DEMO_ISSUES = (
    DemoIssue(
        "Damaged road surface near World Trade Park",
        IssueCategory.ROAD_DAMAGE,
        IssueSeverity.HIGH,
        IssueStatus.COMMUNITY_VERIFIED,
        "Malviya Nagar",
        "World Trade Park, JLN Marg",
        26.8530,
        75.8056,
        7,
        "Jaipur Development Authority / Road Maintenance",
        "Commuters reported broken road patches and rough edges near the World Trade Park "
        "service lane.",
    ),
    DemoIssue(
        "Streetlights flickering around Jawahar Circle",
        IssueCategory.STREETLIGHT,
        IssueSeverity.MEDIUM,
        IssueStatus.IN_PROGRESS,
        "Jawahar Circle",
        "Patrika Gate walking track",
        26.8427,
        75.8034,
        5,
        "Municipal Lighting",
        "Evening walkers reported multiple flickering lights around the Jawahar Circle "
        "walking track.",
    ),
    DemoIssue(
        "Overflowing waste bins outside City Park",
        IssueCategory.GARBAGE_WASTE,
        IssueSeverity.HIGH,
        IssueStatus.ESCALATED,
        "Mansarovar",
        "City Park entrance",
        26.8498,
        75.7515,
        8,
        "Sanitation Department",
        "Residents reported overflowing bins and scattered waste near the City Park entrance.",
    ),
    DemoIssue(
        "Water leaking across the footpath near Statue Circle",
        IssueCategory.WATER_LEAKAGE,
        IssueSeverity.HIGH,
        IssueStatus.IN_PROGRESS,
        "C-Scheme",
        "Statue Circle",
        26.9056,
        75.8064,
        6,
        "Water Department",
        "Office commuters reported a visible water leak spreading across the footpath near "
        "Statue Circle.",
    ),
    DemoIssue(
        "Blocked drain causing waterlogging in market lane",
        IssueCategory.DRAINAGE_SEWAGE,
        IssueSeverity.HIGH,
        IssueStatus.COMMUNITY_VERIFIED,
        "Bapu Bazaar",
        "Bapu Bazaar main lane",
        26.9207,
        75.8257,
        9,
        "Drainage / Sewage Department",
        "Shopkeepers reported waterlogging from a blocked drain in a busy Bapu Bazaar lane.",
    ),
    DemoIssue(
        "Broken pedestrian railing near metro approach",
        IssueCategory.PUBLIC_SAFETY,
        IssueSeverity.CRITICAL,
        IssueStatus.IN_PROGRESS,
        "Civil Lines",
        "Civil Lines Metro Station approach",
        26.9060,
        75.7823,
        9,
        "Public Works / Public Safety",
        "Pedestrians reported a broken railing near the Civil Lines metro approach.",
    ),
    DemoIssue(
        "Uneven footpath outside Mall of Jaipur",
        IssueCategory.ROAD_DAMAGE,
        IssueSeverity.MEDIUM,
        IssueStatus.RESOLVED,
        "Vaishali Nagar",
        "Mall of Jaipur, Gandhi Path",
        26.9124,
        75.7432,
        5,
        "Public Works / Footpath Maintenance",
        "Residents reported uneven paving stones outside Mall of Jaipur that made walking "
        "difficult.",
    ),
    DemoIssue(
        "Garbage scattered near Govind Marg bus stop",
        IssueCategory.GARBAGE_WASTE,
        IssueSeverity.MEDIUM,
        IssueStatus.REPORTED,
        "Raja Park",
        "Govind Marg bus stop",
        26.8960,
        75.8276,
        2,
        "Sanitation Department",
        "Commuters reported loose garbage collecting near the Govind Marg bus stop.",
    ),
    DemoIssue(
        "Streetlight outage outside SMS Hospital side road",
        IssueCategory.STREETLIGHT,
        IssueSeverity.HIGH,
        IssueStatus.ESCALATED,
        "Sawai Ram Singh Road",
        "Sawai Man Singh Hospital",
        26.9028,
        75.8166,
        5,
        "Municipal Lighting",
        "Visitors reported a dark side road outside SMS Hospital during evening hours.",
    ),
    DemoIssue(
        "Open drain cover near Jagatpura station road",
        IssueCategory.PUBLIC_SAFETY,
        IssueSeverity.CRITICAL,
        IssueStatus.COMMUNITY_VERIFIED,
        "Jagatpura",
        "Jagatpura Railway Station road",
        26.8324,
        75.8422,
        11,
        "Public Works / Public Safety",
        "Residents reported an open drain cover on the station approach road in Jagatpura.",
    ),
    DemoIssue(
        "Sewage water collecting near Jal Mahal promenade",
        IssueCategory.DRAINAGE_SEWAGE,
        IssueSeverity.HIGH,
        IssueStatus.COMMUNITY_VERIFIED,
        "Amer Road",
        "Jal Mahal promenade",
        26.9535,
        75.8464,
        4,
        "Drainage / Sewage Department",
        "Visitors reported sewage water collecting near the public walkway by Jal Mahal.",
    ),
    DemoIssue(
        "Small pipeline leak near Durgapura bus stop",
        IssueCategory.WATER_LEAKAGE,
        IssueSeverity.LOW,
        IssueStatus.RESOLVED,
        "Tonk Road",
        "Durgapura bus stop",
        26.8467,
        75.7936,
        1,
        "Water Department",
        "A small roadside pipeline leak was reported near the Durgapura bus stop.",
    ),
    DemoIssue(
        "Damaged road markings near Jawahar Kala Kendra",
        IssueCategory.ROAD_DAMAGE,
        IssueSeverity.LOW,
        IssueStatus.REJECTED,
        "JLN Marg",
        "Jawahar Kala Kendra junction",
        26.8644,
        75.8100,
        0,
        "Traffic Engineering / Road Marking",
        "A citizen reported faded markings near Jawahar Kala Kendra; the demo status shows "
        "a rejected report.",
    ),
    DemoIssue(
        "Construction debris blocking footpath near Ajmeri Gate",
        IssueCategory.OTHER,
        IssueSeverity.MEDIUM,
        IssueStatus.REPORTED,
        "Nehru Bazaar",
        "Ajmeri Gate",
        26.9167,
        75.8171,
        2,
        "Municipal Citizen Services",
        "Pedestrians reported construction debris narrowing the footpath near Ajmeri Gate.",
    ),
)

JAIPUR_CITY = "Jaipur"

OLD_DEMO_AREA_NAMES = {
    "Sector 12",
    "Green Park",
    "Old Market",
    "Lake View Colony",
    "River Road",
    "Sector 8",
    "Shanti Nagar",
    "MG Road",
    "Rose Garden",
    "Model Town",
    "Nehru Enclave",
    "University Road",
    "Central Avenue",
}

LEGACY_JAIPUR_AREA_ALIASES = {
    "sector 3, malviya nagar": "Malviya Nagar",
    "sector 3 malviya nagar": "Malviya Nagar",
    "sector 23": "Malviya Nagar",
    "ravindranagar": "Ravindra Nagar",
    "ravindra nagar": "Ravindra Nagar",
}

LEGACY_JAIPUR_AREA_COORDINATES = {
    "Malviya Nagar": (26.8530, 75.8056),
    "Railway Colony": (26.8436, 75.8025),
    "Ravindra Nagar": (26.9004, 75.7898),
}


def create_demo_image(path: Path, number: int, issue: DemoIssue) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    colors = ("#dcecdf", "#f4e6bf", "#dbe8f1", "#eadbd8")
    image = Image.new("RGB", (960, 600), color=colors[number % len(colors)])
    draw = ImageDraw.Draw(image)
    draw.rectangle((55, 55, 905, 545), outline="#17643c", width=8)
    draw.text((90, 100), f"CivicPulse Jaipur demo report {number + 1}", fill="#173226")
    draw.text((90, 160), issue.category.value.replace("_", " ").title(), fill="#17643c")
    draw.text((90, 220), issue.location, fill="#26372f")
    draw.text((90, 280), issue.landmark, fill="#26372f")
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
                note=f"Jaipur demo status updated to {issue.status.value.replace('_', ' ')}.",
                actor_type=UpdateActorType.SYSTEM,
                created_at=created_at + timedelta(hours=2),
            ),
        )


def ensure_demo_confirmations(
    session: Session,
    issue: Issue,
    *,
    seed_index: int,
    confirmations: int,
    created_at: datetime,
) -> int:
    added = 0
    for actor_number in range(confirmations):
        action_id = uuid5(
            NAMESPACE_URL,
            f"civicpulse-demo-action-{seed_index + 1}-{actor_number + 1}",
        )
        exists = session.scalar(select(CommunityAction.id).where(CommunityAction.id == action_id))
        if exists is not None:
            continue
        session.add(
            CommunityAction(
                id=action_id,
                issue_id=issue.id,
                action_type=CommunityActionType.SAW_THIS_TOO,
                actor_hash=f"demo-actor-{seed_index + 1}-{actor_number + 1}",
                created_at=created_at + timedelta(hours=actor_number + 1),
            ),
        )
        added += 1
    return added


def cleanup_old_demo_areas(session: Session) -> None:
    for area in session.scalars(select(Area).where(Area.name.in_(OLD_DEMO_AREA_NAMES))).all():
        if area.issues or area.missions:
            continue
        session.delete(area)


def legacy_jaipur_area_name(value: str) -> str | None:
    normalized = " ".join(value.strip().lower().split())
    if "map-7" in normalized:
        return None
    if "malviya nagar" in normalized:
        return "Malviya Nagar"
    if "railway colony" in normalized:
        return "Railway Colony"
    if normalized in LEGACY_JAIPUR_AREA_ALIASES:
        return LEGACY_JAIPUR_AREA_ALIASES[normalized]
    return None


def remove_obvious_phase_test_records(session: Session) -> None:
    for mission in session.scalars(select(Mission)).all():
        area_name = mission.area.name if mission.area else ""
        if "map-7" in f"{mission.title} {area_name}".lower():
            session.delete(mission)

    for issue in session.scalars(select(Issue).where(Issue.public_reference.not_like("CP-DEMO-%"))):
        if "map-7" in f"{issue.title} {issue.location} {issue.landmark or ''}".lower():
            session.delete(issue)


def migrate_legacy_jaipur_records(session: Session) -> set[UUID]:
    touched_area_ids: set[UUID] = set()
    for issue in session.scalars(select(Issue).where(Issue.public_reference.not_like("CP-DEMO-%"))):
        area_name = legacy_jaipur_area_name(issue.location)
        if area_name is None:
            continue
        area = get_or_create_area_for_location(session, area_name, city=JAIPUR_CITY)
        issue.area = area
        issue.location = area_name
        if area_name in LEGACY_JAIPUR_AREA_COORDINATES:
            issue.latitude, issue.longitude = LEGACY_JAIPUR_AREA_COORDINATES[area_name]
        issue.ai_model = issue.ai_model or "legacy-jaipur-demo"
        touched_area_ids.add(area.id)

    for mission in session.scalars(select(Mission)).all():
        source = mission.area.name if mission.area else mission.title
        area_name = legacy_jaipur_area_name(source)
        if area_name is None:
            continue
        area = get_or_create_area_for_location(session, area_name, city=JAIPUR_CITY)
        mission.area = area
        mission.title = (
            mission.title.replace("Sector 23", area_name)
            .replace("sector 23", area_name)
            .replace("Ravindranagar", "Ravindra Nagar")
            .replace("ravindranagar", "Ravindra Nagar")
        )
        touched_area_ids.add(area.id)

    for area in session.scalars(select(Area).where(Area.city != JAIPUR_CITY)).all():
        if area.issues or area.missions:
            continue
        session.delete(area)
    return touched_area_ids


def seed(session: Session) -> tuple[int, int]:
    settings = get_settings()
    if settings.storage_backend != "local":
        raise RuntimeError("The demo seeder currently requires STORAGE_BACKEND=local")

    added_issues = 0
    added_actions = 0
    now = datetime.now(UTC)
    touched_area_ids: set[UUID] = set()
    for index, sample in enumerate(DEMO_ISSUES):
        reference = f"CP-DEMO-{index + 1:04d}"
        existing = session.scalar(select(Issue).where(Issue.public_reference == reference))

        image_key = f"issues/demo-{index + 1:02d}.png"
        create_demo_image(settings.local_storage_path / image_key, index, sample)
        area = get_or_create_area_for_location(session, sample.location, city=JAIPUR_CITY)
        touched_area_ids.add(area.id)
        created_at = (
            existing.created_at
            if existing is not None
            else now - timedelta(days=index, minutes=index * 7)
        )
        issue = existing or Issue(
            id=uuid5(NAMESPACE_URL, f"civicpulse-demo-issue-{index + 1}"),
            public_reference=reference,
            image_key=image_key,
            image_mime="image/png",
            citizen_name=None,
            citizen_contact=None,
            created_at=created_at,
            updated_at=created_at,
        )
        issue.title = sample.title
        issue.original_description = sample.description
        issue.ai_summary = (
            f"{sample.title} has been reported near {sample.landmark} in "
            f"{sample.location}, Jaipur and requires civic review."
        )
        issue.category = sample.category
        issue.severity = sample.severity
        issue.urgency_level = (
            UrgencyLevel.IMMEDIATE
            if sample.severity is IssueSeverity.CRITICAL
            else UrgencyLevel.SOON
        )
        issue.urgency_reason = "The issue affects regular public use of this Jaipur location."
        issue.suggested_department = sample.department
        issue.safety_risk = (
            "Residents and visitors may face disruption or safety risk until this is addressed."
        )
        issue.citizen_explanation = (
            "This Jaipur demo report demonstrates the public tracker workflow with realistic "
            "local places."
        )
        issue.suggested_next_action = (
            "Review the report, collect community verification, and coordinate an on-site check."
        )
        issue.location = sample.location
        issue.landmark = sample.landmark
        issue.latitude = sample.latitude
        issue.longitude = sample.longitude
        issue.image_key = image_key
        issue.image_mime = "image/png"
        issue.status = sample.status
        issue.ai_model = "jaipur-demo-seed"
        issue.prompt_version = "jaipur-demo-seed-v1"
        issue.area = area
        issue.updated_at = created_at
        if existing is None:
            session.add(issue)
            added_issues += 1
        session.flush()

        added_actions += ensure_demo_confirmations(
            session,
            issue,
            seed_index=index,
            confirmations=sample.confirmations,
            created_at=created_at,
        )
        ensure_timeline(session, issue, created_at)

    remove_obvious_phase_test_records(session)
    touched_area_ids.update(migrate_legacy_jaipur_records(session))
    cleanup_old_demo_areas(session)
    area_service = AreaService(repository=SQLAlchemyAreaRepository(session))
    for area_id in touched_area_ids:
        area_service.recalculate_area_scores(
            area_id,
            event_type="jaipur_demo_seed_refreshed",
            reason="Jaipur demo data refreshed with realistic local issue signals.",
        )
    session.commit()
    return added_issues, added_actions


def main() -> None:
    with Session(get_engine()) as session:
        issue_count, action_count = seed(session)
    print(f"Demo tracker ready: {issue_count} issues and {action_count} confirmations added.")


if __name__ == "__main__":
    main()
