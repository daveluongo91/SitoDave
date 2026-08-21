/* ==========================================================================
   Davide Luongo — Workshop Reservation & Info Request System (Event Delegated)
   ========================================================================== */

document.addEventListener('DOMContentLoaded', () => {
  setupReservationModal();
  setupInfoModal();
  setupGlobalClickDelegation();
  updateUrgencyCounters();
});

// Calculate Urgency Counter (Seats available minus 20% for FOMO urgency)
function calculateUrgencySeats(availableSeats, totalSeats = 8) {
  if (availableSeats <= 0) return 0;
  const bias = Math.ceil(totalSeats * 0.20);
  return Math.max(1, availableSeats - bias);
}

function updateUrgencyCounters() {
  fetch('/api/content')
    .then(res => res.json())
    .then(data => {
      if (!data.workshops) return;
      
      data.workshops.forEach(ws => {
        const displayedSeats = calculateUrgencySeats(ws.availableSeats || 8, ws.totalSeats || 8);
        
        document.querySelectorAll(`[data-workshop-seats="${ws.id}"]`).forEach(el => {
          if (ws.availableSeats <= 0) {
            el.innerText = '🔴 SOLD OUT';
            el.className = 'badge-status soldout';
          } else {
            el.innerText = `🔥 Solo ${displayedSeats} Posti Rimanenti!`;
            el.className = 'badge-status active';
          }
        });
      });
    })
    .catch(err => console.log('Urgency counter fetch skipped:', err));
}

// Global Click Delegation to catch ALL clicks on email/info links
function setupGlobalClickDelegation() {
  document.addEventListener('click', (e) => {
    const target = e.target.closest('a[href*="mailto:info@davideluongo.it"], .open-info-modal');
    if (target) {
      e.preventDefault();
      
      let subj = 'Informazioni Workshop';
      try {
        if (target.href && target.href.includes('subject=')) {
          const url = new URL(target.href);
          subj = url.searchParams.get('subject') || subj;
        } else {
          subj = target.getAttribute('data-subject') || target.innerText.replace('✉️', '').replace('↗', '').strip() || subj;
        }
      } catch (err) {
        subj = target.getAttribute('data-subject') || 'Informazioni Workshop';
      }

      openInfoModalWithSubject(subj);
    }
  });
}

function openInfoModalWithSubject(subject) {
  const cleanSubject = (subject || 'Informazioni Generali').trim();
  const formattedTag = cleanSubject.toLowerCase().startsWith('richiesta info per') 
    ? cleanSubject 
    : `Richiesta info per ${cleanSubject}`;

  setupInfoModal();
  const infoOverlay = document.getElementById('info-modal-overlay');
  if (infoOverlay) {
    const titleEl = document.getElementById('info-modal-title');
    const subjInput = document.getElementById('info-subject-input');
    const tagBadge = document.getElementById('info-tag-badge');

    if (titleEl) titleEl.innerText = `✉️ ${cleanSubject}`;
    if (subjInput) subjInput.value = formattedTag;
    if (tagBadge) {
      tagBadge.innerHTML = `🏷️ <strong>Tag email:</strong> ${formattedTag}`;
      tagBadge.style.display = 'inline-block';
    }
    infoOverlay.classList.add('active');
  }
}

