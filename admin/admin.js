/**
 * admin.js — Davide Luongo CMS Admin v3.0
 * Gestione completa dashboard admin: nav, sezioni, API calls.
 * Nessuna dipendenza esterna. Vanilla JS moderno (ES2022+).
 */
'use strict';

// ── Utilità API ──────────────────────────────────────────────────────────────

function csrfToken() {
  const match = document.cookie.match('(^|;)\\s*csrf_token\\s*=\\s*([^;]+)');
  return match ? match.pop() : '';
}

async function api(method, path, body = null, isFormData = false) {
  const opts = {
    method,
    credentials: 'include',
    headers: {},
  };
  if (!isFormData) {
    opts.headers['Content-Type'] = 'application/json';
    if (body) opts.body = JSON.stringify(body);
  } else {
    // FormData: nessun Content-Type header, browser lo imposta con boundary
    if (body) opts.body = body;
  }
  if (['POST', 'PUT', 'DELETE', 'PATCH'].includes(method.toUpperCase())) {
    opts.headers['X-CSRF-Token'] = csrfToken();
  }
  const res = await fetch(path, opts);
  if (res.status === 401) {
    window.location.href = '/admin/index.html';
    return null;
  }
  let data;
  try { data = await res.json(); } catch { data = {}; }
  if (!res.ok) throw new Error(data.detail || `Errore ${res.status}`);
  return data;
}

// ── Messaggi globali ────────────────────────────────────────────────────────

function showMsg(msg, type = 'info', duration = 4000) {
  const el = document.getElementById('globalMessage');
  if (!el) return;
  el.textContent = msg;
  el.className = `global-message ${type}`;
  el.removeAttribute('hidden');
  clearTimeout(el._timer);
  el._timer = setTimeout(() => el.setAttribute('hidden', ''), duration);
}

// ── Formattazione ────────────────────────────────────────────────────────────

function formatEuro(cents) {
  if (cents == null) return '—';
  return new Intl.NumberFormat('it-IT', { style: 'currency', currency: 'EUR' }).format(cents / 100);
}

function formatDate(iso) {
  if (!iso) return '—';
  return new Date(iso).toLocaleDateString('it-IT', { day: '2-digit', month: '2-digit', year: 'numeric' });
}

function formatDateTime(iso) {
  if (!iso) return '—';
  return new Date(iso).toLocaleString('it-IT', { day: '2-digit', month: '2-digit', year: 'numeric', hour: '2-digit', minute: '2-digit' });
}

function badge(status) {
  const labels = {
    active: 'Attivo', paid: 'Pagato', draft: 'Bozza',
    pending: 'In attesa', soldout: 'Sold Out',
    inactive: 'Inattivo', cancelled: 'Annullato',
    completed: 'Completato', published: 'Pubblicato',
  };
  return `<span class="badge badge-${status}">${labels[status] || status}</span>`;
}

// ── Navigazione ──────────────────────────────────────────────────────────────

const sectionLoaders = {};

function navigate(sectionId) {
  document.querySelectorAll('.section').forEach(s => {
    s.classList.remove('active');
    s.hidden = true;
  });
  document.querySelectorAll('.nav-item').forEach(a => {
    a.classList.remove('active');
    a.removeAttribute('aria-current');
  });

  const target = document.getElementById(`section-${sectionId}`);
  if (target) {
    target.classList.add('active');
    target.hidden = false;
  }

  const navLink = document.querySelector(`[data-section="${sectionId}"]`);
  if (navLink) {
    navLink.classList.add('active');
    navLink.setAttribute('aria-current', 'page');
    document.getElementById('pageTitle').textContent = navLink.textContent.trim().replace(/^[^\w]+ /, '');
  }

  // Carica dati sezione
  if (sectionLoaders[sectionId]) sectionLoaders[sectionId]();
}

// ── Init user info ───────────────────────────────────────────────────────────

async function initUser() {
  try {
    const data = await api('GET', '/api/admin/auth/me');
    if (!data) return;
    document.getElementById('userName').textContent = data.username;
    document.getElementById('userRole').textContent = data.role.toUpperCase();
  } catch {
    window.location.href = '/admin/index.html';
  }
}

// ── DASHBOARD ────────────────────────────────────────────────────────────────

