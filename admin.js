/* ==========================================================================
   Davide Luongo — Elementor-Style Admin CMS Client Logic
   ========================================================================== */

let globalData = {};
let activePage = 'page-home';

document.addEventListener('DOMContentLoaded', () => {
  fetchContent();
  setupSaveButton();
  setupEntityModal();
  setupDropzone();
});

// Fetch current data from server API
function fetchContent() {
  fetch('/api/content')
    .then(res => res.json())
    .then(data => {
      globalData = data;
      renderActivePageEditor();
    })
    .catch(err => {
      console.error('Error fetching content:', err);
    });
}

// Tree view page node selector
function selectPageNode(pageId) {
  activePage = pageId;

  // Highlight active tree page title
  document.querySelectorAll('.tree-page-title').forEach(el => el.classList.remove('active'));
  document.querySelectorAll('.tree-sub-item').forEach(el => el.classList.remove('active'));

  // Toggle sub-list dropdowns
  document.querySelectorAll('.tree-sub-list').forEach(list => list.style.display = 'none');
  
  const selectedNode = event ? event.currentTarget : null;
  if (selectedNode) {
    selectedNode.classList.add('active');
    const subList = selectedNode.nextElementSibling;
    if (subList) subList.style.display = 'flex';
  }

  // Update Page Title
  const titles = {
    'page-home': '🏠 Home Page (index.html)',
    'page-friuli': '🏞️ Workshop Friuli 2026 (workshops_2026/friuli-2026.html)',
    'page-cascate': '💧 Workshop Cascate Appennino 2026 (workshops_2026/cascate-appennino-2026.html)',
    'page-canfaito': '🍂 Workshop Faggeta di Canfaito 2026 (workshops_2026/canfaito-2026.html)',
    'page-casentinesi': '🌲 Workshop Foreste Casentinesi 2026 (workshops_2026/foreste-casentinesi-2026.html)',
    'page-gear': '📷 Pagina Gear & Attrezzatura (gear/gear.html)',
    'page-blog': '📰 Pagina Blog & Pubblicazioni (blog/blog.html)',
    'page-participants': '📊 Lista Partecipanti & Export Report Excel',
    'page-coupons': '🎟️ Gestione & Generatore Codici Sconto'
  };

  const titleEl = document.getElementById('active-page-title');
  if (titleEl) titleEl.innerText = titles[pageId] || pageId;

  renderActivePageEditor();
}

// Scroll directly to a specific section card
function scrollToSection(sectionId) {
  const target = document.getElementById(sectionId);
  if (target) {
    target.scrollIntoView({ behavior: 'smooth', block: 'start' });
    target.style.borderColor = 'var(--accent-cyan)';
    setTimeout(() => {
      target.style.borderColor = 'var(--border-glass)';
    }, 2000);
  }
}

// Render property inspector editor based on selected page
function renderActivePageEditor() {
  const panelHome = document.getElementById('panel-page-home');
  const panelGeneric = document.getElementById('panel-page-generic');
  const panelParticipants = document.getElementById('panel-page-participants');
  const panelCoupons = document.getElementById('panel-page-coupons');

  if (activePage === 'page-home') {
    if (panelHome) panelHome.style.display = 'block';
    if (panelGeneric) panelGeneric.style.display = 'none';
    if (panelParticipants) panelParticipants.style.display = 'none';
    if (panelCoupons) panelCoupons.style.display = 'none';
    renderHomeEditor();
  } else if (activePage === 'page-participants') {
    if (panelHome) panelHome.style.display = 'none';
    if (panelGeneric) panelGeneric.style.display = 'none';
    if (panelParticipants) panelParticipants.style.display = 'block';
    if (panelCoupons) panelCoupons.style.display = 'none';
    renderParticipantsEditor();
  } else if (activePage === 'page-coupons') {
    if (panelHome) panelHome.style.display = 'none';
    if (panelGeneric) panelGeneric.style.display = 'none';
    if (panelParticipants) panelParticipants.style.display = 'none';
    if (panelCoupons) panelCoupons.style.display = 'block';
    renderCouponsEditor();
  } else {
    if (panelHome) panelHome.style.display = 'none';
    if (panelGeneric) panelGeneric.style.display = 'block';
    if (panelParticipants) panelParticipants.style.display = 'none';
    if (panelCoupons) panelCoupons.style.display = 'none';
    renderGenericPageEditor(activePage);
  }
}

