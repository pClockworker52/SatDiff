"""Phase 2 rules engine — deterministic severity / action from diff numbers.

Background: LFM2.5-VL-450M produces good imagery-grounded evidence text but
mis-applies multi-tier severity thresholds (pond_to_wall<25 m → urgent
got dropped to elevated; gully_count=34 → urgent got dropped to nominal).
Rather than fight this with prompting, we move the deterministic part to
Python and let the VLM focus on what it's good at (evidence + trend).

Public surface:
    compute_severity(diff) -> dict — same shape the contract output expects
        for severity_level / recommended_action plus the aggregate fields.

Schema reminder (spikes/schema.json):
    severity_level    ∈ {nominal, elevated, urgent}
    recommended_action ∈ {none, flag_for_review, urgent_inspection}
    overall_status    ∈ {nominal, elevated, urgent}
    downlink_priority ∈ {routine, priority, immediate}

The threshold table is the source of truth — if the contract memo or the
prompt rules ever drift, update HERE first and re-derive the prompt.
"""

from __future__ import annotations

from typing import Any

# ----------------------------- maps ------------------------------- #

_RANK = {"nominal": 0, "elevated": 1, "urgent": 2}
_RANK_INV = {v: k for k, v in _RANK.items()}

_ACTION = {
    "nominal": "none",
    "elevated": "flag_for_review",
    "urgent": "urgent_inspection",
}

_PRIORITY = {
    "nominal": "routine",
    "elevated": "priority",
    "urgent": "immediate",
}


def _max(*levels: str) -> str:
    return _RANK_INV[max(_RANK[l] for l in levels)]


# ----------------------------- per-claim -------------------------- #


def _claim1_severity(diff: dict) -> str:
    """Containment geometry / asymmetric deposition.

    Rules:
      deposition_asymmetry_index > 5  → urgent
      deposition_asymmetry_index > 1.5 → elevated
      otherwise → nominal
    """
    imp = diff.get("impoundment") or {}
    asym = imp.get("deposition_asymmetry_index")
    if asym is None:
        return "nominal"
    if asym > 5.0:
        return "urgent"
    if asym > 1.5:
        return "elevated"
    return "nominal"


def _claim2_severity(diff: dict) -> str:
    """Pond management.

    Rules:
      pond_to_wall_distance_m < 25  → urgent
      pond_to_wall_distance_m < 75  → elevated
      area_change_pct_vs_baseline > +500 → urgent
      area_change_pct_vs_baseline > +100 → elevated
      take MAX of the two evaluations.
    """
    pond = diff.get("pond") or {}
    p2w = pond.get("pond_to_wall_distance_m")
    pct = pond.get("area_change_pct_vs_baseline")

    via_p2w = "nominal"
    if p2w is not None:
        if p2w < 25.0:
            via_p2w = "urgent"
        elif p2w < 75.0:
            via_p2w = "elevated"

    via_pct = "nominal"
    if pct is not None:
        if pct > 500.0:
            via_pct = "urgent"
        elif pct > 100.0:
            via_pct = "elevated"

    return _max(via_p2w, via_pct)


def _claim3_severity(diff: dict) -> str:
    """Wall surface integrity.

    Rules:
      gully_count >= 10 → urgent
      gully_count >= 1  → elevated
      otherwise → nominal
    """
    wall = diff.get("retaining_wall") or {}
    g = wall.get("gully_count")
    if g is None:
        return "nominal"
    if g >= 10:
        return "urgent"
    if g >= 1:
        return "elevated"
    return "nominal"


def _claim4_severity(_diff: dict) -> str:
    """Surface deformation — multispectral-only path; always nominal."""
    return "nominal"


def _claim5_severity(diff: dict, claim123_max: str) -> str:
    """Downstream community zone.

    No direct geometric overlap signal in the current diff; track the
    upstream wall/pond/asymmetry severity and escalate to match if any of
    Claims 1-3 is urgent. Otherwise nominal — there's no diff field that
    proves protected-zone status by itself.
    """
    if claim123_max == "urgent":
        return "urgent"
    return "nominal"


# ----------------------------- public ----------------------------- #


def compute_severity(diff: dict) -> dict[str, Any]:
    """Compute severity per claim + aggregates from the Phase 1 diff.

    Returns a dict with the keys the runner overlays onto the model's
    parsed output:
        per_claim: list of 5 dicts, each {id, severity_level, recommended_action}
        overall_status: str
        downlink_priority: str
        regulatory_escalation_flag: bool
        rule_inputs: dict — the numeric inputs we used (audit trail)
    """
    s1 = _claim1_severity(diff)
    s2 = _claim2_severity(diff)
    s3 = _claim3_severity(diff)
    s4 = _claim4_severity(diff)
    s123 = _max(s1, s2, s3)
    s5 = _claim5_severity(diff, s123)

    severities = [s1, s2, s3, s4, s5]
    overall = _max(*severities)
    escalation = (overall == "urgent") or (s2 == "urgent")

    imp = diff.get("impoundment") or {}
    pond = diff.get("pond") or {}
    wall = diff.get("retaining_wall") or {}

    return {
        "per_claim": [
            {"id": i + 1, "severity_level": sev, "recommended_action": _ACTION[sev]}
            for i, sev in enumerate(severities)
        ],
        "overall_status": overall,
        "downlink_priority": _PRIORITY[overall],
        "regulatory_escalation_flag": bool(escalation),
        "rule_inputs": {
            "deposition_asymmetry_index": imp.get("deposition_asymmetry_index"),
            "pond_to_wall_distance_m": pond.get("pond_to_wall_distance_m"),
            "pond_area_change_pct_vs_baseline": pond.get("area_change_pct_vs_baseline"),
            "gully_count": wall.get("gully_count"),
        },
    }


def overlay_on_parsed(parsed: dict, computed: dict) -> dict:
    """Merge `computed` (from compute_severity) onto `parsed` (the model's JSON).

    Mutates a shallow copy of `parsed`. Keeps model's evidence + probability_trend
    + name + id; replaces severity_level / recommended_action / overall_status /
    downlink_priority / regulatory_escalation_flag.
    """
    out = dict(parsed)
    out["claims"] = []
    by_id = {c["id"]: c for c in computed["per_claim"]}
    for c in parsed.get("claims", []):
        cid = c.get("id")
        comp = by_id.get(cid, {})
        merged = dict(c)
        if comp:
            merged["severity_level"] = comp["severity_level"]
            merged["recommended_action"] = comp["recommended_action"]
        out["claims"].append(merged)
    out["overall_status"] = computed["overall_status"]
    out["downlink_priority"] = computed["downlink_priority"]
    out["regulatory_escalation_flag"] = computed["regulatory_escalation_flag"]
    return out


def count_corrections(parsed_before: dict, computed: dict) -> dict[str, Any]:
    """Compare model output vs rules engine. Returns audit metrics."""
    by_id = {c["id"]: c for c in computed["per_claim"]}
    corrections = 0
    per_claim_diffs = []
    for c in parsed_before.get("claims", []) or []:
        cid = c.get("id")
        comp = by_id.get(cid)
        if not comp:
            continue
        model_sev = c.get("severity_level")
        rule_sev = comp["severity_level"]
        if model_sev != rule_sev:
            corrections += 1
            per_claim_diffs.append({
                "id": cid, "model": model_sev, "rules": rule_sev,
            })
    return {
        "severity_corrections": corrections,
        "severity_corrections_detail": per_claim_diffs,
        "model_overall": parsed_before.get("overall_status"),
        "computed_overall": computed["overall_status"],
        "overall_corrected": parsed_before.get("overall_status") != computed["overall_status"],
    }