// 1. INFO REQUEST MODAL (Richiedi Info via Email a info@davideluongo.it)
function setupInfoModal() {
  let infoOverlay = document.getElementById('info-modal-overlay');

  if (!infoOverlay) {
    infoOverlay = document.createElement('div');
    infoOverlay.id = 'info-modal-overlay';
    infoOverlay.className = 'modal-overlay';

    infoOverlay.innerHTML = `
      <div class="modal-content" style="max-width: 580px;">
        <button id="info-modal-close" class="modal-close" type="button">&times;</button>

        <div style="text-align: center; margin-bottom: 1.25rem;">
          <span id="info-tag-badge" style="display: inline-block; background: rgba(255, 42, 133, 0.15); border: 1px solid #ff2a85; color: #ff2a85; font-size: 0.8rem; font-weight: 700; padding: 0.3rem 0.8rem; border-radius: 9999px; margin-bottom: 0.75rem; text-transform: uppercase; letter-spacing: 0.05em;">🏷️ Tag: Richiesta info per...</span>
          <h3 id="info-modal-title" style="font-size: 1.5rem; color: var(--accent-cyan);" class="gradient-text">Richiedi Informazioni</h3>
          <p style="color: var(--text-secondary); font-size: 0.875rem; margin-top: 0.25rem;">La tua richiesta sarà inoltrata direttamente a <strong>info@davideluongo.it</strong>.</p>
        </div>

        <form id="info-request-form">
          <input type="hidden" id="info-subject-input" value="Richiesta info per Informazioni Generali" />
          
          <div class="form-group">
            <label class="form-label" for="info-name-input">Nome e Cognome *</label>
            <input type="text" id="info-name-input" class="form-input" placeholder="Es. Mario Rossi" required />
          </div>

          <div class="form-group" style="margin-top: 1rem;">
            <label class="form-label" for="info-email-input">Indirizzo Email *</label>
            <input type="email" id="info-email-input" class="form-input" placeholder="nome@esempio.com" required />
          </div>

          <div class="form-group" style="margin-top: 1rem;">
            <label class="form-label" for="info-phone-input">Telefono (Opzionale / WhatsApp)</label>
            <input type="tel" id="info-phone-input" class="form-input" placeholder="+39 340 1234567" />
          </div>

          <div class="form-group" style="margin-top: 1rem;">
            <label class="form-label" for="info-message-input">Messaggio / Domande *</label>
            <textarea id="info-message-input" class="form-textarea" rows="4" placeholder="Scrivi qui cosa vorresti sapere su programma, disponibilità, lista d'attesa o dettagli logistici..." required></textarea>
          </div>

          <button type="submit" class="btn btn-primary" style="width: 100%; padding: 0.9rem; margin-top: 1.25rem; font-size: 1rem; cursor: pointer;">✉️ Invia Richiesta a info@davideluongo.it</button>
        </form>
      </div>
    `;
    document.body.appendChild(infoOverlay);
  }

  const closeBtn = document.getElementById('info-modal-close');
  if (closeBtn) {
    closeBtn.onclick = () => infoOverlay.classList.remove('active');
  }

  // Handle Info Form Submit
  const infoForm = document.getElementById('info-request-form');
  if (infoForm && !infoForm.dataset.initialized) {
    infoForm.dataset.initialized = "true";
    infoForm.addEventListener('submit', (e) => {
      e.preventDefault();
      
      const name = document.getElementById('info-name-input').value;
      const email = document.getElementById('info-email-input').value;
      const phone = document.getElementById('info-phone-input').value || 'Non specificato';
      const subject = document.getElementById('info-subject-input').value;
      const message = document.getElementById('info-message-input').value;

      fetch('/api/send-info-email', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name, email, phone, subject, message })
      })
      .then(res => res.json())
      .then(data => {
        infoOverlay.classList.remove('active');
        showThankYouInfoModal(name, email, subject);
        infoForm.reset();
      })
      .catch(err => {
        console.error('Info email error:', err);
        infoOverlay.classList.remove('active');
        showThankYouInfoModal(name, email, subject);
      });
    });
  }
}

