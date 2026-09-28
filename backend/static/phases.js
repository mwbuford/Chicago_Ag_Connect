// Chicago Ag Connect — Phases 4–6: Walkthrough, Resource Hub, Agronomy mode helpers

const AGRONOMY_PROMPTS_BY_MODE = {
  gardener: [
    { label: '🏙️ Chicago Raised Beds', prompt: 'How do I start a safe raised-bed vegetable garden in a Chicago backyard or parkway?' },
    { label: '🧪 Soil & Lead Safety', prompt: 'How do I test Chicago urban soil for lead and grow food safely in containers or raised beds?' },
    { label: '🪴 Balcony & Patio', prompt: 'What vegetables grow well in containers on a Chicago balcony or patio?' },
    { label: '❄️ Zone 5/6 Timing', prompt: 'When can I plant tomatoes, greens, and peppers outdoors in Chicago?' }
  ],
  homesteader: [
    { label: '🤝 Join a Plot', prompt: 'How do I join a community garden plot in Chicago and what should I expect?' },
    { label: '📋 Shared Rules', prompt: 'What are typical Chicago community garden rules for watering, weeds, and end-of-season cleanup?' },
    { label: '🌱 Plot Crops', prompt: 'What crops fit a small Chicago community garden plot with shared tools and limited space?' },
    { label: '♻️ Shared Compost', prompt: 'How do community gardens in Chicago handle compost and shared soil safely?' }
  ],
  small_farm: [
    { label: '🧺 Sell at Markets', prompt: 'How do I apply to sell produce at Chicago farmers markets?' },
    { label: '💳 SNAP / Link Match', prompt: 'How does SNAP Link Match work for vendors and shoppers at Chicago farmers markets?' },
    { label: '🏷️ Cottage Food', prompt: 'What Illinois cottage food rules apply if I sell jam, pickles, or baked goods at a Chicago market?' },
    { label: '📍 List My Booth', prompt: 'How do I list my Chicago farmers market booth on Chicago Ag Connect?' }
  ]
};

let learningPathsLoaded = false;
let activeStoryMap = null;
let activeStorySlide = 0;

function getAppContext() {
  if (typeof window.getBackyardAgContext === 'function') {
    return window.getBackyardAgContext();
  }
  return { lat: null, lon: null, label: 'Your Property', state: null, county: null };
}

function escapeHtml(text) {
  const div = document.createElement('div');
  div.textContent = text;
  return div.innerHTML;
}

function updateAgronomyPromptChips(mode) {
  const container = document.querySelector('.prompt-chips-container');
  if (!container) return;
  const prompts = AGRONOMY_PROMPTS_BY_MODE[mode] || AGRONOMY_PROMPTS_BY_MODE.gardener;
  container.innerHTML = prompts.map((p) =>
    `<button class="prompt-chip" data-prompt="${escapeHtml(p.prompt)}">${p.label}</button>`
  ).join('');
  container.querySelectorAll('.prompt-chip').forEach((chip) => {
    chip.addEventListener('click', () => {
      const prompt = chip.getAttribute('data-prompt');
      const input = document.getElementById('agronomy-query-input');
      if (prompt && input && typeof window.sendAgronomyQuery === 'function') {
        input.value = prompt;
        window.sendAgronomyQuery(prompt);
      }
    });
  });
}

function setupAgronomyModeSelector() {
  document.querySelectorAll('.agronomy-mode-btn').forEach((btn) => {
    btn.addEventListener('click', (e) => {
      e.stopPropagation();
      const mode = btn.getAttribute('data-mode') || 'gardener';
      document.querySelectorAll('.agronomy-mode-btn').forEach((b) => b.classList.remove('active'));
      btn.classList.add('active');
      if (typeof window.setAgronomyMode === 'function') window.setAgronomyMode(mode);
      updateAgronomyPromptChips(mode);
    });
  });
  updateAgronomyPromptChips('gardener');
}