// Render Participants Table
function renderParticipantsEditor() {
  // Load from new bookings API (falls back to old participants if empty)
  const panel = document.getElementById('panel-page-participants');
  if (!panel) return;

  // Show header with export button
  const header = panel.querySelector('#bookings-list-header');
  if (!header) {
    const h = document.createElement('div');
    h.id = 'bookings-list-header';
    h.style.cssText = 'display:flex; justify-content:space-between; align-items:center; margin-bottom:1rem; flex-wrap:wrap; gap:0.5rem;';
    h.innerHTML = `
      <h3 style="color:var(--accent-cyan); margin:0;">📋 Prenotazioni & Pagamenti</h3>
      <div style="display:flex; gap:0.5rem; flex-wrap:wrap;">
        <button onclick="downloadBookingsCsv()" class="btn btn-secondary" style="font-size:0.8rem; padding:0.4rem 0.8rem;">
          📥 Esporta CSV
        </button>
        <button onclick="renderParticipantsEditor()" class="btn btn-secondary" style="font-size:0.8rem; padding:0.4rem 0.8rem;">
          🔄 Aggiorna
        </button>
      </div>
    `;
    panel.insertBefore(h, panel.firstChild);
  }

  fetch('/api/bookings')
    .then(res => res.json())
    .then(bookings => {
      const tbody = document.getElementById('participants-table-body');
      if (!tbody) return;
      tbody.innerHTML = '';

      if (!bookings || bookings.length === 0) {
        // Fallback: try legacy /api/participants
        fetch('/api/participants')
          .then(r => r.json())
          .then(parts => {
            if (!parts || parts.length === 0) {
              tbody.innerHTML = '<tr><td colspan="10" style="padding:1.5rem; text-align:center; color:var(--text-muted);">Nessuna prenotazione registrata.</td></tr>';
            } else {
              renderLegacyParticipants(parts, tbody);
            }
          });
        return;
      }

      // Status badge helper
      function statusBadge(status) {
        const map = {
          paid:               ['#4ade80', '✅ Pagato'],
          pending:            ['#facc15', '⏳ In Attesa'],
          approved:           ['#60a5fa', '👍 Approvato'],
          failed:             ['#f87171', '❌ Fallito'],
          cancelled:          ['#9ca3af', '🚫 Annullato'],
          refunded:           ['#a78bfa', '↩️ Rimborsato'],
          partially_refunded: ['#f59e0b', '↩️ Rim. Parziale'],
          already_paid:       ['#4ade80', '✅ Pagato'],
        };
        const [color, label] = map[status] || ['#9ca3af', status];
        return `<span style="color:${color}; font-size:0.8rem; font-weight:700;">${label}</span>`;
      }

      bookings.forEach(b => {
        const tr = document.createElement('tr');
        tr.style.borderBottom = '1px solid rgba(255,255,255,0.05)';
        const finalEur = (b.finalCents || 35000) / 100;
        const balEur   = (b.balanceCents || 30000) / 100;
        const dueEur   = (b.amountDueCents || 5000) / 100;
        const formulaLabel = b.formula === 'caparra' ? '💳 Caparra €50' : '💰 Saldo Completo';
        const extraDayTag  = b.extraDay ? '<br><span style="color:#00f0ff;font-size:0.75rem;">+ venerdì (€100)</span>' : '';
        const couponTag    = b.couponCode ? `<span style="color:#4ade80; font-size:0.75rem;">🏷️ ${b.couponCode}</span>` : '—';
        const balanceBadge = b.formula === 'caparra'
          ? (b.balancePaid
              ? `<span style="color:#4ade80; font-size:0.75rem;">✅ Saldo pagato (${b.balancePaidMethod})</span>`
              : `<button onclick="adminMarkBalancePaid('${b.id}')"
                         style="font-size:0.72rem; padding:0.25rem 0.5rem; background:transparent; border:1px solid #facc15;
                                color:#facc15; border-radius:4px; cursor:pointer; white-space:nowrap;">
                   Segna Saldo Pagato
                 </button>`)
          : '<span style="color:var(--text-muted); font-size:0.75rem;">—</span>';

        tr.innerHTML = `
          <td style="padding:0.65rem; font-weight:700; color:var(--accent-cyan); font-size:0.8rem;">${b.id}</td>
          <td style="padding:0.65rem; color:var(--text-muted); font-size:0.75rem;">${(b.createdAt || '').slice(0,16).replace('T',' ')}</td>
          <td style="padding:0.65rem;">${statusBadge(b.status)}</td>
          <td style="padding:0.65rem; font-weight:700;">${b.firstName} ${b.lastName}</td>
          <td style="padding:0.65rem; color:var(--text-secondary); font-size:0.8rem;">${b.email}<br>
            <a href="https://wa.me/${(b.phone||'').replace(/[^0-9]/g,'')}" target="_blank" style="color:#25D366; font-size:0.75rem;">💬 ${b.phone}</a>
          </td>
          <td style="padding:0.65rem; font-size:0.8rem;">${formulaLabel}${extraDayTag}<br>${couponTag}</td>
          <td style="padding:0.65rem; font-size:0.8rem;">
            Finale: <strong>€${finalEur.toFixed(2)}</strong><br>
            Pagato: <strong style="color:var(--accent-cyan);">€${dueEur.toFixed(2)}</strong><br>
            ${b.formula === 'caparra' ? `In loco: €${balEur.toFixed(2)}` : ''}
          </td>
          <td style="padding:0.65rem; font-size:0.75rem;">${balanceBadge}</td>
          <td style="padding:0.65rem; font-size:0.7rem; color:var(--text-muted);">
            ${b.paypalOrderId ? b.paypalOrderId.slice(0,12)+'…' : '—'}<br>
            ${b.paypalCaptureId ? b.paypalCaptureId.slice(0,12)+'…' : ''}
          </td>
        `;
        tbody.appendChild(tr);
      });

      // Update table headers if not already done
      const thead = tbody.closest('table')?.querySelector('thead tr');
      if (thead && thead.children.length < 9) {
        thead.innerHTML = `
          <th style="padding:0.75rem; text-align:left;">ID</th>
          <th style="padding:0.75rem; text-align:left;">Data</th>
          <th style="padding:0.75rem; text-align:left;">Stato</th>
          <th style="padding:0.75rem; text-align:left;">Nome</th>
          <th style="padding:0.75rem; text-align:left;">Contatti</th>
          <th style="padding:0.75rem; text-align:left;">Formula</th>
          <th style="padding:0.75rem; text-align:left;">Importi</th>
          <th style="padding:0.75rem; text-align:left;">Saldo</th>
          <th style="padding:0.75rem; text-align:left;">PayPal IDs</th>
        `;
      }
    })
    .catch(err => console.error('Fetch bookings error:', err));
}

