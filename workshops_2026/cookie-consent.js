(() => {
  'use strict';

  // Chiave pubblica CookieYes: copiare qui la Website Key del dominio davideluongo.it.
  const COOKIEYES_WEBSITE_KEY = 'b11bb2f53a7fd366526ca1ae247777e3';

  if (COOKIEYES_WEBSITE_KEY) {
    const script = document.createElement('script');
    script.id = 'cookieyes';
    script.src = `https://cdn-cookieyes.com/client_data/${encodeURIComponent(COOKIEYES_WEBSITE_KEY)}/script.js`;
    document.head.appendChild(script);
  }

  document.addEventListener('click', (event) => {
    const trigger = event.target.closest('[data-cookie-preferences]');
    if (!trigger) return;

    if (typeof window.revisitCkyConsent === 'function') {
      window.revisitCkyConsent();
      return;
    }

    window.alert('Le preferenze cookie saranno disponibili dopo l’attivazione della Website Key CookieYes.');
  });
})();

