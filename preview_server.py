"""
Server di preview con dati mock e stato mutabile in memoria – CRUD completo.
"""
import copy, os, time, uuid
from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from pathlib import Path
import uvicorn

app = FastAPI()
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

# ─── Dati mock iniziali ────────────────────────────────────────────────────────

_CLIENTI = [
    {"id": "A1B2C3D4", "ragione_sociale": "Fonderia Meridionale SpA", "referente": "Ing. Marco Russo", "email": "m.russo@fonderia.it", "telefono": "011 4521890", "note": "Cliente storico dal 2018"},
    {"id": "E5F6G7H8", "ragione_sociale": "GreenEnergy Solutions Srl", "referente": "Dott.ssa Laura Bianchi", "email": "l.bianchi@greenenergy.it", "telefono": "02 7893214", "note": "Progetto fotovoltaico in corso"},
    {"id": "I9J0K1L2", "ragione_sociale": "Manifattura Tessile Nord", "referente": "Sig. Paolo Ferrari", "email": "ferrari@tessile.com", "telefono": "035 8823410", "note": ""},
    {"id": "M3N4O5P6", "ragione_sociale": "Logistica Rapida Srl", "referente": "Ing. Sara Conti", "email": "s.conti@logistica.it", "telefono": "051 3319876", "note": "Nuovo cliente 2025"},
]

_CONTATTI = [
    {"id": "C1A2B3C4", "cliente_id": "A1B2C3D4", "cliente_nome": "Fonderia Meridionale SpA", "nome": "Marco", "cognome": "Russo", "ruolo": "Direttore Tecnico", "email": "m.russo@fonderia.it", "telefono": "011 4521890", "note": "Referente principale per progetti elettrici"},
    {"id": "C2D3E4F5", "cliente_id": "A1B2C3D4", "cliente_nome": "Fonderia Meridionale SpA", "nome": "Anna", "cognome": "Ferrari", "ruolo": "Responsabile Acquisti", "email": "a.ferrari@fonderia.it", "telefono": "011 4521891", "note": "Contattare per ordini > 50k€"},
    {"id": "C3G4H5I6", "cliente_id": "A1B2C3D4", "cliente_nome": "Fonderia Meridionale SpA", "nome": "Luca", "cognome": "Bianchi", "ruolo": "Site Manager", "email": "l.bianchi@fonderia.it", "telefono": "345 1234567", "note": "Solo per urgenze cantiere"},
    {"id": "C4J5K6L7", "cliente_id": "E5F6G7H8", "cliente_nome": "GreenEnergy Solutions Srl", "nome": "Laura", "cognome": "Bianchi", "ruolo": "CEO", "email": "l.bianchi@greenenergy.it", "telefono": "02 7893214", "note": ""},
    {"id": "C5M6N7O8", "cliente_id": "E5F6G7H8", "cliente_nome": "GreenEnergy Solutions Srl", "nome": "Roberto", "cognome": "Verdi", "ruolo": "CTO", "email": "r.verdi@greenenergy.it", "telefono": "02 7893215", "note": "Referente tecnico impianti"},
    {"id": "C6P7Q8R9", "cliente_id": "I9J0K1L2", "cliente_nome": "Manifattura Tessile Nord", "nome": "Paolo", "cognome": "Ferrari", "ruolo": "Titolare", "email": "ferrari@tessile.com", "telefono": "035 8823410", "note": ""},
    {"id": "C7R8S9T0", "cliente_id": "M3N4O5P6", "cliente_nome": "Logistica Rapida Srl", "nome": "Sara", "cognome": "Conti", "ruolo": "Responsabile Produzione", "email": "s.conti@logistica.it", "telefono": "051 3319876", "note": "Decisore finale su automazioni"},
]

