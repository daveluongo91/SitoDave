# Prelancio Friuli 2026

Cartella autonoma destinata a `/Friuli_2026/`.

## Stato

- Header e footer rimossi.
- Asset, CSS e JavaScript locali alla cartella.
- Checkout collegato a `/api/create-paypal-order` e `/api/capture-paypal-order`.
- PayPal ancora in modalità sandbox: non pubblicare come pagina live di vendita.
- Indicizzazione disattivata (`noindex`) durante il prelancio.

## Prima della pubblicazione

1. Configurare e verificare il backend HTTPS sullo stesso dominio per gli endpoint `/api`.
2. Inserire nel backend `PAYPAL_ENV=live`, Client ID, Client Secret e Webhook ID live.
3. Sostituire nell'HTML il Client ID SDK sandbox con il Client ID live.
4. Correggere nel backend le URL PayPal di ritorno/annullamento, oggi impostate su localhost.
5. Verificare firma webhook, CSP, CORS/CSRF e invio email.
6. Eseguire un pagamento reale controllato di importo minimo e verificare ordine, cattura, email e decremento posti.
7. Rimuovere `noindex` soltanto quando la pagina è pronta per essere indicizzata.
8. Inserire la Website Key pubblica CookieYes in `cookie-consent.js` e verificare accettazione, rifiuto e riapertura delle preferenze.
9. Configurare `ARUBA_SMTP_PASS` nel file `.env` privato del backend. Il mittente è `info@davideluongo.it` e non richiede modifiche al frontend.
10. Avviare il backend almeno una volta per creare la tabella `availability_subscribers`, quindi provare iscrizione, disiscrizione e invii alle soglie 2/1.

## Upload previsto

Caricare l'intero contenuto di questa cartella nella directory remota che risponde a:

`https://www.davideluongo.it/Friuli_2026/`

Il percorso FTP esatto va verificato con un elenco remoto in sola lettura prima dell'upload.
