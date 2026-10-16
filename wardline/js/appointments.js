/* =========================================================
   ADMIN / DOCTOR — APPOINTMENTS VIEW
   ========================================================= */

async function renderAppointmentsView(body){
  const isAdmin = state.role === 'admin';
  const today = new Date().toISOString().slice(0, 10);
  body.innerHTML = `
    <div class="card">
      <h3>Appointments</h3>
      <div class="field" style="max-width:220px;margin-bottom:14px;">
        <label>Date</label>
        <input type="date" id="apptDateFilter" value="${today}">
      </div>
      <div id="appointmentsTableWrap">${emptyStateHtml('Loading…')}</div>
    </div>
  `;

  document.getElementById('apptDateFilter').addEventListener('change', (e)=>{
    loadAppointmentsTable(e.target.value, isAdmin);
  });

  loadAppointmentsTable(today, isAdmin);

  // Opening this tab is the "read receipt" - clear the unseen badge.
  try{
    await api('/appointments/mark-seen', { method:'POST' });
    refreshAppointmentBadge();
  }catch(err){ /* non-critical - badge just won't clear this time */ }
}

function statusTagHtml(status){
  if(status === 'accepted') return '<span class="tag tag-active">Accepted</span>';
  return '<span class="tag tag-pending">Pending</span>';
}

async function loadAppointmentsTable(date, isAdmin){
  const wrap = document.getElementById('appointmentsTableWrap');
  wrap.innerHTML = emptyStateHtml('Loading…');
  try{
    const appts = await api(`/appointments/?appointment_date=${encodeURIComponent(date)}`);
    if(!appts.length){ wrap.innerHTML = emptyStateHtml('No appointments on this date.'); return; }
    // Admin is view-only here by design - no Accept/Cancel column at all.
    // Only the owning Doctor can act on their own appointments.
    wrap.innerHTML = `<table><thead><tr>
        <th>Time</th><th>Token</th><th>Patient</th><th>Contact</th><th>Email</th><th>Type</th>${isAdmin ? '<th>Doctor</th>' : ''}<th>Status</th>${isAdmin ? '' : '<th></th>'}
      </tr></thead><tbody>
      ${appts.map(a => `<tr>
        <td class="mono">${esc(a.appointment_time)}</td>
        <td class="mono">#${esc(String(a.token_number))}</td>
        <td>${esc(a.name)}</td>
        <td>${esc(a.contact)}</td>
        <td>${esc(a.email || '—')}</td>
        <td>${a.is_guest ? 'New patient' : 'Registered'}</td>
        ${isAdmin ? `<td>${esc(a.doctor_username || a.doctor_id)}</td>` : ''}
        <td>${statusTagHtml(a.status)}</td>
        ${isAdmin ? '' : `<td class="row-actions">
          ${a.status === 'booked' ? `<button class="btn btn-secondary" onclick="acceptAppointmentRow('${a._id}','${date}')">Accept</button>` : ''}
          <button class="btn btn-danger" onclick="cancelAppointmentRow('${a._id}','${date}')">Cancel</button>
        </td>`}
      </tr>`).join('')}
    </tbody></table>`;
  }catch(err){
    wrap.innerHTML = `<div class="empty-state">${esc(err.message)}</div>`;
  }
}

async function acceptAppointmentRow(appointmentId, date){
  try{
    await api(`/appointments/${appointmentId}/accept`, { method:'POST' });
    toast('Appointment accepted');
    loadAppointmentsTable(date, false);
  }catch(err){ toast(err.message, true); }
}

async function cancelAppointmentRow(appointmentId, date){
  if(!confirm('Cancel this appointment?')) return;
  try{
    await api(`/appointments/${appointmentId}`, { method:'DELETE' });
    toast('Appointment cancelled');
    loadAppointmentsTable(date, false);
  }catch(err){ toast(err.message, true); }
}