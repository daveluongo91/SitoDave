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
    'page-participants': '📊 Lista Partecipanti & Export Report Excel'
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

  if (activePage === 'page-home') {
    if (panelHome) panelHome.style.display = 'block';
    if (panelGeneric) panelGeneric.style.display = 'none';
    if (panelParticipants) panelParticipants.style.display = 'none';
    renderHomeEditor();
  } else if (activePage === 'page-participants') {
    if (panelHome) panelHome.style.display = 'none';
    if (panelGeneric) panelGeneric.style.display = 'none';
    if (panelParticipants) panelParticipants.style.display = 'block';
    renderParticipantsEditor();
  } else {
    if (panelHome) panelHome.style.display = 'none';
    if (panelGeneric) panelGeneric.style.display = 'block';
    if (panelParticipants) panelParticipants.style.display = 'none';
    renderGenericPageEditor(activePage);
  }
}

// Render Participants Table
function renderParticipantsEditor() {
  fetch('/api/participants')
    .then(res => res.json())
    .then(participants => {
      const tbody = document.getElementById('participants-table-body');
      if (!tbody) return;
      tbody.innerHTML = '';

      if (!participants || participants.length === 0) {
        tbody.innerHTML = '<tr><td colspan="8" style="padding: 1.5rem; text-align: center; color: var(--text-muted);">Nessuna prenotazione registrata al momento.</td></tr>';
        return;
      }

      participants.forEach(p => {
        const tr = document.createElement('tr');
        tr.style.borderBottom = '1px solid rgba(255,255,255,0.05)';
        tr.innerHTML = `
          <td style="padding: 0.75rem; font-weight: 700; color: var(--accent-cyan);">${p.id}</td>
          <td style="padding: 0.75rem; color: var(--text-muted);">${p.bookingDate}</td>
          <td style="padding: 0.75rem;">${p.workshop}</td>
          <td style="padding: 0.75rem; font-weight: 700;">${p.firstName} ${p.lastName}</td>
          <td style="padding: 0.75rem; color: var(--text-secondary);">${p.email}</td>
          <td style="padding: 0.75rem;"><a href="https://wa.me/${p.phone.replace(/[^0-9]/g, '')}" target="_blank" style="color: #25D366; text-decoration: underline;">💬 ${p.phone}</a></td>
          <td style="padding: 0.75rem;"><span style="color: var(--accent-purple);">${p.paymentFormula}</span></td>
          <td style="padding: 0.75rem; font-weight: 700; color: var(--accent-emerald);">${p.amountPaid}</td>
        `;
        tbody.appendChild(tr);
      });
    })
    .catch(err => console.error('Fetch participants error:', err));
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
