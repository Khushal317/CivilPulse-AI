from datetime import UTC, datetime
from uuid import UUID

from fastapi.testclient import TestClient

from app.api.dependencies import get_issue_service
from app.domain.enums import (
    CommunityActionType,
    IssueCategory,
    IssueSeverity,
    IssueSort,
    IssueStatus,
    UpdateActorType,
    UrgencyLevel,
)
from app.main import app
from app.schemas.issues import (
    CommunityActionResponse,
    CommunityCounts,
    IssueListItem,
    IssueListQuery,
    IssueListResponse,
    IssuePublicDetail,
    IssueUpdatePublic,
)


class FakeIssueService:
    def __init__(self) -> None:
        self.query: IssueListQuery | None = None

    def list_public(self, query: IssueListQuery) -> IssueListResponse:
        self.query = query
        return IssueListResponse(
            items=[
                IssueListItem(
                    id=UUID(int=1),
                    public_reference="CP-20260625-00000001",
                    title="Unsafe streetlight",
                    category=IssueCategory.STREETLIGHT,
                    severity=IssueSeverity.HIGH,
                    location="Green Park",
                    landmark=None,
                    image_url="/api/v1/media/issues/1.jpg",
                    status=IssueStatus.IN_PROGRESS,
                    created_at=datetime(2026, 6, 25, tzinfo=UTC),
                    updated_at=datetime(2026, 6, 25, tzinfo=UTC),
                    verification_count=3,
                ),
            ],
            page=query.page,
            page_size=query.page_size,
            total_items=1,
            total_pages=1,
        )

    def get_public_detail(self, issue_id: UUID, actor_hash: str) -> IssuePublicDetail:
        assert issue_id == UUID(int=1)
        assert len(actor_hash) == 64
        return IssuePublicDetail(
            id=issue_id,
            public_reference="CP-20260625-00000001",
            title="Unsafe streetlight",
            original_description="The streetlight has been dark for several nights.",
            ai_summary="A failed streetlight reduces visibility near a public park.",
            category=IssueCategory.STREETLIGHT,
            severity=IssueSeverity.HIGH,
            urgency_level=UrgencyLevel.URGENT,
            urgency_reason="Residents use this path after dark.",
            suggested_department="Electrical Maintenance",
            safety_risk="Low visibility may increase fall and traffic risk.",
            citizen_explanation="This report is ready for community verification.",
            suggested_next_action="Inspect and repair the streetlight.",
            location="Green Park",
            landmark="Community playground",
            image_url="/api/v1/media/issues/1.jpg",
            status=IssueStatus.REPORTED,
            created_at=datetime(2026, 6, 25, tzinfo=UTC),
            updated_at=datetime(2026, 6, 25, tzinfo=UTC),
            verification_count=2,
            community_counts=CommunityCounts(saw_this_too=2),
            updates=[
                IssueUpdatePublic(
                    id=UUID(int=2),
                    from_status=None,
                    to_status=IssueStatus.REPORTED,
                    note="Issue reported by a citizen.",
                    actor_type=UpdateActorType.SYSTEM,
                    created_at=datetime(2026, 6, 25, tzinfo=UTC),
                ),
            ],
            viewer_actions=[],
        )

    def submit_community_action(
        self,
        issue_id: UUID,
        action_type: CommunityActionType,
        actor_hash: str,
    ) -> CommunityActionResponse:
        assert issue_id == UUID(int=1)
        assert len(actor_hash) == 64
        return CommunityActionResponse(
            action_type=action_type,
            accepted=True,
            issue_status=IssueStatus.COMMUNITY_VERIFIED,
            community_counts=CommunityCounts(saw_this_too=3),
            viewer_actions=[action_type],
        )


def test_tracker_route_parses_filters_and_hides_private_fields(client: TestClient) -> None:
    service = FakeIssueService()
    app.dependency_overrides[get_issue_service] = lambda: service

    response = client.get(
        "/api/v1/issues",
        params={
            "page": 2,
            "page_size": 10,
            "category": "streetlight",
            "severity": "high",
            "status": "in_progress",
            "location": "Green Park",
            "sort": "most_verified",
        },
    )

    assert response.status_code == 200
    assert service.query == IssueListQuery(
        page=2,
        page_size=10,
        category=IssueCategory.STREETLIGHT,
        severity=IssueSeverity.HIGH,
        status=IssueStatus.IN_PROGRESS,
        location="Green Park",
        sort=IssueSort.MOST_VERIFIED,
    )
    item = response.json()["items"][0]
    assert item["verification_count"] == 3
    assert "citizen_name" not in item
    assert "citizen_contact" not in item
    assert "image_key" not in item


def test_tracker_route_enforces_page_size_limit(client: TestClient) -> None:
    response = client.get("/api/v1/issues", params={"page_size": 51})

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "validation_error"


def test_public_detail_sets_signed_actor_cookie_and_returns_timeline(
    client: TestClient,
) -> None:
    service = FakeIssueService()
    app.dependency_overrides[get_issue_service] = lambda: service

    response = client.get(f"/api/v1/issues/{UUID(int=1)}")

    assert response.status_code == 200
    assert response.json()["updates"][0]["to_status"] == "reported"
    assert response.json()["community_counts"]["saw_this_too"] == 2
    assert "citizen_contact" not in response.json()
    cookie = response.headers["set-cookie"]
    assert "civicpulse_actor=" in cookie
    assert "HttpOnly" in cookie
    assert "SameSite=lax" in cookie


def test_community_action_uses_actor_cookie_and_returns_promotion(
    client: TestClient,
) -> None:
    service = FakeIssueService()
    app.dependency_overrides[get_issue_service] = lambda: service
    client.get(f"/api/v1/issues/{UUID(int=1)}")

    response = client.post(
        f"/api/v1/issues/{UUID(int=1)}/community-actions",
        json={"action_type": "saw_this_too"},
    )

    assert response.status_code == 200
    assert response.json()["accepted"] is True
    assert response.json()["issue_status"] == "community_verified"
    assert response.json()["community_counts"]["saw_this_too"] == 3