function setupStoryMapUI() {
  const card = document.getElementById('btn-generate-story-map');
  const modal = document.getElementById('story-map-modal');
  const btnClose = document.getElementById('btn-close-story-map');
  const btnPrev = document.getElementById('btn-story-prev');
  const btnNext = document.getElementById('btn-story-next');

  if (card) {
    card.addEventListener('click', () => openStoryMapGenerator());
    card.querySelector('.ai-card-action-btn')?.addEventListener('click', (e) => { e.stopPropagation(); openStoryMapGenerator(); });
  }
  btnClose?.addEventListener('click', () => { modal.style.display = 'none'; });
  modal?.addEventListener('click', (e) => { if (e.target === modal) modal.style.display = 'none'; });
  btnPrev?.addEventListener('click', () => showStorySlide(activeStorySlide - 1));
  btnNext?.addEventListener('click', () => showStorySlide(activeStorySlide + 1));
}

async function openStoryMapGenerator(mode = 'gardener') {
  const ctx = getAppContext();
  const modal = document.getElementById('story-map-modal');
  const loading = document.getElementById('story-map-loading');
  const content = document.getElementById('story-map-content');

  if (!ctx.lat || !ctx.lon) {
    alert('Enter your property address on the Garden Advisory tab first.');
    if (typeof window.switchTab === 'function') window.switchTab('advisory-panel');
    return;
  }

  modal.style.display = 'flex';
  loading.style.display = 'block';
  loading.innerHTML = '<div class="story-map-spinner"></div><p>Building your personalized walkthrough…</p>';
  content.style.display = 'none';

  try {
    const params = new URLSearchParams({ lat: ctx.lat, lon: ctx.lon, mode, label: ctx.label || 'Your Property' });
    if (ctx.state) params.set('state', ctx.state);
    if (ctx.county) params.set('county', ctx.county);

    const res = await fetch(`/api/storymap/generate?${params}`);
    if (!res.ok) throw new Error(`Walkthrough failed (${res.status})`);
    activeStoryMap = await res.json();
    activeStorySlide = 0;
    renderStoryWalkthrough(activeStoryMap);
    loading.style.display = 'none';
    content.style.display = 'block';
  } catch (err) {
    loading.innerHTML = `<p style="color:#b91c1c;">⚠️ ${escapeHtml(err.message)}</p>`;
  }
}

function renderZoneDiagram(zones) {
  const el = document.getElementById('story-zone-diagram');
  if (!el || !zones?.length) { if (el) el.innerHTML = ''; return; }

  const total = zones.reduce((s, z) => s + z.area_sq_ft, 0) || 1;
  el.innerHTML = `
    <div class="story-panel-title">Property Zone Breakdown</div>
    <div class="zone-bar-chart">
      ${zones.map((z) => {
        const pct = Math.max(8, Math.round((z.area_sq_ft / total) * 100));
        return `<div class="zone-bar-segment" style="width:${pct}%;background:${z.color_hex}" title="${escapeHtml(z.label)}"></div>`;
      }).join('')}
    </div>
    <div class="zone-legend-list">
      ${zones.map((z) => `
        <div class="story-zone-item">
          <span class="story-zone-swatch" style="background:${z.color_hex}"></span>
          <div>
            <div class="story-zone-label">${escapeHtml(z.label)}</div>
            <div class="story-zone-meta">${z.area_sq_ft.toLocaleString()} sq ft · ${z.suitability_score}/100 · ${escapeHtml(z.recommended_use)}</div>
          </div>
        </div>
      `).join('')}
    </div>
  `;
}

function renderStoryWalkthrough(data) {
  document.getElementById('story-map-title').textContent = data.location_label;
  document.getElementById('story-map-subtitle').textContent =
    `${data.state_code} · ${data.top_crops.slice(0, 3).join(', ')} · ${data.total_steps} steps`;

  const dots = document.getElementById('story-step-dots');
  if (dots) {
    dots.innerHTML = data.slides.map((s, i) =>
      `<button type="button" class="story-dot ${i === 0 ? 'active' : ''}" data-step="${i}" title="${escapeHtml(s.title)}">${s.slide_number}</button>`
    ).join('');
    dots.querySelectorAll('.story-dot').forEach((dot) => {
      dot.addEventListener('click', () => showStorySlide(parseInt(dot.getAttribute('data-step'), 10)));
    });
  }

  renderZoneDiagram(data.zones);
  showStorySlide(0, data);
}