function renderLegacyParticipants(parts, tbody) {
  parts.forEach(p => {
    const tr = document.createElement('tr');
    tr.style.borderBottom = '1px solid rgba(255,255,255,0.05)';
    tr.innerHTML = `
      <td style="padding:0.75rem; font-weight:700; color:var(--accent-cyan);">${p.id}</td>
      <td style="padding:0.75rem; color:var(--text-muted);">${p.bookingDate}</td>
      <td>—</td>
      <td style="padding:0.75rem; font-weight:700;">${p.firstName} ${p.lastName}</td>
      <td style="padding:0.75rem; color:var(--text-secondary);">${p.email}</td>
      <td><a href="https://wa.me/${(p.phone||'').replace(/[^0-9]/g,'')}" target="_blank" style="color:#25D366;">💬 ${p.phone}</a></td>
      <td style="padding:0.75rem;">${p.paymentFormula}</td>
      <td style="padding:0.75rem; font-weight:700; color:var(--accent-emerald);">${p.amountPaid}</td>
      <td>—</td>
    `;
    tbody.appendChild(tr);
  });
}

async function adminMarkBalancePaid(bookingId) {
  const method = prompt('Metodo pagamento saldo (contanti / bonifico / paypal):', 'contanti');
  if (!method) return;
  try {
    const res = await fetch('/api/mark-balance-paid', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ bookingId, method }),
    });
    const data = await res.json();
    if (data.status === 'success') {
      showToast('✅ Saldo segnato come pagato!');
      renderParticipantsEditor();
    } else {
      alert('Errore: ' + data.message);
    }
  } catch (e) {
    alert('Errore di rete: ' + e.message);
  }
}

function downloadBookingsCsv() {
  window.open('/api/download-excel', '_blank');
}



function sendExcelEmail() {
  showToast('✉️ Invio report Excel in corso a info@davideluongo.com...');

  fetch('/api/send-excel-email', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      recipientEmail: 'info@davideluongo.com',
      workshopName: 'Tutti i Workshop'
    })
  })
  .then(res => res.json())
  .then(data => {
    if (data.status === 'success') {
      showToast('✅ Report Excel inviato con successo a info@davideluongo.com!');
    } else {
      alert('Errore invio email: ' + data.message);
    }
  })
  .catch(err => console.error('Send email error:', err));
}

function saveSmtpConfig() {
  const smtpUser = document.getElementById('smtp-user-input').value;
  const smtpPassword = document.getElementById('smtp-pass-input').value;
  const smtpHost = document.getElementById('smtp-host-input').value;

  if (!smtpPassword) {
    alert('Per favore inserisci la password della tua casella email Aruba.');
    return;
  }

  fetch('/api/save-smtp-config', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      smtpUser: smtpUser,
      smtpPassword: smtpPassword,
      smtpHost: smtpHost,
      smtpPort: 465
    })
  })
  .then(res => res.json())
  .then(data => {
    if (data.status === 'success') {
      showToast('✅ Credenziali Aruba SMTP salvate! Le email verranno spedite realmente.');
    } else {
      alert('Errore salvataggio credenziali: ' + data.message);
    }
  })
  .catch(err => console.error('Save SMTP error:', err));
}

// Render Home Page Editor Sections
function renderHomeEditor() {
  if (!globalData || !globalData.home) return;

  // 1. Hero
  document.getElementById('edit-hero-badge').value = globalData.home.badge || '';
  document.getElementById('edit-hero-title').value = globalData.home.title || '';
  document.getElementById('edit-hero-desc').value = globalData.home.description || '';

  // 2. Bio
  const bioContainer = document.getElementById('bio-paragraphs-container');
  bioContainer.innerHTML = '';
  if (globalData.home.bio && globalData.home.bio.paragraphs) {
    globalData.home.bio.paragraphs.forEach((p, idx) => {
      const div = document.createElement('div');
      div.className = 'form-group';
      div.innerHTML = `
        <label class="form-label">Paragrafo Biografia ${idx + 1}</label>
        <textarea class="form-textarea bio-para-input" rows="3" data-idx="${idx}">${p}</textarea>
      `;
      bioContainer.appendChild(div);
    });
  }

  // 3. Workshops List
  const workshopsContainer = document.getElementById('admin-workshops-list');
  workshopsContainer.innerHTML = '';
  if (globalData.workshops) {
    globalData.workshops.forEach((ws, idx) => {
      workshopsContainer.appendChild(renderEntityCard(ws, idx, 'workshop'));
    });
  }

  // 4. Viaggi 2027 List
  const tripsContainer = document.getElementById('admin-trips-list');
  tripsContainer.innerHTML = '';
  if (globalData.trips_2027) {
    globalData.trips_2027.forEach((trip, idx) => {
      tripsContainer.appendChild(renderEntityCard(trip, idx, 'viaggio'));
    });
  }

  // 5. Assets
  renderAssetsForPage('home', 'home-assets-grid');
}

