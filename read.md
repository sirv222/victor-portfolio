# Ink & Insight

Ink & Insight is a portfolio and blog website built with Django. It includes a personal portfolio landing page, blog publishing, author authentication, comment support, CAPTCHA-protected forms, and a responsive frontend.

## Features

- Portfolio homepage and project/skill sections
- Blog listing page with category filtering
- Published post detail pages
- Guest commenting on published posts
- Author registration and login flow
- Django message-based feedback and user-friendly validation
- ReCAPTCHA-protected auth forms
- PostgreSQL-ready configuration
- Media upload support for blog covers and writer avatars

## Tech Stack

- Python 3.11+
- Django 6.1.2
- PostgreSQL
- HTML, CSS, JavaScript
- Pillow for image processing
- django-debug-toolbar for local debugging
- django-ratelimit for request throttling
- python-dotenv for environment configuration
- requests for reCAPTCHA verification

## Project Structure

- `my_portfolio/` — project settings and root URL config
- `my_blog/` — blog app, models, services, views, and tests
- `sitecore/` — portfolio content app and contact data
- `template/` — Django HTML templates
- `static/` — shared CSS and JavaScript assets
- `media/` — uploaded user and blog media files

## Local Setup

1. Create and activate a virtual environment.
2. Install dependencies:

   ```bash
   pip install -r requirement.txt
   ```

3. Create a `.env` file in the project root with values similar to:

   ```env
   SECRET_KEY=your-secret-key
   DEBUG=True
   ALLOWED_HOSTS=localhost,127.0.0.1
   DB_NAME=portfolio
   DB_USER=postgres
   DB_PASSWORD=yourpassword
   DB_HOST=localhost
   DB_PORT=8000
   EMAIL_HOST_USER=your-email@example.com
   EMAIL_HOST_PASSWORD=your-app-password
   DEFAULT_FROM_EMAIL=your-email@example.com
   RECAPTCHA_SITE_KEY=your-site-key
   RECAPTCHA_SECRET_KEY=your-secret-key
   ```

4. Run database migrations:

   ```bash
   python manage.py migrate
   ```

5. Start the development server:

   ```bash
   python manage.py runserver
   ```

## Useful Commands

```bash
python manage.py test
python manage.py makemigrations
python manage.py migrate
python manage.py createsuperuser
```

## Notes

- The project is configured to use PostgreSQL by default in `my_portfolio/settings.py`.
- For production, make sure `DEBUG` is disabled and strong secret keys and SMTP credentials are configured.
- ReCAPTCHA keys should be supplied in the environment if the auth forms are used.
