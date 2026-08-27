/* ==========================================================================
   Davide Luongo — Workshop Reservation & Info Request System (Event Delegated)
   ========================================================================== */

document.addEventListener('DOMContentLoaded', () => {
  setupInfoModal();
  setupGlobalClickDelegation();
  updateUrgencyCounters();
  setup3DCarousels();
  setupAwardsModal();
  setupGalleriesModal();
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

/* ==========================================================================
   3D Rotating Carousel Engine (Workshops, Viaggi, Blog & Pubblicazioni)
   ========================================================================== */

function setup3DCarousels() {
  document.querySelectorAll('[data-carousel]').forEach((carousel) => {
    if (carousel.dataset.carouselInit === 'true') return;
    carousel.dataset.carouselInit = 'true';

    const slides = Array.from(carousel.querySelectorAll('[data-slide]'));
    if (!slides.length) return;

    const status = carousel.querySelector('.carousel-status');
    const prevBtn = carousel.querySelector('[data-carousel-prev]');
    const nextBtn = carousel.querySelector('[data-carousel-next]');
    let activeIndex = 0;
    let isRotating = false;

    carousel.tabIndex = 0;
    carousel.setAttribute('aria-label', 'Carosello: clicca sulle card laterali, usa i pulsanti o le frecce della tastiera per ruotare');

    const wrappedDistance = (index) => {
      let distance = index - activeIndex;
      const half = slides.length / 2;
      if (distance > half) distance -= slides.length;
      if (distance < -half) distance += slides.length;
      return distance;
    };

    const render = () => {
      slides.forEach((slide, index) => {
        const distance = wrappedDistance(index);
        slide.classList.remove('is-active', 'is-previous', 'is-next', 'is-hidden');
        if (distance === 0) slide.classList.add('is-active');
        else if (distance === -1) slide.classList.add('is-previous');
        else if (distance === 1) slide.classList.add('is-next');
        else slide.classList.add('is-hidden');
        slide.setAttribute('aria-hidden', Math.abs(distance) > 1 ? 'true' : 'false');
      });

      if (status) {
        status.textContent = `${activeIndex + 1} / ${slides.length}`;
      }
    };

    const rotateTo = (index) => {
      if (index === activeIndex || isRotating) return;
      isRotating = true;
      activeIndex = (index + slides.length) % slides.length;
      render();
      window.setTimeout(() => { isRotating = false; }, 400);
    };

    if (prevBtn) {
      prevBtn.addEventListener('click', (e) => {
        e.preventDefault();
        rotateTo(activeIndex - 1);
      });
    }

    if (nextBtn) {
      nextBtn.addEventListener('click', (e) => {
        e.preventDefault();
        rotateTo(activeIndex + 1);
      });
    }

    slides.forEach((slide, index) => {
      slide.addEventListener('pointerenter', (event) => {
        const isSideCard = slide.classList.contains('is-previous') || slide.classList.contains('is-next');
        if (event.pointerType === 'mouse' && isSideCard) rotateTo(index);
      });

      slide.addEventListener('click', (event) => {
        const isSideCard = slide.classList.contains('is-previous') || slide.classList.contains('is-next');
        if (isSideCard) {
          event.preventDefault();
          rotateTo(index);
        }
      });
    });

    carousel.addEventListener('keydown', (event) => {
      if (event.key === 'ArrowLeft') rotateTo(activeIndex - 1);
      if (event.key === 'ArrowRight') rotateTo(activeIndex + 1);
    });

    // Touch Swipe Support
    let touchStartX = 0;
    let touchEndX = 0;
    carousel.addEventListener('touchstart', (e) => {
      touchStartX = e.changedTouches[0].screenX;
    }, { passive: true });

    carousel.addEventListener('touchend', (e) => {
      touchEndX = e.changedTouches[0].screenX;
      if (touchStartX - touchEndX > 45) {
        rotateTo(activeIndex + 1);
      } else if (touchEndX - touchStartX > 45) {
        rotateTo(activeIndex - 1);
      }
    }, { passive: true });

    render();
  });
}

/* ==========================================================================
   Premi & Riconoscimenti (Awards & Contest Verification Modal System)
   ========================================================================== */

const DEFAULT_AWARDS_DATA = [
  {
    "id": "bpa",
    "name": "Best Photography Awards",
    "shortName": "BPA",
    "badge": "BPA",
    "icon": "🏅",
    "accentColor": "#FFB800",
    "description": "Riconoscimenti internazionali ufficiali assegnati dalla giuria di Best Photography Awards per eccellenza tecnica, astrofotografia e fotografia di paesaggio.",
    "awards": [
      {
        "id": "bpa-silver-3909",
        "year": "2025 / 2026",
        "title": "2° Posto (Silver Medal) • Categoria Nature",
        "work": "Autumn Symphony & Alpine Light (Entry #3909)",
        "badgeText": "Silver Medal (2° Posto)",
        "medalImage": "assets/awards/bpa_silver_medal.png",
        "bannerImage": "assets/awards/bpa_nature_01.jpg",
        "verifyUrl": "https://bestphotographyawards.com/gallery/?type=Amateur&cat=NATURE&entry=3909&place=2nd&form_id=2398"
      },
      {
        "id": "bpa-bronze-3908",
        "year": "2025 / 2026",
        "title": "3° Posto (Bronze Medal) • Categoria Night Photography",
        "work": "Where Mountains Embrace the Sky — Colle del Nivolet (Entry #3908)",
        "badgeText": "Bronze Medal (3° Posto)",
        "medalImage": "assets/awards/bpa_bronze_medal.png",
        "bannerImage": "assets/awards/bpa_night_2025.jpg",
        "verifyUrl": "https://bestphotographyawards.com/gallery/?type=Amateur&cat=NIGHT-PHOTOGRAPHY&entry=3908&place=3rd&form_id=2398"
      },
      {
        "id": "bpa-blue-3908",
        "year": "2025 / 2026",
        "title": "Menzione d'Onore (Blue Medal) • Categoria Nature",
        "work": "Reflections in the Julian Waters — Laghi di Fusine (Entry #3908)",
        "badgeText": "Blue Medal (Honorable Mention)",
        "medalImage": "assets/awards/bpa_blue_medal.png",
        "bannerImage": "assets/awards/bpa_nature_02.jpg",
        "verifyUrl": "https://bestphotographyawards.com/gallery/?type=Amateur&cat=Nature&entry=3908&blue=1&place=HONORABLE%20MENTION&form_id=2398"
      },
      {
        "id": "bpa-blue-4075",
        "year": "2025 / 2026",
        "title": "Menzione d'Onore (Blue Medal) • Categoria Nature",
        "work": "Alpine Forest Mist & Light (Entry #4075)",
        "badgeText": "Blue Medal (Honorable Mention)",
        "medalImage": "assets/awards/bpa_blue_medal.png",
        "bannerImage": "assets/awards/bpa_nature_4075.jpg",
        "verifyUrl": "https://bestphotographyawards.com/gallery/?type=Amateur&cat=Nature&entry=4075&blue=1&place=HONORABLE%20MENTION&form_id=2398"
      },
      {
        "id": "bpa-blue-2477",
        "year": "2024 / 2025",
        "title": "Menzione d'Onore (Blue Medal) • Categoria Nature",
        "work": "Pan di marmotta — Colle del Nivolet (Entry #2477)",
        "badgeText": "Blue Medal (Honorable Mention)",
        "medalImage": "assets/awards/bpa_blue_medal.png",
        "bannerImage": "assets/awards/bpa_nature_02.jpg",
        "verifyUrl": "https://bestphotographyawards.com/gallery/?type=Amateur&cat=Nature&entry=2477&blue=1&place=HONORABLE%20MENTION&form_id=2240"
      }
    ]
  },
  {
    "id": "one-eyeland",
    "name": "One Eyeland",
    "shortName": "One Eyeland",
    "badge": "ONE EYELAND",
    "icon": "👁️",
    "accentColor": "#00F0FF",
    "description": "Riconoscimenti internazionali nel network d'élite One Eyeland per il concorso World's Top 10 Fine Art Photo Contest.",
    "awards": [
      {
        "id": "oe-rank1-italy",
        "year": "2025",
        "title": "World's Top 10 Fine Art Photo Contest • Italy Rank #1",
        "work": "Roque Cinchado under the Galactic Core — Tenerife",
        "badgeText": "Italy Rank #1",
        "bannerImage": "assets/awards/one_eyeland_rank1_italy_2025.jpg",
        "verifyUrl": "https://oneeyeland.com/world-top10-fine-art-photographers-2025"
      },
      {
        "id": "oe-silver-2025",
        "year": "2025",
        "title": "World's Top 10 Fine Art Photo Contest • Silver Award",
        "work": "Roque Cinchado under the Galactic Core — Tenerife",
        "badgeText": "Silver Award",
        "bannerImage": "assets/awards/one_eyeland_silver_2025.jpg",
        "verifyUrl": "https://oneeyeland.com/world-top10-fine-art-photographers-2025"
      }
    ]
  },
  {
    "id": "1x",
    "name": "1x.com",
    "shortName": "1x.com",
    "badge": "1X",
    "icon": "💎",
    "accentColor": "#A855F7",
    "description": "Certificazioni e opere pubblicate e premiate dal team curatoriale di 1x.com, la galleria di fotografia d'arte più selettiva al mondo.",
    "awards": [
      {
        "id": "1x-cert",
        "year": "2024 - 2026",
        "title": "Official Awarded Photographer Certificate",
        "work": "Certificato di Fotografo Premiato Ufficiale • Membro ID 796527",
        "badgeText": "Certificato Ufficiale",
        "bannerImage": "assets/awards/1x_certificate_796527.jpg",
        "verifyUrl": "https://1x.com/member/daveluongo"
      },
      {
        "id": "1x-3496868",
        "year": "2025",
        "title": "Awarded Photograph • Nightscapes & Alps",
        "work": "Curator's Choice Selection #3496868",
        "badgeText": "Awarded",
        "bannerImage": "assets/awards/1x_awarded_3496868.jpg",
        "verifyUrl": "https://1x.com/photo/3496868"
      },
      {
        "id": "1x-3498663",
        "year": "2025",
        "title": "Awarded Photograph • Landscape Mood",
        "work": "Curator's Choice Selection #3498663",
        "badgeText": "Awarded",
        "bannerImage": "assets/awards/1x_awarded_3498663.jpg",
        "verifyUrl": "https://1x.com/photo/3498663"
      },
      {
        "id": "1x-3505996",
        "year": "2025",
        "title": "Awarded Photograph • Vertical Fine Art",
        "work": "Curator's Choice Selection #3505996",
        "badgeText": "Awarded",
        "bannerImage": "assets/awards/1x_awarded_3505996.jpg",
        "verifyUrl": "https://1x.com/photo/3505996"
      },
      {
        "id": "1x-3568397",
        "year": "2025",
        "title": "Awarded Photograph • Atmosphere & Silence",
        "work": "Curator's Choice Selection #3568397",
        "badgeText": "Awarded",
        "bannerImage": "assets/awards/1x_awarded_3568397.jpg",
        "verifyUrl": "https://1x.com/photo/3568397"
      },
      {
        "id": "1x-3576087",
        "year": "2025",
        "title": "Awarded Photograph • Water & Long Exposure",
        "work": "Curator's Choice Selection #3576087",
        "badgeText": "Awarded",
        "bannerImage": "assets/awards/1x_awarded_3576087.jpg",
        "verifyUrl": "https://1x.com/photo/3576087"
      },
      {
        "id": "1x-3598273",
        "year": "2025",
        "title": "Awarded Photograph • Mountain Geometry",
        "work": "Curator's Choice Selection #3598273",
        "badgeText": "Awarded",
        "bannerImage": "assets/awards/1x_awarded_3598273.jpg",
        "verifyUrl": "https://1x.com/photo/3598273"
      }
    ]
  }
];

let awardsStore = DEFAULT_AWARDS_DATA;

async function setupAwardsModal() {
  try {
    const res = await fetch('data/awards.json');
    if (res.ok) {
      const data = await res.json();
      if (Array.isArray(data) && data.length) {
        awardsStore = data;
      }
    }
  } catch (e) {
    // Usa fallback predefinito
  }

  // Aggiorna i contatori incrementali su ciascun pulsante concorso
  awardsStore.forEach(contest => {
    const countEl = document.querySelector(`[data-award-count="${contest.id}"]`);
    if (countEl) {
      countEl.textContent = contest.awards ? contest.awards.length : 0;
    }
  });

  // Event delegation per i click sui pulsanti concorso
  document.addEventListener('click', (e) => {
    const btn = e.target.closest('.award-contest-btn');
    if (btn) {
      e.preventDefault();
      const contestId = btn.getAttribute('data-award-contest');
      openAwardContestModal(contestId);
      return;
    }

    const verifyBtn = e.target.closest('.award-verify-btn');
    if (verifyBtn) {
      e.preventDefault();
      const contestId = verifyBtn.getAttribute('data-contest-id');
      const awardId = verifyBtn.getAttribute('data-award-id');
      openAwardVerificationModal(contestId, awardId);
    }
  });
}

function openAwardContestModal(contestId) {
  const contest = awardsStore.find(c => c.id === contestId);
  if (!contest) return;

  let modal = document.getElementById('award-modal-overlay');
  if (!modal) {
    modal = document.createElement('div');
    modal.id = 'award-modal-overlay';
    modal.className = 'modal-overlay';
    document.body.appendChild(modal);
  }

  const escapeHtml = str => String(str ?? '').replace(/[&<>"]/g, c => ({
    '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;'
  }[c]));

  const awardsListHtml = (contest.awards || []).map(a => `
    <div class="award-item-card" style="display: flex; flex-direction: row; gap: 1.25rem; align-items: center; justify-content: space-between; flex-wrap: wrap;">
      <div style="display: flex; gap: 1rem; align-items: center; flex: 1; min-width: 260px;">
        ${a.medalImage ? `<img src="${escapeHtml(a.medalImage)}" alt="Medaglia ${escapeHtml(a.badgeText)}" style="width: 52px; height: 52px; object-fit: contain; flex-shrink: 0; filter: drop-shadow(0 2px 8px rgba(0,0,0,0.5));" />` : ''}
        ${a.bannerImage && !a.medalImage ? `<img src="${escapeHtml(a.bannerImage)}" alt="${escapeHtml(a.title)}" style="width: 64px; height: 64px; object-fit: cover; border-radius: var(--radius-sm); border: 1px solid var(--border-glass); flex-shrink: 0;" />` : ''}
        <div>
          <div class="award-item-header" style="margin-bottom: 0.25rem;">
            <span class="award-item-tag" style="background: rgba(255, 184, 0, 0.15); color: ${contest.accentColor || '#FFB800'}; border-color: ${contest.accentColor || '#FFB800'};">
              ${escapeHtml(a.badgeText || 'Riconoscimento')}
            </span>
            <span class="award-item-year">📅 ${escapeHtml(a.year)}</span>
          </div>
          <h4 class="award-item-title" style="font-size: 1.05rem;">${escapeHtml(a.title)}</h4>
          <div class="award-item-work" style="font-size: 0.84rem;">📷 Opera: <strong>${escapeHtml(a.work)}</strong></div>
        </div>
      </div>
      <button type="button" class="btn btn-primary award-verify-btn" data-contest-id="${contest.id}" data-award-id="${a.id}" style="align-self: center; white-space: nowrap;">
        🔍 Mostra Certificato ↗
      </button>
    </div>
  `).join('');

  modal.innerHTML = `
    <div class="modal-content" style="max-width: 740px; max-height: 88vh; overflow-y: auto; text-align: left; padding: 2.25rem 2rem;">
      <button class="modal-close" onclick="closeAwardModal()">&times;</button>
      
      <div style="display: flex; align-items: center; justify-content: space-between; border-bottom: 1px solid var(--border-glass); padding-bottom: 1rem; margin-bottom: 1.25rem; flex-wrap: wrap; gap: 0.5rem;">
        <div style="display: flex; align-items: center; gap: 0.6rem;">
          <span style="font-size: 1.8rem;">${contest.icon}</span>
          <h3 style="font-size: 1.5rem; color: var(--accent-cyan); margin: 0;">${escapeHtml(contest.name)}</h3>
        </div>
        <span class="award-contest-count" style="font-size: 0.82rem; padding: 0.25rem 0.75rem;">
          ${contest.awards ? contest.awards.length : 0} Riconoscimenti Ufficiali
        </span>
      </div>

      <p style="color: var(--text-secondary); font-size: 0.92rem; line-height: 1.6; margin-bottom: 1.5rem;">
        ${escapeHtml(contest.description)}
      </p>

      <div class="awards-items-wrapper">
        ${awardsListHtml}
      </div>

      <div style="text-align: center; margin-top: 1.5rem; border-top: 1px solid var(--border-glass); padding-top: 1.25rem;">
        <button type="button" class="btn btn-secondary" onclick="closeAwardModal()" style="padding: 0.6rem 2rem; font-size: 0.9rem;">
          Chiudi
        </button>
      </div>
    </div>
  `;

  modal.classList.add('active');
}

function openAwardVerificationModal(contestId, awardId) {
  const contest = awardsStore.find(c => c.id === contestId);
  if (!contest) return;
  const award = (contest.awards || []).find(a => a.id === awardId);
  if (!award) return;

  let verifyModal = document.getElementById('award-verify-modal-overlay');
  if (!verifyModal) {
    verifyModal = document.createElement('div');
    verifyModal.id = 'award-verify-modal-overlay';
    verifyModal.className = 'modal-overlay';
    verifyModal.style.zIndex = '99999';
    document.body.appendChild(verifyModal);
  }

  const escapeHtml = str => String(str ?? '').replace(/[&<>"]/g, c => ({
    '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;'
  }[c]));

  verifyModal.innerHTML = `
    <div class="modal-content" style="max-width: 680px; text-align: center; padding: 2rem 1.75rem;">
      <button class="modal-close" onclick="closeAwardVerifyModal()">&times;</button>
      
      <div style="font-size: 2.2rem; margin-bottom: 0.35rem;">🏆</div>
      <h3 style="font-size: 1.35rem; color: var(--accent-cyan); margin-bottom: 0.25rem;">Certificato &amp; Banner Ufficiale</h3>
      <div style="font-size: 0.88rem; color: var(--text-muted); margin-bottom: 1rem;">
        ${escapeHtml(contest.name)} • Edizione ${escapeHtml(award.year)}
      </div>

      <div style="position: relative; overflow: hidden; border-radius: var(--radius-md); max-height: 56vh; background: #000; display: flex; align-items: center; justify-content: center; border: 1px solid var(--border-glow); box-shadow: 0 10px 30px rgba(0,0,0,0.6); margin-bottom: 1.25rem;">
        <img src="${escapeHtml(award.bannerImage)}" alt="${escapeHtml(award.title)}" style="width: 100%; height: auto; max-height: 54vh; object-fit: contain;" />
      </div>

      <div style="text-align: left; background: rgba(255,255,255,0.03); border: 1px solid var(--border-glass); border-radius: var(--radius-sm); padding: 0.85rem 1.1rem; margin-bottom: 1.25rem;">
        <div style="font-size: 1.05rem; font-weight: 700; color: #fff; margin-bottom: 0.25rem;">${escapeHtml(award.title)}</div>
        <div style="font-size: 0.84rem; color: var(--text-secondary);">Opera / Assegnazione: <em>${escapeHtml(award.work)}</em></div>
      </div>

      <div style="display: flex; justify-content: center; gap: 0.75rem; flex-wrap: wrap;">
        ${award.verifyUrl && award.verifyUrl !== '#' ? `
          <a href="${escapeHtml(award.verifyUrl)}" target="_blank" rel="noopener noreferrer" class="btn btn-primary" style="padding: 0.6rem 1.6rem; font-size: 0.88rem;">
            Verifica su ${escapeHtml(contest.shortName || contest.name)} ↗
          </a>
        ` : ''}
        <button type="button" class="btn btn-secondary" onclick="closeAwardVerifyModal()" style="padding: 0.6rem 1.6rem; font-size: 0.88rem;">
          Torna all'Elenco
        </button>
      </div>
    </div>
  `;

  verifyModal.classList.add('active');
}

