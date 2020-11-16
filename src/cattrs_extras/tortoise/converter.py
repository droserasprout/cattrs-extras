import importlib
from datetime import date
from datetime import datetime
from datetime import timedelta
from types import ModuleType
from typing import Any
from typing import Dict
from typing import List
from typing import Optional
from typing import Type
from typing import Union

import tortoise
from tortoise import fields

from cattrs_extras.converter import Converter
from cattrs_extras.tortoise.fields import ReversedCharEnumFieldInstance

JSONType = Union[Dict[str, Any], List[Dict[str, Any]]]


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

            if field_name in obj:

                known_type = None
                if isinstance(field, fields.DatetimeField):
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

            if isinstance(field_value, tortoise.QuerySet):
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
