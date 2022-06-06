from enum import Enum
from typing import Any
from typing import Optional
from typing import Type
from typing import Union

from tortoise import Model
from tortoise.fields.data import CharEnumType
from tortoise.fields.data import CharField

from cattrs_extras.converter import ReversedEnum


class ReversedCharEnumFieldInstance(CharField):
    def __init__(
        self,
        enum_type: Type[ReversedEnum],
        description: Optional[str] = None,
        max_length: int = 0,
        **kwargs: Any,
    ) -> None:

        # Automatic description for the field if not specified by the user
        if description is None:
            description = "\n".join([f"{e.name}: {str(e.value)}" for e in enum_type])[:2048]

        # Automatic CharField max_length
        if max_length == 0:
            for item in enum_type:
                item_len = len(str(item.name))
                if item_len > max_length:
                    max_length = item_len

        super().__init__(description=description, max_length=max_length, **kwargs)
        self.enum_type = enum_type

    def to_python_value(self, value: Union[Enum, str, None]) -> Optional[Enum]:
        if value is None:
            return None
        if isinstance(value, Enum):
            return value
        return self.enum_type[value]

    def to_db_value(self, value: Optional[Any], instance: Union[Type[Model], Model]) -> Optional[str]:
        if value is None:
            return None
        if isinstance(value, Enum):
            return value.name
        return self.enum_type[value].name


def ReversedCharEnumField(  # pylint: disable=invalid-name
    enum_type: Type[CharEnumType],
    description: Optional[str] = None,
    max_length: int = 0,
    **kwargs: Any,
) -> CharEnumType:

    return ReversedCharEnumFieldInstance(enum_type, description, max_length, **kwargs)  # type: ignore
