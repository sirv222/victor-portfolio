import logging
from smtplib import SMTPException

from django.conf import settings
from django.contrib import messages
from django.shortcuts import redirect, render
from django_ratelimit.decorators import ratelimit

from .captcha import verify_recaptcha
from .forms import ContactForm
from .service import contact_rate_limited, send_email

logger = logging.getLogger(__name__)


def homepage(request):
    return render(request, 'index.html')


def about(request):
    return render(request, 'about.html')


def projects(request):
    return render(request, 'projects.html')


def skills(request):
    return render(request, 'skills.html')


@ratelimit(key='ip', rate='10/h', method='POST', block=False)
def contact(request):
    form = ContactForm(request.POST or None)

    if request.method != 'POST':
        return render(
            request,
            'contact.html',
            {'recaptcha_site_key': settings.RECAPTCHA_SITE_KEY, 'form': form},
        )

    if request.limited:
        messages.error(
            request,
            'Too many requests from your network. Please try again later.',
        )
        return redirect('contact')

    if request.POST.get('website', '').strip():
        logger.warning('Honeypot triggered.')
        messages.error(
            request,
            'Invalid submission detected. Please try again.',
        )
        return render(
            request,
            'contact.html',
            {'recaptcha_site_key': settings.RECAPTCHA_SITE_KEY, 'form': form},
        )

    if not form.is_valid():
        logger.warning('Invalid contact form submission received.')
        messages.error(request, 'Please correct the highlighted form fields and try again.')
        return render(
            request,
            'contact.html',
            {'recaptcha_site_key': settings.RECAPTCHA_SITE_KEY, 'form': form},
        )

    captcha_token = request.POST.get('g-recaptcha-response')
    if not verify_recaptcha(captcha_token):
        messages.error(
            request,
            'please complete the CAPTCHA verification.',
        )
        return render(
            request,
            'contact.html',
            {'recaptcha_site_key': settings.RECAPTCHA_SITE_KEY, 'form': form},
        )

    if contact_rate_limited(request):
        messages.error(
            request,
            'Too many submissions. Please try again in about an hour.',
        )
        return redirect('contact')

    data = form.cleaned_data

    try:
        send_email(data)
    except (SMTPException, OSError, TimeoutError, ValueError):
        logger.exception('Error sending contact email.')
        messages.error(
            request,
            'An error occurred while sending the email. Please try again later.',
        )
    else:
        logger.info('Contact form message sent successfully.')
        messages.success(
            request,
            "Your message has been sent successfully! I'll get back to you as soon as possible.",
        )

    return redirect('contact')