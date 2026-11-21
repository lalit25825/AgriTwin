(() => {
  const $ = (selector) => document.querySelector(selector);
  const messages = $('#chatMessages');
  const form = $('#chatForm');
  const input = $('#messageInput');
  const sendButton = $('#sendButton');
  const agentSelect = $('#agentSelect');
  const toast = $('#toast');
  const sessionKey = 'agritwin_session_id';
  let sessionId = localStorage.getItem(sessionKey) || createSessionId();
  let isSending = false;
  let toastTimer;

  function createSessionId() {
    const id = (window.crypto && crypto.randomUUID)
      ? crypto.randomUUID()
      : `agritwin-${Date.now()}-${Math.random().toString(16).slice(2)}`;
    localStorage.setItem(sessionKey, id);
    return id;
  }

  function showToast(message) {
    toast.textContent = message;
    toast.classList.add('show');
    window.clearTimeout(toastTimer);
    toastTimer = window.setTimeout(() => toast.classList.remove('show'), 3300);
  }

  function setServiceStatus(isOnline, text) {
    ['#sidebarStatusDot', '#topStatusDot', '#chatStatusDot'].forEach((selector) => {
      const el = $(selector);
      el.classList.toggle('online', isOnline);
      el.classList.toggle('offline', !isOnline);
    });
    $('#sidebarStatusText').textContent = text;
    $('#topStatusText').textContent = isOnline ? 'API key configured' : 'Setup required';
    $('#chatStatusText').textContent = isOnline ? 'Ready to assist' : 'API key required';
  }

  const marketWatch = {
    loading: false,
    lastPayload: null,
    timer: null,
  };

  const formatRupees = (value) => {
    const number = Number(value);
    return Number.isFinite(number)
      ? `₹${new Intl.NumberFormat('en-IN', { maximumFractionDigits: 0 }).format(number)}`
      : '—';
  };

  const formatMarketDate = (value) => {
    if (!value) return 'Date unavailable';
    const parsed = new Date(`${value}T00:00:00`);
    if (Number.isNaN(parsed.getTime())) return String(value);
    return new Intl.DateTimeFormat('en-IN', { day: '2-digit', month: 'short', year: 'numeric' }).format(parsed);
  };

  function svgElement(tag, attrs = {}, text = '') {
    const node = document.createElementNS('http://www.w3.org/2000/svg', tag);
    Object.entries(attrs).forEach(([key, value]) => node.setAttribute(key, String(value)));
    if (text) node.textContent = text;
    return node;
  }

  function renderMarketChart(history, forecasts) {
    const svg = $('#marketTrendChart');
    if (!svg) return;
    svg.replaceChildren();
    const observed = Array.isArray(history) ? history.filter((item) => Number.isFinite(Number(item.modal_price))) : [];
    const predicted = Array.isArray(forecasts) ? forecasts.filter((item) => Number.isFinite(Number(item.predicted_price))) : [];
    if (!observed.length && !predicted.length) {
      svg.appendChild(svgElement('text', { x: 380, y: 126, 'text-anchor': 'middle', class: 'chart-axis-label' }, 'Price history is not available yet'));
      return;
    }
    const combined = observed.map((item) => Number(item.modal_price)).concat(predicted.map((item) => Number(item.predicted_price)));
    const low = Math.min(...combined);
    const high = Math.max(...combined);
    const padding = Math.max((high - low) * 0.18, high * 0.015, 1);
    const minValue = Math.max(0, low - padding);
    const maxValue = high + padding;
    const x0 = 48, x1 = 744, y0 = 18, y1 = 208;
    const count = Math.max(2, observed.length + predicted.length);
    const x = (index) => x0 + (x1 - x0) * index / (count - 1);
    const y = (value) => y1 - ((value - minValue) / Math.max(maxValue - minValue, 1)) * (y1 - y0);

    for (let index = 0; index <= 4; index += 1) {
      const value = minValue + (maxValue - minValue) * index / 4;
      const yy = y(value);
      svg.appendChild(svgElement('line', { x1: x0, y1: yy, x2: x1, y2: yy, class: 'chart-grid-line' }));
      svg.appendChild(svgElement('text', { x: x0 - 8, y: yy + 3, 'text-anchor': 'end', class: 'chart-axis-label' }, Math.round(value).toLocaleString('en-IN')));
    }

    const allDates = observed.map((item) => item.date).concat(predicted.map((item) => item.date));
    const tickIndices = [...new Set([0, Math.floor((allDates.length - 1) / 3), Math.floor(2 * (allDates.length - 1) / 3), allDates.length - 1])];
    tickIndices.forEach((index) => {
      if (index < 0 || !allDates[index]) return;
      const parsed = new Date(`${allDates[index]}T00:00:00`);
      const label = Number.isNaN(parsed.getTime()) ? allDates[index] : new Intl.DateTimeFormat('en-IN', { day: '2-digit', month: 'short' }).format(parsed);
      svg.appendChild(svgElement('text', { x: x(index), y: 232, 'text-anchor': 'middle', class: 'chart-axis-label' }, label));
    });

    const observedPoints = observed.map((item, index) => `${x(index)},${y(Number(item.modal_price))}`).join(' ');
    if (observed.length) {
      svg.appendChild(svgElement('polyline', { points: observedPoints, class: 'chart-observed-line' }));
      observed.forEach((item, index) => {
        if (index === observed.length - 1 || observed.length < 8) {
          svg.appendChild(svgElement('circle', { cx: x(index), cy: y(Number(item.modal_price)), r: 3.7, class: 'chart-observed-point' }));
        }
      });
    }
    if (predicted.length) {
      const forecastPoints = [];
      if (observed.length) forecastPoints.push(`${x(observed.length - 1)},${y(Number(observed[observed.length - 1].modal_price))}`);
      predicted.forEach((item, index) => forecastPoints.push(`${x(observed.length + index)},${y(Number(item.predicted_price))}`));
      svg.appendChild(svgElement('polyline', { points: forecastPoints.join(' '), class: 'chart-forecast-line' }));
      predicted.forEach((item, index) => {
        if (index === predicted.length - 1 || predicted.length < 8) {
          svg.appendChild(svgElement('circle', { cx: x(observed.length + index), cy: y(Number(item.predicted_price)), r: 3.5, class: 'chart-forecast-point' }));
        }
      });
    }
  }

  function renderMarketWatch(data) {
    marketWatch.lastPayload = data;
    const feedStatus = $('#marketFeedStatus');
    const statusText = $('#marketFeedStatusText');
    const live = data.source_status === 'live_api';
    const historicalApi = data.source_status === 'historical_api';
    const unavailable = !data.available;
    feedStatus.classList.toggle('offline', !live && !unavailable);
    feedStatus.classList.toggle('error', unavailable);
    statusText.textContent = unavailable ? 'No matching market data' : live ? 'Government API queried' : historicalApi ? 'Historical API data · not live' : 'Saved observations · not live';

    const summary = data.summary || {};
    const best = (data.mandis || []).find((item) => item.market === summary.best_mandi) || (data.mandis || [])[0];
    $('#marketBestPrice').textContent = best ? formatRupees(summary.best_modal_price ?? best.modal_price) : '—';
    $('#marketBestMeta').textContent = best ? `${data.commodity} · ${formatMarketDate(best.date)}${best.data_age_days > 3 ? ' · stale quote' : ''}` : 'No published price found';
    $('#marketBestMandi').textContent = summary.best_mandi || '—';
    $('#marketBestDistrict').textContent = summary.best_district || data.resolved_district || 'Region not resolved';
    $('#marketMandiCount').textContent = Number(summary.mandi_count || 0).toLocaleString('en-IN');
    $('#marketRegionMatch').textContent = data.region_match === 'nearby_districts' ? `Nearby districts: ${(data.nearby_districts_considered || []).join(', ')}` : data.region_match === 'same_state_fallback' ? 'Same-state fallback' : data.region_match === 'all_available_fallback' ? 'Wider data fallback' : data.region_match === 'no_regional_match' ? 'No matching region' : 'Requested region';
    $('#marketLatestDate').textContent = data.last_observed_date ? formatMarketDate(data.last_observed_date) : '—';
    $('#marketSourceFreshness').textContent = data.freshness === 'today' && live ? 'Today · API checked' : data.freshness === 'recent' ? `${data.data_age_days} day(s) old` : data.freshness === 'stale' ? `${data.data_age_days ?? '?'} days old · stale` : 'Freshness unavailable';
    $('#marketChartTitle').textContent = best ? `${best.market} · ${data.commodity}` : 'Regional price trend';

    const forecastMeta = data.forecast_meta || {};
    const forecast = data.forecast || [];
    const terminal = forecast.length ? forecast[forecast.length - 1] : null;
    $('#marketForecastPrice').textContent = terminal ? formatRupees(terminal.predicted_price) : '—';
    $('#marketForecastDate').textContent = terminal ? `Estimate for ${formatMarketDate(terminal.date)}` : 'End-of-horizon estimate';
    const confidence = String(forecastMeta.confidence || 'none').toLowerCase();
    const tag = $('#marketConfidenceTag');
    tag.textContent = confidence.replaceAll('_', ' ').toUpperCase();
    tag.className = `forecast-tag ${confidence}`;
    const direction = forecastMeta.direction || 'not_established';
    const firstForecast = forecast[0] ? Number(forecast[0].predicted_price) : NaN;
    const current = Number(best?.modal_price ?? summary.best_modal_price);
    const move = Number.isFinite(firstForecast) && current ? ((firstForecast - current) / current) * 100 : null;
    $('#marketForecastDirection').textContent = direction === 'up'
      ? `Model outlook: upward${move == null ? '' : ` · +${move.toFixed(1)}% first-step estimate`}`
      : direction === 'down'
        ? `Model outlook: downward${move == null ? '' : ` · ${move.toFixed(1)}% first-step estimate`}`
        : direction === 'flat' ? 'Model outlook: broadly stable' : 'Directional movement not established';
    $('#marketTrainingDays').textContent = forecastMeta.history_days ?? '—';
    $('#marketForecastMae').textContent = forecastMeta.mae == null ? 'Not validated' : `${formatRupees(forecastMeta.mae)} / qtl`;
    $('#marketForecastMape').textContent = forecastMeta.mape == null ? 'Not available' : `${Number(forecastMeta.mape).toFixed(1)}%`;
    $('#marketForecastMethod').textContent = forecastMeta.model || '—';
    $('#marketForecastNote').textContent = forecastMeta.note || 'There is not enough source history to make a reliable forecast.';
    $('#marketModelLabel').textContent = forecastMeta.model ? `MODEL · ${forecastMeta.model}` : 'MODEL · NOT AVAILABLE';

    const rows = $('#marketMandiRows');
    rows.replaceChildren();
    const mandis = Array.isArray(data.mandis) ? data.mandis : [];
    $('#marketTableCount').textContent = `${mandis.length} markets`;
    if (!mandis.length) {
      const tr = document.createElement('tr');
      const td = document.createElement('td');
      td.colSpan = 4;
      td.className = 'market-empty-cell';
      td.textContent = data.warning || 'No matching mandi observations found.';
      tr.appendChild(td);
      rows.appendChild(tr);
    } else {
      mandis.slice(0, 12).forEach((item, index) => {
        const tr = document.createElement('tr');
        if (index === 0) tr.className = 'best-row';
        const name = document.createElement('td');
        name.className = 'mandi-name-cell';
        const strong = document.createElement('strong'); strong.textContent = item.market || 'Unknown mandi';
        const small = document.createElement('small'); small.textContent = item.district || item.state || 'District unavailable';
        const proximity = document.createElement('span'); proximity.className = 'market-proximity'; proximity.textContent = item.proximity || 'regional result';
        name.append(strong, small, proximity);
        const observedCell = document.createElement('td'); observedCell.textContent = formatMarketDate(item.date);
        const range = document.createElement('td'); range.textContent = item.min_price == null || item.max_price == null ? '—' : `${formatRupees(item.min_price)} · ${formatRupees(item.max_price)}`;
        const modal = document.createElement('td'); modal.className = 'market-price-cell';
        const modalValue = document.createElement('strong'); modalValue.textContent = formatRupees(item.modal_price);
        modal.appendChild(modalValue);
        const quality = document.createElement('small');
        const quoteDetails = Array.isArray(item.quality_quotes) ? item.quality_quotes : [];
        if (quoteDetails.length > 1 && item.modal_price_spread_low != null && item.modal_price_spread_high != null) {
          quality.textContent = `${formatRupees(item.modal_price_spread_low)}–${formatRupees(item.modal_price_spread_high)} across variety/grade quotes`;
        } else if (quoteDetails.length === 1) {
          quality.textContent = `${quoteDetails[0].variety} · ${quoteDetails[0].grade}`;
        } else {
          quality.textContent = `${Number(item.records || 1)} source quote(s)`;
        }
        modal.appendChild(quality);
        tr.append(name, observedCell, range, modal);
        rows.appendChild(tr);
      });
    }
    $('#marketBestPriceNote').textContent = summary.price_basis || 'Highest published modal quote before transport and other sale costs.';

    const tape = $('#marketTapeList');
    tape.replaceChildren();
    const tapeRows = Array.isArray(data.market_tape) ? data.market_tape : [];
    if (!tapeRows.length) {
      const empty = document.createElement('div'); empty.className = 'market-tape-empty'; empty.textContent = 'No published observations are available for this crop and region.'; tape.appendChild(empty);
    } else {
      tapeRows.slice(0, 14).forEach((item) => {
        const row = document.createElement('div'); row.className = 'market-tape-item';
        const dot = document.createElement('i'); dot.className = 'market-tape-dot';
        const copy = document.createElement('div'); copy.className = 'market-tape-copy';
        const title = document.createElement('strong'); title.textContent = `${item.market} · ${item.district}`;
        const sub = document.createElement('small'); sub.textContent = `${data.commodity} · published ${formatMarketDate(item.date)}`;
        copy.append(title, sub);
        const price = document.createElement('span'); price.className = 'market-tape-price'; price.textContent = formatRupees(item.modal_price);
        row.append(dot, copy, price); tape.appendChild(row);
      });
    }

    const fetchedAt = data.fetched_at ? new Date(data.fetched_at) : null;
    const fetchedLabel = fetchedAt && !Number.isNaN(fetchedAt.getTime())
      ? new Intl.DateTimeFormat('en-IN', { dateStyle: 'medium', timeStyle: 'short' }).format(fetchedAt)
      : 'not recorded';
    const statusLine = data.warning || (live
      ? `Source checked ${fetchedLabel}. The government dataset is a daily published mandi feed; repeat polling only detects new published rows when the source updates.`
      : historicalApi
        ? `The API returned historical records but no current daily quote for this crop and region. Last check: ${fetchedLabel}.`
        : `Showing saved observations. A live refresh is unavailable. Add DATA_GOV_API_KEY to .env and restart the server. Last check: ${fetchedLabel}.`);
    $('#marketWatchNote').textContent = `${data.source || 'Market source unavailable'} · ${statusLine}`;
    renderMarketChart(data.history || [], forecast);
  }

  async function loadMarketWatch(force = false) {
    if (marketWatch.loading) return;
    const button = $('#marketRefreshButton');
    marketWatch.loading = true;
    button.disabled = true;
    button.classList.toggle('is-loading', force);
    const region = $('#marketRegion').value.trim() || 'Nashik';
    const commodity = $('#marketCommodity').value || 'Onion';
    const horizon = Number($('#marketHorizon').value || 7);
    try {
      const response = force
        ? await fetch('/api/market/watch/refresh', {
          method: 'POST', headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ region, commodity, horizon }),
        })
        : await fetch(`/api/market/watch?${new URLSearchParams({ region, commodity, horizon: String(horizon) })}`);
      const data = await response.json().catch(() => ({}));
      if (!response.ok) throw new Error(data.detail || `Market feed request failed (${response.status})`);
      renderMarketWatch(data);
    } catch (error) {
      $('#marketFeedStatus').classList.add('error');
      $('#marketFeedStatusText').textContent = 'Market feed unavailable';
      $('#marketWatchNote').textContent = error.message || 'Could not load the Market Agent dashboard.';
      showToast(error.message || 'Market feed unavailable.');
    } finally {
      marketWatch.loading = false;
      button.disabled = false;
      button.classList.remove('is-loading');
    }
  }

  function startMarketWatch() {
    if (marketWatch.timer) window.clearInterval(marketWatch.timer);
    marketWatch.timer = window.setInterval(() => {
      if (document.visibilityState === 'visible') loadMarketWatch(false);
    }, 300000);
  }

  async function loadHealth() {
    try {
      const response = await fetch('/api/health');
      if (!response.ok) throw new Error('Health endpoint unavailable');
      const data = await response.json();
      const configured = Boolean(data.provider_configured);
      setServiceStatus(configured, configured ? 'AI key configured' : 'AI setup required');
      const market = data.market_data || {};
      $('#marketRecordCount').textContent = Number(market.records || 0).toLocaleString('en-IN');
      $('#commodityCount').textContent = Number(market.commodities || 0).toLocaleString('en-IN');
      $('#marketCount').textContent = Number(market.markets || 0).toLocaleString('en-IN');
      $('#marketRecordFoot').textContent = market.available
        ? `Historical snapshot · ${market.snapshot_date || 'date unavailable'}`
        : 'Market CSV not found';
      $('#snapshotDate').textContent = market.snapshot_date || 'Snapshot date unavailable';
      $('#sessionLabel').textContent = `${sessionId.slice(0, 8)}…`;
      if (!configured) showToast('Add your Groq API key to .env and restart AgriTwin to enable chat.');
    } catch (error) {
      setServiceStatus(false, 'API server unavailable');
      showToast('Could not connect to the AgriTwin API. Start the server with run.bat or run.sh.');
    }
  }

  function appendMessage(role, content, options = {}) {
    const row = document.createElement('div');
    row.className = `message-row ${role}${options.error ? ' error' : ''}`;
    const avatar = document.createElement('div');
    avatar.className = 'message-avatar';
    avatar.textContent = role === 'user' ? 'YOU' : 'AT';
    const body = document.createElement('div');
    body.className = 'message-body';
    const meta = document.createElement('div');
    meta.className = 'message-meta';
    meta.textContent = role === 'user' ? 'You' : (options.label || 'AgriTwin');
    const bubble = document.createElement('div');
    bubble.className = 'message-bubble';
    if (content && typeof content === 'object' && content.type === 'route_map') {
      const summary = document.createElement('p');
      summary.textContent = content.message || 'Route from your previous logistics request.';
      bubble.appendChild(summary);
      const details = document.createElement('p');
      const distance = content.distance_km != null ? `${content.distance_km} km` : 'distance unavailable';
      const minutes = Number(content.duration_minutes);
      const duration = Number.isFinite(minutes) ? `${Math.floor(minutes / 60)} h ${Math.round(minutes % 60)} min` : 'ETA unavailable';
      details.textContent = `${content.origin || 'Origin'} → ${content.destination || 'Destination'} · ${distance} · ${duration}`;
      bubble.appendChild(details);
      if (content.location_resolution && content.location_resolution.destination_was_interpreted) {
        const note = document.createElement('p');
        note.className = 'route-resolution-note';
        note.textContent = `Destination interpreted as: ${content.location_resolution.destination_resolved}`;
        bubble.appendChild(note);
      }
      const link = document.createElement('a');
      link.className = 'route-map-link';
      link.textContent = 'Open route in Google Maps';
      try {
        const url = new URL(content.maps_url);
        if (url.protocol === 'https:' && url.hostname === 'www.google.com' && url.pathname.startsWith('/maps/dir/')) {
          link.href = url.href;
          link.target = '_blank';
          link.rel = 'noopener noreferrer';
          bubble.appendChild(link);
        }
      } catch (_) {
        const note = document.createElement('p');
        note.textContent = 'Map link is unavailable.';
        bubble.appendChild(note);
      }
    } else {
      bubble.textContent = typeof content === 'string' ? content : JSON.stringify(content, null, 2);
    }
    body.append(meta, bubble);
    if (Array.isArray(options.agents) && options.agents.length) {
      const tags = document.createElement('div');
      tags.className = 'message-agent-tags';
      options.agents.forEach((agent) => {
        const tag = document.createElement('span');
        tag.textContent = `${agent[0].toUpperCase()}${agent.slice(1)} agent`;
        tags.appendChild(tag);
      });
      body.appendChild(tags);
    }
    row.append(avatar, body);
    messages.appendChild(row);
    messages.scrollTop = messages.scrollHeight;
    return row;
  }

  function addTyping() {
    const row = document.createElement('div');
    row.className = 'message-row assistant';
    row.id = 'typingMessage';
    const avatar = document.createElement('div');
    avatar.className = 'message-avatar';
    avatar.textContent = 'AT';
    const body = document.createElement('div');
    body.className = 'message-body';
    const meta = document.createElement('div');
    meta.className = 'message-meta';
    meta.textContent = 'AgriTwin is coordinating';
    const bubble = document.createElement('div');
    bubble.className = 'message-bubble';
    const dots = document.createElement('span');
    dots.className = 'typing-dots';
    for (let i = 0; i < 3; i += 1) dots.appendChild(document.createElement('i'));
    bubble.appendChild(dots);
    body.append(meta, bubble);
    row.append(avatar, body);
    messages.appendChild(row);
    messages.scrollTop = messages.scrollHeight;
  }

  function removeTyping() {
    const typing = $('#typingMessage');
    if (typing) typing.remove();
  }

  function displayActivity(agents) {
    const empty = $('#activityEmpty');
    const list = $('#activityList');
    list.replaceChildren();
    if (!agents || agents.length === 0) {
      empty.hidden = false;
      list.hidden = true;
      return;
    }
    empty.hidden = true;
    list.hidden = false;
    const glyphs = { harvest: '✳', climate: '◌', market: '⌁', logistics: '↗' };
    agents.forEach((name) => {
      const item = document.createElement('div');
      item.className = 'activity-item';
      const icon = document.createElement('span');
      icon.className = `activity-item-icon ${name}-symbol`;
      icon.textContent = glyphs[name] || '•';
      const copy = document.createElement('span');
      const strong = document.createElement('strong');
      strong.textContent = `${name[0].toUpperCase()}${name.slice(1)} Agent`;
      const small = document.createElement('small');
      small.textContent = 'Completed specialist analysis';
      copy.append(strong, small);
      const check = document.createElement('span');
      check.className = 'activity-check';
      check.textContent = '✓';
      item.append(icon, copy, check);
      list.appendChild(item);
    });
  }

  async function sendMessage(message) {
    const trimmed = message.trim();
    if (!trimmed || isSending) return;
    isSending = true;
    sendButton.disabled = true;
    input.disabled = true;
    appendMessage('user', trimmed);
    $('#welcomeMessage')?.remove();
    addTyping();

    try {
      const response = await fetch('/api/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message: trimmed, session_id: sessionId, agent: agentSelect.value }),
      });
      const data = await response.json().catch(() => ({}));
      removeTyping();
      if (!response.ok) throw new Error(data.detail || `Request failed (${response.status})`);
      sessionId = data.session_id || sessionId;
      localStorage.setItem(sessionKey, sessionId);
      $('#sessionLabel').textContent = `${sessionId.slice(0, 8)}…`;
      appendMessage('assistant', data.response, { label: data.agent_label, agents: data.agents_used || [] });
      displayActivity(data.agents_used || []);
    } catch (error) {
      removeTyping();
      appendMessage('assistant', error.message || 'Something went wrong while contacting AgriTwin.', { label: 'Connection notice', error: true });
      if ((error.message || '').toLowerCase().includes('api key')) showToast('Configure GROQ_API_KEY in .env, then restart the server.');
    } finally {
      isSending = false;
      sendButton.disabled = false;
      input.disabled = false;
      input.focus();
    }
  }

  form.addEventListener('submit', (event) => {
    event.preventDefault();
    const message = input.value;
    if (!message.trim()) return;
    input.value = '';
    input.style.height = 'auto';
    $('#charCounter').textContent = '0 / 5000';
    sendMessage(message);
  });

  input.addEventListener('input', () => {
    input.style.height = 'auto';
    input.style.height = `${Math.min(input.scrollHeight, 130)}px`;
    $('#charCounter').textContent = `${input.value.length} / 5000`;
  });

  input.addEventListener('keydown', (event) => {
    if (event.key === 'Enter' && !event.shiftKey) {
      event.preventDefault();
      form.requestSubmit();
    }
  });

  document.querySelectorAll('[data-prompt]').forEach((button) => {
    button.addEventListener('click', () => {
      input.value = button.dataset.prompt || '';
      input.dispatchEvent(new Event('input'));
      input.focus();
    });
  });

  $('#newConversation').addEventListener('click', () => {
    if (isSending) return;
    sessionId = createSessionId();
    $('#sessionLabel').textContent = `${sessionId.slice(0, 8)}…`;
    messages.replaceChildren();
    const welcome = document.createElement('div');
    welcome.className = 'welcome-message';
    welcome.id = 'welcomeMessage';
    welcome.innerHTML = '<div class="welcome-kicker">NEW PRIVATE SESSION</div><h3>Where should<br>we begin?</h3><p>Your previous conversation remains separate. Start a new agricultural or supply-chain question below.</p>';
    messages.appendChild(welcome);
    displayActivity([]);
    input.value = '';
    input.focus();
  });

  $('#settingsButton').addEventListener('click', () => showToast('System configuration is managed in the project .env file.'));
  $('#mobileMenu').addEventListener('click', () => $('#sidebar').classList.toggle('open'));
  document.querySelectorAll('.nav-item').forEach((link) => {
    link.addEventListener('click', () => {
      document.querySelectorAll('.nav-item').forEach((item) => item.classList.remove('active'));
      link.classList.add('active');
      $('#sidebar').classList.remove('open');
    });
  });

  $('#marketWatchForm').addEventListener('submit', (event) => {
    event.preventDefault();
    loadMarketWatch(true);
  });

  $('#dateLabel').textContent = new Intl.DateTimeFormat('en-IN', { day: '2-digit', month: 'short', year: 'numeric' }).format(new Date()).toUpperCase() + ' · INDIA';
  loadHealth();
  loadMarketWatch(false);
  startMarketWatch();
})();
