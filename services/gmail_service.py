"""
Servizio Gmail – invio email di preventivo, solleciti e report settimanali.
"""

import base64
import os
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Optional

from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build

SCOPES = [
    "https://www.googleapis.com/auth/gmail.send",
]


def _get_service():
    """Costruisce il client Gmail."""
    creds_file = os.getenv("GOOGLE_SERVICE_ACCOUNT_FILE", "credentials.json")
    creds = Credentials.from_service_account_file(creds_file, scopes=SCOPES)

    # Gmail API richiede delegazione del dominio (domain-wide delegation)
    # oppure un account utente delegato via subject
    gmail_user = os.getenv("GMAIL_FROM_EMAIL", "")
    if gmail_user:
        creds = creds.with_subject(gmail_user)

    return build("gmail", "v1", credentials=creds)


def _build_message(to: str, subject: str, body_html: str, body_text: str = "") -> dict:
    """Costruisce il messaggio MIME codificato in base64 per l'API Gmail."""
    from_email = os.getenv("GMAIL_FROM_EMAIL", "")
    from_name = os.getenv("GMAIL_FROM_NAME", "CRM")

    msg = MIMEMultipart("alternative")
    msg["To"] = to
    msg["From"] = f"{from_name} <{from_email}>"
    msg["Subject"] = subject

    if body_text:
        msg.attach(MIMEText(body_text, "plain", "utf-8"))
    msg.attach(MIMEText(body_html, "html", "utf-8"))

    raw = base64.urlsafe_b64encode(msg.as_bytes()).decode()
    return {"raw": raw}


def invia_email(to: str, subject: str, body_html: str, body_text: str = "") -> bool:
    """
    Invia un'email via Gmail API.
    Ritorna True se l'invio ha successo.
    """
    try:
        service = _get_service()
        message = _build_message(to, subject, body_html, body_text)
        service.users().messages().send(userId="me", body=message).execute()
        return True
    except Exception as e:
        print(f"[Gmail] Errore invio email a {to}: {e}")
        return False


# ─── Template email ──────────────────────────────────────────────────────────

def template_richiesta_preventivo(
    fornitore_nome: str,
    progetto_nome: str,
    descrizione: str,
    scadenza: str = "",
) -> tuple[str, str]:
    """
    Genera oggetto e corpo HTML per una email di richiesta preventivo.
    Ritorna (subject, body_html).
    """
    subject = f"Richiesta Preventivo – {progetto_nome}"
    scadenza_str = f"<p>Vi chiediamo di inviarci il preventivo entro il <strong>{scadenza}</strong>.</p>" if scadenza else ""

    body_html = f"""
    <html><body style="font-family: Arial, sans-serif; color: #333;">
      <p>Gentili {fornitore_nome},</p>
      <p>Vi contatto per richiedere un preventivo relativo al progetto <strong>{progetto_nome}</strong>.</p>
      <p><strong>Descrizione lavori/fornitura:</strong><br>{descrizione}</p>
      {scadenza_str}
      <p>Per qualsiasi chiarimento rimango a disposizione.</p>
      <p>Cordiali saluti,<br><em>Inviato dal CRM Personale</em></p>
    </body></html>
    """
    return subject, body_html


def template_sollecito(
    fornitore_nome: str,
    progetto_nome: str,
    descrizione: str,
    data_invio_originale: str,
    num_sollecito: int = 1,
) -> tuple[str, str]:
    """
    Genera oggetto e corpo HTML per un sollecito offerta.
    Ritorna (subject, body_html).
    """
    subject = f"Sollecito ({num_sollecito}) – Preventivo {progetto_nome}"

    body_html = f"""
    <html><body style="font-family: Arial, sans-serif; color: #333;">
      <p>Gentili {fornitore_nome},</p>
      <p>Vi contatto per sollecitare un riscontro alla nostra richiesta di preventivo del <strong>{data_invio_originale}</strong>
      relativa al progetto <strong>{progetto_nome}</strong>.</p>
      <p><strong>Oggetto:</strong> {descrizione}</p>
      <p>In attesa di un vostro cortese riscontro, porgo cordiali saluti.</p>
      <p><em>Inviato dal CRM Personale – Sollecito n.{num_sollecito}</em></p>
    </body></html>
    """
    return subject, body_html


