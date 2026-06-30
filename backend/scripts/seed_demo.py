from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import NAMESPACE_URL, UUID, uuid5

from PIL import Image, ImageOps
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db.session import get_engine
from app.domain.areas import BASELINE_AREA_SCORE
from app.domain.enums import (
    CommunityActionType,
    IssueCategory,
    IssueSeverity,
    IssueStatus,
    UpdateActorType,
    UrgencyLevel,
)
from app.models.area import Area
from app.models.area_score_event import AreaScoreEvent
from app.models.community_action import CommunityAction
from app.models.issue import Issue
from app.models.issue_draft import IssueDraft
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
    created_days_ago: int
    department: str
    source_image_filename: str
    description: str


DEMO_ISSUES = (
    DemoIssue(
        "Large potholes holding rainwater near World Trade Park",
        IssueCategory.ROAD_DAMAGE,
        IssueSeverity.HIGH,
        IssueStatus.COMMUNITY_VERIFIED,
        "Malviya Nagar",
        "World Trade Park, JLN Marg",
        26.8530,
        75.8056,
        9,
        5,
        "Jaipur Development Authority / Road Maintenance",
        "road0.jpeg",
        "Commuters reported deep broken road patches filled with muddy water near the "
        "World Trade Park service lane, creating a skid risk for two-wheelers.",
    ),
    DemoIssue(
        "Severely broken road edge near City Park",
        IssueCategory.ROAD_DAMAGE,
        IssueSeverity.CRITICAL,
        IssueStatus.ESCALATED,
        "Mansarovar",
        "City Park approach road",
        26.8498,
        75.7515,
        5,
        8,
        "Jaipur Development Authority / Road Maintenance",
        "road1.avif",
        "Residents reported a badly damaged road edge on the City Park approach road that "
        "could become dangerous during evening traffic and rain.",
    ),
    DemoIssue(
        "Flood-damaged road stretch needs barricading",
        IssueCategory.ROAD_DAMAGE,
        IssueSeverity.CRITICAL,
        IssueStatus.IN_PROGRESS,
        "Amer Road",
        "Jal Mahal promenade approach",
        26.9535,
        75.8464,
        7,
        2,
        "Public Works / Road Safety",
        "road2.jpg",
        "Visitors reported a dangerous washed-out road stretch near the Jal Mahal approach "
        "that needs temporary barricading and repair planning.",
    ),
    DemoIssue(
        "Broken footpath tiles outside Mall of Jaipur",
        IssueCategory.ROAD_DAMAGE,
        IssueSeverity.MEDIUM,
        IssueStatus.COMMUNITY_VERIFIED,
        "Vaishali Nagar",
        "Mall of Jaipur, Gandhi Path",
        26.9124,
        75.7432,
        6,
        4,
        "Public Works / Footpath Maintenance",
        "footpath0.jpeg",
        "Residents reported a sunken patch of broken paving blocks outside Mall of Jaipur "
        "that makes the walkway difficult for pedestrians.",
    ),
    DemoIssue(
        "Cracked pedestrian path near Statue Circle",
        IssueCategory.ROAD_DAMAGE,
        IssueSeverity.MEDIUM,
        IssueStatus.REPORTED,
        "C-Scheme",
        "Statue Circle pedestrian path",
        26.9056,
        75.8064,
        2,
        1,
        "Public Works / Footpath Maintenance",
        "footpath1.jpeg",
        "Office commuters reported cracked and uneven footpath slabs near Statue Circle "
        "that can trip pedestrians during rush hours.",
    ),
    DemoIssue(
        "Open footpath cavity near Raja Park shops",
        IssueCategory.PUBLIC_SAFETY,
        IssueSeverity.HIGH,
        IssueStatus.ESCALATED,
        "Raja Park",
        "Govind Marg shopping stretch",
        26.8960,
        75.8276,
        8,
        6,
        "Public Works / Public Safety",
        "footpath2.jpeg",
        "Pedestrians reported a large open cavity in the footpath near the Raja Park shop "
        "fronts, creating a clear fall risk.",
    ),
    DemoIssue(
        "Water spraying from pipe joint near SMS Hospital",
        IssueCategory.WATER_LEAKAGE,
        IssueSeverity.HIGH,
        IssueStatus.IN_PROGRESS,
        "Sawai Ram Singh Road",
        "Sawai Man Singh Hospital side road",
        26.9028,
        75.8166,
        6,
        7,
        "Water Department",
        "water0.jpeg",
        "Visitors reported a pipe joint spraying water near the SMS Hospital side road, "
        "wasting water and making the edge of the road slippery.",
    ),
    DemoIssue(
        "Small but continuous pipe leak near Durgapura",
        IssueCategory.WATER_LEAKAGE,
        IssueSeverity.LOW,
        IssueStatus.RESOLVED,
        "Tonk Road",
        "Durgapura bus stop",
        26.8467,
        75.7936,
        3,
        3,
        "Water Department",
        "water1.jpeg",
        "A small continuous pipe leak was reported near the Durgapura bus stop and marked "
        "resolved after local repair confirmation.",
    ),
    DemoIssue(
        "Seepage staining under market structure",
        IssueCategory.WATER_LEAKAGE,
        IssueSeverity.MEDIUM,
        IssueStatus.COMMUNITY_VERIFIED,
        "Bapu Bazaar",
        "Bapu Bazaar covered lane",
        26.9207,
        75.8257,
        5,
        10,
        "Water Department / Building Maintenance",
        "water2.jpg",
        "Shopkeepers reported visible seepage marks under a busy market structure, suggesting "
        "a slow leak that needs inspection before it worsens.",
    ),
    DemoIssue(
        "Open drinking activity near Civil Lines public seating",
        IssueCategory.PUBLIC_SAFETY,
        IssueSeverity.HIGH,
        IssueStatus.COMMUNITY_VERIFIED,
        "Civil Lines",
        "Civil Lines Metro Station approach road",
        26.9060,
        75.7823,
        9,
        4,
        "Community Policing / Public Safety",
        "alco1.jpg",
        "Residents reported open alcohol consumption near public seating at night, raising "
        "concerns about nuisance and safety for pedestrians.",
    ),
    DemoIssue(
        "Late-night drinking outside liquor shop frontage",
        IssueCategory.PUBLIC_SAFETY,
        IssueSeverity.MEDIUM,
        IssueStatus.REPORTED,
        "Jagatpura",
        "Jagatpura Railway Station road market",
        26.8324,
        75.8422,
        2,
        1,
        "Community Policing / Public Safety",
        "alcoho.jpeg",
        "Residents reported late-night drinking near a shop frontage close to the station "
        "road market and requested visible monitoring.",
    ),
    DemoIssue(
        "Alcohol litter and gathering near Jawahar Circle",
        IssueCategory.PUBLIC_SAFETY,
        IssueSeverity.MEDIUM,
        IssueStatus.RESOLVED,
        "Jawahar Circle",
        "Patrika Gate parking edge",
        26.8427,
        75.8034,
        4,
        2,
        "Community Policing / Public Safety",
        "alcoho2.jpeg",
        "A resident reported alcohol-related litter and gathering near the Patrika Gate "
        "parking edge; the issue is marked resolved after local follow-up.",
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


def demo_source_image_path(storage_path: Path, issue: DemoIssue) -> Path:
    packaged_demo_source = Path(__file__).resolve().parent / "demo_issue_images" / (
        issue.source_image_filename
    )
    if packaged_demo_source.exists():
        return packaged_demo_source
    local_demo_source = storage_path / "demo-source" / issue.source_image_filename
    if local_demo_source.exists():
        return local_demo_source
    downloads_source = Path("/Users/khush/Downloads") / issue.source_image_filename
    if downloads_source.exists():
        return downloads_source
    raise FileNotFoundError(
        "Missing demo source image "
        f"{issue.source_image_filename}. Add it to {storage_path / 'demo-source'}.",
    )


def write_demo_image(path: Path, issue: DemoIssue, *, storage_path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    source_path = demo_source_image_path(storage_path, issue)
    with Image.open(source_path) as source_image:
        image = ImageOps.exif_transpose(source_image).convert("RGB")
        image.thumbnail((1600, 1600))
        image.save(path, format="JPEG", quality=88, optimize=True)


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


def reset_demo_reports_and_scores(session: Session) -> None:
    for draft in session.scalars(select(IssueDraft)).all():
        session.delete(draft)
    for issue in session.scalars(select(Issue)).all():
        session.delete(issue)
    for score_event in session.scalars(select(AreaScoreEvent)).all():
        session.delete(score_event)
    for area in session.scalars(select(Area)).all():
        area.overall_score = BASELINE_AREA_SCORE
        area.infrastructure_score = BASELINE_AREA_SCORE
        area.cleanliness_score = BASELINE_AREA_SCORE
        area.safety_score = BASELINE_AREA_SCORE
        area.participation_score = BASELINE_AREA_SCORE
        area.responsiveness_score = BASELINE_AREA_SCORE
        area.environment_score = BASELINE_AREA_SCORE
        area.rank = None
        area.status_label = "improving"
    session.flush()


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
    reset_demo_reports_and_scores(session)
    for index, sample in enumerate(DEMO_ISSUES):
        reference = f"CP-DEMO-{index + 1:04d}"
        existing = session.scalar(select(Issue).where(Issue.public_reference == reference))

        image_key = f"issues/jaipur-issue-{index + 1:02d}.jpg"
        write_demo_image(
            settings.local_storage_path / image_key,
            sample,
            storage_path=settings.local_storage_path,
        )
        area = get_or_create_area_for_location(session, sample.location, city=JAIPUR_CITY)
        touched_area_ids.add(area.id)
        created_at = (
            existing.created_at
            if existing is not None
            else now - timedelta(days=sample.created_days_ago, minutes=index * 7)
        )
        issue = existing or Issue(
            id=uuid5(NAMESPACE_URL, f"civicpulse-demo-issue-{index + 1}"),
            public_reference=reference,
            image_key=image_key,
            image_mime="image/jpeg",
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
        issue.image_mime = "image/jpeg"
        issue.status = sample.status
        issue.ai_model = "jaipur-real-issue-seed"
        issue.prompt_version = "jaipur-real-issue-seed-v1"
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
