"""Chatbot features:
1. Trip Assistant - answers questions grounded in the current trip (budget, schedule, packing).
2. AI Itinerary Generator - turns a natural-language prompt into a full draft trip.
Uses Gemini when GEMINI_API_KEY is set, otherwise a deterministic rule-based engine.
"""
import json
import re
from datetime import date, timedelta

import httpx

from ..config import settings
from ..schemas import ActivityCreate
from .budget import compute_budget

GEMINI_URL = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"


async def _gemini(system: str, user: str, json_mode: bool = False) -> str:
    body = {
        "systemInstruction": {"parts": [{"text": system}]},
        "contents": [{"role": "user", "parts": [{"text": user}]}],
        "generationConfig": {"temperature": 0.6},
    }
    if json_mode:
        body["generationConfig"]["responseMimeType"] = "application/json"
    async with httpx.AsyncClient(timeout=40) as client:
        r = await client.post(GEMINI_URL.format(model=settings.GEMINI_MODEL), json=body,
                              headers={"x-goog-api-key": settings.GEMINI_API_KEY})
    r.raise_for_status()
    return r.json()["candidates"][0]["content"]["parts"][0]["text"]


def _trip_context(trip: dict) -> str:
    b = compute_budget(trip)
    lines = [f"Trip: {trip['name']} ({trip['start_date']} to {trip['end_date']})",
             f"Budget: {b['budget']} {b['currency']}, committed {b['committed']}, actual spent "
             f"{b['total_actual']}, remaining {b['remaining']}, status {b['status']}",
             "Destinations: " + ", ".join(d["name"] for d in trip.get("destinations", [])) or "none"]
    for a in sorted(trip.get("activities", []), key=lambda a: (str(a["date"]), a.get("time", ""))):
        lines.append(f"- {a['date']} {a.get('time')} {a['title']} est={a.get('estimated_cost')} "
                     f"actual={a.get('actual_cost')} notes={a.get('notes', '')}")
    return "\n".join(lines)


# ---------------------------------------------------------------- Assistant
def _rule_chat(trip: dict, message: str) -> str:
    m = message.lower()
    b = compute_budget(trip)
    cur = b["currency"]
    if any(w in m for w in ("budget", "spent", "spend", "cost", "money", "remaining", "left", "over")):
        msg = (f"Budget {b['budget']:,} {cur}. Planned (estimated) {b['total_estimated']:,}, "
               f"actually spent {b['total_actual']:,}. Remaining {b['remaining']:,} {cur} "
               f"({b['used_pct']}% used, status: {b['status'].replace('_', ' ')}).")
        if b["per_day"]:
            top = max(b["per_day"], key=lambda d: d["estimated"])
            msg += f" Most expensive day: {top['date']} ({top['estimated']:,} {cur} estimated)."
        return msg
    day = re.search(r"day\s*(\d+)", m)
    if day or "today" in m or "schedule" in m or "plan" in m:
        n = int(day.group(1)) if day else 1
        target = (date.fromisoformat(str(trip["start_date"])) + timedelta(days=n - 1)).isoformat()
        acts = sorted([a for a in trip["activities"] if str(a["date"]) == target], key=lambda a: a["time"])
        if not acts:
            return f"Nothing planned for day {n} ({target}) yet."
        return f"Day {n} ({target}): " + "; ".join(f"{a['time']} {a['title']}" for a in acts)
    if "pack" in m:
        return ("Packing checklist: ID/passport + copies (upload them in Documents), tickets, phone charger "
                "& power bank, comfortable shoes, weather-appropriate clothes, basic medicines, "
                "reusable water bottle, some local cash.")
    if "where" in m or "destination" in m:
        names = [d["name"] for d in trip["destinations"]]
        return "Your destinations: " + (", ".join(names) if names else "none added yet.")
    return ("I can help with: your budget (\"how much is left?\"), a day's schedule (\"what's on day 2?\"), "
            "destinations, or a packing list. Add a GEMINI_API_KEY for open-ended answers.")


