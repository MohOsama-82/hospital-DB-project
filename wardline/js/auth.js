/* =========================================================
   LOGIN
   ========================================================= */
document.getElementById('loginForm').addEventListener('submit', async (e)=>{
  e.preventDefault();
  const errBox = document.getElementById('loginErr');
  errBox.className = 'err-msg';
  const btn = document.getElementById('loginBtn');
  btn.disabled = true; btn.textContent = 'Signing in…';

  state.apiBase = document.getElementById('apiBase').value.trim().replace(/\/$/,'');
  const username = document.getElementById('loginUsername').value.trim();
  const password = document.getElementById('loginPassword').value;

  try{
    const data = await api('/auth/login', { method:'POST', body:{ username, password } });
    const payload = decodeJwt(data.access_token);
    if(!payload || !payload.role) throw new Error('Logged in, but could not read role from token.');

    if(state.selectedPortal && payload.role !== state.selectedPortal){
      throw new Error(`That account is a ${payload.role} account. Please use the ${payload.role} portal to sign in.`);
    }

    state.token = data.access_token;
    state.role = payload.role;
    state.userId = payload.sub;
    state.username = username;

    if(state.role === 'patient'){
      state.myPatient = await api('/patients/me');
    }

    enterApp();
  }catch(err){
    errBox.textContent = err.message;
    errBox.className = 'err-msg show';
  }finally{
    btn.disabled = false; btn.textContent = 'Sign in';
  }
});

document.getElementById('logoutBtn').addEventListener('click', ()=>{
  state.token = null; state.role = null; state.userId = null; state.myPatient = null;
  document.getElementById('app').classList.remove('active');
  document.getElementById('loginPassword').value = '';
  stopAppointmentBadgePolling();
  showFrontPage();
});