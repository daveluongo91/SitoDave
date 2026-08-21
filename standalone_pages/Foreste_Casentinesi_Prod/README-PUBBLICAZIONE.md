# Workshop Foreste Casentinesi 2026 — Bosco, Acqua e Tardo Autunno

Cartella autonoma destinata a `/Foreste_Casentinesi_2026/`.

## Stato della bozza

- Date: 28–29 Novembre 2026.
- Quota: €350; caparra €50; saldo €300; politiche identiche a Friuli e Dardagna.
- Otto posti gestiti dal backend con aggiornamento automatico, sold out e avvisi alle soglie 2/1.
- Docenti: Davide Luongo e Manuel Linari.
- Le richieste informazioni arrivano con il marker `[FORESTE CASENTINESI 2026]`.
- Hero e tre immagini editoriali sono segnaposto SVG riconoscibili da sostituire.
- Indicizzazione disattivata (`noindex`) durante il prelancio.
- PayPal è configurato in sandbox nel frontend di prelancio.

## Collegamenti tecnici

- Checkout: `/api/create-paypal-order` e `/api/capture-paypal-order`.
- Disponibilità: `/api/workshops/foreste-casentinesi-2026/seats`.
- Avvisi ultimi posti: `/api/availability-alerts/subscribe`.
- Richieste informazioni: `/api/send-info-email`.

## Prima della pubblicazione

1. Sostituire hero e tre segnaposto con asset definitivi ottimizzati per il web.
2. Verificare il backend HTTPS sul dominio e la presenza del workshop nel database.
3. Passare PayPal a credenziali live e verificare Client ID, Client Secret e Webhook ID.
4. Eseguire un pagamento reale controllato e verificare cattura, email e decremento posti.
5. Provare richieste informazioni, avvisi 2/1, disiscrizione e report cutoff.
6. Rimuovere `noindex` soltanto dopo approvazione di contenuti, privacy e checkout.

## Versionamento

La cartella produttiva locale è `L:\Foreste_Casentinesi_Prod`. Lo specchio versionato è
`Sito_Dave/standalone_pages/Foreste_Casentinesi_Prod`. Le due copie devono restare identiche.
