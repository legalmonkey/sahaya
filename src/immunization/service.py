"""Deterministic child immunization evaluation service.

Evaluates vaccination status (received, due, overdue, upcoming) against the official
National Immunization Schedule (UIP) without hallucination or hardcoded medical assumptions.
"""
from __future__ import annotations

import datetime
from dataclasses import asdict, dataclass, field
from typing import Any

from .schedule import UIP_SCHEDULE, VaccineDose, match_vaccine_dose


class ImmunizationError(ValueError):
    """Raised for invalid input parameters (e.g. missing/malformed DOB)."""


@dataclass
class DoseRecord:
    vaccine_id: str
    vaccine_name: str
    recommended_age: str
    status: str                              # "received" | "due" | "overdue" | "upcoming"
    date_given: str | None = None
    due_date: str | None = None
    days_overdue: int | None = None
    protects_against: str = ""
    route_and_site: str = ""


@dataclass
class ImmunizationStatus:
    child_dob: str
    age_days: int
    age_weeks: int
    age_months: int
    age_display: str
    received: list[dict[str, Any]] = field(default_factory=list)
    due: list[dict[str, Any]] = field(default_factory=list)
    overdue: list[dict[str, Any]] = field(default_factory=list)
    upcoming: list[dict[str, Any]] = field(default_factory=list)
    unrecognized_doses: list[dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "child_dob": self.child_dob,
            "age_days": self.age_days,
            "age_weeks": self.age_weeks,
            "age_months": self.age_months,
            "age_display": self.age_display,
            "received": self.received,
            "due": self.due,
            "overdue": self.overdue,
            "upcoming": self.upcoming,
            "unrecognized_doses": self.unrecognized_doses,
        }


def _parse_date(d: str | datetime.date | None) -> datetime.date:
    if d is None:
        raise ImmunizationError("Date cannot be None.")
    if isinstance(d, datetime.date) and not isinstance(d, datetime.datetime):
        return d
    if isinstance(d, datetime.datetime):
        return d.date()
    if isinstance(d, str):
        cleaned = d.strip()
        if not cleaned:
            raise ImmunizationError("Date string cannot be empty.")
        for fmt in ("%Y-%m-%d", "%d-%m-%Y", "%d/%m/%Y", "%Y/%m/%d"):
            try:
                return datetime.datetime.strptime(cleaned, fmt).date()
            except ValueError:
                continue
        raise ImmunizationError(f"Invalid date format: {d!r}. Expected YYYY-MM-DD.")
    raise ImmunizationError(f"Unsupported date type: {type(d)}")


def _format_age(days: int) -> str:
    if days < 7:
        return f"{days} day{'s' if days != 1 else ''}"
    if days < 60:
        w = days // 7
        return f"{w} week{'s' if w != 1 else ''}"
    if days < 730:
        m = days // 30
        return f"{m} month{'s' if m != 1 else ''}"
    y = days // 365
    return f"{y} year{'s' if y != 1 else ''}"


def evaluate_child_immunization(
    dob: str | datetime.date,
    dose_history: list[dict[str, Any]] | None,
    current_date: str | datetime.date | None = None,
) -> ImmunizationStatus:
    """Evaluate child's vaccination history against the UIP schedule.

    Args:
        dob: Child's Date of Birth (YYYY-MM-DD or date object)
        dose_history: List of dose history records e.g. [{"vaccine": "BCG", "date_given": "2026-01-01"}]
        current_date: Reference evaluation date (defaults to today)

    Returns:
        ImmunizationStatus with categorized doses.
    """
    if not dob:
        raise ImmunizationError("Child DOB is missing or empty.")

    dob_date = _parse_date(dob)
    ref_date = _parse_date(current_date) if current_date is not None else datetime.date.today()

    if dob_date > ref_date:
        raise ImmunizationError(f"Child DOB ({dob_date}) cannot be in the future (reference date: {ref_date}).")

    age_days = (ref_date - dob_date).days
    age_weeks = age_days // 7
    age_months = age_days // 30
    age_display = _format_age(age_days)

    # Sanitize dose_history
    history: list[dict[str, Any]] = []
    if dose_history is not None:
        if isinstance(dose_history, list):
            for item in dose_history:
                if isinstance(item, dict):
                    history.append(item)
        elif isinstance(dose_history, dict):
            history.append(dose_history)

    # Map received doses by matched VaccineDose id
    received_map: dict[str, dict[str, Any]] = {}
    unrecognized: list[dict[str, Any]] = []

    for entry in history:
        v_name = entry.get("vaccine") or entry.get("name") or ""
        matched = match_vaccine_dose(str(v_name))
        date_given = entry.get("date_given") or entry.get("date")
        due_date = entry.get("due_date")

        if matched:
            received_map[matched.id] = {
                "vaccine_id": matched.id,
                "vaccine_name": matched.name,
                "recommended_age": matched.recommended_age_str,
                "status": "received",
                "date_given": str(date_given) if date_given else None,
                "due_date": str(due_date) if due_date else None,
                "protects_against": matched.protects_against,
                "route_and_site": matched.route_and_site,
            }
        else:
            if v_name:
                unrecognized.append({
                    "raw_name": str(v_name),
                    "date_given": str(date_given) if date_given else None,
                })

    received_list: list[dict[str, Any]] = list(received_map.values())
    due_list: list[dict[str, Any]] = []
    overdue_list: list[dict[str, Any]] = []
    upcoming_list: list[dict[str, Any]] = []

    for dose in UIP_SCHEDULE:
        if dose.id in received_map:
            continue  # Already received

        # Calculate expected due date from DOB
        expected_due = dob_date + datetime.timedelta(days=dose.min_age_days)
        expected_due_str = expected_due.isoformat()

        if age_days < dose.min_age_days:
            # Future milestone
            upcoming_list.append({
                "vaccine_id": dose.id,
                "vaccine_name": dose.name,
                "recommended_age": dose.recommended_age_str,
                "status": "upcoming",
                "due_date": expected_due_str,
                "days_until_due": dose.min_age_days - age_days,
                "protects_against": dose.protects_against,
                "route_and_site": dose.route_and_site,
            })
        elif age_days >= dose.overdue_after_days:
            # Past the overdue threshold and not given
            days_over = age_days - dose.overdue_after_days
            overdue_list.append({
                "vaccine_id": dose.id,
                "vaccine_name": dose.name,
                "recommended_age": dose.recommended_age_str,
                "status": "overdue",
                "due_date": expected_due_str,
                "days_overdue": days_over,
                "protects_against": dose.protects_against,
                "route_and_site": dose.route_and_site,
            })
        else:
            # Within the eligible due window
            due_list.append({
                "vaccine_id": dose.id,
                "vaccine_name": dose.name,
                "recommended_age": dose.recommended_age_str,
                "status": "due",
                "due_date": expected_due_str,
                "protects_against": dose.protects_against,
                "route_and_site": dose.route_and_site,
            })

    return ImmunizationStatus(
        child_dob=dob_date.isoformat(),
        age_days=age_days,
        age_weeks=age_weeks,
        age_months=age_months,
        age_display=age_display,
        received=received_list,
        due=due_list,
        overdue=overdue_list,
        upcoming=upcoming_list,
        unrecognized_doses=unrecognized,
    )
