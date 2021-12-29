from datetime import date
from datetime import datetime
from datetime import timedelta
from decimal import Decimal
from enum import Enum
from unittest import TestCase

from tortoise import fields  # type: ignore

from cattrs_extras.converter import ReversedEnum
from cattrs_extras.tortoise.converter import TortoiseConverter
from cattrs_extras.tortoise.fields import ReversedCharEnumField
from cattrs_extras.tortoise.model import Model


class SomeEnum(Enum):
    K1 = 'V1'


class SomeReversedEnum(ReversedEnum):
    K2 = 'V2'


class SomeModel(Model):
    id = fields.IntField(pk=True)
    string = fields.CharField(255, null=True)
    decimal = fields.DecimalField(20, 10, null=True)
    enum = fields.CharEnumField(SomeEnum, null=True)
    reversed_enum = ReversedCharEnumField(SomeReversedEnum, null=True)
    date = fields.DateField(null=True)
    datetime = fields.DatetimeField(null=True)
    timedelta = fields.TimeDeltaField(null=True)
    bool = fields.BooleanField(null=True)
    relation = fields.ForeignKeyField('models.SomeModel', 'id', null=True)

    class Meta:  # pylint: disable=too-few-public-methods)
        table = 'test_models'


class TortoiseConverterTest(TestCase):
    def setUp(self) -> None:
        self.converter = TortoiseConverter('tests.cattrs_extras.test_tortoise')

    def test_tortoise_unstructure(self):
        # Arrange
        model = SomeModel(
            id=1,
            string='test',
            decimal=Decimal('1.23'),
            enum=SomeEnum.K1,
            reversed_enum=SomeReversedEnum.K2,
            date=date(2020, 1, 2),
            datetime=datetime(2020, 1, 2, 3, 4, 5),
            timedelta=timedelta(hours=1),
            bool=True,
        )

        # Act
        json = self.converter.unstructure(model)

        # Assert
        self.assertEqual(
            {
                'bool': True,
                'date': 1577923200.0,
                'datetime': 1577934245.0,
                'timedelta': 3600.0,
                'decimal': '1.23',
                'enum': 'V1',
                'reversed_enum': 'K2',
                'id': 1,
                'relation': None,
                'string': 'test',
            },
            json,
        )

    def test_tortoise_unstructure_optional(self):
        # Arrange
        model = SomeModel(
            string=None,
            decimal=None,
            enum=None,
            reversed_enum=None,
            date=None,
            datetime=None,
            timedelta=None,
            bool=None,
        )

        # Act
        json = self.converter.unstructure(model)

        # Assert
        self.assertEqual(
            {
                'bool': None,
                'date': None,
                'datetime': None,
                'timedelta': None,
                'decimal': None,
                'enum': None,
                'reversed_enum': None,
                'id': None,
                'relation': None,
                'string': None,
            },
            json,
        )

    def test_tortoise_structure(self):
        # Arrange
        json = {
            'bool': True,
            'date': 1577912400.0,
            'datetime': 1577923445.0,
            'timedelta': 3600.0,
            'decimal': '1.23',
            'enum': 'V1',
            'reversed_enum': 'K2',
            'id': 1,
            'string': 'test',
        }

        # Act
        model = self.converter.structure(json, SomeModel)

        # Assert
        self.assertEqual(
            SomeModel(
                id=1,
                string='test',
                decimal=Decimal('1.23'),
                enum=SomeEnum.K1,
                reversed_enum=SomeReversedEnum.K2,
                date=date(2020, 1, 2),
                datetime=datetime(2020, 1, 2, 3, 4, 5),
                timedelta=timedelta(hours=1),
                bool=True,
            ),
            model,
        )

    def test_tortoise_structure_humanreadable(self):
        # Arrange
        json = {
            'bool': 'false',
            'date': '2020-01-01',
            'datetime': '2020-01-01T00:00:00',
            'timedelta': '1h',
            'decimal': '1.23',
            'enum': 'V1',
            'reversed_enum': 'K2',
            'id': 1,
            'string': 'test',
        }

        # Act
        model = self.converter.structure(json, SomeModel)

        # Assert
        self.assertEqual(
            SomeModel(
                id=1,
                string='test',
                decimal=Decimal('1.23'),
                enum=SomeEnum.K1,
                reversed_enum=SomeReversedEnum.K2,
                date=date(2020, 1, 2),
                datetime=datetime(2020, 1, 2, 3, 4, 5),
                timedelta=timedelta(hours=1),
                bool=False,
            ),
            model,
        )

    def test_tortoise_structure_optional(self):
        # Arrange
        json = {
            'bool': None,
            'date': None,
            'datetime': None,
            'timedelta': None,
            'decimal': None,
            'enum': None,
            'reversed_enum': None,
            'id': None,
            'string': None,
        }

        # Act
        model = self.converter.structure(json, SomeModel)

        # Assert
        self.assertEqual(
            SomeModel(
                string=None,
                decimal=None,
                enum=None,
                reversed_enum=None,
                date=None,
                datetime=None,
                timedelta=None,
                bool=None,
            ),
            model,
        )

    def test_tortoise_structure_relation(self):
        # Arrange
        json = {
            'bool': True,
            'date': 1577912400.0,
            'datetime': 1577923445.0,
            'timedelta': 3600.0,
            'decimal': '1.23',
            'enum': 'V1',
            'reversed_enum': 'K2',
            'id': 1,
            'string': 'test',
            'relation': {
                'bool': False,
                'date': 1577912400.0,
                'datetime': 1577923445.0,
                'timedelta': 3600.0,
                'decimal': '1.23',
                'enum': 'V1',
                'reversed_enum': 'K2',
                'id': 2,
            },
        }

        # Act
        model = self.converter.structure(json, SomeModel)

        # Assert
        self.assertEqual(
            SomeModel(
                id=1,
                string='test',
                decimal=Decimal('1.23'),
                enum=SomeEnum.K1,
                reversed_enum=SomeReversedEnum.K2,
                date=date(2020, 1, 2),
                datetime=datetime(2020, 1, 2, 3, 4, 5),
                timedelta=timedelta(hours=1),
                bool=True,
            ),
            model,
        )
        self.assertEqual(True, model._saved_in_db)

        self.assertEqual(
            SomeModel(
                id=2,
                string='test',
                decimal=Decimal('1.23'),
                enum=SomeEnum.K1,
                reversed_enum=SomeReversedEnum.K2,
                date=date(2020, 1, 2),
                datetime=datetime(2020, 1, 2, 3, 4, 5),
                timedelta=timedelta(hours=1),
                bool=False,
            ),
            model.relation,
        )
        self.assertEqual(True, model._saved_in_db)