function showStorySlide(index, data = activeStoryMap) {
  if (!data?.slides?.length) return;
  activeStorySlide = Math.max(0, Math.min(index, data.slides.length - 1));
  const slide = data.slides[activeStorySlide];
  const isChecklist = slide.step_type === 'checklist';

  const progress = ((activeStorySlide + 1) / data.slides.length) * 100;
  const fill = document.getElementById('story-progress-fill');
  if (fill) fill.style.width = `${progress}%`;

  document.getElementById('story-slide-counter').textContent = `Step ${activeStorySlide + 1} of ${data.slides.length}`;

  document.querySelectorAll('.story-dot').forEach((d, i) => {
    d.classList.toggle('active', i === activeStorySlide);
    d.classList.toggle('done', i < activeStorySlide);
  });

  const zoneDiagram = document.getElementById('story-zone-diagram');
  if (zoneDiagram) zoneDiagram.style.display = slide.step_type === 'zones' ? 'block' : 'none';

  let bullets = slide.bullet_points.map((b) => `<li>${escapeHtml(b)}</li>`).join('');
  if (isChecklist && data.next_90_day_checklist?.length) {
    bullets = data.next_90_day_checklist.map((item) =>
      `<li class="story-checklist-item"><label><input type="checkbox"> ${escapeHtml(item)}</label></li>`
    ).join('');
  }

  document.getElementById('story-map-slide').innerHTML = `
    <div class="story-step-number">Step ${slide.slide_number}</div>
    <div class="story-slide-tag">${escapeHtml(slide.title)}</div>
    <h4 class="story-slide-headline">${escapeHtml(slide.headline)}</h4>
    <p class="story-slide-body">${escapeHtml(slide.body)}</p>
    <ul class="story-slide-bullets ${isChecklist ? 'checklist' : ''}">${bullets}</ul>
  `;

  document.getElementById('btn-story-prev').disabled = activeStorySlide === 0;
  const btnNext = document.getElementById('btn-story-next');
  btnNext.disabled = activeStorySlide === data.slides.length - 1;
  btnNext.textContent = activeStorySlide === data.slides.length - 1 ? 'Done ✓' : 'Next →';
}

async function loadLearningPaths() {
  const container = document.getElementById('learning-paths-container');
  if (!container || learningPathsLoaded) return;
  try {
    const res = await fetch('/api/resources/paths');
    if (!res.ok) throw new Error('Failed to load learning paths');
    const data = await res.json();
    learningPathsLoaded = true;
    renderLearningPathCards(data.paths, data.featured_path_id);
  } catch (err) {
    container.innerHTML = `<p class="panel-hint" style="color:#b91c1c;">Could not load paths: ${escapeHtml(err.message)}</p>`;
  }
}
window.loadLearningPaths = loadLearningPaths;

function renderLearningPathCards(paths, featuredId) {
  const container = document.getElementById('learning-paths-container');
  container.innerHTML = paths.map((path) => `
    <div class="learning-path-card ${path.path_id === featuredId ? 'featured' : ''}" data-path-id="${path.path_id}">
      <div class="lp-icon">${path.icon}</div>
      <h3 class="lp-title">${escapeHtml(path.title)}</h3>
      <p class="lp-desc">${escapeHtml(path.description)}</p>
      <div class="lp-meta">${escapeHtml(path.target_audience)}</div>
      <button type="button" class="lp-open-btn" data-path-id="${path.path_id}">Explore →</button>
    </div>
  `).join('');
  container.querySelectorAll('.lp-open-btn').forEach((btn) => {
    btn.addEventListener('click', (e) => { e.stopPropagation(); openLearningPath(btn.getAttribute('data-path-id')); });
  });
  container.querySelectorAll('.learning-path-card').forEach((card) => {
    card.addEventListener('click', () => openLearningPath(card.getAttribute('data-path-id')));
  });
}

