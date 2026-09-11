/* ==========================================================================
   KYL Landingpage
   Vanilla JS, keine Abhaengigkeiten. Vier Bloecke: Menue, Karussell,
   Formular, Jahreszahl. Bewegung passiert nur auf eine Handlung hin,
   der Aufbau des Heros steckt komplett in CSS.
   ========================================================================== */

document.documentElement.classList.remove('no-js');

document.addEventListener('DOMContentLoaded', function () {

  /* ------------------------------------------------------------------------
     1. Mobiles Menue
     ------------------------------------------------------------------------ */

  var toggle = document.querySelector('.nav-toggle');
  var panel = document.getElementById('navPanel');

  if (toggle && panel) {
    var setMenu = function (open) {
      toggle.setAttribute('aria-expanded', String(open));
      toggle.setAttribute('aria-label', open ? 'Menü schließen' : 'Menü öffnen');
      panel.classList.toggle('is-open', open);
      document.body.style.overflow = open ? 'hidden' : '';
    };

    toggle.addEventListener('click', function () {
      setMenu(toggle.getAttribute('aria-expanded') !== 'true');
    });

    panel.querySelectorAll('a').forEach(function (link) {
      link.addEventListener('click', function () { setMenu(false); });
    });

    document.addEventListener('keydown', function (e) {
      if (e.key === 'Escape' && toggle.getAttribute('aria-expanded') === 'true') {
        setMenu(false);
        toggle.focus();
      }
    });

    window.addEventListener('resize', function () {
      if (window.innerWidth >= 1000) { setMenu(false); }
    });
  }

  /* ------------------------------------------------------------------------
     2. Karussell der Arbeiten
     Das Scrollen macht der Browser (scroll-snap). Hier haengen nur die
     Pfeiltasten, die Punkte und der Zustand der Knoepfe dran.
     ------------------------------------------------------------------------ */

  var rail = document.getElementById('workRail');
  var dots = document.getElementById('railDots');
  var prev = document.querySelector('[data-rail-prev]');
  var next = document.querySelector('[data-rail-next]');

  if (rail && prev && next) {
    var tiles = Array.prototype.slice.call(rail.children);

    var step = function () {
      // Eine Kachel plus Abstand, aus dem echten Layout gelesen
      if (tiles.length < 2) { return rail.clientWidth; }
      return tiles[1].offsetLeft - tiles[0].offsetLeft;
    };

    var currentIndex = function () {
      return Math.round(rail.scrollLeft / step());
    };

    var scrollToIndex = function (i) {
      var max = tiles.length - 1;
      var target = Math.max(0, Math.min(max, i));
      rail.scrollTo({ left: tiles[target].offsetLeft - rail.offsetLeft, behavior: 'smooth' });
    };

    prev.addEventListener('click', function () { scrollToIndex(currentIndex() - 1); });
    next.addEventListener('click', function () { scrollToIndex(currentIndex() + 1); });

    // Punkte aufbauen, einer je Kachel
    if (dots) {
      tiles.forEach(function (_, i) {
        var dot = document.createElement('span');
        dot.className = 'rail-dot' + (i === 0 ? ' is-current' : '');
        dots.appendChild(dot);
      });
    }

    var sync = function () {
      var i = currentIndex();
      // Knoepfe abschalten, wenn es in die Richtung nicht weitergeht
      prev.disabled = rail.scrollLeft <= 2;
      next.disabled = rail.scrollLeft >= rail.scrollWidth - rail.clientWidth - 2;
      if (dots) {
        Array.prototype.forEach.call(dots.children, function (dot, index) {
          dot.classList.toggle('is-current', index === i);
        });
      }
    };

    var ticking = false;
    rail.addEventListener('scroll', function () {
      if (!ticking) {
        window.requestAnimationFrame(function () { sync(); ticking = false; });
        ticking = true;
      }
    }, { passive: true });

    // Pfeiltasten, wenn das Karussell den Fokus hat
    rail.addEventListener('keydown', function (e) {
      if (e.key === 'ArrowRight') { e.preventDefault(); scrollToIndex(currentIndex() + 1); }
      if (e.key === 'ArrowLeft')  { e.preventDefault(); scrollToIndex(currentIndex() - 1); }
    });

    window.addEventListener('resize', sync);
    sync();
  }

  /* ------------------------------------------------------------------------
     3. Kontaktformular
     ------------------------------------------------------------------------ */

  var form = document.getElementById('contactForm');
  var formMessage = document.getElementById('formMessage');

  if (form && formMessage) {
    var emailPattern = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

    var setFieldError = function (input, message) {
      var field = input.closest('.field');
      var errorEl = field ? field.querySelector('.field-error') : null;
      if (field) { field.classList.toggle('has-error', Boolean(message)); }
      if (errorEl) { errorEl.textContent = message || ''; }
      input.setAttribute('aria-invalid', message ? 'true' : 'false');
    };

    form.querySelectorAll('input, textarea').forEach(function (input) {
      input.addEventListener('input', function () { setFieldError(input, ''); });
    });

    form.addEventListener('submit', function (e) {
      e.preventDefault();

      var name = form.elements.name;
      var email = form.elements.email;
      var message = form.elements.message;
      var firstInvalid = null;

      formMessage.className = 'form-message';
      formMessage.textContent = '';

      if (!name.value.trim()) {
        setFieldError(name, 'Bitte geben Sie Ihren Namen an.');
        firstInvalid = firstInvalid || name;
      }
      if (!email.value.trim()) {
        setFieldError(email, 'Bitte geben Sie Ihre E-Mail-Adresse an.');
        firstInvalid = firstInvalid || email;
      } else if (!emailPattern.test(email.value.trim())) {
        setFieldError(email, 'Diese E-Mail-Adresse sieht nicht gültig aus.');
        firstInvalid = firstInvalid || email;
      }
      if (!message.value.trim()) {
        setFieldError(message, 'Bitte beschreiben Sie kurz das Objekt.');
        firstInvalid = firstInvalid || message;
      }

      if (firstInvalid) {
        formMessage.classList.add('is-error');
        formMessage.textContent = 'Bitte prüfen Sie die markierten Felder.';
        firstInvalid.focus();
        return;
      }

      // TODO (Backend): Das Formular versendet noch nichts. Für den Live-Betrieb
      // hier ein fetch() an Formspree, Netlify Forms oder ein eigenes Backend
      // ergänzen. Bis dahin läuft die Anfrage über Telefon und E-Mail daneben.
      formMessage.classList.add('is-success');
      formMessage.textContent = 'Danke, Ihre Anfrage ist notiert. Wir melden uns zeitnah.';
      form.reset();
    });
  }

  /* ------------------------------------------------------------------------
     4. Jahreszahl in der Fusszeile
     ------------------------------------------------------------------------ */

  var yearEl = document.getElementById('year');
  if (yearEl) { yearEl.textContent = String(new Date().getFullYear()); }

});
