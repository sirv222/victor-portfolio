from io import BytesIO
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.contrib.sessions.middleware import SessionMiddleware
from django.core.cache import cache
from django.core.exceptions import PermissionDenied, ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import RequestFactory, TestCase, override_settings
from django.urls import reverse
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode
from django.contrib.auth.tokens import default_token_generator
from PIL import Image

from .forms import BlogPostForm, WriterLoginForm, WriterRegistrationForm
from .models import Blog, BlogReaction
from .services import AuthSecurityService, BlogService


class BlogModelTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username='writer', password='secret123')
        self.post = Blog.objects.create(
            title='Test Post',
            content='Some content here for testing.',
            author=self.user,
            status='published',
        )

    def test_post_counts_reactions(self):
        BlogReaction.objects.create(post=self.post, user=self.user, reaction='like')
        another_user = get_user_model().objects.create_user(username='reader', password='secret123')
        BlogReaction.objects.create(post=self.post, user=another_user, reaction='dislike')

        self.assertEqual(self.post.likes_count, 1)
        self.assertEqual(self.post.dislikes_count, 1)

    def test_only_published_posts_are_public(self):
        draft_post = Blog.objects.create(
            title='Draft Post',
            content='Hidden content',
            author=self.user,
            status='draft',
        )

        public_posts = Blog.objects.filter(status='published')

        self.assertIn(self.post, public_posts)
        self.assertNotIn(draft_post, public_posts)

    def test_writer_registration_validates_password_strength(self):
        form = WriterRegistrationForm({
            'username': 'new_writer',
            'email': 'writer@example.com',
            'password1': '123',
            'password2': '123',
        })

        self.assertFalse(form.is_valid())
        self.assertIn('password2', form.errors)

    def test_writer_login_form_rejects_blank_credentials(self):
        form = WriterLoginForm(data={'username': '   ', 'password': '  '})

        with self.assertLogs('my_blog.forms', level='WARNING') as logs:
            self.assertFalse(form.is_valid())

        self.assertIn('username', form.errors)
        self.assertIn('password', form.errors)
        self.assertIn('captcha_token', form.errors)
        self.assertTrue(any('form=WriterLoginForm field=username' in entry for entry in logs.output))
        self.assertTrue(any('form=WriterLoginForm field=password' in entry for entry in logs.output))
        self.assertTrue(any('form=WriterLoginForm field=captcha_token' in entry for entry in logs.output))

    def test_writer_login_form_uses_browser_recaptcha_response(self):
        form = WriterLoginForm(
            data={
                'username': self.user.username,
                'password': 'secret123',
                'g-recaptcha-response': 'captcha-token',
            }
        )

        self.assertTrue(form.is_valid(), form.errors)
        self.assertEqual(form.cleaned_data['captcha_token'], 'captcha-token')

    def test_latest_posts_do_not_change_post_titles(self):
        original_title = self.post.title

        latest_posts = BlogService.get_latest_posts()

        self.assertIn(self.post, latest_posts)
        self.post.refresh_from_db()
        self.assertEqual(self.post.title, original_title)

    def test_unpublished_post_rejects_reactions(self):
        draft_post = Blog.objects.create(
            title='Draft Post',
            content='This draft should not accept reactions.',
            author=self.user,
            status='draft',
        )

        with self.assertRaises(PermissionDenied):
            BlogService.toggle_reaction(self.user, draft_post, 'like')

    def test_unpublished_post_rejects_comments(self):
        draft_post = Blog.objects.create(
            title='Comment Draft',
            content='This draft should not accept comments.',
            author=self.user,
            status='draft',
        )

        with self.assertRaises(PermissionDenied):
            BlogService.add_comment(self.user, draft_post, 'This should not be allowed.')

    def test_guest_comment_is_allowed_without_authentication(self):
        comment = BlogService.add_comment(None, self.post, 'A guest comment is allowed here.')

        self.assertEqual(comment.post, self.post)
        self.assertIsNone(comment.user)
        self.assertEqual(comment.content, 'A guest comment is allowed here.')

    def test_guest_reaction_is_allowed_without_authentication(self):
        result = BlogService.toggle_reaction(None, self.post, 'like', session_key='anon-session-1')

        self.assertEqual(result, 'created')
        self.assertEqual(self.post.reactions.filter(session_key='anon-session-1').count(), 1)
        self.assertEqual(self.post.likes_count, 1)

    def test_invalid_comment_raises_clear_error_message(self):
        with self.assertRaisesMessage(ValueError, 'Comment cannot be empty.'):
            BlogService.add_comment(None, self.post, '   ')

    def test_create_post_saves_cover_image(self):
        buffer = BytesIO()
        Image.new('RGB', (10, 10), color='blue').save(buffer, format='PNG')
        image = SimpleUploadedFile('cover.png', buffer.getvalue(), content_type='image/png')
        form = BlogPostForm(
            data={
                'title': 'Image Post',
                'excerpt': 'A short excerpt.',
                'content': 'This content is long enough to pass validation for the post body.',
                'status': 'draft',
            },
            files={'cover_image': image},
        )

        self.assertTrue(form.is_valid(), form.errors)
        post = BlogService.create_post(self.user, form)
        self.assertTrue(bool(post.cover_image))
        self.assertIn('cover', post.cover_image.name.lower())


