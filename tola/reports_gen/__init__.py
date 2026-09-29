"""Batch T9 -- Client Report Generator.

Deterministic, plain-text report generation from portfolio state.
Pure functions, no I/O.  Stdlib only.  Plain ASCII.
"""

from __future__ import annotations

from tola.reports_gen.daily_brief import daily_brief
from tola.reports_gen.status_report import portfolio_status_report
from tola.reports_gen.weekly_digest import weekly_digest

__all__ = [
    "daily_brief",
    "portfolio_status_report",
    "weekly_digest",
]