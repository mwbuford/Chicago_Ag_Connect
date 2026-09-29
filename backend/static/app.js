// Application State
let currentState = "CHICAGO";
let currentCounty = "all";
let currentRadiusMiles = 20.0;
let allLocations = [];
let currentMarkers = [];
let userLocationMarker = null;
let userAddressCoords = null; // { lat, lon, label, county?, stateCode? }
let map = null;
window.activePopup = null;
let stateConfigs = {};
let currentAgronomyMode = 'gardener';

const CHICAGO_METRO_COUNTIES = ['Cook'];

function scopeDisplayName() {
  return 'Chicago';
}

const US_STATE_NAME_TO_CODE = {
  'alabama': 'AL', 'alaska': 'AK', 'arizona': 'AZ', 'arkansas': 'AR',
  'california': 'CA', 'colorado': 'CO', 'connecticut': 'CT', 'delaware': 'DE',
  'district of columbia': 'DC', 'florida': 'FL', 'georgia': 'GA', 'hawaii': 'HI',
  'idaho': 'ID', 'illinois': 'IL', 'indiana': 'IN', 'iowa': 'IA',
  'kansas': 'KS', 'kentucky': 'KY', 'louisiana': 'LA', 'maine': 'ME',
  'maryland': 'MD', 'massachusetts': 'MA', 'michigan': 'MI', 'minnesota': 'MN',
  'mississippi': 'MS', 'missouri': 'MO', 'montana': 'MT', 'nebraska': 'NE',
  'nevada': 'NV', 'new hampshire': 'NH', 'new jersey': 'NJ', 'new mexico': 'NM',
  'new york': 'NY', 'north carolina': 'NC', 'north dakota': 'ND', 'ohio': 'OH',
  'oklahoma': 'OK', 'oregon': 'OR', 'pennsylvania': 'PA', 'rhode island': 'RI',
  'south carolina': 'SC', 'south dakota': 'SD', 'tennessee': 'TN', 'texas': 'TX',
  'utah': 'UT', 'vermont': 'VT', 'virginia': 'VA', 'washington': 'WA',
  'west virginia': 'WV', 'wisconsin': 'WI', 'wyoming': 'WY'
};

function normalizeStateCode(value) {
  if (!value) return null;
  const raw = String(value).trim();
  if (!raw) return null;
  const upper = raw.toUpperCase();
  if (upper.length === 2 && stateConfigs[upper]) return upper;
  const lower = raw.toLowerCase();
  if (US_STATE_NAME_TO_CODE[lower]) return US_STATE_NAME_TO_CODE[lower];
  for (const [name, code] of Object.entries(US_STATE_NAME_TO_CODE)) {
    if (lower.includes(name) || name.includes(lower)) return code;
  }
  return null;
}

function stateFromCoordinates(lat, lon) {
  if (lat == null || lon == null) return null;
  let best = null;
  let bestDist = Infinity;
  for (const [code, cfg] of Object.entries(stateConfigs)) {
    if (code === 'ALL') continue;
    const dlat = lat - cfg.lat;
    const dlon = lon - cfg.lon;
    const dist = Math.sqrt(dlat * dlat + dlon * dlon);
    if (dist < bestDist) {
      bestDist = dist;
      best = code;
    }
  }
  return best;
}

function getEffectiveState() {
  if (userAddressCoords?.stateCode) return userAddressCoords.stateCode;
  if (currentState === 'CHICAGO') return 'IL';
  if (currentState && currentState !== 'ALL') return currentState;
  if (userAddressCoords?.lat != null && userAddressCoords?.lon != null) {
    return stateFromCoordinates(userAddressCoords.lat, userAddressCoords.lon);
  }
  return 'IL';
}

function getBoundaryStateCode() {
  return 'IL';
}

function updateAgronomyLocationLabel() {
  const el = document.getElementById('chat-active-location');
  if (!el) return;
  if (userAddressCoords?.label) {
    el.textContent = `${userAddressCoords.label} (Chicago)`;
  } else {
    el.textContent = 'Chicago urban agriculture';
  }
}

// Lucide Icon update helper
function updateIcons() {
  if (window.lucide) {
    window.lucide.createIcons();
  }
}

// Entity styling configuration
const ENTITY_CONFIG = {
  farmers_market: { color: "#0284c7", label: "Farmers Market", icon: "🧺" },
  farm_stand: { color: "#16a34a", label: "Farm Stand", icon: "🚜" },
  csa: { color: "#b45309", label: "CSA / Farm Box", icon: "📦" },
  agritourism: { color: "#7e22ce", label: "U-Pick / Orchard", icon: "🍎" },
  food_hub: { color: "#0f766e", label: "Food Hub", icon: "🏛️" },
  urban_farm: { color: "#ca8a04", label: "Urban Farm", icon: "🌿" }
};

// Rich OpenStreetMap Style definition
const OSM_RASTER_STYLE = {
  version: 8,
  sources: {
    'osm-tiles': {
      type: 'raster',
      tiles: [
        'https://tile.openstreetmap.org/{z}/{x}/{y}.png'
      ],
      tileSize: 256,
      attribution: '© <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
    }
  },
  layers: [
    {
      id: 'osm-tiles-layer',
      type: 'raster',
      source: 'osm-tiles',
      minzoom: 0,
      maxzoom: 19
    }
  ]
};

// Initialize Map with OpenStreetMap (Allowing full zoom out & USA Overview)
async function initMap() {
  try {
    const statesRes = await fetch('/api/map/states');
    stateConfigs = await statesRes.json();
    populateStateDropdown();
  } catch (err) {
    console.error("Failed to load state configs:", err);
  }

  const cfg = stateConfigs[currentState] || stateConfigs.CHICAGO || { lat: 41.8781, lon: -87.6298, zoom: 10.2, name: "Chicago" };

  map = new maplibregl.Map({
    container: 'map',
    style: OSM_RASTER_STYLE,
    center: [cfg.lon, cfg.lat],
    zoom: cfg.zoom || 9.0,
    minZoom: 2.0,
    maxZoom: 19.0
  });

  map.addControl(new maplibregl.NavigationControl(), 'top-right');
  map.addControl(new maplibregl.ScaleControl(), 'bottom-left');

  map.on('load', () => {
    loadCountyBoundariesLayer();
    loadCountiesForState();
    fetchLocations();
    loadGardenAdvisory(cfg.lat, cfg.lon, null, `${cfg.name || 'Chicago'} Garden Plan`);
    const scopeElem = document.getElementById('map-active-scope');
    if (scopeElem) scopeElem.innerText = scopeDisplayName();
  });
}

// Populate region dropdown (locked to Chicago)
function populateStateDropdown() {
  const stateSelector = document.getElementById('state-selector');
  if (!stateSelector || !stateConfigs) return;

  stateSelector.innerHTML = '';

  const ordered = Object.keys(stateConfigs);
  // Keep API order (CHICAGO first) but ensure CHICAGO is selected by default
  ordered.forEach((code) => {
    const opt = document.createElement('option');
    opt.value = code;
    const name = stateConfigs[code].name || code;
    opt.textContent = code === 'CHICAGO' ? `🏙️ ${name}` : `${name} (${code})`;
    if (code === currentState) opt.selected = true;
    stateSelector.appendChild(opt);
  });
  if (!stateSelector.value) {
    currentState = 'CHICAGO';
    stateSelector.value = 'CHICAGO';
  }
}

