/* ==========================================================================
   Davide Luongo — Admin CMS Client Logic
   ========================================================================== */

let globalData = {};

document.addEventListener('DOMContentLoaded', () => {
  fetchContent();
  setupTabNavigation();
  setupDropzone();
  setupSaveButton();
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

  // 2. Workshops List Form
  const workshopsContainer = document.getElementById('admin-workshops-list');
  workshopsContainer.innerHTML = '';
  if (globalData.workshops) {
    globalData.workshops.forEach((ws, idx) => {
      const card = document.createElement('div');
      card.style.background = 'var(--bg-card)';
      card.style.border = '1px solid var(--border-glass)';
      card.style.borderRadius = 'var(--radius-md)';
      card.style.padding = '1.5rem';
      card.style.marginBottom = '1.5rem';

      card.innerHTML = `
        <div style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 1rem;">
          <h3 style="font-size: 1.1rem; color: var(--accent-cyan);">${ws.title}</h3>
          <span style="font-size: 0.8rem; color: var(--text-muted);">ID: ${ws.id}</span>
        </div>
        <div class="form-grid">
          <div class="form-group">
            <label class="form-label">Titolo Evento</label>
            <input type="text" class="form-input ws-title" data-idx="${idx}" value="${ws.title}" />
          </div>
          <div class="form-group">
            <label class="form-label">Data e Location</label>
            <input type="text" class="form-input ws-date" data-idx="${idx}" value="${ws.date}" />
          </div>
          <div class="form-group">
            <label class="form-label">Posti Disponibili</label>
            <input type="number" class="form-input ws-avail" data-idx="${idx}" value="${ws.availableSeats}" />
          </div>
          <div class="form-group">
            <label class="form-label">Posti Totali</label>
            <input type="number" class="form-input ws-total" data-idx="${idx}" value="${ws.totalSeats}" />
          </div>
          <div class="form-group">
            <label class="form-label">Etichetta Stato (es. Ultimi 2 Posti / Aperte)</label>
            <input type="text" class="form-input ws-status-label" data-idx="${idx}" value="${ws.statusLabel || ''}" />
          </div>
          <div class="form-group">
            <label class="form-label">Prezzo Quota</label>
            <input type="text" class="form-input ws-price" data-idx="${idx}" value="${ws.price}" />
          </div>
        </div>
        <div class="form-group" style="margin-top: 1rem;">
          <label class="form-label">Descrizione Evento</label>
          <textarea class="form-textarea ws-desc" data-idx="${idx}" rows="2">${ws.description}</textarea>
        </div>
      `;
      workshopsContainer.appendChild(card);
    });
  }

  // 3. Gear List Form
  const gearContainer = document.getElementById('admin-gear-list');
  gearContainer.innerHTML = '';
  if (globalData.gear) {
    globalData.gear.forEach((g, idx) => {
      const card = document.createElement('div');
      card.style.background = 'var(--bg-card)';
      card.style.border = '1px solid var(--border-glass)';
      card.style.borderRadius = 'var(--radius-md)';
      card.style.padding = '1.5rem';
      card.style.marginBottom = '1.5rem';

      card.innerHTML = `
        <div style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 1rem;">
          <h3 style="font-size: 1.1rem; color: var(--accent-blue);">${g.title}</h3>
          <span style="font-size: 0.8rem; color: var(--text-muted);">${g.brand}</span>
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

  // 4. Render Assets
  renderAssets();
}

// Render Asset Cards in Admin Tab
function renderAssets() {
  const assetsContainer = document.getElementById('admin-assets-list');
  if (!assetsContainer) return;
  assetsContainer.innerHTML = '';

  if (globalData.assets && globalData.assets.length > 0) {
    globalData.assets.forEach(asset => {
      const card = document.createElement('div');
      card.className = 'asset-card';
      card.innerHTML = `
        <img src="${asset.webpPath || asset.jpegPath}" alt="${asset.filename}" />
        <div class="asset-card-body">
          <div style="font-weight: 700; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;">${asset.filename}</div>
          <div style="color: var(--text-secondary); font-size: 0.75rem;">${asset.width}x${asset.height} px • WebP sRGB</div>
          <div style="margin-top: 0.4rem; font-size: 0.7rem; color: var(--accent-emerald);">✓ sRGB Preservato</div>
        </div>
      `;
      assetsContainer.appendChild(card);
    });
  } else {
    assetsContainer.innerHTML = '<p style="color: var(--text-muted);">Nessun asset caricato tramite il backend.</p>';
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
        if (content.id === targetTab) {
          content.style.display = 'block';
        } else {
          content.style.display = 'none';
        }
      });
    });
  });
}

// Drag & drop upload handler
function setupDropzone() {
  const dropzone = document.getElementById('image-dropzone');
  const fileInput = document.getElementById('file-input');

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
      handleFiles(e.dataTransfer.files);
    }
  });

  fileInput.addEventListener('change', () => {
    if (fileInput.files.length > 0) {
      handleFiles(fileInput.files);
    }
  });
}

function handleFiles(files) {
  Array.from(files).forEach(file => {
    const reader = new FileReader();
    reader.onload = (e) => {
      const base64Data = e.target.result.split(',')[1];
      
      fetch('/api/upload', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          filename: file.name,
          base64Data: base64Data
        })
      })
      .then(res => res.json())
      .then(data => {
        if (data.status === 'success') {
          showToast(`Immagine "${file.name}" elaborata con profilo sRGB!`);
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

    // 2. Gather Workshops values
    if (globalData.workshops) {
      const titles = document.querySelectorAll('.ws-title');
      const dates = document.querySelectorAll('.ws-date');
      const avails = document.querySelectorAll('.ws-avail');
      const totals = document.querySelectorAll('.ws-total');
      const statusLabels = document.querySelectorAll('.ws-status-label');
      const prices = document.querySelectorAll('.ws-price');
      const descs = document.querySelectorAll('.ws-desc');

      titles.forEach((input, idx) => {
        globalData.workshops[idx].title = input.value;
        globalData.workshops[idx].date = dates[idx].value;
        globalData.workshops[idx].availableSeats = parseInt(avails[idx].value, 10);
        globalData.workshops[idx].totalSeats = parseInt(totals[idx].value, 10);
        globalData.workshops[idx].statusLabel = statusLabels[idx].value;
        globalData.workshops[idx].price = prices[idx].value;
        globalData.workshops[idx].description = descs[idx].value;

        // Auto update status badge
        if (globalData.workshops[idx].availableSeats <= 2 && globalData.workshops[idx].availableSeats > 0) {
          globalData.workshops[idx].status = 'limited';
        } else if (globalData.workshops[idx].availableSeats === 0) {
          globalData.workshops[idx].status = 'soldout';
        }
      });
    }

    // 3. Gather Gear values
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