// Render Generic Page Editor (e.g. Friuli, Gear, Blog)
function renderGenericPageEditor(pageKey) {
  const genericTitle = document.getElementById('generic-card-title');
  const genericContent = document.getElementById('generic-editor-content');

  const pageSlugMap = {
    'page-friuli': 'friuli-2026',
    'page-cascate': 'cascate-appennino-2026',
    'page-canfaito': 'canfaito-2026',
    'page-casentinesi': 'foreste-casentinesi-2026',
    'page-gear': 'gear',
    'page-blog': 'blog'
  };

  const slug = pageSlugMap[pageKey] || 'general';

  if (pageKey === 'page-gear') {
    genericTitle.innerText = '📷 Prodotti Gear, Recensioni & Codici Sconto';
    genericContent.innerHTML = '<div id="gear-entities-list"></div>';
    const gearList = document.getElementById('gear-entities-list');
    if (globalData.gear) {
      globalData.gear.forEach((g, idx) => {
        const card = document.createElement('div');
        card.className = 'entity-card';
        card.innerHTML = `
          <div style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 1rem;">
            <h3 style="font-size: 1.1rem; color: var(--accent-blue);">${g.title}</h3>
            <button class="delete-btn" onclick="deleteEntity('gear', '${g.id}')">🗑️ Elimina</button>
          </div>
          <div class="form-grid">
            <div class="form-group">
              <label class="form-label">Nome Prodotto</label>
              <input type="text" class="form-input gear-title-input" data-idx="${idx}" value="${g.title}" />
            </div>
            <div class="form-group">
              <label class="form-label">Codice Sconto</label>
              <input type="text" class="form-input gear-discount-input" data-idx="${idx}" value="${g.discountCode || ''}" />
            </div>
          </div>
          <div class="form-group" style="margin-top: 1rem;">
            <label class="form-label">Micro-Articolo / Recensione</label>
            <textarea class="form-textarea gear-article-input" data-idx="${idx}" rows="3">${g.microArticle}</textarea>
          </div>
        `;
        gearList.appendChild(card);
      });
    }

  } else if (pageKey === 'page-blog') {
    genericTitle.innerText = '📰 Articoli del Blog & Pubblicazioni';
    genericContent.innerHTML = '<div id="blog-entities-list"></div>';
    const blogList = document.getElementById('blog-entities-list');
    if (globalData.blog) {
      globalData.blog.forEach((b, idx) => {
        const card = document.createElement('div');
        card.className = 'entity-card';
        card.innerHTML = `
          <div style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 1rem;">
            <h3 style="font-size: 1.1rem; color: var(--accent-cyan);">${b.title}</h3>
            <button class="delete-btn" onclick="deleteEntity('blog', '${b.id}')">🗑️ Elimina</button>
          </div>
          <div class="form-grid">
            <div class="form-group">
              <label class="form-label">Titolo Articolo</label>
              <input type="text" class="form-input blog-title-input" data-idx="${idx}" value="${b.title}" />
            </div>
            <div class="form-group">
              <label class="form-label">Tag Editore</label>
              <input type="text" class="form-input blog-pubtag-input" data-idx="${idx}" value="${b.publisherTag || ''}" />
            </div>
          </div>
          <div class="form-group" style="margin-top: 1rem;">
            <label class="form-label">Estratto / Sommario</label>
            <textarea class="form-textarea blog-excerpt-input" data-idx="${idx}" rows="2">${b.excerpt}</textarea>
          </div>
        `;
        blogList.appendChild(card);
      });
    }

  } else {
    // Specific Workshop Landing Page Inspector
    const ws = (globalData.workshops || []).find(w => w.id === slug);
    genericTitle.innerText = `🏞️ Landing Page: ${ws ? ws.title : slug}`;
    
    genericContent.innerHTML = `
      <div class="form-grid">
        <div class="form-group">
          <label class="form-label">Titolo Landing Page</label>
          <input type="text" class="form-input" id="generic-ws-title" value="${ws ? ws.title : ''}" />
        </div>
        <div class="form-group">
          <label class="form-label">Data Ufficiale</label>
          <input type="text" class="form-input" id="generic-ws-date" value="${ws ? ws.date : ''}" />
        </div>
        <div class="form-group">
          <label class="form-label">Posti Disponibili</label>
          <input type="number" class="form-input" id="generic-ws-avail" value="${ws ? ws.availableSeats : 8}" />
        </div>
        <div class="form-group">
          <label class="form-label">Quota Partecipazione</label>
          <input type="text" class="form-input" id="generic-ws-price" value="${ws ? ws.price : ''}" />
        </div>
      </div>
      <div class="form-group" style="margin-top: 1rem;">
        <label class="form-label">Descrizione Landing</label>
        <textarea class="form-textarea" id="generic-ws-desc" rows="3">${ws ? ws.description : ''}</textarea>
      </div>

      <div style="margin-top: 2rem;">
        <h4 style="font-size: 1rem; color: var(--accent-cyan); margin-bottom: 0.75rem;">🖼️ Immagini della Pagina (${slug})</h4>
        <div class="dropzone" id="generic-dropzone">
          <div style="font-size: 1.5rem;">📸 Carica Foto per ${slug}</div>
          <p style="font-size: 0.8rem; color: var(--text-secondary);">Preserva al 100% lo spazio colore sRGB ed auto-riscala >5MB/2048px.</p>
          <input type="file" id="generic-file-input" accept="image/*" style="display: none;" multiple />
        </div>
        <div class="asset-list-grid" id="generic-assets-grid"></div>
      </div>
    `;

    setupGenericDropzone(slug);
    renderAssetsForPage(slug, 'generic-assets-grid');
  }
}