_FORNITORI = [
    {"id": "F1A2B3C4", "ragione_sociale": "Quadrel Automazione Srl", "tipo": "Elettrico", "referente": "Paolo Quadrelli", "email": "p.quadrelli@quadrel.it", "telefono": "011 4532100", "note": "Quadri elettrici BT/MT, certificati CEI. Partner storico dal 2015"},
    {"id": "F5D6E7F8", "ragione_sociale": "Automac Engineering Srl", "tipo": "Elettrico", "referente": "Sara Macconi", "email": "s.macconi@automac.it", "telefono": "02 8844221", "note": "Programmazione PLC Siemens S7 e Rockwell. Sviluppo HMI WinCC e FactoryTalk"},
    {"id": "F9G0H1I2", "ragione_sociale": "Siemens Italia SpA", "tipo": "Altro", "referente": "Luca Ferretti", "email": "l.ferretti@siemens.com", "telefono": "02 66521234", "note": "Partner Siemens ufficiale. Forniture S7-1500, ET200SP, WinCC Unified, SCADA"},
    {"id": "F3J4K5L6", "ragione_sociale": "ElettroMech Srl", "tipo": "Elettrico", "referente": "Antonio Neri", "email": "a.neri@elettromech.it", "telefono": "049 8811200", "note": "Cablaggio quadri, installazioni elettriche industriali. Zona Nord-Est"},
]

_PROGETTI = [
    {"id": "P1A2B3C4", "nome": "Ristrutturazione Uffici Sede Nord", "cliente_id": "A1B2C3D4", "cliente_nome": "Fonderia Meridionale SpA", "stato": "Attivo", "data_inizio": "01/02/2026", "data_fine_prevista": "30/06/2026", "note": "Impianto elettrico + dati"},
    {"id": "P5D6E7F8", "nome": "Digitalizzazione Processi ERP", "cliente_id": "E5F6G7H8", "cliente_nome": "GreenEnergy Solutions Srl", "stato": "Attivo", "data_inizio": "15/01/2026", "data_fine_prevista": "31/12/2026", "note": "Integrazione SAP + IoT"},
    {"id": "P9G0H1I2", "nome": "Ampliamento Capannone Produzione", "cliente_id": "I9J0K1L2", "cliente_nome": "Manifattura Tessile Nord", "stato": "Attivo", "data_inizio": "01/03/2026", "data_fine_prevista": "15/09/2026", "note": "Quadro elettrico MT/BT"},
    {"id": "P3J4K5L6", "nome": "Sistema Supervisione SCADA", "cliente_id": "M3N4O5P6", "cliente_nome": "Logistica Rapida Srl", "stato": "Sospeso", "data_inizio": "01/11/2025", "data_fine_prevista": "30/04/2026", "note": "In attesa approvazione budget"},
    {"id": "P7M8N9O0", "nome": "Fotovoltaico Tetto Industriale", "cliente_id": "E5F6G7H8", "cliente_nome": "GreenEnergy Solutions Srl", "stato": "Chiuso", "data_inizio": "01/06/2025", "data_fine_prevista": "30/11/2025", "note": "Completato nei tempi"},
]

_OFFERTE = [
    {"id": "O1A2B3C4", "progetto_id": "P1A2B3C4", "progetto_nome": "Ristrutturazione Uffici Sede Nord", "tipo": "Elettrico", "fornitore_id": "F1A2B3C4", "fornitore_nome": "Elettro Rossi Srl", "descrizione": "Impianto elettrico BT + quadri", "data_invio_richiesta": "01/03/2026", "scadenza_attesa": "01/04/2026", "stato": "Inviata", "data_ricezione": "", "importo": "", "priorita": "Alta", "num_solleciti": "1", "note": "Sollecitata il 03/04"},
    {"id": "O5D6E7F8", "progetto_id": "P5D6E7F8", "progetto_nome": "Digitalizzazione Processi ERP", "tipo": "Software", "fornitore_id": "F5D6E7F8", "fornitore_nome": "TechSoft Italia SpA", "descrizione": "Licenze SAP + implementazione 6 mesi", "data_invio_richiesta": "15/02/2026", "scadenza_attesa": "15/03/2026", "stato": "Aggiudicata", "data_ricezione": "12/03/2026", "importo": "87.500", "priorita": "Alta", "num_solleciti": "0", "note": "Contratto in firma"},
    {"id": "O9G0H1I2", "progetto_id": "P9G0H1I2", "progetto_nome": "Ampliamento Capannone Produzione", "tipo": "Elettrico", "fornitore_id": "F9G0H1I2", "fornitore_nome": "AutoMax Srl", "descrizione": "Automazione linea produttiva + PLC", "data_invio_richiesta": "10/03/2026", "scadenza_attesa": "10/04/2026", "stato": "In Valutazione", "data_ricezione": "08/04/2026", "importo": "43.200", "priorita": "Media", "num_solleciti": "0", "note": ""},
    {"id": "O3J4K5L6", "progetto_id": "P1A2B3C4", "progetto_nome": "Ristrutturazione Uffici Sede Nord", "tipo": "Software", "fornitore_id": "F3J4K5L6", "fornitore_nome": "DataSys Europa Srl", "descrizione": "Sistema domotica uffici + app gestione", "data_invio_richiesta": "20/03/2026", "scadenza_attesa": "05/04/2026", "stato": "Ricevuta", "data_ricezione": "04/04/2026", "importo": "12.800", "priorita": "Bassa", "num_solleciti": "0", "note": ""},
    {"id": "O7M8N9O0", "progetto_id": "P3J4K5L6", "progetto_nome": "Sistema Supervisione SCADA", "tipo": "Software", "fornitore_id": "F5D6E7F8", "fornitore_nome": "TechSoft Italia SpA", "descrizione": "SCADA licenza + configurazione", "data_invio_richiesta": "01/11/2025", "scadenza_attesa": "25/03/2026", "stato": "Inviata", "data_ricezione": "", "importo": "", "priorita": "Alta", "num_solleciti": "2", "note": "2 solleciti senza risposta"},
]

