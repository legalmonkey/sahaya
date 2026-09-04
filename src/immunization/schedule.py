"""Official National Immunization Schedule (UIP) definitions and vaccine rules.

Derived strictly from the official Ministry of Health and Family Welfare (MoHFW)
National Immunization Schedule (data/raw/Current_UIP_Schedule.pdf and Immunization Handbook).
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Sequence


@dataclass(frozen=True)
class VaccineDose:
    id: str                                  # Canonical ID (e.g. "BCG", "OPV-1", "PENTAVALENT-1")
    name: str                                # Display name (e.g. "BCG", "Pentavalent 1st dose")
    vaccine_group: str                       # Group (e.g. "BCG", "OPV", "Pentavalent", "MR")
    dose_number: int                         # Dose number within series (0, 1, 2, 3, etc.)
    recommended_age_str: str                 # e.g. "At birth", "6 weeks", "10 weeks", "14 weeks", "9-12 months"
    min_age_days: int                        # Minimum eligible age in days
    overdue_after_days: int                  # Age after which missing this dose is considered overdue
    max_age_days: int | None                 # Maximum eligible age in days (if any)
    protects_against: str                    # Target disease(s)
    route_and_site: str                      # Route and site per handbook
    aliases: tuple[str, ...] = field(default_factory=tuple)


# Official UIP Schedule list in chronological milestone order
UIP_SCHEDULE: list[VaccineDose] = [
    # --- At Birth ---
    VaccineDose(
        id="BCG",
        name="BCG",
        vaccine_group="BCG",
        dose_number=1,
        recommended_age_str="At birth (up to 1 year)",
        min_age_days=0,
        overdue_after_days=28,  # >28 days without birth dose is overdue for birth timeline
        max_age_days=365,       # Up to 1 year of age
        protects_against="Childhood Tuberculosis",
        route_and_site="Intra-dermal, Left upper arm",
        aliases=("bcg", "bcg vaccine", "bacillus calmette guerin"),
    ),
    VaccineDose(
        id="HEPB-0",
        name="Hepatitis B (Birth dose)",
        vaccine_group="Hepatitis B",
        dose_number=0,
        recommended_age_str="At birth (within 24 hours)",
        min_age_days=0,
        overdue_after_days=1,   # Must be given within 24 hours of birth
        max_age_days=1,
        protects_against="Hepatitis B",
        route_and_site="Intra-muscular, Anterolateral side of mid-thigh",
        aliases=("hepb-0", "hepb 0", "hepatitis b birth dose", "hep b 0", "hep b birth", "hepb"),
    ),
    VaccineDose(
        id="OPV-0",
        name="OPV-0 (Birth dose)",
        vaccine_group="OPV",
        dose_number=0,
        recommended_age_str="At birth (within first 15 days)",
        min_age_days=0,
        overdue_after_days=15,  # Within first 15 days
        max_age_days=15,
        protects_against="Poliomyelitis",
        route_and_site="Oral, 2 drops",
        aliases=("opv-0", "opv 0", "oral polio 0", "oral polio birth dose", "opv birth"),
    ),

    # --- 6 Weeks (42 days) ---
    VaccineDose(
        id="OPV-1",
        name="OPV-1",
        vaccine_group="OPV",
        dose_number=1,
        recommended_age_str="6 weeks",
        min_age_days=42,
        overdue_after_days=70,  # 10 weeks
        max_age_days=1825,      # 5 years
        protects_against="Poliomyelitis",
        route_and_site="Oral, 2 drops",
        aliases=("opv-1", "opv 1", "oral polio 1", "opv1"),
    ),
    VaccineDose(
        id="PENTAVALENT-1",
        name="Pentavalent-1",
        vaccine_group="Pentavalent",
        dose_number=1,
        recommended_age_str="6 weeks",
        min_age_days=42,
        overdue_after_days=70,
        max_age_days=365,
        protects_against="Diphtheria, Pertussis, Tetanus, Hepatitis B, Hib pneumonia & meningitis",
        route_and_site="Intra-muscular, Anterolateral side of mid-thigh",
        aliases=("pentavalent-1", "pentavalent 1", "penta-1", "penta 1", "penta1", "dpt-1", "dpt 1"),
    ),
    VaccineDose(
        id="ROTA-1",
        name="Rotavirus-1",
        vaccine_group="Rotavirus",
        dose_number=1,
        recommended_age_str="6 weeks",
        min_age_days=42,
        overdue_after_days=70,
        max_age_days=365,
        protects_against="Rotavirus Diarrhoea",
        route_and_site="Oral, 5 drops / 2.5 ml as per formulation",
        aliases=("rotavirus-1", "rotavirus 1", "rota-1", "rota 1", "rota1"),
    ),
    VaccineDose(
        id="FIPV-1",
        name="fIPV-1 / IPV-1",
        vaccine_group="IPV",
        dose_number=1,
        recommended_age_str="6 weeks (or 14 weeks per state schedule)",
        min_age_days=42,
        overdue_after_days=98,
        max_age_days=365,
        protects_against="Poliomyelitis",
        route_and_site="Intra-dermal, Right upper arm",
        aliases=("fipv-1", "fipv 1", "ipv-1", "ipv 1", "fipv1", "ipv1", "fractional ipv 1"),
    ),

    # --- 10 Weeks (70 days) ---
    VaccineDose(
        id="OPV-2",
        name="OPV-2",
        vaccine_group="OPV",
        dose_number=2,
        recommended_age_str="10 weeks",
        min_age_days=70,
        overdue_after_days=98,  # 14 weeks
        max_age_days=1825,
        protects_against="Poliomyelitis",
        route_and_site="Oral, 2 drops",
        aliases=("opv-2", "opv 2", "oral polio 2", "opv2"),
    ),
    VaccineDose(
        id="PENTAVALENT-2",
        name="Pentavalent-2",
        vaccine_group="Pentavalent",
        dose_number=2,
        recommended_age_str="10 weeks",
        min_age_days=70,
        overdue_after_days=98,
        max_age_days=365,
        protects_against="Diphtheria, Pertussis, Tetanus, Hepatitis B, Hib",
        route_and_site="Intra-muscular, Anterolateral side of mid-thigh",
        aliases=("pentavalent-2", "pentavalent 2", "penta-2", "penta 2", "penta2", "dpt-2", "dpt 2"),
    ),
    VaccineDose(
        id="ROTA-2",
        name="Rotavirus-2",
        vaccine_group="Rotavirus",
        dose_number=2,
        recommended_age_str="10 weeks",
        min_age_days=70,
        overdue_after_days=98,
        max_age_days=365,
        protects_against="Rotavirus Diarrhoea",
        route_and_site="Oral",
        aliases=("rotavirus-2", "rotavirus 2", "rota-2", "rota 2", "rota2"),
    ),

    # --- 14 Weeks (98 days) ---
    VaccineDose(
        id="OPV-3",
        name="OPV-3",
        vaccine_group="OPV",
        dose_number=3,
        recommended_age_str="14 weeks",
        min_age_days=98,
        overdue_after_days=180, # 6 months
        max_age_days=1825,
        protects_against="Poliomyelitis",
        route_and_site="Oral, 2 drops",
        aliases=("opv-3", "opv 3", "oral polio 3", "opv3"),
    ),
    VaccineDose(
        id="PENTAVALENT-3",
        name="Pentavalent-3",
        vaccine_group="Pentavalent",
        dose_number=3,
        recommended_age_str="14 weeks",
        min_age_days=98,
        overdue_after_days=180,
        max_age_days=365,
        protects_against="Diphtheria, Pertussis, Tetanus, Hepatitis B, Hib",
        route_and_site="Intra-muscular, Anterolateral side of mid-thigh",
        aliases=("pentavalent-3", "pentavalent 3", "penta-3", "penta 3", "penta3", "dpt-3", "dpt 3"),
    ),
    VaccineDose(
        id="ROTA-3",
        name="Rotavirus-3",
        vaccine_group="Rotavirus",
        dose_number=3,
        recommended_age_str="14 weeks",
        min_age_days=98,
        overdue_after_days=180,
        max_age_days=365,
        protects_against="Rotavirus Diarrhoea",
        route_and_site="Oral",
        aliases=("rotavirus-3", "rotavirus 3", "rota-3", "rota 3", "rota3"),
    ),
    VaccineDose(
        id="FIPV-2",
        name="fIPV-2 / IPV-2",
        vaccine_group="IPV",
        dose_number=2,
        recommended_age_str="14 weeks",
        min_age_days=98,
        overdue_after_days=180,
        max_age_days=365,
        protects_against="Poliomyelitis",
        route_and_site="Intra-dermal, Right upper arm",
        aliases=("fipv-2", "fipv 2", "ipv-2", "ipv 2", "fipv2", "ipv2", "fractional ipv 2"),
    ),

    # --- 9 to 12 Months (270 - 365 days) ---
    VaccineDose(
        id="MR-1",
        name="Measles-Rubella-1 (MR-1)",
        vaccine_group="MR",
        dose_number=1,
        recommended_age_str="9-12 months",
        min_age_days=270,
        overdue_after_days=365,
        max_age_days=1825,
        protects_against="Measles and Rubella",
        route_and_site="Sub-cutaneous, Right upper arm",
        aliases=("mr-1", "mr 1", "measles-1", "measles 1", "mr1", "measles1", "measles"),
    ),
    VaccineDose(
        id="JE-1",
        name="Japanese Encephalitis-1 (JE-1)",
        vaccine_group="JE",
        dose_number=1,
        recommended_age_str="9-12 months (in endemic districts)",
        min_age_days=270,
        overdue_after_days=365,
        max_age_days=5475,
        protects_against="Japanese Encephalitis",
        route_and_site="Sub-cutaneous, Left upper arm",
        aliases=("je-1", "je 1", "japanese encephalitis 1", "je1"),
    ),
    VaccineDose(
        id="VITA-1",
        name="Vitamin A (1st Dose)",
        vaccine_group="Vitamin A",
        dose_number=1,
        recommended_age_str="9 months (with MR-1)",
        min_age_days=270,
        overdue_after_days=365,
        max_age_days=1825,
        protects_against="Vitamin A Deficiency / Night Blindness",
        route_and_site="Oral, 1 ml (1 lakh IU)",
        aliases=("vita-1", "vitamin a 1", "vit a 1", "vitamin a 1st dose", "vita1", "vit a dose 1"),
    ),

    # --- 16 to 24 Months (480 - 730 days) ---
    VaccineDose(
        id="MR-2",
        name="Measles-Rubella-2 (MR-2)",
        vaccine_group="MR",
        dose_number=2,
        recommended_age_str="16-24 months",
        min_age_days=480,
        overdue_after_days=730,
        max_age_days=1825,
        protects_against="Measles and Rubella",
        route_and_site="Sub-cutaneous, Right upper arm",
        aliases=("mr-2", "mr 2", "measles-2", "measles 2", "mr2", "measles2", "mr booster"),
    ),
    VaccineDose(
        id="JE-2",
        name="Japanese Encephalitis-2 (JE-2)",
        vaccine_group="JE",
        dose_number=2,
        recommended_age_str="16-24 months (in endemic districts)",
        min_age_days=480,
        overdue_after_days=730,
        max_age_days=5475,
        protects_against="Japanese Encephalitis",
        route_and_site="Sub-cutaneous, Left upper arm",
        aliases=("je-2", "je 2", "japanese encephalitis 2", "je2"),
    ),
    VaccineDose(
        id="DPT-BOOSTER-1",
        name="DPT Booster-1",
        vaccine_group="DPT",
        dose_number=4,
        recommended_age_str="16-24 months",
        min_age_days=480,
        overdue_after_days=730,
        max_age_days=2555,
        protects_against="Diphtheria, Pertussis and Tetanus",
        route_and_site="Intra-muscular, Anterolateral side of mid-thigh",
        aliases=("dpt-booster-1", "dpt booster 1", "dpt booster-1", "dpt booster", "dpt-b1", "dpt booster 1st"),
    ),
    VaccineDose(
        id="OPV-BOOSTER",
        name="OPV Booster",
        vaccine_group="OPV",
        dose_number=4,
        recommended_age_str="16-24 months",
        min_age_days=480,
        overdue_after_days=730,
        max_age_days=1825,
        protects_against="Poliomyelitis",
        route_and_site="Oral, 2 drops",
        aliases=("opv-booster", "opv booster", "oral polio booster", "opvb"),
    ),
    VaccineDose(
        id="VITA-2",
        name="Vitamin A (2nd Dose)",
        vaccine_group="Vitamin A",
        dose_number=2,
        recommended_age_str="16-18 months",
        min_age_days=480,
        overdue_after_days=730,
        max_age_days=1825,
        protects_against="Vitamin A Deficiency",
        route_and_site="Oral, 2 ml (2 lakh IU)",
        aliases=("vita-2", "vitamin a 2", "vit a 2", "vitamin a 2nd dose", "vita2"),
    ),

    # --- 5 to 6 Years (1825 days) ---
    VaccineDose(
        id="DPT-BOOSTER-2",
        name="DPT Booster-2",
        vaccine_group="DPT",
        dose_number=5,
        recommended_age_str="5-6 years",
        min_age_days=1825,
        overdue_after_days=2190, # 6 years
        max_age_days=2555,
        protects_against="Diphtheria, Pertussis and Tetanus",
        route_and_site="Intra-muscular, Upper arm",
        aliases=("dpt-booster-2", "dpt booster 2", "dpt-b2", "dpt booster 2nd"),
    ),

    # --- 10 & 16 Years ---
    VaccineDose(
        id="TD-10YR",
        name="Td (10 Years)",
        vaccine_group="Td",
        dose_number=1,
        recommended_age_str="10 years",
        min_age_days=3650,
        overdue_after_days=4015,
        max_age_days=None,
        protects_against="Tetanus and adult Diphtheria",
        route_and_site="Intra-muscular, Upper arm",
        aliases=("td-10", "td 10", "tt 10", "td 10 years", "tt-10yr", "td-10yr"),
    ),
    VaccineDose(
        id="TD-16YR",
        name="Td (16 Years)",
        vaccine_group="Td",
        dose_number=2,
        recommended_age_str="16 years",
        min_age_days=5840,
        overdue_after_days=6205,
        max_age_days=None,
        protects_against="Tetanus and adult Diphtheria",
        route_and_site="Intra-muscular, Upper arm",
        aliases=("td-16", "td 16", "tt 16", "td 16 years", "tt-16yr", "td-16yr"),
    ),
]


def _normalize_str(s: str) -> str:
    return re.sub(r"[\s\-_]+", " ", s.strip().lower())


_ALIAS_MAP: dict[str, VaccineDose] = {}
for _dose in UIP_SCHEDULE:
    _ALIAS_MAP[_normalize_str(_dose.id)] = _dose
    _ALIAS_MAP[_normalize_str(_dose.name)] = _dose
    for alias in _dose.aliases:
        _ALIAS_MAP[_normalize_str(alias)] = _dose


def match_vaccine_dose(name_or_id: str) -> VaccineDose | None:
    """Resolve user/record vaccine string to official VaccineDose definition."""
    if not name_or_id or not isinstance(name_or_id, str):
        return None
    cleaned = _normalize_str(name_or_id)
    if cleaned in _ALIAS_MAP:
        return _ALIAS_MAP[cleaned]
    # Partial token match if exact match fails
    for k, v in _ALIAS_MAP.items():
        if cleaned == k or (len(cleaned) >= 3 and cleaned in k):
            return v
    return None
