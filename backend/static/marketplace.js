// Chicago Ag Connect Marketplace — Phases 2, 3
// Vendor presence, community logging, product-first search

let activeMarketId = null;
let activeMarketName = null;
let sessionVendorId = null;

const JSON_HEADERS = { 'Content-Type': 'application/json' };

async function initMarketplace() {
  setupProductSearch();
  setupMarketAttendanceModal();
}

// ── Product Search (Phase 3) ─────────────────────────────────

function setupProductSearch() {
  const btn = document.getElementById('btn-product-search');
  const input = document.getElementById('product-search-input');
  if (btn) btn.addEventListener('click', runProductSearch);
  if (input) input.addEventListener('keydown', (e) => { if (e.key === 'Enter') runProductSearch(); });
}

async function runProductSearch() {
  const q = document.getElementById('product-search-input').value.trim();
  const when = document.getElementById('product-search-when').value;
  const container = document.getElementById('product-search-results');
  if (!q || q.length < 2) {
    container.innerHTML = '<p style="font-size:0.75rem;color:#64748b;">Enter at least 2 characters.</p>';
    return;
  }

  container.innerHTML = '<p style="font-size:0.75rem;color:#64748b;">Searching vendors & markets...</p>';

  let url = `/api/search/products?q=${encodeURIComponent(q)}&when=${when}`;
  if (typeof currentState !== 'undefined' && currentState && currentState !== 'ALL') {
    url += `&state=${currentState}`;
  }
  if (typeof userAddressCoords !== 'undefined' && userAddressCoords) {
    url += `&lat=${userAddressCoords.lat}&lon=${userAddressCoords.lon}&radius_miles=${typeof currentRadiusMiles !== 'undefined' ? currentRadiusMiles : 25}`;
  }

  try {
    const res = await fetch(url);
    const data = await res.json();
    renderProductSearchResults(data, container);
  } catch (err) {
    container.innerHTML = `<p style="color:#b91c1c;font-size:0.75rem;">Search failed: ${err.message}</p>`;
  }
}

function renderProductSearchResults(data, container) {
  if (!data.results || data.results.length === 0) {
    container.innerHTML = `<p style="font-size:0.75rem;color:#64748b;">No results for "${data.query}". Try logging vendors at your local market!</p>`;
    return;
  }

  container.innerHTML = `<p style="font-size:0.72rem;color:#64748b;margin-bottom:0.35rem;">${data.total} result(s) for <strong>${data.normalized_query}</strong></p>`;

  data.results.forEach(hit => {
    const card = document.createElement('div');
    card.className = 'product-hit-card';

    let badgeClass = 'badge-usda';
    if (hit.vendor_confirmed) badgeClass = 'badge-vendor-confirmed';
    else if (hit.hit_type === 'vendor_presence') badgeClass = 'badge-community';

    const title = hit.vendor_name
      ? `${hit.vendor_name}${hit.market_name ? ` @ ${hit.market_name}` : ''}`
      : hit.market_name;

    const dateStr = hit.visit_date ? ` · ${hit.visit_date}` : '';
    const locStr = hit.city ? `${hit.city}, ${hit.state_code}` : '';

    card.innerHTML = `
      <div class="product-hit-title">${hit.product_matched}: ${title}</div>
      <div class="product-hit-meta">${locStr}${dateStr}</div>
      <div class="product-hit-meta">${(hit.products || []).slice(0, 4).join(' · ')}</div>
      <span class="product-hit-badge ${badgeClass}">${hit.source_label}</span>
    `;

    card.addEventListener('click', () => {
      if (hit.latitude && hit.longitude && typeof map !== 'undefined') {
        map.flyTo({ center: [hit.longitude, hit.latitude], zoom: 13.5 });
      }
      if (hit.market_id) {
        openMarketAttendanceModal(hit.market_id, hit.market_name || 'Market');
      }
    });

    container.appendChild(card);
  });
}

