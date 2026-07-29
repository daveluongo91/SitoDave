/* ==========================================================================
   Davide Luongo — Interactive JavaScript Logic
   ========================================================================== */

document.addEventListener('DOMContentLoaded', () => {
  console.log("Davide Luongo Astrophotography Website — Loaded successfully.");

  // 1. Modal Functionality (Prenotazioni / Richiesta Info)
  const modalOverlay = document.getElementById('reservation-modal');
  const modalCloseBtn = document.getElementById('modal-close');
  const openModalBtns = document.querySelectorAll('.open-modal-btn');
  const modalSubjectInput = document.getElementById('modal-subject');

  if (openModalBtns.length > 0 && modalOverlay) {
    openModalBtns.forEach(btn => {
      btn.addEventListener('click', (e) => {
        e.preventDefault();
        const subject = btn.getAttribute('data-subject') || 'Informazioni Generali';
        if (modalSubjectInput) {
          modalSubjectInput.value = subject;
        }
        modalOverlay.classList.add('active');
        document.body.style.overflow = 'hidden';
      });
    });

    if (modalCloseBtn) {
      modalCloseBtn.addEventListener('click', closeModal);
    }

    modalOverlay.addEventListener('click', (e) => {
      if (e.target === modalOverlay) {
        closeModal();
      }
    });

    function closeModal() {
      modalOverlay.classList.remove('active');
      document.body.style.overflow = 'auto';
    }
  }

  // 2. Reservation Form Submission Handler
  const reservationForm = document.getElementById('reservation-form');
  if (reservationForm) {
    reservationForm.addEventListener('submit', (e) => {
      e.preventDefault();
      const name = document.getElementById('form-name').value;
      const email = document.getElementById('form-email').value;

      alert(`Grazie ${name}! La tua richiesta per "${modalSubjectInput.value}" è stata inviata con successo. Ti ricontatterò a breve all'indirizzo ${email}.`);
      
      if (modalOverlay) {
        modalOverlay.classList.remove('active');
        document.body.style.overflow = 'auto';
      }
      reservationForm.reset();
    });
  }

  // 3. Category Filter Tabs (Workshops, Gear & Blog)
  const filterTabs = document.querySelectorAll('.filter-tab');
  const workshopCards = document.querySelectorAll('.workshop-card-item');
  const gearCards = document.querySelectorAll('.gear-card');
  const blogCards = document.querySelectorAll('.blog-card-item');

  if (filterTabs.length > 0) {
    filterTabs.forEach(tab => {
      tab.addEventListener('click', () => {
        filterTabs.forEach(t => t.classList.remove('active', 'btn-primary'));
        filterTabs.forEach(t => t.classList.add('btn-secondary'));

        tab.classList.remove('btn-secondary');
        tab.classList.add('active', 'btn-primary');

        const category = tab.getAttribute('data-category');

        // Filter Workshop Cards
        if (workshopCards.length > 0) {
          workshopCards.forEach(card => {
            if (category === 'all' || card.getAttribute('data-category') === category) {
              card.style.display = 'flex';
            } else {
              card.style.display = 'none';
            }
          });
        }

        // Filter Gear Cards
        if (gearCards.length > 0) {
          gearCards.forEach(card => {
            if (category === 'all' || card.getAttribute('data-category') === category) {
              card.style.display = 'flex';
            } else {
              card.style.display = 'none';
            }
          });
        }

        // Filter Blog Cards
        if (blogCards.length > 0) {
          blogCards.forEach(card => {
            if (category === 'all' || card.getAttribute('data-category') === category) {
              card.style.display = 'flex';
            } else {
              card.style.display = 'none';
            }
          });
        }
      });
    });
  }

  // 4. Smooth Scroll for Navbar Links
  const navLinks = document.querySelectorAll('.nav-links a[href^="#"]');
  navLinks.forEach(link => {
    link.addEventListener('click', (e) => {
      const targetId = link.getAttribute('href');
      if (targetId !== '#') {
        e.preventDefault();
        const targetElement = document.querySelector(targetId);
        if (targetElement) {
          targetElement.scrollIntoView({ behavior: 'smooth' });
        }
      }
    });
  });
});
