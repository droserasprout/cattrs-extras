import importlib
from contextlib import suppress
from datetime import date
from datetime import datetime
from datetime import timedelta
from types import ModuleType
from typing import Any
from typing import Callable
from typing import Dict
from typing import List
from typing import Mapping
from typing import Optional
from typing import Type
from typing import Union

import tortoise
from tortoise import fields
from tortoise.queryset import QuerySet
from typing_inspect import get_args  # type: ignore

from cattrs_extras.converter import Converter
from cattrs_extras.converter import StructureError
from cattrs_extras.tortoise.fields import ReversedCharEnumFieldInstance

JSONType = Union[Dict[str, Any], List[Dict[str, Any]]]
NoneType = type(None)


# TODO: Set datetime timezone awareness?
# TODO: Ability to format timestamps as strings?
class TortoiseConverter(Converter):
    def __init__(self, models: str) -> None:
        super().__init__()
        self._models: ModuleType = importlib.import_module(models)
        self.register_structure_hook(tortoise.Model, self._structure_tortoise_model)
        self.register_unstructure_hook(tortoise.Model, self._unstructure_tortoise_model)

    def _structure_tortoise_model(self, obj: Dict[str, Any], cls: Type[tortoise.Model]) -> tortoise.Model:

        result_dict: Dict[str, Any] = {}
        saved_in_db = False

        for field_name, field in cls._meta.fields_map.items():

            field_value = obj.get(field_name)

            if field.pk and field.generated:
                if field_value is not None:
                    saved_in_db = True
                else:
                    continue

            if all(
                [
                    field.null is False,
                    field_value is None,
                    not (isinstance(field, fields.DatetimeField) and field.auto_now_add),
                ]
            ):
                raise StructureError(f'Cannot structure {cls.__qualname__}: "{field_name}" field is not nullable')

            if field_name not in obj:
                continue

            known_type = None
            if isinstance(field, fields.BooleanField):
                known_type = Optional[bool] if field.null else bool
            elif isinstance(field, fields.DatetimeField):
                known_type = Optional[datetime] if field.null else datetime
            elif isinstance(field, fields.DateField):
                known_type = Optional[date] if field.null else date
            elif isinstance(field, fields.TimeDeltaField):
                known_type = Optional[timedelta] if field.null else timedelta
            elif isinstance(field, (fields.data.CharEnumFieldInstance, ReversedCharEnumFieldInstance)):
                known_type = Optional[field.enum_type] if field.null else field.enum_type

            if known_type is not None:
                result_dict[field_name] = self.structure(
                    obj=field_value,
                    cl=known_type,  # type: ignore
                )

            # FIXME: tortoise.exceptions.ConfigurationError: You can't set backward relations through init, change related model instead
            # Should we try to hack it somehow or just ignore backward relations even if fetched?
            elif isinstance(field, fields.relational.BackwardFKRelation):
                continue

            elif isinstance(field, fields.relational.RelationalField) and field_value:
                # FIXME: Hinted as Type['Model']
                if isinstance(field.model, str):
                    field_model = getattr(self._models, field.model.split('.')[-1])
                else:
                    field_model = field.model

                related_model = self.structure(
                    obj=field_value,
                    cl=field_model,
                )
                related_model._saved_in_db = True
                result_dict[field_name] = related_model

            else:
                result_dict[field_name] = field_value

        model = cls(**result_dict)
        model._saved_in_db = saved_in_db
        return model

    def _unstructure_tortoise_model(self, obj: tortoise.Model) -> JSONType:

        result_dict = {}

        for field_name, field in obj.__class__._meta.fields_map.items():

            field_value = getattr(obj, field_name, None)

            if isinstance(field_value, QuerySet):
                continue

            if isinstance(field, fields.relational.BackwardFKRelation):
                try:
                    result_dict[field_name] = self.unstructure(field_value.related_objects)
                except tortoise.exceptions.NoValuesFetched:
                    pass

            elif isinstance(field, fields.relational.RelationalField):
                try:
                    result_dict[field_name] = self.unstructure(field_value)
                except tortoise.exceptions.NoValuesFetched:
                    pass

            else:
                result_dict[field_name] = self.unstructure(field_value)

        return result_dict

    # FIXME: super() copypaste
    @staticmethod
    def _get_dis_func(union: Type) -> Callable[..., Type]:

        with suppress(StructureError):
            return super()._get_dis_func(union)

        union_types = get_args(union)
        if NoneType in union_types:  # type: ignore
            union_types = tuple(e for e in union_types if e is not NoneType)  # type: ignore

        if not all(hasattr(e, '_meta') for e in union_types):
            raise StructureError(
                f'Cannot structure {union}: only unions of attr classes or tortoise models are supported currently. '
                f'Register a structure hook manually.'
            )

        if len(union_types) < 2:
            raise StructureError(f'Cannot structure {union}: at least two classes required.')

        cls_and_attrs = [(cl, set(at for at in cl._meta.fields)) for cl in union_types]

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
