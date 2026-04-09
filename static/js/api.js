/**
 * Client API – tutte le chiamate al backend FastAPI.
 * Gestisce il token JWT, gli errori e il refresh automatico.
 */

const BASE = '';  // Stesso origine – Nginx fa da proxy

let _token = localStorage.getItem('crm_token') || '';

export function setToken(t) {
  _token = t;
  localStorage.setItem('crm_token', t);
}

export function clearToken() {
  _token = '';
  localStorage.removeItem('crm_token');
}

export function hasToken() {
  return Boolean(_token);
}

async function request(method, path, body = null) {
  const headers = { 'Content-Type': 'application/json' };
  if (_token) headers['Authorization'] = `Bearer ${_token}`;

  const opts = { method, headers };
  if (body) opts.body = JSON.stringify(body);

  let res;
  try {
    res = await fetch(BASE + path, opts);
  } catch (e) {
    throw new Error('Errore di rete – verifica la connessione');
  }

  if (res.status === 401) {
    clearToken();
    window.dispatchEvent(new Event('crm:logout'));
    throw new Error('Sessione scaduta – effettua nuovamente il login');
  }

  if (!res.ok) {
    let msg = `Errore ${res.status}`;
    try {
      const data = await res.json();
      msg = data.detail || msg;
    } catch {}
    throw new Error(msg);
  }

  if (res.status === 204) return null;
  return res.json();
}

// ─── Auth ─────────────────────────────────────────────────────────────────

/**
 * Login Step 1: verifica password.
 * Ritorna { requires_otp, temp_token, access_token }
 * Se requires_otp=true → servire il form OTP con temp_token.
 * Se access_token presente → login completato (TOTP non configurato).
 */
export async function login(username, password) {
  const form = new URLSearchParams({ username, password });
  const res = await fetch('/api/auth/token', {
    method: 'POST',
    headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
    body: form,
  });
  if (!res.ok) throw new Error('Credenziali non valide');
  const data = await res.json();
  if (data.access_token) setToken(data.access_token);
  return data;
}

/**
 * Login Step 2: verifica codice OTP (Google Authenticator).
 * Ritorna { access_token, token_type }
 */
export async function verifyOtp(tempToken, otpCode) {
  const res = await fetch('/api/auth/verify-otp', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ temp_token: tempToken, otp_code: otpCode }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || 'Codice OTP non valido');
  }
  const data = await res.json();
  setToken(data.access_token);
  return data;
}

/** Genera QR code per setup Google Authenticator (richiede JWT valido). */
export const setupTotp   = () => request('POST', '/api/auth/setup-totp');

/** Conferma setup TOTP con codice di verifica. */
export const confirmTotp = (code) => request('POST', '/api/auth/confirm-totp', { code });

/** Disabilita TOTP. */
export const disableTotp = () => request('POST', '/api/auth/disable-totp');

/** Profilo utente corrente. */
export const getMe       = () => request('GET',  '/api/auth/me');

// ─── Dashboard ────────────────────────────────────────────────────────────
export const getDashboard = () => request('GET', '/api/dashboard/');

// ─── Clienti ─────────────────────────────────────────────────────────────
export const getClienti    = ()       => request('GET',    '/api/clienti/');
export const getCliente    = id       => request('GET',    `/api/clienti/${id}`);
export const creaCliente   = data     => request('POST',   '/api/clienti/', data);
export const updateCliente = (id, d)  => request('PUT',    `/api/clienti/${id}`, d);
export const deleteCliente = id       => request('DELETE', `/api/clienti/${id}`);

// ─── Fornitori ────────────────────────────────────────────────────────────
export const getFornitori    = ()       => request('GET',    '/api/fornitori/');
export const getFornitore    = id       => request('GET',    `/api/fornitori/${id}`);
export const creaFornitore   = data     => request('POST',   '/api/fornitori/', data);
export const updateFornitore = (id, d)  => request('PUT',    `/api/fornitori/${id}`, d);
export const deleteFornitore = id       => request('DELETE', `/api/fornitori/${id}`);

// ─── Progetti ─────────────────────────────────────────────────────────────
export const getProgetti    = ()       => request('GET',    '/api/progetti/');
export const getProgetto    = id       => request('GET',    `/api/progetti/${id}`);
export const creaProgetto   = data     => request('POST',   '/api/progetti/', data);
export const updateProgetto = (id, d)  => request('PUT',    `/api/progetti/${id}`, d);
export const deleteProgetto = id       => request('DELETE', `/api/progetti/${id}`);

// ─── Offerte ──────────────────────────────────────────────────────────────
export const getOfferte    = ()       => request('GET',    '/api/offerte/');
export const getOfferta    = id       => request('GET',    `/api/offerte/${id}`);
export const creaOfferta   = data     => request('POST',   '/api/offerte/', data);
export const updateOfferta = (id, d)  => request('PUT',    `/api/offerte/${id}`, d);
export const deleteOfferta = id       => request('DELETE', `/api/offerte/${id}`);
export const inviaRichiesta = (id, d) => request('POST',   `/api/offerte/${id}/invia-richiesta`, d);
export const sollecitaOfferta = (id, d) => request('POST', `/api/offerte/${id}/sollecita`, d);

// ─── Attività ─────────────────────────────────────────────────────────────
export const getAttivita    = ()       => request('GET',    '/api/attivita/');
export const getAttivitaById = id      => request('GET',    `/api/attivita/${id}`);
export const creaAttivita   = data     => request('POST',   '/api/attivita/', data);
export const updateAttivita = (id, d)  => request('PUT',    `/api/attivita/${id}`, d);
export const deleteAttivita = id       => request('DELETE', `/api/attivita/${id}`);

// ─── Contatti ─────────────────────────────────────────────────────────────
export const getContatti             = ()      => request('GET',    '/api/contatti/');
export const getContattiByCliente    = id      => request('GET',    `/api/contatti/by-cliente/${id}`);
export const creaContatto            = data    => request('POST',   '/api/contatti/', data);
export const updateContatto          = (id, d) => request('PUT',    `/api/contatti/${id}`, d);
export const deleteContatto          = id      => request('DELETE', `/api/contatti/${id}`);

// ─── Log ──────────────────────────────────────────────────────────────────
export const getLog = (limite = 200) => request('GET', `/api/log/?limite=${limite}`);
