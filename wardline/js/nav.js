/* =========================================================
   APP SHELL / NAV
   ========================================================= */

// Small line-art icons, same stroke style as the front page's portal
// cards (rounded square badge + 1.6px stroke) - reused here so the
// dashboard nav visually rhymes with the landing page.
const NAV_ICONS = {
  staff: '<svg viewBox="0 0 24 24"><path d="M12 3 L20 6.5 V11 C20 16 16.5 20 12 21.5 C7.5 20 4 16 4 11 V6.5 Z"/><path d="M8.5 12 L11 14.5 L16 9"/></svg>',
  patients: '<svg viewBox="0 0 24 24"><path d="M12 19 C5.5 14.5 3 10.5 6 7.5 C7.9 5.6 10.7 5.9 12 8 C13.3 5.9 16.1 5.6 18 7.5 C21 10.5 18.5 14.5 12 19 Z"/></svg>',
  appointments: '<svg viewBox="0 0 24 24"><rect x="3.5" y="5" width="17" height="15.5" rx="2"/><line x1="3.5" y1="9.5" x2="20.5" y2="9.5"/><line x1="7.5" y1="2.5" x2="7.5" y2="6.5"/><line x1="16.5" y1="2.5" x2="16.5" y2="6.5"/></svg>',
  me: '<svg viewBox="0 0 24 24"><circle cx="12" cy="8.5" r="3.5"/><path d="M5 20 C5 15.5 8 13 12 13 C16 13 19 15.5 19 20"/></svg>',
  files: '<svg viewBox="0 0 24 24"><path d="M6 3.5 H14 L18 7.5 V20.5 H6 Z"/><path d="M14 3.5 V7.5 H18"/></svg>',
  book: '<svg viewBox="0 0 24 24"><rect x="3.5" y="5" width="17" height="15.5" rx="2"/><line x1="3.5" y1="9.5" x2="20.5" y2="9.5"/><path d="M8 14 H10.5 M13 14 H16 M8 17.5 H10.5"/></svg>',
};

// Small line-art icon shown above an empty-state message - same visual
// language as the nav icons, muted so it doesn't compete with the text.
const EMPTY_ICON = '<svg viewBox="0 0 24 24"><path d="M4 10 L12 4 L20 10 V20 H4 Z"/><path d="M9.5 20 V14 H14.5 V20"/></svg>';

function emptyStateHtml(message){
  return `<div class="empty-state"><span class="empty-icon">${EMPTY_ICON}</span>${esc(message)}</div>`;
}

// Formats an ISO timestamp (or anything Date can parse) as e.g. "14 Aug 2026".
// Falls back to an em dash for missing/invalid values - used for "Joining
// date" (staff) and "Admit date" (patients), both of which can be blank on
// older records created before those fields existed.
function fmtDate(value){
  if(!value) return '—';
  const d = new Date(value);
  if(isNaN(d.getTime())) return '—';
  return d.toLocaleDateString(undefined, { day:'2-digit', month:'short', year:'numeric' });
}

const ROLE_EYEBROW = { admin: 'ADMIN WORKSPACE', doctor: 'DOCTOR WORKSPACE', patient: 'PATIENT PORTAL' };

const NAV = {
  admin: [
    { id:'staff',    label:'Staff' },
    { id:'patients', label:'Patients' },
    { id:'appointments', label:'Appointments' },
  ],
  doctor: [
    { id:'patients', label:'Patients' },
    { id:'appointments', label:'Appointments' },
  ],
  patient: [
    { id:'me',    label:'My Record' },
    { id:'files', label:'My Files' },
    { id:'book',  label:'Book Appointment' },
  ],
};

function enterApp(){
  document.getElementById('loginScreen').style.display = 'none';
  document.getElementById('app').classList.add('active');
  document.getElementById('roleBadge').textContent = state.role;
  document.getElementById('whoLabel').textContent = state.username + ' · ' + state.userId;

  const navWrap = document.getElementById('navItems');
  navWrap.innerHTML = '';
  NAV[state.role].forEach((item, i)=>{
    const b = document.createElement('button');
    b.className = 'nav-item' + (i===0 ? ' active' : '');
    b.innerHTML = `<span class="nav-icon">${NAV_ICONS[item.id] || ''}</span><span>${esc(item.label)}</span>` + (item.id === 'appointments' ? '<span class="nav-badge" id="apptBadge" style="display:none;"></span>' : '');
    b.onclick = ()=>{
      document.querySelectorAll('.nav-item').forEach(n=>n.classList.remove('active'));
      b.classList.add('active');
      renderView(item.id);
    };
    navWrap.appendChild(b);
  });

  renderView(NAV[state.role][0].id);

  if(state.role === 'admin' || state.role === 'doctor'){
    startAppointmentBadgePolling();
  }
}

let _apptBadgeTimer = null;

async function refreshAppointmentBadge(){
  const badge = document.getElementById('apptBadge');
  if(!badge) return; // nav re-rendered without an appointments item, or already logged out
  try{
    const { count } = await api('/appointments/unseen-count');
    if(count > 0){ badge.textContent = count; badge.style.display = 'inline-block'; }
    else{ badge.style.display = 'none'; }
  }catch(err){ /* silent - badge just stays as-is on a transient failure */ }
}

function startAppointmentBadgePolling(){
  refreshAppointmentBadge();
  clearInterval(_apptBadgeTimer);
  _apptBadgeTimer = setInterval(refreshAppointmentBadge, 30000);
}

function stopAppointmentBadgePolling(){
  clearInterval(_apptBadgeTimer);
  _apptBadgeTimer = null;
}

function renderView(id){
  const eyebrow = document.getElementById('viewEyebrow');
  const icon = document.getElementById('viewIcon');
  const title = document.getElementById('viewTitle');
  const desc = document.getElementById('viewDesc');
  const body = document.getElementById('viewBody');
  eyebrow.textContent = ROLE_EYEBROW[state.role] || '';
  icon.innerHTML = NAV_ICONS[id] || '';
  body.innerHTML = emptyStateHtml('Loading…');

  if(id === 'staff'){
    title.textContent = 'Staff'; desc.textContent = 'Doctors and Admins — create-only by Admin, never self-registered.';
    renderStaffView(body);
  } else if(id === 'patients'){
    title.textContent = 'Patients';
    desc.textContent = state.role === 'admin'
      ? 'Full access to create and delete. Editing details is a Doctor-only action.'
      : 'Create new patients and update their details.';
    renderPatientsView(body);
  } else if(id === 'me'){
    title.textContent = 'My Record'; desc.textContent = 'Only visible to you — your Doctor can update these details.';
    renderMyRecordView(body);
  } else if(id === 'files'){
    title.textContent = 'My Files'; desc.textContent = 'Documents and images your care team has uploaded for you.';
    renderMyFilesView(body);
  } else if(id === 'appointments'){
    title.textContent = 'Appointments'; desc.textContent = state.role === 'admin'
      ? 'Every appointment booked across the hospital.'
      : 'Appointments booked with you.';
    renderAppointmentsView(body);
  } else if(id === 'book'){
    title.textContent = 'Book Appointment'; desc.textContent = 'Pick a doctor, date, and an open 30-minute slot.';
    renderBookAppointmentView(body);
  }
}