class AuthSecurityServiceTests(TestCase):
    def setUp(self):
        cache.clear()
        self.factory = RequestFactory()
        self.session_middleware = SessionMiddleware(lambda request: None)

    def test_anonymous_rate_limits_use_separate_session_buckets(self):
        first_request = self.factory.post('/login/')
        second_request = self.factory.post('/login/')
        self.session_middleware.process_request(first_request)
        self.session_middleware.process_request(second_request)

        self.assertTrue(
            AuthSecurityService.enforce_rate_limit(
                first_request,
                'test-login',
                ip_limit='10/m',
                session_limit='1/m',
            )
        )
        self.assertTrue(
            AuthSecurityService.enforce_rate_limit(
                second_request,
                'test-login',
                ip_limit='10/m',
                session_limit='1/m',
            )
        )
        self.assertNotEqual(first_request.session.session_key, second_request.session.session_key)

    def test_registration_rolls_back_when_verification_email_fails(self):
        form = WriterRegistrationForm(
            data={
                'username': 'undeliverable_writer',
                'email': 'undeliverable@example.com',
                'password1': 'StrongPass123!',
                'password2': 'StrongPass123!',
                'captcha_token': 'captcha-token',
            }
        )
        self.assertTrue(form.is_valid(), form.errors)

        with patch(
            'my_blog.services.AuthSecurityService.send_verification_email',
            return_value=False,
        ):
            result = AuthSecurityService.register_user(form)

        self.assertFalse(result['ok'])
        self.assertFalse(get_user_model().objects.filter(username='undeliverable_writer').exists())


class WriterDashboardTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username='dashboard_writer', password='secret123')
        self.posts = [
            Blog.objects.create(
                title=f'Dashboard Post {index}',
                content='This post has enough content for the dashboard test.',
                author=self.user,
                status='published',
            )
            for index in range(7)
        ]
        like_user = get_user_model().objects.create_user(username='like_reader', password='secret123')
        dislike_user = get_user_model().objects.create_user(username='dislike_reader', password='secret123')
        BlogReaction.objects.create(post=self.posts[0], user=like_user, reaction='like')
        BlogReaction.objects.create(post=self.posts[0], user=dislike_user, reaction='dislike')
        self.client.force_login(self.user)

    def test_dashboard_paginates_posts_and_shows_received_reactions(self):
        response = self.client.get(reverse('writer_dashboard'), {'page': 2})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['posts'].number, 2)
        self.assertEqual(len(response.context['posts']), 1)
        self.assertEqual(response.context['posts_total'], 7)
        self.assertEqual(response.context['published_posts_total'], 7)
        self.assertEqual(response.context['likes_total'], 1)
        self.assertEqual(response.context['dislikes_total'], 1)


class PasswordResetServiceTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username='reset_writer',
            email='writer@example.com',
            password='StrongPass123!',
        )

    @override_settings(EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend')
    def test_password_reset_request_sends_email_for_known_user(self):
        from django.core import mail

        sent = BlogService.request_password_reset('writer@example.com')

        self.assertTrue(sent)
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn('Reset your password', mail.outbox[0].subject)

    def test_unknown_email_does_not_disclose_user_existence(self):
        self.assertFalse(BlogService.request_password_reset('unknown@example.com'))

    def test_password_reset_confirm_updates_password_when_token_valid(self):
        token = default_token_generator.make_token(self.user)
        uid = urlsafe_base64_encode(force_bytes(self.user.pk))

        updated = BlogService.confirm_password_reset(uid, token, 'NewSecurePass456!')

        self.assertTrue(updated)
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password('NewSecurePass456!'))

    def test_password_reset_confirm_rejects_invalid_token(self):
        uid = urlsafe_base64_encode(force_bytes(self.user.pk))

        self.assertFalse(BlogService.confirm_password_reset(uid, 'invalid-token', 'NewSecurePass456!'))

    def test_password_reset_confirmation_enforces_password_strength(self):
        uid = urlsafe_base64_encode(force_bytes(self.user.pk))
        token = default_token_generator.make_token(self.user)

        with self.assertRaises(ValidationError):
            BlogService.confirm_password_reset(uid, token, '123')
