from datetime import time
from typing import Union

MINIMUM_WAGE = 29.12
ISRAELI_JEWISH = 1  # Revision required after holiday times feature is added
REGULAR_HOUR_BASIS = 8
FIRST_OVERTIME_AMOUNT = 2
FIRST_OVERTIME_PAY = 1.25
SECOND_OVERTIME_PAY = 1.50
NIGHT_HOUR_BASIS = 7
NIGHT_START = time(hour=22)
NIGHT_END = time(hour=6)
NIGHT_MIN_LEN = time(hour=2)
WEEK_WORKING_HOURS = 42
STANDARD_TRANSPORT = 11.8
MAXIMUM_TRANSPORT = 22.6

OFF_DAY_ADDITION = 0.5
SATURDAY = 5
HOURS_SECONDS_RATIO = 3600

NUMERIC = Union[float, int]
HOUR_FORMAT = '%H:%M:%S'
ALT_HOUR_FORMAT = '%H:%M'
