// Pure rendering functions: take server data, produce DOM. No calculations here.
import { escapeHtml as e } from "./map.js";

const money = (v, cur) => `${cur} ${Number(v || 0).toLocaleString()}`;

export function renderBudget(trip) {
  const b = trip.budget_summary;
  document.getElementById("tripTitle").textContent = `${trip.name} · ${trip.start_date} → ${trip.end_date}`;
  document.getElementById("budgetText").textContent =
    `Budget ${money(b.budget, b.currency)} · Estimated ${money(b.total_estimated, b.currency)} · ` +
    `Actual ${money(b.total_actual, b.currency)} · Remaining ${money(b.remaining, b.currency)}`;
  document.getElementById("progEst").style.width = `${Math.min(b.estimated_pct, 100)}%`;
  const act = document.getElementById("progAct");
  act.style.width = `${Math.min(b.actual_pct, 100)}%`;
  act.classList.toggle("over", b.status === "over");
  const st = document.getElementById("budgetStatus");
  st.className = `pill ${b.status}`;
  st.textContent = `${b.used_pct}% used · ${b.status.replace("_", " ")}`;
}

export function renderTimeline(trip, handlers) {
  const el = document.getElementById("timeline");
  const cur = trip.currency;
  if (!trip.timeline.length) { el.innerHTML = `<p class="empty">No activities yet.</p>`; return; }
  const perDay = Object.fromEntries(trip.budget_summary.per_day.map((d) => [d.date, d]));
  el.innerHTML = trip.timeline.map((day) => `
    <div class="day"><h4>Day ${day.day_number} — ${day.date}<span>${money(perDay[day.date]?.estimated, cur)} est.</span></h4>
      ${day.activities.map((a) => `
        <div class="act" data-id="${a.id}">
          <div><span class="time">${e(a.time)}</span><span class="t">${e(a.title)}</span>
            <button class="icon del" title="Delete">✕</button></div>
          ${a.destination_name ? `<small>📍 ${e(a.destination_name)}</small>` : ""}
          ${a.notes ? `<small>${e(a.notes)}</small>` : ""}
          <div class="costs">Est <input type="number" min="0" class="est" value="${a.estimated_cost ?? 0}">
            Actual <input type="number" min="0" class="actual" placeholder="—" value="${a.actual_cost ?? ""}">
            ${a.actual_cost != null && a.actual_cost > a.estimated_cost ? `<span class="over">over</span>` : ""}</div>
        </div>`).join("")}
    </div>`).join("");
  el.querySelectorAll(".act").forEach((node) => {
    const id = node.dataset.id;
    node.querySelector(".del").onclick = () => handlers.onDelete(id);
    node.querySelector(".est").onchange = (ev) => handlers.onCost(id, { estimated_cost: Number(ev.target.value || 0) });
    node.querySelector(".actual").onchange = (ev) =>
      handlers.onCost(id, { actual_cost: ev.target.value === "" ? null : Number(ev.target.value) });
  });
}

export function renderDestinations(trip, handlers) {
  const el = document.getElementById("destinations");
  el.innerHTML = trip.destinations.map((d, i) => `
    <div class="dest" data-id="${d.id}">
      <div class="head"><strong>${i + 1}. ${e(d.name)}</strong><button class="icon del" title="Remove">✕</button></div>
      <small>${e(d.address || "")}</small>
      <div>${d.rating != null ? `<span class="stars">★ ${d.rating}</span>` : `<small>No rating</small>`}
        <button class="icon focus" title="Show on map">🔎</button></div>
      <textarea rows="2" placeholder="Your notes…">${e(d.notes || "")}</textarea>
    </div>`).join("");
  el.querySelectorAll(".dest").forEach((node) => {
    const d = trip.destinations.find((x) => x.id === node.dataset.id);
    node.querySelector(".del").onclick = () => handlers.onDelete(d.id);
    node.querySelector(".focus").onclick = () => handlers.onFocus(d);
    node.querySelector("textarea").onchange = (ev) => handlers.onNotes(d.id, ev.target.value);
  });
  const sel = document.querySelector("#activityForm select[name=destination_id]");
  sel.innerHTML = `<option value="">No destination</option>` +
    trip.destinations.map((d) => `<option value="${d.id}">${e(d.name)}</option>`).join("");
}

export function renderDocuments(trip, handlers) {
  const el = document.getElementById("docList");
  el.innerHTML = trip.documents.map((d) => `
    <li data-id="${d.id}"><a href="/api/trips/${trip.id}/documents/${d.id}" target="_blank">${e(d.name)}</a>
      <span><small>${(d.size / 1024).toFixed(0)} KB</small> <button class="icon del">✕</button></span></li>`).join("")
    || `<li><small>No documents uploaded.</small></li>`;
  el.querySelectorAll("li[data-id]").forEach((li) => (li.querySelector(".del").onclick = () => handlers.onDelete(li.dataset.id)));
}

export function addChatMessage(text, who) {
  const log = document.getElementById("chatLog");
  const div = document.createElement("div");
  div.className = `msg ${who}`; div.textContent = text;
  log.appendChild(div); log.scrollTop = log.scrollHeight;
  return div;
}
