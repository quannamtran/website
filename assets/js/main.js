// Augmenting Decision: small enhancements. Every page also works without JavaScript.
(function () {
  // Where sign-ups are sent: the Google Apps Script web app that writes them
  // to a private Google Sheet (see tools/google-sheet-signup.gs and the README).
  // While empty, visitors are told sign-ups are not open yet.
  var SIGNUP_ENDPOINT = 'https://script.google.com/macros/s/AKfycbxl2H7htlZjt_XDHzmIW4KdjfJmOIG5cHQ7HnBYwQHobIWZou4OccXYRyc3EAYsZNXD/exec';

  // Keep the copyright year current.
  var year = String(new Date().getFullYear());
  document.querySelectorAll('[data-year]').forEach(function (el) {
    el.textContent = year;
  });

  // Sign-up forms. Messages come from data-msg-* attributes so each page
  // speaks its own language.
  document.querySelectorAll('form[data-signup]').forEach(function (form) {
    var input = form.querySelector('input[type="email"]');
    var trap = form.querySelector('input[name="website"]');
    var button = form.querySelector('button[type="submit"]');
    var status = form.querySelector('.signup__status');

    function say(message, state) {
      status.textContent = message;
      form.setAttribute('data-state', state);
    }

    input.addEventListener('input', function () {
      if (form.getAttribute('data-state') === 'error') say('', '');
    });

    form.addEventListener('submit', function (event) {
      event.preventDefault();
      input.value = input.value.trim();
      if (!input.value || !input.checkValidity()) {
        say(form.getAttribute('data-msg-invalid'), 'error');
        input.focus();
        return;
      }
      if (!SIGNUP_ENDPOINT) {
        say(form.getAttribute('data-msg-closed'), 'info');
        return;
      }

      button.disabled = true;
      var body = new URLSearchParams({
        email: input.value,
        lang: document.documentElement.lang,
        page: location.pathname,
        website: trap ? trap.value : '',
      });
      // Google's script does not answer cross-site requests readably, so the
      // request is sent "no-cors": it arrives, but its reply cannot be read.
      fetch(SIGNUP_ENDPOINT, { method: 'POST', mode: 'no-cors', body: body })
        .then(function () {
          form.reset();
          say(form.getAttribute('data-msg-success'), 'success');
        })
        .catch(function () {
          say(form.getAttribute('data-msg-error'), 'error');
        })
        .then(function () {
          button.disabled = false;
        });
    });
  });
})();
