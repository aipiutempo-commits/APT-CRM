/**
 * DIOZZI CRM – SPA con navigazione bidirezionale tra entità
 * Dettagli per: Progetti, Clienti, Fornitori, Offerte, Attività
 * Viste speciali: Kanban (Attività), Gantt (Progetti)
 */

import * as api from './api.js?v=2';

// ─── Navigazione con filtro preimpostato ───────────────────────────────────
window.navigateWithFilter = function(view, filterKey, filterValue) {
  navigateTo(view);
  if (filterKey && filterValue) {
    setTimeout(() => {
      const el = document.getElementById(`filter-stato-${view}`) ||
                 document.getElementById(`filter-prio-${view}`);
      if (el) { el.value = filterValue; window.filterTable(view); }
    }, 450);
  }
};

// ─── Stato globale ─────────────────────────────────────────────────────────
let _cachedData = {};
let _ganttProjectOrder = null;  // ordine manuale righe Gantt

// ─── Boot ──────────────────────────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', () => {
  if ('serviceWorker' in navigator) navigator.serviceWorker.register('/sw.js').catch(() => {});
  window.addEventListener('crm:logout', showLogin);
  if (api.hasToken()) { showApp(); navigateTo('dashboard'); } else showLogin();

  document.getElementById('menu-toggle').addEventListener('click', toggleSidebar);
  document.getElementById('overlay').addEventListener('click', closeSidebar);
  document.getElementById('btn-logout').addEventListener('click', logout);
  document.getElementById('btn-login').addEventListener('click', doLogin);
  document.getElementById('login-password').addEventListener('keydown', e => { if (e.key === 'Enter') doLogin(); });
  document.getElementById('btn-verify-otp')?.addEventListener('click', doVerifyOtp);
  document.getElementById('otp-input')?.addEventListener('keydown', e => { if (e.key === 'Enter') doVerifyOtp(); });
  document.getElementById('modal-overlay')?.addEventListener('click', e => {
    if (e.target === document.getElementById('modal-overlay')) closeModal();
  });
});

// ─── Auth (2-step: password + OTP) ────────────────────────────────────────

let _pendingTempToken = null;  // Token temporaneo per verifica OTP

function showLogin() {
  document.getElementById('login-screen').style.display = 'flex';
  document.getElementById('app').style.display = 'none';
  document.getElementById('login-password').value = '';
  document.getElementById('login-error').textContent = '';
  _hideOtpStep();
}
function showApp() {
  document.getElementById('login-screen').style.display = 'none';
  document.getElementById('app').style.display = 'flex';
}

function _showOtpStep() {
  document.getElementById('login-step-password').style.display = 'none';
  document.getElementById('login-step-otp').style.display = 'block';
  document.getElementById('otp-input')?.focus();
}
function _hideOtpStep() {
  const otpStep = document.getElementById('login-step-otp');
  const pwdStep = document.getElementById('login-step-password');
  if (otpStep) otpStep.style.display = 'none';
  if (pwdStep) pwdStep.style.display = 'block';
  _pendingTempToken = null;
}

async function doLogin() {
  const u = document.getElementById('login-username').value.trim();
  const p = document.getElementById('login-password').value;
  const errEl = document.getElementById('login-error');
  errEl.textContent = '';
  document.getElementById('btn-login').disabled = true;
  try {
    const result = await api.login(u, p);
    if (result.requires_otp) {
      // Step 2: mostra il campo OTP
      _pendingTempToken = result.temp_token;
      _showOtpStep();
    } else {
      // Login diretto (TOTP non configurato)
      showApp(); navigateTo('dashboard');
    }
  } catch (e) { errEl.textContent = e.message; }
  finally { document.getElementById('btn-login').disabled = false; }
}

async function doVerifyOtp() {
  const code = document.getElementById('otp-input')?.value.trim();
  const errEl = document.getElementById('login-error');
  errEl.textContent = '';
  if (!code || code.length !== 6) { errEl.textContent = 'Inserisci il codice a 6 cifre'; return; }
  const btn = document.getElementById('btn-verify-otp');
  if (btn) btn.disabled = true;
  try {
    await api.verifyOtp(_pendingTempToken, code);
    _pendingTempToken = null;
    showApp(); navigateTo('dashboard');
  } catch (e) { errEl.textContent = e.message; }
  finally { if (btn) btn.disabled = false; }
}
window.doVerifyOtp = doVerifyOtp;

function logout() { api.clearToken(); _cachedData = {}; showLogin(); }

// ─── Sidebar ───────────────────────────────────────────────────────────────
function toggleSidebar() {
  document.getElementById('sidebar').classList.toggle('open');
  document.getElementById('overlay').classList.toggle('visible');
}
function closeSidebar() {
  document.getElementById('sidebar').classList.remove('open');
  document.getElementById('overlay').classList.remove('visible');
}

// ─── Navigazione ───────────────────────────────────────────────────────────
const VIEW_TITLES = {
  dashboard: 'Dashboard', clienti: 'Clienti', contatti: 'Contatti', fornitori: 'Fornitori',
  progetti: 'Progetti', offerte: 'Offerte / Preventivi', attivita: 'Attività', log: 'Log',
};

export function navigateTo(view) {
  closeSidebar();
  _setNav(view, VIEW_TITLES[view] || view);
  renderView(view);
}
window.navigateTo = navigateTo;

function _setNav(view, title) {
  document.getElementById('page-title').textContent = title;
  document.querySelectorAll('.nav-item').forEach(el =>
    el.classList.toggle('active', el.dataset.view === view));
}

async function renderView(view) {
  const content = document.getElementById('content');
  content.innerHTML = `<div class="loader"><div class="spinner"></div> Caricamento…</div>`;
  try {
    switch (view) {
      case 'dashboard': await renderDashboard(content); break;
      case 'clienti':   await renderEntityTable(content, 'clienti');   break;
      case 'contatti':  await renderEntityTable(content, 'contatti');  break;
      case 'fornitori': await renderEntityTable(content, 'fornitori'); break;
      case 'progetti':  await renderEntityTable(content, 'progetti');  break;
      case 'offerte':   await renderEntityTable(content, 'offerte');   break;
      case 'attivita':  await renderEntityTable(content, 'attivita');  break;
      case 'log':       await renderLog(content); break;
    }
  } catch (e) {
    content.innerHTML = `<div class="loader" style="color:var(--danger)">⚠ ${e.message}</div>`;
  }
  setTimeout(() => window._refreshIcons?.(), 50);
}

// ─── Cache helper ──────────────────────────────────────────────────────────
async function _ensureCache(entity) {
  if (!_cachedData[entity]) {
    _cachedData[entity] = await ENTITY_CONFIG[entity].fetchAll();
  }
  return _cachedData[entity];
}

// ─── Dashboard ─────────────────────────────────────────────────────────────
async function renderDashboard(el) {
  const data = await api.getDashboard();
  el.innerHTML = `
    <div class="kpi-grid">
      <div class="kpi-card danger kpi-clickable" onclick="navigateWithFilter('offerte','stato','Inviata')" title="Vai alle offerte in attesa">
        <div class="kpi-icon"><i data-lucide="alert-triangle"></i></div><div class="kpi-body"><div class="kpi-value">${data.kpi.offerte_scadute}</div><div class="kpi-label">Offerte scadute</div></div>
      </div>
      <div class="kpi-card warning kpi-clickable" onclick="navigateWithFilter('attivita','prio','Alta')" title="Vai ai task urgenti">
        <div class="kpi-icon"><i data-lucide="flame"></i></div><div class="kpi-body"><div class="kpi-value">${data.kpi.task_urgenti}</div><div class="kpi-label">Task urgenti</div></div>
      </div>
      <div class="kpi-card success kpi-clickable" onclick="navigateWithFilter('progetti','stato','Attivo')" title="Vai ai progetti attivi">
        <div class="kpi-icon"><i data-lucide="folder-open"></i></div><div class="kpi-body"><div class="kpi-value">${data.kpi.progetti_attivi}</div><div class="kpi-label">Progetti attivi</div></div>
      </div>
      <div class="kpi-card info kpi-clickable" onclick="navigateTo('offerte')" title="Vai a tutte le offerte">
        <div class="kpi-icon"><i data-lucide="file-check"></i></div><div class="kpi-body"><div class="kpi-value">${data.kpi.offerte_totali}</div><div class="kpi-label">Offerte totali</div></div>
      </div>
    </div>
    <div class="section">
      <div class="section-header">
        <span class="section-title"><i data-lucide="clipboard-list" style="width:16px;height:16px;display:inline;vertical-align:-2px"></i> Da fare oggi</span>
        <button class="btn btn-primary btn-sm" onclick="navigateTo('attivita')">Tutte le attività</button>
      </div>
      <div id="dash-tasks"></div>
    </div>
    <div class="section section-dark">
      <div class="section-header">
        <span class="section-title"><i data-lucide="alert-circle" style="width:16px;height:16px;display:inline;vertical-align:-2px"></i> Offerte in scadenza</span>
        <button class="btn btn-ghost-dark btn-sm" onclick="navigateTo('offerte')">Vedi tutte</button>
      </div>
      <div id="dash-offerte"></div>
    </div>`;

  // Tasks table
  const tasksEl = el.querySelector('#dash-tasks');
  if (!data.da_fare_oggi.length) {
    tasksEl.innerHTML = `<div class="empty-state"><div class="icon"><i data-lucide="check-circle" style="width:36px;height:36px"></i></div>Nessun task in scadenza oggi</div>`;
  } else {
    tasksEl.innerHTML = `<div class="table-wrap"><table>
      <thead><tr><th>Titolo</th><th class="hide-mobile">Progetto</th><th>Scadenza</th><th>Priorità</th><th>Stato</th></tr></thead>
      <tbody>${data.da_fare_oggi.map(t => `<tr>
        <td><span class="link-cell" onclick="openAttivitaDetail('${t.id}')">${esc(t.titolo)}</span></td>
        <td class="hide-mobile"><span class="link-cell" onclick="openProgettoDetailByName('${t.progetto_nome.replace(/'/g,"\\'")}'">${esc(t.progetto_nome)}</span></td>
        <td>${esc(t.scadenza)}</td><td>${badgePriorita(t.priorita)}</td><td>${badgeStatoTask(t.stato)}</td>
      </tr>`).join('')}</tbody></table></div>`;
  }

  // Offerte table
  const offerteEl = el.querySelector('#dash-offerte');
  if (!data.offerte_scadute.length) {
    offerteEl.innerHTML = `<div class="empty-state"><div class="icon">👍</div>Nessuna offerta scaduta</div>`;
  } else {
    offerteEl.innerHTML = `<div class="table-wrap"><table>
      <thead><tr><th>Progetto</th><th class="hide-mobile">Fornitore</th><th>Scadenza</th><th>Solleciti</th></tr></thead>
      <tbody>${data.offerte_scadute.map(o => `<tr>
        <td><span class="link-cell" onclick="openProgettoDetailByName('${o.progetto_nome.replace(/'/g,"\\'")}'">${esc(o.progetto_nome)}</span></td>
        <td class="hide-mobile"><span class="link-cell" onclick="openFornitoreDetailByName('${o.fornitore_nome.replace(/'/g,"\\'")}'">${esc(o.fornitore_nome)}</span></td>
        <td style="color:var(--danger)">${esc(o.scadenza_attesa)}</td><td>${o.num_solleciti || 0}</td>
      </tr>`).join('')}</tbody></table></div>`;
  }
}