async def chat(trip: dict, message: str) -> dict:
    if settings.GEMINI_API_KEY:
        try:
            system = ("You are a concise travel assistant inside a trip-planner app. Answer using the trip "
                      "data below; give practical suggestions. Keep answers under 120 words.\n\n"
                      + _trip_context(trip))
            return {"reply": (await _gemini(system, message)).strip(), "source": "gemini"}
        except Exception:
            pass
    return {"reply": _rule_chat(trip, message), "source": "rules"}


# ---------------------------------------------------------------- Generator
def parse_prompt(prompt: str) -> dict:
    days = re.search(r"(\d+)\s*-?\s*(?:day|days|d)\b", prompt, re.I)
    budget = re.search(r"(?:₹|rs\.?|inr|\$|budget|under)\s*([\d,]+)\s*(k)?", prompt, re.I)
    place = re.search(r"\b(?:in|to|at|visit)\s+([A-Za-z][A-Za-z .'-]+?)(?:\s+(?:for|under|with|on|in)\b|[,.]|$)",
                      prompt, re.I)
    amount = None
    if budget:
        amount = float(budget.group(1).replace(",", "")) * (1000 if budget.group(2) else 1)
    return {
        "days": max(1, min(int(days.group(1)) if days else 3, 14)),
        "budget": amount or 20000.0,
        "destination": place.group(1).strip().title() if place else "City Trip",
    }


def _rule_plan(p: dict) -> list:
    per_day = p["budget"] / p["days"]
    template = [("08:30", "Breakfast at a local café", 0.08), ("10:00", "Explore top sights of {d}", 0.2),
                ("13:00", "Lunch - try local cuisine", 0.12), ("15:00", "Museum / cultural visit", 0.15),
                ("18:00", "Sunset viewpoint & market walk", 0.1), ("20:00", "Dinner", 0.2)]
    return [
        {"day": i + 1, "activities": [
            {"time": t, "title": title.format(d=p["destination"]), "estimated_cost": round(per_day * share, -1)}
            for t, title, share in template]}
        for i in range(p["days"])
    ]


async def generate_itinerary(prompt: str) -> dict:
    p = parse_prompt(prompt)
    plan, source = None, "rules"
    if settings.GEMINI_API_KEY:
        try:
            system = ("Return ONLY JSON: {\"name\": str, \"destination\": str, \"days\": int, \"budget\": number, "
                      "\"plan\": [{\"day\": int, \"activities\": [{\"time\": \"HH:MM\", \"title\": str, "
                      "\"estimated_cost\": number, \"notes\": str}]}]}. 4-6 real, specific activities per day; "
                      "costs in the user's currency and the total must fit the budget.")
            data = json.loads(await _gemini(system, prompt, json_mode=True))
            plan = data["plan"]
            p.update(days=int(data.get("days") or p["days"]), budget=float(data.get("budget") or p["budget"]),
                     destination=data.get("destination") or p["destination"], name=data.get("name"))
            source = "gemini"
        except Exception:
            plan = None
    if plan is None:
        plan = _rule_plan(p)

    start = date.today() + timedelta(days=7)
    activities = []
    for day in plan:
        d = start + timedelta(days=int(day.get("day", 1)) - 1)
        for a in day.get("activities", []):
            try:  # validate every AI-produced activity with the same server schema
                act = ActivityCreate(title=str(a.get("title", "Activity"))[:200], date=d,
                                     time=str(a.get("time", "09:00"))[:5],
                                     estimated_cost=max(0.0, float(a.get("estimated_cost") or 0)),
                                     notes=str(a.get("notes", ""))[:2000])
                activities.append(act.model_dump())
            except Exception:
                continue
    return {
        "trip": {"name": p.get("name") or f"{p['days']} days in {p['destination']}",
                 "start_date": start, "end_date": start + timedelta(days=p["days"] - 1),
                 "budget": p["budget"], "currency": "INR"},
        "destination": p["destination"],
        "activities": activities,
        "source": source,
    }