// ── Market Attendance (Phase 2) ──────────────────────────────

function setupMarketAttendanceModal() {
  const modal = document.getElementById('market-attendance-modal');
  document.getElementById('btn-close-market-modal')?.addEventListener('click', () => { modal.style.display = 'none'; });
  modal?.addEventListener('click', (e) => { if (e.target === modal) modal.style.display = 'none'; });

  document.getElementById('btn-load-attendance')?.addEventListener('click', loadAttendanceForDate);

  document.querySelectorAll('[data-market-tab]').forEach(tab => {
    tab.addEventListener('click', () => switchMarketTab(tab.dataset.marketTab));
  });

  document.getElementById('btn-add-vendor-row')?.addEventListener('click', addCommunityVendorRow);
  document.getElementById('btn-submit-community-visit')?.addEventListener('click', submitCommunityVisit);
  document.getElementById('btn-submit-vendor-presence')?.addEventListener('click', submitVendorPresence);
  document.getElementById('btn-create-vendor-profile')?.addEventListener('click', createVendorProfile);

  addCommunityVendorRow();
}

window.openMarketAttendanceModal = function(marketId, marketName) {
  activeMarketId = marketId;
  activeMarketName = marketName;
  const modal = document.getElementById('market-attendance-modal');
  document.getElementById('market-modal-title').textContent = marketName;
  document.getElementById('market-modal-subtitle').textContent = 'Who was selling here? Log vendors or report your booth.';
  document.getElementById('attendance-date-picker').value = new Date().toISOString().split('T')[0];
  modal.style.display = 'flex';
  switchMarketTab('view');
  loadAttendanceForDate();
  updateVendorPanelStatus();
  if (typeof lucide !== 'undefined') lucide.createIcons();
};

function switchMarketTab(tab) {
  document.querySelectorAll('[data-market-tab]').forEach(t => t.classList.toggle('active', t.dataset.marketTab === tab));
  document.getElementById('panel-attendance-view').style.display = tab === 'view' ? 'block' : 'none';
  document.getElementById('panel-attendance-log').style.display = tab === 'log' ? 'block' : 'none';
  document.getElementById('panel-attendance-vendor').style.display = tab === 'vendor' ? 'block' : 'none';
}

async function loadAttendanceForDate() {
  if (!activeMarketId) return;
  const dateVal = document.getElementById('attendance-date-picker').value;
  const list = document.getElementById('attendance-list');
  list.innerHTML = '<p style="font-size:0.75rem;color:#64748b;">Loading...</p>';

  try {
    const res = await fetch(`/api/markets/${activeMarketId}/attendance?visit_date=${dateVal}`);
    const data = await res.json();
    if (!data.vendors || data.vendors.length === 0) {
      list.innerHTML = '<p style="font-size:0.75rem;color:#64748b;">No vendors reported for this date yet. Be the first to log who you saw!</p>';
      return;
    }
    list.innerHTML = '';
    data.vendors.forEach(v => {
      const row = document.createElement('div');
      row.className = 'attendance-row';
      const badge = v.vendor_confirmed
        ? '<span class="product-hit-badge badge-vendor-confirmed">✓ Vendor confirmed</span>'
        : `<span class="product-hit-badge badge-community">Community (${v.community_report_count})</span>`;
      row.innerHTML = `
        <div class="attendance-row-name">${v.farm_name}</div>
        <div class="attendance-row-products">${v.products_available.join(' · ') || 'Products not listed'}</div>
        ${badge}
        ${v.booth_hint ? `<div style="font-size:0.7rem;color:#94a3b8;margin-top:0.2rem;">📍 ${v.booth_hint}</div>` : ''}
      `;
      list.appendChild(row);
    });
  } catch (err) {
    list.innerHTML = `<p style="color:#b91c1c;font-size:0.75rem;">Failed to load: ${err.message}</p>`;
  }
}

