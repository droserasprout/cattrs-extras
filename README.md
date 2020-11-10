# cattrs-extras

This package contains advanced converter classes for [cattrs](https://github.com/Tinche/cattrs), a great serialization library built around [attrs](https://github.com/python-attrs/attrs).

## Key features 

* Support for additional types: Decimal, bool, datetime, date, timedelta
* Alternative structuring algorithm capable of handling complex Unions without registering additional hooks 
* Human-readable exceptions on structuring failure
* Support for Tortoise ORM models serialization (including relations)

## Installation

```shell-script
PYTHON=python make install  # pyenv is used by default
make build
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

Important note: Tortoise ORM have chosen [pydantic](https://github.com/samuelcolvin/pydantic) as a serialization library so better to stick with it. However pydantic support is still WIP, you can check current status [here](https://tortoise-orm.readthedocs.io/en/latest/contrib/pydantic.html).

```python
from cattrs_extras.tortoise.converter import TortoiseConverter
from cattrs_extras.tortoise.model import Model
from tortoise import fields

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