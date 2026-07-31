/* ==========================================================================
   Davide Luongo — Admin CMS Client Logic
   ========================================================================== */

let globalData = {};

document.addEventListener('DOMContentLoaded', () => {
  fetchContent();
  setupTabNavigation();
  setupDropzone();
  setupSaveButton();
  setupEntityModals();
  setupAssetFilter();
});

// Fetch current data from server API
function fetchContent() {
  fetch('/api/content')
    .then(res => res.json())
    .then(data => {
      globalData = data;
      renderAdminForms();
    })
    .catch(err => {
      console.error('Error fetching content:', err);
    });
}

// Render forms with database values
function renderAdminForms() {
  if (!globalData) return;

  // 1. Home Hero
  if (globalData.home) {
    document.getElementById('edit-hero-badge').value = globalData.home.badge || '';
    document.getElementById('edit-hero-title').value = globalData.home.title || '';
    document.getElementById('edit-hero-desc').value = globalData.home.description || '';

    // Bio
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
  }

  // 2. Workshops 2026 List Form
  const workshopsContainer = document.getElementById('admin-workshops-list');
  workshopsContainer.innerHTML = '';
  if (globalData.workshops) {
    globalData.workshops.forEach((ws, idx) => {
      const card = renderWorkshopCard(ws, idx, 'workshop');
      workshopsContainer.appendChild(card);
    });
  }

  // 3. Viaggi 2027 List Form
  const tripsContainer = document.getElementById('admin-trips-list');
  tripsContainer.innerHTML = '';
  if (globalData.trips_2027) {
    globalData.trips_2027.forEach((trip, idx) => {
      const card = renderWorkshopCard(trip, idx, 'viaggio');
      tripsContainer.appendChild(card);
    });
  }

  // 4. Blog Articles Form
  const blogContainer = document.getElementById('admin-blog-list');
  blogContainer.innerHTML = '';
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
            <label class="form-label">Tag Editore / Categoria</label>
            <input type="text" class="form-input blog-pubtag-input" data-idx="${idx}" value="${b.publisherTag || ''}" />
          </div>
        </div>
        <div class="form-group" style="margin-top: 1rem;">
          <label class="form-label">Estratto / Sommario</label>
          <textarea class="form-textarea blog-excerpt-input" data-idx="${idx}" rows="2">${b.excerpt}</textarea>
        </div>
      `;
      blogContainer.appendChild(card);
    });
  }

  // 5. Gear List Form
  const gearContainer = document.getElementById('admin-gear-list');
  gearContainer.innerHTML = '';
  if (globalData.gear) {
    globalData.gear.forEach((g, idx) => {
      const card = document.createElement('div');
      card.className = 'entity-card';
      card.innerHTML = `
        <div style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 1rem;">
          <h3 style="font-size: 1.1rem; color: var(--accent-blue);">${g.title}</h3>
          <div>
            <span style="font-size: 0.8rem; color: var(--text-muted); margin-right: 1rem;">${g.brand}</span>
            <button class="delete-btn" onclick="deleteEntity('gear', '${g.id}')">🗑️ Elimina</button>
          </div>
        </div>
        <div class="form-grid">
          <div class="form-group">
            <label class="form-label">Nome Prodotto</label>
            <input type="text" class="form-input gear-title-input" data-idx="${idx}" value="${g.title}" />
          </div>
          <div class="form-group">
            <label class="form-label">Codice Sconto (opzionale)</label>
            <input type="text" class="form-input gear-discount-input" data-idx="${idx}" value="${g.discountCode || ''}" />
          </div>
        </div>
        <div class="form-group" style="margin-top: 1rem;">
          <label class="form-label">Micro-Articolo / Recensione Sintetica</label>
          <textarea class="form-textarea gear-article-input" data-idx="${idx}" rows="3">${g.microArticle}</textarea>
        </div>
      `;
      gearContainer.appendChild(card);
    });
  }

  // 6. Render Assets
  renderAssets();
}

function renderWorkshopCard(ws, idx, type) {
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
        <label class="form-label">Quota Partecipazione</label>
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

// Render Asset Cards filtered by page
function renderAssets() {
  const assetsContainer = document.getElementById('admin-assets-list');
  const filterVal = document.getElementById('asset-filter-select') ? document.getElementById('asset-filter-select').value : 'all';

  if (!assetsContainer) return;
  assetsContainer.innerHTML = '';

  if (globalData.assets && globalData.assets.length > 0) {
    const filtered = globalData.assets.filter(a => filterVal === 'all' || a.pageTag === filterVal);

    if (filtered.length === 0) {
      assetsContainer.innerHTML = `<p style="color: var(--text-muted); grid-column: 1 / -1;">Nessun asset salvato per la sezione "${filterVal}".</p>`;
      return;
    }

    filtered.forEach(asset => {
      const card = document.createElement('div');
      card.className = 'asset-card';
      const scaleBadge = asset.wasRescaled ? '<span style="color: #FBBF24; font-size: 0.7rem;">⚡ Rescaled ≤2048px</span>' : '';

      card.innerHTML = `
        <img src="${asset.webpPath || asset.jpegPath}" alt="${asset.filename}" />
        <div class="asset-card-body">
          <div style="font-weight: 700; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;">${asset.filename}</div>
          <div style="color: var(--text-secondary); font-size: 0.75rem;">${asset.width}x${asset.height} px • WebP sRGB</div>
          <div style="font-size: 0.75rem; color: var(--accent-cyan); margin: 0.2rem 0;">📍 Pagina: ${asset.pageTag || 'Generale'}</div>
          <div style="display: flex; justify-content: space-between; align-items: center; margin-top: auto; padding-top: 0.5rem;">
            <span style="font-size: 0.7rem; color: var(--accent-emerald);">✓ sRGB Preservato</span>
            ${scaleBadge}
          </div>
          <button class="delete-btn" style="margin-top: 0.5rem; width: 100%;" onclick="deleteEntity('asset', '${asset.filename}')">Rimuovi Asset</button>
        </div>
      `;
      assetsContainer.appendChild(card);
    });
  } else {
    assetsContainer.innerHTML = '<p style="color: var(--text-muted);">Nessun asset caricato nel sistema.</p>';
  }
}

function setupAssetFilter() {
  const filterSelect = document.getElementById('asset-filter-select');
  if (filterSelect) {
    filterSelect.addEventListener('change', renderAssets);
  }
}

// Tab navigation switcher
function setupTabNavigation() {
  const tabBtns = document.querySelectorAll('.admin-tab-btn');
  const tabContents = document.querySelectorAll('.admin-tab-content');

  tabBtns.forEach(btn => {
    btn.addEventListener('click', () => {
      tabBtns.forEach(b => b.classList.remove('active', 'btn-primary'));
      tabBtns.forEach(b => b.classList.add('btn-secondary'));

      btn.classList.remove('btn-secondary');
      btn.classList.add('active', 'btn-primary');

      const targetTab = btn.getAttribute('data-tab');
      tabContents.forEach(content => {
        content.style.display = (content.id === targetTab) ? 'block' : 'none';
      });
    });
  });
}

// Drag & drop upload handler with X-Page-Tag header
function setupDropzone() {
  const dropzone = document.getElementById('image-dropzone');
  const fileInput = document.getElementById('file-input');
  const pageSelect = document.getElementById('asset-page-select');

  if (!dropzone || !fileInput) return;

  dropzone.addEventListener('click', () => fileInput.click());

  dropzone.addEventListener('dragover', (e) => {
    e.preventDefault();
    dropzone.style.borderColor = 'var(--accent-emerald)';
  });

  dropzone.addEventListener('dragleave', () => {
    dropzone.style.borderColor = 'var(--accent-cyan)';
  });

  dropzone.addEventListener('drop', (e) => {
    e.preventDefault();
    dropzone.style.borderColor = 'var(--accent-cyan)';
    if (e.dataTransfer.files.length > 0) {
      handleFiles(e.dataTransfer.files, pageSelect.value);
    }
  });

  fileInput.addEventListener('change', () => {
    if (fileInput.files.length > 0) {
      handleFiles(fileInput.files, pageSelect.value);
    }
  });
}

function handleFiles(files, pageTag) {
  Array.from(files).forEach(file => {
    const reader = new FileReader();
    reader.onload = (e) => {
      const base64Data = e.target.result.split(',')[1];
      
      fetch('/api/upload', {
        method: 'POST',
        headers: { 
          'Content-Type': 'application/json',
          'X-Page-Tag': pageTag
        },
        body: JSON.stringify({
          filename: file.name,
          pageTag: pageTag,
          base64Data: base64Data
        })
      })
      .then(res => res.json())
      .then(data => {
        if (data.status === 'success') {
          showToast(`Foto "${file.name}" salvata per "${pageTag}" con profilo sRGB!`);
          if (!globalData.assets) globalData.assets = [];
          globalData.assets.unshift(data.asset);
          renderAssets();
        } else {
          alert('Errore caricamento: ' + data.message);
        }
      })
      .catch(err => console.error('Upload error:', err));
    };
    reader.readAsDataURL(file);
  });
}

// Modal dialogs and creation handlers
function setupEntityModals() {
  const openWsModalBtn = document.getElementById('open-create-workshop-modal');
  const wsModal = document.getElementById('create-workshop-modal');
  const createWsForm = document.getElementById('create-workshop-form');

  if (openWsModalBtn && wsModal) {
    openWsModalBtn.addEventListener('click', () => {
      wsModal.classList.add('active');
    });
  }

  if (createWsForm) {
    createWsForm.addEventListener('submit', (e) => {
      e.preventDefault();
      const entityType = document.getElementById('new-ws-type').value;
      const entity = {
        id: document.getElementById('new-ws-id').value,
        title: document.getElementById('new-ws-title').value,
        category: entityType === 'workshop' ? 'nazionale' : 'viaggio',
        date: document.getElementById('new-ws-date').value,
        location: document.getElementById('new-ws-location').value,
        duration: document.getElementById('new-ws-duration').value,
        price: document.getElementById('new-ws-price').value,
        availableSeats: parseInt(document.getElementById('new-ws-seats').value, 10),
        totalSeats: 8,
        status: 'active',
        statusLabel: 'Iscrizioni Aperte',
        image: document.getElementById('new-ws-image').value,
        description: document.getElementById('new-ws-desc').value
      };

      fetch('/api/create-entity', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          entityType: entityType,
          entity: entity
        })
      })
      .then(res => res.json())
      .then(data => {
        if (data.status === 'success') {
          showToast(`Entità "${entity.title}" creata e pagina landing generata!`);
          wsModal.classList.remove('active');
          fetchContent();
        } else {
          alert('Errore creazione: ' + data.message);
        }
      })
      .catch(err => console.error('Create entity error:', err));
    });
  }
}

// Delete Entity Handler
function deleteEntity(entityType, entityId) {
  if (!confirm(`Sei sicuro di voler eliminare questo elemento (${entityId})?`)) return;

  fetch('/api/delete-entity', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      entityType: entityType,
      entityId: entityId
    })
  })
  .then(res => res.json())
  .then(data => {
    if (data.status === 'success') {
      showToast(`Elemento ${entityId} eliminato con successo!`);
      fetchContent();
    } else {
      alert('Errore eliminazione: ' + data.message);
    }
  })
  .catch(err => console.error('Delete entity error:', err));
}

// Save all changes button
function setupSaveButton() {
  const saveBtn = document.getElementById('save-all-btn');
  if (!saveBtn) return;

  saveBtn.addEventListener('click', () => {
    // 1. Gather Home values
    if (globalData.home) {
      globalData.home.badge = document.getElementById('edit-hero-badge').value;
      globalData.home.title = document.getElementById('edit-hero-title').value;
      globalData.home.description = document.getElementById('edit-hero-desc').value;

      const bioInputs = document.querySelectorAll('.bio-para-input');
      bioInputs.forEach((textarea, idx) => {
        globalData.home.bio.paragraphs[idx] = textarea.value;
      });
    }

    // 2. Gather Workshops 2026 values
    if (globalData.workshops) {
      const titles = document.querySelectorAll('.workshop-title');
      const dates = document.querySelectorAll('.workshop-date');
      const avails = document.querySelectorAll('.workshop-avail');
      const prices = document.querySelectorAll('.workshop-price');
      const descs = document.querySelectorAll('.workshop-desc');

      titles.forEach((input, idx) => {
        globalData.workshops[idx].title = input.value;
        globalData.workshops[idx].date = dates[idx].value;
        globalData.workshops[idx].availableSeats = parseInt(avails[idx].value, 10);
        globalData.workshops[idx].price = prices[idx].value;
        globalData.workshops[idx].description = descs[idx].value;
      });
    }

    // 3. Gather Viaggi 2027 values
    if (globalData.trips_2027) {
      const titles = document.querySelectorAll('.viaggio-title');
      const dates = document.querySelectorAll('.viaggio-date');
      const descs = document.querySelectorAll('.viaggio-desc');

      titles.forEach((input, idx) => {
        globalData.trips_2027[idx].title = input.value;
        globalData.trips_2027[idx].date = dates[idx].value;
        globalData.trips_2027[idx].description = descs[idx].value;
      });
    }

    // 4. Gather Blog values
    if (globalData.blog) {
      const bTitles = document.querySelectorAll('.blog-title-input');
      const bPubtags = document.querySelectorAll('.blog-pubtag-input');
      const bExcerpts = document.querySelectorAll('.blog-excerpt-input');

      bTitles.forEach((input, idx) => {
        globalData.blog[idx].title = input.value;
        globalData.blog[idx].publisherTag = bPubtags[idx].value;
        globalData.blog[idx].excerpt = bExcerpts[idx].value;
      });
    }

    // 5. Gather Gear values
    if (globalData.gear) {
      const gTitles = document.querySelectorAll('.gear-title-input');
      const gDiscounts = document.querySelectorAll('.gear-discount-input');
      const gArticles = document.querySelectorAll('.gear-article-input');

      gTitles.forEach((input, idx) => {
        globalData.gear[idx].title = input.value;
        globalData.gear[idx].discountCode = gDiscounts[idx].value || null;
        globalData.gear[idx].microArticle = gArticles[idx].value;
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
        showToast('Tutti i contenuti salvati ed aggiornati nel Backend!');
      } else {
        alert('Errore durante il salvataggio: ' + resData.message);
      }
    })
    .catch(err => console.error('Save error:', err));
  });
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
