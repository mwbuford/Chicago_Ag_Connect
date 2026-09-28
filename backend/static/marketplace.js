// Chicago Ag Connect Marketplace — Phases 0, 2, 3
// Auth, vendor presence, community logging, product-first search

let authToken = localStorage.getItem('backyard_ag_token') || null;
let currentUser = null;
let activeMarketId = null;
let activeMarketName = null;
let authModeRegister = false;

function authHeaders() {
  const h = { 'Content-Type': 'application/json' };
  if (authToken) h['Authorization'] = `Bearer ${authToken}`;
  return h;
}

async function initMarketplace() {
  if (authToken) {
    try {
      const res = await fetch('/api/auth/me', { headers: authHeaders() });
      if (res.ok) {
        currentUser = await res.json();
        updateAuthButton();
      } else {
        authToken = null;
        localStorage.removeItem('backyard_ag_token');
      }
    } catch (e) {
      console.warn('Auth check failed', e);
    }
  }
  setupAuthUI();
  setupProductSearch();
  setupMarketAttendanceModal();
}

function updateAuthButton() {
  const btn = document.getElementById('btn-auth-header');
  if (!btn) return;
  if (currentUser) {
    btn.textContent = `👤 ${currentUser.display_name}`;
    btn.classList.add('signed-in');
  } else {
    btn.textContent = 'Sign In';
    btn.classList.remove('signed-in');
  }
}

function setupAuthUI() {
  const modal = document.getElementById('auth-modal');
  const btnOpen = document.getElementById('btn-auth-header');
  const btnClose = document.getElementById('btn-close-auth-modal');
  const btnSubmit = document.getElementById('btn-auth-submit');
  const btnToggle = document.getElementById('btn-auth-toggle-mode');
  const nameField = document.getElementById('auth-display-name');

  if (btnOpen) btnOpen.addEventListener('click', () => {
    if (currentUser) {
      if (confirm('Sign out of Chicago Ag Connect?')) {
        authToken = null;
        currentUser = null;
        localStorage.removeItem('backyard_ag_token');
        updateAuthButton();
      }
      return;
    }
    modal.style.display = 'flex';
  });

  if (btnClose) btnClose.addEventListener('click', () => { modal.style.display = 'none'; });
  if (modal) modal.addEventListener('click', (e) => { if (e.target === modal) modal.style.display = 'none'; });

  if (btnToggle) btnToggle.addEventListener('click', () => {
    authModeRegister = !authModeRegister;
    btnSubmit.textContent = authModeRegister ? 'Create Account' : 'Sign In';
    btnToggle.textContent = authModeRegister ? 'Already have an account? Sign In' : 'Need an account? Register';
    if (nameField) nameField.style.display = authModeRegister ? 'block' : 'none';
  });

  if (btnSubmit) btnSubmit.addEventListener('click', async () => {
    const email = document.getElementById('auth-email').value.trim();
    const password = document.getElementById('auth-password').value;
    const displayName = document.getElementById('auth-display-name').value.trim();
    const errEl = document.getElementById('auth-error');
    errEl.style.display = 'none';

    try {
      const url = authModeRegister ? '/api/auth/register' : '/api/auth/login';
      const body = authModeRegister
        ? { email, password, display_name: displayName || email.split('@')[0], role: 'consumer' }
        : { email, password };

      const res = await fetch(url, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || 'Auth failed');

      authToken = data.token;
      currentUser = data.user;
      localStorage.setItem('backyard_ag_token', authToken);
      updateAuthButton();
      modal.style.display = 'none';
    } catch (err) {
      errEl.textContent = err.message;
      errEl.style.display = 'block';
    }
  });
}

function requireAuthOrPrompt() {
  if (currentUser) return true;
  alert('Please sign in to log vendors or report your farm presence.');
  document.getElementById('auth-modal').style.display = 'flex';
  return false;
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
  if (!requireAuthOrPrompt() || !activeMarketId) return;
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
      headers: authHeaders(),
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
  if (!currentUser) {
    el.innerHTML = '⚠️ <a href="#" id="link-signin-vendor" style="color:#0284c7;">Sign in</a> to report as a vendor.';
    document.getElementById('link-signin-vendor')?.addEventListener('click', (e) => {
      e.preventDefault();
      document.getElementById('auth-modal').style.display = 'flex';
    });
    return;
  }
  if (currentUser.vendor_id) {
    el.innerHTML = `✓ Vendor profile linked. Reporting as vendor ID: <strong>${currentUser.vendor_id}</strong>`;
  } else {
    el.innerHTML = 'No vendor profile yet. Create one below to report your booth presence.';
  }
}

async function createVendorProfile() {
  if (!requireAuthOrPrompt()) return;
  const farmName = prompt('Farm / vendor name:');
  if (!farmName) return;
  const products = (document.getElementById('vendor-products-input').value || '')
    .split(',').map(s => s.trim()).filter(Boolean);

  try {
    const res = await fetch('/api/vendors', {
      method: 'POST',
      headers: authHeaders(),
      body: JSON.stringify({ farm_name: farmName, product_tags: products, sells_direct: false })
    });
    const vendor = await res.json();
    if (!res.ok) throw new Error(vendor.detail || 'Create failed');
    currentUser.vendor_id = vendor.id;
    updateVendorPanelStatus();
    alert(`Vendor profile "${vendor.farm_name}" created!`);
  } catch (err) {
    alert('Error: ' + err.message);
  }
}

async function submitVendorPresence() {
  if (!requireAuthOrPrompt() || !activeMarketId) return;
  if (!currentUser.vendor_id) {
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
      headers: authHeaders(),
      body: JSON.stringify({
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
