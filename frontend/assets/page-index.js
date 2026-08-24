// Landing page: build the OAuth entry link with the captured UTMs.
'use strict';
(function () {
  const params = new URLSearchParams(getUTMs());
  document.getElementById('cta-btn').href = `${BACKEND}/oauth/start?${params}`;
})();
