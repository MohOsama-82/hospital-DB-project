/* =========================================================
   ADMIN — STAFF VIEW
   ========================================================= */
async function renderStaffView(body){
  body.innerHTML = `
    <div class="stat-strip" id="staffStats"></div>
    <div class="card">
      <h3>Add a Doctor or Admin</h3>
      <form id="staffForm">
        <div class="form-grid">
          <div class="field"><label>User ID</label><input name="user_id" required placeholder="e.g. DOC002"></div>
          <div class="field"><label>Username</label><input name="username" required placeholder="e.g. doc2"></div>
          <div class="field"><label>Email</label><input name="email" type="email" required></div>
          <div class="field"><label>Password</label><input name="password" type="password" required minlength="8"></div>
          <div class="field"><label>Role</label>
            <select name="role"><option value="doctor">Doctor</option><option value="admin">Admin</option></select>
          </div>
        </div>
        <div class="form-actions">
          <button class="btn btn-primary" type="submit">Create account</button>
          <span class="inline-msg" id="staffFormMsg"></span>
        </div>
      </form>
    </div>
    <div class="card">
      <h3>Staff</h3>
      <div class="field" style="max-width:320px;margin-bottom:14px;">
        <input type="search" id="staffSearch" placeholder="Search by user ID, username, email…">
      </div>
      <div class="staff-tabs" id="staffTabs">
        <button type="button" class="staff-tab active" data-tab="doctor">Doctors</button>
        <button type="button" class="staff-tab" data-tab="admin">Admins</button>
      </div>
      <div id="doctorTableWrap">${emptyStateHtml('Loading…')}</div>
      <div id="adminTableWrap" style="display:none;">${emptyStateHtml('Loading…')}</div>
    </div>
  `;

  document.getElementById('staffTabs').addEventListener('click', (e)=>{
    const btn = e.target.closest('.staff-tab');
    if(!btn) return;
    document.querySelectorAll('.staff-tab').forEach(b=>b.classList.remove('active'));
    btn.classList.add('active');
    const isDoctor = btn.dataset.tab === 'doctor';
    document.getElementById('doctorTableWrap').style.display = isDoctor ? '' : 'none';
    document.getElementById('adminTableWrap').style.display = isDoctor ? 'none' : '';
  });

  document.getElementById('staffForm').addEventListener('submit', async (e)=>{
    e.preventDefault();
    const msg = document.getElementById('staffFormMsg');
    const fd = new FormData(e.target);
    const body = Object.fromEntries(fd.entries());
    try{
      await api('/auth/create-staff', { method:'POST', body });
      msg.textContent = 'Created.'; msg.className = 'inline-msg ok';
      e.target.reset();
      toast(`${body.role} account "${body.username}" created`);
      loadStaffTable();
    }catch(err){
      msg.textContent = err.message; msg.className = 'inline-msg err';
    }
  });

  document.getElementById('staffSearch').addEventListener('input', (e)=>{
  renderStaffTables(filterStaff(e.target.value));
});

loadStaffTable();
}

let _allStaff = [];

const STAT_ICON_DOCTOR = '<svg viewBox="0 0 24 24"><rect x="5" y="3" width="14" height="18" rx="2"/><path d="M9.5 3 V1.6 a1 1 0 0 1 1-1 h3 a1 1 0 0 1 1 1 V3"/><path d="M8 10 H10.5 L12 7.5 L14 12.5 L15.5 10 H17"/></svg>';
const STAT_ICON_ADMIN = '<svg viewBox="0 0 24 24"><path d="M12 3 L20 6.5 V11 C20 16 16.5 20 12 21.5 C7.5 20 4 16 4 11 V6.5 Z"/><path d="M8.5 12 L11 14.5 L16 9"/></svg>';

function renderStaffStats(staff){
  const wrap = document.getElementById('staffStats');
  if(!wrap) return;
  const doctorCount = staff.filter(s => s.role === 'doctor').length;
  const adminCount = staff.filter(s => s.role === 'admin').length;
  wrap.innerHTML = `
    <div class="stat-card">
      <span class="stat-icon">${STAT_ICON_DOCTOR}</span>
      <div><div class="stat-value">${doctorCount}</div><div class="stat-label">Doctors</div></div>
    </div>
    <div class="stat-card">
      <span class="stat-icon">${STAT_ICON_ADMIN}</span>
      <div><div class="stat-value">${adminCount}</div><div class="stat-label">Admins</div></div>
    </div>
  `;
}

function filterStaff(query){
  const q = query.trim().toLowerCase();
  if(!q) return _allStaff;
  return _allStaff.filter(s =>
    (s._id||'').toLowerCase().includes(q) ||
    (s.username||'').toLowerCase().includes(q) ||
    (s.email||'').toLowerCase().includes(q)
  );
}

function renderStaffTables(staff){
  document.getElementById('doctorTableWrap').innerHTML = staffTableHtml(staff.filter(s => s.role === 'doctor'));
  document.getElementById('adminTableWrap').innerHTML = staffTableHtml(staff.filter(s => s.role === 'admin'));
}

