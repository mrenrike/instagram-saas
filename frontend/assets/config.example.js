// frontend/assets/config.js
// EDIT THIS FILE before uploading to Hostinger, then copy it to config.js.
// It is the ONLY file that needs to be changed for deployment configuration.
//
// NOTE: config.js is gitignored — only this example is committed. Nothing here is a
// secret: everything in this file is readable by anyone who loads the page. API keys,
// webhook secrets and admin tokens belong in the backend's environment, never here
// (item 1).
window.APP_CONFIG = {
  AGENCY_EMAIL: 'contato@suaagencia.com.br',
  AGENCY_LINK: 'https://suaagencia.com.br/diagnostico',
};

// Must be https:// — flow.js refuses a plain-http backend outside localhost (item 19).
window.BACKEND_URL = 'https://your-app.railway.app';
