from functools import lru_cache
from typing import Annotated

from fastapi import Depends
from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.db.session import get_db_session
from app.repositories.admin import SQLAlchemyAdminSessionRepository
from app.repositories.admin_issues import SQLAlchemyAdminIssueRepository
from app.repositories.areas import SQLAlchemyAreaRepository
from app.repositories.issues import SQLAlchemyIssueRepository
from app.repositories.missions import SQLAlchemyMissionRepository
from app.repositories.operations import SQLAlchemyOperationsRepository
from app.repositories.reports import SQLAlchemyReportRepository
from app.services.admin import AdminService
from app.services.admin_auth import AdminAuthService, get_login_rate_limiter
from app.services.ai import CivicIssueAnalyzer, get_civic_issue_analyzer
from app.services.area_explanations import CivicAreaExplainer, get_civic_area_explainer
from app.services.areas import AreaService
from app.services.issues import IssueService
from app.services.mission_generation import (
    CivicMissionGenerator,
    MissionGenerationService,
    get_civic_mission_generator,
)
from app.services.mission_refinement import (
    CivicMissionRefiner,
    MissionRefinementService,
    get_civic_mission_refiner,
)
from app.services.missions import MissionService
from app.services.operations import OperationsService
from app.services.operations_ai import CivicOperationsAnalyzer, get_civic_operations_analyzer
from app.services.rate_limit import InMemoryRateLimiter
from app.services.reports import ReportService
from app.services.storage import ImageStorage, get_image_storage

DatabaseDependency = Annotated[Session, Depends(get_db_session)]
SettingsDependency = Annotated[Settings, Depends(get_settings)]
StorageDependency = Annotated[ImageStorage, Depends(get_image_storage)]
AnalyzerDependency = Annotated[CivicIssueAnalyzer, Depends(get_civic_issue_analyzer)]
OperationsAnalyzerDependency = Annotated[
    CivicOperationsAnalyzer,
    Depends(get_civic_operations_analyzer),
]
MissionGeneratorDependency = Annotated[
    CivicMissionGenerator,
    Depends(get_civic_mission_generator),
]
MissionRefinerDependency = Annotated[
    CivicMissionRefiner,
    Depends(get_civic_mission_refiner),
]
AreaExplainerDependency = Annotated[
    CivicAreaExplainer,
    Depends(get_civic_area_explainer),
]


@lru_cache
def build_report_analysis_rate_limiter(limit: int, window_minutes: int) -> InMemoryRateLimiter:
    return InMemoryRateLimiter(
        limit=limit,
        window_minutes=window_minutes,
        code="report_analysis_rate_limited",
        message="Too many report analyses were requested. Please try again later.",
    )


def get_report_analysis_rate_limiter(
    settings: SettingsDependency,
) -> InMemoryRateLimiter:
    return build_report_analysis_rate_limiter(
        settings.report_analysis_rate_limit,
        settings.report_analysis_rate_window_minutes,
    )


ReportAnalysisRateLimiterDependency = Annotated[
    InMemoryRateLimiter,
    Depends(get_report_analysis_rate_limiter),
]


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
        area_score_trigger=AreaService(repository=SQLAlchemyAreaRepository(session)),
    )


ReportServiceDependency = Annotated[ReportService, Depends(get_report_service)]


def get_issue_service(
    session: DatabaseDependency,
    settings: SettingsDependency,
) -> IssueService:
    return IssueService(
        repository=SQLAlchemyIssueRepository(session),
        settings=settings,
        area_score_trigger=AreaService(repository=SQLAlchemyAreaRepository(session)),
    )


IssueServiceDependency = Annotated[IssueService, Depends(get_issue_service)]


def get_admin_auth_service(
    session: DatabaseDependency,
    settings: SettingsDependency,
) -> AdminAuthService:
    return AdminAuthService(
        repository=SQLAlchemyAdminSessionRepository(session),
        settings=settings,
        rate_limiter=get_login_rate_limiter(),
    )


AdminAuthServiceDependency = Annotated[AdminAuthService, Depends(get_admin_auth_service)]


def get_admin_service(session: DatabaseDependency) -> AdminService:
    return AdminService(
        repository=SQLAlchemyAdminIssueRepository(session),
        area_score_trigger=AreaService(repository=SQLAlchemyAreaRepository(session)),
    )


AdminServiceDependency = Annotated[AdminService, Depends(get_admin_service)]


def get_area_service(
    session: DatabaseDependency,
    explainer: AreaExplainerDependency,
) -> AreaService:
    return AreaService(
        repository=SQLAlchemyAreaRepository(session),
        explainer=explainer,
    )


AreaServiceDependency = Annotated[AreaService, Depends(get_area_service)]


def get_mission_service(session: DatabaseDependency) -> MissionService:
    return MissionService(
        repository=SQLAlchemyMissionRepository(session),
        reward_trigger=AreaService(repository=SQLAlchemyAreaRepository(session)),
    )


MissionServiceDependency = Annotated[MissionService, Depends(get_mission_service)]


def get_mission_generation_service(
    session: DatabaseDependency,
    generator: MissionGeneratorDependency,
) -> MissionGenerationService:
    return MissionGenerationService(
        repository=SQLAlchemyMissionRepository(session),
        generator=generator,
    )


MissionGenerationServiceDependency = Annotated[
    MissionGenerationService,
    Depends(get_mission_generation_service),
]


def get_mission_refinement_service(
    session: DatabaseDependency,
    refiner: MissionRefinerDependency,
) -> MissionRefinementService:
    return MissionRefinementService(
        repository=SQLAlchemyMissionRepository(session),
        refiner=refiner,
    )


MissionRefinementServiceDependency = Annotated[
    MissionRefinementService,
    Depends(get_mission_refinement_service),
]


def get_operations_service(
    session: DatabaseDependency,
    analyzer: OperationsAnalyzerDependency,
) -> OperationsService:
    return OperationsService(
        repository=SQLAlchemyOperationsRepository(session),
        analyzer=analyzer,
    )


OperationsServiceDependency = Annotated[OperationsService, Depends(get_operations_service)]
