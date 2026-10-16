const BLOOD_GROUPS = ["A+", "A-", "B+", "B-", "AB+", "AB-", "O+", "O-"];
function bloodGroupOptionsHtml(selected){
  return '<option value="">Select…</option>' +
    BLOOD_GROUPS.map(g => `<option value="${g}" ${g === selected ? 'selected' : ''}>${g}</option>`).join('');
}

/* =========================================================
   ADMIN / DOCTOR — PATIENTS VIEW
   ========================================================= */
async function renderPatientsView(body){
  const canCreate = state.role === 'admin' || state.role === 'doctor';
  const isAdmin = state.role === 'admin';
  body.innerHTML = `
    <div class="stat-strip" id="patientStats"></div>
    ${canCreate ? `
    <div class="card">
      <h3>Add a patient</h3>
      <form id="patientForm">
        <div class="form-grid">
          <div class="field"><label>User ID</label><input name="user_id" required placeholder="e.g. PAT002"></div>
          <div class="field"><label>Username</label><input name="username" required placeholder="e.g. jane"></div>
          <div class="field"><label>Password</label><input name="password" type="password" required minlength="8"></div>
          <div class="field"><label>Full name</label><input name="name" required></div>
          <div class="field"><label>Contact</label><input name="contact" required></div>
          <div class="field"><label>Relative contact</label><input name="relative_contact" required></div>
          <div class="field"><label>Age</label><input name="age" type="number" min="0" max="150" required></div>
          <div class="field"><label>Email</label><input name="email" type="email" required></div>
          <div class="field"><label>Blood group</label><select name="blood_group" required>${bloodGroupOptionsHtml('')}</select></div>
          ${isAdmin ? `
          <div class="field">
            <label>Assign to doctor</label>
            <select name="assigned_doctor_id" id="assignedDoctorSelect" required>
              <option value="">Loading doctors…</option>
            </select>
          </div>` : ''}
        </div>
        <div class="form-actions">
          <button class="btn btn-primary" type="submit">Create patient</button>
          <span class="inline-msg" id="patientFormMsg"></span>
        </div>
      </form>
    </div>` : ''}
    <div class="card">
      <h3>All patients</h3>
      <div class="field" style="max-width:320px;margin-bottom:14px;">
        <input type="search" id="patientSearch" placeholder="Search by name, username, contact, email…">
      </div>
      <div id="patientsTableWrap">${emptyStateHtml('Loading…')}</div>
    </div>
  `;

  if(canCreate){ if(isAdmin) loadDoctorOptions();
    document.getElementById('patientForm').addEventListener('submit', async (e)=>{
      e.preventDefault();
      const msg = document.getElementById('patientFormMsg');
      const fd = new FormData(e.target);
      const body = Object.fromEntries(fd.entries());
      body.age = Number(body.age);
      try{
        await api('/patients/', { method:'POST', body });
        msg.textContent = 'Created.'; msg.className = 'inline-msg ok';
        e.target.reset();
        toast(`Patient "${body.username}" created`);
        loadPatientsTable();
      }catch(err){
        msg.textContent = err.message; msg.className = 'inline-msg err';
      }
    });
  }
  document.getElementById('patientSearch').addEventListener('input', (e)=>{
  renderPatientsTable(filterPatients(e.target.value));
  });

  if(isAdmin) await loadDoctorNameMap();
  loadPatientsTable();
}
let _allPatients = [];

// Admin-only: user_id -> doctor username, so the patients table can show
// "assigned to" without a per-row API call. Doctors don't need this - their
// own patient list is already implicitly all-one-doctor.
let _doctorNameMap = {};

async function loadDoctorNameMap(){
  try{
    const staff = await api('/auth/staff');
    _doctorNameMap = {};
    staff.filter(s => s.role === 'doctor').forEach(d => { _doctorNameMap[d._id] = d.username; });
  }catch(err){ /* table just falls back to showing the raw ID */ }
}

