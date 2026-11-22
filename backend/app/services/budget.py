"""Budget vs. Actual calculations. All money math happens here, on the server."""
from collections import defaultdict


def _round(x: float) -> float:
    return round(float(x), 2)


def compute_budget(trip: dict) -> dict:
    budget = float(trip.get("budget") or 0)
    activities = trip.get("activities", [])

    total_estimated = sum(float(a.get("estimated_cost") or 0) for a in activities)
    total_actual = sum(float(a.get("actual_cost") or 0) for a in activities)
    # "Committed" spend: use the actual cost once known, otherwise the estimate.
    committed = sum(
        float(a["actual_cost"]) if a.get("actual_cost") is not None else float(a.get("estimated_cost") or 0)
        for a in activities
    )

    def pct(v: float) -> float:
        return _round(v / budget * 100) if budget > 0 else 0.0

    used_pct = pct(committed)
    if budget > 0 and committed > budget:
        status = "over"
    elif used_pct >= 80:
        status = "warning"
    else:
        status = "on_track"

    per_day = defaultdict(lambda: {"estimated": 0.0, "actual": 0.0})
    for a in activities:
        d = per_day[str(a.get("date"))]
        d["estimated"] += float(a.get("estimated_cost") or 0)
        d["actual"] += float(a.get("actual_cost") or 0)

    return {
        "budget": _round(budget),
        "currency": trip.get("currency", "INR"),
        "total_estimated": _round(total_estimated),
        "total_actual": _round(total_actual),
        "committed": _round(committed),
        "remaining": _round(budget - committed),
        "estimated_pct": pct(total_estimated),
        "actual_pct": pct(total_actual),
        "used_pct": used_pct,
        "variance": _round(total_actual - sum(
            float(a.get("estimated_cost") or 0) for a in activities if a.get("actual_cost") is not None
        )),
        "status": status,
        "per_day": [
            {"date": k, "estimated": _round(v["estimated"]), "actual": _round(v["actual"])}
            for k, v in sorted(per_day.items())
        ],
    }
