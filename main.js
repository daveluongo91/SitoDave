

/* ==========================================================================
   Hero Auto-scrolling Review Slider & Promo Modals (Vanguard / RCE Foto)
   ========================================================================== */


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
          <div style="margin: 1.5rem 0 1rem 0; padding: 1.25rem; background: var(--bg-card); border: 1px solid var(--border-glass); border-radius: var(--radius-md);">
            <h4 style="font-size: 0.95rem; color: var(--accent-cyan); margin-bottom: 0.85rem;">💳 Modalità di Pagamento</h4>
            
            <label style="display: flex; align-items: flex-start; gap: 0.75rem; margin-bottom: 1rem; cursor: pointer; background: rgba(0, 240, 255, 0.04); padding: 0.85rem; border-radius: var(--radius-sm); border: 1px solid rgba(0, 240, 255, 0.2);">
              <input type="radio" name="paymentFormula" value="caparra" checked style="margin-top: 0.25rem;" onchange="onPaymentFormulaChange()" />
              <div>
                <strong style="color: var(--accent-cyan); font-size: 0.95rem;">Caparra Confirmatoria (€50)</strong>
                <div style="font-size: 0.8rem; color: var(--text-secondary); margin-top: 0.25rem; line-height: 1.5;">
                  Blocchi il tuo posto ora versando <strong>€50</strong>. Il saldo rimanente verrà regolato in loco con la modalità che preferisci tra <strong>Bonifico, Contanti o PayPal</strong>.
                </div>
              </div>
            </label>

            <label style="display: flex; align-items: flex-start; gap: 0.75rem; cursor: pointer; background: rgba(168, 85, 247, 0.06); padding: 0.85rem; border-radius: var(--radius-sm); border: 1px solid rgba(168, 85, 247, 0.2);">
              <input type="radio" name="paymentFormula" value="saldo" style="margin-top: 0.25rem;" onchange="onPaymentFormulaChange()" />
              <div>
                <strong style="color: #D8B4FE; font-size: 0.95rem;">Saldo Totale (€350) • Opzione 3 Rate senza interessi PayPal *</strong>
                <div style="font-size: 0.8rem; color: var(--text-secondary); margin-top: 0.25rem; line-height: 1.5;">
                  Versi il saldo completo (€350) con la possibilità di selezionare l'opzione <strong>"Paga in 3 rate" da €116.66/mese</strong> direttamente su PayPal senza alcun costo aggiuntivo.
                </div>
              </div>
            </label>
          </div>

          <!-- CAMPO CODICE SCONTO -->
          <div style="margin-bottom: 1.25rem;">
            <label class="form-label" for="booking-coupon-input" style="font-size: 0.825rem; color: var(--accent-cyan);">🎟️ Hai un Codice Sconto?</label>
            <div style="display: flex; gap: 0.5rem; margin-top: 0.35rem;">
              <input type="text" id="booking-coupon-input" class="form-input" placeholder="Es. DAVEPRO10" style="text-transform: uppercase; font-family: var(--font-heading); font-weight: 700; letter-spacing: 1px;" />
              <button type="button" class="btn btn-secondary" onclick="applyDiscountCoupon()" style="padding: 0.5rem 1rem; font-size: 0.825rem; white-space: nowrap;">Applica</button>
            </div>
            <div id="coupon-feedback-banner" style="display: none; margin-top: 0.5rem; font-size: 0.8rem; padding: 0.5rem 0.75rem; border-radius: var(--radius-sm);"></div>
          </div>

          <!-- NOTA ASTERISCO RIMBORSO -->
          <div style="font-size: 0.775rem; color: var(--text-secondary); background: rgba(255,255,255,0.02); padding: 0.85rem; border-radius: var(--radius-sm); margin-bottom: 1.5rem; border-left: 3px solid var(--accent-cyan); line-height: 1.5;">
            <strong>* Nota Trasparenza Rimborso:</strong><br />
            Le politiche di annullamento e rimborso si applicano sempre sulla sola quota di caparra (€50). In caso di disdetta entro i termini previsti (15-30 giorni prima dell'evento), l'intero saldo di <strong>€300 ti verrà sempre e comunque rimborsato al 100%</strong>.
          </div>

          <button type="submit" id="booking-submit-btn" class="btn btn-primary" style="width: 100%; padding: 0.9rem; font-size: 1rem; margin-bottom: 1rem;">💳 Conferma & Paga Caparra (€50) con PayPal</button>
          
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
      
      document.getElementById('booking-modal-title').innerText = `Prenota ${subject}`;
      document.getElementById('booking-workshop-id').value = subject;
      document.getElementById('modal-whatsapp-btn').href = `https://wa.me/393735096237?text=${encodeURIComponent('Ciao Davide, vorrei informazioni su ' + subject)}`;

      modalOverlay.classList.add('active');
    });
  });

  const bookingForm = document.getElementById('workshop-booking-form');
  if (bookingForm) {
    bookingForm.addEventListener('submit', (e) => {
      e.preventDefault();
      
      const workshopName = document.getElementById('booking-workshop-id').value;
      const firstName = document.getElementById('booking-first-name').value;
      const lastName = document.getElementById('booking-last-name').value;
      const phone = document.getElementById('booking-phone').value;
      const email = document.getElementById('booking-email').value;
      const selectedFormula = document.querySelector('input[name="paymentFormula"]:checked').value;
      let amount = selectedFormula === 'caparra' ? '€50' : '€350';

      if (selectedFormula === 'saldo' && currentAppliedDiscount) {
        amount = `€${currentAppliedDiscount.finalPrice}`;
      }

      fetch('/api/book-workshop', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          workshopId: workshopName.toLowerCase().replace(/ /g, '-'),
          workshopName: workshopName,
          firstName: firstName,
          lastName: lastName,
          phone: phone,
          email: email,
          paymentFormula: selectedFormula,
          amountPaid: amount,
          couponCode: currentAppliedDiscount ? currentAppliedDiscount.code : ''
        })
      })
      .then(res => res.json())
      .then(data => {
        if (data.status === 'success') {
          modalOverlay.classList.remove('active');
          if (data.paypalUrl) {
            window.location.href = data.paypalUrl;
          } else {
            window.location.href = data.thankYouUrl;
          }
        } else {
          alert('Errore: ' + data.message);
        }
      })
      });
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