// ─── Config entità ─────────────────────────────────────────────────────────
const ENTITY_CONFIG = {
  clienti: {
    fetchAll: api.getClienti, create: api.creaCliente,
    update: api.updateCliente, delete: api.deleteCliente,
    columns: [
      { key: 'ragione_sociale', label: 'Ragione Sociale', sortable: true, link: true },
      { key: 'referente',       label: 'Referente',       sortable: true },
      { key: 'email',           label: 'Email',           mobile: false },
      { key: 'telefono',        label: 'Telefono',        mobile: false },
    ],
    fields: [
      { key: 'ragione_sociale', label: 'Ragione Sociale', type: 'text', required: true },
      { key: 'referente',  label: 'Referente',  type: 'text' },
      { key: 'email',      label: 'Email',      type: 'email' },
      { key: 'telefono',   label: 'Telefono',   type: 'tel' },
      { key: 'note',       label: 'Note',       type: 'textarea', span: 2 },
    ],
    filterKey: 'ragione_sociale', title: 'cliente', detailFn: 'openClienteDetail',
  },

  contatti: {
    fetchAll: api.getContatti, create: api.creaContatto,
    update: api.updateContatto, delete: api.deleteContatto,
    columns: [
      { key: '_nome_completo', label: 'Nome',       sortable: true, computed: r => `${r.nome||''} ${r.cognome||''}`.trim() },
      { key: 'ruolo',          label: 'Ruolo',      sortable: true },
      { key: 'cliente_nome',   label: 'Cliente',    sortable: true, clienteLink: true },
      { key: 'email',          label: 'Email',      mobile: false },
      { key: 'telefono',       label: 'Telefono',   mobile: false },
    ],
    fields: [
      { key: 'nome',         label: 'Nome',     type: 'text', required: true },
      { key: 'cognome',      label: 'Cognome',  type: 'text', required: true },
      { key: 'ruolo',        label: 'Ruolo',    type: 'text' },
      { key: 'cliente_id',   label: 'ID Cliente', type: 'text' },
      { key: 'cliente_nome', label: 'Cliente',  type: 'text' },
      { key: 'email',        label: 'Email',    type: 'email' },
      { key: 'telefono',     label: 'Telefono', type: 'tel' },
      { key: 'note',         label: 'Note',     type: 'textarea', span: 2 },
    ],
    filterKey: '_nome_completo', title: 'contatto',
  },

  fornitori: {
    fetchAll: api.getFornitori, create: api.creaFornitore,
    update: api.updateFornitore, delete: api.deleteFornitore,
    columns: [
      { key: 'ragione_sociale', label: 'Ragione Sociale', sortable: true, link: true },
      { key: 'tipo',      label: 'Tipo',      badge: 'tipo' },
      { key: 'referente', label: 'Referente', mobile: false },
      { key: 'email',     label: 'Email',     mobile: false },
    ],
    fields: [
      { key: 'ragione_sociale', label: 'Ragione Sociale', type: 'text', required: true },
      { key: 'tipo',      label: 'Tipo',      type: 'select', options: ['Elettrico','Software','Altro'] },
      { key: 'referente', label: 'Referente', type: 'text' },
      { key: 'email',     label: 'Email',     type: 'email' },
      { key: 'telefono',  label: 'Telefono',  type: 'tel' },
      { key: 'note',      label: 'Note',      type: 'textarea', span: 2 },
    ],
    filterKey: 'ragione_sociale', title: 'fornitore', detailFn: 'openFornitoreDetail',
  },

  progetti: {
    fetchAll: api.getProgetti, create: api.creaProgetto,
    update: api.updateProgetto, delete: api.deleteProgetto,
    columns: [
      { key: 'nome',               label: 'Nome',          sortable: true, link: true },
      { key: 'cliente_nome',       label: 'Cliente',       mobile: false, clienteLink: true },
      { key: 'stato',              label: 'Stato',         badge: 'progetto' },
      { key: 'data_fine_prevista', label: 'Fine Prevista', mobile: false },
    ],
    fields: [
      { key: 'nome',               label: 'Nome Progetto',  type: 'text', required: true },
      { key: 'cliente_id',         label: 'ID Cliente',     type: 'text' },
      { key: 'cliente_nome',       label: 'Nome Cliente',   type: 'text' },
      { key: 'stato',   label: 'Stato', type: 'select', options: ['Attivo','Sospeso','Chiuso'] },
      { key: 'data_inizio',        label: 'Data Inizio',    type: 'date' },
      { key: 'data_fine_prevista', label: 'Fine Prevista',  type: 'date' },
      { key: 'note',               label: 'Note',           type: 'textarea', span: 2 },
    ],
    filterKey: 'nome', title: 'progetto', detailFn: 'openProgettoDetail',
  },

  offerte: {
    fetchAll: api.getOfferte, create: api.creaOfferta,
    update: api.updateOfferta, delete: api.deleteOfferta,
    columns: [
      { key: 'progetto_nome',  label: 'Progetto',  sortable: true, projectLink: true },
      { key: 'fornitore_nome', label: 'Fornitore', mobile: false, forniLink: true },
      { key: 'tipo',           label: 'Tipo' },
      { key: 'stato',          label: 'Stato',    badge: 'offerta' },
      { key: 'scadenza_attesa',label: 'Scadenza', mobile: false },
      { key: 'importo',        label: '€',        mobile: false },
      { key: 'priorita',       label: 'Priorità', badge: 'priorita', mobile: false },
    ],
    fields: [
      { key: 'progetto_id',          label: 'ID Progetto',    type: 'text' },
      { key: 'progetto_nome',        label: 'Nome Progetto',  type: 'text' },
      { key: 'tipo', label: 'Tipo', type: 'select', options: ['Elettrico','Software','Civile','Altro'] },
      { key: 'fornitore_id',         label: 'ID Fornitore',   type: 'text' },
      { key: 'fornitore_nome',       label: 'Nome Fornitore', type: 'text' },
      { key: 'descrizione',          label: 'Descrizione',    type: 'textarea', span: 2 },
      { key: 'data_invio_richiesta', label: 'Data Invio',     type: 'date' },
      { key: 'scadenza_attesa',      label: 'Scadenza Attesa',type: 'date' },
      { key: 'stato', label: 'Stato', type: 'select',
        options: ['Da Inviare','Inviata','Ricevuta','In Valutazione','Aggiudicata','Rifiutata'] },
      { key: 'data_ricezione', label: 'Data Ricezione', type: 'date' },
      { key: 'importo',        label: 'Importo €',      type: 'text' },
      { key: 'priorita', label: 'Priorità', type: 'select', options: ['Alta','Media','Bassa'] },
      { key: 'num_solleciti',  label: 'Num. Solleciti', type: 'number' },
      { key: 'note',           label: 'Note',           type: 'textarea', span: 2 },
    ],
    filterKey: 'progetto_nome',
    filterStatus: ['stato', ['Da Inviare','Inviata','Ricevuta','In Valutazione','Aggiudicata','Rifiutata']],
    title: 'offerta', extraActions: true,
  },

  attivita: {
    fetchAll: api.getAttivita, create: api.creaAttivita,
    update: api.updateAttivita, delete: api.deleteAttivita,
    columns: [
      { key: 'titolo',        label: 'Titolo',    sortable: true, link: true },
      { key: 'progetto_nome', label: 'Progetto',  mobile: false, projectLink: true },
      { key: 'assegnato_a',   label: 'Assegnato', mobile: false },
      { key: 'scadenza',      label: 'Scadenza' },
      { key: 'stato',         label: 'Stato',    badge: 'task' },
      { key: 'priorita',      label: 'Priorità', badge: 'priorita', mobile: false },
    ],
    fields: [
      { key: 'titolo',        label: 'Titolo',        type: 'text', required: true, span: 2 },
      { key: 'progetto_id',   label: 'ID Progetto',   type: 'text' },
      { key: 'progetto_nome', label: 'Nome Progetto', type: 'text' },
      { key: 'assegnato_a',   label: 'Assegnato a',   type: 'text' },
      { key: 'data_inizio',   label: 'Data Inizio',   type: 'date' },
      { key: 'data_fine',     label: 'Data Fine',     type: 'date' },
      { key: 'scadenza',      label: 'Scadenza',      type: 'date' },
      { key: 'stato', label: 'Stato', type: 'select', options: ['Da fare','In corso','Fatto'] },
      { key: 'priorita', label: 'Priorità', type: 'select', options: ['Alta','Media','Bassa'] },
      { key: 'note',          label: 'Note',          type: 'textarea', span: 2 },
    ],
    filterKey: 'titolo',
    filterStatus: ['stato', ['Da fare','In corso','Fatto']],
    filterPrio: ['priorita', ['Alta','Media','Bassa']],
    title: 'attività', detailFn: 'openAttivitaDetail',
  },
};

// ─── Tabelle generiche ─────────────────────────────────────────────────────
async function renderEntityTable(el, entity) {
  const cfg = ENTITY_CONFIG[entity];
  const items = await cfg.fetchAll();
  _cachedData[entity] = items;

  const isProgetti  = entity === 'progetti';
  const isAttivita  = entity === 'attivita';
  const hasViewToggle = isProgetti || isAttivita;

  el.innerHTML = `
    <div class="section">
      <div class="section-header">
        <span class="section-title">${VIEW_TITLES[entity]}</span>
        <div style="display:flex;gap:8px;align-items:center">
          ${hasViewToggle ? `
            <div class="view-toggle" id="view-toggle-${entity}">
              <button class="view-toggle-btn active" data-view="table" onclick="switchView('${entity}','table')">≡ Lista</button>
              ${isAttivita ? `<button class="view-toggle-btn" data-view="kanban" onclick="switchView('${entity}','kanban')">☰ Kanban</button>` : ''}
              ${isProgetti ? `<button class="view-toggle-btn" data-view="gantt" onclick="switchView('${entity}','gantt')"><i data-lucide="gantt-chart" style="width:14px;height:14px;display:inline;vertical-align:-2px"></i> Gantt</button>` : ''}
            </div>` : ''}
          <button class="btn btn-primary btn-sm" onclick="openCreateModal('${entity}')">+ Nuovo</button>
          ${entity === 'contatti' ? `<button class="btn btn-ghost btn-sm" onclick="syncGoogleContacts()" title="Sincronizza da Google Workspace"><i data-lucide="refresh-cw" style="width:14px;height:14px"></i> Google</button>` : ''}
          <button class="btn btn-ghost btn-sm" onclick="scaricaTemplateCSV('${entity}')" title="Scarica template CSV"><i data-lucide="download" style="width:14px;height:14px"></i></button>
          <button class="btn btn-ghost btn-sm" onclick="importaCSV('${entity}')" title="Importa CSV"><i data-lucide="upload" style="width:14px;height:14px"></i> CSV</button>
          <input type="file" id="csv-input-${entity}" accept=".csv" style="display:none" onchange="handleCSVUpload(event,'${entity}')">
        </div>
      </div>
      <div class="toolbar" id="toolbar-${entity}">
        <input class="search-input" type="search" placeholder="Cerca…"
               id="search-${entity}" oninput="filterTable('${entity}')">
        ${cfg.filterStatus ? `
          <select class="filter-select" id="filter-stato-${entity}" onchange="filterTable('${entity}')">
            <option value="">Tutti gli stati</option>
            ${cfg.filterStatus[1].map(s => `<option value="${s}">${s}</option>`).join('')}
          </select>` : ''}
        ${cfg.filterPrio ? `
          <select class="filter-select" id="filter-prio-${entity}" onchange="filterTable('${entity}')">
            <option value="">Tutte le priorità</option>
            ${cfg.filterPrio[1].map(s => `<option value="${s}">${s}</option>`).join('')}
          </select>` : ''}
      </div>
      ${isProgetti ? `
      <div class="toolbar" id="gantt-toolbar-${entity}" style="display:none">
        <input class="search-input" type="search" placeholder="Cerca progetto…"
               id="gantt-search-${entity}" oninput="applyGanttFilters('${entity}')">
        <select class="filter-select" id="gantt-stato-${entity}" onchange="applyGanttFilters('${entity}')">
          <option value="">Tutti gli stati</option>
          <option value="Attivo">Attivo</option>
          <option value="Sospeso">Sospeso</option>
          <option value="Chiuso">Chiuso</option>
        </select>
        <select class="filter-select" id="gantt-cliente-${entity}" onchange="applyGanttFilters('${entity}')">
          <option value="">Tutti i clienti</option>
        </select>
      </div>` : ''}
      <div id="view-container-${entity}">
        <div class="table-wrap">
          <table id="table-${entity}">
            <thead><tr>
              ${cfg.columns.map(c => `
                <th ${c.mobile === false ? 'class="hide-mobile"' : ''}
                    ${c.sortable ? `onclick="sortTable('${entity}','${c.key}')" style="cursor:pointer"` : ''}>
                  ${c.label}${c.sortable ? ' <span class="sort-icon">↕</span>' : ''}
                </th>`).join('')}
              <th>Azioni</th>
            </tr></thead>
            <tbody id="tbody-${entity}"></tbody>
          </table>
        </div>
      </div>
    </div>`;

  renderTableRows(entity, items);
}

