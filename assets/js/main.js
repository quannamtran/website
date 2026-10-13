// Augmenting Decision: small enhancements. Every page also works without JavaScript.
(function () {
  // Keep the copyright year current.
  var year = String(new Date().getFullYear());
  document.querySelectorAll('[data-year]').forEach(function (el) {
    el.textContent = year;
  });

  // Sign-up forms. Messages come from data-msg-* attributes so each page
  // speaks its own language. Until an email service is connected (the form
  // has no action="..." yet), visitors are told sign-ups are not open,
  // rather than their address being silently dropped.
  document.querySelectorAll('form[data-signup]').forEach(function (form) {
    var input = form.querySelector('input[type="email"]');
    var status = form.querySelector('.signup__status');

    function say(message, state) {
      status.textContent = message;
      form.setAttribute('data-state', state);
    }

    input.addEventListener('input', function () {
      if (form.getAttribute('data-state') === 'error') say('', '');
    });

    form.addEventListener('submit', function (event) {
      input.value = input.value.trim();
      if (!input.value || !input.checkValidity()) {
        event.preventDefault();
        say(form.getAttribute('data-msg-invalid'), 'error');
        input.focus();
        return;
      }
      if (!form.hasAttribute('action')) {
        event.preventDefault();
        say(form.getAttribute('data-msg-closed'), 'info');
      }
      // Otherwise the browser sends the form to the email service as usual.
    });
  });
})();
