/* =========================================================
   HELPERS
   ========================================================= */
function toast(msg, isErr=false){
  const t = document.getElementById('toast');
  t.textContent = msg;
  t.className = 'toast show' + (isErr ? ' err' : '');
  clearTimeout(toast._t);
  toast._t = setTimeout(()=> t.className = 'toast', 3200);
}

function decodeJwt(token){
  try{
    const payload = token.split('.')[1].replace(/-/g,'+').replace(/_/g,'/');
    return JSON.parse(decodeURIComponent(atob(payload).split('').map(c =>
      '%' + ('00' + c.charCodeAt(0).toString(16)).slice(-2)).join('')));
  }catch(e){ return null; }
}

async function api(path, opts={}){
  const headers = opts.headers || {};
  if(state.token) headers['Authorization'] = 'Bearer ' + state.token;
  if(opts.body && !(opts.body instanceof FormData)){
    headers['Content-Type'] = 'application/json';
    opts.body = JSON.stringify(opts.body);
  }
  let res;
  try{
    res = await fetch(state.apiBase + path, {...opts, headers});
  }catch(e){
    throw new Error('Could not reach the API server. Check the server is running and the Base URL is correct.');
  }
  if(res.status === 204) return null;
  const isJson = (res.headers.get('content-type')||'').includes('application/json');
  const data = isJson ? await res.json().catch(()=>null) : null;
  if(!res.ok){
    const msg = (data && (data.detail || data.message)) || `Request failed (${res.status})`;
    throw new Error(typeof msg === 'string' ? msg : JSON.stringify(msg));
  }
  return data;
}

function esc(s){
  return String(s ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
}

function openModal(html){
  document.getElementById('modalContent').innerHTML = html;
  document.getElementById('modalBackdrop').classList.add('show');
}
function closeModal(){ document.getElementById('modalBackdrop').classList.remove('show'); }
document.getElementById('modalBackdrop').addEventListener('click', e=>{
  if(e.target.id === 'modalBackdrop') closeModal();
});