function renderTableRows(entity, items) {
  const cfg = ENTITY_CONFIG[entity];
  const tbody = document.getElementById(`tbody-${entity}`);
  if (!tbody) return;

  if (!items.length) {
    tbody.innerHTML = `<tr><td colspan="99" class="empty-state"><div class="icon">📂</div>Nessun elemento</td></tr>`;
    return;
  }

  tbody.innerHTML = items.map(item => {
    const id = item.id;
    const cells = cfg.columns.map(c => {
      const raw = c.computed ? c.computed(item) : (item[c.key] || '');
      let val = esc(raw);

      if (c.badge === 'offerta')  val = badgeStatoOfferta(raw);
      if (c.badge === 'task')     val = badgeStatoTask(raw);
      if (c.badge === 'progetto') val = badgeStatoProgetto(raw);
      if (c.badge === 'priorita') val = badgePriorita(raw);

      // Link al dettaglio dell'entità corrente
      if (c.link && raw && cfg.detailFn) {
        val = `<span class="link-cell" onclick="${cfg.detailFn}('${id}')">${esc(raw)}</span>`;
      }
      // Link progetto
      if (c.projectLink && raw) {
        const pid = item.progetto_id || '';
        val = pid
          ? `<span class="link-cell" onclick="openProgettoDetail('${pid}')">${esc(raw)}</span>`
          : `<span class="link-cell" onclick="openProgettoDetailByName('${raw.replace(/'/g,"\\'")}'">${esc(raw)}</span>`;
      }
      // Link cliente
      if (c.clienteLink && raw) {
        const cid = item.cliente_id || '';
        val = cid
          ? `<span class="link-cell" onclick="openClienteDetail('${cid}')">${esc(raw)}</span>`
          : `<span class="link-cell" onclick="openClienteDetailByName('${raw.replace(/'/g,"\\'")}'">${esc(raw)}</span>`;
      }
      // Link fornitore
      if (c.forniLink && raw) {
        const fid = item.fornitore_id || '';
        val = fid
          ? `<span class="link-cell" onclick="openFornitoreDetail('${fid}')">${esc(raw)}</span>`
          : `<span class="link-cell" onclick="openFornitoreDetailByName('${raw.replace(/'/g,"\\'")}'">${esc(raw)}</span>`;
      }

      return `<td ${c.mobile === false ? 'class="hide-mobile"' : ''}>${val}</td>`;
    }).join('');

    return `<tr>
      ${cells}
      <td class="td-actions">
        <button class="btn-icon" title="Modifica" onclick='openEditModal("${entity}","${id}")'><i data-lucide="pencil" style="width:15px;height:15px"></i></button>
        <button class="btn-icon" title="Elimina" onclick='confirmDelete("${entity}","${id}","${esc(cfg.filterKey.startsWith('_') ? cfg.columns.find(c=>c.key===cfg.filterKey)?.computed?.(item)||'' : item[cfg.filterKey] || '')}")'><i data-lucide="trash-2" style="width:15px;height:15px"></i></button>
        ${cfg.extraActions && entity === 'offerte' ? `<button class="btn-icon" title="Email" onclick='openEmailModal("${id}")'><i data-lucide="mail" style="width:15px;height:15px"></i></button>` : ''}
      </td>
    </tr>`;
  }).join('');
}

// ─── Vista switcher (Kanban / Gantt) ───────────────────────────────────────
window.switchView = function(entity, view) {
  document.querySelectorAll(`#view-toggle-${entity} .view-toggle-btn`).forEach(b => {
    b.classList.toggle('active', b.dataset.view === view);
  });
  const toolbar      = document.getElementById(`toolbar-${entity}`);
  const ganttToolbar = document.getElementById(`gantt-toolbar-${entity}`);
  if (toolbar)      toolbar.style.display      = view === 'table' ? '' : 'none';
  if (ganttToolbar) ganttToolbar.style.display  = view === 'gantt' ? '' : 'none';

  // Popola il select clienti del gantt al primo accesso
  if (view === 'gantt' && ganttToolbar) {
    const clienteSelect = document.getElementById(`gantt-cliente-${entity}`);
    if (clienteSelect && clienteSelect.options.length === 1) {
      const items = _cachedData[entity] || [];
      const clienti = [...new Set(items.map(p => p.cliente_nome).filter(Boolean))].sort();
      clienti.forEach(c => {
        const o = document.createElement('option');
        o.value = o.textContent = c;
        clienteSelect.appendChild(o);
      });
    }
  }

  const container = document.getElementById(`view-container-${entity}`);
  if (!container) return;
  const items = _cachedData[entity] || [];

  if (view === 'table') {
    container.innerHTML = `<div class="table-wrap">
      <table id="table-${entity}">
        <thead><tr>
          ${ENTITY_CONFIG[entity].columns.map(c => `
            <th ${c.mobile === false ? 'class="hide-mobile"' : ''}
                ${c.sortable ? `onclick="sortTable('${entity}','${c.key}')" style="cursor:pointer"` : ''}>
              ${c.label}${c.sortable ? ' <span class="sort-icon">↕</span>' : ''}
            </th>`).join('')}
          <th>Azioni</th>
        </tr></thead>
        <tbody id="tbody-${entity}"></tbody>
      </table></div>`;
    renderTableRows(entity, items);
  } else if (view === 'kanban') {
    renderKanbanInContainer(container, items);
  } else if (view === 'gantt') {
    renderGanttInContainer(container, items);
  }
  setTimeout(() => window._refreshIcons?.(), 50);
};

window.applyGanttFilters = function(entity) {
  const q       = (document.getElementById(`gantt-search-${entity}`)?.value || '').toLowerCase();
  const stato   = document.getElementById(`gantt-stato-${entity}`)?.value  || '';
  const cliente = document.getElementById(`gantt-cliente-${entity}`)?.value || '';
  let items     = _cachedData[entity] || [];
  if (q)       items = items.filter(p => (p.nome || '').toLowerCase().includes(q));
  if (stato)   items = items.filter(p => p.stato === stato);
  if (cliente) items = items.filter(p => p.cliente_nome === cliente);
  const container = document.getElementById(`view-container-${entity}`);
  if (container) renderGanttInContainer(container, items);
};

