/* ==========================================================================
   KYL Landingpage
   Vanilla JS, keine Abhaengigkeiten. Vier Bloecke: Menue, Lesestand,
   Formular, Jahreszahl. Bewegung gibt es nur dort, wo sie sagt, an
   welcher Stelle des Dokuments man steht.
   ========================================================================== */

// Signalisiert dem Stylesheet, dass Skripte laufen. Ohne diese Zeile
// bleiben die Haekchen dauerhaft sichtbar, was ohne JS richtig ist.
document.documentElement.classList.remove('no-js');

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
     2. Lesestand
     Zwei Beobachter: einer setzt den aktiven Registerreiter, der andere
     hakt die Zeilen des Leistungsverzeichnisses ab, sobald sie die
     Lesemarke passiert haben. Beides einmalig und ohne Layoutverschiebung.
     ------------------------------------------------------------------------ */

  var hatBeobachter = 'IntersectionObserver' in window;

  // 2a. Aktiver Reiter
  var reiter = document.querySelectorAll('.register-tabs a');

  if (hatBeobachter && reiter.length) {
    var zuReiter = {};
    reiter.forEach(function (a) { zuReiter[a.getAttribute('href').slice(1)] = a; });

    var abschnitte = Object.keys(zuReiter)
      .map(function (id) { return document.getElementById(id); })
      .filter(Boolean);

    var sichtbar = {};

    var aktualisiere = function () {
      // Der oberste sichtbare Abschnitt gewinnt
      var aktiv = abschnitte.filter(function (s) { return sichtbar[s.id]; })[0];
      reiter.forEach(function (a) {
        var ist = aktiv && a.getAttribute('href') === '#' + aktiv.id;
        a.classList.toggle('is-current', Boolean(ist));
        if (ist) { a.setAttribute('aria-current', 'true'); }
        else { a.removeAttribute('aria-current'); }
      });
    };

    var abschnittBeobachter = new IntersectionObserver(function (eintraege) {
      eintraege.forEach(function (e) { sichtbar[e.target.id] = e.isIntersecting; });
      aktualisiere();
    }, { rootMargin: '-30% 0px -60% 0px' });

    abschnitte.forEach(function (s) { abschnittBeobachter.observe(s); });
  }

  // 2b. Zeilen abhaken
  var zeilen = document.querySelectorAll('.register tbody tr');

  if (hatBeobachter && zeilen.length) {
    var zeilenBeobachter = new IntersectionObserver(function (eintraege, beobachter) {
      eintraege.forEach(function (e) {
        if (!e.isIntersecting) { return; }
        var i = Array.prototype.indexOf.call(zeilen, e.target);
        // Leichter Versatz, damit es wie ein Durchgehen der Liste wirkt
        setTimeout(function () { e.target.classList.add('is-checked'); }, (i % 3) * 70);
        beobachter.unobserve(e.target);
      });
    }, { rootMargin: '0px 0px -25% 0px', threshold: 0.6 });

    zeilen.forEach(function (tr) { zeilenBeobachter.observe(tr); });
  } else {
    zeilen.forEach(function (tr) { tr.classList.add('is-checked'); });
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
      formMessage.textContent = 'Anfrage notiert. Wir melden uns zurück, meistens am selben Tag.';
      form.reset();
    });
  }

  /* ------------------------------------------------------------------------
     4. Jahreszahl in der Fusszeile
     ------------------------------------------------------------------------ */

  var yearEl = document.getElementById('year');
  if (yearEl) { yearEl.textContent = String(new Date().getFullYear()); }

});
