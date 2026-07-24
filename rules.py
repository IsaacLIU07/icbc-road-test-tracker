"""Filtering engine: decides whether a given date is an acceptable test date."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date

WEEKDAY_NAMES = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]


@dataclass
class DateRange:
    start: date | None  # None means "no lower bound beyond eligibility"
    end: date

    def contains(self, d: date) -> bool:
        if self.start is not None and d < self.start:
            return False
        return d <= self.end


@dataclass
class DateRules:
    allowed_ranges: list[DateRange]
    blocked_weekdays: set[str]
    blocked_dates: set[date]
    earliest_eligible: date

    def is_acceptable(self, d: date) -> bool:
        if d < self.earliest_eligible:
            return False
        if d in self.blocked_dates:
            return False
        if WEEKDAY_NAMES[d.weekday()] in self.blocked_weekdays:
            return False
        return any(r.contains(d) for r in self.allowed_ranges)
