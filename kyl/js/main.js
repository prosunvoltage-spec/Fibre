/* ==========================================================================
   KYL Facility Management & Services — Website JavaScript
   Vanilla JS, keine Abhaengigkeiten. Vier getrennte Bloecke:
   Nav-Scroll-State, Mobile-Menue, Scroll-Reveal, Formular-Validierung.
   ========================================================================== */

// Signalisiert dem CSS, dass JS laeuft (Reveal-Elemente duerfen versteckt starten)
document.documentElement.classList.remove('no-js');

document.addEventListener('DOMContentLoaded', function () {

  /* ------------------------------------------------------------------------
     1. Navigation: heller Balken, beim Scrollen Linie und leichter Schatten
     ------------------------------------------------------------------------ */

  var header = document.querySelector('.site-header');

  if (header) {
    var ticking = false;

    var updateHeader = function () {
      header.classList.toggle('site-header--scrolled', window.scrollY > 40);
      ticking = false;
    };

    window.addEventListener('scroll', function () {
      if (!ticking) {
        window.requestAnimationFrame(updateHeader);
        ticking = true;
      }
    }, { passive: true });

    updateHeader(); // Startzustand, z.B. bei Reload mitten auf der Seite
  }

  /* ------------------------------------------------------------------------
     2. Mobiles Menue
     ------------------------------------------------------------------------ */

  var navToggle = document.querySelector('.nav-toggle');
  var navMobile = document.querySelector('.nav-mobile');

  if (navToggle && navMobile) {
    var setMenu = function (open) {
      navToggle.setAttribute('aria-expanded', String(open));
      navToggle.setAttribute('aria-label', open ? 'Menü schließen' : 'Menü öffnen');
      navMobile.classList.toggle('is-open', open);
      // Offenes Overlay bekommt dieselbe Abgrenzung wie die gescrollte Navi
      if (header) {
        header.classList.toggle('site-header--scrolled', open || window.scrollY > 40);
      }
      // Hintergrund nicht mitscrollen lassen, solange das Overlay offen ist
      document.body.style.overflow = open ? 'hidden' : '';
    };

    navToggle.addEventListener('click', function () {
      setMenu(navToggle.getAttribute('aria-expanded') !== 'true');
    });

    // Nach der Auswahl eines Links schliessen
    navMobile.querySelectorAll('a').forEach(function (link) {
      link.addEventListener('click', function () { setMenu(false); });
    });

    // Escape schliesst und gibt den Fokus zurueck
    document.addEventListener('keydown', function (e) {
      if (e.key === 'Escape' && navToggle.getAttribute('aria-expanded') === 'true') {
        setMenu(false);
        navToggle.focus();
      }
    });

    // Beim Wechsel auf Desktop-Breite aufraeumen
    window.addEventListener('resize', function () {
      if (window.innerWidth >= 1000) { setMenu(false); }
    });
  }

  /* ------------------------------------------------------------------------
     3. Lesestand
     Der Kopf nennt den Abschnitt, in dem man steht, und zeigt an seiner
     Unterkante den Lesefortschritt. Beides Orientierung, keine Zierde.
     ------------------------------------------------------------------------ */

  var kolumnentitel = document.getElementById('runningHead');
  var balken = document.getElementById('readBar');

  if (kolumnentitel && 'IntersectionObserver' in window) {
    var benennung = {
      services: 'Leistungen',
      projekte: 'Arbeiten',
      'ueber-uns': 'Über uns',
      kontakt: 'Kontakt'
    };

    var offen = {};

    var navLinks = document.querySelectorAll('.nav-links a');

    var setzeTitel = function () {
      var id = Object.keys(benennung).filter(function (k) { return offen[k]; })[0];
      kolumnentitel.textContent = id ? benennung[id] : '';
      kolumnentitel.classList.toggle('is-visible', Boolean(id));

      // Die Navigation zeigt denselben Abschnitt, sonst widersprechen
      // sich zwei Anzeigen auf demselben Balken.
      var ziel = id ? '#' + id : '#top';
      navLinks.forEach(function (a) {
        var ist = a.getAttribute('href') === ziel;
        a.classList.toggle('is-active', ist);
        if (ist) { a.setAttribute('aria-current', 'true'); }
        else { a.removeAttribute('aria-current'); }
      });
    };

    var titelBeobachter = new IntersectionObserver(function (eintraege) {
      eintraege.forEach(function (e) { offen[e.target.id] = e.isIntersecting; });
      setzeTitel();
    }, { rootMargin: '-25% 0px -65% 0px' });

    Object.keys(benennung).forEach(function (id) {
      var el = document.getElementById(id);
      if (el) { titelBeobachter.observe(el); }
    });
  }

  if (balken) {
    var balkenLaeuft = false;

    var zeichneBalken = function () {
      var hoehe = document.documentElement.scrollHeight - window.innerHeight;
      var anteil = hoehe > 0 ? Math.min(1, Math.max(0, window.scrollY / hoehe)) : 0;
      balken.style.transform = 'scaleX(' + anteil.toFixed(4) + ')';
      balkenLaeuft = false;
    };

    window.addEventListener('scroll', function () {
      if (!balkenLaeuft) {
        window.requestAnimationFrame(zeichneBalken);
        balkenLaeuft = true;
      }
    }, { passive: true });

    window.addEventListener('resize', zeichneBalken);
    zeichneBalken();
  }

  /* ------------------------------------------------------------------------
     4. Bewegung
     Die einzige nicht ausgeloeste Bewegung ist der Aufbau des Heros beim
     Laden. Sie steckt komplett in CSS, hier ist nichts zu steuern —
     prefers-reduced-motion schaltet sie im Stylesheet ab.
     ------------------------------------------------------------------------ */

  /* ------------------------------------------------------------------------
     5. Kontaktformular
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

    // Fehler verschwindet, sobald der Nutzer korrigiert
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
        setFieldError(message, 'Bitte beschreiben Sie kurz Ihr Anliegen.');
        firstInvalid = firstInvalid || message;
      }

      if (firstInvalid) {
        formMessage.classList.add('is-error');
        formMessage.textContent = 'Bitte prüfen Sie die markierten Felder.';
        firstInvalid.focus();
        return;
      }

      // TODO (Backend): Das Formular versendet aktuell nichts. Für den Live-Betrieb
      // hier ein fetch() an ein Backend, Formspree oder Netlify Forms ergänzen, z.B.:
      //
      //   fetch('https://formspree.io/f/XXXXXXX', {
      //     method: 'POST',
      //     headers: { 'Accept': 'application/json' },
      //     body: new FormData(form)
      //   }).then(...)
      //
      // Bis dahin läuft die Anfrage über den E-Mail-Link daneben.
      formMessage.classList.add('is-success');
      formMessage.textContent =
        'Vielen Dank für Ihre Anfrage! Wir melden uns zeitnah bei Ihnen.';
      form.reset();
    });
  }

  /* ------------------------------------------------------------------------
     6. Jahreszahl im Footer aktuell halten
     ------------------------------------------------------------------------ */

  var yearEl = document.getElementById('year');
  if (yearEl) { yearEl.textContent = String(new Date().getFullYear()); }

});