def template_promemoria_offerta_scaduta(
    offerte_scadute: list,
) -> tuple[str, str]:
    """
    Genera il report giornaliero delle offerte scadute.
    Ritorna (subject, body_html).
    """
    subject = f"[CRM] Offerte in attesa – {datetime.now().strftime('%d/%m/%Y')}"

    righe = ""
    for o in offerte_scadute:
        righe += f"""
        <tr>
          <td style="padding:6px; border-bottom:1px solid #eee">{o.get('progetto_nome','')}</td>
          <td style="padding:6px; border-bottom:1px solid #eee">{o.get('fornitore_nome','')}</td>
          <td style="padding:6px; border-bottom:1px solid #eee">{o.get('descrizione','')[:60]}</td>
          <td style="padding:6px; border-bottom:1px solid #eee">{o.get('scadenza_attesa','')}</td>
          <td style="padding:6px; border-bottom:1px solid #eee">{o.get('num_solleciti','0')}</td>
        </tr>
        """

    body_html = f"""
    <html><body style="font-family: Arial, sans-serif; color: #333;">
      <h2 style="color:#c0392b;">⚠ Offerte in attesa di risposta</h2>
      <p>Le seguenti offerte hanno superato la scadenza attesa e sono ancora in stato "Inviata":</p>
      <table style="border-collapse:collapse; width:100%; font-size:14px;">
        <thead style="background:#f5f5f5;">
          <tr>
            <th style="padding:6px; text-align:left;">Progetto</th>
            <th style="padding:6px; text-align:left;">Fornitore</th>
            <th style="padding:6px; text-align:left;">Descrizione</th>
            <th style="padding:6px; text-align:left;">Scadenza</th>
            <th style="padding:6px; text-align:left;">Solleciti</th>
          </tr>
        </thead>
        <tbody>{righe}</tbody>
      </table>
      <p style="color:#888; font-size:12px; margin-top:20px;">
        Inviato automaticamente dal CRM Personale – {datetime.now().strftime('%d/%m/%Y %H:%M')}
      </p>
    </body></html>
    """
    return subject, body_html


def template_report_settimanale(
    offerte_scadute: list,
    task_in_scadenza: list,
    progetti_attivi: list,
) -> tuple[str, str]:
    """
    Genera il report settimanale del lunedì mattina.
    Ritorna (subject, body_html).
    """
    from datetime import date, timedelta
    oggi = date.today()
    fine_settimana = oggi + timedelta(days=7)

    subject = f"[CRM] Report settimanale – {oggi.strftime('%d/%m/%Y')}"

    def _tabella(titolo: str, colonne: list, righe_html: str, colore: str = "#2c3e50") -> str:
        return f"""
        <h3 style="color:{colore}; border-bottom:2px solid {colore}; padding-bottom:4px;">{titolo}</h3>
        <table style="border-collapse:collapse; width:100%; font-size:13px; margin-bottom:20px;">
          <thead style="background:#f0f0f0;">
            <tr>{''.join(f'<th style="padding:5px 8px; text-align:left;">{c}</th>' for c in colonne)}</tr>
          </thead>
          <tbody>{righe_html or '<tr><td colspan="99" style="padding:8px; color:#999;">Nessun elemento</td></tr>'}</tbody>
        </table>
        """

    # Tabella offerte scadute
    righe_offerte = ""
    for o in offerte_scadute:
        righe_offerte += f"""<tr>
          <td style="padding:5px 8px; border-bottom:1px solid #eee">{o.get('progetto_nome','')}</td>
          <td style="padding:5px 8px; border-bottom:1px solid #eee">{o.get('fornitore_nome','')}</td>
          <td style="padding:5px 8px; border-bottom:1px solid #eee">{o.get('scadenza_attesa','')}</td>
          <td style="padding:5px 8px; border-bottom:1px solid #eee">{o.get('stato','')}</td>
        </tr>"""

    # Tabella task in scadenza questa settimana
    righe_task = ""
    for t in task_in_scadenza:
        righe_task += f"""<tr>
          <td style="padding:5px 8px; border-bottom:1px solid #eee">{t.get('titolo','')}</td>
          <td style="padding:5px 8px; border-bottom:1px solid #eee">{t.get('progetto_nome','')}</td>
          <td style="padding:5px 8px; border-bottom:1px solid #eee">{t.get('scadenza','')}</td>
          <td style="padding:5px 8px; border-bottom:1px solid #eee">{t.get('priorita','')}</td>
        </tr>"""

    # Tabella progetti attivi
    righe_progetti = ""
    for p in progetti_attivi:
        righe_progetti += f"""<tr>
          <td style="padding:5px 8px; border-bottom:1px solid #eee">{p.get('nome','')}</td>
          <td style="padding:5px 8px; border-bottom:1px solid #eee">{p.get('cliente_nome','')}</td>
          <td style="padding:5px 8px; border-bottom:1px solid #eee">{p.get('data_fine_prevista','')}</td>
        </tr>"""

    body_html = f"""
    <html><body style="font-family: Arial, sans-serif; color: #333; max-width:800px;">
      <h2 style="color:#2c3e50;">📋 Report CRM – Settimana del {oggi.strftime('%d/%m/%Y')}</h2>
      {_tabella('⚠ Offerte Scadute / In Attesa', ['Progetto','Fornitore','Scadenza','Stato'], righe_offerte, '#c0392b')}
      {_tabella('📅 Task in scadenza questa settimana', ['Titolo','Progetto','Scadenza','Priorità'], righe_task, '#e67e22')}
      {_tabella('🔵 Progetti Attivi', ['Nome','Cliente','Fine Prevista'], righe_progetti, '#2980b9')}
      <p style="color:#aaa; font-size:11px;">
        Report automatico CRM Personale – {datetime.now().strftime('%d/%m/%Y %H:%M')}
      </p>
    </body></html>
    """
    return subject, body_html
