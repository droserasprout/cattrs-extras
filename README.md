# cattrs-extras

This package contains advanced converter classes for [cattrs](https://github.com/Tinche/cattrs), a great serialization library built around [attrs](https://github.com/python-attrs/attrs).

## Key features 

* Support for additional types: Decimal, bool, datetime, date, timedelta
* Alternative structuring algorithm capable of handling complex Unions without registering additional hooks 
* Human-readable exceptions on structuring failure
* Support for Tortoise ORM models serialization (including relations)
* Additional class and Tortoise field for reversed enumerations (serialized to member name instead of value)

## Installation

```text
 ==> cattrs-extras makefile

 DEV=1           Install dev dependencies

all:             Run a whole CI pipeline (default)
install:         Install project
lint:            Lint with all tools
isort:           Lint with isort
black:           Lint with black
flake:           Lint with flake8
mypy:            Lint with mypy
test:            Run test suite
cover:           Print coverage for the current branch
build:           Build wheel Python package
release-patch:   Release patch version
release-minor:   Release minor version
release-major:   Release major version
help:            Show this help
```

## Usage

```python
from enum import Enum
from decimal import Decimal
from datetime import datetime
from attr import dataclass
from cattrs_extras.converter import Converter

class Color(Enum):
    RED = 'RED'
    GREEN = 'GREEN'

@dataclass(kw_only=True)
class Apple:
    weight: Decimal
    color: Color
    best_before: datetime
    sweet: bool

converter = Converter()
raw_apple = {
    'weight': '200.5',
    'color': 'RED',
    'best_before': '2020-04-02T12:00:00',
    'sweet': 'true'
}

apple = converter.structure(raw_apple, Apple)
assert apple == Apple(weight=Decimal('200.5'), color=Color.RED, best_before=datetime(2020, 4, 2, 12, 0), sweet=True)

raw_apple = converter.unstructure(apple)
assert raw_apple == {'weight': '200.5', 'color': 'RED', 'best_before': 1585818000.0, 'sweet': True}
```


## Tortoise ORM

Important note: Tortoise ORM has chosen [Pydantic](https://github.com/samuelcolvin/pydantic) as a serialization library, so better to stick with it. However, Pydantic support is still WIP; you can check the current status [here](https://tortoise-orm.readthedocs.io/en/latest/contrib/pydantic.html).

```python
from cattrs_extras.tortoise.converter import TortoiseConverter
from cattrs_extras.tortoise.model import Model
from tortoise import fields

# TODO: ReversedCharEnumField example
class AppleModel(Model):
    id = fields.IntField(pk=True)
    weight = fields.DecimalField(20, 10)
    color = fields.CharEnumField(Color)
    best_before = fields.DateField()
    sweet = fields.BooleanField()

# NOTE: Replace with module name of your models
tortoise_converter = TortoiseConverter('cattrs_extras.tortoise.model')

apple_model = tortoise_converter.structure(raw_apple, AppleModel)
assert apple_model == AppleModel(weight=Decimal('200.5'), color=Color.RED, best_before=datetime(2020, 4, 2, 12, 0), sweet=True)

raw_apple = tortoise_converter.unstructure(apple_model)
assert raw_apple == {'id': None, 'weight': '200.5', 'color': 'RED', 'best_before': 1585774800.0, 'sweet': True}
```

## Limitations

* [PEP 563 – Postponed Evaluation of Annotations](https://www.python.org/dev/peps/pep-0563/) is not supported. Attempt to import `__future__.annotations` in module containing models will lead to exception. However, you can still use strings as typehints.
* Backward relations in Tortoise models are ignored during structuring even if fetched. Not sure if we should fix it.