// Display Thank You Info Modal Overlay
function showThankYouInfoModal(name, email, subject) {
  let thankYouOverlay = document.getElementById('thankyou-info-overlay');
  
  if (!thankYouOverlay) {
    thankYouOverlay = document.createElement('div');
    thankYouOverlay.id = 'thankyou-info-overlay';
    thankYouOverlay.className = 'modal-overlay';
    document.body.appendChild(thankYouOverlay);
  }

  thankYouOverlay.innerHTML = `
    <div class="modal-content" style="max-width: 500px; text-align: center; padding: 2.5rem 2rem;">
      <div style="font-size: 3.5rem; margin-bottom: 0.5rem;">📩</div>
      <h3 class="gradient-text" style="font-size: 1.75rem; margin-bottom: 0.75rem;">Richiesta Inviata!</h3>
      <p style="color: var(--text-primary); font-size: 1rem; line-height: 1.6; margin-bottom: 1.5rem;">
        Grazie <strong>${name}</strong>!<br />
        La tua richiesta per "<em>${subject}</em>" è stata inviata con successo alla casella di posta <strong>info@davideluongo.it</strong>.
      </p>

      <div style="background: rgba(0, 240, 255, 0.08); border: 1px solid var(--accent-cyan); padding: 1rem; border-radius: var(--radius-md); font-size: 0.85rem; color: var(--text-secondary); margin-bottom: 1.5rem; text-align: left;">
        ✉️ Risponderemo al più presto direttamente alla tua email: <strong>${email}</strong>.
      </div>

      <div style="display: flex; justify-content: center;">
        <button class="btn btn-primary" onclick="document.getElementById('thankyou-info-overlay').classList.remove('active')" style="padding: 0.75rem 2rem; font-size: 0.95rem;">Chiudi</button>
      </div>
    </div>
  `;

  thankYouOverlay.classList.add('active');
}

