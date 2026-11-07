import logging
import re
import time

from django.conf import settings
from django.contrib.auth import authenticate, get_user_model
from django.contrib.auth.tokens import default_token_generator
from django.core import mail
from django.core.cache import cache
from django.core.exceptions import PermissionDenied, ValidationError
from django.core.mail import EmailMultiAlternatives
from django.db import transaction
from django.db.models import Count, Q, Sum
from django.template.loader import render_to_string
from django.utils.encoding import force_bytes, force_str
from django.utils.http import urlsafe_base64_decode, urlsafe_base64_encode

from sitecore.captcha import verify_recaptcha

logger = logging.getLogger(__name__)


class AuthSecurityService:
    """Security helpers that gate registration and authentication flows."""

    @staticmethod
    def parse_rate_limit(limit_value):
        """Convert a string like "10/m" or "5/h" into a count and window."""
        raw = str(limit_value or '5/m').strip().lower()
        if '/' not in raw:
            raise ValueError('Rate limit must use the format "count/unit".')

        value, unit = raw.split('/', 1)
        count = int(value)
        if unit == 'm':
            return count, 60
        if unit == 'h':
            return count, 60 * 60
        return count, 60

    @staticmethod
    def enforce_rate_limit(request, action, ip_limit='10/m', session_limit='5/m'):
        # Fail closed for repeated abusive behavior by tracking both IP and session buckets.
        if request is None:
            return True

        ip_value, ip_window = AuthSecurityService.parse_rate_limit(ip_limit)
        session_value, session_window = AuthSecurityService.parse_rate_limit(session_limit)
        client_ip = request.META.get('REMOTE_ADDR', 'unknown')
        session_key = f'auth:{action}:session:{request.session.session_key or "anonymous"}'
        ip_key = f'auth:{action}:ip:{client_ip}'
        now = int(time.time())

        session_bucket = cache.get(session_key, [])
        ip_bucket = cache.get(ip_key, [])
        session_bucket = [ts for ts in session_bucket if now - ts < session_window]
        ip_bucket = [ts for ts in ip_bucket if now - ts < ip_window]

        if len(session_bucket) >= session_value or len(ip_bucket) >= ip_value:
            logger.warning('Auth rate limit exceeded for action=%s.', action)
            return False

        session_bucket.append(now)
        ip_bucket.append(now)
        cache.set(session_key, session_bucket, timeout=session_window + 5)
        cache.set(ip_key, ip_bucket, timeout=ip_window + 5)
        return True

    @staticmethod
    def validate_honeypot(value):
        # Hidden form field used to catch automated bots and malformed submissions.
        return bool((value or '').strip())

    @staticmethod
    def validate_captcha(token):
        # ReCAPTCHA token must be verified on the server before login or registration proceeds.
        return bool(verify_recaptcha(token))

    @staticmethod
    def register_user(form, request=None):
        # Registration flow is gated by IP/session rate limits, honeypot checks, and CAPTCHA validation.
        if not AuthSecurityService.enforce_rate_limit(request, 'register', ip_limit='8/h', session_limit='4/h'):
            return {'ok': False, 'message': 'Too many account creation attempts. Please wait a moment and try again.'}

        if AuthSecurityService.validate_honeypot(form.cleaned_data.get('website')):
            logger.warning('Registration rejected: honeypot triggered.')
            return {'ok': False, 'message': 'We could not process your request.'}

        captcha_token = form.cleaned_data.get('captcha_token')
        if not AuthSecurityService.validate_captcha(captcha_token):
            logger.warning('Registration rejected: CAPTCHA validation failed.')
            return {'ok': False, 'message': 'Please complete the CAPTCHA verification.'}

        try:
            user = form.save(commit=False)
            user.is_active = False
            user.save()
            AuthSecurityService.send_verification_email(user, request=request)
            logger.info('User registration accepted; verification email queued.')
            return {'ok': True, 'user': user}
        except Exception:
            logger.exception('User registration failed during account creation.')
            return {'ok': False, 'message': 'We could not create your account right now. Please try again later.'}

    @staticmethod
    def authenticate_user(request, username, password, captcha_token=None, honeypot=''):
        # Login requests are blocked early for abuse, bot traffic, and accounts not yet verified.
        if not AuthSecurityService.enforce_rate_limit(request, 'login', ip_limit='10/m', session_limit='5/m'):
            return {'ok': False, 'message': 'Too many login attempts. Please wait a moment and try again.'}

        if AuthSecurityService.validate_honeypot(honeypot):
            logger.warning('Login rejected: honeypot triggered.')
            return {'ok': False, 'message': 'We could not process your request.'}

        if not AuthSecurityService.validate_captcha(captcha_token):
            logger.warning('Login rejected: CAPTCHA validation failed.')
            return {'ok': False, 'message': 'Please complete the CAPTCHA verification.'}

        user = authenticate(request, username=username, password=password)
        if user is None:
            logger.warning('Login rejected: invalid credentials.')
            return {'ok': False, 'message': 'Invalid username or password.'}

        if not user.is_active:
            logger.warning('Login rejected: unverified account.')
            return {'ok': False, 'message': 'Please verify your email before signing in.'}

        return {'ok': True, 'user': user}

    @staticmethod
    def send_verification_email(user, request=None):
        # Send a one-time verification link after registration so the account cannot log in before email confirmation.
        if user is None or not getattr(user, 'email', None):
            logger.warning('Verification email skipped because the account has no email address.')
            return False

        try:
            uid = urlsafe_base64_encode(force_bytes(user.pk))
            token = default_token_generator.make_token(user)
            protocol = 'https' if getattr(request, 'is_secure', lambda: False)() or not settings.DEBUG else 'http'
            domain = request.get_host() if request is not None else getattr(settings, 'DEFAULT_DOMAIN', 'localhost:9000')
            context = {'protocol': protocol, 'domain': domain, 'uid': uid, 'token': token}
            body = render_to_string('email/account_verification_email.html', context)
            subject = 'Verify your Ink & Insight author account'
            message = EmailMultiAlternatives(
                subject,
                body,
                settings.DEFAULT_FROM_EMAIL or settings.EMAIL_HOST_USER,
                [user.email],
            )
            message.attach_alternative(body, 'text/html')
            connection = mail.get_connection()
            sent = connection.send_messages([message])
            return sent > 0
        except Exception:
            logger.exception('Failed to send verification email for a user account.')
            return False

    @staticmethod
    def verify_account_email(uidb64, token):
        # Validate the signed user ID and token from the verification email before activating the account.
        if not uidb64 or not token:
            return False

        try:
            uid = force_str(urlsafe_base64_decode(uidb64))
            user = get_user_model().objects.filter(pk=uid).first()
            if user is None:
                logger.warning('Email verification rejected: no matching account.')
                return False
            if not default_token_generator.check_token(user, token):
                logger.warning('Email verification rejected: invalid token.')
                return False
            if user.is_active:
                return True
            user.is_active = True
            user.save(update_fields=['is_active'])
            logger.info('Account email verification completed successfully.')
            return True
        except (TypeError, ValueError, OverflowError):
            logger.warning('Email verification rejected: malformed token or UID.')
            return False
        except Exception:
            logger.exception('Unexpected failure while verifying an account email.')
            return False