function renderEntityCard(ws, idx, type) {
  const card = document.createElement('div');
  card.className = 'entity-card';
  card.innerHTML = `
    <div style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 1rem;">
      <h3 style="font-size: 1.1rem; color: ${type === 'workshop' ? 'var(--accent-cyan)' : 'var(--accent-purple)'};">${ws.title}</h3>
      <div>
        <span style="font-size: 0.8rem; color: var(--text-muted); margin-right: 1rem;">ID: ${ws.id}</span>
        <button class="delete-btn" onclick="deleteEntity('${type}', '${ws.id}')">🗑️ Elimina</button>
      </div>
    </div>
    <div class="form-grid">
      <div class="form-group">
        <label class="form-label">Titolo Evento</label>
        <input type="text" class="form-input ${type}-title" data-idx="${idx}" value="${ws.title}" />
      </div>
      <div class="form-group">
        <label class="form-label">Data</label>
        <input type="text" class="form-input ${type}-date" data-idx="${idx}" value="${ws.date}" />
      </div>
      <div class="form-group">
        <label class="form-label">Posti Disponibili</label>
        <input type="number" class="form-input ${type}-avail" data-idx="${idx}" value="${ws.availableSeats || 8}" />
      </div>
      <div class="form-group">
        <label class="form-label">Quota</label>
        <input type="text" class="form-input ${type}-price" data-idx="${idx}" value="${ws.price}" />
      </div>
    </div>
    <div class="form-group" style="margin-top: 1rem;">
      <label class="form-label">Descrizione Evento</label>
      <textarea class="form-textarea ${type}-desc" data-idx="${idx}" rows="2">${ws.description}</textarea>
    </div>
  `;
  return card;
}

// Render Asset cards filtered by page
function renderAssetsForPage(pageTag, targetContainerId) {
  const container = document.getElementById(targetContainerId);
  if (!container) return;
  container.innerHTML = '';

  if (globalData.assets && globalData.assets.length > 0) {
    const pageAssets = globalData.assets.filter(a => a.pageTag === pageTag || pageTag === 'home');
    if (pageAssets.length === 0) {
      container.innerHTML = '<p style="color: var(--text-muted); grid-column: 1 / -1;">Nessun asset caricato per questa pagina.</p>';
      return;
    }

    pageAssets.forEach(asset => {
      const card = document.createElement('div');
      card.className = 'asset-card';
      const scaleBadge = asset.wasRescaled ? '<span style="color: #FBBF24; font-size: 0.65rem;">⚡ Rescaled ≤2048px</span>' : '';

      card.innerHTML = `
        <img src="${asset.webpPath || asset.jpegPath}" alt="${asset.filename}" />
        <div class="asset-card-body">
          <div style="font-weight: 700; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;">${asset.filename}</div>
          <div style="color: var(--text-secondary); font-size: 0.75rem;">${asset.width}x${asset.height} px • WebP sRGB</div>
          <div style="display: flex; justify-content: space-between; align-items: center; margin-top: 0.5rem;">
            <span style="font-size: 0.7rem; color: var(--accent-emerald);">✓ sRGB Preservato</span>
            ${scaleBadge}
          </div>
        </div>
      `;
      container.appendChild(card);
    });
  } else {
    container.innerHTML = '<p style="color: var(--text-muted);">Nessun asset disponibile.</p>';
  }
}

// Dropzone handler for Home page
function setupDropzone() {
  const dropzone = document.getElementById('home-dropzone');
  const fileInput = document.getElementById('home-file-input');

  if (!dropzone || !fileInput) return;

  dropzone.addEventListener('click', () => fileInput.click());
  dropzone.addEventListener('dragover', (e) => { e.preventDefault(); });
  dropzone.addEventListener('drop', (e) => {
    e.preventDefault();
    if (e.dataTransfer.files.length > 0) handleUpload(e.dataTransfer.files, 'home');
  });

  fileInput.addEventListener('change', () => {
    if (fileInput.files.length > 0) handleUpload(fileInput.files, 'home');
  });
}

function setupGenericDropzone(pageSlug) {
  setTimeout(() => {
    const dropzone = document.getElementById('generic-dropzone');
    const fileInput = document.getElementById('generic-file-input');
    if (!dropzone || !fileInput) return;

    dropzone.addEventListener('click', () => fileInput.click());
    dropzone.addEventListener('dragover', (e) => { e.preventDefault(); });
    dropzone.addEventListener('drop', (e) => {
      e.preventDefault();
      if (e.dataTransfer.files.length > 0) handleUpload(e.dataTransfer.files, pageSlug);
    });

    fileInput.addEventListener('change', () => {
      if (fileInput.files.length > 0) handleUpload(fileInput.files, pageSlug);
    });
  }, 100);
}

