from pydantic import Field, model_validator

from app.schemas.common import APIModel


class OptionalCoordinates(APIModel):
    latitude: float | None = Field(default=None, ge=-90, le=90)
    longitude: float | None = Field(default=None, ge=-180, le=180)

    @model_validator(mode="after")
    def require_complete_coordinate_pair(self) -> "OptionalCoordinates":
        if (self.latitude is None) != (self.longitude is None):
            raise ValueError("latitude and longitude must be provided together")
        return self


Coordinates = OptionalCoordinates
