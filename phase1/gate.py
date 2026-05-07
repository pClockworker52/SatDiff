"""Phase 1 gate — pre-VLM filter.

Decides whether a given pass is "interesting enough" to invoke the VLM
on, or whether we should skip the LFM2.5-VL call entirely. This is the
Φ-sat cloud-discard heritage applied to SatDiff: cheap signals at the
edge save downlink + compute.

Public surface:
    decide(diff: dict | None, *, prior_passes_since_vlm: int = 0,
           force: bool = False) -> GateDecision

The gate output rolls into the contract memo's `downlink_priority`
field (routine / priority / immediate). Phase 2's prompt builder reads
the gate decision when populating that field on a skipped pass.
"""

from __future__ import annotations

from dataclasses import dataclass


# --- thresholds (Torres-Cruz-anchored, conservative) ---
CLOUD_COVER_SKIP_PCT = 50.0          # Φ-sat heritage gate
GULLY_COUNT_TRIGGER = 1              # any gully → flag
POND_TO_WALL_TRIGGER_M = 75.0        # closer than this → escalate
POND_AREA_GROWTH_TRIGGER_PCT = 100.0 # > 2× baseline pond → flag
DEPOSITION_ASYMMETRY_TRIGGER = 1.5   # 1.5× north/south imbalance → flag
HEARTBEAT_PASSES = 6                 # always invoke every Nth pass


@dataclass(frozen=True)
class GateDecision:
    invoke_vlm: bool
    reason: str
    severity_hint: str  # "routine" | "priority" | "immediate"

    def as_dict(self) -> dict:
        return {
            "invoke_vlm": self.invoke_vlm,
            "reason": self.reason,
            "severity_hint": self.severity_hint,
        }


def decide(diff: dict | None, *, prior_passes_since_vlm: int = 0,
           force: bool = False) -> GateDecision:
    """Return the gate decision for one pass.

    Args:
        diff: physical_diff.compute_diff() output for the pass, or None
              if the loader returned image_available=False.
        prior_passes_since_vlm: count of consecutive skipped passes; the
              heartbeat ensures we don't go silent indefinitely.
        force: bypass the gate (e.g. user `--force` flag).
    """
    if force:
        return GateDecision(True, "forced by caller", "priority")

    if diff is None:
        return GateDecision(False, "image_available=false (no tile)", "routine")

    cloud = diff.get("cloud_cover")
    if cloud is not None and cloud > CLOUD_COVER_SKIP_PCT:
        return GateDecision(False, f"cloud_cover={cloud:.1f}%>{CLOUD_COVER_SKIP_PCT}%", "routine")

    pond = diff.get("pond") or {}
    wall = diff.get("retaining_wall") or {}
    imp = diff.get("impoundment") or {}

    # Strongest signals first — return on the first match.
    pond_to_wall = pond.get("pond_to_wall_distance_m")
    if pond_to_wall is not None and pond_to_wall < POND_TO_WALL_TRIGGER_M:
        return GateDecision(
            True,
            f"pond_to_wall_distance_m={pond_to_wall:.0f}m<{POND_TO_WALL_TRIGGER_M}m",
            "immediate",
        )

    pond_growth = pond.get("area_change_pct_vs_baseline")
    if pond_growth is not None and pond_growth > POND_AREA_GROWTH_TRIGGER_PCT:
        return GateDecision(
            True,
            f"pond_area +{pond_growth:.0f}% vs baseline > +{POND_AREA_GROWTH_TRIGGER_PCT:.0f}%",
            "priority",
        )

    gully = wall.get("gully_count", 0)
    if isinstance(gully, int) and gully >= GULLY_COUNT_TRIGGER:
        return GateDecision(
            True,
            f"gully_count={gully}>={GULLY_COUNT_TRIGGER}",
            "priority",
        )

    asymmetry = imp.get("deposition_asymmetry_index")
    if asymmetry is not None and asymmetry > DEPOSITION_ASYMMETRY_TRIGGER:
        return GateDecision(
            True,
            f"deposition_asymmetry={asymmetry:.2f}>{DEPOSITION_ASYMMETRY_TRIGGER}",
            "priority",
        )

    if prior_passes_since_vlm >= HEARTBEAT_PASSES:
        return GateDecision(
            True,
            f"heartbeat ({prior_passes_since_vlm} passes since last VLM)",
            "routine",
        )

    return GateDecision(False, "all metrics within nominal", "routine")