const STAT_ICON_PATIENTS = '<svg viewBox="0 0 24 24"><path d="M12 19 C5.5 14.5 3 10.5 6 7.5 C7.9 5.6 10.7 5.9 12 8 C13.3 5.9 16.1 5.6 18 7.5 C21 10.5 18.5 14.5 12 19 Z"/></svg>';
const STAT_ICON_BLOOD = '<svg viewBox="0 0 24 24"><path d="M12 3 C16 9 19 13 19 16.5 A7 7 0 0 1 5 16.5 C5 13 8 9 12 3 Z"/></svg>';

function renderPatientStats(patients){
  const wrap = document.getElementById('patientStats');
  if(!wrap) return;
  const uniqueBloodGroups = new Set(patients.map(p => p.blood_group).filter(Boolean)).size;
  wrap.innerHTML = `
    <div class="stat-card">
      <span class="stat-icon">${STAT_ICON_PATIENTS}</span>
      <div><div class="stat-value">${patients.length}</div><div class="stat-label">Total patients</div></div>
    </div>
    <div class="stat-card">
      <span class="stat-icon">${STAT_ICON_BLOOD}</span>
      <div><div class="stat-value">${uniqueBloodGroups}</div><div class="stat-label">Blood groups on file</div></div>
    </div>
  `;
}

function filterPatients(query){
  const q = query.trim().toLowerCase();
  if(!q) return _allPatients;
  return _allPatients.filter(p =>
    (p.name||'').toLowerCase().includes(q) ||
    (p.username||'').toLowerCase().includes(q) ||
    (p.contact||'').toLowerCase().includes(q) ||
    (p.relative_contact||'').toLowerCase().includes(q) ||
    (p.email||'').toLowerCase().includes(q) ||
    (p.blood_group||'').toLowerCase().includes(q) ||
    (_doctorNameMap[p.created_by] || '').toLowerCase().includes(q)
  );
}

function renderPatientsTable(patients){
  const wrap = document.getElementById('patientsTableWrap');
  if(!patients.length){ wrap.innerHTML = emptyStateHtml('No matching patients.'); return; }
  const isAdmin = state.role === 'admin';
  wrap.innerHTML = `<table><thead><tr><th>Name</th><th>Username</th><th>Age</th><th>Blood grp</th><th>Contact</th>${isAdmin ? '<th>Doctor</th>' : ''}<th>Admit date</th><th>Status</th><th></th></tr></thead><tbody>
    ${patients.map(p => `<tr>
      <td>${esc(p.name)}</td>
      <td class="mono">${esc(p.username)}</td>
      <td>${esc(p.age)}</td>
      <td>${esc(p.blood_group)}</td>
      <td>${esc(p.contact)}</td>
      ${isAdmin ? `<td>${esc(_doctorNameMap[p.created_by] || p.created_by || '—')}</td>` : ''}
      <td>${fmtDate(p.created_at)}</td>
      <td><span class="tag ${p.discharge_date ? 'tag-inactive' : 'tag-active'}">${p.discharge_date ? 'Discharged' : 'Admitted'}</span></td>
      <td class="row-actions">
        <button class="btn btn-secondary" onclick="openPatientDetail('${p._id}')">View</button>
      </td>
    </tr>`).join('')}
  </tbody></table>`;
}

async function loadPatientsTable(){
  const wrap = document.getElementById('patientsTableWrap');
  try{
    _allPatients = await api('/patients/');
    renderPatientStats(_allPatients);
    if(!_allPatients.length){ wrap.innerHTML = emptyStateHtml('No patients yet.'); return; }
    const searchBox = document.getElementById('patientSearch');
    renderPatientsTable(filterPatients(searchBox ? searchBox.value : ''));
  }catch(err){
    wrap.innerHTML = `<div class="empty-state">${esc(err.message)}</div>`;
  }
}

