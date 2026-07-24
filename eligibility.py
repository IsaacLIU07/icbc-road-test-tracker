"""Computes the earliest date someone is legally allowed to book a BC road test."""

from __future__ import annotations

from datetime import date

from dateutil.relativedelta import relativedelta


def min_eligible_date(l_issue_date: date, completed_driver_training_course: bool) -> date:
    months = 9 if completed_driver_training_course else 12
    return l_issue_date + relativedelta(months=months)