function handleUpload(files, pageTag) {
  Array.from(files).forEach(file => {
    const reader = new FileReader();
    reader.onload = (e) => {
      const base64Data = e.target.result.split(',')[1];
      
      fetch('/api/upload', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          filename: file.name,
          pageTag: pageTag,
          base64Data: base64Data
        })
      })
      .then(res => res.json())
      .then(data => {
        if (data.status === 'success') {
          showToast(`Foto "${file.name}" caricata per "${pageTag}" con profilo sRGB!`);
          if (!globalData.assets) globalData.assets = [];
          globalData.assets.unshift(data.asset);
          renderActivePageEditor();
        } else {
          alert('Errore caricamento: ' + data.message);
        }
      })
      .catch(err => console.error('Upload error:', err));
    };
    reader.readAsDataURL(file);
  });
}

// Modal handling
function openCreateModal(type) {
  const modal = document.getElementById('create-entity-modal');
  if (!modal) return;
  document.getElementById('modal-entity-type').value = type;
  modal.classList.add('active');
}

function setupEntityModal() {
  const form = document.getElementById('create-entity-form');
  const modal = document.getElementById('create-entity-modal');
  const addBtn = document.getElementById('add-entity-btn');

  if (addBtn && modal) {
    addBtn.addEventListener('click', () => modal.classList.add('active'));
  }

  if (form) {
    form.addEventListener('submit', (e) => {
      e.preventDefault();
      const entityType = document.getElementById('modal-entity-type').value;
      const entity = {
        id: document.getElementById('modal-entity-id').value,
        title: document.getElementById('modal-entity-title').value,
        category: entityType === 'workshop' ? 'nazionale' : 'viaggio',
        date: document.getElementById('modal-entity-date').value,
        location: document.getElementById('modal-entity-location').value,
        price: document.getElementById('modal-entity-price').value,
        availableSeats: 8,
        totalSeats: 8,
        status: 'active',
        statusLabel: 'Iscrizioni Aperte',
        image: document.getElementById('modal-entity-image').value,
        description: document.getElementById('modal-entity-desc').value
      };

      fetch('/api/create-entity', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ entityType, entity })
      })
      .then(res => res.json())
      .then(data => {
        if (data.status === 'success') {
          showToast(`Entità "${entity.title}" creata e pagina landing generata!`);
          modal.classList.remove('active');
          fetchContent();
        } else {
          alert('Errore creazione: ' + data.message);
        }
      })
      .catch(err => console.error('Create error:', err));
    });
  }
}

function deleteEntity(entityType, entityId) {
  if (!confirm(`Confermi l'eliminazione dell'elemento "${entityId}"?`)) return;

  fetch('/api/delete-entity', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ entityType, entityId })
  })
  .then(res => res.json())
  .then(data => {
    if (data.status === 'success') {
      showToast(`Elemento "${entityId}" eliminato!`);
      fetchContent();
    } else {
      alert('Errore eliminazione: ' + data.message);
    }
  })
  .catch(err => console.error('Delete error:', err));
}

// Save all changes button
function setupSaveButton() {
  const saveBtn = document.getElementById('save-all-btn');
  if (!saveBtn) return;

  saveBtn.addEventListener('click', () => {
    // 1. Home values
    if (globalData.home) {
      globalData.home.badge = document.getElementById('edit-hero-badge').value;
      globalData.home.title = document.getElementById('edit-hero-title').value;
      globalData.home.description = document.getElementById('edit-hero-desc').value;

      const bioInputs = document.querySelectorAll('.bio-para-input');
      bioInputs.forEach((textarea, idx) => {
        globalData.home.bio.paragraphs[idx] = textarea.value;
      });
    }

    // 2. Workshops values
    if (globalData.workshops) {
      const titles = document.querySelectorAll('.workshop-title');
      const dates = document.querySelectorAll('.workshop-date');
      const avails = document.querySelectorAll('.workshop-avail');
      const prices = document.querySelectorAll('.workshop-price');
      const descs = document.querySelectorAll('.workshop-desc');

      titles.forEach((input, idx) => {
        if (globalData.workshops[idx]) {
          globalData.workshops[idx].title = input.value;
          globalData.workshops[idx].date = dates[idx].value;
          globalData.workshops[idx].availableSeats = parseInt(avails[idx].value, 10);
          globalData.workshops[idx].price = prices[idx].value;
          globalData.workshops[idx].description = descs[idx].value;
        }
      });
    }

    // Send POST to /api/content
    fetch('/api/content', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(globalData)
    })
    .then(res => res.json())
    .then(resData => {
      if (resData.status === 'success') {
        showToast('Tutte le sezioni ed i contenuti sono stati salvati!');
      } else {
        alert('Errore durante il salvataggio: ' + resData.message);
      }
    })
    .catch(err => console.error('Save error:', err));
  });
}

function triggerAiSeoOptimization() {
  showToast('🤖 L\'Agente AI SEO sta analizzando i contenuti e rigenerando i tag SEO per Google...');

  fetch('/api/content', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(globalData)
  })
  .then(res => res.json())
  .then(resData => {
    if (resData.status === 'success') {
      showToast('✨ AI SEO Agent: Tag <title>, <meta description> e Schema JSON-LD ottimizzati per tutte le pagine!');
      fetchContent();
    } else {
      alert('Errore ottimizzazione SEO: ' + resData.message);
    }
  })
  .catch(err => console.error('AI SEO error:', err));
}

