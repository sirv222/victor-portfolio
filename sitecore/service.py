import logging
from datetime import timedelta
from typing import Any, Mapping

from django.conf import settings
from django.core.mail import EmailMessage
from django.utils import timezone

logger = logging.getLogger(__name__)


def send_email(data: Mapping[str, Any]) -> int:
    """Send a contact-form email and return the number of emails sent."""
    # Normalize form input before sending so empty or whitespace-only values are treated as missing.
    name = str(data.get('name', '')).strip()
    email = str(data.get('email', '')).strip()
    subject = str(data.get('subject', '')).strip()
    message = str(data.get('message', '')).strip()

    # Reject incomplete submissions before trying to build or deliver the email.
    missing_fields = [
        field_name
        for field_name, value in {
            'name': name,
            'email': email,
            'subject': subject,
            'message': message,
        }.items()
        if not value
    ]
    if missing_fields:
        raise ValueError(
            'Missing required contact fields: ' + ', '.join(missing_fields)
        )

    # Construct the message body in a readable format and send it to the configured contact address.
    email_message = EmailMessage(
        subject=subject,
        body='\n'.join(
            [
                f'Name: {name}',
                f'Email: {email}',
                '',
                'Message:',
                message,
            ]
        ),
        from_email=settings.DEFAULT_FROM_EMAIL,
        to=[settings.CONTACT_EMAIL],
        reply_to=[email],
    )
    return email_message.send(fail_silently=False)


def contact_rate_limited(
    request,
    key: str = 'contact_attempts',
    limit: int = 5,
    period: timedelta = timedelta(hours=1),
) -> bool:
    """Return True when the contact form rate limit has been exceeded."""
    # A missing session means the request cannot be safely rate-limited.
    if not hasattr(request, 'session'):
        logger.error('Rate limit check failed because the request has no session.')
        return True

    # Fail fast if the rate limit configuration is invalid.
    if limit <= 0:
        raise ValueError('limit must be greater than 0')

    if period <= timedelta(0):
        raise ValueError('period must be greater than zero')

    # Track each submission timestamp and remove any entries that are outside the active time window.
    now = timezone.now()
    now_timestamp = now.timestamp()
    attempts = request.session.get(key, []) or []

    if not isinstance(attempts, list):
        attempts = []

    valid_attempts = []
    cutoff_timestamp = (now - period).timestamp()

    for timestamp in attempts:
        try:
            timestamp_value = float(timestamp)
        except (TypeError, ValueError):
            continue

        if timestamp_value >= cutoff_timestamp:
            valid_attempts.append(timestamp_value)

    if len(valid_attempts) >= limit:
        request.session[key] = valid_attempts
        logger.warning('Contact rate limit exceeded for session key %s.', key)
        return True

    valid_attempts.append(now_timestamp)
    request.session[key] = valid_attempts
    logger.info('Contact rate limit check completed successfully.')
    return False