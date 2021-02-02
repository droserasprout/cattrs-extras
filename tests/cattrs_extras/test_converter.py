import unittest
from decimal import Decimal
from enum import Enum
from typing import Dict
from typing import List
from typing import Optional
from typing import Union

from attr import dataclass

from cattrs_extras.converter import Converter
from cattrs_extras.converter import ReversedEnum
from cattrs_extras.converter import StructureError


class TestEnum(Enum):
    K1 = 'V1'
    K2 = 'V2'


class TestReversedEnum(ReversedEnum):
    K1 = 'V1'
    K2 = 'V2'


@dataclass(kw_only=True)
class TestNestedDataclass:
    int_value: int


@dataclass(kw_only=True)
class TestDataclass:
    int_value: Optional[int] = None
    float_value: Optional[float] = None
    bool_value: Optional[bool] = None
    decimal_value: Optional[Decimal] = None
    enum_value: Optional[TestEnum] = None
    reversed_enum_value: Optional[TestReversedEnum] = None
    list_value: Optional[List[str]] = None
    dict_value: Optional[Dict[str, str]] = None
    attrs_value: Optional[TestNestedDataclass] = None


class ConverterTest(unittest.TestCase):
    def setUp(self) -> None:
        self.converter = Converter()

    def test_structure_invalid_types_messages(self):
        # Arrange
        subtest_params = [
            [
                {'int_value': 'not_an_int'},
                "Cannot structure TestDataclass: "
                "not_an_int is not an instance of typing.Optional[int]"],
            [
                {'float_value': 'not_a_float'},
                "Cannot structure TestDataclass: "
                "not_a_float is not an instance of typing.Optional[float]"],
            [
                {'bool_value': 'not_a_bool'},
                "Cannot structure TestDataclass: "
                "not_a_bool is not an instance of typing.Optional[bool]"],
            [
                {'decimal_value': 'not_a_decimal'},
                "Cannot structure TestDataclass: "
                "not_a_decimal is not an instance of typing.Optional[decimal.Decimal]"],
            [
                {'enum_value': 'not_an_enum'},
                "Cannot structure TestDataclass: "
                "not_an_enum is not an instance of typing.Optional[tests.cattrs_extras.test_converter.TestEnum]"],
            [
                {'dict_value': 'not_a_dict'},
                "Cannot structure TestDataclass: "
                "not_a_dict is not an instance of typing.Optional[typing.Dict[str, str]]"],
            [
                {'attrs_value': 'not_an_attrs'},
                "Cannot structure TestDataclass: "
                "not_an_attrs is not an instance of typing.Optional[tests.cattrs_extras.test_converter.TestNestedDataclass]"],
            [
                {'attrs_value': {'int_value': 'not_an_int'}},
                "Cannot structure TestNestedDataclass: "
                "not_an_int is not an instance of int"],
            [
                {'attrs_value': {}},
                "Cannot structure TestNestedDataclass: "
                "missing 1 required keyword-only argument: 'int_value'"],
        ]

        for data, message in subtest_params:
            with self.subTest():
                # Act, Assert
                try:
                    self.converter.structure(data, TestDataclass)
                except StructureError as exc:
                    self.assertEqual(message, str(exc))

    def test_union_edge_cases_plain(self):
        @dataclass(kw_only=True)
        class SomeClass:
            a: str
            b: int

        @dataclass(kw_only=True)
        class AnotherClass:
            c: str
            d: int

        @dataclass(kw_only=True)
        class WorkingConfig:
            subconfig: Union[SomeClass, AnotherClass]

        first_config = self.converter.structure({'subconfig': {'a': '', 'b': 1}}, WorkingConfig)
        second_config = self.converter.structure({'subconfig': {'c': '', 'd': 1}}, WorkingConfig)

        self.assertIsInstance(first_config.subconfig, SomeClass)
        self.assertIsInstance(second_config.subconfig, AnotherClass)

    def test_union_edge_cases_shared_attrs_left(self):
        @dataclass(kw_only=True)
        class SomeClass:
            a: str
            b: int

        @dataclass(kw_only=True)
        class AnotherClass:
            a: str
            b: int
            c: int

        @dataclass(kw_only=True)
        class WorkingConfig:
            subconfig: Union[SomeClass, AnotherClass]

        first_config = self.converter.structure({'subconfig': {'a': '', 'b': 1}}, WorkingConfig)
        second_config = self.converter.structure({'subconfig': {'a': '', 'b': 1, 'c': 1}}, WorkingConfig)

        self.assertIsInstance(first_config.subconfig, SomeClass)
        self.assertIsInstance(second_config.subconfig, AnotherClass)

    def test_union_edge_cases_shared_attrs_union(self):
        @dataclass(kw_only=True)
        class SomeClass:
            a: str

        @dataclass(kw_only=True)
        class AnotherClass:
            b: str

        @dataclass(kw_only=True)
        class UnionClass:
            a: str
            b: str

        @dataclass(kw_only=True)
        class WorkingConfig:
            subconfig: Union[SomeClass, AnotherClass, UnionClass]

        first_config = self.converter.structure({'subconfig': {'a': ''}}, WorkingConfig)
        second_config = self.converter.structure({'subconfig': {'b': ''}}, WorkingConfig)
        third_config = self.converter.structure({'subconfig': {'a': '', 'b': ''}}, WorkingConfig)

        assert isinstance(first_config.subconfig, SomeClass)
        assert isinstance(second_config.subconfig, AnotherClass)
        assert isinstance(third_config.subconfig, UnionClass)

    def test_union_edge_cases_shared_attrs_union_different_order_and_optional(self):
        @dataclass(kw_only=True)
        class SomeClass:
            a: str

        @dataclass(kw_only=True)
        class AnotherClass:
            b: str

        @dataclass(kw_only=True)
        class UnionClass:
            a: Optional[str] = None
            b: Optional[str] = None

        @dataclass(kw_only=True)
        class WorkingConfig:
            subconfig: Union[UnionClass, SomeClass, AnotherClass]

        first_config = self.converter.structure({'subconfig': {'a': ''}}, WorkingConfig)
        second_config = self.converter.structure({'subconfig': {'b': ''}}, WorkingConfig)
        third_config = self.converter.structure({'subconfig': {'a': '', 'b': ''}}, WorkingConfig)

        assert isinstance(first_config.subconfig, SomeClass)
        assert isinstance(second_config.subconfig, AnotherClass)
        assert isinstance(third_config.subconfig, UnionClass)

    def test_union_edge_cases_shared_attrs_and_lists(self):
        @dataclass(kw_only=True)
        class SomeClass:
            a: str

        @dataclass(kw_only=True)
        class AnotherClass:
            b: str

        @dataclass(kw_only=True)
        class UnionClass:
            a: Optional[str] = None
            b: Optional[str] = None

        @dataclass(kw_only=True)
        class WorkingConfig:
            subconfig: List[Union[UnionClass, SomeClass, AnotherClass]]

        config = self.converter.structure(
            {
                'subconfig': [
                    {'a': ''},
                    {'b': ''},
                    {'a': '', 'b': ''}]
            },
            WorkingConfig)

        assert isinstance(config.subconfig[0], SomeClass)
        assert isinstance(config.subconfig[1], AnotherClass)
        assert isinstance(config.subconfig[2], UnionClass)

    def test_union_edge_cases_no_match(self):
        @dataclass(kw_only=True)
        class SomeClass:
            a: str

        @dataclass(kw_only=True)
        class AnotherClass:
            b: str

        @dataclass(kw_only=True)
        class UnionClass:
            a: str
            b: str

        @dataclass(kw_only=True)
        class WorkingConfig:
            subconfig: Union[SomeClass, AnotherClass, UnionClass]

        try:
            self.converter.structure({'subconfig': {'c': ''}}, WorkingConfig)
        except StructureError as exc:
            self.assertEqual(
                "Cannot structure typing.Union["
                "tests.cattrs_extras.test_converter.ConverterTest.test_union_edge_cases_no_match.<locals>.SomeClass, "
                "tests.cattrs_extras.test_converter.ConverterTest.test_union_edge_cases_no_match.<locals>.AnotherClass, "
                "tests.cattrs_extras.test_converter.ConverterTest.test_union_edge_cases_no_match.<locals>.UnionClass]: "
                "{'c': ''} does not match any of generic arguments",
                str(exc))
        else:
            raise AssertionError
