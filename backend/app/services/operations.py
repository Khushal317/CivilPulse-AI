from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any, cast

from pydantic import ValidationError

from app.core.errors import AppError
from app.models.civic_operations_report import CivicOperationsReport
from app.repositories.operations import OperationsIssueRecord, OperationsRepository
from app.schemas.operations import (
    OperationsAnalysis,
    OperationsIssueInput,
    OperationsReportResponse,
)
from app.services.operations_ai import CivicOperationsAnalyzer


def now_utc() -> datetime:
    return datetime.now(UTC)


def _issue_input(record: OperationsIssueRecord) -> OperationsIssueInput:
    try:
        return OperationsIssueInput.model_validate(record)
    except ValidationError as exc:
        raise AppError(
            code="operations_issue_payload_invalid",
            message="An active issue could not be prepared for operations analysis.",
            status_code=500,
        ) from exc


def _json_list(analysis: OperationsAnalysis, field_name: str) -> list[dict[str, Any]]:
    value = analysis.model_dump(mode="json")[field_name]
    if not isinstance(value, list) or any(not isinstance(item, dict) for item in value):
        raise AppError(
            code="operations_analysis_invalid",
            message="The operations analysis could not be saved.",
            status_code=500,
        )
    return cast(list[dict[str, Any]], value)


def _json_dict(analysis: OperationsAnalysis, field_name: str) -> dict[str, Any]:
    value = analysis.model_dump(mode="json")[field_name]
    if not isinstance(value, dict):
        raise AppError(
            code="operations_analysis_invalid",
            message="The operations analysis could not be saved.",
            status_code=500,
        )
    return cast(dict[str, Any], value)


def report_response(report: CivicOperationsReport) -> OperationsReportResponse:
    return OperationsReportResponse(
        id=report.id,
        generated_at=report.generated_at,
        created_at=report.created_at,
        total_issues_analyzed=report.total_issues_analyzed,
        model_used=report.model_used,
        executive_summary=report.executive_summary,
        urgent_issues=report.urgent_issues_json,
        duplicate_clusters=report.duplicate_clusters_json,
        area_hotspots=report.area_hotspots_json,
        department_priorities=report.department_priorities_json,
        escalation_messages=report.escalation_messages_json,
        predicted_risks=report.predicted_risks_json,
        raw_response=report.raw_response_json,
    )


@dataclass(slots=True)
class OperationsService:
    repository: OperationsRepository
    analyzer: CivicOperationsAnalyzer

    def analyze_active_issues(self) -> OperationsReportResponse:
        active_records = self.repository.active_issues_for_analysis(current_time=now_utc())
        active_issues = [_issue_input(record) for record in active_records]
        analysis = self.analyzer.analyze(active_issues)
        generated_at = now_utc()
        report = self.repository.add_report(
            CivicOperationsReport(
                generated_at=generated_at,
                total_issues_analyzed=analysis.total_issues_analyzed,
                model_used=analysis.model_used,
                executive_summary=analysis.executive_summary,
                urgent_issues_json=_json_list(analysis, "urgent_issues"),
                duplicate_clusters_json=_json_list(analysis, "duplicate_clusters"),
                area_hotspots_json=_json_list(analysis, "area_hotspots"),
                department_priorities_json=_json_list(analysis, "department_priorities"),
                escalation_messages_json=_json_list(analysis, "escalation_messages"),
                predicted_risks_json=_json_list(analysis, "predicted_risks"),
                raw_response_json=_json_dict(analysis, "raw_response"),
            ),
        )
        return report_response(report)

    def latest_report(self) -> OperationsReportResponse | None:
        report = self.repository.latest_report()
        if report is None:
            return None
        return report_response(report)
