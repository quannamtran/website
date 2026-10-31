// Augmenting Decision: small enhancements. Every page also works without JavaScript.
(function () {
  // Where sign-ups are sent: the Google Apps Script web app that writes them
  // to a private Google Sheet (see tools/google-sheet-signup.gs and the README).
  // While empty, visitors are told sign-ups are not open yet.
  var SIGNUP_ENDPOINT = 'https://script.google.com/macros/s/AKfycbxl2H7htlZjt_XDHzmIW4KdjfJmOIG5cHQ7HnBYwQHobIWZou4OccXYRyc3EAYsZNXD/exec';

  // Sticky header: a thin line and shadow appear once the page is scrolled.
  var header = document.querySelector('.site-header');
  function onScroll() {
    header.classList.toggle('is-scrolled', window.scrollY > 8);
  }
  window.addEventListener('scroll', onScroll, { passive: true });
  onScroll();

  // Menu button (phones): opens the dropdown with every link. It closes after a
  // link is chosen, on Escape, or when tapping outside.
  var toggle = document.querySelector('.menu-toggle');
  var menu = document.getElementById('site-menu');
  function setMenu(open) {
    menu.classList.toggle('is-open', open);
    toggle.setAttribute('aria-expanded', open ? 'true' : 'false');
  }
  toggle.addEventListener('click', function () {
    setMenu(toggle.getAttribute('aria-expanded') !== 'true');
  });
  menu.addEventListener('click', function (event) {
    if (event.target.closest('a')) setMenu(false);
  });
  document.addEventListener('keydown', function (event) {
    if (event.key === 'Escape' && menu.classList.contains('is-open')) {
      setMenu(false);
      toggle.focus();
    }
  });
  document.addEventListener('click', function (event) {
    if (menu.classList.contains('is-open') && !header.contains(event.target)) setMenu(false);
  });

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

  // Endorsement carousel: one quote at a time, moving on every 5 seconds on
  // every device. It holds still only after the pause button is pressed,
  // while it has keyboard focus, and while the tab is hidden. For people who
  // ask their system for reduced motion, quotes change without the fade (CSS).
  document.querySelectorAll('[data-carousel]').forEach(function (root) {
    var DELAY = 5000;
    var slides = [].slice.call(root.querySelectorAll('.praise__slide'));
    var box = root.querySelector('.praise__slides');
    var dotsBox = root.querySelector('.praise__dots');
    var toggle = root.querySelector('[data-carousel-toggle]');
    var current = 0;
    var timer = null;
    var paused = false;
    var focused = false;

    var dots = slides.map(function (slide, i) {
      var dot = document.createElement('button');
      dot.type = 'button';
      dot.className = 'praise__dot';
      dot.setAttribute('aria-controls', box.id);
      dot.setAttribute('aria-label', root.getAttribute('data-label-dot')
        .replace('%n', i + 1).replace('%total', slides.length));
      dot.addEventListener('click', function () { show(i); });
      dotsBox.appendChild(dot);
      return dot;
    });

    function show(index) {
      current = (index + slides.length) % slides.length;
      slides.forEach(function (slide, i) {
        slide.classList.toggle('is-active', i === current);
        slide.setAttribute('aria-hidden', i === current ? 'false' : 'true');
      });
      dots.forEach(function (dot, i) {
        dot.setAttribute('aria-current', i === current ? 'true' : 'false');
      });
      schedule();
    }

    // (Re)start the 5-second countdown, or stop it while the carousel should hold still.
    function schedule() {
      clearTimeout(timer);
      var moving = !paused && !focused && !document.hidden;
      if (moving) timer = setTimeout(function () { show(current + 1); }, DELAY);
      // Announce slide changes to screen readers only when they are not automatic.
      box.setAttribute('aria-live', moving ? 'off' : 'polite');
      root.setAttribute('data-paused', paused ? 'true' : 'false');
      toggle.setAttribute('aria-label', root.getAttribute(paused ? 'data-label-play' : 'data-label-pause'));
    }

    root.querySelector('[data-carousel-prev]').addEventListener('click', function () { show(current - 1); });
    root.querySelector('[data-carousel-next]').addEventListener('click', function () { show(current + 1); });
    toggle.addEventListener('click', function () { paused = !paused; schedule(); });

    root.addEventListener('focusin', function (event) {
      // Keyboard focus pauses; a mouse click on a button does not.
      var keyboard = true;
      try { keyboard = event.target.matches(':focus-visible'); } catch (e) { /* older browsers */ }
      focused = keyboard;
      schedule();
    });
    root.addEventListener('focusout', function (event) {
      if (!root.contains(event.relatedTarget)) { focused = false; schedule(); }
    });
    document.addEventListener('visibilitychange', schedule);

    // Swipe left or right on touch screens.
    var startX = null;
    box.addEventListener('touchstart', function (event) { startX = event.touches[0].clientX; }, { passive: true });
    box.addEventListener('touchend', function (event) {
      if (startX === null) return;
      var dx = event.changedTouches[0].clientX - startX;
      startX = null;
      if (Math.abs(dx) > 40) show(current + (dx < 0 ? 1 : -1));
    });

    show(0);
  });

  // "Why it matters now": the two figures are drawn as they come into view.
  // Scroll progress (0 when the plate's top enters the bottom of the screen,
  // 1 once it has risen past the middle) sets the plate's --coin, --draw and
  // --after, which the stylesheet turns into the drawing. People who ask for
  // reduced motion get the finished charts straight away.
  var calm = window.matchMedia('(prefers-reduced-motion: reduce)');
  document.querySelectorAll('[data-scene]').forEach(function (scene) {
    var plate = scene.querySelector('[data-plate]');
    var last = null;

    // How far between two points of the progress we are, eased, from 0 to 1.
    function ease(p, from, to) {
      var t = Math.min(1, Math.max(0, (p - from) / (to - from)));
      return t * t * (3 - 2 * t);
    }
    function progress() {
      var vh = window.innerHeight;
      return Math.min(1, Math.max(0, (vh * 0.9 - plate.getBoundingClientRect().top) / (vh * 0.5)));
    }
    function tick() {
      var p = calm.matches ? 1 : progress();
      if (p === last) return;
      last = p;
      plate.style.setProperty('--coin', ease(p, 0.1, 0.35).toFixed(3));
      plate.style.setProperty('--draw', ease(p, 0.3, 0.7).toFixed(3));
      plate.style.setProperty('--after', ease(p, 0.65, 0.95).toFixed(3));
    }
    window.addEventListener('scroll', function () { window.requestAnimationFrame(tick); }, { passive: true });
    window.addEventListener('resize', tick);
    if (calm.addEventListener) calm.addEventListener('change', function () { last = null; tick(); });
    tick();
  });
})();