function closeAwardModal() {
  const modal = document.getElementById('award-modal-overlay');
  if (modal) modal.classList.remove('active');
}

function closeAwardVerifyModal() {
  const modal = document.getElementById('award-verify-modal-overlay');
  if (modal) modal.classList.remove('active');
}

/* ==========================================================================
   Gallerie Fotografiche (Modal & Immersive Lightbox Engine)
   ========================================================================== */

const DEFAULT_GALLERIES_DATA = [
  {
    "id": "islanda",
    "name": "Islanda",
    "title": "Galleria Fotografica • Islanda",
    "coverImage": "assets/galleries/cover_islanda.jpg",
    "accentColor": "#00F0FF",
    "description": "Un viaggio visivo tra aurore boreali, cascate impetuose, ghiacciai millenari e desolazioni vulcaniche d'Islanda.",
    "photos": [
      {
        "id": "islanda-01",
        "filename": "1X_02_awarded-3505996.jpg",
        "badge": "1X Awarded",
        "image": "assets/galleries/islanda/islanda_01_1X_02_awarded-3505996.jpg"
      },
      {
        "id": "islanda-02",
        "filename": "1X_03_published-3496438.jpg",
        "badge": "1X Published",
        "image": "assets/galleries/islanda/islanda_02_1X_03_published-3496438.jpg"
      },
      {
        "id": "islanda-03",
        "filename": "1X_04_published-3503283.jpg",
        "badge": "1X Published",
        "image": "assets/galleries/islanda/islanda_03_1X_04_published-3503283.jpg"
      },
      {
        "id": "islanda-04",
        "filename": "1X_05_published-3504458.jpg",
        "badge": "1X Published",
        "image": "assets/galleries/islanda/islanda_04_1X_05_published-3504458.jpg"
      },
      {
        "id": "islanda-05",
        "filename": "1X_06_published-3505996.jpg",
        "badge": "1X Published",
        "image": "assets/galleries/islanda/islanda_05_1X_06_published-3505996.jpg"
      },
      {
        "id": "islanda-06",
        "filename": "1X_07_published-3517205.jpg",
        "badge": "1X Published",
        "image": "assets/galleries/islanda/islanda_06_1X_07_published-3517205.jpg"
      },
      {
        "id": "islanda-07",
        "filename": "1X_08_published-3635693.jpg",
        "badge": "1X Published",
        "image": "assets/galleries/islanda/islanda_07_1X_08_published-3635693.jpg"
      },
      {
        "id": "islanda-08",
        "filename": "1X_01_accepted-3515028.jpg",
        "badge": "1X Accepted",
        "image": "assets/galleries/islanda/islanda_08_1X_01_accepted-3515028.jpg"
      },
      {
        "id": "islanda-09",
        "filename": "TOP10_02_BF_00060-Enhanced-NR.jpg",
        "badge": null,
        "image": "assets/galleries/islanda/islanda_09_TOP10_02_BF_00060-Enhanced-NR.jpg"
      },
      {
        "id": "islanda-10",
        "filename": "TOP10_04_BF_00105-Edit.jpg",
        "badge": null,
        "image": "assets/galleries/islanda/islanda_10_TOP10_04_BF_00105-Edit.jpg"
      },
      {
        "id": "islanda-11",
        "filename": "TOP10_05_IMG01623.jpg",
        "badge": null,
        "image": "assets/galleries/islanda/islanda_11_TOP10_05_IMG01623.jpg"
      },
      {
        "id": "islanda-12",
        "filename": "TOP10_07_FPL00171-Edit_M_1.jpg",
        "badge": null,
        "image": "assets/galleries/islanda/islanda_12_TOP10_07_FPL00171-Edit_M_1.jpg"
      },
      {
        "id": "islanda-13",
        "filename": "TOP10_08_A7R00028-Edit.jpg",
        "badge": null,
        "image": "assets/galleries/islanda/islanda_13_TOP10_08_A7R00028-Edit.jpg"
      },
      {
        "id": "islanda-14",
        "filename": "A7R00001-Enhanced-NR-Edit.jpg",
        "badge": null,
        "image": "assets/galleries/islanda/islanda_14_A7R00001-Enhanced-NR-Edit.jpg"
      },
      {
        "id": "islanda-15",
        "filename": "A7R00018-Edit_K_1.jpg",
        "badge": null,
        "image": "assets/galleries/islanda/islanda_15_A7R00018-Edit_K_1.jpg"
      },
      {
        "id": "islanda-16",
        "filename": "A7R00074-Edit.jpg",
        "badge": null,
        "image": "assets/galleries/islanda/islanda_16_A7R00074-Edit.jpg"
      },
      {
        "id": "islanda-17",
        "filename": "A7R00076-Enhanced-NR.jpg",
        "badge": null,
        "image": "assets/galleries/islanda/islanda_17_A7R00076-Enhanced-NR.jpg"
      },
      {
        "id": "islanda-18",
        "filename": "A7R00081-Edit.jpg",
        "badge": null,
        "image": "assets/galleries/islanda/islanda_18_A7R00081-Edit.jpg"
      },
      {
        "id": "islanda-19",
        "filename": "A7R00329-Enhanced-NR-Edit.jpg",
        "badge": null,
        "image": "assets/galleries/islanda/islanda_19_A7R00329-Enhanced-NR-Edit.jpg"
      },
      {
        "id": "islanda-20",
        "filename": "DSC00021_I_1.jpg",
        "badge": null,
        "image": "assets/galleries/islanda/islanda_20_DSC00021_I_1.jpg"
      },
      {
        "id": "islanda-21",
        "filename": "FPL00131-Edit_M_1.jpg",
        "badge": null,
        "image": "assets/galleries/islanda/islanda_21_FPL00131-Edit_M_1.jpg"
      },
      {
        "id": "islanda-22",
        "filename": "FPL00179-HDR-Edit.jpg",
        "badge": null,
        "image": "assets/galleries/islanda/islanda_22_FPL00179-HDR-Edit.jpg"
      },
      {
        "id": "islanda-23",
        "filename": "FPL00195-Edit.jpg",
        "badge": null,
        "image": "assets/galleries/islanda/islanda_23_FPL00195-Edit.jpg"
      },
      {
        "id": "islanda-24",
        "filename": "Kirkjufell_NorthernLights_2.jpg",
        "badge": null,
        "image": "assets/galleries/islanda/islanda_24_Kirkjufell_NorthernLights_2.jpg"
      }
    ]
  },
  {
    "id": "madeira",
    "name": "Madeira",
    "title": "Galleria Fotografica • Madeira",
    "coverImage": "assets/galleries/cover_madeira.jpg",
    "accentColor": "#A855F7",
    "description": "L'isola dell'eterna primavera: scogliere a picco sull'oceano, la foresta millenaria di Fanal e vette che emergono dalle nuvole.",
    "photos": [
      {
        "id": "madeira-01",
        "filename": "1X_03_awarded-3498663.jpg",
        "badge": "1X Awarded",
        "image": "assets/galleries/madeira/madeira_01_1X_03_awarded-3498663.jpg"
      },
      {
        "id": "madeira-02",
        "filename": "1X_04_published-3635688.jpg",
        "badge": "1X Published",
        "image": "assets/galleries/madeira/madeira_02_1X_04_published-3635688.jpg"
      },
      {
        "id": "madeira-03",
        "filename": "1X_05_published-3498663.jpg",
        "badge": "1X Published",
        "image": "assets/galleries/madeira/madeira_03_1X_05_published-3498663.jpg"
      },
      {
        "id": "madeira-04",
        "filename": "1X_01_accepted-3520093.jpg",
        "badge": "1X Accepted",
        "image": "assets/galleries/madeira/madeira_04_1X_01_accepted-3520093.jpg"
      },
      {
        "id": "madeira-05",
        "filename": "1X_02_accepted-3635692.jpg",
        "badge": "1X Accepted",
        "image": "assets/galleries/madeira/madeira_05_1X_02_accepted-3635692.jpg"
      },
      {
        "id": "madeira-06",
        "filename": "TOP10_02_BF_01400-Edit.jpg",
        "badge": null,
        "image": "assets/galleries/madeira/madeira_06_TOP10_02_BF_01400-Edit.jpg"
      },
      {
        "id": "madeira-07",
        "filename": "TOP10_03_A7R00463-HDR-Edit.jpg",
        "badge": null,
        "image": "assets/galleries/madeira/madeira_07_TOP10_03_A7R00463-HDR-Edit.jpg"
      },
      {
        "id": "madeira-08",
        "filename": "TOP10_04_BF_01641-Edit.jpg",
        "badge": null,
        "image": "assets/galleries/madeira/madeira_08_TOP10_04_BF_01641-Edit.jpg"
      },
      {
        "id": "madeira-09",
        "filename": "TOP10_05_A7R00317-Edit.jpg",
        "badge": null,
        "image": "assets/galleries/madeira/madeira_09_TOP10_05_A7R00317-Edit.jpg"
      },
      {
        "id": "madeira-10",
        "filename": "TOP10_06_A7R00305-Edit.jpg",
        "badge": null,
        "image": "assets/galleries/madeira/madeira_10_TOP10_06_A7R00305-Edit.jpg"
      },
      {
        "id": "madeira-11",
        "filename": "TOP10_07_A7R00374-Pano_Edit-Recovered1.jpg",
        "badge": null,
        "image": "assets/galleries/madeira/madeira_11_TOP10_07_A7R00374-Pano_Edit-Recovered1.jpg"
      },
      {
        "id": "madeira-12",
        "filename": "TOP10_08_A7R00033.jpg",
        "badge": null,
        "image": "assets/galleries/madeira/madeira_12_TOP10_08_A7R00033.jpg"
      },
      {
        "id": "madeira-13",
        "filename": "TOP10_09_A7R00019-Edit_M_1.jpg",
        "badge": null,
        "image": "assets/galleries/madeira/madeira_13_TOP10_09_A7R00019-Edit_M_1.jpg"
      },
      {
        "id": "madeira-14",
        "filename": "TOP10_10_BF_01560-Enhanced-NR-Edit.jpg",
        "badge": null,
        "image": "assets/galleries/madeira/madeira_14_TOP10_10_BF_01560-Enhanced-NR-Edit.jpg"
      }
    ]
  },
  {
    "id": "tenerife",
    "name": "Tenerife",
    "title": "Galleria Fotografica • Tenerife",
    "coverImage": "assets/galleries/cover_tenerife.jpg",
    "accentColor": "#FFB800",
    "description": "Paesaggi lunari del Parco Nazionale del Teide, mari di nubi e uno dei cieli stellati Starlight più puri del pianeta.",
    "photos": [
      {
        "id": "tenerife-01",
        "filename": "1X_02_awarded-3496868.jpg",
        "badge": "1X Awarded",
        "image": "assets/galleries/tenerife/tenerife_01_1X_02_awarded-3496868.jpg"
      },
      {
        "id": "tenerife-02",
        "filename": "1X_03_awarded-3598273.jpg",
        "badge": "1X Awarded",
        "image": "assets/galleries/tenerife/tenerife_02_1X_03_awarded-3598273.jpg"
      },
      {
        "id": "tenerife-03",
        "filename": "1X_06_awarded-3568397.jpg",
        "badge": "1X Awarded",
        "image": "assets/galleries/tenerife/tenerife_03_1X_06_awarded-3568397.jpg"
      },
      {
        "id": "tenerife-04",
        "filename": "1X_04_published-3635687.jpg",
        "badge": "1X Published",
        "image": "assets/galleries/tenerife/tenerife_04_1X_04_published-3635687.jpg"
      },
      {
        "id": "tenerife-05",
        "filename": "1X_07_published-3496868.jpg",
        "badge": "1X Published",
        "image": "assets/galleries/tenerife/tenerife_05_1X_07_published-3496868.jpg"
      },
      {
        "id": "tenerife-06",
        "filename": "1X_08_published-3523236.jpg",
        "badge": "1X Published",
        "image": "assets/galleries/tenerife/tenerife_06_1X_08_published-3523236.jpg"
      },
      {
        "id": "tenerife-07",
        "filename": "1X_09_published-3524421.jpg",
        "badge": "1X Published",
        "image": "assets/galleries/tenerife/tenerife_07_1X_09_published-3524421.jpg"
      },
      {
        "id": "tenerife-08",
        "filename": "1X_10_published-3525966.jpg",
        "badge": "1X Published",
        "image": "assets/galleries/tenerife/tenerife_08_1X_10_published-3525966.jpg"
      },
      {
        "id": "tenerife-09",
        "filename": "1X_11_published-3568397.jpg",
        "badge": "1X Published",
        "image": "assets/galleries/tenerife/tenerife_09_1X_11_published-3568397.jpg"
      },
      {
        "id": "tenerife-10",
        "filename": "1X_12_published-3598273.jpg",
        "badge": "1X Published",
        "image": "assets/galleries/tenerife/tenerife_10_1X_12_published-3598273.jpg"
      },
      {
        "id": "tenerife-11",
        "filename": "1X_13_published-3617243.jpg",
        "badge": "1X Published",
        "image": "assets/galleries/tenerife/tenerife_11_1X_13_published-3617243.jpg"
      },
      {
        "id": "tenerife-12",
        "filename": "1X_14_published-3668829.jpg",
        "badge": "1X Published",
        "image": "assets/galleries/tenerife/tenerife_12_1X_14_published-3668829.jpg"
      },
      {
        "id": "tenerife-13",
        "filename": "1X_01_accepted-3598271.jpg",
        "badge": "1X Accepted",
        "image": "assets/galleries/tenerife/tenerife_13_1X_01_accepted-3598271.jpg"
      },
      {
        "id": "tenerife-14",
        "filename": "1X_05_accepted-3700272.jpg",
        "badge": "1X Accepted",
        "image": "assets/galleries/tenerife/tenerife_14_1X_05_accepted-3700272.jpg"
      },
      {
        "id": "tenerife-15",
        "filename": "TOP10_02_IMG00023-Edit.jpg",
        "badge": null,
        "image": "assets/galleries/tenerife/tenerife_15_TOP10_02_IMG00023-Edit.jpg"
      },
      {
        "id": "tenerife-16",
        "filename": "TOP10_03_IMG00012-Modifica.jpg",
        "badge": null,
        "image": "assets/galleries/tenerife/tenerife_16_TOP10_03_IMG00012-Modifica.jpg"
      },
      {
        "id": "tenerife-17",
        "filename": "TOP10_04_A7R00256-Edit.jpg",
        "badge": null,
        "image": "assets/galleries/tenerife/tenerife_17_TOP10_04_A7R00256-Edit.jpg"
      },
      {
        "id": "tenerife-18",
        "filename": "TOP10_05_A7R00018-Edit.jpg",
        "badge": null,
        "image": "assets/galleries/tenerife/tenerife_18_TOP10_05_A7R00018-Edit.jpg"
      },
      {
        "id": "tenerife-19",
        "filename": "TOP10_08_IMG00301-Edit.jpg",
        "badge": null,
        "image": "assets/galleries/tenerife/tenerife_19_TOP10_08_IMG00301-Edit.jpg"
      },
      {
        "id": "tenerife-20",
        "filename": "TOP10_09_A7R04063-Edit-3.jpg",
        "badge": null,
        "image": "assets/galleries/tenerife/tenerife_20_TOP10_09_A7R04063-Edit-3.jpg"
      },
      {
        "id": "tenerife-21",
        "filename": "35mm.jpg",
        "badge": null,
        "image": "assets/galleries/tenerife/tenerife_21_35mm.jpg"
      },
      {
        "id": "tenerife-22",
        "filename": "A6700062-Edit.jpg",
        "badge": null,
        "image": "assets/galleries/tenerife/tenerife_22_A6700062-Edit.jpg"
      },
      {
        "id": "tenerife-23",
        "filename": "A7R00060-Edit.jpg",
        "badge": null,
        "image": "assets/galleries/tenerife/tenerife_23_A7R00060-Edit.jpg"
      },
      {
        "id": "tenerife-24",
        "filename": "A7R00417-Edit_M_1.jpg",
        "badge": null,
        "image": "assets/galleries/tenerife/tenerife_24_A7R00417-Edit_M_1.jpg"
      },
      {
        "id": "tenerife-25",
        "filename": "A7R00452-Edit.jpg",
        "badge": null,
        "image": "assets/galleries/tenerife/tenerife_25_A7R00452-Edit.jpg"
      },
      {
        "id": "tenerife-26",
        "filename": "A7R04059-Edit-2.jpg",
        "badge": null,
        "image": "assets/galleries/tenerife/tenerife_26_A7R04059-Edit-2.jpg"
      },
      {
        "id": "tenerife-27",
        "filename": "IMG00104-Modifica-2.jpg",
        "badge": null,
        "image": "assets/galleries/tenerife/tenerife_27_IMG00104-Modifica-2.jpg"
      },
      {
        "id": "tenerife-28",
        "filename": "Playa_Amarilla_Post.jpg",
        "badge": null,
        "image": "assets/galleries/tenerife/tenerife_28_Playa_Amarilla_Post.jpg"
      }
    ]
  }
];

