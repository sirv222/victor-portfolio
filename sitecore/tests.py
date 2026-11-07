from unittest.mock import patch

from django.http import HttpResponse
from django.test import SimpleTestCase, override_settings
from django.urls import reverse

from sitecore.captcha import verify_recaptcha


class VerifyRecaptchaTests(SimpleTestCase):
    @override_settings(RECAPTCHA_SECRET_KEY='test-secret')
    @patch('sitecore.captcha.requests.post')
    def test_verify_recaptcha_returns_true_for_successful_response(self, mock_post):
        mock_post.return_value.json.return_value = {'success': True}

        self.assertTrue(verify_recaptcha('valid-token'))

    @override_settings(RECAPTCHA_SECRET_KEY='test-secret')
    @patch('sitecore.captcha.requests.post')
    def test_verify_recaptcha_returns_false_for_failed_response(self, mock_post):
        mock_post.return_value.json.return_value = {'success': False}

        self.assertFalse(verify_recaptcha('invalid-token'))


class ContactViewTests(SimpleTestCase):
    @override_settings(RECAPTCHA_SITE_KEY='test-site-key', RECAPTCHA_SECRET_KEY='test-secret')
    @patch('sitecore.views.render')
    @patch('sitecore.views.verify_recaptcha', return_value=False)
    def test_contact_view_re_renders_form_when_captcha_fails(self, mock_verify_recaptcha, mock_render):
        mock_render.return_value = HttpResponse('captcha error')

        response = self.client.post(
            reverse('contact'),
            {
                'name': 'Jane Doe',
                'email': 'jane@example.com',
                'subject': 'Project inquiry',
                'message': 'This is a valid message for testing.',
                'website': '',
                'g-recaptcha-response': 'bad-token',
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content, b'captcha error')
        self.assertEqual(mock_render.call_args[0][2]['recaptcha_site_key'], 'test-site-key')
        mock_verify_recaptcha.assert_called_once_with('bad-token')