// ── Choose-Your-Own-Adventure state ─────────────────────────
let cyoaState = { pathId: null, subPathId: null, pathData: null };

function goBackLearning() {
  const detail = document.getElementById('learning-path-detail');
  const grid = document.getElementById('learning-paths-container');
  if (cyoaState.subPathId) {
    // Back from module detail → sub-path picker
    cyoaState.subPathId = null;
    renderSubPathPicker(cyoaState.pathData);
  } else if (cyoaState.pathId) {
    // Back from path view → top-level card grid
    cyoaState = { pathId: null, subPathId: null, pathData: null };
    detail.style.display = 'none';
    detail.innerHTML = '';
    grid.style.display = '';
  }
}

async function openLearningPath(pathId) {
  const detail = document.getElementById('learning-path-detail');
  const grid = document.getElementById('learning-paths-container');
  const res = await fetch(`/api/resources/paths/${pathId}`);
  if (!res.ok) return;
  const path = await res.json();
  cyoaState = { pathId, subPathId: null, pathData: path };
  grid.style.display = 'none';
  detail.style.display = 'block';

  // If the path has sub-paths (CYOA branches), show the chooser first
  if (path.sub_paths && path.sub_paths.length > 0) {
    renderSubPathPicker(path);
  } else {
    renderPathModules(path, path.modules);
  }
}

function renderSubPathPicker(path) {
  const detail = document.getElementById('learning-path-detail');
  detail.innerHTML = `
    <button type="button" class="lp-back-btn" id="btn-lp-back">← All Paths</button>
    <div class="lp-detail-header">
      <span class="lp-detail-icon">${path.icon}</span>
      <div>
        <h3>${escapeHtml(path.title)}</h3>
        <p>${escapeHtml(path.description)}</p>
      </div>
    </div>
    <div class="cyoa-question">
      <h4 class="cyoa-q-label">How much space do you have?</h4>
      <div class="cyoa-options">
        ${path.sub_paths.map((sp) => `
          <button type="button" class="cyoa-option-btn" data-sub-path="${sp.sub_path_id}">
            <span class="cyoa-option-icon">${sp.icon}</span>
            <span class="cyoa-option-label">${escapeHtml(sp.label)}</span>
            <span class="cyoa-option-desc">${escapeHtml(sp.description)}</span>
          </button>
        `).join('')}
      </div>
    </div>
  `;
  document.getElementById('btn-lp-back')?.addEventListener('click', goBackLearning);
  detail.querySelectorAll('.cyoa-option-btn').forEach((btn) => {
    btn.addEventListener('click', async () => {
      const subPathId = btn.getAttribute('data-sub-path');
      cyoaState.subPathId = subPathId;
      const res = await fetch(`/api/resources/paths/${cyoaState.pathId}/sub/${subPathId}`);
      if (!res.ok) return;
      const data = await res.json();
      renderPathModules(cyoaState.pathData, data.modules, subPathId);
    });
  });
}