// Generate GeoJSON polygon for a radius buffer circle
function createGeoJSONCircle(center, radiusInMiles, points = 64) {
  const km = radiusInMiles * 1.60934;
  const coords = {
    latitude: center[1],
    longitude: center[0]
  };

  const ret = [];
  const distanceX = km / (111.320 * Math.cos(coords.latitude * Math.PI / 180));
  const distanceY = km / 110.574;

  for (let i = 0; i < points; i++) {
    const theta = (i / points) * (2 * Math.PI);
    const x = distanceX * Math.cos(theta);
    const y = distanceY * Math.sin(theta);
    ret.push([coords.longitude + x, coords.latitude + y]);
  }
  ret.push(ret[0]);

  return {
    type: 'FeatureCollection',
    features: [{
      type: 'Feature',
      geometry: {
        type: 'Polygon',
        coordinates: [ret]
      }
    }]
  };
}

// Render Customizable Radius Buffer on Map
function renderRadiusBuffer(lon, lat, radiusMiles = currentRadiusMiles) {
  if (map.getLayer('radius-circle-layer')) map.removeLayer('radius-circle-layer');
  if (map.getLayer('radius-circle-line')) map.removeLayer('radius-circle-line');
  if (map.getSource('radius-circle-source')) map.removeSource('radius-circle-source');

  const circleGeoJSON = createGeoJSONCircle([lon, lat], radiusMiles);

  map.addSource('radius-circle-source', {
    type: 'geojson',
    data: circleGeoJSON
  });

  map.addLayer({
    id: 'radius-circle-layer',
    type: 'fill',
    source: 'radius-circle-source',
    paint: {
      'fill-color': '#0284c7',
      'fill-opacity': 0.15
    }
  });

  map.addLayer({
    id: 'radius-circle-line',
    type: 'line',
    source: 'radius-circle-source',
    paint: {
      'line-color': '#0284c7',
      'line-width': 2.5,
      'line-dasharray': [2, 2]
    }
  });

  // User Home Marker
  if (userLocationMarker) userLocationMarker.remove();

  const el = document.createElement('div');
  el.className = 'user-home-pin';
  el.innerHTML = '🏠';

  userLocationMarker = new maplibregl.Marker({ element: el })
    .setLngLat([lon, lat])
    .addTo(map);

  map.flyTo({ center: [lon, lat], zoom: radiusMiles > 30 ? 8.8 : (radiusMiles > 15 ? 9.8 : 10.8) });
}

// Remove Radius Buffer
function clearRadiusBuffer() {
  if (map.getLayer('radius-circle-layer')) map.removeLayer('radius-circle-layer');
  if (map.getLayer('radius-circle-line')) map.removeLayer('radius-circle-line');
  if (map.getSource('radius-circle-source')) map.removeSource('radius-circle-source');
  if (userLocationMarker) {
    userLocationMarker.remove();
    userLocationMarker = null;
  }
  userAddressCoords = null;
  
  const banner = document.getElementById('radius-banner-map');
  if (banner) banner.style.display = 'none';

  const mapInput = document.getElementById('address-input-map');
  if (mapInput) {
    mapInput.value = '';
    mapInput.classList.remove('is-confirmed');
  }
  const clearMapBtn = document.getElementById('btn-clear-input-map');
  if (clearMapBtn) clearMapBtn.style.display = 'none';

  const advInput = document.getElementById('address-input-advisory');
  if (advInput) {
    advInput.value = '';
    advInput.classList.remove('is-confirmed');
  }
  const clearAdvBtn = document.getElementById('btn-clear-input-advisory');
  if (clearAdvBtn) clearAdvBtn.style.display = 'none';
}

// Set active county across both dropdowns and refresh both map and advisory panel
function setActiveCounty(countyName, shouldFly = true) {
  if (!countyName) return;

  // Check if countyName has state code attached e.g. "Travis (TX)"
  if (countyName.includes("(") && countyName.includes(")")) {
    const match = countyName.match(/^(.+?)\s*\(([A-Z]{2})\)$/);
    if (match) {
      countyName = match[1].trim();
      const st = match[2].trim();
      if (currentState !== st) {
        currentState = st;
        const stateSelector = document.getElementById('state-selector');
        if (stateSelector) stateSelector.value = st;
        loadCountyBoundariesLayer();
        loadCountiesForState();
      }
    }
  }

  currentCounty = countyName;

  // Sync Dropdowns
  const selectorMap = document.getElementById('county-selector');
  const selectorAdv = document.getElementById('county-selector-advisory');
  if (selectorMap) selectorMap.value = countyName;
  if (selectorAdv) selectorAdv.value = countyName;

  clearRadiusBuffer();
  fetchLocations();

  if (countyName !== "all") {
    const stName = stateConfigs[currentState]?.name || currentState;
    const scopeElem = document.getElementById('map-active-scope');
    if (scopeElem) scopeElem.innerText = `${countyName} County, ${stName}`;
    
    // Immediately fetch and update advisory report for selected county
    loadGardenAdvisory(null, null, countyName, `${countyName} County Garden Plan`);

    if (shouldFly) {
      setTimeout(() => {
        if (allLocations.length > 0) {
          map.flyTo({ center: [allLocations[0].longitude, allLocations[0].latitude], zoom: 10.5 });
        }
      }, 200);
    }
  } else {
    const cfg = stateConfigs[currentState] || { lat: 41.8781, lon: -87.6298, zoom: 10.2, name: "Chicago" };
    const scopeElem = document.getElementById('map-active-scope');
    if (scopeElem) scopeElem.innerText = scopeDisplayName();
    loadGardenAdvisory(cfg.lat, cfg.lon, null, `${cfg.name} Garden Plan`);
    if (shouldFly) {
      map.flyTo({ center: [cfg.lon, cfg.lat], zoom: cfg.zoom || 9.0 });
    }
  }
}

// County boundaries disabled — Chicago-only product (no county filter)
async function loadCountyBoundariesLayer() {
  return;
}

// County filter removed — Chicago-only product
async function loadCountiesForState() {
  const containerMap = document.getElementById('county-select-container-map');
  const containerAdv = document.getElementById('county-select-container-advisory');
  if (containerMap) containerMap.style.display = 'none';
  if (containerAdv) containerAdv.style.display = 'none';
}

// Fetch Locations with Active Filters
async function fetchLocations() {
  try {
    let url = `/api/map/locations?state=${currentState}`;
    
    if (userAddressCoords) {
      url += `&user_lat=${userAddressCoords.lat}&user_lon=${userAddressCoords.lon}&radius_miles=${currentRadiusMiles}`;
    } else if (currentCounty !== "all") {
      url += `&county=${encodeURIComponent(currentCounty)}`;
    }

    const res = await fetch(url);
    allLocations = await res.json();
    applyFilters();
  } catch (err) {
    console.error("Failed to load locations:", err);
  }
}

