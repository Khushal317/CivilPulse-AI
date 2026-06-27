from typing import Protocol
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.domain.missions import MissionStatus
from app.models.mission import Mission

PUBLIC_DETAIL_STATUSES = {
    MissionStatus.ACTIVE,
    MissionStatus.COMPLETED,
    MissionStatus.EXPIRED,
}


class MissionRepository(Protocol):
    def add(self, mission: Mission) -> Mission: ...

    def list_public(self) -> list[Mission]: ...

    def get_public_detail(self, mission_id: UUID) -> Mission | None: ...

    def flush(self) -> None: ...


class SQLAlchemyMissionRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def add(self, mission: Mission) -> Mission:
        self._session.add(mission)
        self._session.flush()
        return mission

    def list_public(self) -> list[Mission]:
        return list(
            self._session.scalars(
                select(Mission)
                .where(Mission.status == MissionStatus.ACTIVE)
                .options(selectinload(Mission.area))
                .order_by(
                    Mission.expires_at.is_(None),
                    Mission.expires_at.asc(),
                    Mission.created_at.desc(),
                ),
            ).all(),
        )

    def get_public_detail(self, mission_id: UUID) -> Mission | None:
        return self._session.scalar(
            select(Mission)
            .where(
                Mission.id == mission_id,
                Mission.status.in_(PUBLIC_DETAIL_STATUSES),
            )
            .options(selectinload(Mission.area)),
        )

    def flush(self) -> None:
        self._session.flush()