function addCommunityVendorRow() {
  const container = document.getElementById('community-vendor-rows');
  const row = document.createElement('div');
  row.className = 'community-vendor-row';
  row.innerHTML = `
    <input type="text" class="cv-name" placeholder="Vendor / farm name">
    <input type="text" class="cv-products" placeholder="What they sold (comma sep)">
    <button type="button" class="prompt-chip btn-remove-row">✕</button>
  `;
  row.querySelector('.btn-remove-row').addEventListener('click', () => row.remove());
  container.appendChild(row);
}

async function submitCommunityVisit() {
  if (!activeMarketId) return;
  const dateVal = document.getElementById('attendance-date-picker').value;
  const rows = document.querySelectorAll('.community-vendor-row');
  const entries = [];
  rows.forEach(row => {
    const name = row.querySelector('.cv-name').value.trim();
    const products = row.querySelector('.cv-products').value.split(',').map(s => s.trim()).filter(Boolean);
    if (name) entries.push({ vendor_name: name, products_seen: products });
  });
  if (entries.length === 0) {
    alert('Add at least one vendor name.');
    return;
  }

  try {
    const res = await fetch(`/api/markets/${activeMarketId}/community-visit`, {
      method: 'POST',
      headers: JSON_HEADERS,
      body: JSON.stringify({ visit_date: dateVal, vendor_entries: entries })
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || 'Submit failed');
    alert(`Logged ${data.length} vendor(s). Thank you!`);
    document.getElementById('community-vendor-rows').innerHTML = '';
    addCommunityVendorRow();
    switchMarketTab('view');
    loadAttendanceForDate();
  } catch (err) {
    alert('Error: ' + err.message);
  }
}

function updateVendorPanelStatus() {
  const el = document.getElementById('vendor-profile-status');
  if (!el) return;
  if (sessionVendorId) {
    el.innerHTML = `✓ Vendor profile active. Reporting as vendor ID: <strong>${sessionVendorId}</strong>`;
  } else {
    el.innerHTML = 'No vendor profile yet. Create one below to report your booth presence.';
  }
}

async function createVendorProfile() {
  const farmName = prompt('Farm / vendor name:');
  if (!farmName) return;
  const products = (document.getElementById('vendor-products-input').value || '')
    .split(',').map(s => s.trim()).filter(Boolean);

  try {
    const res = await fetch('/api/vendors', {
      method: 'POST',
      headers: JSON_HEADERS,
      body: JSON.stringify({ farm_name: farmName, product_tags: products, sells_direct: false })
    });
    const vendor = await res.json();
    if (!res.ok) throw new Error(vendor.detail || 'Create failed');
    sessionVendorId = vendor.id;
    updateVendorPanelStatus();
    alert(`Vendor profile "${vendor.farm_name}" created!`);
  } catch (err) {
    alert('Error: ' + err.message);
  }
}

async function submitVendorPresence() {
  if (!activeMarketId) return;
  if (!sessionVendorId) {
    alert('Create a vendor profile first.');
    return;
  }
  const dateVal = document.getElementById('attendance-date-picker').value;
  const products = (document.getElementById('vendor-products-input').value || '')
    .split(',').map(s => s.trim()).filter(Boolean);
  const booth = document.getElementById('vendor-booth-hint').value.trim() || null;

  try {
    const res = await fetch(`/api/markets/${activeMarketId}/presence`, {
      method: 'POST',
      headers: JSON_HEADERS,
      body: JSON.stringify({
        vendor_id: sessionVendorId,
        visit_date: dateVal,
        products_available: products,
        booth_hint: booth
      })
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || 'Report failed');
    alert('Your presence has been reported!');
    switchMarketTab('view');
    loadAttendanceForDate();
  } catch (err) {
    alert('Error: ' + err.message);
  }
}

document.addEventListener('DOMContentLoaded', initMarketplace);
