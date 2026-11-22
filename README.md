# ✈️ Travel Planner

Interactive trip-planning app: define destinations, pin them on a map, build a day-by-day itinerary,
track **Budget vs. Actual**, store travel documents and plan with an AI chatbot.

## Features
| Requirement | Implementation |
|---|---|
| Interactive Map | Google Maps JS (falls back to Leaflet/OpenStreetMap when no key) with numbered pins |
| Itinerary Timeline | Vertical, chronological, grouped by day — ordering done on the server (`build_timeline`) |
| Destination Cards | Name, address, rating, editable personal notes, "show on map" |
| Mapping Integration | Server calls Google Places API (New) Text Search for details + lat/lng (OSM Nominatim fallback) |
| Itinerary Storage | MongoDB: one trip document with nested `destinations[]`, `activities[]`, `documents[]` |
| **Vibe Check – Budget vs. Actual** | Each activity has estimated + actual cost; server computes totals, % used, remaining, variance, per-day spend and status (`on_track` / `warning` ≥80% / `over`) → progress bar at the top |
| Travel documents | Upload PDF/images/TXT (≤2 MB, type-checked server-side), stored in the trip document |
| **Extra 1 – AI Trip Assistant** | Chatbot grounded in the trip's live data: "how much budget is left?", "what's on day 2?", packing tips, suggestions |
| **Extra 2 – AI Itinerary Generator** | Natural-language prompt ("3 days in Jaipur under ₹15k") → complete trip with timed, costed activities and the destination pinned. Every AI activity is re-validated with the same Pydantic schema |

Both AI features use **Gemini** when `GEMINI_API_KEY` is set and fall back to a deterministic rule-based engine otherwise.

## Architecture
```
backend/app/
  main.py          FastAPI app, mounts routers + serves frontend
  config.py        env settings
  db.py            Motor (MongoDB) client, in-memory mock fallback
  schemas.py       Pydantic request validation (dates, costs, time format…)
  routes/          trips.py · places.py · ai.py   (thin HTTP layer)
  services/        trips.py · budget.py · places.py · ai.py   (business logic)
frontend/
  index.html, css/styles.css
  js/api.js (HTTP client) · map.js · views.js (pure rendering) · app.js (controller)
```
All calculations, validation and ordering live on the server; the frontend only renders responses.

## Run
```bash
pip install -r requirements.txt
cp .env.example .env      # fill MONGODB_URI, GOOGLE_MAPS_API_KEY, GEMINI_API_KEY (all optional)
python -m uvicorn backend.app.main:app --port 8000
# open http://localhost:8000
```

## API
`GET/POST /api/trips` · `GET/PATCH/DELETE /api/trips/{id}` · `GET /api/trips/{id}/budget`
`POST/PATCH/DELETE /api/trips/{id}/destinations[/{did}]` · `.../activities[/{aid}]` · `.../documents[/{docid}]`
`GET /api/places/search?q=` · `POST /api/ai/trips/{id}/chat` · `POST /api/ai/generate`
Interactive docs: `http://localhost:8000/docs`
