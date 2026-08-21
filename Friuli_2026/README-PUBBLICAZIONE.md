# Prelancio Friuli 2026

Cartella autonoma destinata a `/Friuli_2026/`.

## Stato

- Header e footer rimossi.
- Asset, CSS e JavaScript locali alla cartella.
- Checkout collegato agli endpoint PHP locali `./api/create-paypal-order` e `./api/capture-paypal-order`.
- Opzione facoltativa da venerdì 9 ottobre: +€100, totale €450; caparra invariata a €50.
- Il backend calcola e registra il supplemento; PayPal Pay Later riceve €350 o €450 in base alla scelta.
- PayPal usa la configurazione live privata già presente sull’hosting; nessuna credenziale è inclusa nei file pubblici.
- Indicizzazione disattivata (`noindex`) durante il prelancio.

## Prima della pubblicazione

1. Verificare gli endpoint HTTPS locali nella cartella `./api`.
2. Mantenere Client ID, Client Secret e Webhook ID live esclusivamente in `private/production.env` sull’hosting.
3. Verificare firma webhook, CSP, controllo dell’origine e invio email.
4. Dopo modifiche al checkout, eseguire un pagamento reale controllato e verificare ordine, cattura, email e decremento posti.
5. Rimuovere `noindex` soltanto quando la pagina è pronta per essere indicizzata.
6. Inserire la Website Key pubblica CookieYes in `cookie-consent.js` e verificare accettazione, rifiuto e riapertura delle preferenze.
7. Mantenere le credenziali SMTP nel file privato dell’hosting. Il mittente è `info@davideluongo.it` e non richiede modifiche al frontend.
8. Provare iscrizione, disiscrizione e invii degli avvisi alle soglie di 2 e 1 posto.

## Upload previsto

Caricare l'intero contenuto di questa cartella nella directory remota che risponde a:

`https://www.davideluongo.it/Friuli_2026/`

Il percorso FTP esatto va verificato con un elenco remoto in sola lettura prima dell'upload.
