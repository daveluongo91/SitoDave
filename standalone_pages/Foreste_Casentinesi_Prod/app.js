(() => {
  'use strict';

  const API_BASE = '/api';
  const WORKSHOP_ID = 'foreste-casentinesi-2026';
  const modal = document.getElementById('reservation-modal');
  const infoModal = document.getElementById('info-modal');
  const form = document.getElementById('reservation-form');
  const feedback = document.getElementById('payment-feedback');
  const paypalContainer = document.getElementById('paypal-button-container');
  const prepareButton = document.getElementById('prepare-payment');
  let buttonsRendered = false;

  const updateSeats = async () => {
    const seatBadges = document.querySelectorAll(`[data-workshop-seats="${WORKSHOP_ID}"]`);
    if (!seatBadges.length) return;
    try {
      const response = await fetch(`${API_BASE}/workshops/${WORKSHOP_ID}/seats`, {
        credentials: 'same-origin'
      });
      const result = await parseResponse(response);
      const availableSeats = Math.max(0, Number(result.availableSeats) || 0);
      const displayedSeats = availableSeats > 0 ? Math.max(1, availableSeats - 2) : 0;
      seatBadges.forEach((badge) => {
        if (availableSeats === 0 || result.status === 'soldout') {
          badge.textContent = '🔴 SOLD OUT';
          badge.className = 'badge-status soldout';
        } else {
          badge.textContent = `🔥 Solo ${displayedSeats} Posti Rimanenti!`;
          badge.className = 'badge-status active';
        }
      });
    } catch (error) {
      seatBadges.forEach((badge) => {
        badge.textContent = '👥 Massimo 8 Partecipanti';
      });
    }
  };

  const setFeedback = (message, isError = false) => {
    feedback.textContent = message;
    feedback.classList.toggle('error', isError);
  };

  const openModal = () => {
    modal.classList.add('active');
    document.body.classList.add('modal-open');
    document.getElementById('form-first-name').focus();
  };

  const closeModal = () => {
    modal.classList.remove('active');
    document.body.classList.remove('modal-open');
  };

  document.querySelectorAll('.open-modal-btn').forEach((button) => button.addEventListener('click', openModal));
  document.querySelectorAll('.open-info-modal').forEach((button) => {
    button.addEventListener('click', () => {
      infoModal.dataset.subject = button.dataset.subject || '[FORESTE CASENTINESI 2026] Richiesta informazioni';
      infoModal.classList.add('active');
      document.body.classList.add('modal-open');
      document.getElementById('info-name').focus();
    });
  });
  document.getElementById('modal-close').addEventListener('click', closeModal);
  document.getElementById('info-modal-close').addEventListener('click', () => {
    infoModal.classList.remove('active');
    document.body.classList.remove('modal-open');
  });
  modal.addEventListener('click', (event) => { if (event.target === modal) closeModal(); });
  infoModal.addEventListener('click', (event) => {
    if (event.target === infoModal) {
      infoModal.classList.remove('active');
      document.body.classList.remove('modal-open');
    }
  });
  document.addEventListener('keydown', (event) => {
    if (event.key !== 'Escape') return;
    if (modal.classList.contains('active')) closeModal();
    if (infoModal.classList.contains('active')) {
      infoModal.classList.remove('active');
      document.body.classList.remove('modal-open');
    }
  });

  const customerData = () => ({
    workshopId: WORKSHOP_ID,
    formula: document.getElementById('form-payment').value,
    couponCode: '',
    firstName: document.getElementById('form-first-name').value.trim(),
    lastName: document.getElementById('form-last-name').value.trim(),
    email: document.getElementById('form-email').value.trim(),
    phone: document.getElementById('form-phone').value.trim(),
    participants: 1
  });

  const parseResponse = async (response) => {
    const body = await response.json().catch(() => ({}));
    if (!response.ok || body.status === 'error') throw new Error(body.detail || body.message || 'Servizio di pagamento non disponibile.');
    return body;
  };

  form.addEventListener('submit', (event) => {
    event.preventDefault();
    if (!form.reportValidity()) return;
    if (!window.paypal?.Buttons) {
      setFeedback('PayPal non è raggiungibile. Controlla la connessione e riprova.', true);
      return;
    }
    if (buttonsRendered) return;

    prepareButton.hidden = true;
    paypalContainer.hidden = false;
    setFeedback('Scegli come completare il pagamento in ambiente PayPal sandbox.');

    window.paypal.Buttons({
      style: { layout: 'vertical', shape: 'pill', label: 'paypal' },
      createOrder: async () => {
        setFeedback('Preparazione del pagamento…');
        const response = await fetch(`${API_BASE}/create-paypal-order`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          credentials: 'same-origin',
          body: JSON.stringify(customerData())
        });
        const result = await parseResponse(response);
        setFeedback('Ordine pronto. Completa l’autorizzazione su PayPal.');
        return result.orderId;
      },
      onApprove: async (data) => {
        setFeedback('Conferma del pagamento…');
        const response = await fetch(`${API_BASE}/capture-paypal-order`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          credentials: 'same-origin',
          body: JSON.stringify({ orderId: data.orderID })
        });
        const result = await parseResponse(response);
        if (!['paid', 'already_paid'].includes(result.status)) throw new Error('Il pagamento non risulta completato.');
        window.location.assign(`./thank-you.html?booking=${encodeURIComponent(result.bookingId || '')}`);
      },
      onCancel: () => setFeedback('Pagamento annullato. Puoi riprovare quando vuoi.'),
      onError: (error) => {
        console.error('PayPal checkout error', error);
        setFeedback('Non è stato possibile completare il pagamento. Riprova o contatta Davide.', true);
      }
    }).render('#paypal-button-container');

    buttonsRendered = true;
  });

  const alertForm = document.getElementById('availability-alert-form');
  const alertFeedback = document.getElementById('availability-alert-feedback');
  if (alertForm && alertFeedback) {
    alertForm.addEventListener('submit', async (event) => {
      event.preventDefault();
      if (!alertForm.reportValidity()) return;

      const submit = alertForm.querySelector('button[type="submit"]');
      submit.disabled = true;
      alertFeedback.classList.remove('error');
      alertFeedback.textContent = 'Registrazione in corso…';

      try {
        const response = await fetch(`${API_BASE}/availability-alerts/subscribe`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          credentials: 'same-origin',
          body: JSON.stringify({
            workshopId: WORKSHOP_ID,
            name: document.getElementById('alert-name').value.trim(),
            email: document.getElementById('alert-email').value.trim(),
            consent: document.getElementById('alert-consent').checked
          })
        });
        const result = await parseResponse(response);
        alertFeedback.textContent = result.message;
        alertForm.reset();
      } catch (error) {
        alertFeedback.classList.add('error');
        alertFeedback.textContent = error.message || 'Iscrizione non riuscita. Riprova tra poco.';
      } finally {
        submit.disabled = false;
      }
    });
  }

  const infoForm = document.getElementById('info-request-form');
  const infoFeedback = document.getElementById('info-request-feedback');
  infoForm.addEventListener('submit', async (event) => {
    event.preventDefault();
    if (!infoForm.reportValidity()) return;
    const submit = infoForm.querySelector('button[type="submit"]');
    submit.disabled = true;
    infoFeedback.classList.remove('error');
    infoFeedback.textContent = 'Invio in corso…';
    try {
      const response = await fetch(`${API_BASE}/send-info-email`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'same-origin',
        body: JSON.stringify({
          name: document.getElementById('info-name').value.trim(),
          email: document.getElementById('info-email').value.trim(),
          phone: document.getElementById('info-phone').value.trim(),
          source: WORKSHOP_ID,
          subject: infoModal.dataset.subject || '[FORESTE CASENTINESI 2026] Richiesta informazioni',
          message: document.getElementById('info-message').value.trim()
        })
      });
      const result = await parseResponse(response);
      infoFeedback.textContent = 'Messaggio inviato. Davide ti risponderà appena possibile.';
      infoForm.reset();
    } catch (error) {
      infoFeedback.classList.add('error');
      infoFeedback.textContent = error.message || 'Invio non riuscito. Riprova tra poco.';
    } finally {
      submit.disabled = false;
    }
  });

  updateSeats();
})();