_ATTIVITA = [
    {"id": "T1A2B3C4", "titolo": "Sopralluogo e rilievo impianto elettrico", "progetto_id": "P1A2B3C4", "progetto_nome": "Ristrutturazione Uffici Sede Nord", "assegnato_a": "M. Diozzi", "data_inizio": "15/03/2026", "data_fine": "16/03/2026", "scadenza": "16/03/2026", "stato": "Fatto", "priorita": "Alta", "note": "Rilievo planimetrico completato"},
    {"id": "T5D6E7F8", "titolo": "Emissione schema quadro elettrico BT", "progetto_id": "P1A2B3C4", "progetto_nome": "Ristrutturazione Uffici Sede Nord", "assegnato_a": "M. Diozzi", "data_inizio": "20/03/2026", "data_fine": "28/03/2026", "scadenza": "28/03/2026", "stato": "Fatto", "priorita": "Alta", "note": "AutoCAD Electrical – schema approvato"},
    {"id": "T9G0H1I2", "titolo": "Verifica cablaggi e certificazione impianto", "progetto_id": "P1A2B3C4", "progetto_nome": "Ristrutturazione Uffici Sede Nord", "assegnato_a": "M. Diozzi", "data_inizio": "09/04/2026", "data_fine": "11/04/2026", "scadenza": "11/04/2026", "stato": "In corso", "priorita": "Alta", "note": "Portare multimetro e DPI"},
    {"id": "T3J4K5L6", "titolo": "Analisi requisiti sistema SCADA", "progetto_id": "P3J4K5L6", "progetto_nome": "Sistema Supervisione SCADA", "assegnato_a": "M. Diozzi", "data_inizio": "01/11/2025", "data_fine": "15/11/2025", "scadenza": "15/11/2025", "stato": "Fatto", "priorita": "Alta", "note": "Documento requisiti approvato"},
    {"id": "T7M8N9O0", "titolo": "Sviluppo HMI WinCC – schermate supervisione", "progetto_id": "P3J4K5L6", "progetto_nome": "Sistema Supervisione SCADA", "assegnato_a": "M. Diozzi", "data_inizio": "01/02/2026", "data_fine": "28/02/2026", "scadenza": "28/02/2026", "stato": "Da fare", "priorita": "Alta", "note": "Dashboard trend, allarmi e report"},
    {"id": "T8X9Y0Z1", "titolo": "Programmazione PLC S7-1500 linea A", "progetto_id": "P9G0H1I2", "progetto_nome": "Ampliamento Capannone Produzione", "assegnato_a": "M. Diozzi", "data_inizio": "01/04/2026", "data_fine": "30/04/2026", "scadenza": "30/04/2026", "stato": "Da fare", "priorita": "Alta", "note": "TIA Portal V18 – sequenza avviamento motori"},
    {"id": "T2B3C4D5", "titolo": "Sopralluogo capannone B per quadro MT", "progetto_id": "P9G0H1I2", "progetto_nome": "Ampliamento Capannone Produzione", "assegnato_a": "M. Diozzi", "data_inizio": "10/04/2026", "data_fine": "10/04/2026", "scadenza": "10/04/2026", "stato": "Da fare", "priorita": "Alta", "note": "Verifica dimensionamento trasformatore"},
    {"id": "T4C5D6E7", "titolo": "Revisione contratto SAP con fornitore", "progetto_id": "P5D6E7F8", "progetto_nome": "Digitalizzazione Processi ERP", "assegnato_a": "M. Diozzi", "data_inizio": "09/04/2026", "data_fine": "09/04/2026", "scadenza": "09/04/2026", "stato": "Da fare", "priorita": "Media", "note": "Verificare clausole penali e SLA"},
    {"id": "T6E7F8G9", "titolo": "Collaudo impianto fotovoltaico", "progetto_id": "P7M8N9O0", "progetto_nome": "Fotovoltaico Tetto Industriale", "assegnato_a": "M. Diozzi", "data_inizio": "01/12/2025", "data_fine": "01/12/2025", "scadenza": "01/12/2025", "stato": "Fatto", "priorita": "Alta", "note": "Completato con successo"},
    {"id": "T0H1I2J3", "titolo": "Invio documentazione certificazioni GSE", "progetto_id": "P7M8N9O0", "progetto_nome": "Fotovoltaico Tetto Industriale", "assegnato_a": "M. Diozzi", "data_inizio": "15/04/2026", "data_fine": "15/04/2026", "scadenza": "15/04/2026", "stato": "Da fare", "priorita": "Bassa", "note": "Certificati CEI + modulo GSE"},
]