let galleriesStore = DEFAULT_GALLERIES_DATA;
let currentActiveGallery = null;
let currentLightboxIndex = 0;

async function setupGalleriesModal() {
  try {
    const res = await fetch('data/galleries.json');
    if (res.ok) {
      const data = await res.json();
      if (Array.isArray(data) && data.length > 0) {
        galleriesStore = data;
      }
    }
  } catch (err) {
    // Fallback su DEFAULT_GALLERIES_DATA
  }

  document.addEventListener('click', e => {
    // Click su card galleria
    const card = e.target.closest('.gallery-vertical-card');
    if (card) {
      e.preventDefault();
      const galleryId = card.getAttribute('data-gallery-id');
      openGalleryModal(galleryId);
      return;
    }

    // Click su thumbnail foto all'interno della modale
    const photoItem = e.target.closest('.gallery-photo-item');
    if (photoItem) {
      e.preventDefault();
      const index = parseInt(photoItem.getAttribute('data-photo-index'), 10);
      openGalleryLightbox(index);
      return;
    }
  });

  // Accessibilita tastiera per card
  document.addEventListener('keydown', e => {
    if (e.key === 'Enter' || e.key === ' ') {
      const card = document.activeElement.closest('.gallery-vertical-card');
      if (card) {
        e.preventDefault();
        const galleryId = card.getAttribute('data-gallery-id');
        openGalleryModal(galleryId);
      }
    } else if (e.key === 'Escape') {
      const lb = document.getElementById('gallery-lightbox-overlay');
      if (lb && lb.classList.contains('active')) {
        closeGalleryLightbox();
      } else {
        closeGalleryModal();
      }
    } else if (e.key === 'ArrowLeft') {
      const lb = document.getElementById('gallery-lightbox-overlay');
      if (lb && lb.classList.contains('active')) {
        prevLightboxPhoto();
      }
    } else if (e.key === 'ArrowRight') {
      const lb = document.getElementById('gallery-lightbox-overlay');
      if (lb && lb.classList.contains('active')) {
        nextLightboxPhoto();
      }
    }
  });
}

