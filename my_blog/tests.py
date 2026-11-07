from io import BytesIO

from django.contrib.auth import get_user_model
from django.core.exceptions import PermissionDenied
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode
from django.contrib.auth.tokens import default_token_generator
from PIL import Image

from .forms import BlogPostForm, WriterLoginForm, WriterRegistrationForm
from .models import Blog, BlogReaction
from .services import BlogService


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

        self.assertFalse(form.is_valid())
        self.assertIn('username', form.errors)
        self.assertIn('password', form.errors)

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
