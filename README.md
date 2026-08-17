# Sito Davide Luongo

Baseline consolidata: frontend statico pubblico e CMS/API FastAPI nello stesso processo.

## Avvio locale

1. Creare un ambiente Python virtuale.
2. Installare `backend/requirements.txt`.
3. Copiare `.env.example` in `.env` e compilare soltanto i valori locali necessari.
4. Avviare `python -m backend.run` dalla root del progetto.
5. Verificare `http://localhost:3000/api/health`, la home e `/admin/`.

Il vecchio `server.py` è mantenuto temporaneamente come riferimento per la migrazione, ma non è l'entry point supportato. Non usare PayPal live finché i test sandbox end-to-end e la configurazione webhook non sono stati completati.

## Produzione

- Impostare `APP_ENV=production`, una `SECRET_KEY` persistente e casuale, `SITE_PUBLIC_URL` e `ALLOWED_ORIGINS` sul dominio HTTPS reale.
- Conservare SMTP e credenziali PayPal esclusivamente nei segreti dell'ambiente di hosting.
- Eseguire backup del database prima di ogni migrazione.
- Verificare email, PayPal sandbox, webhook, importi, disponibilità e rollback prima di abilitare `PAYPAL_ENV=live`.
