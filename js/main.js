// ============================================
// Musterbau GmbH – Website JavaScript
// ============================================

document.addEventListener('DOMContentLoaded', function () {

  // --- Mobile Navigation Toggle ---
  const navToggle = document.querySelector('.nav-toggle');
  const navLinks = document.querySelector('.nav-links');

  if (navToggle && navLinks) {
    navToggle.addEventListener('click', function () {
      navLinks.classList.toggle('open');
    });

    // Close menu when clicking a link
    navLinks.querySelectorAll('a').forEach(link => {
      link.addEventListener('click', () => {
        navLinks.classList.remove('open');
      });
    });
  }

  // --- Project Filter (only on Referenzen page) ---
  const filterButtons = document.querySelectorAll('.filter-btn');
  const projectCards = document.querySelectorAll('.project-card');

  if (filterButtons.length && projectCards.length) {
    filterButtons.forEach(btn => {
      btn.addEventListener('click', function () {
        const filter = this.dataset.filter;

        filterButtons.forEach(b => b.classList.remove('active'));
        this.classList.add('active');

        projectCards.forEach(card => {
          if (filter === 'all' || card.dataset.category === filter) {
            card.style.display = '';
          } else {
            card.style.display = 'none';
          }
        });
      });
    });
  }

  // --- Contact Form Validation ---
  const contactForm = document.getElementById('contactForm');
  const formMessage = document.getElementById('formMessage');

  if (contactForm) {
    contactForm.addEventListener('submit', function (e) {
      e.preventDefault();

      const name = contactForm.querySelector('[name="name"]').value.trim();
      const email = contactForm.querySelector('[name="email"]').value.trim();
      const message = contactForm.querySelector('[name="message"]').value.trim();

      formMessage.className = 'form-message';
      formMessage.textContent = '';

      if (!name || !email || !message) {
        formMessage.classList.add('error');
        formMessage.textContent = 'Bitte füllen Sie alle Pflichtfelder aus.';
        return;
      }

      const emailPattern = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
      if (!emailPattern.test(email)) {
        formMessage.classList.add('error');
        formMessage.textContent = 'Bitte geben Sie eine gültige E-Mail-Adresse ein.';
        return;
      }

      // Success – in production this would submit to a backend
      formMessage.classList.add('success');
      formMessage.textContent = 'Vielen Dank für Ihre Anfrage! Wir melden uns innerhalb von 24 Stunden bei Ihnen.';
      contactForm.reset();
    });
  }

  // --- Set active nav link based on current page ---
  const currentPage = window.location.pathname.split('/').pop() || 'index.html';
  document.querySelectorAll('.nav-links a').forEach(link => {
    const href = link.getAttribute('href');
    if (href === currentPage) {
      link.classList.add('active');
    }
  });
});
