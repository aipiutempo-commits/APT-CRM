-- ═══════════════════════════════════════════════════════════════════════════
-- DIOZZI CRM – Schema PostgreSQL
-- Compatibile con: n8n (nodo Postgres), Coolify, Google Sheets sync
-- ═══════════════════════════════════════════════════════════════════════════

-- Pulizia (per re-installazione)
DROP TABLE IF EXISTS log CASCADE;
DROP TABLE IF EXISTS attivita CASCADE;
DROP TABLE IF EXISTS offerte CASCADE;
DROP TABLE IF EXISTS contatti CASCADE;
DROP TABLE IF EXISTS progetti CASCADE;
DROP TABLE IF EXISTS fornitori CASCADE;
DROP TABLE IF EXISTS clienti CASCADE;
DROP TABLE IF EXISTS utenti CASCADE;

DROP TYPE IF EXISTS stato_progetto CASCADE;
DROP TYPE IF EXISTS stato_offerta CASCADE;
DROP TYPE IF EXISTS stato_task CASCADE;
DROP TYPE IF EXISTS priorita CASCADE;
DROP TYPE IF EXISTS tipo_fornitore CASCADE;
DROP TYPE IF EXISTS tipo_offerta CASCADE;
DROP TYPE IF EXISTS ruolo_utente CASCADE;

-- ─── ENUM TYPES ────────────────────────────────────────────────────────────

CREATE TYPE stato_progetto  AS ENUM ('Attivo', 'Sospeso', 'Chiuso');
CREATE TYPE stato_offerta   AS ENUM ('Da Inviare', 'Inviata', 'Ricevuta', 'In Valutazione', 'Aggiudicata', 'Rifiutata');
CREATE TYPE stato_task      AS ENUM ('Da fare', 'In corso', 'Fatto');
CREATE TYPE priorita        AS ENUM ('Bassa', 'Media', 'Alta');
CREATE TYPE tipo_fornitore  AS ENUM ('Elettrico', 'Software', 'Altro');
CREATE TYPE tipo_offerta    AS ENUM ('Elettrico', 'Software');
CREATE TYPE ruolo_utente    AS ENUM ('admin', 'utente', 'readonly');

-- ─── UTENTI (autenticazione + TOTP) ───────────────────────────────────────

