/* =========================================================
   APPOINTMENT BOOKING
   Shared between: guest (no-login) booking on the front page,
   and the logged-in patient's "Book Appointment" nav view.
   ========================================================= */

/* Renders a checkmark confirmation card into `containerEl`, replacing
   whatever form was in there. Used after both guest and patient booking. */
function renderBookingConfirmation(containerEl, appt, onBookAnother, backLabel, onBack){
  containerEl.innerHTML = `
    <div class="confirm-check">
      <svg viewBox="0 0 24 24"><path d="M4 12.5 L9.5 18 L20 6"/></svg>
    </div>
    <h3 class="confirm-title">Appointment confirmed</h3>
    <div class="confirm-details">
      <div class="kv"><label>Doctor</label><div>Dr. ${esc(appt.doctor_username || appt.doctor_id)}</div></div>
      <div class="kv"><label>Date</label><div>${esc(appt.appointment_date)}</div></div>
      <div class="kv"><label>Time</label><div>${esc(appt.appointment_time)}</div></div>
      <div class="kv"><label>Booked for</label><div>${esc(appt.name)}</div></div>
      ${appt.email ? `<div class="kv"><label>Email</label><div>${esc(appt.email)}</div></div>` : ''}
      <div class="kv"><label>Your token number</label><div>#${esc(String(appt.token_number))}</div></div>
    </div>
    <p class="inline-msg" style="text-align:center;">This time slot is shared - you'll be seen in token order, not necessarily right at ${esc(appt.appointment_time)}.</p>
    <div class="form-actions" style="margin-top:20px;">
      <button class="btn btn-primary" id="confirmBookAnotherBtn">Book another appointment</button>
      ${backLabel ? `<button type="button" class="btn btn-secondary" id="confirmBackBtn">${esc(backLabel)}</button>` : ''}
    </div>
  `;
  document.getElementById('confirmBookAnotherBtn').onclick = onBookAnother;
  if(backLabel){ document.getElementById('confirmBackBtn').onclick = onBack; }
}

async function fetchBookableDoctors(){
  return await api('/appointments/doctors');
}

function doctorOptionsHtml(doctors){
  if(!doctors.length) return '<option value="">No doctors available yet</option>';
  return '<option value="">Select a doctor…</option>' +
    doctors.map(d => `<option value="${esc(d.user_id)}">${esc(d.username)}</option>`).join('');
}

/* Returns [{date:'2026-08-14', label:'Today'}, {date:'2026-08-15', label:'Tomorrow'}].
   Booking is only ever open for these two dates. */
async function fetchBookableDates(){
  return await api('/appointments/available-dates');
}

function dateOptionsHtml(dates){
  return '<option value="">Select…</option>' +
    dates.map(d => `<option value="${esc(d.date)}">${esc(d.label)} (${esc(d.date)})</option>`).join('');
}

/* Renders the slot grid into `gridEl`, wiring clicks to set `hiddenInput`'s
   value. Re-fetches whenever doctor or date changes. Every slot is always
   bookable - a slot is a shared queue, not a single seat, so nothing is
   ever disabled. Each button shows how many patients are already queued
   and what token number booking it now would give you. */
