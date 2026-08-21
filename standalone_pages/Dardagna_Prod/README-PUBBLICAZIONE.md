# Workshop Dardagna 2026 — Cascate dell’Appennino

Cartella autonoma destinata a `/Dardagna_2026/`.

## Stato della bozza

- Hero video compresso dal master ProRes 444, con poster statico di fallback.
- Il master è già stabile: nessun crop o filtro di stabilizzazione applicato.
- Foto delle tre schede ancora da sostituire: i file SVG sono segnaposto riconoscibili.
- Data: 24–25 ottobre 2026.
- Quota: €350; caparra €50; saldo €300; politiche identiche al Friuli.
- Otto posti gestiti dal backend con aggiornamento automatico, sold out e avvisi a 2/1.
- Docenti: Davide Luongo e Manuel Linari.
- Le richieste informazioni arrivano con il marker `[DARDAGNA 2026]` nell’oggetto.

## Stato

- Header e footer rimossi.
- Asset, CSS e JavaScript locali alla cartella.
- Checkout collegato agli endpoint PHP locali `./api/create-paypal-order` e `./api/capture-paypal-order`.
- PayPal usa la configurazione live privata dell’hosting; nessuna credenziale è inclusa nei file pubblici.
- Indicizzazione disattivata (`noindex`) durante il prelancio.

## Prima della pubblicazione

1. Verificare gli endpoint HTTPS locali nella cartella `./api`.
2. Mantenere Client ID, Client Secret e Webhook ID live esclusivamente in `private/production.env` sull’hosting.
3. Verificare firma webhook, controllo dell’origine e invio email.
4. Dopo modifiche al checkout, eseguire un pagamento reale controllato e verificare ordine, cattura, email e decremento posti.
5. Rimuovere `noindex` soltanto quando la pagina è pronta per essere indicizzata.
6. Verificare accettazione, rifiuto e riapertura delle preferenze CookieYes.
7. Provare iscrizione, disiscrizione e invii degli avvisi alle soglie di 2 e 1 posto.

## Upload previsto

Caricare l'intero contenuto di questa cartella nella directory remota che risponde a:

`https://www.davideluongo.it/Dardagna_2026/`

Il percorso FTP esatto va verificato con un elenco remoto in sola lettura prima dell'upload.
