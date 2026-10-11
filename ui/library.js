'use strict';
(() => {
  const key = 'larp-studio-routes';
  let routes = [], busy = false, nativeLoaded = false;
  function valid(route) {
    return route && typeof route.name === 'string' && route.name.length <= 60 && ['walk', 'run', 'drive'].includes(route.mode)
      && Array.isArray(route.points) && route.points.length >= 2 && route.points.length <= 12
      && route.points.every(x => x && typeof x.title === 'string' && x.title.length <= 120 && Array.isArray(x.point)
        && x.point.length === 2 && x.point.every(Number.isFinite) && Math.abs(x.point[0]) <= 90 && Math.abs(x.point[1]) <= 180);
  }
  try { const saved = JSON.parse(localStorage.getItem(key)); if (Array.isArray(saved)) routes = saved.filter(valid).slice(0, 20); } catch {}
  async function persist(next) {
    if (busy) return false;
    busy = true;
    try {
      if (window.pywebview?.api) {
        const result = await window.pywebview.api.save_routes(next);
        if (!result.ok) throw new Error(result.error);
        routes = result.data;
      } else { localStorage.setItem(key, JSON.stringify(next)); routes = next; }
      return true;
    }
    catch { toast('Der lokale Speicher ist nicht verfügbar. Route wurde nicht gespeichert.', true); return false; }
    finally { busy = false; }
  }
  function renderLibrary() {
    const list = $('savedRouteList'); list.replaceChildren();
    if (!routes.length) { const note = document.createElement('p'); note.className = 'dialog-note'; note.textContent = 'Noch keine Routen gespeichert. Wähle auf der Karte mindestens zwei Punkte.'; list.append(note); }
    routes.forEach((route, index) => {
      const row = document.createElement('div'); row.className = 'saved-route-row';
      const load = document.createElement('button'); load.className = 'saved-route-load'; load.disabled = active();
      const name = document.createElement('strong'); name.textContent = route.name;
      const detail = document.createElement('span'); detail.textContent = modes[route.mode].label + ' · ' + route.points.length + ' Punkte';
      load.append(name, detail);
      load.onclick = () => {
        if (active()) { toast('Beende zuerst die laufende Sitzung.'); return; }
        switchMode(route.mode); waypoints = structuredClone(route.points); invalidateRoute(); renderEditor(); drawMap();
        map.fitBounds(L.latLngBounds(waypoints.map(x => x.point)), {padding: [90, 120]});
        $('routeLibraryDialog').close(); toast('Route geladen. Jetzt entlang Wegen neu planen.');
      };
      const remove = document.createElement('button'); remove.className = 'icon-button'; remove.innerHTML = svg('close');
      remove.setAttribute('aria-label', route.name + ' löschen');
      remove.onclick = async () => { if (await persist(routes.filter((_, i) => i !== index))) renderLibrary(); };
      row.append(load, remove); list.append(row);
    });
  }
  $('saveRoute').onclick = () => {
    if (mode === 'pin' || waypoints.length < 2) { toast('Wähle zuerst mindestens zwei Routenpunkte.', true); return; }
    if (routes.length >= 20) { toast('Die Bibliothek ist voll. Lösche zuerst eine gespeicherte Route.', true); return; }
    $('savedRouteName').value = modes[mode].label + ' · ' + new Date().toLocaleDateString('de-DE'); $('saveRouteDialog').showModal();
  };
  $('saveRouteForm').onsubmit = async event => {
    event.preventDefault(); const name = $('savedRouteName').value.trim();
    if (!name || name.length > 60 || routes.length >= 20 || mode === 'pin' || waypoints.length < 2) return;
    const route = {name, mode, points: structuredClone(waypoints).map(x => ({point: x.point, title: x.title.slice(0, 120)}))};
    if (valid(route) && await persist([...routes, route])) { $('saveRouteDialog').close(); toast('Route lokal gespeichert.'); }
  };
  $('openRoutes').onclick = () => { renderLibrary(); $('routeLibraryDialog').showModal(); };
  async function loadNative() {
    if (!window.pywebview?.api || nativeLoaded) return;
    nativeLoaded = true;
    try {
      const result = await window.pywebview.api.get_routes();
      if (!result.ok) throw new Error(result.error);
      routes = Array.isArray(result.data) ? result.data.filter(valid).slice(0, 20) : [];
      if ($('routeLibraryDialog').open) renderLibrary();
    } catch { routes = []; toast('Routenbibliothek konnte nicht geladen werden.', true); }
  }
  window.addEventListener('pywebviewready', loadNative); loadNative();
  setInterval(() => { if ($('routeLibraryDialog').open) $('savedRouteList').querySelectorAll('.saved-route-load').forEach(b => b.disabled = active()); }, 600);
})();
