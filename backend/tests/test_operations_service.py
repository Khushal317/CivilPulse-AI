from datetime import UTC, datetime
from uuid import UUID

import pytest

from app.core.errors import AppError
from app.domain.enums import IssueCategory, IssueSeverity, IssueStatus
from app.models.civic_operations_report import CivicOperationsReport
from app.repositories.operations import OperationsIssueRecord, OperationsRepository
from app.schemas.operations import OperationsAnalysis, OperationsIssueInput
from app.services.operations import OperationsService
from app.services.operations_ai import DemoCivicOperationsAnalyzer


def operations_record(number: int = 1) -> OperationsIssueRecord:
    return OperationsIssueRecord(
        issue_id=str(UUID(int=number)),
        public_reference=f"CP-20260626-{number:08d}",
        title=f"Severe pothole near school gate {number}",
        category=IssueCategory.ROAD_DAMAGE.value,
        department="Public Works / Road Maintenance",
        severity=IssueSeverity.HIGH.value,
        status=IssueStatus.COMMUNITY_VERIFIED.value,
        location="Sector 12",
        landmark="City Public School",
        verification_count=5,
        unresolved_count=3,
        fixed_count=0,
        incorrect_count=0,
        created_at=datetime(2026, 6, 24, 10, tzinfo=UTC),
        age_hours=48,
        age_days=2,
        summary="Large pothole near school gate causing risk to children and riders.",
        latest_admin_update="Escalated for inspection.",
    )


class FakeOperationsRepository(OperationsRepository):
    def __init__(self, records: list[OperationsIssueRecord] | None = None) -> None:
        self.records = records or []
        self.saved_reports: list[CivicOperationsReport] = []

    def active_issues_for_analysis(
        self,
        current_time: datetime | None = None,
    ) -> list[OperationsIssueRecord]:
        return self.records

    def add_report(self, report: CivicOperationsReport) -> CivicOperationsReport:
        report.id = UUID(int=len(self.saved_reports) + 1)
        report.created_at = report.generated_at
        self.saved_reports.append(report)
        return report

    def latest_report(self) -> CivicOperationsReport | None:
        if not self.saved_reports:
            return None
        return self.saved_reports[-1]


class CapturingAnalyzer:
    model_name = "capturing-operations-analyzer"

    def __init__(self) -> None:
        self.received: list[OperationsIssueInput] = []

    def analyze(self, issues: list[OperationsIssueInput]) -> OperationsAnalysis:
        self.received = issues
        return DemoCivicOperationsAnalyzer().analyze(issues)


class FailingAnalyzer:
    model_name = "failing-operations-analyzer"

    def analyze(self, issues: list[OperationsIssueInput]) -> OperationsAnalysis:
        raise AppError(
            code="operations_ai_unavailable",
            message="The Civic Operations Agent could not analyze city issues right now.",
            status_code=503,
        )


def test_operations_service_analyzes_active_issues_and_saves_report() -> None:
    repository = FakeOperationsRepository([operations_record(1), operations_record(2)])
    analyzer = CapturingAnalyzer()

    response = OperationsService(repository=repository, analyzer=analyzer).analyze_active_issues()

    assert response.id == UUID(int=1)
    assert response.total_issues_analyzed == 2
    assert response.model_used == "demo-civic-operations-agent-v1"
    assert response.urgent_issues[0].issue_id == UUID(int=1)
    assert analyzer.received[0].issue_id == UUID(int=1)
    assert analyzer.received[0].category is IssueCategory.ROAD_DAMAGE
    assert len(repository.saved_reports) == 1
    assert repository.saved_reports[0].urgent_issues_json[0]["issue_id"] == str(UUID(int=1))


def test_operations_service_saves_empty_report_without_active_issues() -> None:
    repository = FakeOperationsRepository([])

    response = OperationsService(
        repository=repository,
        analyzer=DemoCivicOperationsAnalyzer(),
    ).analyze_active_issues()

    assert response.total_issues_analyzed == 0
    assert response.model_used == "system-empty"
    assert response.urgent_issues == []
    assert len(repository.saved_reports) == 1


def test_operations_service_returns_latest_report_without_analyzing() -> None:
    repository = FakeOperationsRepository([])
    service = OperationsService(repository=repository, analyzer=FailingAnalyzer())
    generated = OperationsService(
        repository=repository,
        analyzer=DemoCivicOperationsAnalyzer(),
    ).analyze_active_issues()

    latest = service.latest_report()

    assert latest is not None
    assert latest.id == generated.id
    assert latest.model_used == "system-empty"


def test_latest_operations_report_hides_duplicate_clusters_with_inactive_issues() -> None:
    repository = FakeOperationsRepository([operations_record(1)])
    report = CivicOperationsReport(
        id=UUID(int=40),
        generated_at=datetime(2026, 6, 28, 10, tzinfo=UTC),
        created_at=datetime(2026, 6, 28, 10, tzinfo=UTC),
        total_issues_analyzed=2,
        model_used="stored-report",
        executive_summary="Stored report with a stale duplicate cluster.",
        urgent_issues_json=[],
        duplicate_clusters_json=[
            {
                "cluster_title": "Possible duplicate road reports",
                "issues": [
                    {
                        "issue_id": str(UUID(int=1)),
                        "public_reference": "CP-20260626-00000001",
                        "title": "Severe pothole near school gate 1",
                    },
                    {
                        "issue_id": str(UUID(int=2)),
                        "public_reference": "CP-20260626-00000002",
                        "title": "Severe pothole near school gate 2",
                    },
                ],
                "reason": "Both reports describe the same place.",
                "recommended_action": "Keep one and mark the other as duplicate.",
            },
        ],
        area_hotspots_json=[
            {
                "area": "Sector 12",
                "issue_count": 1,
                "main_categories": ["road_damage"],
                "risk_level": "medium",
                "insight": "One active issue remains.",
            },
        ],
        department_priorities_json=[],
        escalation_messages_json=[],
        predicted_risks_json=[],
        raw_response_json={"executive_summary": "Stored report with a stale cluster."},
    )
    repository.saved_reports.append(report)

    latest = OperationsService(repository=repository, analyzer=FailingAnalyzer()).latest_report()

    assert latest is not None
    assert latest.duplicate_clusters == []


def test_operations_service_returns_none_when_latest_report_is_missing() -> None:
    repository = FakeOperationsRepository([])

    assert (
        OperationsService(
            repository=repository,
            analyzer=DemoCivicOperationsAnalyzer(),
        ).latest_report()
        is None
    )


def test_operations_service_does_not_save_report_when_analysis_fails() -> None:
    repository = FakeOperationsRepository([operations_record()])

    with pytest.raises(AppError) as caught:
        OperationsService(repository=repository, analyzer=FailingAnalyzer()).analyze_active_issues()

    assert caught.value.code == "operations_ai_unavailable"
    assert repository.saved_reports == []