function staffTableHtml(list){
  if(!list.length) return emptyStateHtml('None yet.');
  return `<table><thead><tr><th>User ID</th><th>Username</th><th>Email</th><th>Status</th><th>Joining date</th><th></th></tr></thead><tbody>
    ${list.map(s => `<tr>
      <td class="mono">${esc(s._id)}</td>
      <td>${esc(s.username)}</td>
      <td>${esc(s.email)}</td>
      <td><span class="tag ${s.status === 'resigned' ? 'tag-inactive' : 'tag-active'}">${s.status === 'resigned' ? 'Resigned' : 'Active'}</span></td>
      <td>${fmtDate(s.created_at)}</td>
      <td class="row-actions">
        <button class="btn btn-secondary" onclick="openStaffDetail('${s._id}')">View</button>
      </td>
    </tr>`).join('')}
  </tbody></table>`;
}

async function loadStaffTable(){
  const doctorWrap = document.getElementById('doctorTableWrap');
  const adminWrap = document.getElementById('adminTableWrap');
  try{
    _allStaff = await api('/auth/staff');
    renderStaffStats(_allStaff);
    const searchBox = document.getElementById('staffSearch');
    renderStaffTables(filterStaff(searchBox ? searchBox.value : ''));
  }catch(err){
    const msg = `<div class="empty-state">${esc(err.message)}</div>`;
    doctorWrap.innerHTML = msg;
    adminWrap.innerHTML = msg;
  }
}

async function openStaffDetail(userId){
  openModal(emptyStateHtml('Loading…'));
  try{
    const s = await api(`/auth/staff/${userId}`);
    const isSelf = s._id === state.userId;
    document.getElementById('modalContent').innerHTML = `
      <div class="modal-head"><h3>${esc(s.username)}</h3><button class="modal-close" onclick="closeModal()">&times;</button></div>
      <div class="patient-detail" id="staffDetailFields">
        ${detailField('User ID', s._id)}
        ${detailField('Username', s.username)}
        ${detailField('Email', s.email)}
        ${detailField('Role', s.role)}
        ${detailField('Joining date', fmtDate(s.created_at))}
        ${s.status === 'resigned' ? detailField('Resigned on', fmtDate(s.resigned_at)) : ''}
      </div>
      <span class="tag ${s.status === 'resigned' ? 'tag-inactive' : 'tag-active'}" style="margin-bottom:4px;">${s.status === 'resigned' ? 'Resigned' : 'Active'}</span>

      <div style="margin:16px 0 4px;display:flex;gap:8px;flex-wrap:wrap;">
        <button class="btn btn-secondary" id="editStaffToggleBtn">Edit</button>
        ${!isSelf ? `<button class="btn ${s.status === 'resigned' ? 'btn-secondary' : 'btn-danger'}" id="toggleStatusBtn">${s.status === 'resigned' ? 'Reinstate' : 'Mark as resigned'}</button>` : ''}
      </div>
      <form id="editStaffForm" style="display:none;margin-top:12px;">
        <div class="form-grid">
          <div class="field"><label>Email</label><input name="email" type="email" value="${esc(s.email)}"></div>
          <div class="field"><label>Role</label>
            <select name="role">
              <option value="doctor" ${s.role==='doctor'?'selected':''}>Doctor</option>
              <option value="admin" ${s.role==='admin'?'selected':''}>Admin</option>
            </select>
          </div>
        </div>
        <div class="form-actions">
          <button class="btn btn-primary" type="submit">Save changes</button>
          <span class="inline-msg" id="editStaffMsg"></span>
        </div>
      </form>

      <div style="margin-top:22px;border-top:1px solid var(--line);padding-top:16px;">
        <button class="btn btn-danger" id="deleteStaffBtn" ${isSelf ? 'disabled title="You cannot delete your own account"' : ''}>Delete this account</button>
      </div>
    `;

    document.getElementById('editStaffToggleBtn').onclick = ()=>{
      const f = document.getElementById('editStaffForm');
      f.style.display = f.style.display === 'none' ? 'block' : 'none';
    };
    document.getElementById('editStaffForm').addEventListener('submit', async (e)=>{
      e.preventDefault();
      const msg = document.getElementById('editStaffMsg');
      const fd = new FormData(e.target);
      const body = Object.fromEntries(fd.entries());
      try{
        const updated = await api(`/auth/staff/${s._id}`, { method:'PUT', body });
        msg.textContent = 'Saved.'; msg.className = 'inline-msg ok';
        toast('Staff account updated');
        loadStaffTable();
        openStaffDetail(updated._id);
      }catch(err){
        msg.textContent = err.message; msg.className = 'inline-msg err';
      }
    });

    if(!isSelf){
      document.getElementById('toggleStatusBtn').onclick = async ()=>{
        const nextStatus = s.status === 'resigned' ? 'active' : 'resigned';
        const verb = nextStatus === 'resigned' ? 'mark this account as resigned' : 'reinstate this account';
        if(!confirm(`Are you sure you want to ${verb}?`)) return;
        try{
          await api(`/auth/staff/${s._id}`, { method:'PUT', body: { status: nextStatus } });
          toast(nextStatus === 'resigned' ? 'Marked as resigned' : 'Account reinstated');
          loadStaffTable();
          openStaffDetail(s._id);
        }catch(err){ toast(err.message, true); }
      };
      document.getElementById('deleteStaffBtn').onclick = async ()=>{
        if(!confirm(`Delete ${s.username} (${s.role})? This cannot be undone.`)) return;
        try{
          await api(`/auth/staff/${s._id}`, { method:'DELETE' });
          toast('Staff account deleted');
          closeModal();
          loadStaffTable();
        }catch(err){ toast(err.message, true); }
      };
    }
  }catch(err){
    openModal(`<div class="empty-state">${esc(err.message)}</div>`);
  }
}