/* ==========================================================================
   Alex Morgan — Software Engineer Portfolio
   Main JavaScript
   ========================================================================== */

(function () {
  'use strict';

  /* ---------------- Theme Toggle ---------------- */
  const THEME_KEY = 'portfolio-theme';

  function applyTheme(theme) {
    document.documentElement.setAttribute('data-theme', theme);
    const toggleBtns = document.querySelectorAll('.theme-toggle');
    toggleBtns.forEach((btn) => {
      btn.textContent = theme === 'dark' ? '🌙' : '☀️';
    });
  }

  function initTheme() {
    const saved = localStorage.getItem(THEME_KEY) ||
      (window.matchMedia('(prefers-color-scheme: light)').matches ? 'light' : 'dark');
    applyTheme(saved);

    document.querySelectorAll('.theme-toggle').forEach((btn) => {
      btn.addEventListener('click', () => {
        const current = document.documentElement.getAttribute('data-theme');
        const next = current === 'dark' ? 'light' : 'dark';
        applyTheme(next);
        localStorage.setItem(THEME_KEY, next);
      });
    });
  }

  /* ---------------- Mobile Nav ---------------- */
  function initNav() {
    const toggle = document.querySelector('.nav-toggle');
    const links = document.querySelector('.nav-links');
    if (!toggle || !links) return;

    toggle.addEventListener('click', () => {
      links.classList.toggle('open');
    });

    links.querySelectorAll('a').forEach((a) => {
      a.addEventListener('click', () => links.classList.remove('open'));
    });

    // Highlight active page
    const current = window.location.pathname.split('/').pop() || 'index.html';
    links.querySelectorAll('a').forEach((a) => {
      const href = a.getAttribute('href');
      if (href === current || (current === '' && href === 'index.html')) {
        a.classList.add('active');
      }
    });
  }

  /* ---------------- Scroll Reveal ---------------- */
  function initReveal() {
    const items = document.querySelectorAll('.reveal');
    if (!items.length) return;

    const observer = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          if (entry.isIntersecting) {
            entry.target.classList.add('in-view');
            observer.unobserve(entry.target);
          }
        });
      },
      { threshold: 0.15 }
    );

    items.forEach((item) => observer.observe(item));
  }

  /* ---------------- Navbar scroll shadow + back to top ---------------- */
  function initScrollEffects() {
    const navbar = document.querySelector('.navbar');
    const backToTop = document.querySelector('.back-to-top');

    window.addEventListener('scroll', () => {
      const scrolled = window.scrollY > 40;
      if (navbar) navbar.style.boxShadow = scrolled ? '0 6px 20px rgba(0,0,0,0.25)' : 'none';
      if (backToTop) backToTop.classList.toggle('show', window.scrollY > 500);
    });

    if (backToTop) {
      backToTop.addEventListener('click', () => {
        window.scrollTo({ top: 0, behavior: 'smooth' });
      });
    }
  }

  /* ---------------- Typing Effect (Home hero) ---------------- */
  function initTypedRole() {
    const el = document.getElementById('typed-role');
    if (!el) return;

    const roles = ['Software Engineer', 'Problem Solver', 'Open-Source Contributor'];
    let roleIndex = 0;
    let charIndex = 0;
    let deleting = false;

    function tick() {
      const current = roles[roleIndex];
      if (!deleting) {
        charIndex++;
        el.textContent = current.slice(0, charIndex);
        if (charIndex === current.length) {
          deleting = true;
          setTimeout(tick, 1400);
          return;
        }
      } else {
        charIndex--;
        el.textContent = current.slice(0, charIndex);
        if (charIndex === 0) {
          deleting = false;
          roleIndex = (roleIndex + 1) % roles.length;
        }
      }
      setTimeout(tick, deleting ? 45 : 90);
    }
    tick();
  }

  /* ---------------- Animated Counters (Home stats) ---------------- */
  function initCounters() {
    const counters = document.querySelectorAll('[data-counter]');
    if (!counters.length) return;

    const observer = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          if (!entry.isIntersecting) return;
          const el = entry.target;
          const target = parseFloat(el.getAttribute('data-counter'));
          const suffix = el.getAttribute('data-suffix') || '';
          let current = 0;
          const step = Math.max(target / 60, 0.1);
          const update = () => {
            current += step;
            if (current >= target) {
              el.textContent = target + suffix;
            } else {
              el.textContent = Math.floor(current) + suffix;
              requestAnimationFrame(update);
            }
          };
          update();
          observer.unobserve(el);
        });
      },
      { threshold: 0.4 }
    );

    counters.forEach((c) => observer.observe(c));
  }

  /* ---------------- Skill Bars (Skills page) ---------------- */
  function initSkillBars() {
    const bars = document.querySelectorAll('.skill-bar-fill');
    if (!bars.length) return;

    const observer = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          if (entry.isIntersecting) {
            const el = entry.target;
            el.style.width = el.getAttribute('data-level') + '%';
            observer.unobserve(el);
          }
        });
      },
      { threshold: 0.3 }
    );

    bars.forEach((bar) => observer.observe(bar));
  }

  /* ---------------- Tabs (About page) ---------------- */
  function initTabs() {
    const tabGroups = document.querySelectorAll('.tab-group');
    tabGroups.forEach((group) => {
      const buttons = group.querySelectorAll('.tab-btn');
      buttons.forEach((btn) => {
        btn.addEventListener('click', () => {
          const target = btn.getAttribute('data-tab');
          const panelContainer = document.querySelector(btn.getAttribute('data-target'));
          buttons.forEach((b) => b.classList.remove('active'));
          btn.classList.add('active');
          if (panelContainer) {
            panelContainer.querySelectorAll('.tab-panel').forEach((panel) => {
              panel.classList.toggle('active', panel.getAttribute('data-panel') === target);
            });
          }
        });
      });
    });
  }

  /* ---------------- Project Filtering ---------------- */
  function initProjectFilter() {
    const filterBtns = document.querySelectorAll('.filter-bar .tab-btn');
    const projects = document.querySelectorAll('.project-card');
    if (!filterBtns.length || !projects.length) return;

    filterBtns.forEach((btn) => {
      btn.addEventListener('click', () => {
        filterBtns.forEach((b) => b.classList.remove('active'));
        btn.classList.add('active');
        const filter = btn.getAttribute('data-filter');

        projects.forEach((card) => {
          const cats = (card.getAttribute('data-category') || '').split(' ');
          const show = filter === 'all' || cats.includes(filter);
          card.classList.toggle('hidden-project', !show);
        });
      });
    });
  }

  /* ---------------- Toast Notification ---------------- */
  function showToast(title, message, isError) {
    let toast = document.querySelector('.toast');
    if (!toast) {
      toast = document.createElement('div');
      toast.className = 'toast';
      document.body.appendChild(toast);
    }
    toast.classList.toggle('error', !!isError);
    toast.replaceChildren();
    const heading = document.createElement('strong');
    heading.textContent = title;

    const text = document.createElement('span');
    text.textContent = message;

    toast.append(heading, text);

    requestAnimationFrame(() => toast.classList.add('show'));
    clearTimeout(toast._timeout);
    toast._timeout = setTimeout(() => toast.classList.remove('show'), 5000);
  }

  /*----------------error handling for Django messages----------------*/
  document.addEventListener('DOMContentLoaded', () => {
    const djangoMessages = document.getElementById('django-messages');
    if (djangoMessages) {
      const messages = djangoMessages.querySelectorAll('div[data-message]');
      messages.forEach((msgDiv) => {
        const message = msgDiv.getAttribute('data-message');
        const tags = msgDiv.getAttribute('data-tags');
        const isError = tags && tags.includes('error');
        showToast(isError ? 'Error' : 'Info', message, isError);
      });
    }
  });

  /* ---------------- Contact Form Validation ---------------- */
  function initContactForm() {
    const form = document.getElementById('contact-form');
    if (!form) return;

    const fields = {
      name: { el: form.querySelector('#name'), validate: (v) => v.trim().length >= 2, msg: 'Please enter your full name.' },
      email: {
        el: form.querySelector('#email'),
        validate: (v) => /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(v.trim()),
        msg: 'Please enter a valid email address.',
      },
      subject: { el: form.querySelector('#subject'), validate: (v) => v.trim().length >= 3, msg: 'Please enter a subject.' },
      message: { el: form.querySelector('#message'), validate: (v) => v.trim().length >= 10, msg: 'Message should be at least 10 characters.' },
    };

    function validateField(key) {
      const field = fields[key];
      if (!field || !field.el) return true;
      const group = field.el.closest('.form-group');
      const valid = field.validate(field.el.value);
      if (group) group.classList.toggle('invalid', !valid);
      return valid;
    }

    Object.keys(fields).forEach((key) => {
      const field = fields[key];
      if (field.el) {
        field.el.addEventListener('blur', () => validateField(key));
        field.el.addEventListener('input', () => {
          if (field.el.closest('.form-group').classList.contains('invalid')) {
            validateField(key);
          }
        });
      }
    });

    form.addEventListener('submit', (e) => {
      
      let allValid = true;
      Object.keys(fields).forEach((key) => {
        if (!validateField(key)) allValid = false;
      });

      if (!allValid) {
        e.preventDefault();
        showToast('Oops!', 'Please fix the highlighted fields.', true);
        return;
      }
      else {
        const submitBtn = document.getElementById('btn-text')
        const loader = document.getElementById('loader');
        const originalText = submitBtn.textContent;
        submitBtn.disabled = true;
        submitBtn.textContent = 'Sending...';
        loader.hidden = false;

        /* Simulate async submission (no backend — static front-end only)
        setTimeout(() => {
          submitBtn.disabled = false;
          submitBtn.textContent = originalText;
          form.reset();
          showToast('Message sent!', "Thanks for reaching out — I'll reply within 24 hours.");
        }, 1200);*/
      }
    });
  }

  /* ---------------- Current year in footer ---------------- */
  function initYear() {
    document.querySelectorAll('.current-year').forEach((el) => {
      el.textContent = new Date().getFullYear();
    });
  }

  /* ---------------- Init ---------------- */
  document.addEventListener('DOMContentLoaded', () => {
    initTheme();
    initNav();
    initReveal();
    initScrollEffects();
    initTypedRole();
    initCounters();
    initSkillBars();
    initTabs();
    initProjectFilter();
    initContactForm();
    initYear();
  });
})();
