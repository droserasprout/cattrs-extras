import sys
from contextlib import suppress
from datetime import date
from datetime import datetime
from datetime import timedelta
from datetime import timezone
from decimal import Decimal
from enum import Enum
from typing import Any
from typing import Callable
from typing import Mapping
from typing import Type
from typing import TypeVar

import cattr
import dateutil.parser
from attr import fields
from dateutil.parser._parser import ParserError  # type: ignore
from pytimeparse.timeparse import timeparse  # type: ignore
from typing_extensions import Literal
from typing_extensions import get_args

T = TypeVar('T')  # pylint: disable=invalid-name
NoneType = type(None)


class ReversedEnum(Enum):
    ...


class StructureError(ValueError):
    pass


class Converter(cattr.Converter):
    """cattrs converter patched to correctly load complex attrs structures.

    Keep in mind that __future__.annotations import is not supported when using this class!
    """
    def __init__(self):
        super().__init__()

        self.register_structure_hook(Decimal, self._structure_decimal)
        self.register_unstructure_hook(Decimal, self._unstructure_decimal)

        self.register_structure_hook(Literal[True], self._structure_literal_true)
        self.register_structure_hook(Literal[False], self._structure_literal_false)
        self.register_structure_hook(bool, self._structure_bool)

        self.register_structure_hook(datetime, self._structure_datetime)
        self.register_unstructure_hook(datetime, self._unstructure_datetime)
        self.register_structure_hook(date, self._structure_date)
        self.register_unstructure_hook(date, self._unstructure_date)
        self.register_structure_hook(timedelta, self._structure_timedelta)
        self.register_unstructure_hook(timedelta, self._unstructure_timedelta)
        self.register_structure_hook(ReversedEnum, self._structure_reversed_enum)
        self.register_unstructure_hook(ReversedEnum, self._unstructure_reversed_enum)

    def structure_attrs_fromdict(self, obj: Mapping, cl: Type[T]) -> T:
        """Instantiate an attrs class from a mapping.

        Raises human-readable StructureError exceptions on failure.
        """
        try:
            self._eval_str_types(cl)
            return super().structure_attrs_fromdict(obj or {}, cl)
        # NOTE: If exception has occurred while structuring nested attrs class raise it directly without further processing
        except StructureError:
            raise
        except Exception as exc:
            last_frame_locals = sys.exc_info()[2].tb_next.tb_frame.f_locals  # type: ignore
            human_class = last_frame_locals['cl'].__qualname__

            if isinstance(exc, TypeError) and 'required keyword-only' in str(exc):
                message = f"Cannot structure {human_class}: {str(exc)[11:]}"
            else:
                value = last_frame_locals['val']
                human_type = getattr(last_frame_locals['type_'], '__name__', str(last_frame_locals['type_']))
                message = f"Cannot structure {human_class}: {value} is not an instance of {human_type}"

            raise StructureError(message) from exc

    @classmethod
    def _eval_str_types(cls, attrs_class: Type[T]) -> None:
        """Evaluate Attribute.type from string annotations.

        When using attr.dataclass(kw_only=True) decorator attrs set type of generated Optional attribs to their string
        representations making impossible for cattrs to correctly structure them. This class fixes this issue evaluating
        strings back into Type objects before structuring.
        """
        for attrib in attrs_class.__attrs_attrs__:  # type: ignore
            if isinstance(attrib.type, str):
                object.__setattr__(attrib, 'type', eval(attrib.type))  # pylint: disable=eval-used

    def _get_dis_func(self, union: Type) -> Callable[..., Type]:
        """Fetch or try creating a disambiguation function for a Union.

        This algorithm is more strict than default Converter's one and will fail if data contains redundant attributes.
        However lots of complex edge cases are covered.
        """
        union_types = get_args(union)
        if NoneType in union_types:  # type: ignore
            union_types = tuple(e for e in union_types if e is not NoneType)  # type: ignore

        if not all(hasattr(e, '__attrs_attrs__') for e in union_types):
            raise StructureError(
                f'Cannot structure {union}: only unions of attr classes are supported currently. Register a structure hook manually.')

        if len(union_types) < 2:
            raise StructureError(f'Cannot structure {union}: at least two classes required.')

        cls_and_attrs = [(cl, set(at.name for at in fields(cl))) for cl in union_types]

        if len([attrs for _, attrs in cls_and_attrs if len(attrs) == 0]) > 1:
            raise StructureError(f'Cannot structure {union}: at least two classes have no attributes.')

        cls_and_attrs.sort(key=lambda c_a: len(c_a[1]))

        def _dis_func(data: Mapping) -> Type:
            if not isinstance(data, Mapping):  # pylint: disable=isinstance-second-argument-not-valid-type)
                raise StructureError(f'Cannot structure {union}: only mappings are supported as input.')
            for cls, cls_keys in cls_and_attrs:
                if all([data_key in cls_keys for data_key in data]):
                    return cls
            raise StructureError(f'Cannot structure {union}: {data} does not match any of generic arguments')

        return _dis_func

    @staticmethod
    def _structure_decimal(obj: Any, cls: Type) -> Decimal:
        return cls(str(obj))

    @staticmethod
    def _unstructure_decimal(obj: Decimal) -> str:
        return str(obj)

    @staticmethod
    def _structure_literal_true(obj: Any, cls: Type) -> Literal[True]:  # pylint: disable=unused-argument
        if obj in ('true', 'True', True):
            return True
        raise ValueError

    @staticmethod
    def _structure_literal_false(obj: Any, cls: Type) -> Literal[False]:  # pylint: disable=unused-argument
        if obj in ('false', 'False', False):
            return False
        raise ValueError

    @staticmethod
    def _structure_bool(obj: Any, cls: Type) -> bool:
        with suppress(ValueError):
            return Converter._structure_literal_true(obj, cls)
        with suppress(ValueError):
            return Converter._structure_literal_false(obj, cls)
        raise ValueError

    @staticmethod
    def _structure_datetime(obj: Any, cls: Type) -> datetime:  # pylint: disable=unused-argument
        with suppress(ValueError, TypeError):
            return datetime.utcfromtimestamp(float(obj)).replace(tzinfo=timezone.utc)
        with suppress(ParserError):
            return dateutil.parser.parse(obj)
        raise ValueError

    @staticmethod
    def _unstructure_datetime(obj: datetime) -> float:
        return obj.timestamp()

    @staticmethod
    def _structure_date(obj: Any, cls: Type) -> date:  # pylint: disable=unused-argument
        with suppress(ValueError, TypeError):
            return date.fromtimestamp(float(obj))
        with suppress(ParserError):
            dt = dateutil.parser.parse(obj)  # pylint: disable=invalid-name
            return date(year=dt.year, month=dt.month, day=dt.day)
        raise ValueError

    @staticmethod
    def _unstructure_date(obj: date) -> float:
        return datetime(obj.year, obj.month, obj.day).timestamp()

    @staticmethod
    def _structure_timedelta(obj: Any, cls: Type) -> timedelta:  # pylint: disable=unused-argument
        with suppress(TypeError):
            return timedelta(seconds=obj)
        with suppress(TypeError):
            return timedelta(seconds=timeparse(obj))
        raise ValueError

    @staticmethod
    def _unstructure_timedelta(obj: timedelta) -> float:
        return obj.total_seconds()

    @staticmethod
    def _structure_reversed_enum(obj: str, cls: Type[ReversedEnum]) -> ReversedEnum:
        return cls[obj]

    @staticmethod
    def _unstructure_reversed_enum(obj: ReversedEnum) -> str:
        return obj.name
