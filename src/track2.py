"""Track 2: deterministic risk/eligibility decisions plus required RAG explanations."""
from __future__ import annotations

from datetime import date
from typing import Any, Protocol


class Explainer(Protocol):
    def answer(self, query: str) -> dict: ...


SEVERITY = {"low": 1, "medium": 2, "high": 3, "critical": 4}
DANGER_SIGNS = {
    "vaginal bleeding", "severe headache with blurred vision", "convulsions",
    "loss of consciousness", "leaking fluid", "continuous severe abdominal pain",
    "decreased fetal movements", "absent fetal movements", "high fever",
    "fast breathing", "difficult breathing", "persistent vomiting",
}


def _bool(value: Any) -> bool:
    return value is True or value == 1


def _age_years(dob: str, today: date | None = None) -> int:
    current = today or date.today()
    born = date.fromisoformat(dob)
    return current.year - born.year - ((current.month, current.day) < (born.month, born.day))


class Track2Service:
    """No result is returned if the real core cannot provide its cited explanation."""

    def __init__(self, explainer: Explainer):
        self.explainer = explainer

    def _explain(self, query: str) -> dict:
        result = self.explainer.answer(query)
        return {"answer": result["answer"], "source_chunks": result["source_chunks"], "confidence": result["confidence"]}

    def assess_risk(self, mother: dict, anc_checkup: dict) -> dict:
        flags: list[dict] = []
        hb = anc_checkup.get("hb_level")
        bp = anc_checkup.get("bp")
        systolic, diastolic = self._parse_bp(bp) if bp else (None, None)

        if hb is not None and float(hb) < 7:
            flags.append(self._flag("severe_anaemia", "critical", "Explain severe anaemia in pregnancy and high-risk referral. Source: nhm-anc-severe-anaemia-001."))
        elif hb is not None and float(hb) < 11:
            flags.append(self._flag("anaemia", "medium", "Explain anaemia in pregnancy. Source: nhm-anc-anaemia-002."))

        if systolic is not None and (systolic >= 160 or diastolic >= 110):
            flags.append(self._flag("severe_hypertension", "critical", "Explain severe hypertension in pregnancy and referral. Source: nhm-anc-hypertension-003."))
        elif systolic is not None and (systolic > 140 or diastolic > 90):
            flags.append(self._flag("hypertensive_disorder", "high", "Explain hypertension in pregnancy. Source: nhm-anc-hypertension-003."))

        for sign in {str(item).strip().casefold() for item in anc_checkup.get("danger_signs", [])}:
            if sign in DANGER_SIGNS:
                flags.append(self._flag("danger_sign", "high", f"Explain the pregnancy danger sign '{sign}' and urgent assessment. Source: nhm-anc-danger-signs-004."))

        flags.sort(key=lambda item: (-SEVERITY[item["severity"]], item["code"]))
        return {"risk_flags": flags, "severity": flags[0]["severity"] if flags else "low", "mother_id": mother.get("id")}

    def _flag(self, code: str, severity: str, query: str) -> dict:
        return {"code": code, "severity": severity, "explanation": self._explain(query)}

    @staticmethod
    def _parse_bp(value: str) -> tuple[int, int]:
        try:
            systolic, diastolic = value.replace(" ", "").split("/")
            return int(systolic), int(diastolic)
        except (AttributeError, ValueError) as exc:
            raise ValueError("BP must use systolic/diastolic form, for example 140/90.") from exc

    def assess_eligibility(self, household: dict, mother: dict | None, children: list[dict]) -> dict:
        if mother is None:
            raise ValueError("A mother record is required for Track 2 household eligibility assessment.")
        income = household.get("annual_income_inr")
        if income is not None and int(income) < 0:
            raise ValueError("annual_income_inr cannot be negative.")
        pregnant_or_lactating = _bool(mother.get("is_pregnant")) or _bool(mother.get("is_lactating"))
        category = str(household.get("category", "")).upper()
        pmmvy_evidence = any((
            category in {"SC", "ST"}, _bool(household.get("has_bpl_ration_card")), _bool(household.get("has_nfsa_ration_card")),
            _bool(household.get("has_e_shram_card")), _bool(household.get("has_mgnrega_job_card")), _bool(household.get("is_pm_kisan_beneficiary")),
            _bool(household.get("is_pmjay_listed")), _bool(household.get("is_disabled_40_percent")), _bool(household.get("has_pmmvy_eligible_worker")),
            income is not None and int(income) < 800000,
        ))
        second_or_third = str(mother.get("trimester", "")) in {"2", "3"}
        child_under_six = any(_age_years(child["dob"]) < 6 for child in children)
        child_under_eighteen = any(_age_years(child["dob"]) < 18 for child in children)
        low_performing_states = {"uttar pradesh", "uttarakhand", "bihar", "jharkhand", "madhya pradesh", "chhattisgarh", "assam", "rajasthan", "odisha", "orissa", "jammu and kashmir"}
        state = str(household.get("state", "")).casefold()
        facility = str(mother.get("planned_delivery_facility", "")).casefold()
        disadvantaged = _bool(household.get("has_bpl_ration_card")) or category in {"SC", "ST"}
        jsy = _bool(mother.get("is_pregnant")) and ((state in low_performing_states and facility == "government") or (disadvantaged and facility in {"government", "accredited_private"}))
        results = [
            self._match("JSY", jsy, "Explain Janani Suraksha Yojana JSY institutional-delivery eligibility. Source: nhm-jsy-eligibility-001."),
            self._match("PMMVY", pregnant_or_lactating and pmmvy_evidence, "PMMVY eligibility uses an eligible pregnant or lactating woman with qualifying social, work-card, PM-JAY, disability, or income evidence. Explain it using mwcd-pmmvy-eligibility-001."),
            self._match("PMSMA", _bool(mother.get("is_pregnant")) and second_or_third, "PMSMA provides fixed-day ANC to pregnant women in the second and third trimester. Explain it using nhm-pmsma-anc-002."),
            self._match("Ayushman Bharat PM-JAY", _bool(household.get("is_pmjay_listed")), "PM-JAY eligibility is confirmed from the official beneficiary list, not inferred from income. Explain the verification next step using nha-pmjay-list-001."),
            self._match("Anemia Mukt Bharat", pregnant_or_lactating or (15 <= int(mother.get("age", -1)) <= 49), "Anemia Mukt Bharat covers pregnant and lactating women and women of reproductive age. Explain it using nhm-amb-beneficiaries-001."),
            self._match("POSHAN Abhiyaan", pregnant_or_lactating or child_under_six, "POSHAN services cover pregnant or lactating mothers and children under six. Explain it using mwcd-poshan-beneficiaries-001."),
            self._match("RBSK", child_under_eighteen, "RBSK screens children from birth to 18 years. Explain it using nhm-rbsk-eligibility-001."),
        ]
        return {"household_id": household.get("id"), "scheme_matches": results}

    def _match(self, scheme_name: str, eligible: bool, query: str) -> dict:
        # The boolean comes only from the predicate above; the explanation is
        # always generated by the shared, source-grounded local pipeline.
        explanation = self._explain(query)
        return {"scheme_name": scheme_name, "eligible": eligible, "reason": explanation, "next_action": explanation}