async function loadSlotGrid(gridEl, hiddenInput, doctorId, date){
  hiddenInput.value = '';
  if(!doctorId || !date){
    gridEl.innerHTML = '<div class="empty-state">Pick a doctor and date to see open times.</div>';
    return;
  }
  gridEl.innerHTML = '<div class="empty-state">Loading times…</div>';
  try{
    const slots = await api(`/appointments/available-slots?doctor_id=${encodeURIComponent(doctorId)}&appointment_date=${encodeURIComponent(date)}`);
    if(!slots.length){ gridEl.innerHTML = '<div class="empty-state">No slots configured.</div>'; return; }
    gridEl.innerHTML = slots.map(s => `
      <button type="button" class="slot-btn" data-time="${s.time}">
        ${s.time}<span class="slot-count">${s.booked_count ? `${s.booked_count} booked · you'd be #${s.next_token}` : 'open'}</span>
      </button>
    `).join('');
    gridEl.querySelectorAll('.slot-btn').forEach(btn=>{
      btn.addEventListener('click', ()=>{
        gridEl.querySelectorAll('.slot-btn').forEach(b=>b.classList.remove('selected'));
        btn.classList.add('selected');
        hiddenInput.value = btn.dataset.time;
      });
    });
  }catch(err){
    gridEl.innerHTML = `<div class="empty-state">${esc(err.message)}</div>`;
  }
}

/* ---------- Guest (no-login) booking — front page ---------- */

function guestBookingFormHtml(){
  return `
    <form id="guestBookingForm">
      <div class="form-grid">
        <div class="field"><label>Full name</label><input name="name" required></div>
        <div class="field">
          <label>Gender</label>
          <select name="gender" required>
            <option value="">Select…</option>
            <option value="male">Male</option>
            <option value="female">Female</option>
            <option value="other">Other</option>
          </select>
        </div>
        <div class="field"><label>Contact number</label><input name="contact" required></div>
        <div class="field"><label>Email</label><input name="email" type="email" required></div>
        <div class="field">
          <label>Doctor</label>
          <select name="doctor_id" id="guestDoctorSelect" required><option value="">Loading doctors…</option></select>
        </div>
        <div class="field">
          <label>Date</label>
          <select name="appointment_date" id="guestDateInput" required><option value="">Loading dates…</option></select>
        </div>
      </div>
      <div class="field" style="margin-top:6px;">
        <label>Available times</label>
        <div id="guestSlotGrid" class="slot-grid"><div class="empty-state">Pick a doctor and date to see open times.</div></div>
        <input type="hidden" name="appointment_time" id="guestTimeInput">
      </div>
      <div class="form-actions">
        <button class="btn btn-primary" type="submit">Confirm appointment</button>
        <span class="inline-msg" id="guestBookingMsg"></span>
      </div>
    </form>
  `;
}

/* Renders a fresh guest booking form into #guestBookingCard and wires it up.
   Called on first open, and again after "book another appointment". */
async function renderGuestBookingForm(){
  const card = document.getElementById('guestBookingCard');
  card.innerHTML = guestBookingFormHtml();

  const doctorSelect = document.getElementById('guestDoctorSelect');
  const dateInput = document.getElementById('guestDateInput');
  const grid = document.getElementById('guestSlotGrid');
  const timeInput = document.getElementById('guestTimeInput');

  try{
    doctorSelect.innerHTML = doctorOptionsHtml(await fetchBookableDoctors());
  }catch(err){
    doctorSelect.innerHTML = '<option value="">Could not load doctors</option>';
  }
  try{
    dateInput.innerHTML = dateOptionsHtml(await fetchBookableDates());
  }catch(err){
    dateInput.innerHTML = '<option value="">Could not load dates</option>';
  }

  const refreshSlots = ()=> loadSlotGrid(grid, timeInput, doctorSelect.value, dateInput.value);
  doctorSelect.addEventListener('change', refreshSlots);
  dateInput.addEventListener('change', refreshSlots);

  document.getElementById('guestBookingForm').addEventListener('submit', async (e)=>{
    e.preventDefault();
    const msg = document.getElementById('guestBookingMsg');
    if(!timeInput.value){
      msg.textContent = 'Please pick an available time.'; msg.className = 'inline-msg err';
      return;
    }
    const fd = new FormData(e.target);
    const body = Object.fromEntries(fd.entries());
    try{
      const appt = await api('/appointments/guest', { method:'POST', body });
      renderBookingConfirmation(card, appt, renderGuestBookingForm, 'Back to portals', closeGuestBooking);
    }catch(err){
      msg.textContent = err.message; msg.className = 'inline-msg err';
      refreshSlots(); // in case the slot was taken in the meantime
    }
  });
}

/* ---------- Logged-in patient booking — nav view ---------- */

function patientBookingFormHtml(){
  return `
    <form id="patientBookingForm">
      <div class="form-grid">
        <div class="field">
          <label>Doctor</label>
          <select name="doctor_id" id="patientDoctorSelect" required><option value="">Loading doctors…</option></select>
        </div>
        <div class="field">
          <label>Date</label>
          <select name="appointment_date" id="patientDateInput" required><option value="">Loading dates…</option></select>
        </div>
      </div>
      <div class="field" style="margin-top:6px;">
        <label>Available times</label>
        <div id="patientSlotGrid" class="slot-grid"><div class="empty-state">Pick a doctor and date to see open times.</div></div>
        <input type="hidden" name="appointment_time" id="patientTimeInput">
      </div>
      <div class="form-actions">
        <button class="btn btn-primary" type="submit">Confirm appointment</button>
        <span class="inline-msg" id="patientBookingMsg"></span>
      </div>
    </form>
  `;
}

async function renderBookAppointmentView(body){
  body.innerHTML = `<div class="card" id="patientBookingCard" style="max-width:560px;"></div>`;
  await renderPatientBookingForm();
}

async function renderPatientBookingForm(){
  const card = document.getElementById('patientBookingCard');
  card.innerHTML = patientBookingFormHtml();

  const doctorSelect = document.getElementById('patientDoctorSelect');
  const dateInput = document.getElementById('patientDateInput');
  const grid = document.getElementById('patientSlotGrid');
  const timeInput = document.getElementById('patientTimeInput');

  try{
    doctorSelect.innerHTML = doctorOptionsHtml(await fetchBookableDoctors());
  }catch(err){
    doctorSelect.innerHTML = '<option value="">Could not load doctors</option>';
  }
  try{
    dateInput.innerHTML = dateOptionsHtml(await fetchBookableDates());
  }catch(err){
    dateInput.innerHTML = '<option value="">Could not load dates</option>';
  }

  const refreshSlots = ()=> loadSlotGrid(grid, timeInput, doctorSelect.value, dateInput.value);
  doctorSelect.addEventListener('change', refreshSlots);
  dateInput.addEventListener('change', refreshSlots);

  document.getElementById('patientBookingForm').addEventListener('submit', async (e)=>{
    e.preventDefault();
    const msg = document.getElementById('patientBookingMsg');
    if(!timeInput.value){
      msg.textContent = 'Please pick an available time.'; msg.className = 'inline-msg err';
      return;
    }
    const fd = new FormData(e.target);
    const reqBody = Object.fromEntries(fd.entries());
    try{
      const appt = await api('/appointments/', { method:'POST', body: reqBody });
      renderBookingConfirmation(card, appt, renderPatientBookingForm);
    }catch(err){
      msg.textContent = err.message; msg.className = 'inline-msg err';
      refreshSlots();
    }
  });
}