function renderPathModules(path, modules, subPathId) {
  const detail = document.getElementById('learning-path-detail');
  const subPath = subPathId && path.sub_paths
    ? path.sub_paths.find((sp) => sp.sub_path_id === subPathId)
    : null;
  const subLabel = subPath ? ` — ${subPath.label}` : '';

  detail.innerHTML = `
    <button type="button" class="lp-back-btn" id="btn-lp-back">← ${subPathId ? 'Choose Size' : 'All Paths'}</button>
    <div class="lp-detail-header">
      <span class="lp-detail-icon">${path.icon}</span>
      <div>
        <h3>${escapeHtml(path.title)}${escapeHtml(subLabel)}</h3>
        <p>${escapeHtml(path.description)}</p>
        <div class="lp-meta">${modules.length} modules · ${escapeHtml(path.target_audience)}</div>
      </div>
    </div>
    <div class="lp-modules">${modules.map((mod, i) => `
      <div class="lp-module">
        <div class="lp-module-num">${i + 1}</div>
        <div class="lp-module-body">
          <h4>${escapeHtml(mod.title)} <span class="lp-weeks">~${mod.estimated_weeks} wk</span></h4>
          <p>${escapeHtml(mod.summary)}</p>
          <ul class="lp-checklist">${mod.checklist.map((c) => `<li>${escapeHtml(c)}</li>`).join('')}</ul>
          ${mod.ai_prompt_suggestion ? `<button type="button" class="lp-ai-btn" data-mode="${path.agronomy_mode}" data-prompt="${escapeHtml(mod.ai_prompt_suggestion)}">💬 Ask AI about this</button>` : ''}
        </div>
      </div>
    `).join('')}</div>
    <div class="lp-cta-row">
      ${path.cta_action === 'story_map' ? `<button type="button" class="ai-card-action-btn" id="btn-lp-story-map" data-mode="${path.agronomy_mode}">${escapeHtml(path.cta_label || 'Start Walkthrough')}</button>` : ''}
      ${path.cta_action === 'ai_chat' ? `<button type="button" class="ai-card-action-btn" id="btn-lp-ai-chat" data-mode="${path.agronomy_mode}">Open AI Agronomist</button>` : ''}
      ${path.cta_action === 'list_farm' ? `<button type="button" class="ai-card-action-btn" id="btn-lp-list-farm">List My Farm</button>` : ''}
    </div>
  `;
  document.getElementById('btn-lp-back')?.addEventListener('click', goBackLearning);
  detail.querySelectorAll('.lp-ai-btn').forEach((btn) => {
    btn.addEventListener('click', () => openAgronomyChat(btn.getAttribute('data-mode'), btn.getAttribute('data-prompt')));
  });
  document.getElementById('btn-lp-story-map')?.addEventListener('click', (e) => {
    if (typeof window.switchTab === 'function') window.switchTab('advisory-panel');
    openStoryMapGenerator(e.currentTarget.getAttribute('data-mode') || 'gardener');
  });
  document.getElementById('btn-lp-ai-chat')?.addEventListener('click', (e) => openAgronomyChat(e.currentTarget.getAttribute('data-mode')));
  document.getElementById('btn-lp-list-farm')?.addEventListener('click', () => {
    if (typeof window.switchTab === 'function') window.switchTab('map-panel');
    document.getElementById('auth-modal').style.display = 'flex';
  });
}

function openAgronomyChat(mode, prompt) {
  if (typeof window.switchTab === 'function') window.switchTab('advisory-panel');
  if (typeof window.setAgronomyMode === 'function') window.setAgronomyMode(mode);
  const modeBtn = document.querySelector(`.agronomy-mode-btn[data-mode="${mode}"]`);
  if (modeBtn) {
    document.querySelectorAll('.agronomy-mode-btn').forEach((b) => b.classList.remove('active'));
    modeBtn.classList.add('active');
    updateAgronomyPromptChips(mode);
  }
  const chatBody = document.getElementById('agronomy-chat-body');
  if (chatBody) { chatBody.style.display = 'block'; document.getElementById('chat-toggle-icon').textContent = '▼'; }
  if (prompt && typeof window.sendAgronomyQuery === 'function') {
    document.getElementById('agronomy-query-input').value = prompt;
    window.sendAgronomyQuery(prompt);
  }
  document.getElementById('agronomy-chat-drawer')?.scrollIntoView({ behavior: 'smooth' });
}

function initPhases() {
  setupAgronomyModeSelector();
  setupStoryMapUI();
  document.getElementById('tab-learn')?.addEventListener('click', () => loadLearningPaths());
  if (window.lucide) window.lucide.createIcons();
}

document.addEventListener('DOMContentLoaded', initPhases);