function openGalleryModal(galleryId) {
  const gallery = galleriesStore.find(g => g.id === galleryId);
  if (!gallery) return;
  currentActiveGallery = gallery;

  let modal = document.getElementById('gallery-modal-overlay');
  if (!modal) {
    modal = document.createElement('div');
    modal.id = 'gallery-modal-overlay';
    modal.className = 'modal-overlay';
    modal.style.zIndex = '99990';
    document.body.appendChild(modal);
  }

  const escapeHtml = str => String(str ?? '').replace(/[&<>"]/g, c => ({
    '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;'
  }[c]));

  const photosHtml = (gallery.photos || []).map((photo, idx) => {
    let badgeHtml = '';
    if (photo.badge === '1X Awarded') {
      badgeHtml = '<span class="gallery-photo-badge badge-awarded">🏆 1X Awarded</span>';
    } else if (photo.badge === '1X Published') {
      badgeHtml = '<span class="gallery-photo-badge badge-published">⭐ 1X Published</span>';
    } else if (photo.badge === '1X Accepted') {
      badgeHtml = '<span class="gallery-photo-badge badge-accepted">✨ 1X Accepted</span>';
    }

    return `
      <div class="gallery-photo-item" data-photo-index="${idx}" tabindex="0" role="button" aria-label="Visualizza foto a schermo intero">
        ${badgeHtml}
        <img src="${escapeHtml(photo.image)}" alt="Fotografia ${escapeHtml(gallery.name)}" class="gallery-photo-thumb" loading="lazy" />
      </div>
    `;
  }).join('');

  modal.innerHTML = `
    <div class="modal-content" style="max-width: 1140px; max-height: 92vh; overflow-y: auto; text-align: left; padding: 2.25rem 2rem;">
      <button class="modal-close" onclick="closeGalleryModal()">&times;</button>
      
      <div style="display: flex; align-items: center; justify-content: space-between; border-bottom: 1px solid var(--border-glass); padding-bottom: 1.25rem; margin-bottom: 1.25rem; flex-wrap: wrap; gap: 0.75rem;">
        <div>
          <span style="font-size: 0.8rem; font-weight: 700; color: var(--accent-cyan); text-transform: uppercase; letter-spacing: 0.12em;">Galleria Fotografica</span>
          <h3 style="font-size: 2rem; color: #fff; margin: 0.25rem 0 0 0; font-family: var(--font-heading);">${escapeHtml(gallery.name)}</h3>
        </div>
      </div>

      <p style="color: var(--text-secondary); font-size: 0.95rem; line-height: 1.6; margin-bottom: 1.75rem; max-width: 860px;">
        ${escapeHtml(gallery.description)}
      </p>

      <div class="gallery-modal-grid">
        ${photosHtml}
      </div>

      <div style="text-align: center; margin-top: 2.5rem; border-top: 1px solid var(--border-glass); padding-top: 1.5rem;">
        <button type="button" class="btn btn-secondary" onclick="closeGalleryModal()" style="padding: 0.65rem 2.5rem; font-size: 0.95rem;">
          Chiudi Galleria
        </button>
      </div>
    </div>
  `;

  modal.classList.add('active');
}

