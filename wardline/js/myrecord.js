/* =========================================================
   PATIENT — OWN RECORD / OWN FILES
   ========================================================= */
async function renderMyRecordView(body){
  try{
    const p = state.myPatient || await api('/patients/me');
    state.myPatient = p;
    body.innerHTML = `<div class="card"><div class="patient-detail">
      ${detailField('Name', p.name)}
      ${detailField('Username', p.username)}
      ${detailField('Age', p.age)}
      ${detailField('Blood group', p.blood_group)}
      ${detailField('Contact', p.contact)}
      ${detailField('Relative contact', p.relative_contact)}
      ${detailField('Email', p.email)}
    </div></div>`;
  }catch(err){
    body.innerHTML = `<div class="empty-state">${esc(err.message)}</div>`;
  }
}

async function renderMyFilesView(body){
  body.innerHTML = '<div class="card"><div id="myFilesWrap"><div class="empty-state">Loading…</div></div></div>';
  try{
    const p = state.myPatient || await api('/patients/me');
    state.myPatient = p;
    const wrap = document.getElementById('myFilesWrap');
    const files = await api(`/patients/${p._id}/files`);
    if(!files.length){ wrap.innerHTML = '<div class="empty-state">No files have been uploaded for you yet.</div>'; return; }
    wrap.innerHTML = files.map(f => `
      <div class="file-row">
        <div>
          <div class="file-name">${esc(f.filename)}</div>
          <div class="file-meta">${esc(f.content_type||'')} · ${(f.length/1024).toFixed(1)} KB</div>
        </div>
        <button class="btn btn-secondary" onclick="downloadFile('${p._id}','${f.file_id}')">Download</button>
      </div>
    `).join('');
  }catch(err){
    body.innerHTML = `<div class="empty-state">${esc(err.message)}</div>`;
  }
}