function showToast(msg) {
  const toast = document.getElementById('toast');
  if (!toast) return;
  toast.innerText = msg;
  toast.style.display = 'block';
  setTimeout(() => {
    toast.style.display = 'none';
  }, 3500);
}

// ----------------------------------------------------
// GESTORE CODICI SCONTO (COUPONS)
// ----------------------------------------------------
let adminCoupons = [];

function renderCouponsEditor() {
  const container = document.getElementById('admin-coupons-container');
  if (!container) return;

  adminCoupons = globalData.coupons || [];
  container.innerHTML = '';

  if (adminCoupons.length === 0) {
    container.innerHTML = '<p style="color:var(--text-muted); text-align:center; padding:1rem;">Nessun codice sconto. Clicca su "+ Nuovo Codice Sconto" per crearne uno.</p>';
    return;
  }

  adminCoupons.forEach((c, idx) => {
    const isPercent   = c.type === 'percentage';
    const isFixed     = c.type === 'fixed_price';
    const percentVal  = c.percentage  != null ? c.percentage  : (c.value || 0);
    const fixedVal    = c.fixedPrice  != null ? c.fixedPrice  : (isFixed ? (c.value || 0) : '');
    const usedCount   = c.usedCount   || 0;
    const usageLimit  = c.usageLimit  != null ? c.usageLimit  : '';
    const description = c.description || '';

    const card = document.createElement('div');
    card.className = 'entity-card';
    card.style.marginBottom = '1.25rem';
    card.innerHTML = `
      <div style="display:flex; align-items:center; justify-content:space-between; margin-bottom:1rem;">
        <div>
          <h3 style="font-size:1.1rem; color:var(--accent-cyan); font-family:var(--font-heading); font-weight:800; letter-spacing:1px; margin:0;">
            🎟️ ${c.code || 'NUOVO_CODICE'}
          </h3>
          <div style="font-size:0.75rem; color:var(--text-muted); margin-top:0.2rem;">
            Utilizzi: ${usedCount}${usageLimit !== '' ? ' / ' + usageLimit : ' (illimitato)'}
            &nbsp;·&nbsp;
            <span style="color:${c.active !== false ? '#4ade80' : '#f87171'}">
              ${c.active !== false ? '● Attivo' : '● Disattivato'}
            </span>
          </div>
        </div>
        <button class="delete-btn" onclick="deleteCoupon(${idx})">🗑️ Elimina</button>
      </div>

      <div class="form-grid">
        <div class="form-group">
          <label class="form-label">Codice (es. DAVEPRO10)</label>
          <input type="text" class="form-input coupon-code-input" data-idx="${idx}"
                 value="${c.code || ''}"
                 style="text-transform:uppercase; font-family:var(--font-heading); font-weight:700;" />
        </div>

        <div class="form-group">
          <label class="form-label">Tipologia Sconto</label>
          <select class="form-input coupon-type-input" data-idx="${idx}" onchange="onCouponTypeChange(this)">
            <option value="percentage" ${isPercent ? 'selected' : ''}>Sconto Percentuale (%)</option>
            <option value="fixed_price" ${isFixed   ? 'selected' : ''}>Prezzo Finale Fisso (€)</option>
          </select>
        </div>
      </div>

      <!-- Campo Percentuale -->
      <div class="form-group coupon-pct-group-${idx}" style="display:${isPercent ? '' : 'none'}; margin-top:0.5rem;">
        <label class="form-label">Percentuale di Sconto (es. 10 = -10%)</label>
        <div style="display:flex; align-items:center; gap:0.5rem;">
          <input type="number" class="form-input coupon-pct-input" data-idx="${idx}"
                 value="${percentVal}" min="1" max="99" step="1" style="max-width:120px;" />
          <span style="color:var(--text-secondary); font-size:0.9rem;">%</span>
          <span style="font-size:0.8rem; color:var(--text-muted); margin-left:0.5rem;" id="pct-preview-${idx}">
            → Su €350: risparmio €${((percentVal/100)*350).toFixed(2)}, paghi €${(350 - (percentVal/100)*350).toFixed(2)}
          </span>
        </div>
      </div>

      <!-- Campo Prezzo Fisso -->
      <div class="form-group coupon-fixed-group-${idx}" style="display:${isFixed ? '' : 'none'}; margin-top:0.5rem;">
        <label class="form-label">Prezzo Finale Fisso (€) — es. 300 = prezzo finale €300</label>
        <div style="display:flex; align-items:center; gap:0.5rem;">
          <span style="color:var(--text-secondary);">€</span>
          <input type="number" class="form-input coupon-fixed-input" data-idx="${idx}"
                 value="${fixedVal}" min="0" max="349" step="1" style="max-width:120px;" />
          <span style="font-size:0.8rem; color:var(--text-muted); margin-left:0.5rem;" id="fixed-preview-${idx}">
            ${fixedVal !== '' ? `→ Sconto: -€${(350 - fixedVal).toFixed(2)}` : ''}
          </span>
        </div>
        <div style="font-size:0.75rem; color:rgba(168,85,247,0.8); margin-top:0.35rem;">
          ✱ In caso di caparra, il saldo in loco sarà <strong>prezzo fisso − €50</strong>.
        </div>
      </div>

      <div class="form-grid" style="margin-top:1rem;">
        <div class="form-group">
          <label class="form-label">Descrizione (interna, per admin)</label>
          <input type="text" class="form-input coupon-desc-input" data-idx="${idx}"
                 value="${description}" placeholder="Es. Sconto per iscritti newsletter" />
        </div>

        <div class="form-group">
          <label class="form-label">Limite Utilizzi (vuoto = illimitato)</label>
          <input type="number" class="form-input coupon-limit-input" data-idx="${idx}"
                 value="${usageLimit}" min="1" placeholder="es. 10" />
        </div>

        <div class="form-group">
          <label class="form-label">Stato</label>
          <select class="form-input coupon-active-input" data-idx="${idx}">
            <option value="true"  ${c.active !== false ? 'selected' : ''}>✅ Attivo</option>
            <option value="false" ${c.active === false  ? 'selected' : ''}>⛔ Disattivato</option>
          </select>
        </div>
      </div>
    `;
    container.appendChild(card);

    // Live preview on percentage input
    const pctInput = card.querySelector(`.coupon-pct-input`);
    if (pctInput) {
      pctInput.addEventListener('input', () => {
        const v = parseFloat(pctInput.value) || 0;
        const el = document.getElementById(`pct-preview-${idx}`);
        if (el) el.textContent = `→ Su €350: risparmio €${((v/100)*350).toFixed(2)}, paghi €${(350-(v/100)*350).toFixed(2)}`;
      });
    }
    const fixedInput = card.querySelector(`.coupon-fixed-input`);
    if (fixedInput) {
      fixedInput.addEventListener('input', () => {
        const v = parseFloat(fixedInput.value) || 0;
        const el = document.getElementById(`fixed-preview-${idx}`);
        if (el) el.textContent = v > 0 ? `→ Sconto: -€${(350 - v).toFixed(2)}` : '';
      });
    }
  });
}

