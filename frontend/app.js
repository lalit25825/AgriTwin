(() => {
  'use strict';

  const API = '';
  const state = {
    token: localStorage.getItem('agritwin_token') || '',
    user: null,
    role: 'farmer',
    dashboard: null,
    connectionBox: 'all',
    activeConnectionId: null,
    activeConnectionName: '',
    listingTarget: null,
    people: [],
    listings: [],
    connections: [],
    roleWorkspace: null,
  };
  let driverMap = null;
  let driverRouteLayer = null;
  let driverMarkersLayer = null;
  let lastAutoRouteKey = '';
  let aiOwnerKey = '';
  let aiSessionId = '';
  let aiMessages = [];
  let aiSending = false;
  let aiAgentCatalog = [];
  let aiPlannedCatalog = [];

  const $ = (selector, root = document) => root.querySelector(selector);
  const $$ = (selector, root = document) => [...root.querySelectorAll(selector)];
  const roleLabels = {
    farmer: 'Farmer', driver: 'Driver / vehicle owner', storage_owner: 'Storage owner',
    mandi_seller: 'Mandi seller / trader', mandi_owner: 'Mandi owner / operator',
    fpo_manager: 'FPO manager', buyer: 'Buyer', transporter: 'Transporter',
    storage_provider: 'Storage provider', fpo: 'FPO manager', admin: 'Administrator'
  };
  const aiRoleCopy = {
    farmer: { title: 'Farmer workspace', description: 'Prioritise crop health, harvest timing, weather risk, market choices, net realization and safe movement of your produce.', prompts: [
      ['✳', 'Harvest readiness', 'Should I harvest onions in Nashik tomorrow?', 'Check crop maturity and weather before deciding.'],
      ['☼', 'Weather outlook', 'Give me the weather forecast for Nashik for the next 5 days.', 'Review rain, temperature and wind risk.'],
      ['⌁', 'Market decision', 'Compare the latest available onion prices in Lasalgaon and nearby mandis.', 'Check quote dates, freshness and nearby markets.'],
      ['↗', 'Move my produce', 'Plan transportation for 8 tonnes of onions from Nashik to Lasalgaon and estimate the cost.', 'Review route, vehicle suitability and trip cost.']
    ] },
    driver: { title: 'Driver / vehicle owner workspace', description: 'Prioritise load suitability, pickup and drop planning, road routes, estimated trip costs, weather exposure and vehicle utilization.', prompts: [
      ['↗', 'Plan a delivery route', 'Plan the best available route for 8 tonnes of onions from Nashik to Lasalgaon.', 'Compare route distance, travel time and cost assumptions.'],
      ['⚖', 'Estimate a trip', 'Estimate the transport cost for moving 12 tonnes of produce from Nashik to Pune.', 'Review load, distance and cost components.'],
      ['☼', 'Check route weather', 'What weather conditions could affect a produce trip from Nashik tomorrow?', 'Review rain, wind and temperature conditions.'],
      ['📦', 'Prepare for a load', 'What details should I confirm before accepting a 10-tonne agricultural shipment?', 'Check the shipment and vehicle information to confirm.']
    ] },
    storage_owner: { title: 'Storage owner workspace', description: 'Prioritise crop-specific storage conditions, storage duration, weather exposure, spoilage risk, inventory movement and commercial decisions.', prompts: [
      ['🌾', 'Storage conditions', 'What storage conditions should I maintain for onions over the next 30 days?', 'Review commodity-specific handling and storage guidance.'],
      ['☼', 'Weather exposure', 'Give me the weather outlook for Nashik and explain risks for stored produce.', 'Assess weather information and practical precautions.'],
      ['⌁', 'Store or sell context', 'Compare the latest available onion market observations for Nashik and nearby mandis.', 'Understand price freshness and nearby market signals.'],
      ['↗', 'Plan movement', 'Estimate the cost of moving 20 tonnes of onions from Nashik to Lasalgaon.', 'Plan an inbound or outbound shipment.']
    ] },
    mandi_seller: { title: 'Mandi seller / trader workspace', description: 'Prioritise sourcing, mandi quote freshness, nearby market comparisons, quality and grade, purchase economics and transport planning.', prompts: [
      ['⌁', 'Compare mandi prices', 'Compare the latest available onion prices in Lasalgaon and nearby mandis.', 'Check official observations and their dates.'],
      ['🧺', 'Review a purchase', 'What should I inspect before buying 20 tonnes of onions from a farmer?', 'Build a practical sourcing checklist.'],
      ['↗', 'Estimate transport', 'Estimate the cost of moving 20 tonnes of onions from Nashik to Pune.', 'Review route and transport assumptions.'],
      ['☼', 'Arrival weather', 'Give me the next 5 days weather forecast for Nashik.', 'Plan around weather and movement risks.']
    ] },
    mandi_owner: { title: 'Mandi operator workspace', description: 'Prioritise arrivals, commodity mix, market observations, yard movement, dispatch coordination and operational planning.', prompts: [
      ['⌁', 'Market snapshot', 'Compare the latest available onion price observations in Nashik and nearby markets.', 'Check published quote dates and differences.'],
      ['☼', 'Weather for arrivals', 'Give me the 5-day forecast for Nashik and highlight risks for produce arrivals.', 'Review weather and operational exposure.'],
      ['↗', 'Plan shipment movement', 'Plan a route for moving 25 tonnes of onions from Nashik to Lasalgaon.', 'Review routing and vehicle requirements.'],
      ['📋', 'Arrival planning', 'What information should I collect to coordinate several produce arrivals at a mandi?', 'Create a practical arrival checklist.']
    ] },
    fpo_manager: { title: 'FPO manager workspace', description: 'Prioritise farmer aggregation, harvest windows, collective quantities, bulk transport, storage coordination and buyer or mandi linkages.', prompts: [
      ['🌱', 'Aggregate harvests', 'Help plan a harvest and aggregation schedule for onion farmers in Nashik.', 'Coordinate crop stages and field-level timing.'],
      ['⌁', 'Compare market options', 'Compare latest available onion mandi observations for Lasalgaon and nearby markets.', 'Review market quote freshness and options.'],
      ['↗', 'Move a bulk lot', 'Plan transportation for 40 tonnes of onions from Nashik to Lasalgaon and estimate the cost.', 'Review route, vehicles and shipment assumptions.'],
      ['☼', 'Member weather outlook', 'Give me the weather forecast for Nashik for the next 5 days.', 'Support harvest and collection scheduling.']
    ] }
  };
  const categoryLabels = {
    produce: 'Crop for sale', need_transport: 'Transport needed', need_storage: 'Storage needed',
    need_buyer: 'Looking for buyers', need_fpo_support: 'FPO support needed', transport: 'Transport service',
    storage: 'Storage capacity', buying: 'Buying produce', mandi_service: 'Mandi service', fpo_service: 'FPO services'
  };
  const categoryIcons = {
    produce: '🌾', need_transport: '🚚', need_storage: '🏬', need_buyer: '🤝', need_fpo_support: '👥',
    transport: '🚛', storage: '🏚', buying: '🧺', mandi_service: '🏪', fpo_service: '🌱'
  };
  const allowedCategories = {
    farmer: ['produce', 'need_transport', 'need_storage', 'need_buyer', 'need_fpo_support'],
    driver: ['transport'], transporter: ['transport'], storage_owner: ['storage'], storage_provider: ['storage'],
    mandi_seller: ['buying'], buyer: ['buying'], mandi_owner: ['mandi_service'], fpo_manager: ['fpo_service', 'produce', 'need_transport', 'need_storage', 'need_buyer'], fpo: ['fpo_service', 'produce', 'need_transport', 'need_storage', 'need_buyer']
  };
  const quickActionSets = {
    farmer: [
      ['🚚', 'Find a vehicle', 'Connect with drivers for your harvest.', 'marketplace', 'need_transport'],
      ['🏬', 'Find storage', 'Compare available storage capacity.', 'marketplace', 'need_storage'],
      ['🤝', 'Reach buyers', 'Connect with traders and mandi sellers.', 'marketplace', 'need_buyer'],
      ['🌱', 'Talk to an FPO', 'Get aggregation and market support.', 'network', 'fpo_manager'],
    ],
    driver: [
      ['📦', 'Find available loads', 'Discover produce that needs movement.', 'marketplace', 'need_transport'],
      ['＋', 'Publish vehicle capacity', 'Share your routes and availability.', 'create', 'transport'],
      ['👨‍🌾', 'Meet farmers', 'Build direct relationships with producers.', 'network', 'farmer'],
      ['🏪', 'Connect with mandis', 'Coordinate unloading and delivery.', 'network', 'mandi_owner'],
    ],
    storage_owner: [
      ['🌾', 'Find produce owners', 'Connect with farmers seeking storage.', 'marketplace', 'need_storage'],
      ['＋', 'Publish free capacity', 'Show available space and storage type.', 'create', 'storage'],
      ['🧺', 'Meet traders', 'Build relationships with mandi sellers.', 'network', 'mandi_seller'],
      ['🚚', 'Arrange transport', 'Find drivers for inbound and outbound loads.', 'network', 'driver'],
    ],
    mandi_seller: [
      ['🌾', 'Find produce', 'Discover farmers and FPO supply.', 'marketplace', 'produce'],
      ['＋', 'Post buying requirement', 'Tell the network what you need to buy.', 'create', 'buying'],
      ['🏬', 'Find storage', 'Arrange holding space for inventory.', 'network', 'storage_owner'],
      ['🚚', 'Arrange transport', 'Connect with vehicle owners.', 'network', 'driver'],
    ],
    mandi_owner: [
      ['🧺', 'Meet sellers', 'Connect with traders and commission agents.', 'network', 'mandi_seller'],
      ['＋', 'Publish mandi services', 'Share facilities and operating details.', 'create', 'mandi_service'],
      ['🚚', 'Coordinate arrivals', 'Find vehicles for scheduled movement.', 'network', 'driver'],
      ['🌱', 'Connect with FPOs', 'Build direct institutional partnerships.', 'network', 'fpo_manager'],
    ],
    fpo_manager: [
      ['👨‍🌾', 'Connect with farmers', 'Find producers and build aggregation.', 'network', 'farmer'],
      ['＋', 'Publish FPO services', 'Share what your FPO can support.', 'create', 'fpo_service'],
      ['🚚', 'Consolidate transport', 'Find drivers for bulk movement.', 'network', 'driver'],
      ['🧺', 'Reach buyers', 'Connect aggregated produce with traders.', 'network', 'mandi_seller'],
    ]
  };

  function esc(value) {
    return String(value ?? '').replace(/[&<>"']/g, ch => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[ch]));
  }
  function initials(name) {
    return String(name || '?').trim().split(/\s+/).slice(0, 2).map(s => s[0] || '').join('').toUpperCase() || '?';
  }
  function toast(message, bad = false) {
    const el = $('#toast');
    el.textContent = message;
    el.style.background = bad ? '#874b3e' : '';
    el.classList.add('show');
    window.clearTimeout(toast.timer);
    toast.timer = window.setTimeout(() => el.classList.remove('show'), 3200);
  }
  async function api(path, options = {}) {
    const headers = new Headers(options.headers || {});
    if (state.token) headers.set('Authorization', `Bearer ${state.token}`);
    if (options.body && !(options.body instanceof FormData)) headers.set('Content-Type', 'application/json');
    let response;
    try {
      response = await fetch(`${API}${path}`, { ...options, headers });
    } catch (error) {
      throw new Error('Cannot reach the AgriTwin server. Check that the API is running on port 8000.');
    }
    const data = response.status === 204 ? null : await response.json().catch(() => ({}));
    if (response.status === 401) {
      signOut(false);
      throw new Error(data?.detail || 'Your session has expired. Please sign in again.');
    }
    if (!response.ok) {
      const detail = data?.detail;
      throw new Error(Array.isArray(detail) ? detail.map(item => item.msg).join(', ') : (detail || `Request failed (${response.status})`));
    }
    return data;
  }
  function setBusy(button, busy, label = 'Please wait…') {
    if (!button) return;
    if (busy) {
      button.dataset.original = button.innerHTML;
      button.disabled = true;
      button.textContent = label;
    } else {
      button.disabled = false;
      if (button.dataset.original) button.innerHTML = button.dataset.original;
    }
  }
  function showAuth(mode = 'login') {
    $('#authScreen').hidden = false;
    $('#appShell').hidden = true;
    setAuthMode(mode);
  }
  function showApp() {
    $('#authScreen').hidden = true;
    $('#appShell').hidden = false;
  }
  function signOut(showMessage = true) {
    localStorage.removeItem('agritwin_token');
    state.token = '';
    state.user = null;
    state.dashboard = null;
    showAuth('login');
    if (showMessage) toast('You have signed out.');
  }
  function setAuthMode(mode) {
    const isRegister = mode === 'register';
    $('#loginForm').hidden = isRegister;
    $('#registerForm').hidden = !isRegister;
    $$('.auth-tab').forEach(button => button.classList.toggle('active', button.dataset.auth === mode));
    $('#authTitle').textContent = isRegister ? 'Join the network' : 'Welcome back';
    $('#authSubtitle').textContent = isRegister ? 'Create an account for your role in the agricultural supply chain.' : 'Sign in to your AgriTwin workspace.';
    $('#authError').hidden = true;
  }
  async function establishSession(identifier, password) {
    const result = await api('/auth/login', { method: 'POST', body: JSON.stringify({ identifier, password }) });
    state.token = result.access_token;
    localStorage.setItem('agritwin_token', state.token);
    state.user = await api('/users/me');
    state.role = state.user.role;
    await loadWorkspace();
    showApp();
    showPage('overview');
    toast(`Welcome to AgriTwin, ${state.user.full_name.split(' ')[0]}.`);
  }
  function roleLabel(role = state.role) { return roleLabels[role] || 'Stakeholder'; }
  function updateIdentity() {
    const name = state.user?.full_name || 'Your account';
    const role = roleLabel();
    $('#workspaceRole').textContent = `${role} workspace`;
    $('#sidebarName').textContent = name;
    $('#sidebarRole').textContent = role;
    $('#sidebarAvatar').textContent = initials(name);
    $('#topAvatar').textContent = initials(name);
    $('#profileAvatar').textContent = initials(name);
    $('#profileName').textContent = name;
    $('#profileRole').textContent = role;
    $('#profileEmail').textContent = state.user?.email || '';
  }
  async function loadWorkspace() {
    updateIdentity();
    const [dashboardResult, statusResult] = await Promise.allSettled([
      api('/marketplace/dashboard'), api('/agents/status')
    ]);
    if (dashboardResult.status === 'rejected') throw dashboardResult.reason;
    state.dashboard = dashboardResult.value;
    const agentsOk = statusResult.status === 'fulfilled';
    $('#networkStatusText').textContent = agentsOk ? 'Network online' : 'API online';
    renderDashboard();
    await Promise.allSettled([loadMarketplace(), loadDirectory(), loadConnections('all'), loadMyProfile(), loadRoleWorkspace()]);
    await initAiWorkspace();
  }
  function showPage(page) {
    const allowed = ['overview', 'marketplace', 'network', 'requests', 'listings', 'profile', 'agents'];
    if (!allowed.includes(page)) page = 'overview';
    $$('.page-view').forEach(view => view.classList.toggle('active', view.id === `page-${page}`));
    $$('.nav-item[data-page]').forEach(button => button.classList.toggle('active', button.dataset.page === page));
    $('#breadcrumbPage').textContent = ({ overview: 'Overview', marketplace: 'Marketplace', network: 'Stakeholder network', requests: 'Connections', listings: 'My listings', profile: 'My profile', agents: 'AI assistant' })[page];
    $('#sidebar').classList.remove('open');
    if (page === 'marketplace') loadMarketplace();
    if (page === 'network') loadDirectory();
    if (page === 'requests') loadConnections(state.connectionBox);
    if (page === 'listings') loadMyListings();
    if (page === 'profile') loadMyProfile();
    if (page === 'agents') loadAiAgents();
    if (page === 'overview' && state.role === 'driver') window.setTimeout(() => driverMap?.invalidateSize(), 120);
  }
  function renderDashboard() {
    const d = state.dashboard;
    if (!d) return;
    $('#welcomeTitle').textContent = d.welcome?.title || 'Your supply chain, connected.';
    $('#welcomeSubtitle').textContent = d.welcome?.subtitle || 'Find the people and services that move your harvest forward.';
    $('#metricListings').textContent = d.metrics?.active_listings ?? 0;
    $('#metricIncoming').textContent = d.metrics?.incoming_requests ?? 0;
    $('#metricConnections').textContent = d.metrics?.active_connections ?? 0;
    $('#metricMatches').textContent = d.metrics?.recommended_matches ?? 0;
    const metricCopy = {
      farmer: ['My crop & need listings', 'Your produce and requirements', 'Incoming enquiries', 'Responses to your posts', 'Connected partners', 'Accepted business contacts'],
      driver: ['Available services', 'Your vehicle capacity posts', 'Load enquiries', 'Farmers and businesses reaching you', 'Active customers', 'Accepted business contacts'],
      storage_owner: ['Storage listings', 'Your published capacity', 'Storage enquiries', 'Farmers and traders reaching you', 'Connected partners', 'Accepted business contacts'],
      mandi_seller: ['Buying requirements', 'Your active sourcing posts', 'Supply enquiries', 'Farmers and FPOs reaching you', 'Supply partners', 'Accepted business contacts'],
      mandi_owner: ['Market service listings', 'Your mandi service posts', 'Service enquiries', 'Stakeholders reaching your market', 'Market partners', 'Accepted business contacts'],
      fpo_manager: ['FPO service listings', 'Your programmes and services', 'Partner requests', 'Requests from your supply chain', 'Network partners', 'Accepted business contacts']
    }[state.role] || ['My active listings', 'Published by you', 'New requests', 'Waiting for your response', 'Active connections', 'Accepted partners'];
    $('#metricListingsLabel').textContent = metricCopy[0]; $('#metricListingsHint').textContent = metricCopy[1];
    $('#metricIncomingLabel').textContent = metricCopy[2]; $('#metricIncomingHint').textContent = metricCopy[3];
    $('#metricConnectionsLabel').textContent = metricCopy[4]; $('#metricConnectionsHint').textContent = metricCopy[5];
    const requestCount = d.metrics?.incoming_requests ?? 0;
    $('#requestCount').textContent = requestCount;
    $('#requestCount').hidden = requestCount < 1;
    $('#profilePercent').textContent = `${d.profile_completion ?? 0}%`;
    $('#profileProgressBar').style.width = `${d.profile_completion ?? 0}%`;
    $('#profileSidePercent').textContent = `${d.profile_completion ?? 0}%`;
    $('#profileSideBar').style.width = `${d.profile_completion ?? 0}%`;
    renderQuickActions();
    renderRecommendations(d.recommended_matches || []);
    renderRecentRequests(d.recent_requests || []);
  }
  function renderQuickActions() {
    const aliases = { transporter: 'driver', storage_provider: 'storage_owner', buyer: 'mandi_seller', fpo: 'fpo_manager' };
    const normalizedRole = aliases[state.role] || state.role;
    const actions = quickActionSets[normalizedRole] || quickActionSets.farmer;
    const subtitles = { farmer: 'Your next move, from harvest pickup to a fair sale.', driver: 'Find loads, publish capacity and connect with reliable business partners.', storage_owner: 'Fill available space by connecting directly with produce owners.', mandi_seller: 'Source produce, share buying needs and coordinate the next movement.', mandi_owner: 'Bring arrivals, traders and service partners into one coordinated view.', fpo_manager: 'Coordinate members, aggregated lots and partners across the chain.' };
    $('#quickActionSubtitle').textContent = subtitles[normalizedRole] || 'Start with a task. AgriTwin helps you find the right stakeholder.';
    $('#quickActions').innerHTML = actions.map(([icon, title, description, action, filter]) => `
      <button class="quick-action" data-quick-action="${esc(action)}" data-filter="${esc(filter)}"><span class="qa-icon">${icon}</span><strong>${esc(title)}</strong><small>${esc(description)}</small><span class="qa-arrow">↗</span></button>`).join('');
  }
  function renderRecommendations(items) {
    const host = $('#recommendedMatches');
    if (!items.length) {
      host.innerHTML = `<div class="empty-state"><strong>Your network is just getting started.</strong>Complete your profile and explore the marketplace to find your first partner.</div>`;
      return;
    }
    host.innerHTML = items.slice(0, 5).map(item => `
      <div class="listing-row"><div class="listing-kind">${categoryIcons[item.category] || '✳'}</div><div class="listing-row-body"><strong>${esc(item.title)}</strong><small>${esc(item.owner_name)} · ${esc(item.owner_role_label)} · ${esc(item.district || item.owner_profile?.district || item.location || 'Location not added')}</small></div><div class="match-score"><strong>${item.match_score ?? '—'}%</strong><small>match</small></div><button class="mini-arrow" data-connect-listing="${item.id}" title="Connect">→</button></div>`).join('');
  }
  function renderRecentRequests(items) {
    const host = $('#recentRequests');
    if (!items.length) { host.innerHTML = '<div class="empty-inline">No incoming requests yet. Publish a listing to help partners find you.</div>'; return; }
    host.innerHTML = items.slice(0, 4).map(item => `<div class="request-mini"><div class="request-avatar">${initials(item.other_person?.name)}</div><div><strong>${esc(item.other_person?.name || 'Stakeholder')}</strong><small>${esc(item.other_person?.role_label || 'Stakeholder')} · ${esc(item.status)}</small></div><i class="request-dot"></i></div>`).join('');
  }
  async function loadMarketplace() {
    const host = $('#marketplaceGrid');
    if (!host) return;
    host.innerHTML = '<div class="loading-line">Loading marketplace…</div>';
    try {
      const params = new URLSearchParams();
      const q = $('#listingSearch')?.value.trim();
      const category = $('#listingCategory')?.value;
      const district = $('#listingDistrict')?.value.trim();
      if (q) params.set('q', q);
      if (category) params.set('category', category);
      if (district) params.set('district', district);
      const result = await api(`/marketplace/listings?${params.toString()}`);
      state.listings = result.listings || [];
      $('#marketplaceCount').textContent = result.count;
      $('#listingResultsCount').textContent = `${result.count} active listing${result.count === 1 ? '' : 's'}`;
      renderListings(host, state.listings);
    } catch (error) { host.innerHTML = `<div class="empty-state">${esc(error.message)}</div>`; }
  }
  function renderListings(host, items) {
    if (!items.length) { host.innerHTML = '<div class="empty-state"><strong>No listings match these filters.</strong>Try another crop or district, or publish the first listing for this requirement.</div>'; return; }
    host.innerHTML = items.map(item => {
      const location = [item.district, item.state].filter(Boolean).join(', ') || item.location || 'Location not specified';
      const facts = [];
      if (item.commodity) facts.push(`🌾 ${esc(item.commodity)}`);
      if (item.quantity_tonnes) facts.push(`⚖ ${esc(item.quantity_tonnes)} tonnes`);
      if (item.capacity_tonnes) facts.push(`▤ ${esc(item.capacity_tonnes)} t capacity`);
      if (item.price_per_quintal !== null && item.price_per_quintal !== undefined) facts.push(`₹ ${Number(item.price_per_quintal).toLocaleString('en-IN')}/q`);
      return `<article class="listing-card"><div class="listing-card-top"><span class="category-pill">${esc(item.category_label)}</span>${item.match_score ? `<span class="score-pill">${item.match_score}% fit</span>` : ''}</div><h3>${esc(item.title)}</h3><p class="listing-desc">${esc(item.description || item.price_note || 'Open this listing to connect and discuss the details.')}</p><div class="listing-facts">${facts.map(x => `<span>${x}</span>`).join('')}<span>⌖ ${esc(location)}</span></div><div class="listing-owner"><div class="request-avatar">${initials(item.owner_name)}</div><div><strong>${esc(item.owner_name)}</strong><small>${esc(item.owner_role_label)}${item.owner_verified ? ' · Verified' : ''}</small></div>${item.is_mine ? `<button data-close-listing="${item.id}">Close listing</button>` : `<button data-connect-listing="${item.id}">Connect</button>`}</div></article>`;
    }).join('');
  }
  async function loadDirectory() {
    const host = $('#peopleGrid');
    if (!host) return;
    host.innerHTML = '<div class="loading-line">Finding stakeholders…</div>';
    try {
      const params = new URLSearchParams();
      const role = $('#peopleRole')?.value;
      const district = $('#peopleDistrict')?.value.trim();
      const q = $('#peopleSearch')?.value.trim();
      if (role) params.set('role', role);
      if (district) params.set('district', district);
      if (q) params.set('q', q);
      const [result, map, matrix] = await Promise.all([api(`/marketplace/directory?${params.toString()}`), api('/marketplace/connection-map'), api('/marketplace/connection-matrix')]);
      state.people = result.people || [];
      $('#peopleCount').textContent = `${result.count} stakeholder${result.count === 1 ? '' : 's'} found`;
      $('#networkSummary').innerHTML = (map.connections || []).map(row => `<div class="network-chip"><strong>${row.score}</strong>${esc(row.label)} compatibility</div>`).join('');
      renderPeople(host, state.people);
      if (!$('#networkSummary').dataset.note) $('#networkSummary').title = map.note || '';
      renderCompatibilityMatrix(matrix);
    } catch (error) { host.innerHTML = `<div class="empty-state">${esc(error.message)}</div>`; }
  }
  function renderCompatibilityMatrix(data) {
    const host = $('#compatibilityMatrix');
    if (!host || !data?.roles || !data?.matrix) return;
    const roleKeys = data.roles.map(role => role.value);
    const labels = Object.fromEntries(data.roles.map(role => [role.value, role.label]));
    host.innerHTML = `<table class="matrix-table"><thead><tr><th>From \ To</th>${roleKeys.map(key => `<th>${esc(labels[key])}</th>`).join('')}</tr></thead><tbody>${data.matrix.map(row => `<tr><th>${esc(row.from_label)}</th>${roleKeys.map(target => { const score = row.scores[target]; return `<td>${score == null ? '<span class="matrix-diagonal">—</span>' : `<span class="matrix-score ${score >= 90 ? 'high' : score >= 80 ? 'medium' : 'low'}">${score}</span>`}</td>`; }).join('')}</tr>`).join('')}</tbody></table>`;
  }

  function renderPeople(host, people) {
    if (!people.length) { host.innerHTML = '<div class="empty-state"><strong>No stakeholder profiles found.</strong>Try another district or role. New stakeholders appear after they create an account.</div>'; return; }
    host.innerHTML = people.map(person => {
      const profile = person.profile || {};
      const where = [profile.village, profile.district, profile.state].filter(Boolean).join(', ');
      const commodities = (profile.commodities || []).slice(0, 3);
      if (profile.vehicle_type) commodities.push(profile.vehicle_type);
      if (profile.storage_type) commodities.push(profile.storage_type);
      return `<article class="person-card"><div class="person-card-head"><div class="person-avatar">${initials(person.name)}</div><div><h3>${esc(person.name)} ${person.is_verified ? '<span class="verified">✓</span>' : ''}</h3><small>${esc(person.role_label)} · ${esc(profile.organization || 'Independent')}</small></div></div><p>${esc(profile.about || profile.headline || 'This stakeholder has not added an introduction yet.')}</p><div class="person-tags">${commodities.map(tag => `<span>${esc(tag)}</span>`).join('')}${where ? `<span>⌖ ${esc(where)}</span>` : ''}</div><div class="person-card-foot"><small>${person.match_score ?? '—'}% workflow fit</small><button data-connect-person="${person.id}" data-person-name="${esc(person.name)}">Connect ↗</button></div></article>`;
    }).join('');
  }
  async function loadConnections(box = state.connectionBox) {
    state.connectionBox = box;
    const host = $('#connectionsList');
    if (!host) return;
    host.innerHTML = '<div class="loading-line">Loading connections…</div>';
    try {
      const result = await api(`/connections?box=${box}`);
      state.connections = result.connections || [];
      renderConnections(host, state.connections);
      $$('.tab').forEach(tab => tab.classList.toggle('active', tab.dataset.box === box));
    } catch (error) { host.innerHTML = `<div class="empty-state">${esc(error.message)}</div>`; }
  }
  function renderConnections(host, items) {
    if (!items.length) { host.innerHTML = '<div class="empty-state"><strong>No connection requests yet.</strong>Explore the network or send a request from a marketplace listing. Accepted connections can message each other privately.</div>'; return; }
    host.innerHTML = items.map(item => {
      const person = item.other_person || {};
      const incomingPending = item.is_incoming && item.status === 'pending';
      const actions = incomingPending ? `<button class="primary" data-connection-action="accepted" data-id="${item.id}">Accept</button><button data-connection-action="declined" data-id="${item.id}">Decline</button>` : '';
      const canCancel = !item.is_incoming && item.status === 'pending';
      return `<article class="connection-card"><div class="person-avatar">${initials(person.name)}</div><div class="connection-main"><div class="connection-meta"><span class="status-pill ${esc(item.status)}">${esc(item.status)}</span><span>${item.is_incoming ? 'Incoming request' : 'Sent by you'}</span><span>${new Date(item.created_at).toLocaleDateString()}</span></div><h3>${esc(person.name || 'Stakeholder')} · ${esc(person.role_label || 'Stakeholder')}</h3><p>${esc(item.message)}</p><div class="connection-meta">${item.purpose ? `<span>Purpose: ${esc(item.purpose.replaceAll('_', ' '))}</span>` : ''}${item.commodity ? `<span>Crop: ${esc(item.commodity)}</span>` : ''}${item.quantity_tonnes ? `<span>Quantity: ${esc(item.quantity_tonnes)} tonnes</span>` : ''}${item.offered_price ? `<span>Offer: ₹${Number(item.offered_price).toLocaleString('en-IN')}/q</span>` : ''}</div><div class="connection-actions">${actions}${item.status === 'accepted' ? `<button class="primary" data-message-connection="${item.id}" data-message-name="${esc(person.name)}">Open messages</button><button data-connection-action="completed" data-id="${item.id}">Mark completed</button>` : ''}${canCancel ? `<button data-connection-action="cancelled" data-id="${item.id}">Cancel request</button>` : ''}</div></div></article>`;
    }).join('');
  }
  async function loadMyListings() {
    const host = $('#myListingsGrid');
    if (!host) return;
    host.innerHTML = '<div class="loading-line">Loading your listings…</div>';
    try {
      const result = await api('/marketplace/listings?limit=150');
      const mine = (result.listings || []).filter(item => item.is_mine);
      renderListings(host, mine);
      if (!mine.length) host.innerHTML = '<div class="empty-state"><strong>You have not published anything yet.</strong>Share your crop, available capacity, buying requirement or service to become discoverable.</div>';
    } catch (error) { host.innerHTML = `<div class="empty-state">${esc(error.message)}</div>`; }
  }
  async function loadMyProfile() {
    try {
      const result = await api('/marketplace/profile/me');
      const p = result.profile || {};
      const form = $('#profileForm');
      if (!form) return;
      Object.entries(p).forEach(([key, value]) => {
        const input = form.elements.namedItem(key);
        if (!input) return;
        if (key === 'commodities') input.value = Array.isArray(value) ? value.join(', ') : '';
        else input.value = value ?? '';
      });
      updateIdentity();
    } catch (error) { console.warn('Profile load failed', error); }
  }
  function openListingDialog(preferredCategory = '') {
    const select = $('#listingType');
    const categories = allowedCategories[state.role] || allowedCategories.farmer;
    select.innerHTML = categories.map(category => `<option value="${category}">${esc(categoryLabels[category])}</option>`).join('');
    if (preferredCategory && categories.includes(preferredCategory)) select.value = preferredCategory;
    $('#listingForm').reset();
    if (preferredCategory && categories.includes(preferredCategory)) select.value = preferredCategory;
    $('#listingFeedback').textContent = '';
    $('#listingDialog').showModal();
  }
  function openConnectDialog({ recipientId = '', listingId = '', name = '' } = {}) {
    const form = $('#connectForm');
    form.reset();
    form.elements.namedItem('recipient_id').value = recipientId;
    form.elements.namedItem('listing_id').value = listingId;
    $('#connectTargetName').textContent = name ? `Send a request to ${name}.` : 'Send a request to the listing owner.';
    $('#connectFeedback').textContent = '';
    $('#connectDialog').showModal();
  }
  async function closeListing(id) {
    if (!confirm('Close this listing? It will no longer appear as an active opportunity.')) return;
    try { await api(`/marketplace/listings/${id}`, { method: 'PATCH', body: JSON.stringify({ is_active: false }) }); toast('Listing closed.'); await Promise.all([loadMarketplace(), loadMyListings(), refreshDashboard()]); }
    catch (error) { toast(error.message, true); }
  }
  async function refreshDashboard() {
    try { state.dashboard = await api('/marketplace/dashboard'); renderDashboard(); await loadRoleWorkspace(); }
    catch (error) { toast(error.message, true); }
  }
  async function openMessages(id, name) {
    state.activeConnectionId = id;
    state.activeConnectionName = name || 'Stakeholder';
    $('#messageTitle').textContent = `Chat with ${state.activeConnectionName}`;
    $('#messageHistory').innerHTML = '<div class="loading-line">Loading messages…</div>';
    $('#messageDialog').showModal();
    await loadMessages();
  }
  async function loadMessages() {
    if (!state.activeConnectionId) return;
    try {
      const result = await api(`/connections/${state.activeConnectionId}/messages`);
      const host = $('#messageHistory');
      if (!result.messages?.length) host.innerHTML = '<div class="empty-inline">No messages yet. Introduce yourself and agree on the next step.</div>';
      else host.innerHTML = result.messages.map(message => `<div class="message-bubble ${message.is_mine ? 'mine' : ''}"><p>${esc(message.body)}</p><small>${esc(message.is_mine ? 'You' : message.sender_name)} · ${new Date(message.created_at).toLocaleString()}</small></div>`).join('');
      host.scrollTop = host.scrollHeight;
    } catch (error) { $('#messageHistory').innerHTML = `<div class="empty-inline">${esc(error.message)}</div>`; }
  }
  async function handleConnectionStatus(id, status) {
    try {
      await api(`/connections/${id}`, { method: 'PATCH', body: JSON.stringify({ status }) });
      toast(`Connection ${status}.`);
      await Promise.all([loadConnections(state.connectionBox), refreshDashboard()]);
    } catch (error) { toast(error.message, true); }
  }
  async function submitListing(event) {
    event.preventDefault();
    const form = event.currentTarget;
    const data = Object.fromEntries(new FormData(form).entries());
    ['quantity_tonnes', 'capacity_tonnes', 'price_per_quintal'].forEach(key => data[key] = data[key] === '' ? null : Number(data[key]));
    ['description', 'commodity', 'price_note', 'location', 'district', 'state', 'pickup_location', 'destination', 'available_from'].forEach(key => data[key] = data[key] || null);
    if (!data.quantity_tonnes) delete data.quantity_tonnes;
    if (!data.capacity_tonnes) delete data.capacity_tonnes;
    $('#listingFeedback').textContent = 'Publishing…';
    const button = form.querySelector('button[type="submit"]'); setBusy(button, true, 'Publishing…');
    try {
      await api('/marketplace/listings', { method: 'POST', body: JSON.stringify(data) });
      $('#listingDialog').close(); toast('Your listing is now visible to the network.');
      await Promise.all([loadMarketplace(), loadMyListings(), refreshDashboard()]);
    } catch (error) { $('#listingFeedback').textContent = error.message; }
    finally { setBusy(button, false); }
  }
  async function submitConnection(event) {
    event.preventDefault();
    const form = event.currentTarget;
    const data = Object.fromEntries(new FormData(form).entries());
    if (!data.recipient_id) delete data.recipient_id;
    if (!data.listing_id) delete data.listing_id;
    if (!data.commodity) delete data.commodity;
    if (!data.quantity_tonnes) delete data.quantity_tonnes; else data.quantity_tonnes = Number(data.quantity_tonnes);
    if (!data.offered_price) delete data.offered_price; else data.offered_price = Number(data.offered_price);
    $('#connectFeedback').textContent = 'Sending request…';
    const button = form.querySelector('button[type="submit"]'); setBusy(button, true, 'Sending…');
    try {
      await api('/connections', { method: 'POST', body: JSON.stringify(data) });
      $('#connectDialog').close(); toast('Connection request sent.');
      await Promise.all([loadConnections('all'), refreshDashboard()]);
    } catch (error) { $('#connectFeedback').textContent = error.message; }
    finally { setBusy(button, false); }
  }
  async function submitMessage(event) {
    event.preventDefault();
    const form = event.currentTarget;
    const body = form.elements.namedItem('body').value.trim();
    if (!body || !state.activeConnectionId) return;
    try {
      await api(`/connections/${state.activeConnectionId}/messages`, { method: 'POST', body: JSON.stringify({ body }) });
      form.reset(); await loadMessages();
    } catch (error) { toast(error.message, true); }
  }
  async function submitProfile(event) {
    event.preventDefault();
    const form = event.currentTarget;
    const data = Object.fromEntries(new FormData(form).entries());
    data.commodities = data.commodities.split(',').map(item => item.trim()).filter(Boolean);
    ['latitude', 'longitude', 'capacity_tonnes', 'service_radius_km'].forEach(key => data[key] = data[key] === '' ? null : Number(data[key]));
    $('#profileFeedback').textContent = 'Saving profile…';
    const button = form.querySelector('button[type="submit"]'); setBusy(button, true, 'Saving…');
    try {
      await api('/marketplace/profile/me', { method: 'PUT', body: JSON.stringify(data) });
      $('#profileFeedback').textContent = 'Your profile has been saved.';
      toast('Profile updated.'); await refreshDashboard(); await loadDirectory();
    } catch (error) { $('#profileFeedback').textContent = error.message; }
    finally { setBusy(button, false); }
  }

  const aiAgentLabels = {
    coordinator: 'AgriTwin Coordinator', harvest: 'Harvest Agent', climate: 'Climate Agent',
    market: 'Market Agent', logistics: 'Logistics Agent'
  };
  const aiAgentGlyphs = { coordinator: '✳', harvest: '✳', climate: '☼', market: '⌁', logistics: '↗' };

  function aiStorageKey(kind) {
    const userId = String(state.user?.id || state.user?.username || 'guest').replace(/[^a-zA-Z0-9_-]/g, '_');
    return `agritwin_ai_${kind}_${userId}`;
  }
  function createAiSessionId() {
    return (window.crypto && crypto.randomUUID) ? crypto.randomUUID() : `agritwin-${Date.now()}-${Math.random().toString(16).slice(2)}`;
  }
  function persistAiSession() {
    if (!state.user) return;
    try {
      sessionStorage.setItem(aiStorageKey('session'), aiSessionId);
      sessionStorage.setItem(aiStorageKey('history'), JSON.stringify(aiMessages.slice(-80)));
    } catch (_) { /* Browser storage may be disabled; the live conversation still works. */ }
  }
  function roleAiContent() {
    return aiRoleCopy[state.role] || {
      title: `${roleLabel()} workspace`,
      description: 'All active specialists are available. Ask about harvest, weather, mandi prices, transport, storage and supply-chain decisions.',
      prompts: aiRoleCopy.farmer.prompts
    };
  }
  function initAiWorkspace() {
    const ownerKey = String(state.user?.id || state.user?.username || 'guest');
    if (aiOwnerKey !== ownerKey) {
      aiOwnerKey = ownerKey;
      try {
        aiSessionId = sessionStorage.getItem(aiStorageKey('session')) || createAiSessionId();
        aiMessages = JSON.parse(sessionStorage.getItem(aiStorageKey('history')) || '[]');
        if (!Array.isArray(aiMessages)) aiMessages = [];
      } catch (_) {
        aiSessionId = createAiSessionId();
        aiMessages = [];
      }
    }
    renderAiRoleContext();
    renderAiChat();
    loadAiAgents();
  }
  function renderAiRoleContext() {
    const content = roleAiContent();
    const title = $('#aiRoleTitle');
    const description = $('#aiRoleDescription');
    if (title) title.textContent = content.title;
    if (description) description.textContent = `${content.description} All active agents are available to every stakeholder.`;
  }
  function setAiStatus(ready, message) {
    const dot = $('#aiStatusDot');
    const text = $('#aiStatusText');
    if (dot) dot.className = `ai-status-dot ${ready ? 'online' : 'offline'}`;
    if (text) text.textContent = message;
  }
  async function loadAiAgents() {
    if (!state.token || !$('#aiAgentList')) return;
    try {
      const [catalog, health] = await Promise.all([api('/ai/agents'), api('/ai/health')]);
      aiAgentCatalog = catalog.agents || [];
      aiPlannedCatalog = catalog.planned_agents || [];
      renderAiAgentCatalog();
      renderAiPlannedAgents();
      setAiStatus(Boolean(health.provider_configured), health.provider_configured ? `Ready · ${health.model || 'Groq model'}` : 'Add GROQ_API_KEY to .env');
    } catch (error) {
      setAiStatus(false, error.message || 'AI status unavailable');
      if (!aiAgentCatalog.length) {
        aiAgentCatalog = [
          { id: 'coordinator', name: 'AgriTwin Coordinator', description: 'Automatically delegates to relevant specialists.' },
          { id: 'harvest', name: 'Harvest Agent', description: 'Crop and harvest decisions.' },
          { id: 'climate', name: 'Climate Agent', description: 'Weather and forecast analysis.' },
          { id: 'market', name: 'Market Agent', description: 'Mandi prices and market decisions.' },
          { id: 'logistics', name: 'Logistics Agent', description: 'Route and shipment planning.' }
        ];
        renderAiAgentCatalog();
      }
    }
  }
  function renderAiAgentCatalog() {
    const host = $('#aiAgentList');
    if (!host) return;
    host.replaceChildren();
    (aiAgentCatalog.length ? aiAgentCatalog : []).forEach(agent => {
      const row = document.createElement('div'); row.className = 'ai-agent-row';
      const icon = document.createElement('span'); icon.className = 'ai-agent-icon'; icon.textContent = aiAgentGlyphs[agent.id] || '✳';
      const copy = document.createElement('span'); copy.className = 'ai-agent-copy';
      const name = document.createElement('strong'); name.textContent = agent.name;
      const desc = document.createElement('small'); desc.textContent = agent.description;
      copy.append(name, desc);
      const status = document.createElement('span'); status.className = 'ai-agent-state'; status.textContent = agent.id === 'coordinator' ? 'Auto' : 'Active';
      row.append(icon, copy, status); host.appendChild(row);
    });
    if (!host.children.length) host.textContent = 'Agent catalogue is unavailable.';
  }
  function renderAiPlannedAgents() {
    const host = $('#aiPlannedAgents');
    if (!host) return;
    host.replaceChildren();
    aiPlannedCatalog.forEach(agent => {
      const item = document.createElement('span');
      item.textContent = agent.name;
      item.title = agent.note || 'Not yet connected to the conversational runtime.';
      host.appendChild(item);
    });
  }
  function buildAiWelcome() {
    const role = roleAiContent();
    const welcome = document.createElement('div'); welcome.className = 'ai-welcome'; welcome.id = 'aiWelcome';
    const kicker = document.createElement('span'); kicker.className = 'ai-welcome-kicker'; kicker.textContent = 'YOUR SUPPLY-CHAIN DECISIONS, CONNECTED';
    const title = document.createElement('h2'); title.textContent = `What would you like to work through, ${state.user?.full_name?.split(' ')[0] || 'today'}?`;
    const subtitle = document.createElement('p'); subtitle.textContent = 'The Coordinator can involve relevant specialists, or choose one agent directly. Data freshness and estimates are explained in every result.';
    const grid = document.createElement('div'); grid.className = 'ai-prompt-grid';
    role.prompts.forEach(([glyph, heading, prompt, description]) => {
      const button = document.createElement('button'); button.type = 'button'; button.className = 'ai-prompt-card'; button.dataset.aiPrompt = prompt;
      const mark = document.createElement('span'); mark.textContent = glyph;
      const copy = document.createElement('span');
      const strong = document.createElement('strong'); strong.textContent = heading;
      const small = document.createElement('small'); small.textContent = description;
      copy.append(strong, small); button.append(mark, copy); grid.appendChild(button);
    });
    welcome.append(kicker, title, subtitle, grid);
    return welcome;
  }
  function aiResponseParts(content) {
    if (typeof content === 'string') return { text: content, mapUrl: '' };
    if (!content || typeof content !== 'object') return { text: String(content ?? ''), mapUrl: '' };
    if (content.type === 'route_map') {
      const lines = [content.message || 'Route details from your previous logistics request.'];
      if (content.origin || content.destination) lines.push(`${content.origin || 'Origin'} → ${content.destination || 'Destination'}`);
      if (content.distance_km != null) lines.push(`Distance: ${content.distance_km} km`);
      if (content.duration_minutes != null) lines.push(`Estimated duration: ${content.duration_minutes} minutes`);
      if (content.route_provider) lines.push(`Route source: ${content.route_provider}${content.traffic_aware ? ' · traffic-aware' : ' · not traffic-aware'}`);
      return { text: lines.join('\n'), mapUrl: content.maps_url || '' };
    }
    if (typeof content.final_answer === 'string') return { text: content.final_answer, mapUrl: '' };
    if (typeof content.message === 'string') return { text: content.message, mapUrl: '' };
    if (typeof content.answer === 'string') return { text: content.answer, mapUrl: '' };
    return { text: JSON.stringify(content, null, 2), mapUrl: '' };
  }
  function createAiMessage(message, options = {}) {
    const row = document.createElement('article');
    row.className = `ai-message ${message.role}${message.error ? ' error' : ''}`;
    const avatar = document.createElement('span'); avatar.className = 'ai-message-avatar'; avatar.textContent = message.role === 'user' ? initials(state.user?.full_name) : 'AT';
    const content = document.createElement('div'); content.className = 'ai-message-content';
    const meta = document.createElement('div'); meta.className = 'ai-message-meta'; meta.textContent = message.role === 'user' ? 'You' : (message.label || 'AgriTwin');
    const bubble = document.createElement('div'); bubble.className = 'ai-message-bubble';
    const parts = message.role === 'assistant' ? aiResponseParts(message.content) : { text: String(message.content || ''), mapUrl: '' };
    bubble.textContent = parts.text;
    if (parts.mapUrl) {
      try {
        const linkUrl = new URL(parts.mapUrl);
        if (linkUrl.protocol === 'https:' && linkUrl.hostname === 'www.google.com' && linkUrl.pathname.startsWith('/maps/dir/')) {
          const link = document.createElement('a'); link.className = 'ai-map-link'; link.href = linkUrl.href; link.target = '_blank'; link.rel = 'noopener noreferrer'; link.textContent = 'Open route in Google Maps ↗'; bubble.appendChild(link);
        }
      } catch (_) { /* Invalid provider link is omitted. */ }
    }
    content.append(meta, bubble);
    if (message.role === 'assistant' && Array.isArray(message.agents) && message.agents.length) {
      const tags = document.createElement('div'); tags.className = 'ai-message-tags';
      message.agents.forEach(name => { const tag = document.createElement('span'); tag.textContent = aiAgentLabels[name] || `${name} agent`; tags.appendChild(tag); });
      content.appendChild(tags);
    }
    row.append(avatar, content);
    return row;
  }
  function renderAiChat() {
    const host = $('#aiChatMessages');
    if (!host) return;
    host.replaceChildren();
    if (!aiMessages.length) host.appendChild(buildAiWelcome());
    else aiMessages.slice(-80).forEach(message => host.appendChild(createAiMessage(message)));
    host.scrollTop = host.scrollHeight;
  }
  function renderAiActivity(agents) {
    const host = $('#aiActivity');
    if (!host) return;
    host.replaceChildren();
    if (!Array.isArray(agents) || !agents.length) {
      host.className = 'ai-activity-empty';
      host.textContent = 'No specialist tool was needed for the latest turn. Ask a domain question to trigger agent activity.';
      return;
    }
    host.className = 'ai-activity-list';
    agents.forEach(name => {
      const row = document.createElement('div'); row.className = 'ai-activity-item';
      const icon = document.createElement('span'); icon.textContent = aiAgentGlyphs[name] || '✳';
      const copy = document.createElement('div');
      const title = document.createElement('strong'); title.textContent = aiAgentLabels[name] || `${name} agent`;
      const note = document.createElement('small'); note.textContent = 'Specialist analysis returned';
      copy.append(title, note);
      const check = document.createElement('span'); check.className = 'ai-activity-check'; check.textContent = '✓';
      row.append(icon, copy, check); host.appendChild(row);
    });
  }
  function appendAiHistory(message) {
    aiMessages.push(message);
    aiMessages = aiMessages.slice(-80);
    persistAiSession();
    renderAiChat();
  }
  function setAiBusy(busy) {
    aiSending = busy;
    const button = $('#aiSendButton'); const input = $('#aiMessageInput');
    if (button) button.disabled = busy;
    if (input) input.disabled = busy;
  }
  async function sendAiMessage(rawMessage) {
    const message = String(rawMessage || '').trim();
    if (!message || aiSending || !state.token) return;
    appendAiHistory({ role: 'user', content: message });
    setAiBusy(true);
    const host = $('#aiChatMessages');
    const typing = document.createElement('article'); typing.className = 'ai-message assistant'; typing.id = 'aiTyping';
    const avatar = document.createElement('span'); avatar.className = 'ai-message-avatar'; avatar.textContent = 'AT';
    const copy = document.createElement('div'); copy.className = 'ai-message-content';
    const meta = document.createElement('div'); meta.className = 'ai-message-meta'; meta.textContent = 'AgriTwin is coordinating';
    const bubble = document.createElement('div'); bubble.className = 'ai-message-bubble';
    const dots = document.createElement('span'); dots.className = 'ai-typing-dots';
    for (let index = 0; index < 3; index += 1) dots.appendChild(document.createElement('i'));
    bubble.appendChild(dots); copy.append(meta, bubble); typing.append(avatar, copy); host.appendChild(typing); host.scrollTop = host.scrollHeight;
    try {
      const result = await api('/ai/chat', {
        method: 'POST',
        body: JSON.stringify({ message, session_id: aiSessionId, agent: $('#aiAgentSelect')?.value || 'coordinator' })
      });
      aiSessionId = result.session_id || aiSessionId;
      persistAiSession();
      appendAiHistory({ role: 'assistant', content: result.response, label: result.agent_label, agents: result.agents_used || [] });
      renderAiActivity(result.agents_used || []);
      setAiStatus(true, 'Ready · response received');
    } catch (error) {
      appendAiHistory({ role: 'assistant', content: error.message || 'AgriTwin could not complete this request.', label: 'Connection notice', error: true });
      setAiStatus(false, (error.message || '').slice(0, 72));
      if ((error.message || '').toLowerCase().includes('groq_api_key')) toast('Add a new GROQ_API_KEY to .env and restart AgriTwin.', true);
    } finally {
      $('#aiTyping')?.remove();
      setAiBusy(false);
      if ($('#aiMessageInput')) $('#aiMessageInput').focus();
    }
  }
  function startNewAiConversation() {
    if (aiSending) return;
    aiSessionId = createAiSessionId();
    aiMessages = [];
    persistAiSession();
    renderAiChat();
    renderAiActivity([]);
    toast('Started a new AI conversation.');
    $('#aiMessageInput')?.focus();
  }

  async function loadRoleWorkspace() {
    const host = $('#roleWorkspace');
    if (!host || !state.token) return;
    host.innerHTML = '<div class="loading-line">Preparing your role-specific tools…</div>';
    try {
      state.roleWorkspace = await api('/workspace/role-dashboard');
      renderRoleWorkspace(state.roleWorkspace);
    } catch (error) {
      host.innerHTML = `<div class="empty-state"><strong>Your role workspace could not load.</strong>${esc(error.message)}</div>`;
    }
  }

  function roleMetric(label, value, hint, icon = '✳') {
    return `<article class="role-metric"><span>${icon}</span><div><small>${esc(label)}</small><strong>${esc(value ?? '—')}</strong><em>${esc(hint || '')}</em></div></article>`;
  }

  function roleSectionTitle(kicker, title, description = '') {
    return `<div class="role-section-title"><div><span class="section-kicker">${esc(kicker)}</span><h3>${esc(title)}</h3>${description ? `<p>${esc(description)}</p>` : ''}</div></div>`;
  }

  function renderRoleWorkspace(workspace) {
    const host = $('#roleWorkspace');
    if (!host || !workspace) return;
    const data = workspace.data || {};
    const aliases = { transporter: 'driver', storage_provider: 'storage_owner', buyer: 'mandi_seller', fpo: 'fpo_manager' };
    const role = aliases[workspace.role || state.role] || workspace.role || state.role;
    const intro = {
      farmer: ['FARMER FIELD DESK', 'Your farm, season and selling decisions', 'Field records, timely alerts and practical next-step recommendations.'],
      driver: ['DRIVER DISPATCH DESK', 'Find loads. Plan the road. Keep capacity moving.', 'Nearby farmer demand, open transport orders and a road route planner in one workspace.'],
      storage_owner: ['WAREHOUSE OPERATIONS', 'Manage capacity from intake to dispatch', 'Track recorded stock movements and discover farmers currently seeking storage.'],
      mandi_seller: ['TRADER SOURCING DESK', 'Source better lots and manage buying plans', 'Discover crop supply, record buying activity and check market signals before negotiating.'],
      mandi_owner: ['MANDI OPERATIONS', 'Coordinate arrivals and market services', 'See potential incoming loads and record arrival, weighment and auction schedules.'],
      fpo_manager: ['FPO AGGREGATION DESK', 'Bring member supply together', 'Track connected farmers, identify available lots and coordinate aggregation and bulk dispatch.'],
    }[role] || ['STAKEHOLDER WORKSPACE', 'Your role-specific operations', 'Tools for your work across the AgriTwin network.'];
    let body = '';
    if (role === 'farmer') body = renderFarmerDesk(data);
    else if (role === 'driver') body = renderDriverDesk(data);
    else if (role === 'storage_owner') body = renderStorageDesk(data);
    else if (role === 'mandi_seller') body = renderTraderDesk(data);
    else if (role === 'mandi_owner') body = renderMandiDesk(data);
    else if (role === 'fpo_manager') body = renderFpoDesk(data);
    else body = '<div class="empty-state">Choose a supported stakeholder role in your account to unlock the matching operations desk.</div>';
    host.innerHTML = `<div class="role-workspace-heading"><div><span class="section-kicker">${intro[0]}</span><h2>${intro[1]}</h2><p>${intro[2]}</p></div><span class="role-workspace-pill">${esc(workspace.role_label || roleLabel())}</span></div>${body}`;
    if (role === 'driver') initDriverMap(data);
  }

  function renderAlertList(alerts = []) {
    if (!alerts.length) return '<div class="empty-state compact-empty">No alerts right now. Keep your records updated to receive useful reminders.</div>';
    return alerts.map(alert => `<article class="role-alert ${esc(alert.level || 'info')}"><span class="alert-icon">${alert.level === 'attention' ? '⚠' : alert.level === 'success' ? '✓' : 'ⓘ'}</span><div><strong>${esc(alert.title)}</strong><p>${esc(alert.message)}</p></div></article>`).join('');
  }

  function renderRoleListingCards(items = [], emptyText = 'No matching opportunities are available yet.') {
    if (!items.length) return `<div class="empty-state compact-empty">${esc(emptyText)}</div>`;
    return items.slice(0, 8).map(item => `<article class="role-opportunity"><div class="role-opportunity-top"><span class="category-pill">${esc(categoryLabels[item.category] || item.category || 'Opportunity')}</span>${item.fit_score ? `<span class="score-pill">${item.fit_score}% fit</span>` : ''}</div><strong>${esc(item.title)}</strong><p>${esc(item.owner_name || 'Network stakeholder')} · ${esc(item.district || item.location || 'Location not listed')}</p><div class="role-opportunity-facts">${item.commodity ? `<span>🌾 ${esc(item.commodity)}</span>` : ''}${item.quantity_tonnes ? `<span>${esc(item.quantity_tonnes)} tonnes</span>` : ''}${item.capacity_tonnes ? `<span>${esc(item.capacity_tonnes)} t capacity</span>` : ''}${item.destination ? `<span>→ ${esc(item.destination)}</span>` : ''}</div><button class="btn btn-soft btn-small" data-connect-listing="${esc(item.id)}">Connect with stakeholder ↗</button></article>`).join('');
  }

  function renderPlotCards(plots = []) {
    if (!plots.length) return '<div class="empty-state compact-empty"><strong>No farm plots added yet.</strong>Add a crop record to receive season reminders and local weather alerts.</div>';
    return plots.map(plot => `<article class="plot-row"><div class="plot-crop-icon">🌱</div><div class="plot-row-main"><strong>${esc(plot.name)} · ${esc(plot.crop)}</strong><small>${plot.area_acres ? `${esc(plot.area_acres)} acres` : 'Area not provided'} · ${esc((plot.crop_stage || 'unknown').replaceAll('_', ' '))}${plot.sowing_date ? ` · Sown ${esc(plot.sowing_date)}` : ''}</small><div class="plot-row-actions"><select aria-label="Update crop stage" data-plot-stage="${esc(plot.id)}"><option value="${esc(plot.crop_stage)}" selected>${esc((plot.crop_stage || 'unknown').replaceAll('_', ' '))}</option>${['sowing','vegetative','flowering','grain_filling','maturity','ready','harvested','unknown'].filter(stage => stage !== plot.crop_stage).map(stage => `<option value="${stage}">${stage.replaceAll('_', ' ')}</option>`).join('')}</select><button class="text-button danger-text" data-delete-plot="${esc(plot.id)}">Remove</button></div></div></article>`).join('');
  }

  function renderHarvestWindows(items = []) {
    if (!items.length) return '<div class="empty-state compact-empty">Add a supported crop and sowing date to see an indicative harvest window.</div>';
    return `<div class="harvest-calendar">${items.slice(0, 8).map(item => {
      const status = item.status === 'window_open' ? 'Window open for field checks' : item.status === 'window_passed' ? 'Reference window passed' : item.status === 'harvested' ? 'Marked harvested' : `About ${Math.max(0, item.days_until_window)} days until reference window`;
      return `<article class="harvest-calendar-card ${esc(item.status)}"><div><strong>${esc(item.plot_name)} · ${esc(item.crop)}</strong><span>${esc(status)}</span></div><b>${esc(item.window_start)} – ${esc(item.window_end)}</b><small>${esc(item.reference_cycle_days[0])}–${esc(item.reference_cycle_days[1])} day reference cycle after sowing</small></article>`;
    }).join('')}</div><p class="role-footnote">These windows are broad crop-cycle references only. Weather, seed variety, planting method, soil and field checks can shift actual maturity.</p>`;
  }

  function renderWeatherForecast(weather) {
    const days = weather?.data?.forecast || [];
    if (!days.length) return '';
    return `<div class="weather-forecast-grid">${days.map(day => `<article class="weather-day"><strong>${esc(day.date)}</strong><b>${day.max_temp_c ?? '—'}° / ${day.min_temp_c ?? '—'}°C</b><span>Rain chance: ${day.rain_probability_pct ?? '—'}%</span><span>Rain: ${day.rain_mm ?? '—'} mm</span><span>Wind: ${day.max_wind_kmh ?? '—'} km/h</span></article>`).join('')}</div>`;
  }

  function renderFarmerDesk(data) {
    const weather = data.weather;
    const current = weather?.data?.current;
    const weatherLine = current ? `${current.temperature_c ?? '—'}°C · Humidity ${current.humidity_pct ?? '—'}% · Wind ${current.wind_kmh ?? '—'} km/h` : (weather?.summary || 'Add coordinates to a farm plot for a location-specific forecast.');
    return `<div class="role-metrics-grid">${roleMetric('Farm plots', data.plots?.length || 0, 'Tracked crop records', '🌾')}${roleMetric('Cultivated area', `${data.total_area_acres || 0} ac`, 'Across recorded plots', '▧')}${roleMetric('Active crop cycles', data.active_crop_count || 0, 'Not marked harvested', '🌱')}${roleMetric('Action alerts', data.harvest_alerts?.length || 0, 'Season and weather checks', '⚑')}</div>
      <div class="role-two-column">
        <section class="panel role-panel"><div class="panel-heading">${roleSectionTitle('FIELD REGISTER', 'My farm plots', 'Record the crop and stage so AgriTwin can personalize reminders.')}</div>
          <form id="farmPlotForm" class="role-form"><div class="role-form-grid"><label class="form-field"><span>Plot / field name</span><input name="name" required minlength="2" placeholder="North field"/></label><label class="form-field"><span>Crop</span><input name="crop" required placeholder="Onion"/></label><label class="form-field"><span>Variety (optional)</span><input name="variety" placeholder="Red onion / local variety"/></label><label class="form-field"><span>Sowing date</span><input name="sowing_date" type="date"/></label><label class="form-field"><span>Area (acres)</span><input name="area_acres" type="number" min="0.1" step="0.1" placeholder="2.5"/></label><label class="form-field"><span>Current crop stage</span><select name="crop_stage"><option value="unknown">Not sure</option><option value="sowing">Sowing</option><option value="vegetative">Vegetative</option><option value="flowering">Flowering</option><option value="grain_filling">Bulb / grain development</option><option value="maturity">Maturity</option><option value="ready">Potentially ready</option><option value="harvested">Harvested</option></select></label><label class="form-field"><span>Irrigation</span><select name="irrigation_type"><option value="">Not specified</option><option>Drip</option><option>Sprinkler</option><option>Flood / furrow</option><option>Rain-fed</option></select></label><label class="form-field"><span>Soil type (optional)</span><input name="soil_type" placeholder="Black soil, loamy…"/></label><label class="form-field"><span>Latitude (for local weather)</span><input name="latitude" type="number" step="any" placeholder="19.9975"/></label><label class="form-field"><span>Longitude</span><input name="longitude" type="number" step="any" placeholder="73.7898"/></label></div><label class="form-field"><span>Field notes</span><input name="notes" maxlength="1200" placeholder="Variety, soil, observations…"/></label><div class="role-form-actions"><button class="btn btn-primary" type="submit">＋ Save farm plot</button><span class="form-feedback" id="farmPlotFeedback" role="status"></span></div></form>
          <div class="role-list-heading"><strong>Recorded fields</strong><span>${data.plots?.length || 0} plots</span></div><div class="plot-list">${renderPlotCards(data.plots || [])}</div>
        </section>
        <section class="panel role-panel"><div class="panel-heading">${roleSectionTitle('DECISION SUPPORT', 'Harvest & weather alerts', 'Use these as prompts for field inspection, not automatic harvest orders.')}</div><div class="role-alert-list">${renderAlertList(data.harvest_alerts || [])}</div><div class="weather-summary"><span class="weather-symbol">☼</span><div><strong>Local weather</strong><p>${esc(weatherLine)}</p><small>${esc(weather?.source || 'Open-Meteo forecast API')} · ${weather?.live ? 'Live provider response' : 'Not live / needs farm coordinates'}</small></div></div>${renderWeatherForecast(weather)}<div class="role-panel-actions"><button class="btn btn-soft" data-page="agents">Open AI assistant ↗</button><button class="text-button" data-page="marketplace">Open marketplace →</button></div></section>
      </div>
      <section class="panel role-panel"><div class="panel-heading">${roleSectionTitle('CROP CALENDAR', 'Indicative harvest windows', 'Sowing-date based reminders help you plan inspections, labour, transport and storage.')}</div>${renderHarvestWindows(data.harvest_windows || [])}</section>
      <div class="role-two-column"><section class="panel role-panel">${roleSectionTitle('FIELD JOURNAL', 'Log farm activities', 'Keep a simple record of field work, inputs, inspections and planned harvest dates.')}${roleOperationForm('field_activity', { title: 'Activity / field note', placeholder: 'Irrigation, fertilizer, crop inspection…', date: 'Activity date', operationTypes: [['field_activity','Field activity'],['harvest_plan','Harvest plan']] })}<div class="role-list-heading"><strong>Recent field records</strong><span>Private to your account</span></div><div class="operation-list">${renderOperationRows((state.roleWorkspace?.operations || []).filter(item => ['field_activity','harvest_plan'].includes(item.operation_type)))}</div></section>
      <section class="panel role-panel"><div class="panel-heading">${roleSectionTitle('NEXT BEST ACTIONS', 'Recommendations for your farm', 'Ranked using crop fit, district fit and supply-chain usefulness. Availability can change.')}</div><div class="role-opportunity-grid">${renderRoleListingCards(data.recommendations || [], 'No role-matched listings yet. Add crops to your profile and check again after new partners publish.')}</div><div class="farmer-next-steps">${(data.next_steps || []).map((step, index) => `<div><span>${index + 1}</span><p>${esc(step)}</p></div>`).join('')}</div></section></div><p class="role-footnote">Harvest windows are broad crop-cycle references and are not a substitute for local agronomist advice, field maturity checks or moisture testing. Market and weather alerts depend on provider availability.</p>`;
  }

  function renderDriverDesk(data) {
    const orders = data.open_orders || [];
    const first = orders[0];
    const driverBase = state.dashboard?.profile?.address || [state.dashboard?.profile?.village, state.dashboard?.profile?.district, state.dashboard?.profile?.state].filter(Boolean).join(', ');
    const origin = first?.pickup_location || first?.location || driverBase;
    const destination = first?.destination || '';
    return `<div class="role-metrics-grid">${roleMetric('Nearby farmers', data.nearby_farmers ?? 0, data.location_setup_needed ? 'Add district or coordinates to calculate' : `Within ${data.service_radius_km || 100} km / same district`, '👨‍🌾')}${roleMetric('Open transport orders', data.available_orders ?? 0, data.location_setup_needed ? 'Add your service location to filter nearby orders' : data.opportunity_scope === 'network_wide_until_location_added' ? 'Across the network until you add a location' : 'Farmer requirements near your service area', '📦')}${roleMetric('Vehicle capacity', data.vehicle_capacity_tonnes ? `${data.vehicle_capacity_tonnes} t` : 'Not set', data.vehicle_type || 'Update your profile', '🚚')}${roleMetric('Suggested service radius', `${data.service_radius_km || 100} km`, 'Set in your profile', '⌖')}</div>
      <section class="panel role-panel driver-route-panel"><div class="panel-heading">${roleSectionTitle('ROUTE OPTIMIZER', 'Your dispatch map', 'Enter pickup and drop-off points to calculate a road route and compare route alternatives.')}</div><form id="driverRouteForm" class="route-planner-form"><label class="form-field"><span>Source / pickup</span><input name="origin" required value="${esc(origin || '')}" placeholder="Farm, village, town or address"/></label><label class="form-field"><span>Destination / drop-off</span><input name="destination" required value="${esc(destination)}" placeholder="Storage, mandi or buyer location"/></label><button class="btn btn-primary" type="submit" id="optimizeRouteButton">Optimize route ↗</button></form><div id="driverRouteFeedback" class="route-feedback">${esc(data.route_note || '')}</div><div class="driver-map-layout"><div id="driverMap" class="driver-map" role="img" aria-label="Driver route map"></div><aside class="route-side"><div id="driverRouteSummary" class="route-summary"><strong>Route not planned yet</strong><p>Enter a source and destination. The map will show the fastest returned road route from OSRM.</p></div><a id="openExternalRoute" class="btn btn-soft" href="https://www.openstreetmap.org" target="_blank" rel="noreferrer">Open map ↗</a><small>Map data © OpenStreetMap contributors. Routing via OSRM public demo service. No live traffic feed.</small></aside></div></section>
      <section class="panel role-panel"><div class="panel-heading">${roleSectionTitle('LOAD OPPORTUNITIES', 'Transport demand near you', 'Open farmer requests. Check vehicle capacity, plan the pickup-to-drop route and connect to agree freight and timing.')}</div><div class="role-opportunity-grid">${orders.length ? renderDriverOrderCards(orders) : '<div class="empty-state compact-empty">No transport request is currently matched to this radius. Expand your service radius or update your district and coordinates in My profile.</div>'}</div></section>
      <section class="panel role-panel">${roleSectionTitle('TRIP REGISTER', 'Record a booked or completed trip', 'Keep dispatch history and delivered tonnage in your own workspace.')}${roleOperationForm('driver_trip', { title: 'Trip / load reference', placeholder: 'Onion load · Sinnar to Lasalgaon', date: 'Dispatch date' })}<div class="operation-list">${renderOperationRows((state.roleWorkspace?.operations || []).filter(item => ['driver_trip','vehicle_service','delivery_issue'].includes(item.operation_type)))}</div></section>`;
  }

  function renderDriverOrderCards(items = []) {
    return items.slice(0, 12).map(item => {
      const source = item.pickup_location || item.location || item.district || '';
      const destination = item.destination || '';
      const capacityText = item.capacity_fit === true ? 'Fits listed vehicle capacity' : item.capacity_fit === false ? 'Exceeds listed vehicle capacity' : 'Vehicle capacity not yet checked';
      return `<article class="role-opportunity"><div class="role-opportunity-top"><span class="category-pill">Transport needed</span><span class="score-pill">${item.approx_distance_km !== null && item.approx_distance_km !== undefined ? `${esc(item.approx_distance_km)} km away` : esc(item.distance_basis?.replaceAll('_', ' ') || 'Location estimate')}</span></div><strong>${esc(item.title)}</strong><p>${esc(item.owner_name || 'Farmer / FPO')} · ${esc(item.district || item.location || 'Location not listed')}</p><div class="role-opportunity-facts">${item.commodity ? `<span>🌾 ${esc(item.commodity)}</span>` : ''}${item.quantity_tonnes ? `<span>${esc(item.quantity_tonnes)} tonnes needed</span>` : ''}${destination ? `<span>→ ${esc(destination)}</span>` : ''}</div><small class="capacity-fit-note ${item.capacity_fit === false ? 'is-warning' : ''}">${esc(capacityText)}</small><div class="driver-order-actions"><button class="btn btn-soft btn-small" data-connect-listing="${esc(item.id)}">Connect with farmer ↗</button><button class="btn btn-primary btn-small" data-plan-driver-route="${esc(item.id)}" data-route-origin="${esc(source)}" data-route-destination="${esc(destination)}" ${!source || !destination ? 'disabled title="This listing needs a pickup and destination"' : ''}>Plan this load ↗</button></div></article>`;
    }).join('');
  }

  function renderOperationRows(items = []) {
    if (!items.length) return '<div class="empty-state compact-empty">No operational records yet. Add the first record above.</div>';
    return items.slice(0, 12).map(item => {
      const isMandiFlow = ['mandi_arrival', 'auction_slot'].includes(item.operation_type);
      const steps = isMandiFlow ? ['planned', 'arrived', 'weighed', 'auctioned', 'dispatched', 'completed', 'cancelled'] : ['planned', 'pending', 'in_progress', 'dispatched', 'completed', 'cancelled'];
      if (!steps.includes(item.status)) steps.unshift(item.status);
      return `<article class="operation-row"><div><strong>${esc(item.title)}</strong><small>${esc(item.operation_type.replaceAll('_', ' '))}${item.commodity ? ` · ${esc(item.commodity)}` : ''}${item.quantity_tonnes ? ` · ${esc(item.quantity_tonnes)} t` : ''}${item.scheduled_at ? ` · ${esc(item.scheduled_at)}` : ''}</small>${item.notes ? `<p>${esc(item.notes)}</p>` : ''}</div><div class="operation-status"><span class="status-pill ${esc(item.status)}">${esc(item.status.replaceAll('_', ' '))}</span><select aria-label="Update operation status" data-operation-status-change="${esc(item.id)}">${steps.map(step => `<option value="${step}" ${step === item.status ? 'selected' : ''}>${step.replaceAll('_', ' ')}</option>`).join('')}</select></div></article>`;
    }).join('');
  }

  function roleOperationForm(type, labels = {}) {
    const operationSelector = labels.operationTypes
      ? `<label class="form-field"><span>Activity type</span><select name="operation_type">${labels.operationTypes.map(([value, label]) => `<option value="${esc(value)}">${esc(label)}</option>`).join('')}</select></label>`
      : `<input type="hidden" name="operation_type" value="${esc(type)}"/>`;
    return `<form class="role-form role-operation-form" id="roleOperationForm">${operationSelector}<div class="role-form-grid"><label class="form-field"><span>${esc(labels.title || 'Record title')}</span><input name="title" required minlength="3" placeholder="${esc(labels.placeholder || 'Enter a clear activity name')}"/></label><label class="form-field"><span>Crop / commodity</span><input name="commodity" placeholder="Onion, tomato…"/></label><label class="form-field"><span>Quantity (tonnes)</span><input name="quantity_tonnes" type="number" min="0.1" step="0.1" placeholder="Optional"/></label><label class="form-field"><span>${esc(labels.date || 'Planned date')}</span><input name="scheduled_at" type="date"/></label><label class="form-field"><span>From / source</span><input name="origin" placeholder="Optional"/></label><label class="form-field"><span>To / destination</span><input name="destination" placeholder="Optional"/></label></div><label class="form-field"><span>Notes</span><textarea name="notes" rows="2" placeholder="Reference, terms, grade, contact context…"></textarea></label><div class="role-form-actions"><button class="btn btn-primary" type="submit">Save operation</button><span class="form-feedback" id="operationFeedback" role="status"></span></div></form>`;
  }

  function renderStorageDesk(data) {
    const pct = data.capacity_tonnes ? Math.min(100, Math.round((data.occupied_tonnes / data.capacity_tonnes) * 100)) : 0;
    return `<div class="role-metrics-grid">${roleMetric('Total capacity', data.capacity_tonnes ? `${data.capacity_tonnes} t` : 'Not set', data.storage_type || 'Add storage type in profile', '🏬')}${roleMetric('Recorded occupancy', `${data.occupied_tonnes || 0} t`, 'Intake minus dispatch records', '📦')}${roleMetric('Available capacity', data.available_capacity_tonnes !== null ? `${data.available_capacity_tonnes} t` : 'Add capacity', 'Calculated from recorded movement', '✓')}${roleMetric('Storage requests', data.storage_requests?.length || 0, 'Farmers seeking storage', '🌾')}</div>
      <section class="panel role-panel"><div class="capacity-track"><div><strong>Capacity utilization</strong><span>${data.capacity_tonnes ? `${pct}% of listed capacity` : 'Capacity not configured'}</span></div><div class="progress-track"><i style="width:${pct}%"></i></div><small>${esc(data.capacity_note || '')}</small></div></section>
      <div class="role-two-column"><section class="panel role-panel">${roleSectionTitle('INVENTORY CONTROL', 'Record stock movement', 'Record every intake and dispatch to keep occupancy estimates useful.')}
        <form id="roleOperationForm" class="role-form"><input type="hidden" name="status" value="completed"/><label class="form-field"><span>Movement type</span><select name="operation_type"><option value="storage_intake">Stock intake</option><option value="storage_dispatch">Stock dispatch</option><option value="storage_inspection">Storage inspection</option></select></label><div class="role-form-grid"><label class="form-field"><span>Record title</span><input name="title" required placeholder="Onion lot received"/></label><label class="form-field"><span>Commodity</span><input name="commodity" placeholder="Onion"/></label><label class="form-field"><span>Quantity (tonnes)</span><input name="quantity_tonnes" type="number" min="0.1" step="0.1" required/></label></div><label class="form-field"><span>Notes / lot reference</span><textarea name="notes" rows="2"></textarea></label><div class="role-form-actions"><button class="btn btn-primary" type="submit">Save stock movement</button><span class="form-feedback" id="operationFeedback"></span></div></form></section>
        <section class="panel role-panel">${roleSectionTitle('INBOUND DEMAND', 'Farmers seeking storage', 'Open requests from the marketplace in your district.') }<div class="role-opportunity-list">${renderRoleListingCards(data.storage_requests || [], 'No nearby storage requests found.')}</div></section></div>
      <section class="panel role-panel">${roleSectionTitle('WAREHOUSE LOG', 'Recent inventory records')}<div class="operation-list">${renderOperationRows(data.inventory_records || [])}</div></section>`;
  }

  function renderTraderDesk(data) {
    const commodities = data.focus_commodities?.length ? data.focus_commodities.join(', ') : 'Add commodities in your profile';
    return `<div class="role-metrics-grid">${roleMetric('Available crop lots', data.available_supply?.length || 0, 'Active farmer / FPO produce listings', '🌾')}${roleMetric('Active buying plans', data.active_buy_plans || 0, 'Your open sourcing activities', '🧾')}${roleMetric('Focus commodities', data.focus_commodities?.length || 0, commodities, '◈')}${roleMetric('Connected partners', state.dashboard?.metrics?.active_connections || 0, 'Farmers, FPOs and service providers', '◎')}</div>
      <div class="role-two-column"><section class="panel role-panel">${roleSectionTitle('SOURCING BOARD', 'Produce available to buy', 'Compare crop, quantity, location and price notes before opening a deal.') }<div class="role-opportunity-list">${renderRoleListingCards(data.available_supply || [], 'No crop lots match your filters. Add commodities and district to your profile.')}</div></section>
      <section class="panel role-panel">${roleSectionTitle('BUYING & QUALITY', 'Create a purchase plan', 'Log the lot you intend to source and track inspection and negotiation.')}${roleOperationForm('purchase_order', { title: 'Activity title', placeholder: 'Buy 20 tonnes of graded onion', date: 'Target date', operationTypes: [['purchase_order','Purchase plan'],['trade_offer','Trade offer'],['quality_check','Quality inspection']] })}<div class="trade-guidance">${(data.trade_guidance || []).map(line => `<p>✓ ${esc(line)}</p>`).join('')}<button class="btn btn-soft" data-page="agents">Check mandi prices with Market Agent ↗</button></div></section></div>
      <section class="panel role-panel">${roleSectionTitle('TRADE LOG', 'Buying activity')}<div class="operation-list">${renderOperationRows(data.trade_records || [])}</div></section>`;
  }

  function renderMandiDesk(data) {
    return `<div class="role-metrics-grid">${roleMetric('Potential inbound listings', data.expected_arrivals?.length || 0, 'Local / destination-matched crop movement', '🚚')}${roleMetric('Scheduled arrivals', data.scheduled_arrivals || 0, 'Your recorded gate bookings', '🗓')}${roleMetric('Mandi / APMC', data.mandi_name || 'Not configured', 'Set mandi name in profile', '🏪')}${roleMetric('Market partners', state.dashboard?.metrics?.active_connections || 0, 'Accepted network connections', '◎')}</div>
      <div class="role-two-column"><section class="panel role-panel">${roleSectionTitle('ARRIVAL FORECAST BOARD', 'Potential incoming produce', 'This board finds matching listings; only a confirmed appointment is a scheduled arrival.') }<div class="role-opportunity-list">${renderRoleListingCards(data.expected_arrivals || [], 'No nearby inbound listings found. Set your district and mandi name in your profile.')}</div><p class="role-footnote">${esc(data.arrival_note || '')}</p></section>
      <section class="panel role-panel">${roleSectionTitle('GATE & AUCTION DESK', 'Schedule an arrival or slot', 'Record an expected gate arrival, weighment slot or auction service.')}
        <form id="roleOperationForm" class="role-form"><label class="form-field"><span>Operation</span><select name="operation_type"><option value="mandi_arrival">Gate arrival</option><option value="auction_slot">Auction slot</option><option value="market_service">Mandi service booking</option></select></label><div class="role-form-grid"><label class="form-field"><span>Booking title</span><input name="title" required placeholder="Onion load · vehicle arrival"/></label><label class="form-field"><span>Commodity</span><input name="commodity" placeholder="Onion"/></label><label class="form-field"><span>Quantity (tonnes)</span><input name="quantity_tonnes" type="number" min="0.1" step="0.1"/></label><label class="form-field"><span>Expected date</span><input name="scheduled_at" type="date"/></label><label class="form-field"><span>Origin</span><input name="origin" placeholder="Farm / storage"/></label><label class="form-field"><span>Destination / gate</span><input name="destination" placeholder="Gate / yard"/></label></div><label class="form-field"><span>Notes</span><textarea name="notes" rows="2" placeholder="Farmer, vehicle, lot or booking reference"></textarea></label><div class="role-form-actions"><button class="btn btn-primary" type="submit">Save schedule</button><span class="form-feedback" id="operationFeedback"></span></div></form></section></div>
      <section class="panel role-panel">${roleSectionTitle('MARKET OPERATIONS', 'Your schedules & services')}<div class="operation-list">${renderOperationRows(data.market_operations || [])}</div></section>`;
  }

  function renderFpoDesk(data) {
    return `<div class="role-metrics-grid">${roleMetric('Connected farmers', data.connected_farmers || 0, 'Accepted farmer connections', '👨‍🌾')}${roleMetric('Local farmer profiles', data.local_farmers_in_district || 0, 'Same district, not all verified members', '🌱')}${roleMetric('Connected supply', `${data.connected_supply_tonnes || 0} t`, 'Produce listings from connected farmers', '📦')}${roleMetric('Aggregation records', data.aggregation_records?.length || 0, 'Your batches and dispatch plans', '▤')}</div>
      <div class="role-two-column"><section class="panel role-panel">${roleSectionTitle('MEMBER SUPPLY BOARD', 'Connected farmer produce', 'Only produce listings from your accepted farmer connections are included.') }<div class="role-opportunity-list">${renderRoleListingCards(data.member_supply || [], 'Connect with farmers first. Their active crop listings will appear here.')}</div><div class="role-list-heading"><strong>Member crop watchlist</strong><span>Shared agronomic summary, no plot coordinates</span></div>${renderMemberCropWatchlist(data.member_crop_watchlist || [])}</section>
      <section class="panel role-panel">${roleSectionTitle('BULK COORDINATION', 'Create aggregation batch', 'Group member produce by commodity, quantity and dispatch plan.')}${roleOperationForm('aggregation_batch', { title: 'Activity / batch name', placeholder: 'Nashik onion aggregation · week 48', date: 'Planned date', operationTypes: [['aggregation_batch','Aggregation batch'],['member_meeting','Member meeting'],['bulk_dispatch','Bulk dispatch']] })}<div class="trade-guidance">${(data.fpo_guidance || []).map(line => `<p>✓ ${esc(line)}</p>`).join('')}</div><button class="btn btn-soft" data-page="network">Find more farmer members ↗</button></section></div>
      <section class="panel role-panel">${roleSectionTitle('AGGREGATION & DISPATCH LOG', 'FPO operations')}<div class="operation-list">${renderOperationRows(data.aggregation_records || [])}</div></section>`;
  }

  function renderMemberCropWatchlist(items = []) {
    if (!items.length) return '<div class="empty-state compact-empty">No crop plots are shared by accepted farmer connections yet. Members can add farm plots to help coordinate upcoming supply.</div>';
    return `<div class="member-crop-watchlist">${items.slice(0, 16).map(item => `<article><div><strong>${esc(item.farmer_name)} · ${esc(item.plot_name)}</strong><span>${esc(item.crop)} · ${esc((item.crop_stage || 'unknown').replaceAll('_', ' '))}${item.area_acres ? ` · ${esc(item.area_acres)} acres` : ''}</span></div><small>${item.expected_harvest_start && item.expected_harvest_end ? `Reference harvest window: ${esc(item.expected_harvest_start)} to ${esc(item.expected_harvest_end)}` : 'Add sowing date for a reference crop calendar'}</small></article>`).join('')}</div><p class="role-footnote">Crop stages and broad crop-cycle dates are planning hints, not guaranteed supply or harvest commitments. Farmer plot coordinates are not shared.</p>`;
  }

  async function submitFarmPlot(event) {
    event.preventDefault();
    const form = event.currentTarget;
    const data = Object.fromEntries(new FormData(form).entries());
    ['area_acres','latitude','longitude'].forEach(key => data[key] = data[key] === '' ? null : Number(data[key]));
    ['variety','sowing_date','irrigation_type','soil_type','notes'].forEach(key => { if (!data[key]) data[key] = null; });
    const feedback = $('#farmPlotFeedback');
    try {
      await api('/workspace/farm-plots', { method: 'POST', body: JSON.stringify(data) });
      toast('Farm plot saved.'); form.reset(); await loadRoleWorkspace();
    } catch (error) { feedback.textContent = error.message; }
  }

  async function submitRoleOperation(event) {
    event.preventDefault();
    const form = event.currentTarget;
    const data = Object.fromEntries(new FormData(form).entries());
    ['quantity_tonnes'].forEach(key => data[key] = data[key] === '' ? null : Number(data[key]));
    ['commodity','origin','destination','scheduled_at','notes'].forEach(key => { if (!data[key]) data[key] = null; });
    const feedback = form.querySelector('[id="operationFeedback"]');
    const button = form.querySelector('button[type="submit"]'); setBusy(button, true, 'Saving…');
    try {
      await api('/workspace/operations', { method: 'POST', body: JSON.stringify(data) });
      toast('Operation saved.'); form.reset(); await loadRoleWorkspace();
    } catch (error) { if (feedback) feedback.textContent = error.message; }
    finally { setBusy(button, false); }
  }

  async function updateOperationStatus(id, status) {
    try { await api(`/workspace/operations/${id}`, { method: 'PATCH', body: JSON.stringify({ status }) }); toast('Operation updated.'); await loadRoleWorkspace(); }
    catch (error) { toast(error.message, true); }
  }

  async function updatePlotStage(id, stage) {
    try { await api(`/workspace/farm-plots/${id}`, { method: 'PATCH', body: JSON.stringify({ crop_stage: stage }) }); toast('Crop stage updated.'); await loadRoleWorkspace(); }
    catch (error) { toast(error.message, true); }
  }

  async function deleteFarmPlot(id) {
    if (!confirm('Remove this farm plot record?')) return;
    try { await api(`/workspace/farm-plots/${id}`, { method: 'DELETE' }); toast('Farm plot removed.'); await loadRoleWorkspace(); }
    catch (error) { toast(error.message, true); }
  }

  function initDriverMap(data = {}) {
    const mapHost = $('#driverMap');
    if (!mapHost) return;
    if (!window.L) { mapHost.innerHTML = '<div class="map-fallback">Map library unavailable. You can still use the route planner and open the route externally.</div>'; return; }
    const p = state.dashboard?.profile || {};
    const lat = Number(p.latitude), lon = Number(p.longitude);
    const hasCoords = Number.isFinite(lat) && Number.isFinite(lon) && p.latitude !== null && p.longitude !== null;
    if (driverMap) { driverMap.remove(); driverMap = null; driverRouteLayer = null; driverMarkersLayer = null; }
    driverMap = L.map(mapHost, { scrollWheelZoom: true }).setView(hasCoords ? [lat, lon] : [20.5937, 78.9629], hasCoords ? 10 : 5);
    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', { maxZoom: 19, attribution: '&copy; <a href="https://www.openstreetmap.org/copyright" target="_blank" rel="noreferrer">OpenStreetMap</a>' }).addTo(driverMap);
    driverMarkersLayer = L.layerGroup().addTo(driverMap);
    if (hasCoords) L.marker([lat, lon]).addTo(driverMarkersLayer).bindPopup('Your saved business location');
    window.setTimeout(() => driverMap?.invalidateSize(), 100);
    const routeForm = $('#driverRouteForm');
    const autoOrigin = routeForm?.elements.namedItem('origin')?.value.trim();
    const autoDestination = routeForm?.elements.namedItem('destination')?.value.trim();
    const autoKey = `${autoOrigin || ''}=>${autoDestination || ''}`;
    if (autoOrigin && autoDestination && autoKey !== lastAutoRouteKey) {
      lastAutoRouteKey = autoKey;
      window.setTimeout(() => routeForm?.requestSubmit(), 250);
    }
  }

  async function geocodePlace(text) {
    const url = `https://nominatim.openstreetmap.org/search?format=jsonv2&limit=1&q=${encodeURIComponent(text)}`;
    const response = await fetch(url, { headers: { 'Accept-Language': 'en' } });
    if (!response.ok) throw new Error('Location search is unavailable. Try a more specific address.');
    const rows = await response.json();
    if (!rows.length) throw new Error(`Could not find location: ${text}`);
    return { lat: Number(rows[0].lat), lon: Number(rows[0].lon), label: rows[0].display_name };
  }

  async function planDriverRoute(event) {
    event.preventDefault();
    const form = event.currentTarget;
    const originText = form.elements.namedItem('origin').value.trim();
    const destinationText = form.elements.namedItem('destination').value.trim();
    const feedback = $('#driverRouteFeedback');
    const summary = $('#driverRouteSummary');
    const button = $('#optimizeRouteButton');
    setBusy(button, true, 'Finding best route…'); feedback.textContent = 'Searching for both locations and calculating road alternatives…';
    try {
      const origin = await geocodePlace(originText);
      await new Promise(resolve => window.setTimeout(resolve, 1100)); // Respect Nominatim's public one-request-per-second usage policy.
      const destination = await geocodePlace(destinationText);
      const routeUrl = `https://router.project-osrm.org/route/v1/driving/${origin.lon},${origin.lat};${destination.lon},${destination.lat}?overview=full&geometries=geojson&alternatives=true&steps=true`;
      const routeResponse = await fetch(routeUrl);
      if (!routeResponse.ok) throw new Error('Routing service did not return a route. Try again or open the route in an external map.');
      const routeData = await routeResponse.json();
      if (routeData.code !== 'Ok' || !routeData.routes?.length) throw new Error('No drivable route was returned for these locations.');
      const best = [...routeData.routes].sort((a, b) => a.duration - b.duration)[0];
      if (driverMap && window.L) {
        if (driverRouteLayer) driverMap.removeLayer(driverRouteLayer);
        if (driverMarkersLayer) driverMarkersLayer.clearLayers();
        driverMarkersLayer = L.layerGroup().addTo(driverMap);
        const points = best.geometry.coordinates.map(pair => [pair[1], pair[0]]);
        driverRouteLayer = L.polyline(points, { color: '#28724b', weight: 5, opacity: .88 }).addTo(driverMap);
        L.marker([origin.lat, origin.lon]).addTo(driverMarkersLayer).bindPopup(`Source: ${esc(originText)}`);
        L.marker([destination.lat, destination.lon]).addTo(driverMarkersLayer).bindPopup(`Destination: ${esc(destinationText)}`);
        driverMap.fitBounds(driverRouteLayer.getBounds(), { padding: [28, 28] });
      }
      const distance = (best.distance / 1000).toFixed(1);
      const hours = Math.floor(best.duration / 3600);
      const mins = Math.round((best.duration % 3600) / 60);
      const duration = hours ? `${hours} hr ${mins} min` : `${mins} min`;
      summary.innerHTML = `<strong>${distance} km · ${duration}</strong><p>${esc(originText)} → ${esc(destinationText)}</p><small>Fastest of ${routeData.routes.length} route option${routeData.routes.length === 1 ? '' : 's'} returned by OSRM. Travel time excludes live traffic.</small>`;
      const external = `https://www.openstreetmap.org/directions?engine=fossgis_osrm_car&route=${origin.lat}%2C${origin.lon}%3B${destination.lat}%2C${destination.lon}`;
      $('#openExternalRoute').href = external;
      feedback.textContent = 'Route optimized using road-network data. Check vehicle restrictions, tolls and local road conditions before dispatch.';
    } catch (error) {
      feedback.textContent = error.message;
      toast(error.message, true);
      const mapsUrl = `https://www.google.com/maps/dir/?api=1&origin=${encodeURIComponent(originText)}&destination=${encodeURIComponent(destinationText)}&travelmode=driving`;
      $('#openExternalRoute').href = mapsUrl;
    } finally { setBusy(button, false); }
  }

  $('#roleWorkspace').addEventListener('submit', event => {
    if (event.target.id === 'farmPlotForm') submitFarmPlot(event);
    else if (event.target.id === 'roleOperationForm') submitRoleOperation(event);
    else if (event.target.id === 'driverRouteForm') planDriverRoute(event);
  });
  $('#roleWorkspace').addEventListener('change', event => {
    const select = event.target.closest('[data-plot-stage]');
    if (select) updatePlotStage(select.dataset.plotStage, select.value);
    const operationSelect = event.target.closest('[data-operation-status-change]');
    if (operationSelect) updateOperationStatus(operationSelect.dataset.operationStatusChange, operationSelect.value);
  });
  $('#roleWorkspace').addEventListener('click', event => {
    const remove = event.target.closest('[data-delete-plot]');
    if (remove) deleteFarmPlot(remove.dataset.deletePlot);
    const planRoute = event.target.closest('[data-plan-driver-route]');
    if (planRoute) {
      const routeForm = $('#driverRouteForm');
      routeForm.elements.namedItem('origin').value = planRoute.dataset.routeOrigin || '';
      routeForm.elements.namedItem('destination').value = planRoute.dataset.routeDestination || '';
      routeForm.scrollIntoView({ behavior: 'smooth', block: 'center' });
      routeForm.requestSubmit();
    }
  });

  // Auth forms
  $$('.auth-tab').forEach(button => button.addEventListener('click', () => setAuthMode(button.dataset.auth)));
  $('#loginForm').addEventListener('submit', async event => {
    event.preventDefault();
    const form = event.currentTarget;
    const button = form.querySelector('button[type="submit"]'); setBusy(button, true, 'Signing in…');
    $('#authError').hidden = true;
    try {
      const data = Object.fromEntries(new FormData(form).entries());
      await establishSession(data.identifier, data.password);
    } catch (error) { $('#authError').textContent = error.message; $('#authError').hidden = false; }
    finally { setBusy(button, false); }
  });
  $('#registerForm').addEventListener('submit', async event => {
    event.preventDefault();
    const form = event.currentTarget;
    const data = Object.fromEntries(new FormData(form).entries());
    const button = form.querySelector('button[type="submit"]'); setBusy(button, true, 'Creating account…');
    $('#authError').hidden = true;
    try {
      await api('/auth/register', { method: 'POST', body: JSON.stringify(data) });
      await establishSession(data.username, data.password);
    } catch (error) { $('#authError').textContent = error.message; $('#authError').hidden = false; }
    finally { setBusy(button, false); }
  });

  // Global navigation and page actions
  document.addEventListener('click', event => {
    const pageButton = event.target.closest('[data-page]');
    if (pageButton) { event.preventDefault(); showPage(pageButton.dataset.page); return; }
    const quick = event.target.closest('[data-quick-action]');
    if (quick) {
      const action = quick.dataset.quickAction;
      const filter = quick.dataset.filter;
      if (action === 'create') openListingDialog(filter);
      else if (action === 'marketplace') { if ($('#listingCategory')) $('#listingCategory').value = filter || ''; showPage('marketplace'); }
      else if (action === 'network') { if ($('#peopleRole')) $('#peopleRole').value = filter || ''; showPage('network'); }
      return;
    }
    const connectListing = event.target.closest('[data-connect-listing]');
    if (connectListing) { const item = state.listings.find(row => row.id === connectListing.dataset.connectListing) || state.dashboard?.recommended_matches?.find(row => row.id === connectListing.dataset.connectListing); openConnectDialog({ listingId: connectListing.dataset.connectListing, name: item?.owner_name || 'the listing owner' }); return; }
    const connectPerson = event.target.closest('[data-connect-person]');
    if (connectPerson) { openConnectDialog({ recipientId: connectPerson.dataset.connectPerson, name: connectPerson.dataset.personName }); return; }
    const action = event.target.closest('[data-connection-action]');
    if (action) { handleConnectionStatus(action.dataset.id, action.dataset.connectionAction); return; }
    const message = event.target.closest('[data-message-connection]');
    if (message) { openMessages(message.dataset.messageConnection, message.dataset.messageName); return; }
    const close = event.target.closest('[data-close]');
    if (close) { document.getElementById(close.dataset.close).close(); return; }
    const closeListingButton = event.target.closest('[data-close-listing]');
    if (closeListingButton) { closeListing(closeListingButton.dataset.closeListing); return; }
  });
  $('#logoutButton').addEventListener('click', () => signOut(true));
  $('#mobileMenu').addEventListener('click', () => $('#sidebar').classList.toggle('open'));
  $('#refreshButton').addEventListener('click', async () => { await refreshDashboard(); await loadMarketplace(); toast('Workspace refreshed.'); });
  $('#heroCreateButton').addEventListener('click', () => openListingDialog());
  $('#marketCreateButton').addEventListener('click', () => openListingDialog());
  $('#myCreateButton').addEventListener('click', () => openListingDialog());
  $('#applyListingFilters').addEventListener('click', loadMarketplace);
  $('#listingSearch').addEventListener('keydown', event => { if (event.key === 'Enter') loadMarketplace(); });
  $('#applyPeopleFilters').addEventListener('click', loadDirectory);
  $('#peopleSearch').addEventListener('keydown', event => { if (event.key === 'Enter') loadDirectory(); });
  $('#connectionTabs').addEventListener('click', event => { const tab = event.target.closest('[data-box]'); if (tab) loadConnections(tab.dataset.box); });
  $('#listingForm').addEventListener('submit', submitListing);
  $('#connectForm').addEventListener('submit', submitConnection);
  $('#messageForm').addEventListener('submit', submitMessage);
  $('#profileForm').addEventListener('submit', submitProfile);
  $('#aiChatForm').addEventListener('submit', event => {
    event.preventDefault();
    const input = $('#aiMessageInput');
    const message = input.value;
    input.value = ''; input.style.height = 'auto'; $('#aiCharCount').textContent = '0 / 5000';
    sendAiMessage(message);
  });
  $('#aiMessageInput').addEventListener('input', event => {
    event.currentTarget.style.height = 'auto';
    event.currentTarget.style.height = `${Math.min(event.currentTarget.scrollHeight, 130)}px`;
    $('#aiCharCount').textContent = `${event.currentTarget.value.length} / 5000`;
  });
  $('#aiMessageInput').addEventListener('keydown', event => {
    if (event.key === 'Enter' && !event.shiftKey) { event.preventDefault(); $('#aiChatForm').requestSubmit(); }
  });
  $('#aiNewConversation').addEventListener('click', startNewAiConversation);
  $('#aiChatMessages').addEventListener('click', event => {
    const prompt = event.target.closest('[data-ai-prompt]');
    if (prompt) sendAiMessage(prompt.dataset.aiPrompt);
  });

  // Bootstrap the existing login session, if there is one.
  (async () => {
    if (!state.token) { showAuth('login'); return; }
    try {
      state.user = await api('/users/me');
      state.role = state.user.role;
      await loadWorkspace();
      showApp();
      showPage('overview');
    } catch (error) {
      showAuth('login');
      if (state.token) toast(error.message, true);
    }
  })();
})();
