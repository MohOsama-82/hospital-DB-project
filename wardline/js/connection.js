/* =========================================================
   CONNECTION CHECK (login screen)
   ========================================================= */
async function checkConnection(){
  const dot = document.getElementById('connDot');
  const label = document.getElementById('connLabel');
  const base = document.getElementById('apiBase').value.replace(/\/api\/?$/,'');
  try{
    const res = await fetch(base + '/');
    if(res.ok){ dot.className='pulse-dot live'; label.textContent='API server reachable'; }
    else throw new Error();
  }catch(e){
    dot.className='pulse-dot down'; label.textContent='cannot reach API — check Base URL / server';
  }
}
document.getElementById('apiBase').addEventListener('change', checkConnection);
checkConnection();

