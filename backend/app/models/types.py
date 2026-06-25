from enum import StrEnum

from sqlalchemy import Enum


def enum_type[EnumType: StrEnum](enum_class: type[EnumType], name: str) -> Enum:
    return Enum(
        enum_class,
        name=name,
        native_enum=False,
        create_constraint=True,
        validate_strings=True,
        values_callable=lambda members: [member.value for member in members],
    )