async function loadDashboard() {
  try {
    const [workshops, participants] = await Promise.all([
      api('GET', '/api/admin/workshops/'),
      api('GET', '/api/admin/participants/'),
    ]);

    const ws = workshops?.workshops || [];
    const parts = participants?.participants || [];

    const paidCount = parts.filter(p => p.status === 'paid').length;
    const pendingCount = parts.filter(p => p.status === 'pending').length;
    const totalRevenue = parts.filter(p => p.status === 'paid').reduce((s, p) => s + (p.finalCents || 0), 0);
    const activeWs = ws.filter(w => w.status === 'active').length;

    const statsGrid = document.getElementById('statsGrid');
    statsGrid.innerHTML = `
      <div class="stat-card">
        <div class="stat-icon" aria-hidden="true">🏕️</div>
        <div class="stat-label">Workshop Attivi</div>
        <div class="stat-value">${activeWs}</div>
      </div>
      <div class="stat-card">
async function loadDashboard() {
  try {
    const [wsData, partsData, crmStats, jobsData] = await Promise.all([
      api('GET', '/api/admin/workshops/'),
      api('GET', '/api/admin/participants/'),
      api('GET', '/api/admin/crm/stats').catch(() => null),
      api('GET', '/api/admin/jobs/').catch(() => null),
    ]);

    const ws = wsData?.workshops || [];
    const parts = partsData?.participants || [];
    const paidParts = parts.filter(p => p.status === 'paid');
    const pendingCount = parts.filter(p => p.status === 'pending').length;
    const totalRevenue = paidParts.reduce((sum, p) => sum + (p.finalCents || 0), 0);

    const activeWs = ws.filter(w => w.status === 'active').length;
    const soldoutWs = ws.filter(w => w.status === 'soldout').length;

    // Stat cards principali
    document.getElementById('statsGrid').innerHTML = `
      <div class="stat-card">
        <div class="stat-icon" aria-hidden="true">🏕️</div>
        <div class="stat-label">Iniziative Attive</div>
        <div class="stat-value">${activeWs}</div>
        ${soldoutWs > 0 ? `<div class="stat-trend" style="color:var(--yellow)">${soldoutWs} sold out</div>` : ''}
      </div>
      <div class="stat-card">
        <div class="stat-icon" aria-hidden="true">✅</div>
        <div class="stat-label">Prenotazioni Pagate</div>
        <div class="stat-value">${paidParts.length}</div>
        ${pendingCount > 0 ? `<div class="stat-trend">${pendingCount} in attesa</div>` : ''}
      </div>
      <div class="stat-card">
        <div class="stat-icon" aria-hidden="true">💰</div>
        <div class="stat-label">Incasso Online Confermato</div>
        <div class="stat-value">${formatEuro(totalRevenue)}</div>
      </div>
      <div class="stat-card">
        <div class="stat-icon" aria-hidden="true">📇</div>
        <div class="stat-label">Contatti in Rubrica CRM</div>
        <div class="stat-value">${crmStats ? crmStats.totalContacts : parts.length}</div>
        ${crmStats ? `<div class="stat-trend" style="color:var(--accent)">${crmStats.newLeads} nuovi lead (${crmStats.conversionRatePct}% conv.)</div>` : ''}
      </div>
    `;

    // Widget CRM Pipeline
    if (crmStats) {
      document.getElementById('crmPipelineWidget').innerHTML = `
        <div style="display:grid;grid-template-columns:1fr 1fr;gap:.75rem;font-size:.875rem">
          <div style="background:rgba(255,255,255,0.02);padding:.6rem;border-radius:6px;border:1px solid var(--border)">
            <span style="color:var(--text-muted);font-size:.75rem">DA CONTATTARE</span>
            <div style="font-size:1.25rem;font-weight:700;color:var(--accent)">${crmStats.toContact + crmStats.newLeads}</div>
          </div>
          <div style="background:rgba(255,255,255,0.02);padding:.6rem;border-radius:6px;border:1px solid var(--border)">
            <span style="color:var(--text-muted);font-size:.75rem">FOLLOW-UP SCADUTI</span>
            <div style="font-size:1.25rem;font-weight:700;color:${crmStats.overdueFollowups > 0 ? 'var(--red)' : 'var(--green)'}">${crmStats.overdueFollowups}</div>
          </div>
          <div style="background:rgba(255,255,255,0.02);padding:.6rem;border-radius:6px;border:1px solid var(--border)">
            <span style="color:var(--text-muted);font-size:.75rem">CLIENTI CONFERMATI</span>
            <div style="font-size:1.25rem;font-weight:700;color:var(--green)">${crmStats.customers} (${crmStats.loyalCustomers} fedeli)</div>
          </div>
          <div style="background:rgba(255,255,255,0.02);padding:.6rem;border-radius:6px;border:1px solid var(--border)">
            <span style="color:var(--text-muted);font-size:.75rem">IN BLACKLIST</span>
            <div style="font-size:1.25rem;font-weight:700;color:var(--text-muted)">${crmStats.blacklistedCount}</div>
          </div>
        </div>
      `;
    }

    // Ricavi per fonte
    if (crmStats && crmStats.revenueBySource) {
      const revHtml = crmStats.revenueBySource.map(r => `
        <div style="display:flex;justify-content:space-between;padding:.35rem 0;border-bottom:1px solid var(--border);font-size:.85rem">
          <span>${escHtml(r.source)}</span>
          <span style="font-weight:700;color:var(--accent)">${r.totalFormatted}</span>
        </div>
      `).join('');
      document.getElementById('revenueBySourceWidget').innerHTML = revHtml || '<p style="color:var(--text-muted);font-size:.85rem">Nessun incasso</p>';
    }

    // Prossimi cutoff
    const now = new Date();
    const upcomingCutoffs = ws
      .filter(w => w.cutoffAt && new Date(w.cutoffAt) > now && w.cutoffStatus === 'pending')
      .sort((a, b) => new Date(a.cutoffAt) - new Date(b.cutoffAt))
      .slice(0, 5);

    document.getElementById('upcomingCutoffs').innerHTML = upcomingCutoffs.length
      ? upcomingCutoffs.map(w => `<div class="cutoff-item" style="padding:.5rem 0;border-bottom:1px solid var(--border)">
          <strong>${escHtml(w.title)}</strong>
          <div style="font-size:.8rem;color:var(--text-muted)">Cutoff: ${formatDateTime(w.cutoffAt)}</div>
        </div>`).join('')
      : '<p style="color:var(--text-muted);font-size:.85rem">Nessun cutoff imminente</p>';

    // Partecipanti per workshop
    const byWs = {};
    parts.filter(p => p.status === 'paid').forEach(p => {
      if (p.workshopId) byWs[p.workshopId] = (byWs[p.workshopId] || 0) + 1;
    });
    const byWsHtml = Object.entries(byWs).map(([id, count]) => {
      const w = ws.find(x => x.workshopKey === id);
      const title = w ? w.title : id;
      return `<div style="display:flex;justify-content:space-between;padding:.4rem 0;border-bottom:1px solid var(--border);font-size:.875rem">
        <span>${escHtml(title)}</span>
        <span style="font-weight:700;color:var(--accent)">${count} pax</span>
      </div>`;
    }).join('');
    document.getElementById('participantsByWorkshop').innerHTML = byWsHtml || '<p style="color:var(--text-muted);font-size:.85rem">Nessun dato</p>';

    // Coupon attivi
    try {
      const cData = await api('GET', '/api/admin/coupons/');
      const coupons = cData?.coupons || [];
      const activeC = coupons.filter(c => c.active);
      document.getElementById('activeCoupons').innerHTML = activeC.length
        ? activeC.map(c => `<div style="padding:.35rem 0;border-bottom:1px solid var(--border);font-size:.85rem"><code>${escHtml(c.code)}</code> — ${c.valueDecimal}${c.type === 'percentage' ? '%' : '€'}</div>`).join('')
        : '<p style="color:var(--text-muted);font-size:.85rem">Nessun coupon attivo</p>';
    } catch {}

    // Job in background
    if (jobsData && jobsData.jobs && jobsData.jobs.length) {
      const activeJobs = jobsData.jobs.filter(j => j.status === 'pending' || j.status === 'processing');
      document.getElementById('jobErrors').innerHTML = activeJobs.length
        ? activeJobs.map(j => `<div style="padding:.35rem 0;font-size:.85rem">⚙️ ${j.type} (${j.progressPercent}%)</div>`).join('')
        : '<p style="color:var(--green);font-size:.85rem">Tutti i job completati</p>';
    }

  } catch (err) {
    showMsg('Errore caricamento dashboard: ' + err.message, 'error');
  }
}

sectionLoaders['dashboard'] = loadDashboard;

// ── WORKSHOP ─────────────────────────────────────────────────────────────────

let allWorkshops = [];
let editingWorkshopId = null;

async function loadWorkshops() {
  const container = document.getElementById('workshopsList');
  container.innerHTML = '<div class="skeleton" style="height:120px;border-radius:10px"></div>'.repeat(3);
  try {
    const data = await api('GET', '/api/admin/workshops/');
    allWorkshops = data?.workshops || [];
    renderWorkshops(allWorkshops);
    // Popola i select nei filtri
    populateWorkshopSelects(allWorkshops);
  } catch (err) {
    showMsg('Errore caricamento workshop: ' + err.message, 'error');
  }
}

function renderWorkshops(list) {
  const container = document.getElementById('workshopsList');
  if (!list.length) { container.innerHTML = '<p style="color:var(--text-muted)">Nessun workshop trovato.</p>'; return; }
  container.innerHTML = list.map(w => `
    <div class="card-item" role="article">
      <div class="card-item-header">
        <div>
          <div class="card-item-title">${escHtml(w.title)}</div>
          <div style="font-size:.78rem;color:var(--text-muted);margin-top:.2rem">${w.workshopKey}</div>
        </div>
        ${badge(w.status)}
      </div>
      <div class="card-item-body">
        📅 ${w.startDate ? formatDate(w.startDate) : '—'}${w.endDate ? ' – ' + formatDate(w.endDate) : ''}
        &nbsp;|&nbsp; 💰 ${w.priceLabel || formatEuro(w.priceCents)}
        &nbsp;|&nbsp; 👥 ${w.availableSeats}/${w.totalSeats} posti
        ${w.cutoffAt ? `<br>⏰ Cutoff: ${formatDateTime(w.cutoffAt)} — <span class="badge badge-${w.cutoffStatus || 'draft'}">${w.cutoffStatus || 'pending'}</span>` : ''}
      </div>
      <div class="card-item-footer">
        <button class="btn-secondary btn-sm" onclick="openWorkshopModal('${escAttr(w.workshopKey)}')">✏️ Modifica</button>
        <button class="btn-secondary btn-sm" onclick="navigate('participants');filterByWorkshop('${escAttr(w.workshopKey)}')">👥 Partecipanti</button>
        <button class="btn-secondary btn-sm" onclick="navigate('costs');selectCostWorkshop('${escAttr(w.workshopKey)}')">💰 Costi</button>
        <button class="btn-secondary btn-sm" onclick="generateReport('${escAttr(w.workshopKey)}')">📊 Report</button>
      </div>
    </div>
  `).join('');
}

function openWorkshopModal(workshopKey = null) {
  editingWorkshopId = workshopKey;
  const modal = document.getElementById('workshopModal');
  document.getElementById('workshopModalTitle').textContent = workshopKey ? 'Modifica Workshop' : 'Nuovo Workshop';

  // Reset form
  document.getElementById('workshopForm').reset();

  if (workshopKey) {
    const ws = allWorkshops.find(w => w.workshopKey === workshopKey);
    if (ws) {
      document.getElementById('ws-title').value = ws.title || '';
      document.getElementById('ws-key').value = ws.workshopKey || '';
      document.getElementById('ws-key').disabled = true;
      document.getElementById('ws-startDate').value = ws.startDate || '';
      document.getElementById('ws-endDate').value = ws.endDate || '';
      document.getElementById('ws-price').value = ws.priceCents || '';
      document.getElementById('ws-seats').value = ws.totalSeats || 8;
      document.getElementById('ws-cutoff').value = ws.cutoffAt ? ws.cutoffAt.slice(0, 16) : '';
      document.getElementById('ws-status').value = ws.status || 'active';
      document.getElementById('ws-location').value = ws.location || '';
      document.getElementById('ws-description').value = ws.description || '';
      document.getElementById('ws-notes').value = ws.operativeNotes || '';
    }
  } else {
    document.getElementById('ws-key').disabled = false;
  }
  modal.showModal();
}

document.getElementById('newWorkshopBtn').addEventListener('click', () => openWorkshopModal());

document.getElementById('saveWorkshopBtn').addEventListener('click', async () => {
  const body = {
    workshopKey: document.getElementById('ws-key').value.trim(),
    slug: document.getElementById('ws-key').value.trim(),
    title: document.getElementById('ws-title').value.trim(),
    startDate: document.getElementById('ws-startDate').value || null,
    endDate: document.getElementById('ws-endDate').value || null,
    priceCents: parseInt(document.getElementById('ws-price').value) || 0,
    totalSeats: parseInt(document.getElementById('ws-seats').value) || 8,
    availableSeats: parseInt(document.getElementById('ws-seats').value) || 8,
    cutoffAt: document.getElementById('ws-cutoff').value ? new Date(document.getElementById('ws-cutoff').value).toISOString() : null,
    status: document.getElementById('ws-status').value,
    location: document.getElementById('ws-location').value || null,
    description: document.getElementById('ws-description').value || null,
    operativeNotes: document.getElementById('ws-notes').value || null,
  };
  try {
    if (editingWorkshopId) {
      await api('PUT', `/api/admin/workshops/${editingWorkshopId}`, body);
    } else {
      await api('POST', '/api/admin/workshops/', body);
    }
    document.getElementById('workshopModal').close();
    showMsg('Workshop salvato con successo.', 'success');
    loadWorkshops();
  } catch (err) {
    showMsg('Errore: ' + err.message, 'error');
  }
});

sectionLoaders['workshops'] = loadWorkshops;

// ── PARTECIPANTI ─────────────────────────────────────────────────────────────

let allParticipants = [];

async function loadParticipants() {
  const wsFilter = document.getElementById('participantWorkshopFilter')?.value || '';
  const stFilter = document.getElementById('participantStatusFilter')?.value || '';
  let url = '/api/admin/participants/';
  const params = [];
  if (wsFilter) params.push('workshopId=' + encodeURIComponent(wsFilter));
  if (stFilter) params.push('status=' + encodeURIComponent(stFilter));
  if (params.length) url += '?' + params.join('&');

  try {
    const data = await api('GET', url);
    allParticipants = data?.participants || [];
    renderParticipants(allParticipants);
  } catch (err) {
    showMsg('Errore: ' + err.message, 'error');
  }
}

function renderParticipants(list) {
  const tbody = document.getElementById('participantsBody');
  if (!list.length) {
    tbody.innerHTML = '<tr><td colspan="9" class="table-empty">Nessun partecipante trovato.</td></tr>';
    return;
  }
  tbody.innerHTML = list.map(b => `
    <tr>
      <td><code style="font-size:.78rem">${escHtml(b.id)}</code></td>
      <td>${escHtml(b.firstName)} ${escHtml(b.lastName)}</td>
      <td style="max-width:180px;overflow:hidden;text-overflow:ellipsis">${escHtml(b.email)}</td>
      <td>${escHtml(b.workshopId || '—')}</td>
      <td>${escHtml(b.formula || '—')}${b.extraDay ? '<br><span style="color:var(--accent);font-size:.75rem">+ venerdì (€100)</span>' : ''}</td>
      <td>${formatEuro(b.finalCents)}</td>
      <td>${badge(b.status)}</td>
      <td>${b.balancePaid ? '<span style="color:var(--green)">✅ Pagato</span>' : '<span style="color:var(--text-muted)">—</span>'}</td>
      <td>
        <div style="display:flex;gap:.35rem">
          ${!b.balancePaid && b.status === 'paid' ? `<button class="btn-secondary btn-sm" onclick="markBalancePaid('${b.id}')">💳 Saldo</button>` : ''}
          <button class="btn-secondary btn-sm" onclick="openParticipantNotes('${b.id}')">📝 Note</button>
        </div>
      </td>
    </tr>
  `).join('');
}

function filterByWorkshop(wsId) {
  const sel = document.getElementById('participantWorkshopFilter');
  if (sel) sel.value = wsId;
  loadParticipants();
}

async function markBalancePaid(bookingId) {
  if (!await confirm2('Segnare il saldo come pagato? Metodo: Contanti')) return;
  try {
    await api('POST', `/api/admin/participants/${bookingId}/mark-balance-paid`, { method: 'contanti' });
    showMsg('Saldo segnato come pagato.', 'success');
    loadParticipants();
  } catch (err) {
    showMsg('Errore: ' + err.message, 'error');
  }
}

async function openParticipantNotes(bookingId) {
  const note = prompt('Note amministrative:');
  if (note === null) return;
  try {
    await api('PUT', `/api/admin/participants/${bookingId}`, { adminNotes: note });
    showMsg('Note aggiornate.', 'success');
    loadParticipants();
  } catch (err) {
    showMsg('Errore: ' + err.message, 'error');
  }
}

document.getElementById('participantWorkshopFilter')?.addEventListener('change', loadParticipants);
document.getElementById('participantStatusFilter')?.addEventListener('change', loadParticipants);

document.getElementById('exportParticipantsBtn')?.addEventListener('click', () => {
  const wsId = document.getElementById('participantWorkshopFilter')?.value || '';
  const filterType = document.getElementById('participantStatusFilter')?.value || 'all';
  const startDate = document.getElementById('participantStartDate')?.value || '';
  const endDate = document.getElementById('participantEndDate')?.value || '';

  const params = new URLSearchParams();
  if (wsId) params.append('workshopId', wsId);
  if (filterType) params.append('filterType', filterType);
  if (startDate) params.append('startDate', startDate);
  if (endDate) params.append('endDate', endDate);

  showMsg('Generazione export partecipanti in corso...', 'info', 2500);
  window.location.href = `/api/admin/participants/export?${params.toString()}`;
});

sectionLoaders['participants'] = loadParticipants;

// ── COUPON ───────────────────────────────────────────────────────────────────

let editingCouponId = null;
let allCoupons = [];

async function loadCoupons() {
  document.getElementById('couponsList').innerHTML = '<div class="skeleton" style="height:80px;border-radius:10px"></div>'.repeat(3);
  try {
    const data = await api('GET', '/api/admin/coupons/');
    allCoupons = data?.coupons || [];
    renderCoupons(allCoupons);
  } catch (err) {
    showMsg('Errore: ' + err.message, 'error');
  }
}

function renderCoupons(list) {
  const container = document.getElementById('couponsList');
  if (!list.length) { container.innerHTML = '<p style="color:var(--text-muted)">Nessun coupon.</p>'; return; }
  container.innerHTML = list.map(c => `
    <div class="card-item">
      <div class="card-item-header">
        <div>
          <div class="card-item-title"><code style="font-size:.9rem">${escHtml(c.code)}</code></div>
          <div style="font-size:.78rem;color:var(--text-muted);margin-top:.2rem">
            ${c.type === 'percentage' ? `${c.valueDecimal}% di sconto` : `Prezzo fisso €${c.valueDecimal}`}
            ${c.maxUsesTotal ? ` | ${c.usedCount}/${c.maxUsesTotal} utilizzi` : ''}
          </div>
        </div>
        ${badge(c.status)}
      </div>
      <div class="card-item-body">
        ${c.description ? escHtml(c.description) : '<em>Nessuna descrizione</em>'}
        ${c.endDate ? `<br>⏰ Scade: ${formatDate(c.endDate)}` : ''}
      </div>
      <div class="card-item-footer">
        <button class="btn-secondary btn-sm" onclick="openCouponModal(${c.id})">✏️ Modifica</button>
        <button class="btn-secondary btn-sm" onclick="toggleCouponStatus(${c.id}, '${c.status}')">
          ${c.status === 'active' ? '⏸️ Disattiva' : '▶️ Attiva'}
        </button>
        <button class="btn-danger btn-sm" onclick="deleteCoupon(${c.id})">🗑️</button>
      </div>
    </div>
  `).join('');
}

function openCouponModal(couponId = null) {
  editingCouponId = couponId;
  const modal = document.getElementById('couponModal');
  document.getElementById('couponModalTitle').textContent = couponId ? 'Modifica Coupon' : 'Nuovo Coupon';
  document.getElementById('couponForm').reset();
  document.getElementById('couponPreviewContent').textContent = 'Inserisci tipo e valore per vedere l\'anteprima.';

  if (couponId) {
    const c = allCoupons.find(x => x.id === couponId);
    if (c) {
      document.getElementById('cp-code').value = c.code;
      document.getElementById('cp-code').disabled = true;
      document.getElementById('cp-type').value = c.type;
      document.getElementById('cp-value').value = c.valueDecimal;
      document.getElementById('cp-maxUses').value = c.maxUsesTotal || '';
      document.getElementById('cp-startDate').value = c.startDate || '';
      document.getElementById('cp-endDate').value = c.endDate || '';
      document.getElementById('cp-desc').value = c.description || '';
    }
  } else {
    document.getElementById('cp-code').disabled = false;
  }
  modal.showModal();
}

document.getElementById('newCouponBtn').addEventListener('click', () => openCouponModal());

// Preview calcolo coupon
function updateCouponPreview() {
  const type = document.getElementById('cp-type').value;
  const value = document.getElementById('cp-value').value.trim();
  const preview = document.getElementById('couponPreviewContent');
  const exampleBase = 350;
  if (!value) { preview.textContent = 'Inserisci un valore.'; return; }
  const v = parseFloat(value.replace(',', '.'));
  if (isNaN(v) || v < 0) { preview.textContent = 'Valore non valido.'; return; }
  if (type === 'percentage') {
    if (v > 100) { preview.textContent = '⚠️ La percentuale non può superare 100%.'; return; }
    const discount = (exampleBase * v / 100).toFixed(2);
    const final = (exampleBase - parseFloat(discount)).toFixed(2);
    preview.innerHTML = `Su €${exampleBase}: sconto <strong>€${discount}</strong> → prezzo finale <strong>€${final}</strong>`;
  } else {
    if (v > exampleBase) { preview.innerHTML = `⚠️ Il prezzo finale (€${v}) è maggiore del prezzo base (€${exampleBase}).`; return; }
    const discount = (exampleBase - v).toFixed(2);
    preview.innerHTML = `Su €${exampleBase}: sconto <strong>€${discount}</strong> → prezzo finale <strong>€${v.toFixed(2)}</strong>`;
  }
}

document.getElementById('cp-type').addEventListener('change', updateCouponPreview);
document.getElementById('cp-value').addEventListener('input', updateCouponPreview);

document.getElementById('saveCouponBtn').addEventListener('click', async () => {
  const body = {
    code: document.getElementById('cp-code').value.trim().toUpperCase(),
    type: document.getElementById('cp-type').value,
    valueDecimal: document.getElementById('cp-value').value.trim().replace(',', '.'),
    description: document.getElementById('cp-desc').value.trim() || null,
    maxUsesTotal: parseInt(document.getElementById('cp-maxUses').value) || null,
    startDate: document.getElementById('cp-startDate').value || null,
    endDate: document.getElementById('cp-endDate').value || null,
  };
  try {
    if (editingCouponId) {
      await api('PUT', `/api/admin/coupons/${editingCouponId}`, body);
    } else {
      await api('POST', '/api/admin/coupons/', body);
    }
    document.getElementById('couponModal').close();
    showMsg('Coupon salvato.', 'success');
    loadCoupons();
  } catch (err) {
    showMsg('Errore: ' + err.message, 'error');
  }
});

async function toggleCouponStatus(id, current) {
  const newStatus = current === 'active' ? 'inactive' : 'active';
  try {
    await api('PUT', `/api/admin/coupons/${id}/status`, { status: newStatus });
    showMsg(`Coupon ${newStatus === 'active' ? 'attivato' : 'disattivato'}.`, 'success');
    loadCoupons();
  } catch (err) {
    showMsg('Errore: ' + err.message, 'error');
  }
}

async function deleteCoupon(id) {
  if (!await confirm2('Eliminare definitivamente questo coupon?')) return;
  try {
    await api('DELETE', `/api/admin/coupons/${id}`);
    showMsg('Coupon eliminato.', 'success');
    loadCoupons();
  } catch (err) {
    showMsg('Errore: ' + err.message, 'error');
  }
}

sectionLoaders['coupons'] = loadCoupons;

// ── COSTI ────────────────────────────────────────────────────────────────────

let currentCostWorkshopId = null;

async function loadCosts() {
  // Popola select workshop
  const sel = document.getElementById('costsWorkshopSelect');
  if (allWorkshops.length === 0) {
    await loadWorkshops();
  }
  sel.innerHTML = '<option value="">Seleziona un workshop...</option>' +
    allWorkshops.map(w => `<option value="${escAttr(w.workshopKey)}">${escHtml(w.title)}</option>`).join('');
}

document.getElementById('costsWorkshopSelect')?.addEventListener('change', async (e) => {
  const wsId = e.target.value;
  const panel = document.getElementById('costsPanel');
  if (!wsId) { panel.hidden = true; return; }
  currentCostWorkshopId = wsId;
  panel.hidden = false;
  await loadCostData(wsId);
  selectCostWorkshop(wsId);
});

function selectCostWorkshop(wsId) {
  const sel = document.getElementById('costsWorkshopSelect');
  if (sel) sel.value = wsId;
  currentCostWorkshopId = wsId;
  document.getElementById('costsPanel').hidden = false;
  loadCostData(wsId);
}

async function loadCostData(wsId) {
  try {
    const data = await api('GET', `/api/admin/costs/${wsId}`);
    if (!data) return;
    document.getElementById('cost-nights').value = data.nights || 0;
    document.getElementById('cost-nightRate').value = data.costPerNight || '0';
    document.getElementById('cost-rooms').value = data.roomCount || 1;
    document.getElementById('cost-departure').value = data.departureAddress || '';
    document.getElementById('cost-destination').value = data.destination || '';
    document.getElementById('cost-viamichelin').value = data.viamichelinUrl || '';
    document.getElementById('cost-fuel').value = data.fuel || '0';
    document.getElementById('cost-tolls').value = data.tolls || '0';
    document.getElementById('cost-parking').value = data.parking || '0';
    document.getElementById('cost-ferries').value = data.ferries || '0';
    document.getElementById('cost-otherTravel').value = data.otherTravel || '0';
    document.getElementById('cost-otherOrg').value = data.otherOrg || '0';
    document.getElementById('cost-notes').value = data.travelNotes || '';
    document.getElementById('cost-verifiedAt').value = data.verifiedAt ? data.verifiedAt.slice(0,10) : '';
    updateCostSummary(data);
  } catch (err) {
    showMsg('Errore caricamento costi: ' + err.message, 'error');
  }
}

function updateCostSummary(data) {
  const fmt = v => new Intl.NumberFormat('it-IT', {style:'currency', currency:'EUR'}).format(parseFloat(v || '0'));
  document.getElementById('sum-accomm').textContent = fmt(data.totalAccommodation);
  document.getElementById('sum-travel').textContent = fmt(data.totalTravel);
  document.getElementById('sum-other').textContent = fmt(data.otherOrg);
  document.getElementById('sum-total').textContent = fmt(data.totalCosts);
  document.getElementById('sum-cpp').textContent = fmt(data.costPerParticipant);
  const margin = parseFloat(data.estimatedMargin || '0');
  document.getElementById('sum-margin').textContent = fmt(data.estimatedMargin);
  document.getElementById('sum-margin').style.color = margin >= 0 ? 'var(--green)' : 'var(--red)';
}

// Live preview pernottamento
function calcAccomm() {
  const nights = parseFloat(document.getElementById('cost-nights').value) || 0;
  const rate = parseFloat(document.getElementById('cost-nightRate').value.replace(',', '.')) || 0;
  const rooms = parseFloat(document.getElementById('cost-rooms').value) || 1;
  const total = nights * rate * rooms;
  document.getElementById('totalAccomm').textContent = new Intl.NumberFormat('it-IT', {style:'currency', currency:'EUR'}).format(total);
}
['cost-nights', 'cost-nightRate', 'cost-rooms'].forEach(id => {
  document.getElementById(id)?.addEventListener('input', calcAccomm);
});

document.getElementById('openViaMichelinBtn')?.addEventListener('click', () => {
  const url = document.getElementById('cost-viamichelin').value.trim();
  if (url) {
    window.open(url, '_blank', 'noopener,noreferrer');
  } else {
    window.open('https://www.viamichelin.it/', '_blank', 'noopener,noreferrer');
  }
});

document.getElementById('saveCostsBtn')?.addEventListener('click', async () => {
  if (!currentCostWorkshopId) return;
  const body = {
    nights: parseInt(document.getElementById('cost-nights').value) || 0,
    costPerNight: document.getElementById('cost-nightRate').value.replace(',', '.') || '0',
    roomCount: parseInt(document.getElementById('cost-rooms').value) || 1,
    departureAddress: document.getElementById('cost-departure').value.trim() || null,
    destination: document.getElementById('cost-destination').value.trim() || null,
    viamichelinUrl: document.getElementById('cost-viamichelin').value.trim() || null,
    fuel: document.getElementById('cost-fuel').value.replace(',', '.') || '0',
    tolls: document.getElementById('cost-tolls').value.replace(',', '.') || '0',
    parking: document.getElementById('cost-parking').value.replace(',', '.') || '0',
    ferries: document.getElementById('cost-ferries').value.replace(',', '.') || '0',
    otherTravel: document.getElementById('cost-otherTravel').value.replace(',', '.') || '0',
    otherOrg: document.getElementById('cost-otherOrg').value.replace(',', '.') || '0',
    travelNotes: document.getElementById('cost-notes').value || null,
    verifiedAt: document.getElementById('cost-verifiedAt').value || null,
  };
  try {
    const data = await api('PUT', `/api/admin/costs/${currentCostWorkshopId}`, body);
    updateCostSummary(data);
    showMsg('Costi salvati e calcolati.', 'success');
  } catch (err) {
    showMsg('Errore: ' + err.message, 'error');
  }
});

sectionLoaders['costs'] = loadCosts;

// ── REPORT ───────────────────────────────────────────────────────────────────

async function loadReports() {
  const wsFilter = document.getElementById('reportWorkshopFilter')?.value || '';
  let url = '/api/admin/reports/';
  if (wsFilter) url += `?workshopId=${encodeURIComponent(wsFilter)}`;
  try {
    const data = await api('GET', url);
    const reports = data?.reports || [];
    const container = document.getElementById('reportsList');
    if (!reports.length) { container.innerHTML = '<p style="color:var(--text-muted)">Nessun report disponibile.</p>'; return; }
    container.innerHTML = reports.map(r => `
      <div class="report-item" role="article">
        <div class="report-item-info">
          <div class="report-item-title">📊 Report v${r.version} — ${escHtml(r.workshopId)}</div>
          <div class="report-item-meta">
            ${formatDateTime(r.generatedAt)} | ${r.participantCount ?? '—'} partecipanti
            ${r.isCutoffSnapshot ? ' | <strong>Snapshot Cutoff</strong>' : ''}
          </div>
        </div>
        <div class="report-item-actions">
          <a href="/api/admin/reports/${r.id}/download" class="btn-secondary btn-sm"
             download aria-label="Scarica report ${r.id}">
            📥 Scarica XLSX
          </a>
        </div>
      </div>
    `).join('');
  } catch (err) {
    showMsg('Errore: ' + err.message, 'error');
  }
}

async function generateReport(wsId) {
  const targetId = wsId || document.getElementById('reportWorkshopFilter')?.value;
  if (!targetId) { showMsg('Seleziona un workshop.', 'info'); return; }
  try {
    const data = await api('POST', `/api/admin/reports/${targetId}/generate`, { force: true });
    showMsg(`Report generato! ${data.participantCount} partecipanti.`, 'success');
    loadReports();
  } catch (err) {
    showMsg('Errore: ' + err.message, 'error');
  }
}

document.getElementById('generateReportBtn')?.addEventListener('click', () => generateReport());
document.getElementById('reportWorkshopFilter')?.addEventListener('change', loadReports);
sectionLoaders['reports'] = loadReports;

// ── AUDIT LOG ────────────────────────────────────────────────────────────────

async function loadLogs() {
  try {
    const data = await api('GET', '/api/admin/logs/audit?limit=100');
    const logs = data?.logs || [];
    const tbody = document.getElementById('logsBody');
    if (!logs.length) { tbody.innerHTML = '<tr><td colspan="5" class="table-empty">Nessuna voce nel log.</td></tr>'; return; }
    tbody.innerHTML = logs.map(l => `
      <tr>
        <td style="white-space:nowrap;font-size:.78rem">${formatDateTime(l.timestamp)}</td>
        <td>${l.userId || '—'}</td>
        <td><code style="font-size:.78rem">${escHtml(l.action)}</code></td>
        <td>${escHtml(l.resourceType || '')} ${l.resourceId ? '#' + escHtml(l.resourceId) : ''}</td>
        <td style="font-size:.78rem;color:var(--text-muted)">${escHtml(l.ip || '—')}</td>
      </tr>
    `).join('');
  } catch (err) {
    showMsg('Errore caricamento log: ' + err.message, 'error');
  }
}

document.getElementById('logSearch')?.addEventListener('input', debounce(async (e) => {
  const q = e.target.value.trim();
  const url = q ? `/api/admin/logs/audit?action=${encodeURIComponent(q)}&limit=100` : '/api/admin/logs/audit?limit=100';
  try {
    const data = await api('GET', url);
    // re-render filtrato
    sectionLoaders['logs'] = () => {};  // blocca reload automatico
    const logs = data?.logs || [];
    const tbody = document.getElementById('logsBody');
    tbody.innerHTML = logs.map(l => `
      <tr>
        <td style="white-space:nowrap;font-size:.78rem">${formatDateTime(l.timestamp)}</td>
        <td>${l.userId || '—'}</td>
        <td><code style="font-size:.78rem">${escHtml(l.action)}</code></td>
        <td>${escHtml(l.resourceType || '')} ${l.resourceId ? '#' + escHtml(l.resourceId) : ''}</td>
        <td style="font-size:.78rem;color:var(--text-muted)">${escHtml(l.ip || '—')}</td>
      </tr>
    `).join('') || '<tr><td colspan="5" class="table-empty">Nessun risultato.</td></tr>';
  } catch {}
}, 400));

sectionLoaders['logs'] = loadLogs;

// ── MEDIA ─────────────────────────────────────────────────────────────────────

async function loadMedia() {
  try {
    const data = await api('GET', '/api/admin/media/');
    const media = data?.media || [];
    const grid = document.getElementById('mediaGrid');
    if (!media.length) { grid.innerHTML = '<p style="color:var(--text-muted)">Nessun media. Carica la prima immagine.</p>'; return; }
    grid.innerHTML = media.map(m => `
      <div class="media-card" tabindex="0" aria-label="${escAttr(m.altText || m.originalFilename)}">
        <img
          class="media-thumb"
          src="${escAttr(m.webpPath ? '/' + m.webpPath : '/assets/upload/' + m.storedFilename + '_480w.webp')}"
          alt="${escAttr(m.altText || '')}"
          loading="lazy"
          width="160" height="120"
        >
        <div class="media-info">
          <div class="media-name">${escHtml(m.originalFilename)}</div>
          <div>${m.width && m.height ? m.width + '×' + m.height : ''} ${m.fileSizeBytes ? '· ' + (m.fileSizeBytes/1024).toFixed(0) + 'KB' : ''}</div>
          ${m.altText ? '' : '<div style="color:var(--orange);font-size:.68rem">⚠️ Alt text mancante</div>'}
        </div>
      </div>
    `).join('');
  } catch (err) {
    showMsg('Errore caricamento media: ' + err.message, 'error');
  }
}

document.getElementById('mediaUploadInput')?.addEventListener('change', async (e) => {
  const file = e.target.files[0];
  if (!file) return;
  const progress = document.getElementById('uploadProgress');
  const fill = document.getElementById('progressFill');
  const status = document.getElementById('uploadStatus');
  progress.hidden = false;
  fill.style.width = '30%';
  status.textContent = `Caricamento: ${file.name}...`;

  const fd = new FormData();
  fd.append('file', file);
  fd.append('altText', '');
  fd.append('pageTag', 'general');

  try {
    fill.style.width = '70%';
    const data = await api('POST', '/api/admin/media/upload', fd, true);
    fill.style.width = '100%';
    if (data.status === 'duplicate') {
      showMsg('Immagine già presente nella libreria.', 'info');
    } else {
      showMsg('Immagine caricata con successo!', 'success');
    }
    loadMedia();
  } catch (err) {
    showMsg('Errore upload: ' + err.message, 'error');
  } finally {
    setTimeout(() => { progress.hidden = true; fill.style.width = '0'; }, 2000);
    e.target.value = '';
  }
});

sectionLoaders['media'] = loadMedia;

// ── CRM CONTATTI ─────────────────────────────────────────────────────────────

let allContacts = [];
let editingContactId = null;
let csvParsedPreview = null;

async function loadCrm() {
  const tbody = document.getElementById('crmBody');
  if (tbody) tbody.innerHTML = '<tr><td colspan="8" class="table-empty">Caricamento contatti CRM...</td></tr>';
  
  const search = document.getElementById('crmSearchInput')?.value || '';
  const status = document.getElementById('crmStatusFilter')?.value || '';
  const priority = document.getElementById('crmPriorityFilter')?.value || '';
  const followup = document.getElementById('crmFollowupFilter')?.value || '';
  const isBlacklist = document.getElementById('crmBlacklistFilter')?.value || '';

  const params = new URLSearchParams();
  if (search) params.append('search', search);
  if (status) params.append('status', status);
  if (priority) params.append('priority', priority);
  if (followup) params.append('followupFilter', followup);
  if (isBlacklist) params.append('isBlacklisted', isBlacklist);

  try {
    const data = await api('GET', `/api/admin/crm/contacts?${params.toString()}`);
    allContacts = data?.contacts || [];
    renderCrm(allContacts);
  } catch (err) {
    showMsg('Errore CRM: ' + err.message, 'error');
  }
}

function renderCrm(list) {
  const tbody = document.getElementById('crmBody');
  if (!tbody) return;
  if (!list.length) {
    tbody.innerHTML = '<tr><td colspan="8" class="table-empty">Nessun contatto trovato.</td></tr>';
    return;
  }

  const priorityBadges = {
    urgent: '<span class="badge" style="background:rgba(239,68,68,0.2);color:var(--red)">🔴 Urgente</span>',
    high: '<span class="badge" style="background:rgba(249,115,22,0.2);color:var(--orange)">🟠 Alta</span>',
    medium: '<span class="badge" style="background:rgba(234,179,8,0.2);color:var(--yellow)">🟡 Media</span>',
    low: '<span class="badge" style="background:rgba(34,197,94,0.2);color:var(--green)">🟢 Bassa</span>',
  };

  tbody.innerHTML = list.map(c => `
    <tr>
      <td>
        <strong>${escHtml(c.fullName)}</strong>
        ${c.isBlacklisted ? '<br><span style="color:var(--red);font-size:.75rem">⛔ In Blacklist</span>' : ''}
      </td>
      <td>
        <div>${escHtml(c.email)}</div>
        <div style="font-size:.78rem;color:var(--text-muted)">${escHtml(c.phone || '—')}</div>
      </td>
      <td>
        ${badge(c.status)} ${priorityBadges[c.priority] || ''}
      </td>
      <td><span style="font-size:.8rem;color:var(--text-muted)">${escHtml(c.firstSource || '—')}</span></td>
      <td>${formatDate(c.lastContactAt)}</td>
      <td>${c.nextFollowupAt ? `<strong style="color:var(--accent)">${formatDate(c.nextFollowupAt)}</strong>` : '—'}</td>
      <td><strong>${c.totalSpentLabel}</strong></td>
      <td>
        <button class="btn-secondary btn-sm" onclick="openContactModal(${c.id})">🔍 Scheda</button>
      </td>
    </tr>
  `).join('');
}

async function openContactModal(contactId = null) {
  editingContactId = contactId;
  const modal = document.getElementById('contactModal');
  const title = document.getElementById('contactModalTitle');

  if (!contactId) {
    title.textContent = 'Nuovo Contatto';
    document.getElementById('cnt-firstName').value = '';
    document.getElementById('cnt-lastName').value = '';
    document.getElementById('cnt-email').value = '';
    document.getElementById('cnt-phone').value = '';
    document.getElementById('cnt-status').value = 'new_lead';
    document.getElementById('cnt-priority').value = 'medium';
    document.getElementById('cnt-followup').value = '';
    document.getElementById('cnt-country').value = 'IT';
    document.getElementById('cnt-tags').value = '';
    document.getElementById('cnt-notes').value = '';
    document.getElementById('contactInteractionsTimeline').innerHTML = '<p style="color:var(--text-muted)">Le interazioni verranno registrate dopo la creazione.</p>';
    document.getElementById('toggleBlacklistBtn').style.display = 'none';
  } else {
    title.textContent = 'Scheda Contatto CRM';
    document.getElementById('toggleBlacklistBtn').style.display = 'inline-block';
    try {
      const c = await api('GET', `/api/admin/crm/contacts/${contactId}`);
      document.getElementById('cnt-firstName').value = c.firstName || '';
      document.getElementById('cnt-lastName').value = c.lastName || '';
      document.getElementById('cnt-email').value = c.email || '';
      document.getElementById('cnt-phone').value = c.phone || '';
      document.getElementById('cnt-status').value = c.status || 'new_lead';
      document.getElementById('cnt-priority').value = c.priority || 'medium';
      document.getElementById('cnt-followup').value = c.nextFollowupAt ? c.nextFollowupAt.slice(0, 10) : '';
      document.getElementById('cnt-country').value = c.country || 'IT';
      document.getElementById('cnt-tags').value = (c.tags || []).map(t => t.label).join(', ');
      document.getElementById('cnt-notes').value = c.notes || '';

      const tl = document.getElementById('contactInteractionsTimeline');
      const interactions = c.interactions || [];
      if (!interactions.length) {
        tl.innerHTML = '<p style="color:var(--text-muted)">Nessuna interazione registrata.</p>';
      } else {
        tl.innerHTML = interactions.map(i => `
          <div style="padding:.5rem 0;border-bottom:1px solid var(--border)">
            <div style="display:flex;justify-content:space-between;color:var(--text-muted);font-size:.75rem">
              <span><strong>${escHtml(i.type.toUpperCase())}</strong> · ${escHtml(i.adminUserName || 'Sistema')}</span>
              <span>${formatDateTime(i.createdAt)}</span>
            </div>
            <div style="margin-top:.2rem">${escHtml(i.note || i.subject)}</div>
          </div>
        `).join('');
      }

      document.getElementById('toggleBlacklistBtn').textContent = c.isBlacklisted ? '✅ Rimuovi da Blacklist' : '⛔ Inserisci in Blacklist';
      document.getElementById('toggleBlacklistBtn').dataset.blacklisted = String(c.isBlacklisted);
    } catch (err) {
      showMsg('Errore apertura contatto: ' + err.message, 'error');
    }
  }

  modal.showModal();
}

document.getElementById('newContactBtn')?.addEventListener('click', () => openContactModal(null));
document.getElementById('crmSearchInput')?.addEventListener('input', debounce(loadCrm, 350));
document.getElementById('crmStatusFilter')?.addEventListener('change', loadCrm);
document.getElementById('crmPriorityFilter')?.addEventListener('change', loadCrm);
document.getElementById('crmFollowupFilter')?.addEventListener('change', loadCrm);
document.getElementById('crmBlacklistFilter')?.addEventListener('change', loadCrm);

document.getElementById('saveContactBtn')?.addEventListener('click', async () => {
  const payload = {
    firstName: document.getElementById('cnt-firstName').value.trim(),
    lastName: document.getElementById('cnt-lastName').value.trim(),
    email: document.getElementById('cnt-email').value.trim(),
    phone: document.getElementById('cnt-phone').value.trim(),
    status: document.getElementById('cnt-status').value,
    priority: document.getElementById('cnt-priority').value,
    nextFollowupAt: document.getElementById('cnt-followup').value || null,
    country: document.getElementById('cnt-country').value.trim() || 'IT',
    notes: document.getElementById('cnt-notes').value.trim(),
    tags: document.getElementById('cnt-tags').value.split(',').map(t => t.trim()).filter(Boolean),
  };

  if (!payload.firstName || !payload.email) {
    showMsg('Nome ed Email sono obbligatori.', 'error');
    return;
  }

  try {
    if (editingContactId) {
      await api('PUT', `/api/admin/crm/contacts/${editingContactId}`, payload);
      showMsg('Contatto aggiornato con successo!', 'success');
    } else {
      await api('POST', '/api/admin/crm/contacts', payload);
      showMsg('Contatto creato con successo!', 'success');
    }
    document.getElementById('contactModal').close();
    loadCrm();
  } catch (err) {
    showMsg('Errore salvataggio: ' + err.message, 'error');
  }
});

document.getElementById('addInteractionBtn')?.addEventListener('click', async () => {
  if (!editingContactId) return;
  const note = document.getElementById('newIntNote').value.trim();
  const type = document.getElementById('newIntType').value;
  if (!note) { showMsg('Inserisci una nota.', 'info'); return; }

  try {
    await api('POST', `/api/admin/crm/contacts/${editingContactId}/interactions`, { type, note });
    document.getElementById('newIntNote').value = '';
    showMsg('Interazione registrata.', 'success');
    openContactModal(editingContactId);
  } catch (err) {
    showMsg('Errore: ' + err.message, 'error');
  }
});

document.getElementById('toggleBlacklistBtn')?.addEventListener('click', async () => {
  if (!editingContactId) return;
  const currentlyBlacklisted = document.getElementById('toggleBlacklistBtn').dataset.blacklisted === 'true';
  const reason = prompt(currentlyBlacklisted ? 'Confermi la rimozione dalla blacklist?' : 'Motivo inserimento in blacklist:');
  if (reason === null) return;

  try {
    await api('POST', `/api/admin/crm/contacts/${editingContactId}/blacklist`, {
      isBlacklisted: !currentlyBlacklisted,
      reason: reason || 'N/A'
    });
    showMsg(!currentlyBlacklisted ? 'Contatto inserito in blacklist.' : 'Contatto rimosso da blacklist.', 'info');
    openContactModal(editingContactId);
    loadCrm();
  } catch (err) {
    showMsg('Errore: ' + err.message, 'error');
  }
});

// CSV Export & Import
document.getElementById('crmExportCsvBtn')?.addEventListener('click', () => {
  const search = document.getElementById('crmSearchInput')?.value || '';
  const status = document.getElementById('crmStatusFilter')?.value || '';
  const params = new URLSearchParams();
  if (search) params.append('search', search);
  if (status) params.append('status', status);
  window.location.href = `/api/admin/crm/contacts/export?${params.toString()}`;
});

document.getElementById('crmImportCsvBtn')?.addEventListener('click', () => {
  document.getElementById('csvStep1').style.display = 'block';
  document.getElementById('csvStep2').style.display = 'none';
  document.getElementById('csvNextStepBtn').style.display = 'inline-block';
  document.getElementById('csvConfirmImportBtn').style.display = 'none';
  document.getElementById('csvFileInput').value = '';
  document.getElementById('csvImportModal').showModal();
});

document.getElementById('csvNextStepBtn')?.addEventListener('click', async () => {
  const fileInput = document.getElementById('csvFileInput');
  if (!fileInput.files.length) { showMsg('Seleziona un file CSV.', 'info'); return; }

  const fd = new FormData();
  fd.append('file', fileInput.files[0]);

  try {
    const preview = await api('POST', '/api/admin/crm/contacts/import-preview', fd, true);
    csvParsedPreview = preview;

    document.getElementById('csvPreviewSummary').textContent = `Rilevate ${preview.totalRows} righe con delimitatore '${preview.delimiter}'.`;
    
    // Griglia mappatura
    const grid = document.getElementById('csvMappingGrid');
    const fields = [
      { id: 'email', label: 'Email *' },
      { id: 'first_name', label: 'Nome' },
      { id: 'last_name', label: 'Cognome' },
      { id: 'phone', label: 'Telefono' },
      { id: 'status', label: 'Stato Commerciale' },
      { id: 'notes', label: 'Note' },
      { id: 'tags', label: 'Tag' },
      { id: 'next_followup_at', label: 'Data Follow-up' },
    ];

    grid.innerHTML = fields.map(f => {
      const suggestedIdx = preview.mappingSuggestions ? preview.mappingSuggestions[f.id] : undefined;
      const opts = preview.headers.map((h, i) => `<option value="${i}" ${suggestedIdx === i ? 'selected' : ''}>Colonna: ${escHtml(h)}</option>`).join('');
      return `
        <div class="form-group">
          <label>${f.label}</label>
          <select id="map-${f.id}">
            <option value="">— Non mappare —</option>
            ${opts}
          </select>
        </div>
      `;
    }).join('');

    document.getElementById('csvStep1').style.display = 'none';
    document.getElementById('csvStep2').style.display = 'block';
    document.getElementById('csvNextStepBtn').style.display = 'none';
    document.getElementById('csvConfirmImportBtn').style.display = 'inline-block';
  } catch (err) {
    showMsg('Errore analisi CSV: ' + err.message, 'error');
  }
});

document.getElementById('csvConfirmImportBtn')?.addEventListener('click', async () => {
  const fileInput = document.getElementById('csvFileInput');
  if (!fileInput.files.length) return;

  const mapping = {};
  ['email', 'first_name', 'last_name', 'phone', 'status', 'notes', 'tags', 'next_followup_at'].forEach(k => {
    const val = document.getElementById(`map-${k}`)?.value;
    if (val !== '' && val !== undefined) mapping[k] = parseInt(val, 10);
  });

  const fd = new FormData();
  fd.append('file', fileInput.files[0]);
  fd.append('mappingJson', JSON.stringify(mapping));
  fd.append('duplicateStrategy', document.getElementById('csvDuplicateStrategy').value);

  try {
    const res = await api('POST', '/api/admin/crm/contacts/import-confirm', fd, true);
    showMsg(`Importazione completata: ${res.created} creati, ${res.updated} aggiornati, ${res.skipped} saltati.`, 'success', 5000);
    document.getElementById('csvImportModal').close();
    loadCrm();
  } catch (err) {
    showMsg('Errore importazione: ' + err.message, 'error');
  }
});

sectionLoaders['crm'] = loadCrm;

// ── VIDEO & MEDIA ─────────────────────────────────────────────────────────────

document.getElementById('openVideoUploadBtn')?.addEventListener('click', () => {
  document.getElementById('vidFile').value = '';
  document.getElementById('vidAlt').value = '';
  document.getElementById('videoUploadModal').showModal();
});

document.getElementById('confirmUploadVideoBtn')?.addEventListener('click', async () => {
  const fileInput = document.getElementById('vidFile');
  if (!fileInput.files.length) { showMsg('Seleziona un file video.', 'info'); return; }

  const fd = new FormData();
  fd.append('file', fileInput.files[0]);
  fd.append('altText', document.getElementById('vidAlt').value.trim());

  try {
    const res = await api('POST', '/api/admin/media/upload-video', fd, true);
    showMsg('Video caricato. Elaborazione H.264/WebP avviata in background!', 'success');
    document.getElementById('videoUploadModal').close();
    loadMedia();
  } catch (err) {
    showMsg('Errore caricamento video: ' + err.message, 'error');
  }
});

// ── SICUREZZA & BACKUP ────────────────────────────────────────────────────────

async function loadSecurity() {
  try {
    const [sessionsData, backupsData] = await Promise.all([
      api('GET', '/api/admin/auth/sessions'),
      api('GET', '/api/admin/backups/'),
    ]);

    // Render sessioni
    const sessions = sessionsData?.sessions || [];
    const sessContainer = document.getElementById('sessionsList');
    if (sessContainer) {
      sessContainer.innerHTML = sessions.map(s => `
        <div style="display:flex;justify-content:space-between;padding:.5rem 0;border-bottom:1px solid var(--border);font-size:.85rem">
          <div>
            <strong>${s.isCurrent ? '🟢 Sessione Corrente' : 'Dispositivo'}</strong> (${escHtml(s.ip)})
            <div style="font-size:.75rem;color:var(--text-muted)">Ultima attività: ${formatDateTime(s.lastActivity)}</div>
          </div>
          <div>${s.isCurrent ? '<span class="badge badge-active">Attiva</span>' : ''}</div>
        </div>
      `).join('') || '<p style="color:var(--text-muted)">Nessuna sessione attiva</p>';
    }

    // Render backup
    const backups = backupsData?.backups || [];
    const tbody = document.getElementById('backupsBody');
    if (tbody) {
      tbody.innerHTML = backups.map(b => `
        <tr>
          <td><code>${escHtml(b.filename)}</code></td>
          <td>${formatDateTime(b.modifiedAt)}</td>
          <td>${escHtml(b.sizeFormatted)}</td>
          <td>
            <a href="/api/admin/backups/${escAttr(b.filename)}/download" class="btn-secondary btn-sm" download>📥 Scarica</a>
          </td>
        </tr>
      `).join('') || '<tr><td colspan="4" class="table-empty">Nessun backup trovato.</td></tr>';
    }
  } catch (err) {
    showMsg('Errore sicurezza: ' + err.message, 'error');
  }
}

document.getElementById('generateRecoveryCodesBtn')?.addEventListener('click', async () => {
  if (!await confirm2('Generare una nuova serie di 8 codici di recupero monouso?')) return;
  try {
    const res = await api('POST', '/api/admin/auth/generate-recovery-codes');
    const disp = document.getElementById('recoveryCodesDisplay');
    disp.style.display = 'block';
    disp.innerHTML = `
      <h4 style="color:var(--accent);margin-bottom:.5rem">Codici di Recupero (Salvali Adesso):</h4>
      <div style="display:grid;grid-template-columns:1fr 1fr;gap:.5rem;font-family:monospace;font-size:1.1rem;font-weight:700">
        ${res.codes.map(c => `<div>${c}</div>`).join('')}
      </div>
      <p style="font-size:.75rem;color:var(--text-muted);margin-top:.75rem">Ciascun codice può essere usato una sola volta per accedere in caso di mancata ricezione dell'OTP via email.</p>
    `;
  } catch (err) {
    showMsg('Errore generazione codici: ' + err.message, 'error');
  }
});

document.getElementById('revokeOtherSessionsBtn')?.addEventListener('click', async () => {
  if (!await confirm2('Revocare tutte le altre sessioni attive?')) return;
  try {
    await api('DELETE', '/api/admin/auth/sessions');
    showMsg('Tutte le altre sessioni sono state revocate.', 'success');
    loadSecurity();
  } catch (err) {
    showMsg('Errore: ' + err.message, 'error');
  }
});

document.getElementById('triggerBackupNowBtn')?.addEventListener('click', async () => {
  showMsg('Creazione copia atomica database in corso...', 'info', 2000);
  try {
    const res = await api('POST', '/api/admin/backups/create');
    showMsg(`Backup creato con successo! (${res.backup.filename} - ${res.backup.sizeFormatted})`, 'success');
    loadSecurity();
  } catch (err) {
    showMsg('Errore backup: ' + err.message, 'error');
  }
});

sectionLoaders['security'] = loadSecurity;

// ── SETTINGS ─────────────────────────────────────────────────────────────────

document.getElementById('changePasswordForm')?.addEventListener('submit', async (e) => {
  e.preventDefault();
  const curr = document.getElementById('curr-pass').value;
  const next = document.getElementById('new-pass').value;
  if (next.length < 12) { showMsg('La nuova password deve avere almeno 12 caratteri.', 'error'); return; }
  try {
    await api('POST', '/api/admin/auth/change-password', { current_password: curr, new_password: next });
    showMsg('Password aggiornata. Effettua nuovamente il login.', 'success');
    setTimeout(() => window.location.href = '/admin/index.html', 2000);
  } catch (err) {
    showMsg('Errore: ' + err.message, 'error');
  }
});

// Indicatore forza password
document.getElementById('new-pass')?.addEventListener('input', (e) => {
  const v = e.target.value;
  const hint = document.getElementById('pass-strength');
  if (!hint) return;
  if (!v) { hint.textContent = ''; return; }
  const score = [v.length >= 12, /[A-Z]/.test(v), /[0-9]/.test(v), /[^A-Za-z0-9]/.test(v)].filter(Boolean).length;
  const labels = ['', '⚠️ Debole', '⚠️ Debole', '👍 Accettabile', '✅ Forte'];
  const colors = ['', 'var(--red)', 'var(--orange)', 'var(--yellow)', 'var(--green)'];
  hint.textContent = labels[score];
  hint.style.color = colors[score];
});

// ── Dialog conferma ───────────────────────────────────────────────────────────

function confirm2(message) {
  return new Promise(resolve => {
    const dialog = document.getElementById('confirmDialog');
    document.getElementById('confirmMessage').textContent = message;
    document.getElementById('confirmOk').onclick = () => { dialog.close(); resolve(true); };
    document.getElementById('confirmCancel').onclick = () => { dialog.close(); resolve(false); };
    dialog.showModal();
  });
}

// ── Escape utils ─────────────────────────────────────────────────────────────

function escHtml(str) {
  if (str == null) return '';
  return String(str).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
}
function escAttr(str) {
  return escHtml(str);
}

// ── Debounce ─────────────────────────────────────────────────────────────────

function debounce(fn, ms) {
  let t;
  return function(...args) {
    clearTimeout(t);
    t = setTimeout(() => fn.apply(this, args), ms);
  };
}

// ── Helpers comuni ────────────────────────────────────────────────────────────

function populateWorkshopSelects(workshops) {
  ['participantWorkshopFilter', 'reportWorkshopFilter'].forEach(id => {
    const sel = document.getElementById(id);
    if (!sel) return;
    const curr = sel.value;
    const opts = workshops.map(w => `<option value="${escAttr(w.workshopKey)}">${escHtml(w.title)}</option>`).join('');
    sel.innerHTML = `<option value="">Tutti i workshop</option>${opts}`;
    if (curr) sel.value = curr;
  });
}

// ── Event listeners globali ───────────────────────────────────────────────────

// Nav sidebar
document.querySelectorAll('.nav-item').forEach(link => {
  link.addEventListener('click', (e) => {
    e.preventDefault();
    const section = link.dataset.section;
    navigate(section);
    // Chiudi sidebar su mobile
    if (window.innerWidth < 900) {
      document.getElementById('sidebar').classList.remove('open');
      document.getElementById('menuToggle').setAttribute('aria-expanded', 'false');
    }
  });
});

// Menu toggle mobile
document.getElementById('menuToggle')?.addEventListener('click', () => {
  const sidebar = document.getElementById('sidebar');
  const expanded = sidebar.classList.toggle('open');
  document.getElementById('menuToggle').setAttribute('aria-expanded', String(expanded));
});

// Logout
document.getElementById('logoutBtn')?.addEventListener('click', async () => {
  await api('POST', '/api/admin/auth/logout');
  window.location.href = '/admin/index.html';
});

// Refresh
document.getElementById('refreshBtn')?.addEventListener('click', () => {
  const active = document.querySelector('.section.active');
  if (active) {
    const id = active.id.replace('section-', '');
    if (sectionLoaders[id]) sectionLoaders[id]();
  }
});

// Keyboard: ESC chiude modali
document.addEventListener('keydown', (e) => {
  if (e.key === 'Escape') {
    document.querySelectorAll('dialog[open]').forEach(d => {
      if (!d.classList.contains('confirm-modal')) d.close();
    });
  }
});

// ── Avvio ─────────────────────────────────────────────────────────────────────

(async function init() {
  await initUser();

  // Route da hash o default dashboard
  const hash = window.location.hash.replace('#', '') || 'dashboard';
  navigate(hash);

  window.addEventListener('hashchange', () => {
    const section = window.location.hash.replace('#', '');
    if (section) navigate(section);
  });
})();
