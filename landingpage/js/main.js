/* ==========================================================================
   KYL Landingpage
   Vanilla JS, keine Abhaengigkeiten. Drei Bloecke: Menue, Formular,
   Jahreszahl. Die Seite animiert nichts von selbst. Was reagiert,
   reagiert auf eine Handlung.
   ========================================================================== */

document.addEventListener('DOMContentLoaded', function () {

  /* ------------------------------------------------------------------------
     1. Mobiles Menue
     ------------------------------------------------------------------------ */

  var toggle = document.querySelector('.menu-btn');
  var panel = document.getElementById('menuPanel');

  if (toggle && panel) {
    var setMenu = function (open) {
      toggle.setAttribute('aria-expanded', String(open));
      toggle.setAttribute('aria-label', open ? 'Menü schließen' : 'Menü öffnen');
      panel.classList.toggle('is-open', open);
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
      if (window.innerWidth >= 900) { setMenu(false); }
    });
  }

  /* ------------------------------------------------------------------------
     2. Kontaktformular
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
      formMessage.textContent = 'Anfrage notiert. Wir melden uns zurück, meistens am selben Tag.';
      form.reset();
    });
  }

  /* ------------------------------------------------------------------------
     3. Jahreszahl in der Fusszeile
     ------------------------------------------------------------------------ */

  var yearEl = document.getElementById('year');
  if (yearEl) { yearEl.textContent = String(new Date().getFullYear()); }

});