// ─── KANBAN VIEW ───────────────────────────────────────────────────────────
function renderKanbanInContainer(container, items) {
  const cols = [
    { stato: 'Da fare',   label: 'Da fare',   cls: 'col-da-fare' },
    { stato: 'In corso',  label: 'In corso',  cls: 'col-in-corso' },
    { stato: 'Fatto',     label: 'Fatto',     cls: 'col-fatto' },
  ];

  container.innerHTML = `
    <div class="kanban-board" id="kanban-board">
      ${cols.map(col => {
        const cards = items.filter(t => t.stato === col.stato);
        return `
          <div class="kanban-col">
            <div class="kanban-col-header ${col.cls}">
              <span class="kanban-col-title">${col.label}</span>
              <span class="kanban-col-count">${cards.length}</span>
            </div>
            <div class="kanban-col-body" data-stato="${col.stato}">
              ${cards.length ? cards.map(t => `
                <div class="kanban-card" draggable="true" data-id="${t.id}">
                  <div class="kanban-card-title" onclick="openAttivitaDetail('${t.id}')">${esc(t.titolo)}</div>
                  ${t.progetto_nome ? `<div class="kanban-card-project" onclick="openProgettoDetailByName('${t.progetto_nome.replace(/'/g,"\\'")}'">${esc(t.progetto_nome)}</div>` : ''}
                  <div class="kanban-card-meta">
                    <span class="kanban-card-date ${_isScaduta(t.scadenza) && t.stato !== 'Fatto' ? 'overdue' : ''}">${t.scadenza ? '📅 ' + esc(t.scadenza) : ''}</span>
                    ${badgePriorita(t.priorita)}
                  </div>
                  ${t.assegnato_a ? `<div class="kanban-card-assigned">👤 ${esc(t.assegnato_a)}</div>` : ''}
                </div>`).join('') : `<div class="kanban-empty">Nessuna attività</div>`}
            </div>
          </div>`;
      }).join('')}
    </div>`;

  // Drag & Drop via event delegation
  const board = container.querySelector('.kanban-board');
  let dragId = null;

  board.addEventListener('dragstart', e => {
    const card = e.target.closest('.kanban-card');
    if (!card) return;
    dragId = card.dataset.id;
    setTimeout(() => card.classList.add('dragging'), 0);
  });
  board.addEventListener('dragend', e => {
    const card = e.target.closest('.kanban-card');
    if (card) card.classList.remove('dragging');
    board.querySelectorAll('.kanban-col-body').forEach(c => c.classList.remove('drag-over'));
  });
  board.addEventListener('dragover', e => {
    e.preventDefault();
    const col = e.target.closest('.kanban-col-body');
    if (col) col.classList.add('drag-over');
  });
  board.addEventListener('dragleave', e => {
    if (!e.relatedTarget?.closest('.kanban-col-body')) {
      board.querySelectorAll('.kanban-col-body').forEach(c => c.classList.remove('drag-over'));
    }
  });
  board.addEventListener('drop', e => {
    e.preventDefault();
    const col = e.target.closest('.kanban-col-body');
    if (!col || !dragId) return;
    col.classList.remove('drag-over');
    const newStato = col.dataset.stato;
    const cached = _cachedData['attivita'] || [];
    const idx = cached.findIndex(t => t.id === dragId);
    if (idx < 0 || cached[idx].stato === newStato) { dragId = null; return; }

    // Aggiornamento ottimistico – aggiorna cache e ri-renderizza subito
    const oldStato = cached[idx].stato;
    cached[idx] = { ...cached[idx], stato: newStato };
    renderKanbanInContainer(container, cached);
    toast('Stato aggiornato', 'success');

    // Chiama API in background – ripristina se errore
    api.updateAttivita(dragId, { stato: newStato }).catch(() => {
      const i2 = cached.findIndex(t => t.id === dragId);
      if (i2 >= 0) cached[i2] = { ...cached[i2], stato: oldStato };
      renderKanbanInContainer(container, cached);
      toast('Errore – stato ripristinato', 'error');
    });
    dragId = null;
  });
}

// ─── GANTT VIEW ────────────────────────────────────────────────────────────
async function renderGanttInContainer(container, items) {
  const allAttivita = await _ensureCache('attivita');
  // Inizializza ordine se vuoto o cambiato
  if (!_ganttProjectOrder || _ganttProjectOrder.length !== items.length ||
      !items.every(p => _ganttProjectOrder.includes(p.id))) {
    _ganttProjectOrder = items.map(p => p.id);
  }
  _renderGantt(container, items, allAttivita);
}

function _renderGantt(container, items, allAttivita) {
  function pd(s) {
    if (!s) return null;
    const p = s.split('/');
    if (p.length !== 3) return null;
    return new Date(+p[2], +p[1] - 1, +p[0]);
  }
  function fmt(d) {
    if (!d) return '';
    return d.toLocaleDateString('it-IT', { day: '2-digit', month: 'short' });
  }

  const today = new Date();
  let minDate = new Date(today.getFullYear(), today.getMonth() - 1, 1);
  let maxDate = new Date(today.getFullYear(), today.getMonth() + 7, 1);

  items.forEach(p => {
    const s = pd(p.data_inizio), e = pd(p.data_fine_prevista);
    if (s && s < minDate) minDate = new Date(s.getFullYear(), s.getMonth(), 1);
    if (e && e > maxDate) maxDate = new Date(e.getFullYear(), e.getMonth() + 2, 1);
  });
  (allAttivita || []).forEach(t => {
    const s = pd(t.data_inizio) || pd(t.scadenza);
    const e = pd(t.data_fine) || pd(t.scadenza);
    if (s && s < minDate) minDate = new Date(s.getFullYear(), s.getMonth(), 1);
    if (e && e > maxDate) maxDate = new Date(e.getFullYear(), e.getMonth() + 1, 1);
  });

  const totalMs = maxDate - minDate;
  function pct(date) {
    if (!date) return null;
    return Math.max(0, Math.min(100, (date - minDate) / totalMs * 100));
  }

  const months = [];
  let cur = new Date(minDate.getFullYear(), minDate.getMonth(), 1);
  while (cur < maxDate) {
    const next = new Date(cur.getFullYear(), cur.getMonth() + 1, 1);
    const w = (Math.min(next, maxDate) - Math.max(cur, minDate)) / totalMs * 100;
    months.push({ label: cur.toLocaleDateString('it-IT', { month: 'short', year: '2-digit' }), width: w });
    cur = next;
  }

  const todayPct = pct(today);
  const bgCols = months.map(m => `<div class="gantt-bg-col" style="width:${m.width}%"></div>`).join('');
  const todayLine = todayPct !== null ? `<div class="gantt-today-line" style="left:${todayPct}%"></div>` : '';

  // Ordine manuale
  const order = _ganttProjectOrder || items.map(p => p.id);
  const orderedItems = order.map(id => items.find(p => p.id === id)).filter(Boolean);
  items.forEach(p => { if (!order.includes(p.id)) orderedItems.push(p); });

  const rowsHtml = orderedItems.map(p => {
    const s = pd(p.data_inizio), e = pd(p.data_fine_prevista);
    const left  = s ? pct(s) : 0;
    const right = e ? pct(e) : (s ? pct(new Date(s.getTime() + 30*86400000)) : 10);
    const width = Math.max(right - left, 1);
    const cls   = (p.stato || '').toLowerCase().replace(' ', '-') || 'attivo';

    const projAtt = (allAttivita || []).filter(t =>
      t.progetto_id === p.id || t.progetto_nome === p.nome
    );

    const attRowsHtml = projAtt.map(t => {
      const tS = pd(t.data_inizio) || pd(t.scadenza);
      const tE = pd(t.data_fine) || pd(t.scadenza);
      const isRange = tS && tE && (tE - tS) >= 86400000;
      const mCls = t.stato === 'Fatto' ? '#2D7D52' : t.stato === 'In corso' ? '#2060A8' : '#9C8E85';

      let barHtml = '';
      if (isRange) {
        const aL = pct(tS), aR = pct(tE);
        const aW = Math.max(aR - aL, 0.5);
        barHtml = `<div class="gantt-att-bar" style="left:${aL}%;width:${aW}%;background:${mCls}"
                       title="${esc(t.titolo)} | ${fmt(tS)} → ${fmt(tE)} | ${esc(t.stato)}"
                       onclick="openAttivitaDetail('${t.id}')"></div>`;
      } else if (tS) {
        const lp = pct(tS);
        barHtml = `<div class="gantt-att-marker" style="left:${lp}%;background:${mCls};top:10px"
                       title="${esc(t.titolo)} | ${fmt(tS)} | ${esc(t.stato)}"
                       onclick="openAttivitaDetail('${t.id}')"></div>`;
      }

      return `<div class="gantt-row gantt-att-row">
          <div class="gantt-label gantt-att-label" title="${esc(t.titolo)}">
            <span class="gantt-att-indent">└</span>
            <span class="gantt-att-name link-cell" onclick="openAttivitaDetail('${t.id}')">${esc(t.titolo)}</span>
          </div>
          <div class="gantt-timeline">
            <div class="gantt-bg-cols">${bgCols}</div>
            ${todayLine}${barHtml}
          </div>
        </div>`;
    }).join('');

    return `<div class="gantt-proj-group" data-project-id="${p.id}" draggable="true">
        <div class="gantt-row gantt-proj-row">
          <div class="gantt-label gantt-proj-label">
            <span class="gantt-drag-handle" title="Trascina per riordinare">⠿</span>
            <span class="link-cell" onclick="openProgettoDetail('${p.id}')" title="${esc(p.nome)}">${esc(p.nome)}</span>
          </div>
          <div class="gantt-timeline">
            <div class="gantt-bg-cols">${bgCols}</div>
            ${todayLine}
            ${(s || e) ? `<div class="gantt-bar ${cls}" style="left:${left}%;width:${width}%"
                 onclick="openProgettoDetail('${p.id}')"
                 title="${esc(p.nome)} | ${fmt(s)} → ${fmt(e)}">
                 ${width > 8 ? esc(p.nome.substring(0,18)) : ''}
               </div>` : `<div style="position:absolute;left:0;font-size:11px;color:var(--text3);padding-left:4px">—</div>`}
          </div>
        </div>
        ${attRowsHtml}
      </div>`;
  }).join('');

  container.innerHTML = `
    <div class="gantt-wrapper">
      <div class="gantt-header">
        <div class="gantt-label gantt-header-label"></div>
        <div class="gantt-header-months">
          ${months.map(m => `<div class="gantt-month" style="width:${m.width}%">${m.label}</div>`).join('')}
        </div>
      </div>
      <div class="gantt-rows" id="gantt-rows-container">${rowsHtml}</div>
      <div class="gantt-legend">
        <span><div class="gantt-legend-today"></div> Oggi</span>
        <span><div class="gantt-legend-bar attivo"></div> Attivo</span>
        <span><div class="gantt-legend-bar sospeso"></div> Sospeso</span>
        <span><div class="gantt-legend-bar chiuso"></div> Chiuso</span>
        <span><div class="gantt-legend-dot" style="background:#9C8E85"></div> Da fare</span>
        <span><div class="gantt-legend-dot" style="background:#2060A8"></div> In corso</span>
        <span><div class="gantt-legend-dot" style="background:#2D7D52"></div> Fatto</span>
      </div>
    </div>`;

  // ─── Drag & Drop riordino manuale ───────────────────────────────────────
  let dragSrc = null;
  const rowsEl = document.getElementById('gantt-rows-container');
  rowsEl.querySelectorAll('.gantt-proj-group').forEach(grp => {
    grp.addEventListener('dragstart', e => {
      dragSrc = grp;
      setTimeout(() => grp.style.opacity = '0.45', 0);
      e.dataTransfer.effectAllowed = 'move';
    });
    grp.addEventListener('dragend', () => {
      grp.style.opacity = '';
      rowsEl.querySelectorAll('.gantt-proj-group').forEach(g => g.classList.remove('gantt-drag-over'));
    });
    grp.addEventListener('dragover', e => {
      e.preventDefault();
      if (grp !== dragSrc) {
        rowsEl.querySelectorAll('.gantt-proj-group').forEach(g => g.classList.remove('gantt-drag-over'));
        grp.classList.add('gantt-drag-over');
      }
    });
    grp.addEventListener('drop', e => {
      e.preventDefault();
      if (dragSrc && dragSrc !== grp) {
        const all = Array.from(rowsEl.querySelectorAll('.gantt-proj-group'));
        if (all.indexOf(dragSrc) < all.indexOf(grp)) grp.after(dragSrc);
        else grp.before(dragSrc);
        _ganttProjectOrder = Array.from(rowsEl.querySelectorAll('.gantt-proj-group')).map(g => g.dataset.projectId);
      }
      rowsEl.querySelectorAll('.gantt-proj-group').forEach(g => g.classList.remove('gantt-drag-over'));
    });
  });
}

// ─── DETTAGLIO PROGETTO ────────────────────────────────────────────────────
window.openProgettoDetail = async function(progettoId) {
  const items = await _ensureCache('progetti');
  const p = items.find(x => x.id === progettoId);
  if (!p) { toast('Progetto non trovato', 'error'); return; }
  await _renderProgettoDetail(p);
};
window.openProgettoDetailByName = async function(nome) {
  const items = await _ensureCache('progetti');
  const p = items.find(x => x.nome === nome);
  if (!p) { toast('Progetto non trovato', 'error'); return; }
  await _renderProgettoDetail(p);
};

async function _renderProgettoDetail(progetto) {
  const content = document.getElementById('content');
  content.innerHTML = `<div class="loader"><div class="spinner"></div> Caricamento…</div>`;

  const [offerte, attivita, clienti, fornitori] = await Promise.all([
    _ensureCache('offerte'), _ensureCache('attivita'),
    _ensureCache('clienti'), _ensureCache('fornitori'),
  ]);

  const projOfferte  = offerte.filter(o => o.progetto_id === progetto.id || o.progetto_nome === progetto.nome);
  const projAttivita = attivita.filter(t => t.progetto_id === progetto.id || t.progetto_nome === progetto.nome);

  const forniIdSet   = new Set(projOfferte.map(o => o.fornitore_id).filter(Boolean));
  const forniNomiSet = new Set(projOfferte.map(o => o.fornitore_nome).filter(Boolean));
  const projFornitori = fornitori.filter(f => forniIdSet.has(f.id) || (!forniIdSet.has(f.id) && forniNomiSet.has(f.ragione_sociale)));

  const cliente = clienti.find(c => c.id === progetto.cliente_id || c.ragione_sociale === progetto.cliente_nome);

  const taskFatti  = projAttivita.filter(t => t.stato === 'Fatto').length;
  const taskTotali = projAttivita.length;
  const offerteAgg = projOfferte.filter(o => o.stato === 'Aggiudicata').length;
  const importoTot = projOfferte
    .filter(o => o.stato === 'Aggiudicata' && o.importo)
    .reduce((s, o) => s + (parseFloat(String(o.importo).replace(/[^\d.]/g, '')) || 0), 0);

  _setNav('progetti', progetto.nome);
  content.innerHTML = `
    <div class="breadcrumb">
      <span class="breadcrumb-link" onclick="navigateTo('progetti')">Progetti</span>
      <span class="breadcrumb-sep">›</span>
      <span class="breadcrumb-current">${esc(progetto.nome)}</span>
    </div>

    <div class="detail-header">
      <div class="detail-header-top">
        <div class="detail-header-body">
          <div class="detail-header-title">
            <h2>${esc(progetto.nome)}</h2>
            ${badgeStatoProgetto(progetto.stato)}
          </div>
          <div class="detail-meta-row" style="margin-top:8px">
            ${progetto.data_inizio ? `<span class="detail-meta-item">📅 Inizio: <strong>${esc(progetto.data_inizio)}</strong></span>` : ''}
            ${progetto.data_fine_prevista ? `<span class="detail-meta-item">🏁 Scadenza: <strong>${esc(progetto.data_fine_prevista)}</strong></span>` : ''}
          </div>
          ${progetto.note ? `<p class="project-note">${esc(progetto.note)}</p>` : ''}
        </div>
        <div class="detail-actions">
          <button class="btn btn-ghost btn-sm" onclick='openEditModal("progetti","${progetto.id}")'>✏️ Modifica</button>
        </div>
      </div>
    </div>

    <div class="project-kpi-row">
      <div class="proj-kpi"><span class="proj-kpi-val">${taskTotali}</span><span class="proj-kpi-lbl">Attività</span></div>
      <div class="proj-kpi success"><span class="proj-kpi-val">${taskFatti}</span><span class="proj-kpi-lbl">Completate</span></div>
      <div class="proj-kpi info"><span class="proj-kpi-val">${projOfferte.length}</span><span class="proj-kpi-lbl">Offerte</span></div>
      <div class="proj-kpi warning"><span class="proj-kpi-val">${offerteAgg}</span><span class="proj-kpi-lbl">Aggiudicate</span></div>
      ${importoTot > 0 ? `<div class="proj-kpi accent"><span class="proj-kpi-val">€ ${importoTot.toLocaleString('it-IT')}</span><span class="proj-kpi-lbl">Valore</span></div>` : ''}
    </div>

    <div class="detail-grid-2">
      <div class="section">
        <div class="section-header"><span class="section-title">👤 Cliente</span></div>
        ${cliente ? `
          <div class="entity-card clickable" onclick="openClienteDetail('${cliente.id}')">
            <div class="entity-card-name">${esc(cliente.ragione_sociale)}</div>
            ${cliente.referente ? `<div class="entity-card-sub">👤 ${esc(cliente.referente)}</div>` : ''}
            ${cliente.email    ? `<div class="entity-card-sub">✉️ <a href="mailto:${esc(cliente.email)}">${esc(cliente.email)}</a></div>` : ''}
            ${cliente.telefono ? `<div class="entity-card-sub">📞 ${esc(cliente.telefono)}</div>` : ''}
            ${cliente.note     ? `<div class="entity-card-note">${esc(cliente.note)}</div>` : ''}
          </div>` : `<div class="empty-state" style="padding:20px">Nessun cliente collegato</div>`}
      </div>

      <div class="section">
        <div class="section-header"><span class="section-title"><i data-lucide="truck" style="width:16px;height:16px;display:inline;vertical-align:-2px"></i> Fornitori</span><span class="section-count">${projFornitori.length}</span></div>
        ${projFornitori.length ? projFornitori.map(f => `
          <div class="entity-card-inline clickable" onclick="openFornitoreDetail('${f.id}')">
            <div class="entity-card-name">${esc(f.ragione_sociale)}</div>
            <div class="entity-card-row">
              <span class="badge badge-${f.tipo === 'Elettrico' ? 'inviata' : f.tipo === 'Software' ? 'in-valutazione' : 'da-fare'}" style="font-size:10px">${esc(f.tipo || '')}</span>
              ${f.referente ? `<span class="entity-card-sub">${esc(f.referente)}</span>` : ''}
            </div>
            ${f.email ? `<div class="entity-card-sub" style="font-size:12px">✉️ <a href="mailto:${esc(f.email)}">${esc(f.email)}</a></div>` : ''}
          </div>`).join('') : `<div class="empty-state" style="padding:20px">Nessun fornitore</div>`}
      </div>
    </div>

    <div class="section">
      <div class="section-header">
        <span class="section-title"><i data-lucide="file-text" style="width:16px;height:16px;display:inline;vertical-align:-2px"></i> Offerte / Preventivi</span>
        <div style="display:flex;gap:8px;align-items:center">
          <span class="section-count">${projOfferte.length}</span>
          <button class="btn btn-primary btn-sm" onclick="openCreateModalPrefilled('offerte','${esc(progetto.id)}','${esc(progetto.nome)}')">+ Nuova</button>
        </div>
      </div>
      ${projOfferte.length ? `<div class="table-wrap"><table>
        <thead><tr><th>Fornitore</th><th>Tipo</th><th>Stato</th><th class="hide-mobile">Scadenza</th><th class="hide-mobile">Importo</th><th class="hide-mobile">Priorità</th><th>Azioni</th></tr></thead>
        <tbody>${projOfferte.map(o => `<tr>
          <td><span class="link-cell" onclick="openFornitoreDetailByName('${o.fornitore_nome.replace(/'/g,"\\'")}'">${esc(o.fornitore_nome)}</span>${o.descrizione ? `<div style="font-size:11px;color:var(--text2);margin-top:1px">${esc(o.descrizione.substring(0,50))}${o.descrizione.length>50?'…':''}</div>` : ''}</td>
          <td>${esc(o.tipo || '')}</td>
          <td>${badgeStatoOfferta(o.stato)}</td>
          <td class="hide-mobile">${o.scadenza_attesa ? `<span style="${_isScaduta(o.scadenza_attesa) && o.stato==='Inviata' ? 'color:var(--danger);font-weight:600' : ''}">${esc(o.scadenza_attesa)}</span>` : '—'}</td>
          <td class="hide-mobile">${o.importo ? `<strong>${esc(o.importo)} €</strong>` : '—'}</td>
          <td class="hide-mobile">${badgePriorita(o.priorita)}</td>
          <td class="td-actions">
            <button class="btn-icon" onclick='openEditModal("offerte","${o.id}")'>✏️</button>
            <button class="btn-icon" onclick='openEmailModal("${o.id}")'>📧</button>
            <button class="btn-icon" onclick='confirmDelete("offerte","${o.id}","offerta")'>🗑️</button>
          </td>
        </tr>`).join('')}</tbody></table></div>` : `<div class="empty-state">Nessuna offerta per questo progetto</div>`}
    </div>

    <div class="section">
      <div class="section-header">
        <span class="section-title"><i data-lucide="check-square" style="width:16px;height:16px;display:inline;vertical-align:-2px"></i> Attività</span>
        <div style="display:flex;gap:8px;align-items:center">
          <div class="progress-mini-wrap"><div class="progress-mini-bar" style="width:${taskTotali ? Math.round(taskFatti/taskTotali*100) : 0}%"></div></div>
          <span class="section-count">${taskFatti}/${taskTotali}</span>
          <button class="btn btn-primary btn-sm" onclick="openCreateModalPrefilled('attivita','${esc(progetto.id)}','${esc(progetto.nome)}')">+ Nuova</button>
        </div>
      </div>
      ${projAttivita.length ? `<div class="table-wrap"><table>
        <thead><tr><th>Titolo</th><th class="hide-mobile">Assegnato</th><th>Scadenza</th><th>Stato</th><th class="hide-mobile">Priorità</th><th>Azioni</th></tr></thead>
        <tbody>${projAttivita.map(t => `<tr style="${t.stato==='Fatto' ? 'opacity:.6' : ''}">
          <td><span class="link-cell" onclick="openAttivitaDetail('${t.id}')">${esc(t.titolo)}</span></td>
          <td class="hide-mobile">${esc(t.assegnato_a || '—')}</td>
          <td>${esc(t.scadenza || '—')}</td>
          <td>${badgeStatoTask(t.stato)}</td>
          <td class="hide-mobile">${badgePriorita(t.priorita)}</td>
          <td class="td-actions">
            <button class="btn-icon" onclick='openEditModal("attivita","${t.id}")'>✏️</button>
            <button class="btn-icon" onclick='confirmDelete("attivita","${t.id}","${esc(t.titolo)}")'>🗑️</button>
          </td>
        </tr>`).join('')}</tbody></table></div>` : `<div class="empty-state">Nessuna attività per questo progetto</div>`}
    </div>`;
  setTimeout(() => window._refreshIcons?.(), 50);
}

// ─── DETTAGLIO CLIENTE ─────────────────────────────────────────────────────
window.openClienteDetail = async function(id) {
  const items = await _ensureCache('clienti');
  const c = items.find(x => x.id === id);
  if (!c) { toast('Cliente non trovato', 'error'); return; }
  await _renderClienteDetail(c);
};
window.openClienteDetailByName = async function(nome) {
  const items = await _ensureCache('clienti');
  const c = items.find(x => x.ragione_sociale === nome);
  if (!c) { toast('Cliente non trovato', 'error'); return; }
  await _renderClienteDetail(c);
};

async function _renderClienteDetail(cliente) {
  const content = document.getElementById('content');
  content.innerHTML = `<div class="loader"><div class="spinner"></div> Caricamento…</div>`;

  const [progetti, offerte, contatti] = await Promise.all([
    _ensureCache('progetti'), _ensureCache('offerte'),
    api.getContattiByCliente(cliente.id).catch(() => []),
  ]);
  // Merge contatti nel cache globale per editing
  if (!_cachedData['contatti']) _cachedData['contatti'] = [];
  contatti.forEach(c => {
    const idx = _cachedData['contatti'].findIndex(x => x.id === c.id);
    if (idx >= 0) _cachedData['contatti'][idx] = c; else _cachedData['contatti'].push(c);
  });

  const clienteProgetti = progetti.filter(p => p.cliente_id === cliente.id || p.cliente_nome === cliente.ragione_sociale);
  const clienteOfferte  = offerte.filter(o =>
    clienteProgetti.some(p => p.id === o.progetto_id || p.nome === o.progetto_nome)
  );
  const valoreAgg = clienteOfferte
    .filter(o => o.stato === 'Aggiudicata' && o.importo)
    .reduce((s, o) => s + (parseFloat(String(o.importo).replace(/[^\d.]/g, '')) || 0), 0);

  _setNav('clienti', cliente.ragione_sociale);
  content.innerHTML = `
    <div class="breadcrumb">
      <span class="breadcrumb-link" onclick="navigateTo('clienti')">Clienti</span>
      <span class="breadcrumb-sep">›</span>
      <span class="breadcrumb-current">${esc(cliente.ragione_sociale)}</span>
    </div>

    <div class="detail-header">
      <div class="detail-header-top">
        <div class="detail-header-body">
          <div class="detail-header-title">
            <h2>${esc(cliente.ragione_sociale)}</h2>
          </div>
          <div class="detail-meta-row" style="margin-top:8px">
            ${cliente.referente ? `<span class="detail-meta-item">👤 ${esc(cliente.referente)}</span>` : ''}
            ${cliente.email ? `<span class="detail-meta-item">✉️ <a href="mailto:${esc(cliente.email)}" style="color:var(--accent)">${esc(cliente.email)}</a></span>` : ''}
            ${cliente.telefono ? `<span class="detail-meta-item">📞 ${esc(cliente.telefono)}</span>` : ''}
          </div>
          ${cliente.note ? `<p class="project-note">${esc(cliente.note)}</p>` : ''}
        </div>
        <div class="detail-actions">
          <button class="btn btn-ghost btn-sm" onclick='openEditModal("clienti","${cliente.id}")'>✏️ Modifica</button>
        </div>
      </div>
    </div>

    <div class="project-kpi-row">
      <div class="proj-kpi"><span class="proj-kpi-val">${clienteProgetti.length}</span><span class="proj-kpi-lbl">Progetti</span></div>
      <div class="proj-kpi success"><span class="proj-kpi-val">${clienteProgetti.filter(p=>p.stato==='Attivo').length}</span><span class="proj-kpi-lbl">Attivi</span></div>
      <div class="proj-kpi info"><span class="proj-kpi-val">${clienteOfferte.length}</span><span class="proj-kpi-lbl">Offerte totali</span></div>
      ${valoreAgg > 0 ? `<div class="proj-kpi accent"><span class="proj-kpi-val">€ ${valoreAgg.toLocaleString('it-IT')}</span><span class="proj-kpi-lbl">Valore agg.</span></div>` : ''}
    </div>

    <div class="section">
      <div class="section-header">
        <span class="section-title"><i data-lucide="folder-kanban" style="width:16px;height:16px;display:inline;vertical-align:-2px"></i> Progetti</span>
        <span class="section-count">${clienteProgetti.length}</span>
      </div>
      ${clienteProgetti.length ? `
        <div class="proj-cards-grid">
          ${clienteProgetti.map(p => `
            <div class="proj-list-card" onclick="openProgettoDetail('${p.id}')">
              <div style="display:flex;align-items:center;justify-content:space-between;gap:10px">
                <span class="proj-list-card-name">${esc(p.nome)}</span>
                ${badgeStatoProgetto(p.stato)}
              </div>
              ${p.data_fine_prevista ? `<div style="font-size:12px;color:var(--text2);margin-top:4px">🏁 ${esc(p.data_fine_prevista)}</div>` : ''}
              ${p.note ? `<div style="font-size:12px;color:var(--text3);margin-top:4px;font-style:italic">${esc(p.note.substring(0,60))}${p.note.length>60?'…':''}</div>` : ''}
            </div>`).join('')}
        </div>` : `<div class="empty-state">Nessun progetto per questo cliente</div>`}
    </div>

    <div class="section" id="section-contatti-${cliente.id}">
      <div class="section-header">
        <span class="section-title"><i data-lucide="users" style="width:16px;height:16px;display:inline;vertical-align:-2px"></i> Contatti</span>
        <div style="display:flex;gap:8px;align-items:center">
          <span class="section-count" id="contatti-count">${contatti.length}</span>
          <button class="btn btn-primary btn-sm" onclick="openContattoModal(null,'${cliente.id}','${esc(cliente.ragione_sociale)}')">+ Aggiungi</button>
        </div>
      </div>
      <div id="contatti-list-${cliente.id}">
        ${_renderContattiList(contatti, cliente.id)}
      </div>
    </div>`;
  setTimeout(() => window._refreshIcons?.(), 50);
}

// ─── DETTAGLIO FORNITORE ───────────────────────────────────────────────────
window.openFornitoreDetail = async function(id) {
  const items = await _ensureCache('fornitori');
  const f = items.find(x => x.id === id);
  if (!f) { toast('Fornitore non trovato', 'error'); return; }
  await _renderFornitoreDetail(f);
};
window.openFornitoreDetailByName = async function(nome) {
  const items = await _ensureCache('fornitori');
  const f = items.find(x => x.ragione_sociale === nome);
  if (!f) { toast('Fornitore non trovato', 'error'); return; }
  await _renderFornitoreDetail(f);
};

async function _renderFornitoreDetail(fornitore) {
  const content = document.getElementById('content');
  content.innerHTML = `<div class="loader"><div class="spinner"></div> Caricamento…</div>`;

  const [offerte, progetti] = await Promise.all([
    _ensureCache('offerte'), _ensureCache('progetti'),
  ]);

  const forniOfferte = offerte.filter(o => o.fornitore_id === fornitore.id || o.fornitore_nome === fornitore.ragione_sociale);
  const progettIdSet = new Set(forniOfferte.map(o => o.progetto_id).filter(Boolean));
  const progettNomiSet = new Set(forniOfferte.map(o => o.progetto_nome).filter(Boolean));
  const forniProgetti = progetti.filter(p => progettIdSet.has(p.id) || (!progettIdSet.has(p.id) && progettNomiSet.has(p.nome)));

  const importoTot = forniOfferte
    .filter(o => o.stato === 'Aggiudicata' && o.importo)
    .reduce((s, o) => s + (parseFloat(String(o.importo).replace(/[^\d.]/g, '')) || 0), 0);

  _setNav('fornitori', fornitore.ragione_sociale);
  const tipoCls = fornitore.tipo === 'Elettrico' ? 'inviata' : fornitore.tipo === 'Software' ? 'in-valutazione' : 'da-fare';

  content.innerHTML = `
    <div class="breadcrumb">
      <span class="breadcrumb-link" onclick="navigateTo('fornitori')">Fornitori</span>
      <span class="breadcrumb-sep">›</span>
      <span class="breadcrumb-current">${esc(fornitore.ragione_sociale)}</span>
    </div>

    <div class="detail-header">
      <div class="detail-header-top">
        <div class="detail-header-body">
          <div class="detail-header-title">
            <h2>${esc(fornitore.ragione_sociale)}</h2>
            ${fornitore.tipo ? `<span class="badge badge-${tipoCls}">${esc(fornitore.tipo)}</span>` : ''}
          </div>
          <div class="detail-meta-row" style="margin-top:8px">
            ${fornitore.referente ? `<span class="detail-meta-item">👤 ${esc(fornitore.referente)}</span>` : ''}
            ${fornitore.email ? `<span class="detail-meta-item">✉️ <a href="mailto:${esc(fornitore.email)}" style="color:var(--accent)">${esc(fornitore.email)}</a></span>` : ''}
            ${fornitore.telefono ? `<span class="detail-meta-item">📞 ${esc(fornitore.telefono)}</span>` : ''}
          </div>
          ${fornitore.note ? `<p class="project-note">${esc(fornitore.note)}</p>` : ''}
        </div>
        <div class="detail-actions">
          <button class="btn btn-ghost btn-sm" onclick='openEditModal("fornitori","${fornitore.id}")'>✏️ Modifica</button>
        </div>
      </div>
    </div>

    <div class="project-kpi-row">
      <div class="proj-kpi"><span class="proj-kpi-val">${forniOfferte.length}</span><span class="proj-kpi-lbl">Offerte</span></div>
      <div class="proj-kpi success"><span class="proj-kpi-val">${forniOfferte.filter(o=>o.stato==='Aggiudicata').length}</span><span class="proj-kpi-lbl">Aggiudicate</span></div>
      <div class="proj-kpi info"><span class="proj-kpi-val">${forniProgetti.length}</span><span class="proj-kpi-lbl">Progetti</span></div>
      ${importoTot > 0 ? `<div class="proj-kpi accent"><span class="proj-kpi-val">€ ${importoTot.toLocaleString('it-IT')}</span><span class="proj-kpi-lbl">Valore agg.</span></div>` : ''}
    </div>

    <div class="section">
      <div class="section-header">
        <span class="section-title"><i data-lucide="file-text" style="width:16px;height:16px;display:inline;vertical-align:-2px"></i> Offerte</span>
        <span class="section-count">${forniOfferte.length}</span>
      </div>
      ${forniOfferte.length ? `<div class="table-wrap"><table>
        <thead><tr><th>Progetto</th><th>Tipo</th><th>Stato</th><th class="hide-mobile">Scadenza</th><th class="hide-mobile">Importo</th><th>Azioni</th></tr></thead>
        <tbody>${forniOfferte.map(o => `<tr>
          <td><span class="link-cell" onclick="openProgettoDetailByName('${o.progetto_nome.replace(/'/g,"\\'")}'">${esc(o.progetto_nome)}</span></td>
          <td>${esc(o.tipo || '')}</td>
          <td>${badgeStatoOfferta(o.stato)}</td>
          <td class="hide-mobile">${esc(o.scadenza_attesa || '—')}</td>
          <td class="hide-mobile">${o.importo ? `<strong>${esc(o.importo)} €</strong>` : '—'}</td>
          <td class="td-actions">
            <button class="btn-icon" onclick='openEditModal("offerte","${o.id}")'>✏️</button>
            <button class="btn-icon" onclick='openEmailModal("${o.id}")'>📧</button>
          </td>
        </tr>`).join('')}</tbody></table></div>` : `<div class="empty-state">Nessuna offerta</div>`}
    </div>

    ${forniProgetti.length ? `
    <div class="section">
      <div class="section-header"><span class="section-title"><i data-lucide="folder-kanban" style="width:16px;height:16px;display:inline;vertical-align:-2px"></i> Progetti coinvolti</span><span class="section-count">${forniProgetti.length}</span></div>
      <div class="proj-cards-grid">
        ${forniProgetti.map(p => `
          <div class="proj-list-card" onclick="openProgettoDetail('${p.id}')">
            <div style="display:flex;align-items:center;justify-content:space-between;gap:10px">
              <span class="proj-list-card-name">${esc(p.nome)}</span>
              ${badgeStatoProgetto(p.stato)}
            </div>
            ${p.cliente_nome ? `<div style="font-size:12px;color:var(--text2);margin-top:4px">👤 ${esc(p.cliente_nome)}</div>` : ''}
          </div>`).join('')}
      </div>
    </div>` : ''}`;
  setTimeout(() => window._refreshIcons?.(), 50);
}

// ─── DETTAGLIO OFFERTA ─────────────────────────────────────────────────────
window.openOffertaDetail = async function(id) {
  const items = await _ensureCache('offerte');
  const o = items.find(x => x.id === id);
  if (!o) { toast('Offerta non trovata', 'error'); return; }
  await _renderOffertaDetail(o);
};

async function _renderOffertaDetail(offerta) {
  const content = document.getElementById('content');
  content.innerHTML = `<div class="loader"><div class="spinner"></div> Caricamento…</div>`;

  const [progetti, fornitori] = await Promise.all([
    _ensureCache('progetti'), _ensureCache('fornitori'),
  ]);
  const progetto  = progetti.find(p => p.id === offerta.progetto_id || p.nome === offerta.progetto_nome);
  const fornitore = fornitori.find(f => f.id === offerta.fornitore_id || f.ragione_sociale === offerta.fornitore_nome);

  _setNav('offerte', `Offerta – ${offerta.progetto_nome || ''}`);
  content.innerHTML = `
    <div class="breadcrumb">
      <span class="breadcrumb-link" onclick="navigateTo('offerte')">Offerte</span>
      <span class="breadcrumb-sep">›</span>
      ${progetto ? `<span class="breadcrumb-link" onclick="openProgettoDetail('${progetto.id}')">${esc(progetto.nome)}</span><span class="breadcrumb-sep">›</span>` : ''}
      <span class="breadcrumb-current">${esc(offerta.tipo || 'Offerta')}</span>
    </div>

    <div class="detail-header">
      <div class="detail-header-top">
        <div class="detail-header-body">
          <div class="detail-header-title">
            <h2>${esc(offerta.fornitore_nome || 'Offerta')}</h2>
            ${badgeStatoOfferta(offerta.stato)}
            ${badgePriorita(offerta.priorita)}
          </div>
          <div class="detail-meta-row" style="margin-top:8px">
            ${offerta.tipo ? `<span class="detail-meta-item">🏷 ${esc(offerta.tipo)}</span>` : ''}
            ${offerta.data_invio_richiesta ? `<span class="detail-meta-item">📤 Inviata: <strong>${esc(offerta.data_invio_richiesta)}</strong></span>` : ''}
            ${offerta.scadenza_attesa ? `<span class="detail-meta-item" style="${_isScaduta(offerta.scadenza_attesa) ? 'color:var(--danger)' : ''}">⏳ Scadenza: <strong>${esc(offerta.scadenza_attesa)}</strong></span>` : ''}
            ${offerta.data_ricezione ? `<span class="detail-meta-item">📥 Ricevuta: <strong>${esc(offerta.data_ricezione)}</strong></span>` : ''}
            ${offerta.importo ? `<span class="detail-meta-item" style="font-size:16px;font-weight:800;color:var(--success)">€ ${esc(offerta.importo)}</span>` : ''}
          </div>
          ${offerta.descrizione ? `<p class="project-note">${esc(offerta.descrizione)}</p>` : ''}
        </div>
        <div class="detail-actions">
          <button class="btn btn-ghost btn-sm" onclick='openEmailModal("${offerta.id}")'>📧 Email</button>
          <button class="btn btn-ghost btn-sm" onclick='openEditModal("offerte","${offerta.id}")'>✏️ Modifica</button>
        </div>
      </div>
    </div>

    <div class="detail-grid-2">
      <div class="section">
        <div class="section-header"><span class="section-title"><i data-lucide="folder-kanban" style="width:16px;height:16px;display:inline;vertical-align:-2px"></i> Progetto</span></div>
        ${progetto ? `
          <div class="entity-card clickable" onclick="openProgettoDetail('${progetto.id}')">
            <div class="entity-card-name">${esc(progetto.nome)}</div>
            <div class="entity-card-row" style="margin-top:4px">${badgeStatoProgetto(progetto.stato)}</div>
            ${progetto.data_fine_prevista ? `<div class="entity-card-sub">🏁 ${esc(progetto.data_fine_prevista)}</div>` : ''}
            ${progetto.cliente_nome ? `<div class="entity-card-sub">👤 ${esc(progetto.cliente_nome)}</div>` : ''}
          </div>` : `<div class="empty-state" style="padding:20px">Nessun progetto collegato</div>`}
      </div>

      <div class="section">
        <div class="section-header"><span class="section-title"><i data-lucide="truck" style="width:16px;height:16px;display:inline;vertical-align:-2px"></i> Fornitore</span></div>
        ${fornitore ? `
          <div class="entity-card clickable" onclick="openFornitoreDetail('${fornitore.id}')">
            <div class="entity-card-name">${esc(fornitore.ragione_sociale)}</div>
            ${fornitore.tipo ? `<div class="entity-card-row" style="margin-top:4px"><span class="badge badge-${fornitore.tipo==='Elettrico'?'inviata':'in-valutazione'}" style="font-size:10px">${esc(fornitore.tipo)}</span></div>` : ''}
            ${fornitore.referente ? `<div class="entity-card-sub">👤 ${esc(fornitore.referente)}</div>` : ''}
            ${fornitore.email ? `<div class="entity-card-sub">✉️ <a href="mailto:${esc(fornitore.email)}">${esc(fornitore.email)}</a></div>` : ''}
          </div>` : `<div class="empty-state" style="padding:20px">Nessun fornitore collegato</div>`}
      </div>
    </div>`;
  setTimeout(() => window._refreshIcons?.(), 50);
}

// ─── DETTAGLIO ATTIVITÀ ────────────────────────────────────────────────────
window.openAttivitaDetail = async function(id) {
  const items = await _ensureCache('attivita');
  const t = items.find(x => x.id === id);
  if (!t) { toast('Attività non trovata', 'error'); return; }
  await _renderAttivitaDetail(t);
};

async function _renderAttivitaDetail(task) {
  const content = document.getElementById('content');
  content.innerHTML = `<div class="loader"><div class="spinner"></div> Caricamento…</div>`;

  const progetti = await _ensureCache('progetti');
  const progetto = progetti.find(p => p.id === task.progetto_id || p.nome === task.progetto_nome);

  _setNav('attivita', task.titolo);
  const stati = ['Da fare', 'In corso', 'Fatto'];

  content.innerHTML = `
    <div class="breadcrumb">
      <span class="breadcrumb-link" onclick="navigateTo('attivita')">Attività</span>
      <span class="breadcrumb-sep">›</span>
      ${progetto ? `<span class="breadcrumb-link" onclick="openProgettoDetail('${progetto.id}')">${esc(progetto.nome)}</span><span class="breadcrumb-sep">›</span>` : ''}
      <span class="breadcrumb-current">${esc(task.titolo)}</span>
    </div>

    <div class="detail-header">
      <div class="detail-header-top">
        <div class="detail-header-body">
          <div class="detail-header-title">
            <h2>${esc(task.titolo)}</h2>
            ${badgeStatoTask(task.stato)}
            ${badgePriorita(task.priorita)}
          </div>
          <div class="detail-meta-row" style="margin-top:8px">
            ${task.scadenza ? `<span class="detail-meta-item" style="${_isScaduta(task.scadenza) && task.stato!=='Fatto' ? 'color:var(--danger);font-weight:600' : ''}">📅 Scadenza: <strong>${esc(task.scadenza)}</strong></span>` : ''}
            ${task.assegnato_a ? `<span class="detail-meta-item">👤 ${esc(task.assegnato_a)}</span>` : ''}
          </div>
          <div class="status-btn-row" style="margin-top:12px">
            ${stati.map(s => `<button class="status-btn ${task.stato === s ? 'active' : ''}" onclick="changeTaskStato('${task.id}','${s}')">${s}</button>`).join('')}
          </div>
          ${task.note ? `<p class="project-note" style="margin-top:12px">${esc(task.note)}</p>` : ''}
        </div>
        <div class="detail-actions">
          <button class="btn btn-ghost btn-sm" onclick='openEditModal("attivita","${task.id}")'>✏️ Modifica</button>
        </div>
      </div>
    </div>

    ${progetto ? `
    <div class="section">
      <div class="section-header"><span class="section-title"><i data-lucide="folder-kanban" style="width:16px;height:16px;display:inline;vertical-align:-2px"></i> Progetto collegato</span></div>
      <div class="entity-card clickable" onclick="openProgettoDetail('${progetto.id}')">
        <div class="entity-card-name">${esc(progetto.nome)}</div>
        <div class="entity-card-row" style="margin-top:4px">${badgeStatoProgetto(progetto.stato)}</div>
        ${progetto.data_fine_prevista ? `<div class="entity-card-sub">🏁 ${esc(progetto.data_fine_prevista)}</div>` : ''}
        ${progetto.cliente_nome ? `<div class="entity-card-sub">👤 ${esc(progetto.cliente_nome)}</div>` : ''}
      </div>
    </div>` : ''}`;
  setTimeout(() => window._refreshIcons?.(), 50);
}

window.changeTaskStato = async function(id, newStato) {
  try {
    await api.updateAttivita(id, { stato: newStato });
    _cachedData['attivita'] = null;
    const items = await _ensureCache('attivita');
    const t = items.find(x => x.id === id);
    if (t) await _renderAttivitaDetail(t);
    toast('Stato aggiornato', 'success');
  } catch (e) { toast('Errore', 'error'); }
};

// ─── Contatti cliente ──────────────────────────────────────────────────────
const RUOLI_CONTATTO = ['Direttore Tecnico','Direttore Generale','Amministratore Delegato',
  'Responsabile Acquisti','Responsabile Produzione','Responsabile Qualità','Responsabile Manutenzione',
  'Site Manager','Capoprogetto','Project Manager','CTO','CEO','Titolare','Ufficio Tecnico','Altro'];

function _renderContattiList(contatti, clienteId) {
  if (!contatti.length) return `<div class="empty-state" style="padding:24px">Nessun contatto aggiunto</div>`;
  return contatti.map(c => {
    const nomeCompleto = [c.nome, c.cognome].filter(Boolean).join(' ') || '?';
    const initials = [(c.nome||'')[0], (c.cognome||'')[0]].filter(Boolean).join('').toUpperCase() || '?';
    return `
    <div class="contatto-card" id="contatto-${c.id}">
      <div class="contatto-avatar">${esc(initials)}</div>
      <div class="contatto-body">
        <div class="contatto-nome">${esc(nomeCompleto)}</div>
        ${c.ruolo ? `<div class="contatto-ruolo">${esc(c.ruolo)}</div>` : ''}
        <div class="contatto-meta">
          ${c.email ? `<span>✉️ <a href="mailto:${esc(c.email)}">${esc(c.email)}</a></span>` : ''}
          ${c.telefono ? `<span>📞 ${esc(c.telefono)}</span>` : ''}
        </div>
        ${c.note ? `<div class="contatto-note">${esc(c.note)}</div>` : ''}
      </div>
      <div class="contatto-actions">
        <button class="btn-icon" onclick="openContattoModal('${c.id}','${clienteId}','')">✏️</button>
        <button class="btn-icon" onclick="deleteContatto('${c.id}','${clienteId}')">🗑️</button>
      </div>
    </div>`;
  }).join('');
}

window.openContattoModal = function(contattoId, clienteId, clienteNome) {
  const contatto = contattoId
    ? (_cachedData['contatti'] || []).find(c => c.id === contattoId) || {}
    : {};
  const isEdit = Boolean(contattoId);
  const ruoliOptions = RUOLI_CONTATTO.map(r => `<option value="${r}">`).join('');
  showModal({
    title: isEdit ? 'Modifica contatto' : 'Nuovo contatto',
    body: `<datalist id="ruoli-list">${ruoliOptions}</datalist>
    <form id="contatto-form" class="form-grid col2">
      <div class="form-group"><label>Nome *</label><input type="text" name="nome" value="${esc(contatto.nome||'')}" required></div>
      <div class="form-group"><label>Cognome *</label><input type="text" name="cognome" value="${esc(contatto.cognome||'')}" required></div>
      <div class="form-group"><label>Ruolo</label><input type="text" name="ruolo" value="${esc(contatto.ruolo||'')}" list="ruoli-list" autocomplete="off"></div>
      <div class="form-group"><label>Email</label><input type="email" name="email" value="${esc(contatto.email||'')}"></div>
      <div class="form-group"><label>Telefono</label><input type="tel" name="telefono" value="${esc(contatto.telefono||'')}"></div>
      <div class="form-group span2"><label>Note</label><textarea name="note" rows="2">${esc(contatto.note||'')}</textarea></div>
    </form>`,
    footer: `<button class="btn btn-ghost" onclick="closeModal()">Annulla</button>
             <button class="btn btn-primary" onclick="saveContatto('${contattoId||''}','${clienteId}','${esc(clienteNome||contatto.cliente_nome||'')}')">
               ${isEdit ? 'Salva' : 'Aggiungi'}
             </button>`,
  });
};

window.saveContatto = async function(contattoId, clienteId, clienteNome) {
  const form = document.getElementById('contatto-form');
  if (!form) return;
  const fd = new FormData(form);
  const payload = { cliente_id: clienteId, cliente_nome: clienteNome };
  for (const [k, v] of fd.entries()) payload[k] = v;
  const btn = document.querySelector('.modal-footer .btn-primary');
  btn.disabled = true;
  try {
    if (contattoId) {
      await api.updateContatto(contattoId, payload);
      if (!_cachedData['contatti']) _cachedData['contatti'] = [];
      const idx = _cachedData['contatti'].findIndex(c => c.id === contattoId);
      if (idx >= 0) _cachedData['contatti'][idx] = { ...payload, id: contattoId };
    } else {
      const newC = await api.creaContatto(payload);
      if (!_cachedData['contatti']) _cachedData['contatti'] = [];
      _cachedData['contatti'].push(newC);
    }
    closeModal();
    // Refresh contatti section
    const updated = await api.getContattiByCliente(clienteId).catch(() => []);
    const listEl = document.getElementById(`contatti-list-${clienteId}`);
    if (listEl) listEl.innerHTML = _renderContattiList(updated, clienteId);
    const countEl = document.getElementById('contatti-count');
    if (countEl) countEl.textContent = updated.length;
    toast(contattoId ? 'Contatto aggiornato' : 'Contatto aggiunto', 'success');
  } catch (e) {
    toast(e.message, 'error');
    btn.disabled = false;
  }
};

window.deleteContatto = async function(contattoId, clienteId) {
  if (!confirm('Eliminare questo contatto?')) return;
  try {
    await api.deleteContatto(contattoId);
    if (_cachedData['contatti']) {
      _cachedData['contatti'] = _cachedData['contatti'].filter(c => c.id !== contattoId);
    }
    const updated = await api.getContattiByCliente(clienteId).catch(() => []);
    const listEl = document.getElementById(`contatti-list-${clienteId}`);
    if (listEl) listEl.innerHTML = _renderContattiList(updated, clienteId);
    const countEl = document.getElementById('contatti-count');
    if (countEl) countEl.textContent = updated.length;
    toast('Contatto eliminato', 'info');
  } catch (e) { toast(e.message, 'error'); }
};

// ─── Prefilled modal ───────────────────────────────────────────────────────
window.openCreateModalPrefilled = function(entity, progettoId, progettoNome) {
  openModal(entity, { progetto_id: progettoId, progetto_nome: progettoNome });
};

// ─── Filtri e ordinamento ──────────────────────────────────────────────────
window.filterTable = function(entity) {
  const cfg = ENTITY_CONFIG[entity];
  const q = (document.getElementById(`search-${entity}`)?.value || '').toLowerCase();
  const statoFilter = document.getElementById(`filter-stato-${entity}`)?.value || '';
  const prioFilter  = document.getElementById(`filter-prio-${entity}`)?.value || '';
  let items = _cachedData[entity] || [];
  if (q) items = items.filter(i => cfg.columns.some(c => {
    const v = c.computed ? c.computed(i) : (i[c.key] || '');
    return String(v).toLowerCase().includes(q);
  }));
  if (statoFilter) items = items.filter(i => i[cfg.filterStatus?.[0]] === statoFilter);
  if (prioFilter)  items = items.filter(i => i[cfg.filterPrio?.[0]]   === prioFilter);
  renderTableRows(entity, items);
};

let _sortState = {};
window.sortTable = function(entity, key) {
  const items = [...(_cachedData[entity] || [])];
  const asc = !_sortState[entity + key];
  _sortState[entity + key] = asc;
  items.sort((a, b) => String(a[key] || '').localeCompare(String(b[key] || '')));
  if (!asc) items.reverse();
  renderTableRows(entity, items);
};

// ─── Log ───────────────────────────────────────────────────────────────────
async function renderLog(el) {
  const logs = await api.getLog(200);
  el.innerHTML = `
    <div class="section">
      <div class="section-header">
        <span class="section-title">Log Attività</span>
        <span style="color:var(--text2);font-size:13px">Ultimi ${logs.length} eventi</span>
      </div>
      <div class="table-wrap"><table>
        <thead><tr><th>Timestamp</th><th>Azione</th><th>Entità</th>
          <th class="hide-mobile">ID</th><th class="hide-mobile">Utente</th>
          <th class="hide-mobile">Dettagli</th></tr></thead>
        <tbody>
          ${logs.length ? logs.map(l => `<tr class="log-row">
            <td>${esc(l.timestamp)}</td>
            <td><code>${esc(l.azione)}</code></td>
            <td>${esc(l.entita)}</td>
            <td class="hide-mobile">${esc(l.id_entita)}</td>
            <td class="hide-mobile">${esc(l.utente)}</td>
            <td class="hide-mobile" style="max-width:200px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap">${esc(l.dettagli)}</td>
          </tr>`).join('') : `<tr><td colspan="6" class="empty-state">Nessun log</td></tr>`}
        </tbody>
      </table></div>
    </div>`;
}

// ─── Modal Create/Edit ─────────────────────────────────────────────────────
window.openCreateModal = function(entity) { openModal(entity, null); };
window.openEditModal   = function(entity, id) {
  _ensureCache(entity).then(items => {
    const item = items.find(i => i.id === id);
    openModal(entity, item || { id });
  });
};

function openModal(entity, data) {
  const cfg = ENTITY_CONFIG[entity];
  const hasRealId = data?.id && (_cachedData[entity] || []).some(i => i.id === data.id);
  const title = hasRealId ? `Modifica ${cfg.title}` : `Nuovo ${cfg.title}`;

  const fields = cfg.fields.map(f => {
    const val = data?.[f.key] ?? '';
    const spanClass = f.span === 2 ? 'span2' : '';
    if (f.type === 'textarea') return `<div class="form-group ${spanClass}">
      <label>${f.label}${f.required ? ' *' : ''}</label>
      <textarea name="${f.key}" rows="3">${esc(String(val))}</textarea></div>`;
    if (f.type === 'select') {
      const opts = f.options.map(o => `<option value="${o}" ${String(val)===o?'selected':''}>${o}</option>`).join('');
      return `<div class="form-group ${spanClass}"><label>${f.label}</label><select name="${f.key}">${opts}</select></div>`;
    }
    if (f.type === 'date') {
      let dv = String(val);
      if (dv.includes('/')) { const [d,m,y] = dv.split('/'); dv = `${y}-${m}-${d}`; }
      return `<div class="form-group ${spanClass}"><label>${f.label}</label><input type="date" name="${f.key}" value="${dv}"></div>`;
    }
    return `<div class="form-group ${spanClass}">
      <label>${f.label}${f.required?' *':''}</label>
      <input type="${f.type}" name="${f.key}" value="${esc(String(val))}" ${f.required?'required':''}></div>`;
  }).join('');

  showModal({
    title,
    body: `<form id="entity-form" class="form-grid col2">${fields}</form>`,
    footer: `
      <button class="btn btn-ghost" onclick="closeModal()">Annulla</button>
      <button class="btn btn-primary" onclick="submitEntityForm('${entity}',${hasRealId?`'${data.id}'`:'null'})">
        ${hasRealId ? 'Salva modifiche' : 'Crea'}
      </button>`,
  });
}

window.submitEntityForm = async function(entity, id) {
  const cfg = ENTITY_CONFIG[entity];
  const form = document.getElementById('entity-form');
  const formData = new FormData(form);
  const payload = {};
  for (const [key, val] of formData.entries()) {
    const fc = cfg.fields.find(f => f.key === key);
    if (fc?.type === 'date' && val) {
      const [y,m,d] = val.split('-');
      payload[key] = d && m && y ? `${d}/${m}/${y}` : val;
    } else { payload[key] = val; }
  }

  const btn = document.querySelector('.modal-footer .btn-primary');
  btn.disabled = true; btn.textContent = 'Salvo…';
  try {
    if (id) { await cfg.update(id, payload); toast('Modifiche salvate', 'success'); }
    else    { await cfg.create(payload);     toast('Elemento creato', 'success'); }
    closeModal();
    _cachedData[entity] = null;
    await renderEntityTable(document.getElementById('content'), entity);
  } catch (e) {
    toast(e.message, 'error');
    btn.disabled = false;
    btn.textContent = id ? 'Salva modifiche' : 'Crea';
  }
};

// ─── Elimina ───────────────────────────────────────────────────────────────
window.confirmDelete = function(entity, id, name) {
  showModal({
    title: 'Conferma eliminazione',
    body: `<p>Vuoi eliminare <strong>${esc(name)}</strong>?<br>
           <small style="color:var(--text2)">Questa operazione non può essere annullata.</small></p>`,
    footer: `<button class="btn btn-ghost" onclick="closeModal()">Annulla</button>
             <button class="btn btn-danger" onclick="doDelete('${entity}','${id}')">Elimina</button>`,
  });
};
window.doDelete = async function(entity, id) {
  const cfg = ENTITY_CONFIG[entity];
  try {
    await cfg.delete(id);
    toast('Elemento eliminato', 'info');
    closeModal();
    _cachedData[entity] = null;
    await renderEntityTable(document.getElementById('content'), entity);
  } catch (e) { toast(e.message, 'error'); }
};

// ─── Modal email offerta ───────────────────────────────────────────────────
window.openEmailModal = function(offertaId) {
  _ensureCache('offerte').then(items => {
    const offerta = items.find(o => o.id === offertaId);
    const tipo = offerta?.stato === 'Inviata' ? 'sollecito' : 'richiesta';
    showModal({
      title: tipo === 'sollecito' ? '📧 Invia Sollecito' : '📧 Invia Richiesta Preventivo',
      body: `
        <div class="form-grid">
          <div class="form-group span2">
            <label>Email destinatario *</label>
            <input type="email" id="email-dest" value="${esc(offerta?.email_fornitore || '')}" placeholder="email@fornitore.it">
          </div>
          ${tipo !== 'sollecito' ? `<div class="form-group span2">
            <label>Scadenza richiesta</label>
            <input type="date" id="email-scadenza">
          </div>` : ''}
        </div>
        <p style="margin-top:12px;color:var(--text2);font-size:13px">
          Fornitore: <strong>${esc(offerta?.fornitore_nome||'—')}</strong> | Progetto: <strong>${esc(offerta?.progetto_nome||'—')}</strong>
        </p>`,
      footer: `<button class="btn btn-ghost" onclick="closeModal()">Annulla</button>
               <button class="btn btn-primary" onclick="sendOffertaEmail('${offertaId}','${tipo}')">Invia</button>`,
    });
  });
};

window.sendOffertaEmail = async function(offertaId, tipo) {
  const email = document.getElementById('email-dest')?.value?.trim();
  if (!email) { toast('Inserisci un indirizzo email', 'error'); return; }
  try {
    if (tipo === 'sollecito') {
      await api.sollecitaOfferta(offertaId, { email_destinatario: email });
    } else {
      const sr = document.getElementById('email-scadenza')?.value || '';
      let scadenza = sr;
      if (sr) { const [y,m,d] = sr.split('-'); scadenza = `${d}/${m}/${y}`; }
      await api.inviaRichiesta(offertaId, { email_destinatario: email, scadenza });
    }
    toast('Email inviata con successo', 'success');
    closeModal();
  } catch (e) { toast(e.message, 'error'); }
};

// ─── Modal helper ──────────────────────────────────────────────────────────
function showModal({ title, body, footer }) {
  document.getElementById('modal-title').textContent = title;
  document.getElementById('modal-body').innerHTML = body;
  document.getElementById('modal-footer').innerHTML = footer;
  document.getElementById('modal-overlay').classList.add('open');
}
window.closeModal = function() {
  document.getElementById('modal-overlay').classList.remove('open');
};

// ─── Toast ─────────────────────────────────────────────────────────────────
function toast(msg, type = 'info') {
  const container = document.getElementById('toast-container');
  const el = document.createElement('div');
  el.className = `toast ${type}`;
  el.textContent = msg;
  container.appendChild(el);
  requestAnimationFrame(() => requestAnimationFrame(() => el.classList.add('show')));
  setTimeout(() => { el.classList.remove('show'); setTimeout(() => el.remove(), 350); }, 3500);
}

// ─── Badge helpers ─────────────────────────────────────────────────────────
function badgeStatoOfferta(s) {
  const m = {'Da Inviare':'da-inviare','Inviata':'inviata','Ricevuta':'ricevuta',
    'In Valutazione':'in-valutazione','Aggiudicata':'aggiudicata','Rifiutata':'rifiutata'};
  return s ? `<span class="badge badge-${m[s]||'da-inviare'}">${esc(s)}</span>` : '';
}
function badgeStatoTask(s) {
  const m = {'Da fare':'da-fare','In corso':'in-corso','Fatto':'fatto'};
  return s ? `<span class="badge badge-${m[s]||'da-fare'}">${esc(s)}</span>` : '';
}
function badgeStatoProgetto(s) {
  const m = {'Attivo':'attivo','Sospeso':'sospeso','Chiuso':'chiuso'};
  return s ? `<span class="badge badge-${m[s]||'attivo'}">${esc(s)}</span>` : '';
}
function badgePriorita(p) {
  const m = {'Alta':'alta','Media':'media','Bassa':'bassa'};
  return p ? `<span class="badge badge-${m[p]||'media'}">${esc(p)}</span>` : '';
}

// ─── Utility ───────────────────────────────────────────────────────────────
function _isScaduta(dateStr) {
  if (!dateStr) return false;
  const parts = dateStr.split('/');
  if (parts.length !== 3) return false;
  return new Date(+parts[2], +parts[1]-1, +parts[0]) < new Date();
}

function esc(str) {
  return String(str ?? '')
    .replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;')
    .replace(/"/g,'&quot;').replace(/'/g,'&#39;');
}

// ─── Sync Google Contacts ─────────────────────────────────────────────────
window.syncGoogleContacts = async function() {
  const token = localStorage.getItem('crm_token');
  toast('Sincronizzazione in corso…', 'info');
  try {
    const res = await fetch('/api/sync/google-contacts', {
      method: 'POST',
      headers: { 'Authorization': `Bearer ${token}` },
    });
    if (!res.ok) {
      const err = await res.json();
      throw new Error(err.detail || `Errore ${res.status}`);
    }
    const data = await res.json();
    const msg = `Google Contacts: ${data.synced} nuovi, ${data.updated} aggiornati, ${data.skipped} saltati`;
    toast(msg, 'success');
    if (data.errors?.length) console.warn('[Sync] Errori:', data.errors);
    _cachedData['contatti'] = null;
    await renderEntityTable(document.getElementById('content'), 'contatti');
  } catch (e) {
    toast(e.message || 'Errore sync Google', 'error');
  }
};

// ─── Import / Export CSV ───────────────────────────────────────────────────
window.scaricaTemplateCSV = function(entity) {
  const token = localStorage.getItem('crm_token');
  const a = document.createElement('a');
  a.href = `/api/import/${entity}/template`;
  // Aggiungi token come query param temporaneo non è possibile con fetch redirect
  // Uso fetch + blob download
  fetch(`/api/import/${entity}/template`, {
    headers: { 'Authorization': `Bearer ${token}` }
  }).then(r => r.blob()).then(blob => {
    const url = URL.createObjectURL(blob);
    a.href = url;
    a.download = `template_${entity}.csv`;
    a.click();
    URL.revokeObjectURL(url);
  }).catch(() => toast('Errore download template', 'error'));
};

window.importaCSV = function(entity) {
  document.getElementById(`csv-input-${entity}`)?.click();
};

window.handleCSVUpload = async function(event, entity) {
  const file = event.target.files?.[0];
  if (!file) return;
  event.target.value = '';

  const token = localStorage.getItem('crm_token');
  const formData = new FormData();
  formData.append('file', file);

  toast('Importazione in corso…', 'info');
  try {
    const res = await fetch(`/api/import/${entity}`, {
      method: 'POST',
      headers: { 'Authorization': `Bearer ${token}` },
      body: formData,
    });
    if (!res.ok) throw new Error(`Errore ${res.status}`);
    const data = await res.json();
    toast(`Importati ${data.imported} record${data.skipped ? `, ${data.skipped} saltati` : ''}`, 'success');
    if (data.errors?.length) {
      console.warn('[CSV Import] Errori:', data.errors);
    }
    _cachedData[entity] = null;
    await renderEntityTable(document.getElementById('content'), entity);
  } catch (e) {
    toast(e.message || 'Errore importazione', 'error');
  }
};