// 2. RESERVATION MODAL (Prenota Workshop)
function setupReservationModal() {
  const modalBtns = document.querySelectorAll('.open-modal-btn');
  let modalOverlay = document.getElementById('booking-modal-overlay');

  if (!modalOverlay) {
    modalOverlay = document.createElement('div');
    modalOverlay.id = 'booking-modal-overlay';
    modalOverlay.className = 'modal-overlay';

    modalOverlay.innerHTML = `
      <div class="modal-content" style="max-width: 620px;">
        <button id="booking-modal-close" class="modal-close">&times;</button>

        <div style="text-align: center; margin-bottom: 1.5rem;">
          <h3 id="booking-modal-title" style="font-size: 1.6rem; color: var(--accent-cyan);" class="gradient-text">Prenota Workshop Fotografico</h3>
          <p style="color: var(--text-secondary); font-size: 0.875rem;">Compila il form per riservare il tuo posto e procedere con PayPal Business.</p>
        </div>

        <form id="workshop-booking-form">
          <input type="hidden" id="booking-workshop-id" value="workshop-friuli-2026" />
          
          <div class="form-grid">
            <div class="form-group">
              <label class="form-label" for="booking-first-name">Nome *</label>
              <input type="text" id="booking-first-name" class="form-input" placeholder="Es. Mario" required />
            </div>

            <div class="form-group">
              <label class="form-label" for="booking-last-name">Cognome *</label>
              <input type="text" id="booking-last-name" class="form-input" placeholder="Es. Rossi" required />
            </div>
          </div>

          <div class="form-group" style="margin-top: 1rem;">
            <label class="form-label" for="booking-phone">Numero di Telefono *</label>
            <input type="tel" id="booking-phone" class="form-input" placeholder="Es. +39 333 1234567" required />
            <div style="font-size: 0.75rem; color: var(--accent-cyan); margin-top: 0.35rem;">
              ⚠️ Il numero di telefono è essenziale per la creazione del gruppo WhatsApp operativo prima dell'evento.
            </div>
          </div>

          <div class="form-group" style="margin-top: 1rem;">
            <label class="form-label" for="booking-email">Indirizzo Email *</label>
            <input type="email" id="booking-email" class="form-input" placeholder="nome@esempio.com" required />
          </div>

          <!-- FORMULA DI PAGAMENTO PAYPAL -->
          <div style="margin: 1.5rem 0; padding: 1.25rem; background: var(--bg-card); border: 1px solid var(--border-glass); border-radius: var(--radius-md);">
            <h4 style="font-size: 0.95rem; color: var(--accent-cyan); margin-bottom: 0.75rem;">💳 Scegli la Formula di Pagamento (PayPal Business)</h4>
            
            <label style="display: flex; align-items: flex-start; gap: 0.75rem; margin-bottom: 0.85rem; cursor: pointer;">
              <input type="radio" name="paymentFormula" value="caparra" checked style="margin-top: 0.25rem;" />
              <div>
                <strong style="color: var(--text-primary);">Caparra Confirmatoria €50</strong>
                <div style="font-size: 0.8rem; color: var(--text-secondary);">Blocchi il tuo posto ora. Saldo rimanente direttamente in loco all'evento.</div>
              </div>
            </label>

            <label style="display: flex; align-items: flex-start; gap: 0.75rem; cursor: pointer;">
              <input type="radio" name="paymentFormula" value="saldo" style="margin-top: 0.25rem;" />
              <div>
                <strong style="color: var(--text-primary);">Saldo Totale (€290) • Opzione 3 Rate PayPal</strong>
                <div style="font-size: 0.8rem; color: var(--text-secondary);">Saldando il totale puoi selezionare "Paga in 3 rate" direttamente su PayPal senza interessi.</div>
              </div>
            </label>
          </div>

          <!-- POLITICHE DI ANNULLAMENTO -->
          <div style="font-size: 0.775rem; color: var(--text-secondary); background: rgba(255,255,255,0.02); padding: 0.85rem; border-radius: var(--radius-sm); margin-bottom: 1.5rem; border-left: 3px solid var(--accent-purple);">
            <strong>🛡️ Politiche di Annullamento & Refund:</strong><br />
            • <em>Saldo Totale</em>: 100% rimborso fino a 30gg prima • 50% rimborso a 15gg prima.<br />
            • <em>Caparra €50</em>: 100% full refund della caparra a 15gg prima dell'evento.
          </div>

          <button type="submit" class="btn btn-primary" style="width: 100%; padding: 0.9rem; font-size: 1rem; margin-bottom: 1rem;">💳 Conferma & Paga con PayPal Business</button>
          
          <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 0.75rem;">
            <button type="button" class="btn btn-secondary open-info-modal" style="font-size: 0.8rem; padding: 0.5rem; text-align: center;">✉️ Chiedi Info via Email</button>
            <a id="modal-whatsapp-btn" href="https://wa.me/393735096237" target="_blank" class="btn btn-secondary" style="font-size: 0.8rem; padding: 0.5rem; text-align: center; border-color: #25D366; color: #25D366;">💬 Chat WhatsApp</a>
          </div>

        </form>
      </div>
    `;
    document.body.appendChild(modalOverlay);
  }

  const closeBtn = document.getElementById('booking-modal-close');
  if (closeBtn) {
    closeBtn.addEventListener('click', () => modalOverlay.classList.remove('active'));
  }

  modalBtns.forEach(btn => {
    btn.addEventListener('click', (e) => {
      e.preventDefault();
      const subject = btn.getAttribute('data-subject') || 'Workshop Fotografico 2026';
      const workshopId = btn.getAttribute('data-workshop-id') || '';
      
      document.getElementById('booking-modal-title').innerText = `Prenota ${subject}`;
      document.getElementById('booking-workshop-id').value = workshopId;
      document.getElementById('modal-whatsapp-btn').href = `https://wa.me/393735096237?text=${encodeURIComponent('Ciao Davide, vorrei informazioni su ' + subject)}`;

      modalOverlay.classList.add('active');
    });
  });

  const bookingForm = document.getElementById('workshop-booking-form');
  if (bookingForm) {
    bookingForm.addEventListener('submit', async (e) => {
      e.preventDefault();
      
      const workshopId = document.getElementById('booking-workshop-id').value;
      const workshopName = document.getElementById('booking-modal-title').innerText.replace(/^Prenota\s+/, '');
      const firstName = document.getElementById('booking-first-name').value;
      const lastName = document.getElementById('booking-last-name').value;
      const phone = document.getElementById('booking-phone').value;
      const email = document.getElementById('booking-email').value;
      const selectedFormula = document.querySelector('input[name="paymentFormula"]:checked').value;
      try {
        const response = await fetch('/api/create-paypal-order', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({workshopId, formula: selectedFormula, firstName, lastName, phone, email, participants: 1})
        });
        const data = await response.json();
        if (!response.ok || !data.approveUrl) throw new Error(data.detail || 'Impossibile avviare PayPal.');
        window.location.assign(data.approveUrl);
      } catch (error) {
        console.error('Booking error:', error);
        alert(`Prenotazione non completata: ${error.message}`);
      }
    });
  }
}