_LOG = [
    {"timestamp": "09/04/2026 09:42:11", "azione": "UPDATE", "entita": "Offerte", "id_entita": "O1A2B3C4", "utente": "admin", "dettagli": "stato: Inviata, num_solleciti: 1"},
    {"timestamp": "09/04/2026 09:15:33", "azione": "CREATE", "entita": "Attività", "id_entita": "T5D6E7F8", "utente": "admin", "dettagli": "Revisione contratto software ERP"},
    {"timestamp": "09/04/2026 08:00:01", "azione": "PROMEMORIA_OFFERTE", "entita": "Sistema", "id_entita": "", "utente": "scheduler", "dettagli": "3 offerte scadute notificate"},
    {"timestamp": "07/04/2026 17:22:45", "azione": "CREATE", "entita": "Offerte", "id_entita": "O9G0H1I2", "utente": "admin", "dettagli": "Automazione linea produttiva + PLC"},
    {"timestamp": "07/04/2026 14:11:09", "azione": "UPDATE", "entita": "Progetti", "id_entita": "P3J4K5L6", "utente": "admin", "dettagli": "stato: Sospeso"},
]

# ─── Stato mutabile in memoria ─────────────────────────────────────────────────
state = {
    "clienti":   copy.deepcopy(_CLIENTI),
    "contatti":  copy.deepcopy(_CONTATTI),
    "fornitori": copy.deepcopy(_FORNITORI),
    "progetti":  copy.deepcopy(_PROGETTI),
    "offerte":   copy.deepcopy(_OFFERTE),
    "attivita":  copy.deepcopy(_ATTIVITA),
    "log":       copy.deepcopy(_LOG),
}

def _new_id():
    return str(uuid.uuid4()).replace("-","")[:8].upper()

def _find(entity, id):
    return next((x for x in state[entity] if x.get("id") == id), None)

def _log(azione, entita, id_entita, dettagli=""):
    from datetime import datetime
    state["log"].insert(0, {
        "timestamp": datetime.now().strftime("%d/%m/%Y %H:%M:%S"),
        "azione": azione, "entita": entita.capitalize(),
        "id_entita": id_entita, "utente": "admin", "dettagli": dettagli,
    })

# ─── Auth ──────────────────────────────────────────────────────────────────────
@app.post("/api/auth/token")
async def login():
    return {"access_token": "demo_token_preview", "token_type": "bearer"}

@app.get("/api/auth/me")
async def me():
    return {"username": "admin"}

# ─── Dashboard ─────────────────────────────────────────────────────────────────
@app.get("/api/dashboard/")
async def dashboard():
    attivita = state["attivita"]
    offerte  = state["offerte"]
    progetti = state["progetti"]
    attivi   = [p for p in progetti if p.get("stato") == "Attivo"]
    urgenti  = [t for t in attivita if t.get("priorita") == "Alta" and t.get("stato") != "Fatto"]
    scadute  = [o for o in offerte if o.get("stato") == "Inviata"]
    da_fare  = [t for t in attivita if t.get("stato") != "Fatto"][:5]
    return {
        "kpi": {
            "offerte_scadute": len(scadute),
            "task_urgenti": len(urgenti),
            "progetti_attivi": len(attivi),
            "offerte_totali": len(offerte),
        },
        "da_fare_oggi": da_fare,
        "offerte_scadute": scadute[:3],
        "stati_offerte": {},
    }

