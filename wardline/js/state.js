/* =========================================================
   STATE  (kept in memory only — refreshing the page logs you out
   on purpose, since this never writes to localStorage/sessionStorage)
   ========================================================= */
const state = { token: null, role: null, userId: null, username: null, apiBase: '', myPatient: null, selectedPortal: null };

/* When this file is served BY the FastAPI app itself (same origin, e.g. after
   deployment), the API lives at <this origin>/api automatically - no editing
   needed. When opened locally as a plain file (file://) or from a different
   origin, it falls back to the visible "API server address" field so you can
   type your own, e.g. http://127.0.0.1:8000/api. */
(function setDefaultApiBase(){
  const sameOriginGuess = (location.protocol === 'http:' || location.protocol === 'https:')
    ? location.origin + '/api'
    : 'http://127.0.0.1:8000/api';
  document.getElementById('apiBase').value = sameOriginGuess;
  state.apiBase = sameOriginGuess;
})();