/* ==========================================================================
   Hero Auto-scrolling Review Slider & Promo Modals (Vanguard / RCE Foto)
   ========================================================================== */

document.addEventListener('DOMContentLoaded', () => {
  setupHeroReviewSlider();
  setupPromoModals();
});

function setupHeroReviewSlider() {
  const slides = document.querySelectorAll('.hero-review-slide');
  const dotsContainer = document.getElementById('hero-reviews-dots');
  if (!slides.length || !dotsContainer) return;

  let currentIndex = 0;
  let intervalId = null;

  // Create dots
  dotsContainer.innerHTML = '';
  slides.forEach((_, idx) => {
    const dot = document.createElement('div');
    dot.className = `dot ${idx === 0 ? 'active' : ''}`;
    dot.addEventListener('click', () => {
      goToSlide(idx);
      resetTimer();
    });
    dotsContainer.appendChild(dot);
  });

  const dots = dotsContainer.querySelectorAll('.dot');

  function goToSlide(index) {
    slides[currentIndex].classList.remove('active');
    dots[currentIndex].classList.remove('active');

    currentIndex = index;

    slides[currentIndex].classList.add('active');
    dots[currentIndex].classList.add('active');
  }

  function nextSlide() {
    const nextIdx = (currentIndex + 1) % slides.length;
    goToSlide(nextIdx);
  }

  function startTimer() {
    intervalId = setInterval(nextSlide, 4000);
  }

  function resetTimer() {
    if (intervalId) clearInterval(intervalId);
    startTimer();
  }

  startTimer();
}

function setupPromoModals() {
  document.addEventListener('click', (e) => {
    const btn = e.target.closest('.open-promo-modal');
    if (!btn) return;
    
    e.preventDefault();
    const promoType = btn.getAttribute('data-promo');
    openPromoModal(promoType);
  });
}

function openPromoModal(type) {
  let modal = document.getElementById('promo-modal-overlay');
  if (!modal) {
    modal = document.createElement('div');
    modal.id = 'promo-modal-overlay';
    modal.className = 'modal-overlay';
    document.body.appendChild(modal);
  }

  let title = '';
  let code = '';
  let desc = '';
  let siteUrl = '';

  if (type === 'vanguard') {
    title = '🎒 Vanguard World Ambassador';
    code = 'DAVIPRO2026';
    desc = 'Risparmia il 20% su tutto il catalogo ufficiale Vanguard World (zaini, treppiedi e borse interne).';
    siteUrl = 'https://www.vanguardworld.it/';
  } else if (type === 'rce') {
    title = '🛍️ RCE Foto Partner Ufficiale';
    code = 'LUONGO5';
    desc = 'Risparmia un ulteriore 5% sull\'acquisto di fotocamere, obiettivi ed attrezzatura usata garantita su RCE Foto.';
    siteUrl = 'https://www.rcefoto.com/';
  }

  modal.innerHTML = `
    <div class="modal-content" style="max-width: 520px; text-align: center; padding: 2.5rem 2rem;">
      <button class="modal-close" onclick="closePromoModal()">&times;</button>
      
      <h3 style="font-size: 1.6rem; color: var(--accent-cyan); margin-bottom: 0.75rem;">${title}</h3>
      <p style="color: var(--text-secondary); font-size: 0.95rem; margin-bottom: 1.5rem;">${desc}</p>
      
      <div style="background: rgba(0, 240, 255, 0.08); border: 2px dashed var(--accent-cyan); border-radius: var(--radius-md); padding: 1.25rem; margin-bottom: 1.75rem; display: flex; align-items: center; justify-content: space-between; gap: 1rem;">
        <span style="font-family: var(--font-heading); font-size: 1.6rem; font-weight: 800; color: #FFFFFF; letter-spacing: 2px;">${code}</span>
        <button type="button" class="btn btn-primary" style="font-size: 0.85rem; padding: 0.5rem 1rem;" onclick="copyPromoCode('${code}')">📋 Copia Codice</button>
      </div>

      <div style="display: flex; gap: 1rem; justify-content: center;">
        <a href="${siteUrl}" target="_blank" rel="noopener noreferrer" class="btn btn-primary" style="width: 100%;">
          Vai al Sito Ufficiale ↗
        </a>
      </div>
    </div>
  `;

  modal.classList.add('active');
}