function openGalleryLightbox(index) {
  if (!currentActiveGallery || !currentActiveGallery.photos) return;
  currentLightboxIndex = index;
  const photo = currentActiveGallery.photos[index];
  if (!photo) return;

  let lb = document.getElementById('gallery-lightbox-overlay');
  if (!lb) {
    lb = document.createElement('div');
    lb.id = 'gallery-lightbox-overlay';
    lb.className = 'modal-overlay';
    lb.style.zIndex = '99999';
    document.body.appendChild(lb);
  }

  const escapeHtml = str => String(str ?? '').replace(/[&<>"]/g, c => ({
    '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;'
  }[c]));

  let badgeHtml = '';
  if (photo.badge === '1X Awarded') {
    badgeHtml = '<span class="gallery-photo-badge badge-awarded" style="position: static; font-size: 0.85rem; padding: 0.35rem 0.85rem;">🏆 1X Awarded</span>';
  } else if (photo.badge === '1X Published') {
    badgeHtml = '<span class="gallery-photo-badge badge-published" style="position: static; font-size: 0.85rem; padding: 0.35rem 0.85rem;">⭐ 1X Published</span>';
  } else if (photo.badge === '1X Accepted') {
    badgeHtml = '<span class="gallery-photo-badge badge-accepted" style="position: static; font-size: 0.85rem; padding: 0.35rem 0.85rem;">✨ 1X Accepted</span>';
  }

  lb.innerHTML = `
    <div class="gallery-lightbox-modal">
      <button type="button" class="lightbox-close-btn" onclick="closeGalleryLightbox()" aria-label="Chiudi (Esc)" title="Chiudi (Esc)">✕</button>
      
      <!-- Frecce di Navigazione Laterali -->
      <button type="button" class="lightbox-nav-arrow prev" onclick="prevLightboxPhoto()" aria-label="Foto precedente (Freccia Sinistra)">&#10094;</button>
      <button type="button" class="lightbox-nav-arrow next" onclick="nextLightboxPhoto()" aria-label="Foto successiva (Freccia Destra)">&#10095;</button>

      <div style="position: relative; overflow: hidden; border-radius: var(--radius-md); max-height: 80vh; display: flex; align-items: center; justify-content: center; background: #000;">
        <img src="${escapeHtml(photo.image)}" alt="Fotografia ${escapeHtml(currentActiveGallery.name)}" style="width: auto; height: auto; max-width: 90vw; max-height: 78vh; object-fit: contain; display: block;" />
      </div>

      <div style="display: flex; justify-content: space-between; align-items: center; width: 100%; margin-top: 1rem; padding: 0 0.5rem; min-height: 32px;">
        <div style="font-size: 0.85rem; color: var(--accent-cyan); font-weight: 700; text-transform: uppercase; letter-spacing: 0.06em;">
          ${escapeHtml(currentActiveGallery.name)}
        </div>
        <div>
          ${badgeHtml}
        </div>
      </div>
    </div>
  `;

  lb.classList.add('active');
}

function prevLightboxPhoto() {
  if (!currentActiveGallery || !currentActiveGallery.photos) return;
  const newIndex = (currentLightboxIndex - 1 + currentActiveGallery.photos.length) % currentActiveGallery.photos.length;
  openGalleryLightbox(newIndex);
}

function nextLightboxPhoto() {
  if (!currentActiveGallery || !currentActiveGallery.photos) return;
  const newIndex = (currentLightboxIndex + 1) % currentActiveGallery.photos.length;
  openGalleryLightbox(newIndex);
}

function closeGalleryModal() {
  const modal = document.getElementById('gallery-modal-overlay');
  if (modal) modal.classList.remove('active');
}

function closeGalleryLightbox() {
  const lb = document.getElementById('gallery-lightbox-overlay');
  if (lb) lb.classList.remove('active');
}