async function openPatientDetail(patientId){
  openModal(emptyStateHtml('Loading…'));
  try{
    const p = await api(`/patients/${patientId}`);
    renderPatientModal(p);
  }catch(err){
    openModal(`<div class="empty-state">${esc(err.message)}</div>`);
  }
}

function renderPatientModal(p){
  const canEdit = state.role === 'doctor';
  const canDeletePatient = state.role === 'admin' || state.role === 'doctor';
  const canDeleteFile = state.role === 'admin' || state.role === 'doctor';
  document.getElementById('modalContent').innerHTML = `
    <div class="modal-head"><h3>${esc(p.name)}</h3><button class="modal-close" onclick="closeModal()">&times;</button></div>

    <div class="patient-detail" id="detailFields">
      ${detailField('Username', p.username)}
      ${detailField('Age', p.age)}
      ${detailField('Blood group', p.blood_group)}
      ${detailField('Contact', p.contact)}
      ${detailField('Relative contact', p.relative_contact)}
      ${detailField('Email', p.email)}
      ${detailField('Admit date', fmtDate(p.created_at))}
      ${p.discharge_date ? detailField('Discharge date', fmtDate(p.discharge_date)) : ''}
      ${state.role === 'admin' ? detailField('Assigned doctor', _doctorNameMap[p.created_by] || p.created_by || '—') : ''}
    </div>
    <span class="tag ${p.discharge_date ? 'tag-inactive' : 'tag-active'}" style="margin-bottom:4px;">${p.discharge_date ? 'Discharged' : 'Admitted'}</span>

    ${canEdit ? `
    <div style="margin:16px 0 4px;">
      <button class="btn btn-secondary" id="editToggleBtn">Edit details</button>
    </div>
    <form id="editForm" style="display:none;margin-top:12px;">
      <div class="form-grid">
        <div class="field"><label>Name</label><input name="name" value="${esc(p.name)}"></div>
        <div class="field"><label>Age</label><input name="age" type="number" value="${esc(p.age)}"></div>
        <div class="field"><label>Blood group</label><select name="blood_group">${bloodGroupOptionsHtml(p.blood_group)}</select></div>
        <div class="field"><label>Contact</label><input name="contact" value="${esc(p.contact)}"></div>
        <div class="field"><label>Relative contact</label><input name="relative_contact" value="${esc(p.relative_contact)}"></div>
        <div class="field"><label>Email</label><input name="email" type="email" value="${esc(p.email)}"></div>
        <div class="field"><label>Discharge date</label><input name="discharge_date" type="date" value="${esc(p.discharge_date || '')}"></div>
      </div>
      <div class="form-actions">
        <button class="btn btn-primary" type="submit">Save changes</button>

        <span class="inline-msg" id="editMsg"></span>
      </div>
    </form>` : ''}

    <div style="margin-top:22px;border-top:1px solid var(--line);padding-top:16px;">
      <h3 style="font-size:13.5px;margin-bottom:10px;">Files</h3>
      <div id="modalFiles">${emptyStateHtml('Loading…')}</div>
      ${(state.role==='admin'||state.role==='doctor') ? `
      <div class="upload-drop">
        <label for="modalUpload">Choose a file</label> to upload (pdf, image, video, doc)
        <input type="file" id="modalUpload">
      </div>` : ''}
    </div>

    ${canDeletePatient ? `
    <div style="margin-top:22px;border-top:1px solid var(--line);padding-top:16px;">
      <button class="btn btn-danger" id="deletePatientBtn">Delete this patient</button>
    </div>` : ''}
  `;

  if(canEdit){
    document.getElementById('editToggleBtn').onclick = ()=>{
      const f = document.getElementById('editForm');
      f.style.display = f.style.display === 'none' ? 'block' : 'none';
    };
    document.getElementById('editForm').addEventListener('submit', async (e)=>{
      e.preventDefault();
      const msg = document.getElementById('editMsg');
      const fd = new FormData(e.target);
      const body = Object.fromEntries(fd.entries());
      body.age = Number(body.age);
      try{
        const updated = await api(`/patients/${p._id}`, { method:'PUT', body });
        msg.textContent = 'Saved.'; msg.className = 'inline-msg ok';
        toast('Patient updated');
        renderPatientModal(updated);
        loadPatientsTable();
      }catch(err){
        msg.textContent = err.message; msg.className = 'inline-msg err';
      }
    });
  }

  if(canDeletePatient){
    document.getElementById('deletePatientBtn').onclick = async ()=>{
      if(!confirm(`Delete ${p.name}? This also removes their login and uploaded files. This cannot be undone.`)) return;
      try{
        await api(`/patients/${p._id}`, { method:'DELETE' });
        toast('Patient deleted');
        closeModal();
        loadPatientsTable();
      }catch(err){ toast(err.message, true); }
    };
  }

  if(state.role==='admin'||state.role==='doctor'){
    document.getElementById('modalUpload').addEventListener('change', async (e)=>{
      const file = e.target.files[0];
      if(!file) return;
      const fd = new FormData();
      fd.append('file', file);
      try{
        await api(`/patients/${p._id}/files`, { method:'POST', body: fd });
        toast('File uploaded');
        loadModalFiles(p._id, true);
      }catch(err){ toast(err.message, true); }
      e.target.value = '';
    });
  }

  loadModalFiles(p._id, canDeleteFile);
}

