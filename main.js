/* ==========================================================================
   Davide Luongo — Workshop Reservation System, PayPal & Urgency Logic
   ========================================================================== */

document.addEventListener('DOMContentLoaded', () => {
  setupReservationModal();
  updateUrgencyCounters();
});

// Calculate Urgency Counter (Seats available minus 20% for FOMO urgency)
function calculateUrgencySeats(availableSeats, totalSeats = 8) {
  if (availableSeats <= 0) return 0;
  const bias = Math.ceil(totalSeats * 0.20); // 8 * 0.20 = 1.6 -> 2 seats bias
  return Math.max(1, availableSeats - bias);
}

function updateUrgencyCounters() {
  fetch('/api/content')
    .then(res => res.json())
    .then(data => {
      if (!data.workshops) return;
      
      data.workshops.forEach(ws => {
        const displayedSeats = calculateUrgencySeats(ws.availableSeats || 8, ws.totalSeats || 8);
        
        // Find elements with data-workshop-seats attribute
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

// Reservation Modal Setup
function setupReservationModal() {
  const modalBtns = document.querySelectorAll('.open-modal-btn');
  let modalOverlay = document.getElementById('booking-modal-overlay');

  // Create modal dynamically if it doesn't exist
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
            <a id="modal-email-btn" href="mailto:info@davideluongo.it" class="btn btn-secondary" style="font-size: 0.8rem; padding: 0.5rem; text-align: center;">✉️ Chiedi Info via Email</a>
            <a id="modal-whatsapp-btn" href="https://wa.me/393735096237" target="_blank" class="btn btn-secondary" style="font-size: 0.8rem; padding: 0.5rem; text-align: center; border-color: #25D366; color: #25D366;">💬 Chat WhatsApp</a>
          </div>

        </form>
      </div>
    `;
    document.body.appendChild(modalOverlay);
  }

  // Bind close button
  const closeBtn = document.getElementById('booking-modal-close');
  if (closeBtn) {
    closeBtn.addEventListener('click', () => {
      modalOverlay.classList.remove('active');
    });
  }

  // Bind open modal buttons
  modalBtns.forEach(btn => {
    btn.addEventListener('click', (e) => {
      e.preventDefault();
      const subject = btn.getAttribute('data-subject') || 'Workshop Fotografico 2026';
      
      document.getElementById('booking-modal-title').innerText = `Prenota ${subject}`;
      document.getElementById('booking-workshop-id').value = subject;
      
      document.getElementById('modal-email-btn').href = `mailto:info@davideluongo.it?subject=Richiesta%20Info%20${encodeURIComponent(subject)}`;
      document.getElementById('modal-whatsapp-btn').href = `https://wa.me/393735096237?text=${encodeURIComponent('Ciao Davide, vorrei informazioni su ' + subject)}`;

      modalOverlay.classList.add('active');
    });
  });

  // Handle Form Submission
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
      const amount = selectedFormula === 'caparra' ? '€50' : '€290';

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
          amountPaid: amount
        })
      })
      .then(res => res.json())
      .then(data => {
        if (data.status === 'success') {
          // Open PayPal Business window or redirect to Thank You page
          window.open(data.paypalUrl, '_blank');
          window.location.href = data.thankYouUrl;
        } else {
          alert('Errore prenotazione: ' + data.message);
        }
      })
      .catch(err => {
        console.error('Booking error:', err);
        window.location.href = `thank-you.html?name=${encodeURIComponent(firstName + ' ' + lastName)}&email=${encodeURIComponent(email)}&phone=${encodeURIComponent(phone)}&workshop=${encodeURIComponent(workshopName)}&payment=${encodeURIComponent(selectedFormula === 'caparra' ? 'Caparra €50' : 'Saldo €290')}`;
      });
    });
  }
}