CREATE TABLE utenti (
    id              SERIAL PRIMARY KEY,
    username        VARCHAR(50) UNIQUE NOT NULL,
    password_hash   VARCHAR(255) NOT NULL,
    totp_secret     VARCHAR(64),          -- NULL = TOTP non ancora configurato
    email           VARCHAR(255),
    ruolo           ruolo_utente NOT NULL DEFAULT 'utente',
    attivo          BOOLEAN NOT NULL DEFAULT TRUE,
    data_creazione  TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_utenti_username ON utenti(username);

-- ─── CLIENTI ──────────────────────────────────────────────────────────────

CREATE TABLE clienti (
    id              VARCHAR(20) PRIMARY KEY DEFAULT substring(gen_random_uuid()::text, 1, 8),
    ragione_sociale VARCHAR(255) NOT NULL,
    referente       VARCHAR(255),
    email           VARCHAR(255),
    telefono        VARCHAR(50),
    note            TEXT,
    data_creazione  TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_clienti_ragione ON clienti(ragione_sociale);

-- ─── CONTATTI ─────────────────────────────────────────────────────────────

CREATE TABLE contatti (
    id              VARCHAR(20) PRIMARY KEY DEFAULT substring(gen_random_uuid()::text, 1, 8),
    cliente_id      VARCHAR(20) REFERENCES clienti(id) ON DELETE SET NULL,
    cliente_nome    VARCHAR(255),         -- denormalizzato per performance
    nome            VARCHAR(100) NOT NULL,
    cognome         VARCHAR(100) NOT NULL,
    ruolo           VARCHAR(150),
    email           VARCHAR(255),
    telefono        VARCHAR(50),
    note            TEXT,
    data_creazione  TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_contatti_cliente ON contatti(cliente_id);
CREATE INDEX idx_contatti_nome ON contatti(nome, cognome);

-- ─── FORNITORI ────────────────────────────────────────────────────────────

CREATE TABLE fornitori (
    id              VARCHAR(20) PRIMARY KEY DEFAULT substring(gen_random_uuid()::text, 1, 8),
    ragione_sociale VARCHAR(255) NOT NULL,
    tipo            tipo_fornitore NOT NULL DEFAULT 'Altro',
    referente       VARCHAR(255),
    email           VARCHAR(255),
    telefono        VARCHAR(50),
    note            TEXT,
    data_creazione  TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_fornitori_ragione ON fornitori(ragione_sociale);
CREATE INDEX idx_fornitori_tipo ON fornitori(tipo);

-- ─── PROGETTI ─────────────────────────────────────────────────────────────

CREATE TABLE progetti (
    id                  VARCHAR(20) PRIMARY KEY DEFAULT substring(gen_random_uuid()::text, 1, 8),
    nome                VARCHAR(255) NOT NULL,
    cliente_id          VARCHAR(20) REFERENCES clienti(id) ON DELETE SET NULL,
    cliente_nome        VARCHAR(255),     -- denormalizzato
    stato               stato_progetto NOT NULL DEFAULT 'Attivo',
    data_inizio         DATE,
    data_fine_prevista  DATE,
    note                TEXT,
    data_creazione      TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_progetti_cliente ON progetti(cliente_id);
CREATE INDEX idx_progetti_stato ON progetti(stato);
CREATE INDEX idx_progetti_scadenza ON progetti(data_fine_prevista);

-- ─── OFFERTE ──────────────────────────────────────────────────────────────

CREATE TABLE offerte (
    id                      VARCHAR(20) PRIMARY KEY DEFAULT substring(gen_random_uuid()::text, 1, 8),
    progetto_id             VARCHAR(20) REFERENCES progetti(id) ON DELETE SET NULL,
    progetto_nome           VARCHAR(255),
    tipo                    tipo_offerta,
    fornitore_id            VARCHAR(20) REFERENCES fornitori(id) ON DELETE SET NULL,
    fornitore_nome          VARCHAR(255),
    descrizione             TEXT,
    data_invio_richiesta    DATE,
    scadenza_attesa         DATE,
    stato                   stato_offerta NOT NULL DEFAULT 'Da Inviare',
    data_ricezione          DATE,
    importo                 NUMERIC(12,2),
    priorita                priorita NOT NULL DEFAULT 'Media',
    num_solleciti           INTEGER NOT NULL DEFAULT 0,
    note                    TEXT,
    calendar_event_id       VARCHAR(255),
    data_creazione          TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_offerte_progetto ON offerte(progetto_id);
CREATE INDEX idx_offerte_fornitore ON offerte(fornitore_id);
CREATE INDEX idx_offerte_stato ON offerte(stato);
CREATE INDEX idx_offerte_scadenza ON offerte(scadenza_attesa);
CREATE INDEX idx_offerte_priorita ON offerte(priorita);

-- ─── ATTIVITA ─────────────────────────────────────────────────────────────

CREATE TABLE attivita (
    id              VARCHAR(20) PRIMARY KEY DEFAULT substring(gen_random_uuid()::text, 1, 8),
    titolo          VARCHAR(255) NOT NULL,
    progetto_id     VARCHAR(20) REFERENCES progetti(id) ON DELETE SET NULL,
    progetto_nome   VARCHAR(255),
    assegnato_a     VARCHAR(150),
    scadenza        DATE,
    stato           stato_task NOT NULL DEFAULT 'Da fare',
    priorita        priorita NOT NULL DEFAULT 'Media',
    note            TEXT,
    data_inizio     DATE,
    data_fine       DATE,
    calendar_event_id VARCHAR(255),
    google_task_id  VARCHAR(255),
    data_creazione  TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_attivita_progetto ON attivita(progetto_id);
CREATE INDEX idx_attivita_stato ON attivita(stato);
CREATE INDEX idx_attivita_scadenza ON attivita(scadenza);
CREATE INDEX idx_attivita_priorita ON attivita(priorita);
CREATE INDEX idx_attivita_assegnato ON attivita(assegnato_a);

-- ─── LOG ──────────────────────────────────────────────────────────────────

CREATE TABLE log (
    id          SERIAL PRIMARY KEY,
    timestamp   TIMESTAMP NOT NULL DEFAULT NOW(),
    azione      VARCHAR(50) NOT NULL,
    entita      VARCHAR(50),
    id_entita   VARCHAR(20),
    utente      VARCHAR(50),
    dettagli    TEXT
);

CREATE INDEX idx_log_timestamp ON log(timestamp DESC);
CREATE INDEX idx_log_entita ON log(entita, id_entita);
CREATE INDEX idx_log_utente ON log(utente);

-- ═══════════════════════════════════════════════════════════════════════════
-- DATI DI ESEMPIO
-- ═══════════════════════════════════════════════════════════════════════════

-- Utenti (password: "admin" → bcrypt hash)
INSERT INTO utenti (username, password_hash, email, ruolo) VALUES
('admin', '$2b$12$LJ3m4ys3Lk8nFgX.placeholder.hash.change.me', 'admin@diozzi.it', 'admin'),
('marco', '$2b$12$Kp9x7Rt2Hn.placeholder.hash.change.me', 'm.diozzi@diozzi.it', 'utente');

-- Clienti
INSERT INTO clienti (id, ragione_sociale, referente, email, telefono, note) VALUES
('A1B2C3D4', 'Fonderia Meridionale SpA', 'Ing. Marco Russo', 'm.russo@fonderia.it', '011 4521890', 'Cliente storico dal 2018'),
('E5F6G7H8', 'GreenEnergy Solutions Srl', 'Dott.ssa Laura Bianchi', 'l.bianchi@greenenergy.it', '02 7893214', 'Progetto fotovoltaico in corso'),
('I9J0K1L2', 'Manifattura Tessile Nord', 'Sig. Paolo Ferrari', 'ferrari@tessile.com', '035 8823410', ''),
('M3N4O5P6', 'Logistica Rapida Srl', 'Ing. Sara Conti', 's.conti@logistica.it', '051 3319876', 'Nuovo cliente 2025');

-- Contatti
INSERT INTO contatti (id, cliente_id, cliente_nome, nome, cognome, ruolo, email, telefono, note) VALUES
('C1A2B3C4', 'A1B2C3D4', 'Fonderia Meridionale SpA', 'Marco', 'Russo', 'Direttore Tecnico', 'm.russo@fonderia.it', '011 4521890', 'Referente principale per progetti elettrici'),
('C2D3E4F5', 'A1B2C3D4', 'Fonderia Meridionale SpA', 'Anna', 'Ferrari', 'Responsabile Acquisti', 'a.ferrari@fonderia.it', '011 4521891', 'Contattare per ordini > 50k'),
('C3G4H5I6', 'A1B2C3D4', 'Fonderia Meridionale SpA', 'Luca', 'Bianchi', 'Site Manager', 'l.bianchi@fonderia.it', '345 1234567', 'Solo per urgenze cantiere'),
('C4J5K6L7', 'E5F6G7H8', 'GreenEnergy Solutions Srl', 'Laura', 'Bianchi', 'CEO', 'l.bianchi@greenenergy.it', '02 7893214', ''),
('C5M6N7O8', 'E5F6G7H8', 'GreenEnergy Solutions Srl', 'Roberto', 'Verdi', 'CTO', 'r.verdi@greenenergy.it', '02 7893215', 'Referente tecnico impianti'),
('C6P7Q8R9', 'I9J0K1L2', 'Manifattura Tessile Nord', 'Paolo', 'Ferrari', 'Titolare', 'ferrari@tessile.com', '035 8823410', ''),
('C7R8S9T0', 'M3N4O5P6', 'Logistica Rapida Srl', 'Sara', 'Conti', 'Responsabile Produzione', 's.conti@logistica.it', '051 3319876', 'Decisore finale su automazioni');

-- Fornitori
INSERT INTO fornitori (id, ragione_sociale, tipo, referente, email, telefono, note) VALUES
('F1A2B3C4', 'Quadrel Automazione Srl', 'Elettrico', 'Paolo Quadrelli', 'p.quadrelli@quadrel.it', '011 4532100', 'Quadri elettrici BT/MT certificati CEI. Partner storico dal 2015'),
('F5D6E7F8', 'Automac Engineering Srl', 'Elettrico', 'Sara Macconi', 's.macconi@automac.it', '02 8844221', 'Programmazione PLC Siemens S7 e Rockwell. Sviluppo HMI WinCC e FactoryTalk'),
('F9G0H1I2', 'Siemens Italia SpA', 'Altro', 'Luca Ferretti', 'l.ferretti@siemens.com', '02 66521234', 'Partner Siemens ufficiale. Forniture S7-1500 ET200SP WinCC Unified SCADA'),
('F3J4K5L6', 'ElettroMech Srl', 'Elettrico', 'Antonio Neri', 'a.neri@elettromech.it', '049 8811200', 'Cablaggio quadri installazioni elettriche industriali. Zona Nord-Est');

-- Progetti
INSERT INTO progetti (id, nome, cliente_id, cliente_nome, stato, data_inizio, data_fine_prevista, note) VALUES
('P1A2B3C4', 'Ristrutturazione Uffici Sede Nord', 'A1B2C3D4', 'Fonderia Meridionale SpA', 'Attivo', '2025-01-15', '2026-06-30', 'Impianto elettrico + dati'),
('P5D6E7F8', 'Digitalizzazione Processi ERP', 'E5F6G7H8', 'GreenEnergy Solutions Srl', 'Attivo', '2025-03-01', '2026-12-31', ''),
('P9G0H1I2', 'Ampliamento Capannone Produzione', 'I9J0K1L2', 'Manifattura Tessile Nord', 'Attivo', '2025-06-01', '2026-09-15', ''),
('P3J4K5L6', 'Sistema Supervisione SCADA', 'M3N4O5P6', 'Logistica Rapida Srl', 'Sospeso', '2025-02-10', '2026-04-30', ''),
('P7M8N9O0', 'Fotovoltaico Tetto Industriale', 'E5F6G7H8', 'GreenEnergy Solutions Srl', 'Chiuso', '2024-06-01', '2025-11-30', '');

-- Offerte
INSERT INTO offerte (id, progetto_id, progetto_nome, tipo, fornitore_id, fornitore_nome, descrizione, data_invio_richiesta, scadenza_attesa, stato, data_ricezione, importo, priorita, num_solleciti) VALUES
('O1A2B3C4', 'P1A2B3C4', 'Ristrutturazione Uffici Sede Nord', 'Elettrico', 'F1A2B3C4', 'Quadrel Automazione Srl', 'Fornitura quadro BT principale + distribuzione piano', '2025-09-10', '2025-10-15', 'Inviata', NULL, NULL, 'Alta', 1),
('O5D6E7F8', 'P5D6E7F8', 'Digitalizzazione Processi ERP', 'Software', 'F5D6E7F8', 'Automac Engineering Srl', 'Sviluppo interfacce HMI per 12 postazioni operatore', '2025-08-20', '2025-09-20', 'Ricevuta', '2025-09-05', 85000, 'Alta', 0),
('O9G0H1I2', 'P9G0H1I2', 'Ampliamento Capannone Produzione', 'Elettrico', 'F9G0H1I2', 'Siemens Italia SpA', 'PLC S7-1500 + ET200SP + licenze WinCC', '2025-10-01', '2025-11-01', 'Da Inviare', NULL, NULL, 'Media', 0),
('O3J4K5L6', 'P3J4K5L6', 'Sistema Supervisione SCADA', 'Software', 'F5D6E7F8', 'Automac Engineering Srl', 'Programmazione SCADA WinCC Unified 15 pagine', '2025-07-15', '2025-08-15', 'Inviata', NULL, NULL, 'Alta', 2),
('O7M8N9O0', 'P1A2B3C4', 'Ristrutturazione Uffici Sede Nord', 'Elettrico', 'F3J4K5L6', 'ElettroMech Srl', 'Cablaggio strutturato Cat6A 200 punti rete', '2025-09-15', '2025-10-10', 'Aggiudicata', '2025-09-25', 42000, 'Media', 0);

-- Attivita
INSERT INTO attivita (id, titolo, progetto_id, progetto_nome, assegnato_a, scadenza, stato, priorita, data_inizio, data_fine) VALUES
('T1A2B3C4', 'Sopralluogo e rilievo impianto elettrico', 'P1A2B3C4', 'Ristrutturazione Uffici Sede Nord', 'Marco Diozzi', '2026-03-15', 'In corso', 'Alta', '2026-03-10', '2026-03-18'),
('T2D3E4F5', 'Emissione schema quadro elettrico', 'P1A2B3C4', 'Ristrutturazione Uffici Sede Nord', 'Marco Diozzi', '2026-04-20', 'Da fare', 'Alta', '2026-04-01', '2026-04-25'),
('T3G4H5I6', 'Verifica cablaggi e certificazione impianto', 'P1A2B3C4', 'Ristrutturazione Uffici Sede Nord', 'Marco Diozzi', '2026-04-11', 'In corso', 'Alta', '2026-04-05', '2026-04-15'),
('T4J5K6L7', 'Revisione contratto SAP con fornitore', 'P5D6E7F8', 'Digitalizzazione Processi ERP', 'Marco Diozzi', '2026-04-09', 'Da fare', 'Media', '2026-04-01', '2026-04-09'),
('T5M6N7O8', 'Programmazione PLC S7-1500 linea A', 'P9G0H1I2', 'Ampliamento Capannone Produzione', 'Marco Diozzi', '2026-04-30', 'Da fare', 'Alta', '2026-04-10', '2026-05-15'),
('T6P7Q8R9', 'Sopralluogo capannone B per quadro MT', 'P9G0H1I2', 'Ampliamento Capannone Produzione', 'Marco Diozzi', '2026-04-10', 'In corso', 'Alta', '2026-04-05', '2026-04-12'),
('T7R8S9T0', 'Analisi requisiti sistema SCADA', 'P3J4K5L6', 'Sistema Supervisione SCADA', 'Marco Diozzi', '2026-03-20', 'Fatto', 'Alta', '2026-03-01', '2026-03-20'),
('T8U9V0W1', 'Sviluppo HMI WinCC schermate supervisione', 'P3J4K5L6', 'Sistema Supervisione SCADA', 'Marco Diozzi', '2026-02-28', 'Da fare', 'Alta', '2026-02-15', '2026-03-30');

-- Log
INSERT INTO log (timestamp, azione, entita, id_entita, utente, dettagli) VALUES
('2026-04-09 08:30:00', 'LOGIN', 'utenti', '', 'admin', 'Accesso al sistema'),
('2026-04-09 08:35:00', 'UPDATE', 'attivita', 'T1A2B3C4', 'admin', 'Stato cambiato: Da fare -> In corso'),
('2026-04-09 09:00:00', 'CREATE', 'offerte', 'O1A2B3C4', 'admin', 'Nuova offerta per Quadrel Automazione'),
('2026-04-08 14:20:00', 'EMAIL_SOLLECITO', 'offerte', 'O3J4K5L6', 'admin', 'Sollecito inviato a Automac Engineering'),
('2026-04-08 10:00:00', 'UPDATE', 'progetti', 'P3J4K5L6', 'admin', 'Stato cambiato: Attivo -> Sospeso');

-- ═══════════════════════════════════════════════════════════════════════════
-- QUERY UTILI PER n8n
-- ═══════════════════════════════════════════════════════════════════════════

-- n8n: Offerte scadute (per workflow sollecito automatico)
-- SELECT * FROM offerte WHERE stato = 'Inviata' AND scadenza_attesa < NOW();

-- n8n: Task in scadenza domani (per notifica Telegram/WhatsApp)
-- SELECT * FROM attivita WHERE stato != 'Fatto' AND scadenza = CURRENT_DATE + INTERVAL '1 day';

-- n8n: KPI dashboard
-- SELECT
--   (SELECT COUNT(*) FROM offerte WHERE stato = 'Inviata' AND scadenza_attesa < NOW()) AS offerte_scadute,
--   (SELECT COUNT(*) FROM attivita WHERE stato != 'Fatto' AND priorita = 'Alta') AS task_urgenti,
--   (SELECT COUNT(*) FROM progetti WHERE stato = 'Attivo') AS progetti_attivi,
--   (SELECT COUNT(*) FROM offerte) AS offerte_totali;

-- n8n: Export per Google Sheets (tutti i clienti con conteggio progetti)
-- SELECT c.*, COUNT(p.id) AS num_progetti
-- FROM clienti c LEFT JOIN progetti p ON p.cliente_id = c.id
-- GROUP BY c.id ORDER BY c.ragione_sociale;
