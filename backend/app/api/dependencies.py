from typing import Annotated

from fastapi import Depends
from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.db.session import get_db_session
from app.repositories.reports import SQLAlchemyReportRepository
from app.services.ai import CivicIssueAnalyzer, get_civic_issue_analyzer
from app.services.reports import ReportService
from app.services.storage import ImageStorage, get_image_storage

DatabaseDependency = Annotated[Session, Depends(get_db_session)]
SettingsDependency = Annotated[Settings, Depends(get_settings)]
StorageDependency = Annotated[ImageStorage, Depends(get_image_storage)]
AnalyzerDependency = Annotated[CivicIssueAnalyzer, Depends(get_civic_issue_analyzer)]


def get_report_service(
    session: DatabaseDependency,
    storage: StorageDependency,
    analyzer: AnalyzerDependency,
    settings: SettingsDependency,
) -> ReportService:
    return ReportService(
        repository=SQLAlchemyReportRepository(session),
        storage=storage,
        analyzer=analyzer,
        settings=settings,
    )


ReportServiceDependency = Annotated[ReportService, Depends(get_report_service)]
