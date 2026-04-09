# DIOZZI CRM – Manuale di installazione e utilizzo

CRM personale leggero, PWA mobile-first con FastAPI + Google Sheets come database.

---

## Struttura del progetto

```
├── main.py                  # Punto di ingresso FastAPI
├── setup.py                 # Script di configurazione iniziale
├── requirements.txt
├── .env.example             # Template variabili d'ambiente
├── credentials.json         # ← da ottenere (vedi sezione sotto)
├── nginx.conf               # Configurazione Nginx per VPS
├── models/                  # Modelli Pydantic
├── routers/                 # Endpoint REST (auth, clienti, fornitori, …)
├── services/
│   ├── google_sheets.py     # CRUD su Google Sheets
│   ├── google_calendar.py   # Integrazione Calendar
│   ├── google_tasks.py      # Integrazione Tasks
│   ├── gmail_service.py     # Invio email via Gmail
│   └── scheduler.py         # Automazioni giornaliere/settimanali
└── static/                  # Frontend PWA (HTML/CSS/JS puri)
    ├── index.html
    ├── manifest.json
    ├── sw.js                # Service Worker
    ├── css/app.css
    └── js/app.js
```

---

## 1. Prerequisiti

- Python 3.11+
- Account Google (Workspace o personale)
- VPS Linux con Nginx (per il deploy)

---

## 2. Credenziali Google (Service Account)

### 2.1 Crea il progetto Google Cloud

