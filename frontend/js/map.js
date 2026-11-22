// Map view: Google Maps when a key is configured, otherwise Leaflet + OpenStreetMap.
let impl = null;

function loadScript(src) {
  return new Promise((resolve, reject) => {
    const s = document.createElement("script");
    s.src = src; s.async = true; s.onload = resolve; s.onerror = reject;
    document.head.appendChild(s);
  });
}

const googleImpl = {
  async init(el, key) {
    await loadScript(`https://maps.googleapis.com/maps/api/js?key=${encodeURIComponent(key)}`);
    this.map = new google.maps.Map(el, { center: { lat: 20.59, lng: 78.96 }, zoom: 4 });
    this.markers = []; this.info = new google.maps.InfoWindow();
  },
  render(dests) {
    this.markers.forEach((m) => m.setMap(null)); this.markers = [];
    const bounds = new google.maps.LatLngBounds();
    dests.forEach((d, i) => {
      const m = new google.maps.Marker({ position: { lat: d.lat, lng: d.lng }, map: this.map, label: String(i + 1), title: d.name });
      m.addListener("click", () => { this.info.setContent(`<b>${escapeHtml(d.name)}</b><br>${escapeHtml(d.address || "")}`); this.info.open(this.map, m); });
      this.markers.push(m); bounds.extend(m.getPosition());
    });
    if (dests.length === 1) { this.map.setCenter(bounds.getCenter()); this.map.setZoom(12); }
    else if (dests.length > 1) this.map.fitBounds(bounds);
  },
  focus(d) { this.map.panTo({ lat: d.lat, lng: d.lng }); this.map.setZoom(14); },
};

const leafletImpl = {
  async init(el) {
    await loadScript("https://unpkg.com/leaflet@1.9.4/dist/leaflet.js");
    this.map = L.map(el).setView([20.59, 78.96], 4);
    L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", { attribution: "© OpenStreetMap" }).addTo(this.map);
    this.layer = L.layerGroup().addTo(this.map);
  },
  render(dests) {
    this.layer.clearLayers();
    const pts = dests.map((d, i) => {
      L.marker([d.lat, d.lng]).bindPopup(`<b>${i + 1}. ${escapeHtml(d.name)}</b><br>${escapeHtml(d.address || "")}`).addTo(this.layer);
      return [d.lat, d.lng];
    });
    if (pts.length === 1) this.map.setView(pts[0], 12);
    else if (pts.length > 1) this.map.fitBounds(pts, { padding: [30, 30] });
  },
  focus(d) { this.map.setView([d.lat, d.lng], 14); },
};

export function escapeHtml(s) {
  return String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
}

export async function initMap(el, config) {
  impl = config.maps_provider === "google" ? googleImpl : leafletImpl;
  try { await impl.init(el, config.google_maps_key); }
  catch { impl = leafletImpl; await impl.init(el); }
  setTimeout(() => impl.map.invalidateSize?.(), 200);
}
export const renderPins = (dests) => impl && impl.render(dests);
export const focusPin = (d) => impl && impl.focus(d);
