// Thin HTTP client. All business logic lives on the server.
async function request(method, url, body, isForm = false) {
  const opts = { method, headers: {} };
  if (body !== undefined) {
    if (isForm) opts.body = body;
    else { opts.headers["Content-Type"] = "application/json"; opts.body = JSON.stringify(body); }
  }
  const res = await fetch(url, opts);
  if (res.status === 204) return null;
  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    const d = data.detail;
    const msg = Array.isArray(d) ? d.map((e) => e.msg).join("; ") : d || res.statusText;
    throw new Error(msg);
  }
  return data;
}

export const api = {
  config: () => request("GET", "/api/config"),
  listTrips: () => request("GET", "/api/trips"),
  getTrip: (id) => request("GET", `/api/trips/${id}`),
  createTrip: (b) => request("POST", "/api/trips", b),
  updateTrip: (id, b) => request("PATCH", `/api/trips/${id}`, b),
  addDestination: (id, b) => request("POST", `/api/trips/${id}/destinations`, b),
  updateDestination: (id, d, b) => request("PATCH", `/api/trips/${id}/destinations/${d}`, b),
  deleteDestination: (id, d) => request("DELETE", `/api/trips/${id}/destinations/${d}`),
  addActivity: (id, b) => request("POST", `/api/trips/${id}/activities`, b),
  updateActivity: (id, a, b) => request("PATCH", `/api/trips/${id}/activities/${a}`, b),
  deleteActivity: (id, a) => request("DELETE", `/api/trips/${id}/activities/${a}`),
  uploadDoc: (id, file) => { const f = new FormData(); f.append("file", file); return request("POST", `/api/trips/${id}/documents`, f, true); },
  deleteDoc: (id, d) => request("DELETE", `/api/trips/${id}/documents/${d}`),
  searchPlaces: (q) => request("GET", `/api/places/search?q=${encodeURIComponent(q)}`),
  chat: (id, message) => request("POST", `/api/ai/trips/${id}/chat`, { message }),
  generate: (prompt) => request("POST", "/api/ai/generate", { prompt }),
};