1. Vai su [console.cloud.google.com](https://console.cloud.google.com/)
2. Crea un nuovo progetto (es. "CRM Personale")
3. Abilita le seguenti API dal menu **API e servizi → Libreria**:
   - **Google Sheets API**
   - **Google Drive API**
   - **Google Calendar API**
   - **Gmail API**
   - **Google Tasks API**

### 2.2 Crea il Service Account

1. Vai su **IAM e Amministrazione → Account di servizio**
2. Clicca **Crea account di servizio**
3. Nome: `crm-service-account` (o simile)
4. Ruolo: **Editor** (o crea ruoli personalizzati più restrittivi)
5. Clicca **Crea chiave** → Tipo JSON → Scarica il file
6. Rinomina il file in `credentials.json` e mettilo nella cartella del progetto

### 2.3 Condividi il Google Sheet

1. Crea un nuovo Google Sheet (o usa uno esistente)
2. Copia l'ID dalla URL: `https://docs.google.com/spreadsheets/d/**ID_QUI**/edit`
3. Clicca **Condividi** e aggiungi l'email del service account come **Editor**
   (la trovi nel file JSON al campo `client_email`)

### 2.4 Gmail – Delegazione di dominio (solo per account Workspace)

Per inviare email tramite Gmail con un service account, è necessaria la **delegazione di dominio**:

1. In Google Workspace Admin Console → **Sicurezza → Accesso API → Gestione delegazione**
2. Aggiungi il Client ID del service account con questi scope:
   ```
   https://www.googleapis.com/auth/gmail.send
   https://www.googleapis.com/auth/calendar
   https://www.googleapis.com/auth/tasks
   ```
3. Imposta `GMAIL_FROM_EMAIL` in `.env` con l'email dell'utente da impersonare

> **Nota**: per account Gmail personali, la delegazione di dominio non è disponibile.
> L'invio email non funzionerà a meno di usare OAuth2 interattivo (non incluso).

---

## 3. Installazione

```bash
# Clona / copia la cartella del progetto
cd /path/al/progetto

# Esegui il setup guidato (installa dipendenze, crea .env, inizializza Sheets)
python setup.py
```

In alternativa, manualmente:

```bash
pip install -r requirements.txt
cp .env.example .env
# Modifica .env con i tuoi valori
nano .env
```

---

## 4. Avvio in sviluppo

```bash
python main.py
# oppure
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

Apri il browser su `http://localhost:8000` e accedi con le credenziali del `.env`.

La documentazione API OpenAPI è disponibile su `http://localhost:8000/docs`.

---

## 5. Deploy su VPS Linux

### 5.1 Trasferisci i file

```bash
# Dalla tua macchina locale
scp -r /path/al/progetto utente@IP_VPS:/home/utente/crm
```

### 5.2 Installa dipendenze sul VPS

```bash
ssh utente@IP_VPS
cd crm
sudo apt update && sudo apt install python3-pip python3-venv nginx -y
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 5.3 Avvia Uvicorn come servizio systemd

Crea `/etc/systemd/system/crm.service`:

```ini
[Unit]
Description=CRM Personale FastAPI
After=network.target

[Service]
User=utente
WorkingDirectory=/home/utente/crm
EnvironmentFile=/home/utente/crm/.env
ExecStart=/home/utente/crm/venv/bin/uvicorn main:app --host 127.0.0.1 --port 8000 --workers 2
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl daemon-reload
sudo systemctl enable crm
sudo systemctl start crm
sudo systemctl status crm
```

### 5.4 Configura Nginx

```bash
# Modifica nginx.conf: sostituisci TUO_DOMINIO_O_IP con il tuo dominio/IP
sudo cp /home/utente/crm/nginx.conf /etc/nginx/sites-available/crm
sudo ln -s /etc/nginx/sites-available/crm /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```

### 5.5 HTTPS con Certbot (consigliato)

```bash
sudo apt install certbot python3-certbot-nginx -y
sudo certbot --nginx -d tuo-dominio.it
# Certbot modificherà nginx.conf automaticamente
sudo systemctl reload nginx
```

---

## 6. Variabili d'ambiente (.env)

| Variabile | Descrizione | Esempio |
|---|---|---|
| `APP_USERNAME` | Username login CRM | `admin` |
| `APP_PASSWORD` | Password login CRM | `password_sicura` |
| `JWT_SECRET` | Chiave segreta JWT (genera con `secrets.token_hex(32)`) | `abc123…` |
| `JWT_EXPIRE_MINUTES` | Durata sessione in minuti | `1440` (24h) |
| `GOOGLE_SERVICE_ACCOUNT_FILE` | Path al file JSON credenziali | `credentials.json` |
| `GOOGLE_SPREADSHEET_ID` | ID del Google Sheet | `1BxiMVs0…` |
| `GOOGLE_CALENDAR_ID` | ID calendario (`primary` per quello principale) | `primary` |
| `GMAIL_FROM_EMAIL` | Email mittente Gmail | `nome@azienda.it` |
| `GMAIL_FROM_NAME` | Nome mittente | `CRM Personale` |
| `REPORT_RECIPIENT_EMAIL` | Email per ricevere i report automatici | `nome@azienda.it` |

---

## 7. Struttura Google Sheet

Lo script crea automaticamente i seguenti fogli (tab):

| Foglio | Contenuto |
|---|---|
| **Clienti** | Ragione sociale, referente, email, tel, note |
| **Fornitori** | Ragione sociale, tipo, referente, email, tel, note |
| **Progetti** | Nome, cliente, stato, date, note |
| **Offerte** | Tutti i campi preventivo + stato + importo |
| **Attività** | Task con scadenza, stato, priorità, link Calendar/Tasks |
| **Log** | Registro automatico di tutte le operazioni CRUD |

---

## 8. Installare come PWA (app sul telefono)

**Chrome/Android:**
1. Apri il CRM nel browser
2. Menu (⋮) → "Aggiungi a schermata Home"

**Safari/iOS:**
1. Apri il CRM in Safari
2. Tasto Condividi → "Aggiungi a schermata Home"

**Desktop (Chrome/Edge):**
1. Nella barra URL appare l'icona di installazione
2. Clicca "Installa"

---

## 9. Automazioni scheduler

| Job | Orario | Descrizione |
|---|---|---|
| Promemoria offerte | Ogni giorno 08:00 | Email con offerte in stato "Inviata" scadute |
| Report settimanale | Lunedì 07:30 | Riepilogo offerte, task in scadenza, progetti |

---

## 10. Sicurezza

- Accesso protetto da JWT (token 24h, rinnovato al login)
- Password in chiaro nel `.env` – usa permessi `chmod 600 .env`
- Il service account Google ha solo accesso ai file necessari
- HTTPS gestito da Nginx + Certbot (Let's Encrypt)
- In produzione, aggiorna `allow_origins` in `main.py` con il dominio specifico

---

## 11. Aggiornamento

```bash
# Ferma il servizio
sudo systemctl stop crm

# Aggiorna i file (git pull o copia manuale)
cd /home/utente/crm

# Reinstalla dipendenze se necessario
source venv/bin/activate
pip install -r requirements.txt

# Riavvia
sudo systemctl start crm
```
