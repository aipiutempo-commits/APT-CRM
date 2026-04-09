#!/usr/bin/env python3
"""
setup.py – Script di configurazione iniziale del CRM.
Esegui con:  python setup.py

Operazioni:
  1. Verifica le dipendenze Python (requirements.txt)
  2. Crea il file .env dal template se non esiste
  3. Verifica che credentials.json esista
  4. Si connette a Google Sheets e crea la struttura dei fogli
"""

import os
import sys
import subprocess
import shutil
from pathlib import Path

BASE_DIR = Path(__file__).parent


def step(msg: str):
    print(f"\n\033[1;36m▶ {msg}\033[0m")


def ok(msg: str):
    print(f"  \033[32m✓ {msg}\033[0m")


def warn(msg: str):
    print(f"  \033[33m⚠ {msg}\033[0m")


def err(msg: str):
    print(f"  \033[31m✗ {msg}\033[0m")


def ask(prompt: str, default: str = "") -> str:
    val = input(f"  {prompt} [{default}]: ").strip()
    return val if val else default


# ─── 1. Dipendenze Python ───────────────────────────────────────────────────
def check_dependencies():
    step("Verifica dipendenze Python")
    req = BASE_DIR / "requirements.txt"
    if not req.exists():
        err("requirements.txt non trovato")
        sys.exit(1)

    result = subprocess.run(
        [sys.executable, "-m", "pip", "install", "-r", str(req), "-q"],
        capture_output=True, text=True
    )
    if result.returncode != 0:
        err(f"Installazione dipendenze fallita:\n{result.stderr}")
        sys.exit(1)
    ok("Dipendenze installate")


# ─── 2. File .env ────────────────────────────────────────────────────────────
def setup_env():
    step("Configurazione variabili d'ambiente (.env)")
    env_file = BASE_DIR / ".env"
    example = BASE_DIR / ".env.example"

    if env_file.exists():
        ok(".env già presente – salto")
        return

    if not example.exists():
        err(".env.example non trovato")
        sys.exit(1)

    print("\n  Rispondo ad alcune domande per configurare il CRM:\n")

    username = ask("Username per accedere al CRM", "admin")
    password = ask("Password (scegli una password sicura)", "")
    if not password:
        err("La password non può essere vuota")
        sys.exit(1)

    spreadsheet_id = ask("ID del Google Sheet (dalla URL: /d/XXX/edit)", "")
    if not spreadsheet_id:
        warn("GOOGLE_SPREADSHEET_ID non impostato – dovrai aggiornarlo in .env manualmente")

    calendar_id = ask("ID Google Calendar (lascia 'primary' per il principale)", "primary")
    gmail_email = ask("Email Gmail del mittente (service account deve avere delegazione dominio)", "")
    report_email = ask("Email per ricevere i report automatici", gmail_email)

    import secrets
    jwt_secret = secrets.token_hex(32)

    content = (example.read_text()
        .replace("cambia_questa_password", password)
        .replace("admin", username, 1)
        .replace("chiave_segreta_molto_lunga_e_casuale_da_cambiare", jwt_secret)
        .replace("id_del_tuo_foglio_google", spreadsheet_id)
        .replace("primary", calendar_id, 1)
        .replace("tua_email@gmail.com", gmail_email)
        .replace("tua_email@gmail.com", report_email))

    env_file.write_text(content)
    ok(".env creato con successo")


# ─── 3. Credenziali Google ───────────────────────────────────────────────────
def check_credentials():
    step("Verifica credenziali Google (service account)")
    creds = BASE_DIR / "credentials.json"
    if creds.exists():
        ok("credentials.json trovato")
    else:
        warn("credentials.json NON trovato")
        print("""
  Come ottenere le credenziali:
  1. Vai su https://console.cloud.google.com/
  2. Crea un progetto (o usa uno esistente)
  3. Abilita: Google Sheets API, Google Calendar API, Gmail API, Google Tasks API
  4. IAM & Admin → Service Accounts → Crea service account
  5. Crea una chiave JSON e scaricala come 'credentials.json' in questa cartella
  6. Condividi il Google Sheet con l'email del service account (editor)
  7. Per Gmail: configura la delegazione di dominio e aggiungi gli scope nel pannello Google Workspace
        """)


