"""Insights (aggregated energy) model for DeWarmte integration."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass
class InsightsSummary:
    """Year-to-date totals from GET /customer/products/{id}/insights/.

    The official app shows these numbers (Insights -> Year).
    For an MP the live status field `electric_backup_usage` stays 0.0 even
    while the element runs, so the insights are the only source for the
    element's energy.
    """

    electric_backup_usage_sum: float
    heat_sum: float
    electricity_sum: float

    @classmethod
    def from_api_response(cls, data: dict[str, Any]) -> "InsightsSummary":
        """Parse an insights response.

        Strict on purpose: a missing field raises KeyError naming it, so a
        schema change shows up in the log instead of as a silent 0.
        """
        return cls(
            electric_backup_usage_sum=float(data["electric_backup_usage_sum"]),
            heat_sum=float(data["heat_sum"]),
            electricity_sum=float(data["electricity_sum"]),
        )