function detailField(label, value){
  return `<div class="kv"><label>${esc(label)}</label><div>${esc(value)}</div></div>`;
}

async function loadModalFiles(patientId, canDelete){
  const wrap = document.getElementById('modalFiles');
  try{
    const files = await api(`/patients/${patientId}/files`);
    if(!files.length){ wrap.innerHTML = emptyStateHtml('No files uploaded yet.'); return; }
    wrap.innerHTML = files.map(f => `
      <div class="file-row">
        <div>
          <div class="file-name">${esc(f.filename)}</div>
          <div class="file-meta">${esc(f.content_type||'')} · ${(f.length/1024).toFixed(1)} KB</div>
        </div>
        <div class="row-actions">
          <button class="btn btn-secondary" onclick="downloadFile('${patientId}','${f.file_id}')">Download</button>
          ${canDelete ? `<button class="btn btn-danger" onclick="deleteFile('${patientId}','${f.file_id}')">Delete</button>` : ''}
        </div>
      </div>
    `).join('');
  }catch(err){
    wrap.innerHTML = `<div class="empty-state">${esc(err.message)}</div>`;
  }
}

function downloadFile(patientId, fileId){
  // GET redirects to a short-lived signed Cloudinary URL, so a direct
  // navigation (not fetch) is what lets the browser follow it and
  // download/preview the file, while still passing the Bearer token first.
  fetch(`${state.apiBase}/patients/${patientId}/files/${fileId}`, {
    headers: { Authorization: 'Bearer ' + state.token }
  }).then(res=>{
    if(res.redirected || res.url){ window.open(res.url, '_blank'); }
    else toast('Could not open file', true);
  }).catch(()=> toast('Could not open file', true));
}

async function deleteFile(patientId, fileId){
  if(!confirm('Delete this file permanently?')) return;
  try{
    await api(`/patients/${patientId}/files/${fileId}`, { method:'DELETE' });
    toast('File deleted');
    loadModalFiles(patientId, true);
  }catch(err){ toast(err.message, true); }
}

async function loadDoctorOptions(){
  const select = document.getElementById('assignedDoctorSelect');
  try{
    const staff = await api('/auth/staff');
    const doctors = staff.filter(s => s.role === 'doctor');
    if(!doctors.length){
      select.innerHTML = '<option value="">No doctors exist yet — create one first</option>';
      return;
    }
    select.innerHTML = '<option value="">Select a doctor…</option>' +
      doctors.map(d => `<option value="${esc(d._id)}">${esc(d.username)}</option>`).join('');
  }catch(err){
    select.innerHTML = '<option value="">Could not load doctors</option>';
  }
}