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
   Gallerie Fotografiche (Modal & Lightbox Engine per 10 Foto)
   ========================================================================== */

const DEFAULT_GALLERIES_DATA = [
  {
    "id": "islanda",
    "name": "Islanda",
    "title": "Galleria Fotografica • Islanda",
    "badge": "🇮🇸 10 FOTO",
    "coverImage": "assets/islanda_photo_tour.png",
    "accentColor": "#00F0FF",
    "description": "Un viaggio visivo tra aurore boreali, cascate impetuose, ghiacciai millenari e desolazioni vulcaniche d'Islanda.",
    "photos": [
      {
        "id": "is-01",
        "title": "Danza Boreale sul Ghiacciaio",
        "caption": "Aurora boreale di grado G2 che si riflette sulla laguna glaciale di Jökulsárlón.",
        "image": "assets/islanda_photo_tour.png"
      },
      {
        "id": "is-02",
        "title": "Il Risveglio di Skógafoss",
        "caption": "Luce radente dell'alba tra gli spruzzi della maestosa cascata.",
        "image": "assets/islanda_photo_tour.png"
      },
      {
        "id": "is-03",
        "title": "Vestrahorn e la Spiaggia Nera",
        "caption": "Riflessi perfetti sui banchi di marea di Stokksnes sotto cieli tempestosi.",
        "image": "assets/islanda_photo_tour.png"
      },
      {
        "id": "is-04",
        "title": "Canyon di Fjaðrárgljúfur",
        "caption": "Geometrie serpeggianti e muschio smeraldo nelle gole del sud.",
        "image": "assets/islanda_photo_tour.png"
      },
      {
        "id": "is-05",
        "title": "Grotta di Ghiaccio nel Vatnajökull",
        "caption": "Texture blu profondo e luce filtrante all'interno del ghiacciaio perenne.",
        "image": "assets/islanda_photo_tour.png"
      },
      {
        "id": "is-06",
        "title": "Arco di Seljalandsfoss al Tramonto",
        "caption": "La prospettiva dietro la cortina d'acqua con luce dorata atlantica.",
        "image": "assets/islanda_photo_tour.png"
      },
      {
        "id": "is-07",
        "title": "Piana Vulcanica di Landmannalaugar",
        "caption": "Riolite policroma e contrasti primordiali negli altipiani interni.",
        "image": "assets/islanda_photo_tour.png"
      },
      {
        "id": "is-08",
        "title": "Arco Boreale su Kirkjufell",
        "caption": "La montagna iconica incorniciata dalle cascate e dalla via boreale.",
        "image": "assets/islanda_photo_tour.png"
      },
      {
        "id": "is-09",
        "title": "Spiaggia dei Diamanti",
        "caption": "Blocchi di ghiaccio cristallino arenati sulla sabbia basaltica nera.",
        "image": "assets/islanda_photo_tour.png"
      },
      {
        "id": "is-10",
        "title": "Fumo e Zolfo a Hverir",
        "caption": "Sfumature marziane e fumarole solforose nella regione di Mývatn.",
        "image": "assets/islanda_photo_tour.png"
      }
    ]
  },
  {
    "id": "tenerife",
    "name": "Tenerife",
    "title": "Galleria Fotografica • Tenerife",
    "badge": "🇪🇸 10 FOTO",
    "coverImage": "assets/minorca_photo_tour.png",
    "accentColor": "#FFB800",
    "description": "Paesaggi lunari del Parco Nazionale del Teide, mari di nubi e uno dei cieli stellati Starlight più puri del pianeta.",
    "photos": [
      {
        "id": "tf-01",
        "title": "La Via Lattea sul Teide",
        "caption": "Arco galattico estivo sopra le formazioni rocciose di Roques de García.",
        "image": "assets/minorca_photo_tour.png"
      },
      {
        "id": "tf-02",
        "title": "Mare di Nubi al Mirador de Chipeque",
        "caption": "Il tramonto infuocato che tinge il mare di nubi attorno alla cima del vulcano.",
        "image": "assets/minorca_photo_tour.png"
      },
      {
        "id": "tf-03",
        "title": "Paesaggio Lunare di Vilaflor",
        "caption": "Pinnacoli di tufo bianco scolpiti dal vento nella caldera meridionale.",
        "image": "assets/minorca_photo_tour.png"
      },
      {
        "id": "tf-04",
        "title": "L'Osservatorio del Teide sotto le Stelle",
        "caption": "I telescopi solari ed astrofisici illuminati solo dalla luce zodiacale.",
        "image": "assets/minorca_photo_tour.png"
      },
      {
        "id": "tf-05",
        "title": "Punta de Teno e il Faro",
        "caption": "Scogliere a picco e onde oceaniche al calare della notte atlantica.",
        "image": "assets/minorca_photo_tour.png"
      },
      {
        "id": "tf-06",
        "title": "Foresta di Laurisilva ad Anaga",
        "caption": "Nebbie fitte e felci giganti nel polmone verde più antico dell'isola.",
        "image": "assets/minorca_photo_tour.png"
      },
      {
        "id": "tf-07",
        "title": "Pini Canari tra la Lava",
        "caption": "Resistenza e contrasti cromatici tra aghi verdi e basalto nero vulcanico.",
        "image": "assets/minorca_photo_tour.png"
      },
      {
        "id": "tf-08",
        "title": "Alba sul Cratere del Pico Viejo",
        "caption": "I primi raggi che disegnano l'ombra piramidale del Teide sull'oceano.",
        "image": "assets/minorca_photo_tour.png"
      },
      {
        "id": "tf-09",
        "title": "Cielo Profondo su Las Cañadas",
        "caption": "Dettaglio delle nebulose della Via Lattea in assenza di inquinamento luminoso.",
        "image": "assets/minorca_photo_tour.png"
      },
      {
        "id": "tf-10",
        "title": "I Giganti dall'Oceano",
        "caption": "Scogliere monumentali di Los Gigantes che scendono verticali nell'Atlantico.",
        "image": "assets/minorca_photo_tour.png"
      }
    ]
  },
  {
    "id": "madeira",
    "name": "Madeira",
    "title": "Galleria Fotografica • Madeira",
    "badge": "🇵🇹 10 FOTO",
    "coverImage": "assets/azzorre_photo_tour.png",
    "accentColor": "#A855F7",
    "description": "L'isola dell'eterna primavera: scogliere a picco sull'oceano, la foresta millenaria di Fanal e vette che emergono dalle nuvole.",
    "photos": [
      {
        "id": "md-01",
        "title": "La Magica Nebbia di Fanal",
        "caption": "Faggi centenari di Tis avvolti nella nebbia densa della foresta Laurissilva.",
        "image": "assets/azzorre_photo_tour.png"
      },
      {
        "id": "md-02",
        "title": "Alba sul Pico do Arieiro",
        "caption": "Creste affilate che galleggiano su un soffice tappeto di nuvole dorate.",
        "image": "assets/azzorre_photo_tour.png"
      },
      {
        "id": "md-03",
        "title": "Faraglioni di Ribeira da Janela",
        "caption": "Onde imponenti dell'Atlantico che si infrangono sui giganti di roccia lavica.",
        "image": "assets/azzorre_photo_tour.png"
      },
      {
        "id": "md-04",
        "title": "Ponta de São Lourenço",
        "caption": "Colori ocra e scogliere battute dal vento nella penisola orientale.",
        "image": "assets/azzorre_photo_tour.png"
      },
      {
        "id": "md-05",
        "title": "Cascata Dos Anjos",
        "caption": "La cascata naturale che cade direttamente sulla vecchia strada costiera.",
        "image": "assets/azzorre_photo_tour.png"
      },
      {
        "id": "md-06",
        "title": "Sentiero tra Pico do Arieiro e Pico Ruivo",
        "caption": "Percorso escursionistico mozzafiato sospeso sopra le valli scoscese.",
        "image": "assets/azzorre_photo_tour.png"
      },
      {
        "id": "md-07",
        "title": "Piscine Naturali di Porto Moniz",
        "caption": "Bacini vulcanici scavati nella lava costantemente alimentati dalle maree.",
        "image": "assets/azzorre_photo_tour.png"
      },
      {
        "id": "md-08",
        "title": "Miradouro do Guindaste all'Alba",
        "caption": "La passerella di vetro sospesa sulla scogliera durante le prime luci.",
        "image": "assets/azzorre_photo_tour.png"
      },
      {
        "id": "md-09",
        "title": "Luce Filtrante lungo la Levada",
        "caption": "Canali d'acqua storici immersi nella vegetazione lussureggiante dell'isola.",
        "image": "assets/azzorre_photo_tour.png"
      },
      {
        "id": "md-10",
        "title": "Tramonto a Ponta do Pargo",
        "caption": "Il faro solitario sull'estremo lembo occidentale illuminato dagli ultimi raggi.",
        "image": "assets/azzorre_photo_tour.png"
      }
    ]
  },
  {
    "id": "montagna",
    "name": "Montagna",
    "title": "Galleria Fotografica • Montagna & Alpi",
    "badge": "🏔️ 10 FOTO",
    "coverImage": "assets/timelapse_nivolet_poster.jpg",
    "accentColor": "#00F0FF",
    "description": "Vette alpine selvagge, riflessi sui laghi glaciali, foliage autunnale e notti sotto le stelle in alta quota.",
    "photos": [
      {
        "id": "mt-01",
        "title": "Colle del Nivolet e Lago Serrù",
        "caption": "L'arco della Via Lattea specchiato nelle acque cristalline a 2600m.",
        "image": "assets/timelapse_nivolet_poster.jpg"
      },
      {
        "id": "mt-02",
        "title": "Laghi di Fusine in Autunno",
        "caption": "Il Mangart riflesso nello specchio d'acqua circondato dal foliage dorato.",
        "image": "assets/timelapse_nivolet_poster.jpg"
      },
      {
        "id": "mt-03",
        "title": "Cascate del Dardagna in Piena",
        "caption": "Lunga esposizione setosa sui salti d'acqua dell'Appennino Tosco-Emiliano.",
        "image": "assets/timelapse_nivolet_poster.jpg"
      },
      {
        "id": "mt-04",
        "title": "Foliage Monumentale a Canfaito",
        "caption": "Nebbia mattutina tra i rami contorti dei faggi plurisecolari marchigiani.",
        "image": "assets/timelapse_nivolet_poster.jpg"
      },
      {
        "id": "mt-05",
        "title": "Tre Cime di Lavaredo all'Enrosadira",
        "caption": "Dolomiti tinte di rosa e magenta durante gli ultimi istanti del tramonto.",
        "image": "assets/timelapse_nivolet_poster.jpg"
      },
      {
        "id": "mt-06",
        "title": "Sorgenti di Zelenci all'Alba",
        "caption": "Laguna smeraldo con il ghiaccio sottile e vapore acqueo all'aurora.",
        "image": "assets/timelapse_nivolet_poster.jpg"
      },
      {
        "id": "mt-07",
        "title": "Fontanon di Goriuda",
        "caption": "La spettacolare grotta e cascata nascosta nella Val Raccolana.",
        "image": "assets/timelapse_nivolet_poster.jpg"
      },
      {
        "id": "mt-08",
        "title": "Notte Stellata sul Gran Paradiso",
        "caption": "Cieli alpini incontaminati a 3000 metri con inseguimento siderale.",
        "image": "assets/timelapse_nivolet_poster.jpg"
      },
      {
        "id": "mt-09",
        "title": "Foreste Casentinesi nel Picco Autunnale",
        "caption": "Un mare di foglie rosse, oro e arancio nelle faggete patrimonio UNESCO.",
        "image": "assets/timelapse_nivolet_poster.jpg"
      },
      {
        "id": "mt-10",
        "title": "Lago del Predil e Alpi Giulie",
        "caption": "Silenzio mattutino e riflessi d'alta montagna al confine italo-sloveno.",
        "image": "assets/timelapse_nivolet_poster.jpg"
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
      if (Array.isArray(data) && data.length) {
        galleriesStore = data;
      }
    }
  } catch (e) {
    // Failover silenzioso
  }

  // Event listener per le card verticali
  document.addEventListener('click', (e) => {
    const card = e.target.closest('.gallery-vertical-card');
    if (card) {
      e.preventDefault();
      const galleryId = card.getAttribute('data-gallery-id');
      openGalleryModal(galleryId);
      return;
    }

    const photoItem = e.target.closest('.gallery-photo-item');
    if (photoItem) {
      e.preventDefault();
      const index = parseInt(photoItem.getAttribute('data-photo-index'), 10);
      openGalleryLightbox(index);
    }
  });

  // Supporto tastiera per le card
  document.addEventListener('keydown', (e) => {
    if (e.key === 'Enter' || e.key === ' ') {
      const card = document.activeElement.closest('.gallery-vertical-card');
      if (card) {
        e.preventDefault();
        const galleryId = card.getAttribute('data-gallery-id');
        openGalleryModal(galleryId);
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

  const photosHtml = (gallery.photos || []).map((photo, idx) => `
    <div class="gallery-photo-item" data-photo-index="${idx}" tabindex="0" role="button" aria-label="${escapeHtml(photo.title)}">
      <span class="gallery-photo-badge">${idx + 1} / 10</span>
      <img src="${escapeHtml(photo.image)}" alt="${escapeHtml(photo.title)}" class="gallery-photo-thumb" loading="lazy" />
      <div class="gallery-photo-info">
        <h4 class="gallery-photo-title">${escapeHtml(photo.title)}</h4>
        <p class="gallery-photo-caption">${escapeHtml(photo.caption)}</p>
      </div>
    </div>
  `).join('');

  modal.innerHTML = `
    <div class="modal-content" style="max-width: 1040px; max-height: 90vh; overflow-y: auto; text-align: left; padding: 2.25rem 2rem;">
      <button class="modal-close" onclick="closeGalleryModal()">&times;</button>
      
      <div style="display: flex; align-items: center; justify-content: space-between; border-bottom: 1px solid var(--border-glass); padding-bottom: 1.25rem; margin-bottom: 1.25rem; flex-wrap: wrap; gap: 0.75rem;">
        <div>
          <span style="font-size: 0.8rem; font-weight: 700; color: var(--accent-cyan); text-transform: uppercase; letter-spacing: 0.12em;">Galleria Fotografica Ufficiale</span>
          <h3 style="font-size: 1.85rem; color: #fff; margin: 0.25rem 0 0 0;">${escapeHtml(gallery.name)}</h3>
        </div>
        <span class="gallery-card-badge" style="position: static; font-size: 0.85rem; padding: 0.4rem 1rem;">
          ${escapeHtml(gallery.badge || '10 FOTO')}
        </span>
      </div>

      <p style="color: var(--text-secondary); font-size: 0.95rem; line-height: 1.6; margin-bottom: 1.5rem; max-width: 820px;">
        ${escapeHtml(gallery.description)}
      </p>

      <div class="gallery-modal-grid">
        ${photosHtml}
      </div>

      <div style="text-align: center; margin-top: 2rem; border-top: 1px solid var(--border-glass); padding-top: 1.5rem;">
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

  lb.innerHTML = `
    <div class="modal-content" style="max-width: 900px; padding: 1.5rem; text-align: center; background: rgba(4, 9, 20, 0.95); border: 1px solid var(--border-glow);">
      <button class="modal-close" onclick="closeGalleryLightbox()">&times;</button>
      
      <div style="position: relative; overflow: hidden; border-radius: var(--radius-md); max-height: 62vh; background: #000; display: flex; align-items: center; justify-content: center;">
        <img src="${escapeHtml(photo.image)}" alt="${escapeHtml(photo.title)}" style="width: 100%; height: auto; max-height: 60vh; object-fit: contain;" />
      </div>

      <div style="display: flex; justify-content: space-between; align-items: center; margin-top: 1.25rem; text-align: left; gap: 1rem; flex-wrap: wrap;">
        <div>
          <div style="font-size: 0.78rem; color: var(--accent-cyan); font-weight: 700; text-transform: uppercase;">
            ${escapeHtml(currentActiveGallery.name)} • Foto ${index + 1} di ${currentActiveGallery.photos.length}
          </div>
          <h4 style="font-size: 1.2rem; color: #fff; margin: 0.2rem 0;">${escapeHtml(photo.title)}</h4>
          <p style="font-size: 0.88rem; color: var(--text-secondary); margin: 0;">${escapeHtml(photo.caption)}</p>
        </div>
        <div style="display: flex; gap: 0.5rem;">
          <button type="button" class="carousel-nav-btn" onclick="prevLightboxPhoto()" aria-label="Foto precedente">←</button>
          <button type="button" class="carousel-nav-btn" onclick="nextLightboxPhoto()" aria-label="Foto successiva">→</button>
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



