(() => {
  'use strict';

  const API_BASE = './api';
  const WORKSHOP_ID = 'friuli-2026';
  const modal = document.getElementById('reservation-modal');
  const infoModal = document.getElementById('info-modal');
  const form = document.getElementById('reservation-form');
  const feedback = document.getElementById('payment-feedback');
  const paypalContainer = document.getElementById('paypal-button-container');
  const prepareButton = document.getElementById('prepare-payment');
  const paymentSelect = document.getElementById('form-payment');
  const extraDayCheckbox = document.getElementById('form-extra-day');
  const bookingTotal = document.getElementById('booking-total');
  const priceSummary = document.getElementById('booking-price-summary');
  const BASE_PRICE = 350;
  const EXTRA_DAY_PRICE = 100;
  const DEPOSIT = 50;
  let buttonsRendered = false;

  /** Attende che window.paypal.Buttons sia pronto (max 8 s). */
  const waitForPayPal = () => new Promise((resolve, reject) => {
    if (window.paypal?.Buttons) { resolve(); return; }
    let elapsed = 0;
    const interval = setInterval(() => {
      elapsed += 100;
      if (window.paypal?.Buttons) { clearInterval(interval); resolve(); }
      else if (elapsed >= 8000) { clearInterval(interval); reject(new Error('timeout')); }
    }, 100);
  });


  const formatEuro = (amount) => new Intl.NumberFormat('it-IT', {
    style: 'currency', currency: 'EUR', minimumFractionDigits: 0, maximumFractionDigits: 2
  }).format(amount);

  const updatePricing = () => {
    const total = BASE_PRICE + (extraDayCheckbox.checked ? EXTRA_DAY_PRICE : 0);
    const balance = total - DEPOSIT;
    const isBalance = paymentSelect.value === 'saldo';
    paymentSelect.options[1].textContent = `Saldo Totale (${formatEuro(total)} - Opzione 3 rate PayPal)`;
    bookingTotal.textContent = formatEuro(total);
    if (isBalance) {
      const installment = total / 3;
      priceSummary.innerHTML = `<strong>Totale: ${formatEuro(total)}</strong> • Pagamento completo oggi. PayPal può proporre 3 rate da circa ${formatEuro(installment)}, previa approvazione.`;
      prepareButton.textContent = `Continua con PayPal (${formatEuro(total)}) ↗`;
    } else {
      priceSummary.innerHTML = `<strong>Totale: ${formatEuro(total)}</strong> • Caparra oggi: ${formatEuro(DEPOSIT)} • Saldo residuo: ${formatEuro(balance)}.`;
      prepareButton.textContent = `Continua con PayPal (${formatEuro(DEPOSIT)}) ↗`;
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
      infoModal.dataset.subject = button.dataset.subject || 'Informazioni Workshop Friuli 2026';
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
    formula: paymentSelect.value,
    extraDay: extraDayCheckbox.checked,
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

  form.addEventListener('submit', async (event) => {
    event.preventDefault();
    if (!form.reportValidity()) return;
    if (buttonsRendered) return;

    prepareButton.hidden = true;
    paypalContainer.hidden = false;
    setFeedback('Caricamento PayPal…');

    try {
      await waitForPayPal();
    } catch {
      prepareButton.hidden = false;
      paypalContainer.hidden = true;
      setFeedback('PayPal non è raggiungibile. Controlla la connessione e riprova.', true);
      return;
    }

    setFeedback('Scegli come completare il pagamento nell\u2019ambiente sicuro PayPal.');

    window.paypal.Buttons({
      style: { layout: 'vertical', shape: 'pill', label: 'paypal' },
      createOrder: async () => {
        setFeedback('Preparazione del pagamento\u2026');
        const response = await fetch(`${API_BASE}/create-paypal-order`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          credentials: 'same-origin',
          body: JSON.stringify(customerData())
        });
        const result = await parseResponse(response);
        setFeedback('Ordine pronto. Completa l\u2019autorizzazione su PayPal.');
        return result.orderId;
      },
      onApprove: async (data) => {
        setFeedback('Conferma del pagamento\u2026');
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
        setFeedback('Non \u00e8 stato possibile completare il pagamento. Riprova o contatta Davide.', true);
      }
    }).render('#paypal-button-container');

    buttonsRendered = true;
  });


  paymentSelect.addEventListener('change', updatePricing);
  extraDayCheckbox.addEventListener('change', updatePricing);
  updatePricing();

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
          subject: infoModal.dataset.subject || 'Informazioni Workshop Friuli 2026',
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
})();