function closePromoModal() {
  const modal = document.getElementById('promo-modal-overlay');
  if (modal) modal.classList.remove('active');
}

function copyPromoCode(code) {
  navigator.clipboard.writeText(code).then(() => {
    let toast = document.getElementById('toast');
    if (!toast) {
      toast = document.createElement('div');
      toast.id = 'toast';
      toast.className = 'toast';
      document.body.appendChild(toast);
    }
    toast.innerText = `Codice ${code} copiato negli appunti!`;
    toast.classList.add('show');
    setTimeout(() => toast.classList.remove('show'), 3000);
  });
}

/* ==========================================================================
   Multilingual Engine (ITA / ENG Toggle Switcher)
   ========================================================================== */

const DICT_EN = {
  "Home": "Home",
  "Workshop & Tour": "Workshops & Tours",
  "Formazione 1-to-1": "1-on-1 Mentorship",
  "Gear & Attrezzatura": "Gear & Equipment",
  "Blog & Pubblicazioni": "Blog & Articles",
  "Chi Sono": "About Me",
  "Chiedimi Informazioni": "Ask Me Anything",
  "Scegli la tua prossima avventura": "Choose Your Next Adventure",
  "Impara a leggere la luce anche dove sembra non esserci": "Learn to read the light even where it seems absent",
  "Esperienze fotografiche immersive in location straordinarie, viaggi guidati e corsi di formazione One-to-One. Dalla pianificazione sul campo alla stampa Fine Art.": "Immersive photography experiences in extraordinary locations, guided tours, and 1-on-1 coaching. From field planning to Fine Art printing.",
  "Recensioni Google Verificate": "Verified Google Reviews",
  "Vedi tutte su Google ↗": "View all on Google ↗",
  "Esperienze sul campo": "Field Experiences",
  "Workshop & Viaggi Fotografici": "Workshops & Photo Tours",
  "Piccoli gruppi, location selezionate per alba, tramonto e notte, con supporto didattico continuo e pianificazione approfondita.": "Small groups, curated locations for sunrise, sunset and night, with continuous guidance and deep planning.",
  "CALENDARIO 2026": "2026 CALENDAR",
  "Workshop 2026": "2026 Workshops",
  "ANTEPRIMA ESTERO 2027": "2027 OVERSEAS PREVIEW",
  "Viaggi Fotografici 2027": "2027 Photo Tours",
  "🤝 L'UNIONE FA LA FORZA!": "🤝 STRENGTH IN UNITY!",
  "Vi Presento il Team": "Meet the Team",
  "Le cose belle non si fanno mai da soli.": "Great things are never done alone.",
  "Pubblicazioni & Articoli": "Publications & Articles",
  "I miei articoli tecnici su SIGMA Italia, Vanguard World ed UniversoFoto Magazine per approfondire l'attrezzatura ed il flusso di lavoro.": "My technical articles on SIGMA Italia, Vanguard World, and UniversoFoto Magazine covering gear and workflow.",
  "Vedi Tutti gli Articoli": "View All Articles",
  "La Mia Storia": "My Story",
  "Navigazione": "Navigation",
  "Partner Tecnologici": "Tech Partners",
  "Social & Contatti": "Social & Contacts"
};

