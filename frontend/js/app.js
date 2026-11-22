// App controller: wires user interactions to API calls and re-renders server state.
import { api } from "./api.js";
import { initMap, renderPins, focusPin, escapeHtml } from "./map.js";
import { renderBudget, renderTimeline, renderDestinations, renderDocuments, addChatMessage } from "./views.js";

const $ = (id) => document.getElementById(id);
let trip = null;

function toast(msg) {
  const t = $("toast"); t.textContent = msg; t.classList.add("show");
  clearTimeout(t._h); t._h = setTimeout(() => t.classList.remove("show"), 3000);
}
async function safe(fn) { try { return await fn(); } catch (err) { toast("⚠️ " + err.message); } }

function render() {
  $("budgetBar").classList.remove("hidden"); $("app").classList.remove("hidden"); $("empty").classList.add("hidden");
  renderBudget(trip);
  renderTimeline(trip, {
    onDelete: (a) => update(api.deleteActivity(trip.id, a)),
    onCost: (a, body) => update(api.updateActivity(trip.id, a, body)),
  });
  renderDestinations(trip, {
    onDelete: (d) => update(api.deleteDestination(trip.id, d)),
    onFocus: focusPin,
    onNotes: (d, notes) => update(api.updateDestination(trip.id, d, { notes }), "Notes saved"),
  });
  renderDocuments(trip, { onDelete: (d) => update(api.deleteDoc(trip.id, d)) });
  renderPins(trip.destinations);
  const f = $("activityForm");
  f.date.min = trip.start_date; f.date.max = trip.end_date;
  if (!f.date.value) f.date.value = trip.start_date;
}

async function update(promise, msg) {
  const res = await safe(() => promise);
  if (res) { trip = res; render(); if (msg) toast(msg); }
}

async function loadTrips(selectId) {
  const trips = await api.listTrips();
  const sel = $("tripSelect");
  sel.innerHTML = trips.map((t) => `<option value="${t.id}">${escapeHtml(t.name)}</option>`).join("");
  if (!trips.length) {
    $("app").classList.add("hidden"); $("budgetBar").classList.add("hidden"); $("empty").classList.remove("hidden");
    return;
  }
  sel.value = selectId || trips[0].id;
  await openTrip(sel.value);
}

async function openTrip(id) {
  trip = await api.getTrip(id);
  $("chatLog").innerHTML = "";
  addChatMessage(`Hi! Ask me about "${trip.name}" — budget, a day's plan, packing tips or suggestions.`, "bot");
  render();
}

function bindEvents() {
  $("tripSelect").onchange = (e) => safe(() => openTrip(e.target.value));
  $("newTripBtn").onclick = () => $("tripDialog").showModal();
  $("aiGenBtn").onclick = () => $("aiDialog").showModal();

  $("tripDialog").addEventListener("close", async () => {
    if ($("tripDialog").returnValue !== "ok") return;
    const f = $("tripForm");
    const created = await safe(() => api.createTrip({
      name: f.elements.name.value, start_date: f.start_date.value, end_date: f.end_date.value,
      budget: Number(f.budget.value), currency: f.currency.value.toUpperCase(),
    }));
    if (created) { f.reset(); f.currency.value = "INR"; await loadTrips(created.id); toast("Trip created"); }
  });

  $("aiDialog").addEventListener("close", async () => {
    if ($("aiDialog").returnValue !== "ok") return;
    toast("✨ Generating itinerary…");
    const created = await safe(() => api.generate($("aiForm").prompt.value));
    if (created) { await loadTrips(created.id); toast(`Trip generated (${created.generated_by})`); }
  });

  $("activityForm").onsubmit = async (e) => {
    e.preventDefault();
    const f = e.target;
    await update(api.addActivity(trip.id, {
      title: f.elements.title.value, date: f.date.value, time: f.time.value,
      estimated_cost: Number(f.estimated_cost.value || 0), destination_id: f.destination_id.value || null,
    }), "Activity added");
    f.elements.title.value = ""; f.estimated_cost.value = "";
  };

  $("placeForm").onsubmit = async (e) => {
    e.preventDefault();
    const list = $("placeResults");
    list.innerHTML = "<li>Searching…</li>";
    const results = (await safe(() => api.searchPlaces($("placeQuery").value))) || [];
    list.innerHTML = results.map((p, i) => `<li data-i="${i}"><b>${escapeHtml(p.name)}</b>
      ${p.rating ? `<span class="stars">★ ${p.rating}</span>` : ""}<small>${escapeHtml(p.address)}</small></li>`).join("")
      || "<li>No results</li>";
    list.querySelectorAll("li[data-i]").forEach((li) => (li.onclick = async () => {
      const p = results[li.dataset.i];
      await update(api.addDestination(trip.id, {
        name: p.name, place_id: p.place_id, address: p.address, lat: p.lat, lng: p.lng, rating: p.rating, notes: "",
      }), `📍 ${p.name} pinned`);
      list.innerHTML = ""; $("placeQuery").value = "";
    }));
  };

  $("chatForm").onsubmit = async (e) => {
    e.preventDefault();
    const msg = $("chatInput").value; $("chatInput").value = "";
    addChatMessage(msg, "user");
    const pending = addChatMessage("…", "bot");
    const res = await safe(() => api.chat(trip.id, msg));
    pending.textContent = res ? res.reply : "Sorry, something went wrong.";
  };

  $("docForm").onsubmit = async (e) => {
    e.preventDefault();
    const file = $("docFile").files[0];
    if (file) await update(api.uploadDoc(trip.id, file), "Document uploaded");
    e.target.reset();
  };

  $("editBudgetBtn").onclick = () => {
    const v = prompt("New total budget", trip.budget);
    if (v !== null) update(api.updateTrip(trip.id, { budget: Number(v) }), "Budget updated");
  };
}

(async function main() {
  const config = await api.config();
  $("status").textContent = `DB: ${config.database} · Maps: ${config.maps_provider} · AI: ${config.ai_provider}`;
  bindEvents();
  await initMap($("map"), config);
  await safe(() => loadTrips());
})();