# ─── 4. Struttura Google Sheet ──────────────────────────────────────────────
def init_sheets():
    step("Inizializzazione struttura Google Sheet")

    # Carica .env
    try:
        from dotenv import load_dotenv
        load_dotenv(BASE_DIR / ".env")
    except ImportError:
        pass

    creds = BASE_DIR / "credentials.json"
    spreadsheet_id = os.getenv("GOOGLE_SPREADSHEET_ID", "")

    if not creds.exists():
        warn("Salto inizializzazione Sheets – credentials.json mancante")
        return

    if not spreadsheet_id or spreadsheet_id == "id_del_tuo_foglio_google":
        warn("Salto inizializzazione Sheets – GOOGLE_SPREADSHEET_ID non configurato")
        return

    try:
        # Importa solo ora, dopo che pip ha installato le dipendenze
        sys.path.insert(0, str(BASE_DIR))
        from services.google_sheets import get_sheets_service
        svc = get_sheets_service()
        svc.init_structure()
        ok("Struttura Google Sheet creata/verificata (6 fogli)")
    except Exception as e:
        err(f"Errore connessione Google Sheets: {e}")
        print("  Verifica GOOGLE_SPREADSHEET_ID e credentials.json")


# ─── 5. Icone PWA placeholder ────────────────────────────────────────────────
def create_icons():
    step("Creazione icone PWA placeholder")
    icons_dir = BASE_DIR / "static" / "icons"
    icons_dir.mkdir(parents=True, exist_ok=True)

    # SVG semplice come placeholder
    svg = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 192 192">
  <rect width="192" height="192" rx="32" fill="#1a1f2e"/>
  <text x="96" y="130" font-family="sans-serif" font-size="100" font-weight="bold"
        text-anchor="middle" fill="#2563eb">C</text>
</svg>"""

    for size in [192, 512]:
        icon_path = icons_dir / f"icon-{size}.png"
        if not icon_path.exists():
            # Prova con Pillow, altrimenti salva SVG rinominato
            try:
                import io
                from PIL import Image, ImageDraw, ImageFont
                img = Image.new('RGB', (size, size), color='#1a1f2e')
                draw = ImageDraw.Draw(img)
                # Disegna rettangolo arrotondato e testo
                draw.rectangle([0, 0, size, size], fill=(26, 31, 46))
                font_size = int(size * 0.55)
                try:
                    font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", font_size)
                except:
                    font = ImageFont.load_default()
                text = "C"
                bbox = draw.textbbox((0, 0), text, font=font)
                tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
                draw.text(((size - tw) / 2, (size - th) / 2 - size * 0.05),
                          text, fill=(37, 99, 235), font=font)
                img.save(str(icon_path), 'PNG')
                ok(f"icon-{size}.png creata con Pillow")
            except ImportError:
                # Salva SVG come fallback (non è un PNG reale ma funziona per test)
                svg_path = icons_dir / f"icon-{size}.svg"
                svg_path.write_text(svg)
                warn(f"Pillow non disponibile – icona SVG placeholder in icon-{size}.svg")
                warn(f"Crea manualmente icon-{size}.png per la PWA")
        else:
            ok(f"icon-{size}.png già presente")


# ─── Main ────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    print("\n" + "═" * 55)
    print("  DIOZZI CRM – Setup iniziale")
    print("═" * 55)

    check_dependencies()
    setup_env()
    check_credentials()
    init_sheets()
    create_icons()

    print("\n" + "═" * 55)
    print("\033[1;32m  Setup completato!\033[0m")
    print("""
  Prossimi passi:
  1. Copia credentials.json in questa cartella (se non l'hai già fatto)
  2. Verifica il file .env e aggiusta i valori
  3. Avvia il server:   python main.py
  4. Apri nel browser: http://localhost:8000

  Per il deploy su VPS, consulta README.md → sezione Nginx
""")
    print("═" * 55 + "\n")
