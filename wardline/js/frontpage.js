/* =========================================================
   FRONT PAGE / PORTAL SELECTION
   ========================================================= */
const PORTAL_COPY = {
  patient: { eyebrow: 'PATIENT PORTAL', tagline: 'Your records,<br>always in view.' },
  doctor:  { eyebrow: 'DOCTOR PORTAL',  tagline: 'Every ward,<br>one continuous record.' },
  admin:   { eyebrow: 'ADMIN PORTAL',   tagline: 'Run the ward,<br>from one place.' },
};

function selectPortal(portal){
  state.selectedPortal = portal;
  const copy = PORTAL_COPY[portal] || PORTAL_COPY.doctor;
  document.getElementById('loginEyebrow').textContent = copy.eyebrow;
  document.getElementById('railTagline').innerHTML = copy.tagline;
  document.getElementById('frontPage').style.display = 'none';
  document.getElementById('loginScreen').style.display = 'grid';
  document.getElementById('loginUsername').focus();
}

function showFrontPage(){
  document.getElementById('loginScreen').style.display = 'none';
  document.getElementById('guestBookingScreen').style.display = 'none';
  document.getElementById('frontPage').style.display = 'flex';
  document.getElementById('loginForm').reset();
  document.getElementById('loginErr').className = 'err-msg';
}

function openGuestBooking(){
  document.getElementById('frontPage').style.display = 'none';
  document.getElementById('guestBookingScreen').style.display = 'block';
  renderGuestBookingForm();
}

function closeGuestBooking(){
  document.getElementById('guestBookingScreen').style.display = 'none';
  document.getElementById('frontPage').style.display = 'flex';
}