// Open popup for a specific marker (manual addTo — more reliable than Marker.setPopup alone)
function openMarkerPopup(marker, popup) {
  try {
    if (window.activePopup && window.activePopup !== popup) {
      window.activePopup.remove();
      window.activePopup = null;
    }
    if (!popup.isOpen()) {
      popup.setLngLat(marker.getLngLat()).addTo(map);
    }
    window.activePopup = popup;
    map.panTo(marker.getLngLat(), { duration: 400 });
  } catch (err) {
    console.error('Failed to open marker popup', err);
  }
}

// Render Pins on Map with Fixed Persistent Popups
function renderMarkers(locations) {
  currentMarkers.forEach(m => m.remove());
  currentMarkers = [];

  const displayLocations = locations.slice(0, 500);

  displayLocations.forEach((loc) => {
    const cfg = ENTITY_CONFIG[loc.entity_type] || { color: '#16a34a', icon: '📍', label: loc.type_label };

    const el = document.createElement('div');
    el.className = 'consumer-map-pin';
    el.style.backgroundColor = cfg.color;
    el.style.color = 'white';
    el.style.width = '28px';
    el.style.height = '28px';
    el.style.borderRadius = '50%';
    el.style.display = 'flex';
    el.style.alignItems = 'center';
    el.style.justifyContent = 'center';
    el.style.fontSize = '13px';
    el.style.border = '2px solid white';
    el.style.boxShadow = '0 2px 6px rgba(0,0,0,0.3)';
    el.style.cursor = 'pointer';
    el.innerHTML = cfg.icon;

    const snapBadge = (loc.link_match || (loc.payment_methods || []).some(p => p.includes('SNAP') || p.toLowerCase().includes('link')))
      ? `<span style="background:#dcfce7; color:#15803d; font-size:10px; font-weight:bold; padding:2px 6px; border-radius:4px; margin-left:4px;">✓ SNAP/Link</span>`
      : '';

    const webBtn = loc.website_url
      ? `<a href="${loc.website_url}" target="_blank" class="btn-card-link web" style="margin-top:4px;">🌐 ${loc.domain_label || 'Visit Website'} ↗</a>`
      : (loc.search_url ? `<a href="${loc.search_url}" target="_blank" class="btn-card-link web" style="margin-top:4px;">🔍 Search Online ↗</a>` : '');

    const scheduleLine = loc.schedule
      ? `<p style="font-size:11px; color:#334155; margin:0 0 6px 0;"><strong>Hours:</strong> ${loc.schedule}</p>`
      : '';

    const safeName = String(loc.name || '').replace(/'/g, "\\'").replace(/"/g, '&quot;');
    const safeCounty = String(loc.county || 'Cook').replace(/'/g, "\\'");

    const popupHTML = `
      <div style="padding: 6px; font-family: -apple-system, BlinkMacSystemFont, sans-serif; max-width: 285px;">
        <div style="display:flex; align-items:center; justify-content:space-between; margin-bottom:4px;">
          <span class="badge badge-${loc.entity_type}">${loc.type_label}</span>
          ${snapBadge}
        </div>
        <h3 style="font-size: 14px; font-weight: 800; margin: 4px 0 2px 0; color: #0f172a;">${loc.name}</h3>
        <p style="font-size: 11px; color: #64748b; margin-bottom: 4px;">📍 ${loc.address}</p>
        ${scheduleLine}
        
        <div style="background:#f8fafc; border:1px solid #e2e8f0; border-radius:6px; padding:6px; font-size:11px; margin-bottom:6px;">
          <strong>Accepted Payment:</strong> ${(loc.payment_methods && loc.payment_methods.length) ? loc.payment_methods.join(', ') : 'See site for details'}<br>
          ${loc.description ? `<p style="margin-top:3px; color:#475569;">${loc.description}</p>` : ''}
        </div>

        <div style="display:flex; gap:4px; margin-bottom:6px;">
          ${webBtn}
          <a href="${loc.maps_url || '#'}" target="_blank" class="btn-card-link directions" style="margin-top:4px;">
            🗺️ Directions ↗
          </a>
        </div>

        <button onclick="window.openMarketAttendanceModal('${loc.id}', '${safeName}')" 
                style="width: 100%; background: #faf5ff; color: #6d28d9; border: 1px solid #ddd6fe; padding: 5px; border-radius: 5px; font-size: 11px; font-weight: bold; cursor: pointer; margin-bottom: 4px;">
          🧺 Who Was Selling Here?
        </button>
        <button onclick="window.viewGardenPlanForArea(${loc.latitude}, ${loc.longitude}, '${safeCounty}')" 
                style="width: 100%; background: #f0fdf4; color: #15803d; border: 1px solid #86efac; padding: 5px; border-radius: 5px; font-size: 11px; font-weight: bold; cursor: pointer;">
          🌱 Urban garden tips for this area
        </button>
      </div>
    `;

    const popup = new maplibregl.Popup({
      offset: 18,
      closeOnClick: true,
      closeButton: true,
      maxWidth: '300px',
      className: 'chicago-loc-popup'
    })
    .setLngLat([loc.longitude, loc.latitude])
    .setHTML(popupHTML);

    popup.on('close', () => {
      if (window.activePopup === popup) window.activePopup = null;
    });

    const marker = new maplibregl.Marker({ element: el })
      .setLngLat([loc.longitude, loc.latitude])
      .addTo(map);

    el.addEventListener('click', (e) => {
      e.stopPropagation();
      e.preventDefault();
      openMarkerPopup(marker, popup);
    });
    el.addEventListener('touchend', (e) => {
      e.stopPropagation();
      openMarkerPopup(marker, popup);
    });

    loc._marker = marker;
    loc._popup = popup;

    currentMarkers.push(marker);
  });

  const countElem = document.getElementById('results-count');
  if (countElem) {
    countElem.innerText = `Found ${locations.length} Chicago-area food spots (markets, farms & access sites)`;
  }
}

// Global button hook to switch to advisory and update data
window.viewGardenPlanForArea = function(lat, lon, county) {
  switchTab('advisory-panel');
  currentCounty = 'all';
  loadGardenAdvisory(lat, lon, null, 'Chicago Urban Garden Plan');
};

// Render Sidebar Location Cards
function renderLocationCards(locations) {
  const container = document.getElementById('location-cards-container');
  if (!container) return;
  container.innerHTML = '';

  if (locations.length === 0) {
    container.innerHTML = `
      <div style="text-align: center; color: #64748b; font-size: 0.85rem; padding: 2.5rem 1rem; background: #ffffff; border: 1px dashed #cbd5e1; border-radius: 8px;">
        🧺 No locations found matching your filter in ${userAddressCoords ? `${currentRadiusMiles}-mile buffer` : (currentCounty === 'all' ? 'this area' : currentCounty)}.<br>
        <button id="btn-empty-reset" style="margin-top: 8px; background: none; border: none; color: var(--primary); font-weight: bold; cursor: pointer; text-decoration: underline;">
          Reset Filters & Show All
        </button>
      </div>
    `;
    const emptyReset = document.getElementById('btn-empty-reset');
    if (emptyReset) emptyReset.addEventListener('click', resetAllFilters);
    return;
  }

  const displayLocations = locations.slice(0, 100);

  displayLocations.forEach(loc => {
    const card = document.createElement('div');
    card.className = 'location-card';

    const snapPill = loc.payment_methods.some(p => p.includes('SNAP'))
      ? `<span class="payment-pill snap">💳 SNAP / EBT Accepted</span>`
      : '';

    const organicPill = loc.organic_certified
      ? `<span class="payment-pill" style="background:#fef3c7; color:#b45309; font-weight:bold;">🌿 Organic</span>`
      : '';

    const webBtn = loc.website_url
      ? `<a href="${loc.website_url}" target="_blank" class="btn-card-link web" onclick="event.stopPropagation();">🌐 ${loc.domain_label || 'Website'} ↗</a>`
      : `<a href="${loc.search_url}" target="_blank" class="btn-card-link web" onclick="event.stopPropagation();">🔍 Search Web ↗</a>`;

    card.innerHTML = `
      <div class="card-header">
        <div class="card-title">${loc.name}</div>
        <span class="badge badge-${loc.entity_type}">${loc.type_label}</span>
      </div>
      <div class="card-meta">📍 ${loc.city ? `${loc.city}, ` : ''}${loc.county}, ${loc.state_code}</div>
      <p style="font-size: 0.75rem; color: #475569; line-height: 1.35; margin-bottom: 0.35rem;">${loc.description || loc.address}</p>
      <div class="payment-badge-list">
        ${snapPill}
        ${organicPill}
        <span class="payment-pill">${loc.payment_methods.slice(0, 2).join(', ')}</span>
      </div>
      <div class="card-action-bar">
        ${webBtn}
        <a href="${loc.maps_url}" target="_blank" class="btn-card-link directions" onclick="event.stopPropagation();">
          🗺️ Directions ↗
        </a>
      </div>
    `;

    // Click handler for card
    card.addEventListener('click', () => {
      map.flyTo({ center: [loc.longitude, loc.latitude], zoom: 14.5 });
      if (loc._marker && loc._popup) {
        openMarkerPopup(loc._marker, loc._popup);
      }
    });

    container.appendChild(card);
  });

  if (locations.length > 100) {
    const moreNotice = document.createElement('div');
    moreNotice.style = "text-align: center; color: #64748b; font-size: 0.75rem; padding: 0.75rem; font-style: italic;";
    moreNotice.innerText = `Showing 100 of ${locations.length.toLocaleString()} locations. Search an address to narrow down.`;
    container.appendChild(moreNotice);
  }
}

// Load Home Garden Advisory Report
async function loadGardenAdvisory(lat = null, lon = null, county = null, label = null) {
  try {
    let stateCode = getEffectiveState() || currentState;
    let cleanCounty = county;

    if (cleanCounty && cleanCounty.includes("(") && cleanCounty.includes(")")) {
      const match = cleanCounty.match(/^(.+?)\s*\(([A-Z]{2})\)$/);
      if (match) {
        cleanCounty = match[1].trim();
        stateCode = match[2].trim();
      }
    }

    let url = `/api/advisory/report?state=${stateCode || 'ALL'}`;
    if (cleanCounty && cleanCounty !== "all") {
      url += `&county=${encodeURIComponent(cleanCounty)}`;
    }
    if (lat !== null && lat !== undefined) url += `&lat=${lat}`;
    if (lon !== null && lon !== undefined) url += `&lon=${lon}`;
    if (label) url += `&label=${encodeURIComponent(label)}`;

    const res = await fetch(url);
    const data = await res.json();

    const badgeElem = document.getElementById('advisory-badge-county');
    if (badgeElem) {
      const st = getEffectiveState() || data.state_code;
      badgeElem.innerText = data.county && data.county !== 'Regional'
        ? `${data.county}, ${st}`
        : (st || 'Your Area');
    }
    
    const subtitleElem = document.getElementById('advisory-subtitle');
    if (subtitleElem) subtitleElem.innerText = `Backyard Garden & Land Guide for ${data.location_label}`;

    updateAgronomyLocationLabel();

    // Update Stat Grid
    const soilNameElem = document.getElementById('soil-series-name');
    if (soilNameElem) soilNameElem.innerText = data.soil.soil_series;
    
    const soilTextureElem = document.getElementById('soil-texture-desc');
    if (soilTextureElem) soilTextureElem.innerText = `${data.soil.native_texture} (${data.soil.native_ph_range})`;
    
    const climateZoneElem = document.getElementById('climate-zone');
    if (climateZoneElem) climateZoneElem.innerText = data.climate.hardiness_zone.split(' ')[0] + " " + (data.climate.hardiness_zone.split(' ')[1] || '');
    
    const ffdElem = document.getElementById('frost-free-days');
    if (ffdElem) ffdElem.innerText = `${data.climate.frost_free_days} Frost-Free Days`;
    
    const lsfElem = document.getElementById('last-spring-frost');
    if (lsfElem) lsfElem.innerText = data.climate.last_spring_frost_date;
    
    const fffElem = document.getElementById('first-fall-frost');
    if (fffElem) fffElem.innerText = data.climate.first_fall_frost_date;

    const summaryElem = document.getElementById('soil-garden-summary');
    if (summaryElem) summaryElem.innerText = `${data.soil.garden_suitability_summary} ${data.soil.raised_bed_recommendation}`;

    // Render Garden Crops
    const cropsContainer = document.getElementById('garden-crops-list');
    cropsContainer.innerHTML = data.top_garden_crops.map(c => `
      <div class="crop-card">
        <div class="crop-card-header">
          <div>
            <strong style="font-size: 0.88rem; color: #0f172a;">${c.crop_name}</strong>
            <span style="font-size: 0.7rem; color: #64748b; margin-left: 4px;">• ${c.garden_category}</span>
          </div>
          <span class="suitability-badge">${c.difficulty}</span>
        </div>
        <p style="font-size: 0.75rem; color: #334155; margin-bottom: 4px;">${c.why_it_works_here}</p>
        <div class="crop-detail-grid">
          <div>🌱 <strong>Indoor Seed:</strong> ${c.indoor_seed_start}</div>
          <div>🌿 <strong>Outdoor Plant:</strong> ${c.outdoor_transplant_window}</div>
          <div>🧺 <strong>Harvest:</strong> ${c.harvest_season}</div>
          <div>☀️ <strong>Sunlight:</strong> ${c.sun_requirement}</div>
          <div>🪴 <strong>Pot Depth:</strong> ${c.container_depth_inches}" minimum</div>
        </div>
        <div class="tip-box" style="margin-top:6px;">
          <strong>💡 Backyard Tip:</strong> ${c.backyard_pro_tip}
        </div>
      </div>
    `).join('');

    // Render Native Species Recommendations
    const nativeContainer = document.getElementById('native-plants-list');
    if (nativeContainer) {
      if (data.native_species_recommendations && data.native_species_recommendations.length > 0) {
        nativeContainer.innerHTML = data.native_species_recommendations.map(n => `
          <div class="native-card">
            <div style="display:flex; justify-content:space-between; align-items:flex-start;">
              <div>
                <strong style="font-size:0.88rem; color:#0f172a;">🌸 ${n.common_name}</strong>
                <div class="native-botanical">${n.botanical_name}</div>
              </div>
              <span class="native-badge">${n.plant_category}</span>
            </div>
            <p style="font-size:0.75rem; color:#334155; margin:3px 0; line-height:1.35;">${n.ecoregion_benefits}</p>
            <div class="crop-detail-grid" style="background:#f0fdf4; margin:4px 0;">
              <div>☀️ <strong>Soil & Sun:</strong> ${n.sun_and_soil}</div>
              <div>💧 <strong>Water Needs:</strong> ${n.water_needs}</div>
            </div>
            <div style="font-size:0.73rem; color:#166534; font-weight:600; margin-top:2px;">
              🏡 <strong>Best Garden Use:</strong> ${n.best_garden_use}
            </div>
          </div>
        `).join('');
      } else {
        nativeContainer.innerHTML = `<p style="font-size:0.8rem; color:#64748b; font-style:italic;">Select a state or county to view native species.</p>`;
      }
    }

    // Render Organic Soil Recipe
    const soilRecipeContainer = document.getElementById('soil-recipe-list');
    soilRecipeContainer.innerHTML = data.organic_soil_recipe.map(r => `
      <div style="background:#ffffff; border:1px solid #e2e8f0; border-radius:6px; padding:7px 9px; line-height:1.35;">
        ${r}
      </div>
    `).join('');

    // Render Seasonal Calendar
    const calendarContainer = document.getElementById('garden-calendar-list');
    calendarContainer.innerHTML = Object.entries(data.monthly_garden_calendar).map(([season, items]) => `
      <div style="margin-bottom: 0.55rem; background:#ffffff; border:1px solid #e2e8f0; border-radius:6px; padding:7px 9px;">
        <strong style="color: #0f172a; font-size: 0.82rem; display:block; margin-bottom: 3px;">📅 ${season}</strong>
        <ul style="padding-left: 1.15rem; margin:0; line-height:1.4;">
          ${items.map(i => `<li style="font-size: 0.75rem; color: #475569;">${i}</li>`).join('')}
        </ul>
      </div>
    `).join('');

    // Render Pitfalls
    const pitfallsContainer = document.getElementById('garden-pitfalls-list');
    pitfallsContainer.innerHTML = data.common_pitfalls_to_avoid.map(p => `
      <div style="background:#fef2f2; border-left:3px solid #dc2626; padding:7px 9px; border-radius:0 4px 4px 0; line-height:1.35; color:#991b1b;">
        ${p}
      </div>
    `).join('');

    updateIcons();
  } catch (err) {
    console.error("Failed to load garden advisory:", err);
  }
}

// Enhanced UX-Friendly Address Autocomplete
function setupAddressAutocomplete(inputId, dropdownId, clearBtnId, onSelectCallback) {
  const input = document.getElementById(inputId);
  const dropdown = document.getElementById(dropdownId);
  const clearBtn = document.getElementById(clearBtnId);
  let debounceTimeout = null;
  let focusedIndex = -1;

  function closeDropdown() {
    dropdown.style.display = 'none';
    dropdown.innerHTML = '';
    focusedIndex = -1;
  }

  function highlightItem(index) {
    const items = dropdown.querySelectorAll('.autocomplete-item');
    items.forEach((item, idx) => {
      if (idx === index) {
        item.classList.add('is-focused');
        item.scrollIntoView({ block: 'nearest' });
      } else {
        item.classList.remove('is-focused');
      }
    });
  }

  // Input changes
  input.addEventListener('input', () => {
    const query = input.value.trim();
    clearTimeout(debounceTimeout);
    input.classList.remove('is-confirmed');

    if (query.length > 0) {
      if (clearBtn) clearBtn.style.display = 'flex';
    } else {
      if (clearBtn) clearBtn.style.display = 'none';
      closeDropdown();
      return;
    }

    if (query.length < 3) {
      closeDropdown();
      return;
    }

    // Show searching placeholder
    dropdown.innerHTML = `<div class="autocomplete-status-item">Searching address suggestions...</div>`;
    dropdown.style.display = 'block';

    debounceTimeout = setTimeout(async () => {
      try {
        const stateName = currentState === 'CHICAGO'
          ? 'Chicago, Illinois'
          : (stateConfigs[currentState]?.name || 'Illinois');
        const q = `${query}, ${stateName}, USA`;
        const res = await fetch(`https://photon.komoot.io/api/?q=${encodeURIComponent(q)}&limit=6`);
        const data = await res.json();

        if (data.features && data.features.length > 0) {
          dropdown.innerHTML = '';
          focusedIndex = -1;

          data.features.forEach((f) => {
            const props = f.properties;
            const housenumber = props.housenumber || '';
            const street = props.street || props.name || query;
            const primary = housenumber ? `${housenumber} ${street}` : street;
            
            const secondaryParts = [props.city, props.county, props.state, props.postcode].filter(Boolean);
            const secondary = secondaryParts.join(', ');

            const fullFormatted = `${primary}${secondary ? `, ${secondary}` : ''}`;

            const item = document.createElement('div');
            item.className = 'autocomplete-item';
            item.innerHTML = `
              <div class="autocomplete-item-title">📍 ${primary}</div>
              <div class="autocomplete-item-subtitle">${secondary}</div>
            `;

            item.addEventListener('click', () => {
              input.value = fullFormatted;
              input.classList.add('is-confirmed');
              closeDropdown();
              const coords = f.geometry.coordinates; // [lon, lat]
              const stateCode = normalizeStateCode(props.state) || stateFromCoordinates(coords[1], coords[0]);
              onSelectCallback(coords[1], coords[0], fullFormatted, props.county, stateCode);
            });

            dropdown.appendChild(item);
          });
          dropdown.style.display = 'block';
        } else {
          dropdown.innerHTML = `<div class="autocomplete-status-item">No verified addresses found. Try adding a city or zip.</div>`;
          dropdown.style.display = 'block';
        }
      } catch (err) {
        console.error("Autocomplete fetch error:", err);
        closeDropdown();
      }
    }, 220);
  });

  // Keyboard navigation (Up/Down arrow & Enter)
  input.addEventListener('keydown', (e) => {
    const items = dropdown.querySelectorAll('.autocomplete-item');
    if (!items.length || dropdown.style.display === 'none') return;

    if (e.key === 'ArrowDown') {
      e.preventDefault();
      focusedIndex = (focusedIndex + 1) % items.length;
      highlightItem(focusedIndex);
    } else if (e.key === 'ArrowUp') {
      e.preventDefault();
      focusedIndex = (focusedIndex - 1 + items.length) % items.length;
      highlightItem(focusedIndex);
    } else if (e.key === 'Enter') {
      if (focusedIndex >= 0 && focusedIndex < items.length) {
        e.preventDefault();
        items[focusedIndex].click();
      }
    } else if (e.key === 'Escape') {
      closeDropdown();
    }
  });

  // Clear button click
  if (clearBtn) {
    clearBtn.addEventListener('click', () => {
      input.value = '';
      input.classList.remove('is-confirmed');
      clearBtn.style.display = 'none';
      closeDropdown();
      input.focus();
    });
  }

  // Close on outside click
  document.addEventListener('click', (e) => {
    if (!input.contains(e.target) && !dropdown.contains(e.target)) {
      closeDropdown();
    }
  });
}

// Apply Filters to Locations
function applyFilters() {
  const searchTerm = document.getElementById('map-search-input').value.toLowerCase().trim();
  const activeTypeBtns = Array.from(document.querySelectorAll('#entity-filters .filter-pill.active'))
                              .map(btn => btn.dataset.type);
  const snapOnly = document.getElementById('chip-snap').classList.contains('active');
  const organicOnly = document.getElementById('chip-organic').classList.contains('active');

  const filtered = allLocations.filter(loc => {
    const typeMatch = activeTypeBtns.includes(loc.entity_type);
    const snapMatch = !snapOnly || loc.payment_methods.some(p => p.includes('SNAP'));
    const organicMatch = !organicOnly || loc.organic_certified;

    const searchMatch = !searchTerm ||
      loc.name.toLowerCase().includes(searchTerm) ||
      loc.city.toLowerCase().includes(searchTerm) ||
      loc.county.toLowerCase().includes(searchTerm) ||
      (loc.description && loc.description.toLowerCase().includes(searchTerm)) ||
      loc.products_offered.some(p => p.toLowerCase().includes(searchTerm));

    return typeMatch && snapMatch && organicMatch && searchMatch;
  });

  renderMarkers(filtered);
  renderLocationCards(filtered);
}

// Reset Filters
function resetAllFilters() {
  clearRadiusBuffer();
  document.getElementById('map-search-input').value = '';
  document.querySelectorAll('#entity-filters .filter-pill').forEach(p => p.classList.add('active'));
  document.getElementById('btn-select-all').classList.add('active');
  document.getElementById('btn-select-all').innerText = '✓ Select All';
  document.getElementById('chip-snap').classList.remove('active');
  document.getElementById('chip-organic').classList.remove('active');
  setActiveCounty("all", true);
}

// Switch Sidebar Tabs & Adjust Width
function switchTab(tabId) {
  document.querySelectorAll('.nav-tab').forEach(t => t.classList.remove('active'));
  document.querySelectorAll('.sidebar-panel').forEach(p => p.classList.remove('active'));

  const activeBtn = document.querySelector(`[data-tab="${tabId}"]`);
  const activePanel = document.getElementById(tabId);
  const appContainer = document.getElementById('app-container');

  if (activeBtn) activeBtn.classList.add('active');
  if (activePanel) activePanel.classList.add('active');

  if (tabId === 'advisory-panel') {
    appContainer.classList.add('advisory-mode');
  } else {
    appContainer.classList.remove('advisory-mode');
  }

  setTimeout(() => {
    if (map) map.resize();
  }, 350);
}

// Event Listeners Setup
document.addEventListener('DOMContentLoaded', () => {
  initMap();

  // Tab Navigation
  document.querySelectorAll('.nav-tab').forEach(tab => {
    tab.addEventListener('click', () => switchTab(tab.dataset.tab));
  });

  // State Switcher in Header
  const stateSelector = document.getElementById('state-selector');
  stateSelector.addEventListener('change', (e) => {
    currentState = e.target.value;
    currentCounty = "all";
    clearRadiusBuffer();
    const cfg = stateConfigs[currentState] || { lat: 41.8781, lon: -87.6298, zoom: 10.2, name: "Chicago" };
    
    if (map) {
      map.flyTo({ center: [cfg.lon, cfg.lat], zoom: cfg.zoom || 9.0 });
    }

    document.getElementById('map-active-scope').innerText = scopeDisplayName();
    loadCountyBoundariesLayer();
    loadCountiesForState();
    fetchLocations();
    loadGardenAdvisory(cfg.lat, cfg.lon, null, `${cfg.name} Garden Plan`);
    updateAgronomyLocationLabel();
  });

  // Region locked to Chicago — no county selectors
  const countySelectorMap = document.getElementById('county-selector');
  const countySelectorAdv = document.getElementById('county-selector-advisory');
  if (countySelectorMap) countySelectorMap.style.display = 'none';
  if (countySelectorAdv) countySelectorAdv.style.display = 'none';
  loadCountiesForState();

  // Customizable Radius Slider
  const radiusSlider = document.getElementById('radius-range-slider');
  const radiusBadge = document.getElementById('radius-slider-value');
  if (radiusSlider && radiusBadge) {
    radiusSlider.addEventListener('input', (e) => {
      currentRadiusMiles = parseFloat(e.target.value);
      radiusBadge.innerText = `${currentRadiusMiles} miles`;
      
      const bannerText = document.getElementById('radius-banner-text');
      if (bannerText && userAddressCoords) {
        bannerText.innerText = `Showing markets within ${currentRadiusMiles} miles of: ${userAddressCoords.label}`;
      }

      if (userAddressCoords) {
        renderRadiusBuffer(userAddressCoords.lon, userAddressCoords.lat, currentRadiusMiles);
        fetchLocations();
      }
    });
  }

  // Setup Enhanced Address Autocomplete for Map Tab (Customizable Buffer)
  setupAddressAutocomplete('address-input-map', 'autocomplete-dropdown-map', 'btn-clear-input-map', (lat, lon, label, county, stateCode) => {
    userAddressCoords = { lat, lon, label, county, stateCode };
    renderRadiusBuffer(lon, lat, currentRadiusMiles);
    const banner = document.getElementById('radius-banner-map');
    if (banner) banner.style.display = 'flex';
    document.getElementById('radius-banner-text').innerText = `Showing markets within ${currentRadiusMiles} miles of: ${label}`;
    fetchLocations();
    loadGardenAdvisory(lat, lon, county, label);
    updateAgronomyLocationLabel();
  });

  document.getElementById('btn-clear-address-map').addEventListener('click', () => {
    clearRadiusBuffer();
    fetchLocations();
  });

  // Setup Enhanced Address Autocomplete for Advisory Tab
  setupAddressAutocomplete('address-input-advisory', 'autocomplete-dropdown-advisory', 'btn-clear-input-advisory', (lat, lon, label, county, stateCode) => {
    userAddressCoords = { lat, lon, label, county, stateCode };
    renderRadiusBuffer(lon, lat, currentRadiusMiles);
    loadGardenAdvisory(lat, lon, county, label);
    updateAgronomyLocationLabel();
  });

  // Search Input
  document.getElementById('map-search-input').addEventListener('input', applyFilters);

  // Category Filter Pills
  document.querySelectorAll('#entity-filters .filter-pill').forEach(pill => {
    pill.addEventListener('click', () => {
      pill.classList.toggle('active');
      
      const allPills = Array.from(document.querySelectorAll('#entity-filters .filter-pill'));
      const activePills = allPills.filter(p => p.classList.contains('active'));
      const selectAllBtn = document.getElementById('btn-select-all');
      
      if (activePills.length === allPills.length) {
        selectAllBtn.classList.add('active');
        selectAllBtn.innerText = '✓ Select All';
      } else {
        selectAllBtn.classList.remove('active');
        selectAllBtn.innerText = 'Select All';
      }

      applyFilters();
    });
  });

  // Select All Toggle Button
  document.getElementById('btn-select-all').addEventListener('click', function() {
    const allPills = document.querySelectorAll('#entity-filters .filter-pill');
    const isCurrentlyAllActive = Array.from(allPills).every(p => p.classList.contains('active'));
    
    if (isCurrentlyAllActive) {
      allPills.forEach(p => p.classList.remove('active'));
      this.classList.remove('active');
      this.innerText = 'Select All';
    } else {
      allPills.forEach(p => p.classList.add('active'));
      this.classList.add('active');
      this.innerText = '✓ Select All';
    }
    applyFilters();
  });

  // SNAP & Organic Chips
  document.getElementById('chip-snap').addEventListener('click', function() {
    this.classList.toggle('active');
    applyFilters();
  });

  document.getElementById('chip-organic').addEventListener('click', function() {
    this.classList.toggle('active');
    applyFilters();
  });

  // Reset Filters Button
  document.getElementById('btn-reset-filters').addEventListener('click', resetAllFilters);

  // Setup Custom AI Features (Model 1: Plant Doctor CNN & Model 4: Agronomy SLM)
  setupCustomAIModels();
  setupWelcomeHome();
  updateAgronomyLocationLabel();

  updateIcons();
});

// ==========================================
// Custom AI Models Integration Logic
// ==========================================
function setupCustomAIModels() {
  // 1. Plant Doctor Modal Elements
  const modal = document.getElementById('plant-doctor-modal');
  const btnOpenHeader = document.getElementById('btn-open-plant-doctor-header');
  const btnOpenTrigger = document.getElementById('btn-trigger-plant-doctor');
  const btnClose = document.getElementById('btn-close-doctor-modal');
  const dropzone = document.getElementById('doctor-dropzone');
  const fileInput = document.getElementById('doctor-file-input');
  const previewImg = document.getElementById('doctor-preview-img');
  const idleState = document.getElementById('dropzone-idle-state');
  const previewState = document.getElementById('dropzone-preview-state');
  const loadingState = document.getElementById('doctor-loading-state');
  const resultContainer = document.getElementById('doctor-result-container');

  function openDoctorModal() {
    if (modal) modal.style.display = 'flex';
  }

  function closeDoctorModal() {
    if (modal) modal.style.display = 'none';
  }

  if (btnOpenHeader) btnOpenHeader.addEventListener('click', openDoctorModal);
  if (btnOpenTrigger) btnOpenTrigger.addEventListener('click', openDoctorModal);
  if (btnClose) btnClose.addEventListener('click', closeDoctorModal);

  if (modal) {
    modal.addEventListener('click', (e) => {
      if (e.target === modal) closeDoctorModal();
    });
  }

  if (dropzone && fileInput) {
    dropzone.addEventListener('click', () => fileInput.click());

    dropzone.addEventListener('dragover', (e) => {
      e.preventDefault();
      dropzone.style.borderColor = '#16a34a';
      dropzone.style.background = '#dcfce7';
    });

    dropzone.addEventListener('dragleave', () => {
      dropzone.style.borderColor = '#86efac';
      dropzone.style.background = '#f0fdf4';
    });

    dropzone.addEventListener('drop', (e) => {
      e.preventDefault();
      dropzone.style.borderColor = '#86efac';
      dropzone.style.background = '#f0fdf4';
      if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
        handleImageUpload(e.dataTransfer.files[0]);
      }
    });

    fileInput.addEventListener('change', (e) => {
      if (e.target.files && e.target.files.length > 0) {
        handleImageUpload(e.target.files[0]);
      }
    });
  }

  async function handleImageUpload(file) {
    if (!file || !file.type.startsWith('image/')) {
      alert("Please upload a valid image file (JPEG, PNG, WebP).");
      return;
    }

    // Show preview
    const reader = new FileReader();
    reader.onload = (e) => {
      if (previewImg) previewImg.src = e.target.result;
      if (idleState) idleState.style.display = 'none';
      if (previewState) previewState.style.display = 'block';
    };
    reader.readAsDataURL(file);

    // Show loading
    if (resultContainer) resultContainer.style.display = 'none';
    if (loadingState) loadingState.style.display = 'block';

    try {
      const formData = new FormData();
      formData.append('image', file);
      formData.append('state', getEffectiveState() || currentState || 'ALL');
      if (currentCounty && currentCounty !== "all") {
        formData.append('county', currentCounty);
      }

      const res = await fetch('/api/ai/diagnose', {
        method: 'POST',
        body: formData
      });

      if (!res.ok) {
        throw new Error(`Diagnosis failed with status: ${res.status}`);
      }

      const data = await res.json();
      renderDiagnosisResult(data);
    } catch (err) {
      console.error("Diagnosis error:", err);
      alert("Plant diagnosis error: " + err.message);
    } finally {
      if (loadingState) loadingState.style.display = 'none';
    }
  }

  function renderDiagnosisResult(diag) {
    if (!resultContainer) return;
    resultContainer.style.display = 'block';

    document.getElementById('diag-species').innerText = diag.plant_species;
    document.getElementById('diag-condition').innerText = diag.condition_name;
    document.getElementById('diag-category').innerText = `${diag.condition_category} Pathology • Inference: ${diag.inference_time_ms}ms`;

    const confPercent = Math.round(diag.confidence * 100);
    const confBadge = document.getElementById('diag-confidence-badge');
    confBadge.innerText = `${confPercent}% Confidence`;
    confBadge.style.background = confPercent > 60 ? '#dcfce7' : '#fef3c7';
    confBadge.style.color = confPercent > 60 ? '#166534' : '#92400e';

    // Regional note
    const regNote = document.getElementById('diag-regional-note');
    if (diag.regional_context_note) {
      regNote.style.display = 'block';
      regNote.innerText = diag.regional_context_note;
    } else {
      regNote.style.display = 'none';
    }

    // Symptoms
    const symList = document.getElementById('diag-symptoms-list');
    symList.innerHTML = diag.symptoms.map(s => `<li>${s}</li>`).join('');

    // Organic Remedies
    const orgList = document.getElementById('diag-organic-list');
    orgList.innerHTML = diag.organic_remedy.organic_controls.map(r => `<li>✓ ${r}</li>`).join('');

    // Prevention
    const prevList = document.getElementById('diag-prevention-list');
    prevList.innerHTML = diag.organic_remedy.cultural_prevention.map(p => `<li>• ${p}</li>`).join('');

    // Top-k bars
    const barsContainer = document.getElementById('diag-top-k-bars');
    barsContainer.innerHTML = diag.top_predictions.map(pred => {
      const pct = Math.round(pred.confidence * 100);
      return `
        <div>
          <div style="display: flex; justify-content: space-between; font-size: 0.72rem; color: #475569; margin-bottom: 2px;">
            <span><strong>${pred.plant_species}:</strong> ${pred.condition_name}</span>
            <span style="font-weight: 700;">${pct}%</span>
          </div>
          <div style="height: 6px; background: #e2e8f0; border-radius: 3px; overflow: hidden;">
            <div style="height: 100%; width: ${pct}%; background: ${pct > 40 ? '#16a34a' : '#64748b'};"></div>
          </div>
        </div>
      `;
    }).join('');
  }

  // 2. Agronomist SLM Chat Drawer Elements
  const chatDrawerHeader = document.getElementById('toggle-chat-drawer');
  const chatBody = document.getElementById('agronomy-chat-body');
  const chatToggleIcon = document.getElementById('chat-toggle-icon');
  const chatThread = document.getElementById('agronomy-chat-thread');
  const chatInput = document.getElementById('agronomy-query-input');
  const btnSend = document.getElementById('btn-send-agronomy-query');
  const promptChips = document.querySelectorAll('.prompt-chip');

  if (chatDrawerHeader && chatBody) {
    chatDrawerHeader.addEventListener('click', () => {
      const isHidden = chatBody.style.display === 'none';
      chatBody.style.display = isHidden ? 'block' : 'none';
      if (chatToggleIcon) chatToggleIcon.innerText = isHidden ? '▼' : '▲';
    });
  }

  promptChips.forEach(chip => {
    if (chip.classList.contains('agronomy-mode-btn')) return;
    chip.addEventListener('click', () => {
      const prompt = chip.getAttribute('data-prompt');
      if (prompt && chatInput) {
        chatInput.value = prompt;
        sendAgronomyQuery(prompt);
      }
    });
  });

  if (btnSend && chatInput) {
    btnSend.addEventListener('click', () => {
      const prompt = chatInput.value.trim();
      if (prompt) {
        sendAgronomyQuery(prompt);
      }
    });

    chatInput.addEventListener('keydown', (e) => {
      if (e.key === 'Enter') {
        const prompt = chatInput.value.trim();
        if (prompt) {
          sendAgronomyQuery(prompt);
        }
      }
    });
  }

  async function sendAgronomyQuery(promptText) {
    if (!promptText) return;
    chatInput.value = '';

    // Append user message
    const userMsg = document.createElement('div');
    userMsg.className = 'chat-msg user';
    userMsg.innerHTML = `<div class="msg-bubble">${promptText}</div>`;
    chatThread.appendChild(userMsg);

    // Append loading placeholder
    const aiMsg = document.createElement('div');
    aiMsg.className = 'chat-msg ai';
    aiMsg.innerHTML = `<div class="msg-bubble" style="font-style: italic; color: #64748b;">Consulting Agronomic Knowledge Base & Soil Model...</div>`;
    chatThread.appendChild(aiMsg);
    chatThread.scrollTop = chatThread.scrollHeight;

    try {
      const res = await fetch('/api/ai/agronomy-slm', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          prompt: promptText,
          mode: currentAgronomyMode,
          state: getEffectiveState() || (currentState !== 'ALL' ? currentState : null),
          county: currentCounty !== "all" ? currentCounty : (userAddressCoords?.county || null),
          latitude: userAddressCoords ? userAddressCoords.lat : null,
          longitude: userAddressCoords ? userAddressCoords.lon : null
        })
      });

      if (!res.ok) throw new Error(`SLM query failed with status: ${res.status}`);

      const data = await res.json();
      
      // Format markdown-like bold and line breaks for neat display
      let formatted = data.response
        .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
        .replace(/\*(.*?)\*/g, '<em>$1</em>')
        .replace(/\n\n/g, '<br><br>')
        .replace(/\n/g, '<br>');

      const sourceBadge = `<div style="font-size: 0.68rem; color: #64748b; margin-top: 0.4rem; border-top: 1px dashed #e2e8f0; padding-top: 0.3rem;">
        📚 <em>Sources: ${data.sources_referenced.join(', ')} (${data.inference_time_ms}ms)</em>
      </div>`;

      aiMsg.querySelector('.msg-bubble').innerHTML = formatted + sourceBadge;
      aiMsg.querySelector('.msg-bubble').style.fontStyle = 'normal';
      aiMsg.querySelector('.msg-bubble').style.color = '#1e293b';
    } catch (err) {
      console.error("SLM Query Error:", err);
      aiMsg.querySelector('.msg-bubble').innerHTML = `⚠️ Sorry, unable to complete agronomy query: ${err.message}`;
    }

    chatThread.scrollTop = chatThread.scrollHeight;
  }

  window.sendAgronomyQuery = sendAgronomyQuery;
  window.setAgronomyMode = (mode) => { currentAgronomyMode = mode; };
  window.getBackyardAgContext = () => {
    const cfg = stateConfigs[currentState] || { lat: 39.8283, lon: -98.5795, name: 'United States' };
    const effectiveState = getEffectiveState();
    return {
      lat: userAddressCoords?.lat ?? cfg.lat,
      lon: userAddressCoords?.lon ?? cfg.lon,
      label: userAddressCoords?.label ?? (currentCounty !== 'all' ? currentCounty : cfg.name),
      state: effectiveState || (currentState !== 'ALL' ? currentState : null),
      county: userAddressCoords?.county || (currentCounty !== 'all' ? currentCounty : null)
    };
  };
}
window.switchTab = switchTab;