class BlogService:
    @staticmethod
    def sanitize_search_query(raw_query):
        """Normalize and validate a user-provided search string."""
        if raw_query is None:
            logger.debug('Search query was empty because the value was None.')
            return ''

        query = str(raw_query).strip()
        if not query:
            logger.debug('Search query was empty after trimming.')
            return ''

        if len(query) > 100:
            logger.warning('Search query rejected because it exceeds the allowed length: %s', len(query))
            raise ValidationError('Search query is too long.')

        query = re.sub(r'<[^>]+>', ' ', query)
        query = re.sub(r'\s+', ' ', query).strip()

        if not query:
            logger.debug('Search query was blank after sanitization.')
            return ''

        if len(query) > 100:
            logger.warning('Search query rejected after sanitization because it exceeds the limit. length=%s', len(query))
            raise ValidationError('Search query is too long.')

        return query

    @staticmethod
    def get_public_posts(search_query=''):
        """Return published posts, optionally filtered by the provided search term."""
        from .models import Blog

        safe_query = BlogService.sanitize_search_query(search_query)
        queryset = Blog.objects.filter(status='published').select_related(
            'author'
        ).prefetch_related('comments', 'reactions')

        if not safe_query:
            logger.debug('Loading public blog feed without any search filter.')
            return queryset

        logger.info('Filtering public blog feed by query=%r', safe_query)
        return queryset.filter(
            Q(title__icontains=safe_query)
            | Q(excerpt__icontains=safe_query)
            | Q(content__icontains=safe_query)
            | Q(author__username__icontains=safe_query)
        ).distinct()

    @staticmethod
    def get_published_post(slug):
        from .models import Blog
        try:
            return (
                Blog.objects.filter(status='published')
                .select_related('author')
                .prefetch_related('comments__user', 'reactions')
                .get(slug=slug)
            )
        except Blog.DoesNotExist:
            logger.warning(
                'Attempted access to unpublished or unknown blog post with slug=%s',
                slug,
            )
            raise

    @staticmethod
    def get_user_posts(user):
        from .models import Blog
        return Blog.objects.filter(author=user).order_by('-created_at')

    @staticmethod
    def get_author_profile(author, search_query='', page_number=1, page_size=6):
        """Build the author profile payload and aggregate author-level reactions."""
        from .models import Blog, WriterProfile

        profile, _ = WriterProfile.objects.get_or_create(user=author)
        posts = Blog.objects.filter(author=author, status='published').select_related(
            'author'
        ).order_by('-publish_date', '-created_at')

        if search_query:
            logger.info(
                'Filtering author profile content for author=%s with search=%r',
                author.username,
                search_query,
            )
            posts = posts.filter(
                Q(title__icontains=search_query)
                | Q(excerpt__icontains=search_query)
                | Q(content__icontains=search_query)
            ).distinct()

        from django.core.paginator import Paginator

        page_obj = Paginator(posts, page_size).get_page(page_number)

        reaction_stats = (
            Blog.objects.filter(author=author, status='published')
            .annotate(
                like_count=Count('reactions', filter=Q(reactions__reaction='like')),
                dislike_count=Count(
                    'reactions',
                    filter=Q(reactions__reaction='dislike'),
                ),
            )
            .aggregate(
                likes_total=Sum('like_count'),
                dislikes_total=Sum('dislike_count'),
            )
        )

        logger.debug(
            'Author profile summary built for author=%s with %s posts, likes=%s, dislikes=%s',
            author.username,
            posts.count(),
            reaction_stats['likes_total'] or 0,
            reaction_stats['dislikes_total'] or 0,
        )
        return {
            'author': author,
            'profile': profile,
            'posts': page_obj,
            'search_query': search_query,
            'likes_total': reaction_stats['likes_total'] or 0,
            'dislikes_total': reaction_stats['dislikes_total'] or 0,
        }

    @staticmethod
    def create_post(user, data):
        """Persist a valid blog post for an authenticated writer."""
        from .models import Blog

        if not user or not getattr(user, 'is_authenticated', False):
            logger.warning(
                'Post creation blocked for an unauthenticated user attempt.'
            )
            raise PermissionError('Only authenticated writers can create posts.')

        form = data if hasattr(data, 'is_valid') else None
        if form is not None and not form.is_valid():
            logger.warning(
                'Post creation rejected due to invalid form data. user=%s',
                user.id,
            )
            raise ValidationError('Invalid post content.')

        post_data = data if not hasattr(data, 'cleaned_data') else data.cleaned_data
        title = (post_data.get('title') or '').strip()
        excerpt = (post_data.get('excerpt') or '').strip()
        content = (post_data.get('content') or '').strip()
        status = (post_data.get('status') or 'draft').strip()
        cover_image = post_data.get('cover_image')

        if not title or not content:
            logger.warning(
                'Post creation rejected because the title or content was empty. '
                'user=%s',
                user.id,
            )
            raise ValueError('Title and content are required.')

        with transaction.atomic():
            post = Blog.objects.create(
                title=title,
                excerpt=excerpt,
                content=content,
                cover_image=cover_image,
                author=user,
                status=status,
            )

        logger.info('Blog post created successfully. user=%s slug=%s status=%s', user.id, post.slug, post.status)
        return post

    @staticmethod
    def toggle_reaction(user, post, reaction, session_key=None):
        """Create, update, or remove a reaction for a published post."""
        from .models import BlogReaction

        if reaction not in {'like', 'dislike'}:
            logger.warning(
                'Invalid reaction attempted on post=%s value=%r',
                getattr(post, 'id', None),
                reaction,
            )
            raise ValueError('Please choose a valid reaction.')
        if getattr(post, 'status', None) != 'published':
            logger.warning(
                'Reaction rejected for unpublished post=%s',
                getattr(post, 'id', None),
            )
            raise PermissionDenied('This post is not available for reactions.')

        actor_user = user if user is not None and getattr(user, 'is_authenticated', False) else None
        actor_session_key = session_key or None

        if actor_user is None and not actor_session_key:
            logger.warning(
                'Anonymous reaction rejected because no session key was provided.'
            )
            raise PermissionError('Authentication required.')

        if actor_user is not None:
            existing = post.reactions.filter(user=actor_user).first()
        else:
            existing = post.reactions.filter(session_key=actor_session_key).first()

        if existing:
            if existing.reaction == reaction:
                existing.delete()
                logger.info(
                    'Reaction removed for post=%s user=%s session=%s',
                    getattr(post, 'id', None),
                    getattr(actor_user, 'id', None),
                    actor_session_key,
                )
                return 'removed'
            existing.reaction = reaction
            existing.save(update_fields=['reaction'])
            logger.info(
                'Reaction updated for post=%s user=%s session=%s',
                getattr(post, 'id', None),
                getattr(actor_user, 'id', None),
                actor_session_key,
            )
            return 'updated'

        BlogReaction.objects.create(
            post=post,
            user=actor_user,
            session_key=actor_session_key,
            reaction=reaction,
        )
        logger.info(
            'Reaction created for post=%s user=%s session=%s',
            getattr(post, 'id', None),
            getattr(actor_user, 'id', None),
            actor_session_key,
        )
        return 'created'

    @staticmethod
    def add_comment(user, post, content):
        """Create a comment on a published post, supporting guest authors."""
        from .models import BlogComment

        if getattr(post, 'status', None) != 'published':
            logger.warning(
                'Comment rejected for unpublished post=%s',
                getattr(post, 'id', None),
            )
            raise PermissionDenied('This post is not available for comments.')

        cleaned = (content or '').strip()
        if not cleaned:
            logger.warning(
                'Comment rejected on post=%s because the content was empty.',
                getattr(post, 'id', None),
            )
            raise ValueError('Comment cannot be empty.')

        comment_user = user if user is not None and getattr(user, 'is_authenticated', False) else None
        comment = BlogComment.objects.create(post=post, user=comment_user, content=cleaned)
        logger.info(
            'Comment added to post=%s by user=%s',
            getattr(post, 'id', None),
            getattr(comment_user, 'id', None),
        )
        return comment

    @staticmethod
    def get_user_reaction(post, user, request=None):
        if user is not None and getattr(user, 'is_authenticated', False):
            return post.reactions.filter(user=user).first()

        if request is not None and hasattr(request, 'session'):
            session_key = request.session.session_key
            if session_key:
                return post.reactions.filter(session_key=session_key).first()

        return None

    @staticmethod
    def request_password_reset(email, request=None):
        # A reset request should not reveal whether a mail address exists; it only sends a link if the user is known.
        normalized = (email or '').strip().lower()
        if not normalized:
            logger.warning('Password reset request rejected: missing email address.')
            return False

        user_model = get_user_model()
        user = user_model.objects.filter(email__iexact=normalized).first()
        if user is None:
            logger.info('Password reset request received for an unregistered email address.')
            return False

        try:
            uid = urlsafe_base64_encode(force_bytes(user.pk))
            token = default_token_generator.make_token(user)
            protocol = 'https' if getattr(request, 'is_secure', lambda: False)() or not settings.DEBUG else 'http'
            domain = request.get_host() if request is not None else getattr(settings, 'DEFAULT_DOMAIN', 'localhost:8000')
            context = {'protocol': protocol, 'domain': domain, 'uid': uid, 'token': token}

            body = render_to_string('email/password_reset_email.html', context)
            subject = 'Reset your password'
            message = EmailMultiAlternatives(
                subject,
                body,
                settings.DEFAULT_FROM_EMAIL or settings.EMAIL_HOST_USER,
                [user.email],
            )
            message.attach_alternative(body, 'text/html')
            connection = mail.get_connection()
            sent = connection.send_messages([message])
            logger.info('Password reset email sent successfully for an author account. backend=%s recipients=%s', settings.EMAIL_BACKEND, [user.email])
            return sent > 0
        except Exception:
            logger.exception(
                'Password reset email delivery failed for a registered author account. backend=%s host=%s user=%s debug=%s',
                settings.EMAIL_BACKEND,
                getattr(settings, 'EMAIL_HOST', None),
                getattr(settings, 'EMAIL_HOST_USER', None),
                settings.DEBUG,
            )
            return False

    @staticmethod
    def resolve_password_reset_user(uidb64, token):
        # Rehydrate the user from the signed reset link only when the token is valid and unexpired.
        if not uidb64 or not token:
            return None

        try:
            uid = force_str(urlsafe_base64_decode(uidb64))
            user = get_user_model().objects.filter(pk=uid).first()
            if user is None:
                return None
            if not default_token_generator.check_token(user, token):
                return None
            return user
        except (TypeError, ValueError, OverflowError):
            return None

    @staticmethod
    def confirm_password_reset(uidb64, token, new_password):
        # A valid reset token is required before changing the password, and the new value is still validated by Django.
        if not uidb64 or not token or not new_password:
            logger.warning('Password reset confirmation rejected: missing required inputs.')
            return False

        try:
            user = BlogService.resolve_password_reset_user(uidb64, token)
            if user is None:
                logger.warning('Password reset confirmation rejected: invalid or expired reset token.')
                return False

            user.set_password(new_password)
            user.save(update_fields=['password'])
            logger.info('Password reset completed successfully for an author account.')
            return True
        except ValidationError:
            raise
        except Exception:
            logger.exception('Unexpected failure while confirming a password reset.')
            return False
