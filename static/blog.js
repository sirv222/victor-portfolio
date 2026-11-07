(function () {
  'use strict';

  function initTheme() {
    const THEME_KEY = 'portfolio-theme';
    const saved = localStorage.getItem(THEME_KEY) || 'dark';
    document.documentElement.setAttribute('data-theme', saved);

    document.querySelectorAll('.theme-toggle').forEach((button) => {
      button.textContent = saved === 'dark' ? '🌙' : '☀️';
      button.addEventListener('click', () => {
        const current = document.documentElement.getAttribute('data-theme') === 'dark' ? 'light' : 'dark';
        document.documentElement.setAttribute('data-theme', current);
        localStorage.setItem(THEME_KEY, current);
        button.textContent = current === 'dark' ? '🌙' : '☀️';
      });
    });
  }

  function initReveal() {
    const items = document.querySelectorAll('.reveal');
    if (!items.length) return;

    const observer = new IntersectionObserver((entries) => {
      entries.forEach((entry) => {
        if (entry.isIntersecting) {
          entry.target.classList.add('visible');
          observer.unobserve(entry.target);
        }
      });
    }, { threshold: 0.15 });

    items.forEach((item) => observer.observe(item));
  }

  function initBackToTop() {
    const button = document.querySelector('.back-to-top');
    if (!button) return;

    window.addEventListener('scroll', () => {
      button.classList.toggle('show', window.scrollY > 400);
    });

    button.addEventListener('click', () => {
      window.scrollTo({ top: 0, behavior: 'smooth' });
    });
  }

  function initYear() {
    document.querySelectorAll('.current-year').forEach((el) => {
      el.textContent = new Date().getFullYear();
    });
  }

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

  function initDjangoMessages() {
    const djangoMessages = document.getElementById('django-messages');
    if (!djangoMessages) return;

    const messages = djangoMessages.querySelectorAll('div[data-message]');
    messages.forEach((msgDiv) => {
      const message = msgDiv.getAttribute('data-message');
      const tags = msgDiv.getAttribute('data-tags');
      const isError = tags && tags.includes('error');
      showToast(isError ? 'Error' : 'Info', message, isError);
    });
  }

  function initReactionForms() {
    const forms = document.querySelectorAll('.reaction-form');
    if (!forms.length) return;

    forms.forEach((form) => {
      form.addEventListener('submit', async (event) => {
        event.preventDefault();

        const button = form.querySelector('button[type="submit"]');
        if (!button) return;

        const csrfToken = form.querySelector('input[name="csrfmiddlewaretoken"]')?.value;
        const reaction = button.dataset.reaction;
        const payload = new FormData(form);

        try {
          const response = await fetch(form.action, {
            method: 'POST',
            headers: {
              'X-CSRFToken': csrfToken || '',
              'X-Requested-With': 'XMLHttpRequest',
              'Accept': 'application/json',
            },
            body: payload,
            credentials: 'same-origin',
          });

          const data = await response.json();
          if (!response.ok || data.status === 'error') {
            throw new Error(data.message || 'Unable to update reaction.');
          }

          const likeButton = document.querySelector('.reaction-btn[data-reaction="like"]');
          const dislikeButton = document.querySelector('.reaction-btn[data-reaction="dislike"]');

          if (likeButton) {
            likeButton.classList.toggle('active', Boolean(data.liked_by_user));
            const likeCount = likeButton.querySelector('.reaction-count');
            if (likeCount) likeCount.textContent = data.likes_count;
          }

          if (dislikeButton) {
            dislikeButton.classList.toggle('active', Boolean(data.disliked_by_user));
            const dislikeCount = dislikeButton.querySelector('.reaction-count');
            if (dislikeCount) dislikeCount.textContent = data.dislikes_count;
          }

          const currentButton = reaction === 'like' ? likeButton : dislikeButton;
          if (currentButton) {
            currentButton.blur();
          }
        } catch (error) {
          showToast('Reaction error', error.message || 'Unable to update reaction.', true);
        }
      });
    });
  }

  document.addEventListener('DOMContentLoaded', () => {
    initTheme();
    initReveal();
    initBackToTop();
    initYear();
    initDjangoMessages();
    initReactionForms();
  });
})();