# ─── CRUD generico ─────────────────────────────────────────────────────────────

def _crud_routes(entity, path):
    @app.get(f"/api/{path}/", tags=[entity])
    async def get_all():
        return state[entity]

    @app.get(f"/api/{path}/{{item_id}}", tags=[entity])
    async def get_one(item_id: str):
        item = _find(entity, item_id)
        return item or {}

    @app.post(f"/api/{path}/", tags=[entity])
    async def create(request: Request):
        data = await request.json()
        data["id"] = _new_id()
        state[entity].append(data)
        _log("CREATE", entity, data["id"], str(data.get("nome") or data.get("titolo") or data.get("ragione_sociale", "")))
        return data

    @app.put(f"/api/{path}/{{item_id}}", tags=[entity])
    async def update(item_id: str, request: Request):
        data = await request.json()
        for i, item in enumerate(state[entity]):
            if item.get("id") == item_id:
                state[entity][i] = {**item, **data, "id": item_id}
                _log("UPDATE", entity, item_id, ", ".join(f"{k}: {v}" for k,v in data.items())[:100])
                return state[entity][i]
        return {}

    @app.delete(f"/api/{path}/{{item_id}}", tags=[entity], status_code=204)
    async def delete(item_id: str):
        orig = len(state[entity])
        state[entity] = [x for x in state[entity] if x.get("id") != item_id]
        if len(state[entity]) < orig:
            _log("DELETE", entity, item_id)

_crud_routes("clienti",   "clienti")
_crud_routes("contatti",  "contatti")
_crud_routes("fornitori", "fornitori")
_crud_routes("progetti",  "progetti")
_crud_routes("offerte",   "offerte")
_crud_routes("attivita",  "attivita")

# ─── Contatti per cliente ──────────────────────────────────────────────────────
@app.get("/api/contatti/by-cliente/{cliente_id}")
async def contatti_by_cliente(cliente_id: str):
    return [c for c in state["contatti"] if c.get("cliente_id") == cliente_id]

# ─── Offerte extra ─────────────────────────────────────────────────────────────
@app.post("/api/offerte/{offerta_id}/invia-richiesta")
async def invia_richiesta(offerta_id: str, request: Request):
    data = await request.json()
    _log("EMAIL_RICHIESTA", "offerte", offerta_id, f"Email inviata a {data.get('email_destinatario','')}")
    return {"ok": True}

@app.post("/api/offerte/{offerta_id}/sollecita")
async def sollecita(offerta_id: str, request: Request):
    data = await request.json()
    for i, o in enumerate(state["offerte"]):
        if o.get("id") == offerta_id:
            state["offerte"][i]["num_solleciti"] = str(int(o.get("num_solleciti", 0) or 0) + 1)
    _log("EMAIL_SOLLECITO", "offerte", offerta_id, f"Sollecito inviato a {data.get('email_destinatario','')}")
    return {"ok": True}

# ─── Log ───────────────────────────────────────────────────────────────────────
@app.get("/api/log/")
async def log(limite: int = 200):
    return state["log"][:limite]

# ─── Static files ──────────────────────────────────────────────────────────────
static_dir = Path(__file__).parent / "static"
app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

@app.get("/", include_in_schema=False)
async def index():
    html = (static_dir / "index.html").read_text()
    v = str(int(time.time()))
    html = html.replace('/static/css/app.css"', f'/static/css/app.css?v={v}"')
    html = html.replace('/static/js/app.js"', f'/static/js/app.js?v={v}"')
    return HTMLResponse(html)

@app.get("/manifest.json", include_in_schema=False)
async def manifest():
    return FileResponse(str(static_dir / "manifest.json"))

@app.get("/sw.js", include_in_schema=False)
async def sw():
    return FileResponse(str(static_dir / "sw.js"), media_type="application/javascript")

PORT = int(os.environ.get("PORT", 8766))
if __name__ == "__main__":
    uvicorn.run("preview_server:app", host="0.0.0.0", port=PORT, reload=False)