function onCouponTypeChange(selectEl) {
  const idx = selectEl.getAttribute('data-idx');
  const val = selectEl.value;
  const pctGroup   = document.querySelector(`.coupon-pct-group-${idx}`);
  const fixedGroup = document.querySelector(`.coupon-fixed-group-${idx}`);
  if (pctGroup)   pctGroup.style.display   = val === 'percentage'  ? '' : 'none';
  if (fixedGroup) fixedGroup.style.display = val === 'fixed_price'  ? '' : 'none';
}

function addNewCoupon() {
  if (!globalData.coupons) globalData.coupons = [];
  const newCode = `PROMO${Math.floor(Math.random() * 9000) + 1000}`;
  globalData.coupons.push({
    id:          `CP-${Date.now()}`,
    code:        newCode,
    type:        'percentage',
    percentage:  10,
    fixedPrice:  null,
    description: '',
    usageLimit:  null,
    usedCount:   0,
    active:      true
  });
  renderCouponsEditor();
}

function deleteCoupon(idx) {
  if (confirm(`Eliminare il codice "${(globalData.coupons[idx] || {}).code}"?`)) {
    globalData.coupons.splice(idx, 1);
    renderCouponsEditor();
  }
}

function saveCouponsFromAdmin() {
  const codes   = document.querySelectorAll('.coupon-code-input');
  const types   = document.querySelectorAll('.coupon-type-input');
  const actives = document.querySelectorAll('.coupon-active-input');
  const descs   = document.querySelectorAll('.coupon-desc-input');
  const limits  = document.querySelectorAll('.coupon-limit-input');

  const updatedCoupons = [];
  codes.forEach((codeInput, i) => {
    const idx     = parseInt(codeInput.getAttribute('data-idx'));
    const type    = types[i].value;
    const existing = globalData.coupons[idx] || {};

    let percentage = null;
    let fixedPrice = null;
    if (type === 'percentage') {
      const pctEl = document.querySelector(`.coupon-pct-input[data-idx="${idx}"]`);
      percentage  = pctEl ? (parseFloat(pctEl.value) || 10) : 10;
    } else {
      const fixEl = document.querySelector(`.coupon-fixed-input[data-idx="${idx}"]`);
      fixedPrice  = fixEl ? (parseFloat(fixEl.value) || null) : null;
    }

    const limitVal = limits[i].value.trim();
    updatedCoupons.push({
      id:          existing.id || `CP-${Date.now()}-${i}`,
      code:        codeInput.value.trim().toUpperCase(),
      type:        type,
      percentage:  percentage,
      fixedPrice:  fixedPrice,
      description: descs[i] ? descs[i].value.trim() : '',
      usageLimit:  limitVal !== '' ? parseInt(limitVal) : null,
      usedCount:   existing.usedCount || 0,
      active:      actives[i].value === 'true'
    });
  });

  fetch('/api/save-coupons', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ coupons: updatedCoupons })
  })
    .then(res => res.json())
    .then(data => {
      if (data.status === 'success' || data.status === 'ok') {
        globalData.coupons = updatedCoupons;
        renderCouponsEditor();
        showToast('✅ Codici sconto salvati!');
      } else {
        alert('Errore: ' + (data.message || 'Risposta inattesa'));
      }
    })
    .catch(() => alert('Errore di rete nel salvataggio dei coupon.'));
}