// ── Welcome Homepage ─────────────────────────────────────────
function setupWelcomeHome() {
  const overlay = document.getElementById('welcome-home');
  const appContainer = document.getElementById('app-container');
  const header = document.querySelector('header');
  if (!overlay) return;

  // Clear any old "skip home" flag so the landing page always shows on open
  try { localStorage.removeItem('backyard_ag_skip_home'); } catch (_) {}

  function showHome() {
    overlay.style.display = 'flex';
    if (appContainer) appContainer.style.display = 'none';
    if (header) header.style.display = 'none';
  }

  function dismissHome() {
    overlay.style.display = 'none';
    if (appContainer) appContainer.style.display = '';
    if (header) header.style.display = '';
    if (map) setTimeout(() => map.resize(), 200);
  }

  // Always land on the home page when the site first loads
  showHome();

  document.getElementById('btn-welcome-jump-in')?.addEventListener('click', dismissHome);
  document.getElementById('btn-welcome-create-account')?.addEventListener('click', dismissHome);

  document.querySelectorAll('[data-welcome-target]').forEach((card) => {
    card.addEventListener('click', () => {
      const target = card.getAttribute('data-welcome-target');
      dismissHome();
      if (target === 'plant-doctor') {
        document.getElementById('plant-doctor-modal').style.display = 'flex';
      } else if (target) {
        switchTab(target);
        if (target === 'learn-panel' && typeof window.loadLearningPaths === 'function') {
          window.loadLearningPaths();
        }
      }
    });
  });

  document.getElementById('btn-open-welcome')?.addEventListener('click', showHome);
}