let currentLang = localStorage.getItem('site_lang') || 'it';

document.addEventListener('DOMContentLoaded', () => {
  if (currentLang === 'en') {
    applyLanguage('en');
  }
});

function switchLanguage(lang) {
  currentLang = lang;
  localStorage.setItem('site_lang', lang);
  applyLanguage(lang);
}

function applyLanguage(lang) {
  const btnIta = document.getElementById('btn-lang-ita');
  const btnEn = document.getElementById('btn-lang-en');

  if (btnIta && btnEn) {
    if (lang === 'en') {
      btnIta.classList.remove('active');
      btnEn.classList.add('active');
    } else {
      btnEn.classList.remove('active');
      btnIta.classList.add('active');
    }
  }

  const textElements = document.querySelectorAll('h1, h2, h3, h4, p, a, span, button');
  textElements.forEach(el => {
    if (el.children.length === 0) {
      const text = el.innerText.trim();
      if (lang === 'en' && DICT_EN[text]) {
        if (!el.dataset.origText) el.dataset.origText = el.innerText;
        el.innerText = DICT_EN[text];
      } else if (lang === 'it' && el.dataset.origText) {
        el.innerText = el.dataset.origText;
      }
    }
  });
}

/* Homepage Blog Preview — alimentato da data/articles.json */
(async function initHomepageBlogPreview() {
  const grid = document.getElementById('homepage-blog-grid');
  if (!grid) return;
  const escapeHtml = value => String(value ?? '').replace(/[&<>"]/g, char => ({
    '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;'
  }[char]));
  const safeUrl = value => {
    const url = String(value ?? '').trim();
    return /^(https?:\/\/|[a-zA-Z0-9_./-]+$)/.test(url) ? url.replace(/^\.\.\//, '') : '#';
  };
  try {
    const response = await fetch('data/articles.json');
    if (!response.ok) throw new Error('Impossibile caricare gli articoli');
    const articles = await response.json();
    articles.sort((a, b) => new Date(b.date) - new Date(a.date));
    const featured = articles.filter(article => article.featured);
    const picks = [...featured, ...articles.filter(article => !article.featured)].slice(0, 3);
    grid.innerHTML = picks.map(article => {
      const external = Boolean(article.external);
      const publisher = escapeHtml(article.publisher);
      const date = new Date(article.date).toLocaleDateString('it-IT', {day:'numeric', month:'long', year:'numeric'});
      return `<div class="blog-card"><div class="blog-img-wrapper">
        <img src="${safeUrl(article.image)}" alt="${escapeHtml(article.title)}" loading="lazy" />
        <span class="badge-blog-type ${external ? 'external' : 'personal'}">${external ? 'Scrivo per gli Altri' : 'Scrivo per Me'}</span>
        </div><div class="blog-body"><div class="publisher-tag">${escapeHtml(article.publisherIcon)} ${publisher}</div>
        <h3 class="blog-title">${escapeHtml(article.title)}</h3><p class="blog-excerpt">${escapeHtml(article.excerpt)}</p>
        <div class="blog-meta"><span>📅 ${escapeHtml(date)}</span>
        <a href="${safeUrl(article.url)}" ${external ? 'target="_blank" rel="noopener noreferrer"' : ''}
        class="btn ${external ? 'btn-primary' : 'btn-secondary'}">${external ? `Leggi su ${publisher.split(' ')[0]} ↗` : "Leggi l'Articolo →"}</a>
        </div></div></div>`;
    }).join('');
  } catch (error) {
    grid.innerHTML = '<p><a href="blog/blog.html">Vai al Blog completo →</a></p>';
  }
})();
