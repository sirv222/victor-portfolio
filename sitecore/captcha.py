import logging

import requests
from django.conf import settings

logger = logging.getLogger(__name__)


def verify_recaptcha(token):
    # Never validate a request without both a token and the configured secret key.
    if not token:
        logger.warning('reCAPTCHA verification skipped because no token was provided.')
        return False

    if not settings.RECAPTCHA_SECRET_KEY:
        logger.warning('reCAPTCHA verification skipped because the secret key is not configured.')
        return False

    try:
        # Submit the token to Google for verification and fail closed on any transport issue.
        response = requests.post(
            'https://www.google.com/recaptcha/api/siteverify',
            data={
                'secret': settings.RECAPTCHA_SECRET_KEY,
                'response': token,
            },
            timeout=10,
        )
        response.raise_for_status()

        # Accept only a valid JSON success payload; malformed data is treated as invalid.
        result = response.json()
        if not isinstance(result, dict):
            logger.warning('reCAPTCHA verification returned a non-dict response: %s', result)
            return False

        success = bool(result.get('success'))
        if not success:
            logger.warning('reCAPTCHA verification failed. Google response: %s', result)
        return success

    except requests.RequestException as exc:
        logger.exception('reCAPTCHA request to Google failed: %s', exc)
        return False
    except (ValueError, TypeError) as exc:
        logger.exception('reCAPTCHA response parsing failed: %s', exc)
        return False