"""
Scheduler APScheduler – automazioni giornaliere e settimanali del CRM.
"""

import os
from datetime import date, datetime, timedelta

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

from services.google_sheets import (
    SHEET_ATTIVITA,
    SHEET_OFFERTE,
    SHEET_PROGETTI,
    get_sheets_service,
)
from services.gmail_service import (
    invia_email,
    template_promemoria_offerta_scaduta,
    template_report_settimanale,
)

_scheduler: BackgroundScheduler = None


def _parse_date(date_str: str):
    """Converte gg/mm/aaaa o aaaa-mm-gg in oggetto date, None se non valido."""
    if not date_str:
        return None
    for fmt in ("%d/%m/%Y", "%Y-%m-%d"):
        try:
            return datetime.strptime(date_str.strip(), fmt).date()
        except ValueError:
            continue
    return None


# ─── Job: promemoria giornaliero offerte scadute ─────────────────────────────

def job_promemoria_offerte():
    """
    Ogni giorno alle 08:00 – controlla le offerte in stato "Inviata" con
    scadenza passata e invia un'email di promemoria all'utente.
    """
    try:
        sheets = get_sheets_service()
        offerte = sheets.get_all(SHEET_OFFERTE)
        oggi = date.today()

        scadute = []
        for o in offerte:
            if o.get("stato") != "Inviata":
                continue
            scadenza = _parse_date(o.get("scadenza_attesa", ""))
            if scadenza and scadenza < oggi:
                scadute.append(o)

        if not scadute:
            return

        recipient = os.getenv("REPORT_RECIPIENT_EMAIL", "")
        if not recipient:
            print("[Scheduler] REPORT_RECIPIENT_EMAIL non configurato")
            return

        subject, body_html = template_promemoria_offerta_scaduta(scadute)
        invia_email(recipient, subject, body_html)
        sheets.log_action(
            "PROMEMORIA_OFFERTE",
            "Offerte",
            "",
            "scheduler",
            f"Inviate {len(scadute)} offerte scadute a {recipient}",
        )
        print(f"[Scheduler] Promemoria offerte inviato: {len(scadute)} scadute")

    except Exception as e:
        print(f"[Scheduler] Errore job_promemoria_offerte: {e}")


# ─── Job: report settimanale del lunedì ──────────────────────────────────────

def job_report_settimanale():
    """
    Ogni lunedì alle 07:30 – genera e invia il report settimanale via Gmail.
    """
    try:
        sheets = get_sheets_service()
        oggi = date.today()
        fine_settimana = oggi + timedelta(days=7)

        # Offerte scadute (in attesa)
        offerte = sheets.get_all(SHEET_OFFERTE)
        offerte_scadute = [
            o for o in offerte
            if o.get("stato") in ("Inviata", "In Valutazione")
            and _parse_date(o.get("scadenza_attesa", ""))
            and _parse_date(o.get("scadenza_attesa", "")) < oggi
        ]

        # Task in scadenza questa settimana (non completati)
        tasks = sheets.get_all(SHEET_ATTIVITA)
        task_in_scadenza = [
            t for t in tasks
            if t.get("stato") != "Fatto"
            and _parse_date(t.get("scadenza", ""))
            and oggi <= _parse_date(t.get("scadenza", "")) <= fine_settimana
        ]

        # Progetti attivi
        progetti = sheets.get_all(SHEET_PROGETTI)
        progetti_attivi = [p for p in progetti if p.get("stato") == "Attivo"]

        recipient = os.getenv("REPORT_RECIPIENT_EMAIL", "")
        if not recipient:
            print("[Scheduler] REPORT_RECIPIENT_EMAIL non configurato")
            return

        subject, body_html = template_report_settimanale(
            offerte_scadute, task_in_scadenza, progetti_attivi
        )
        invia_email(recipient, subject, body_html)

        sheets.log_action(
            "REPORT_SETTIMANALE",
            "Sistema",
            "",
            "scheduler",
            f"Report inviato a {recipient}: {len(offerte_scadute)} offerte scadute, "
            f"{len(task_in_scadenza)} task in scadenza, {len(progetti_attivi)} progetti attivi",
        )
        print(f"[Scheduler] Report settimanale inviato a {recipient}")

    except Exception as e:
        print(f"[Scheduler] Errore job_report_settimanale: {e}")


# ─── Avvio scheduler ─────────────────────────────────────────────────────────

def avvia_scheduler():
    """Configura e avvia lo scheduler in background."""
    global _scheduler
    _scheduler = BackgroundScheduler(timezone="Europe/Rome")

    # Promemoria giornaliero offerte: ogni giorno alle 08:00
    _scheduler.add_job(
        job_promemoria_offerte,
        CronTrigger(hour=8, minute=0, timezone="Europe/Rome"),
        id="promemoria_offerte",
        replace_existing=True,
    )

    # Report settimanale: ogni lunedì alle 07:30
    _scheduler.add_job(
        job_report_settimanale,
        CronTrigger(day_of_week="mon", hour=7, minute=30, timezone="Europe/Rome"),
        id="report_settimanale",
        replace_existing=True,
    )

    _scheduler.start()
    print("[Scheduler] Avviato – promemoria 08:00 / report lunedì 07:30")


def ferma_scheduler():
    """Ferma lo scheduler (chiamato allo shutdown di FastAPI)."""
    global _scheduler
    if _scheduler and _scheduler.running:
        _scheduler.shutdown(wait=False)
        print("[Scheduler] Fermato")
