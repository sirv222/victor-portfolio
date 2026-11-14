import logging

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import get_user_model, login, logout
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied, ValidationError
from django.core.paginator import Paginator
from django.db import transaction
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST
from django_ratelimit.decorators import ratelimit

from sitecore.context_processors import portfolio_data

from .forms import (
    AuthorPasswordChangeForm,
    BlogPostForm,
    WriterLoginForm,
    WriterPasswordResetForm,
    WriterProfileForm,
    WriterRegistrationForm,
    WriterSetPasswordForm,
)
from .models import Blog, WriterProfile
from .services import AuthSecurityService, BlogService

logger = logging.getLogger(__name__)


def blog(request):
    """Render the public blog listing with optional search filtering."""
    try:
        search_query = request.GET.get('q', '')
        posts = BlogService.get_public_posts(search_query)
        latest_post = BlogService.get_latest_posts()
        paginator = Paginator(posts, 9)
        page_number = request.GET.get('page')
        page_obj = paginator.get_page(page_number)

        context = portfolio_data(request)
        context['posts'] = page_obj
        context['search_query'] = search_query
        context['latest_post'] = latest_post

        logger.info(
        'Public blog feed loaded for user=%s with query=%r page=%s',
        getattr(request.user, 'id', None),
        search_query,
        page_number,
        )
        return render(request, 'blog.html', context,)
    except ValidationError as exc:
        logger.warning(
            'Invalid blog search query from user=%s: %s',
            getattr(request.user, 'id', None),
            exc,
        )
        messages.error(request, str(exc))
        context = portfolio_data(request)
        context['posts'] = Paginator(BlogService.get_public_posts(''), 9).get_page(1)
        context['search_query'] = ''
        return render(request, 'blog.html', context)
    except Exception:
        logger.exception('Unexpected error while loading the public blog feed.')
        messages.error(request, 'The blog feed could not be loaded right now.')
        context = portfolio_data(request)
        context['posts'] = Paginator(BlogService.get_public_posts(''), 9).get_page(1)
        context['search_query'] = ''
        return render(request, 'blog.html', context)


def blog_post_detail(request, slug):
    """Display a published blog post and any user reaction state."""
    try:
        post = BlogService.get_published_post(slug)
    except Blog.DoesNotExist:
        logger.warning('Blog detail request for unknown or unpublished slug: %s', slug)
        return render(request, '404.html', status=404)
    except Exception:
        logger.exception('Unexpected error while fetching blog detail for slug=%s', slug)
        messages.error(request, 'The blog post could not be loaded.')
        return redirect('blog')

    context = portfolio_data(request)
    context['post'] = post
    context['liked_by_user'] = False
    context['disliked_by_user'] = False

    try:
        reaction = BlogService.get_user_reaction(post, request.user, request=request)
        if reaction:
            context['liked_by_user'] = reaction.reaction == 'like'
            context['disliked_by_user'] = reaction.reaction == 'dislike'
    except Exception:
        logger.exception(
            'Failed to resolve reaction state for user=%s on post=%s',
            getattr(request.user, 'id', None),
            slug,
        )

    return render(request, 'blog_detail.html', context)


def author_profile(request, username):
    """Render an author profile and the published posts associated with it."""
    author = get_object_or_404(get_user_model(), username=username)
    search_query = (request.GET.get('q') or '').strip()
    page_number = request.GET.get('page')

    context = portfolio_data(request)
    context.update(
        BlogService.get_author_profile(
            author,
            search_query=search_query,
            page_number=page_number,
            page_size=6,
        )
    )
    logger.info(
        'Author profile requested: username=%s search=%r page=%s',
        author.username,
        search_query,
        page_number,
    )
    return render(request, 'author_profile.html', context)


@login_required
def writer_dashboard(request):
    try:
        profile, _ = WriterProfile.objects.get_or_create(user=request.user)
        posts = BlogService.get_user_posts(request.user)
        context = portfolio_data(request)
        context['profile'] = profile
        context['posts'] = posts
        return render(request, 'writer_dashboard.html', context)
    except Exception:
        logger.exception('User dashboard error for user=%s', getattr(request.user, 'id', None))
        messages.error(request, 'Your dashboard is temporarily unavailable.')
        return redirect('blog')


@login_required
def create_blog_post(request):
    """Create a new draft or published blog post for the authenticated writer."""
    profile, _ = WriterProfile.objects.get_or_create(user=request.user)
    context = portfolio_data(request)
    context['profile'] = profile

    if request.method == 'POST':
        form = BlogPostForm(request.POST, request.FILES)
        if form.is_valid():
            try:
                BlogService.create_post(request.user, form)
                logger.info('Blog post created by user=%s', request.user.id)
                messages.success(request, 'Your blog post was saved successfully.')
                return redirect('writer_dashboard')
            except (PermissionDenied, ValidationError, ValueError) as exc:
                logger.warning('Post creation rejected for user=%s: %s', request.user.id, exc)
                messages.error(request, str(exc))
            except Exception:
                logger.exception('Unexpected post creation failure for user=%s', request.user.id)
                messages.error(request, 'Your post could not be saved. Please try again.')
        else:
            logger.warning(
                'Invalid blog post payload from user=%s: %s',
                request.user.id,
                form.errors,
            )
            messages.error(request, 'Please fix the highlighted fields and try again.')
        context['form'] = form
        return render(request, 'create_blog_post.html', context)

    context['form'] = BlogPostForm()
    return render(request, 'create_blog_post.html', context)


@login_required
def account_settings(request):
    """Manage profile details and password changes for the active writer."""
    profile, _ = WriterProfile.objects.get_or_create(user=request.user)
    context = portfolio_data(request)
    context['profile'] = profile

    if request.method == 'POST':
        profile_data = request.POST.copy()
        if 'bio' not in profile_data:
            profile_data['bio'] = profile.bio
        profile_form = WriterProfileForm(profile_data, request.FILES, instance=profile)
        password_form = AuthorPasswordChangeForm(request.user, request.POST)

        profile_submitted = 'bio' in request.POST or 'avatar' in request.FILES
        password_submitted = any(
            field in request.POST
            for field in ['old_password', 'new_password1', 'new_password2']
        )

        profile_valid = profile_form.is_valid() if profile_submitted else True
        password_valid = password_form.is_valid() if password_submitted else True

        if profile_valid and password_valid:
            try:
                with transaction.atomic():
                    if profile_submitted:
                        profile_form.save()
                    if password_submitted:
                        password_form.save()
                logger.info('Account settings updated for user=%s', request.user.id)
                if profile_submitted and password_submitted:
                    messages.success(
                        request,
                        'Your profile and password were updated successfully.',
                    )
                elif profile_submitted:
                    messages.success(request, 'Your profile was updated successfully.')
                else:
                    messages.success(request, 'Your password was updated successfully.')
                return redirect('account_settings')
            except Exception:
                logger.exception('Account settings update failed for user=%s', request.user.id)
                messages.error(request, 'Your settings could not be updated.')
        else:
            if profile_submitted and not profile_valid:
                logger.warning(
                    'Profile update rejected for user=%s: %s',
                    request.user.id,
                    profile_form.errors,
                )
                messages.error(request, 'Please review the profile fields and try again.')
            if password_submitted and not password_valid:
                logger.warning(
                    'Password update rejected for user=%s: %s',
                    request.user.id,
                    password_form.errors,
                )
                messages.error(request, 'Please review the password fields and try again.')

        context['profile_form'] = profile_form
        context['password_form'] = password_form
        return render(request, 'account_settings.html', context)

    context['profile_form'] = WriterProfileForm(instance=profile)
    context['password_form'] = AuthorPasswordChangeForm(request.user)
    return render(request, 'account_settings.html', context)


@require_POST
@ratelimit(key='ip', rate='20/h', block=True)
def toggle_blog_reaction(request, slug):
    try:
        post = Blog.objects.get(slug=slug)
        reaction = (request.POST.get('reaction') or '').strip().lower()

        if not request.session.session_key:
            request.session.create()

        result = BlogService.toggle_reaction(
            request.user,
            post,
            reaction,
            session_key=request.session.session_key,
        )

        post.refresh_from_db()
        current_reaction = BlogService.get_user_reaction(post, request.user, request=request)
        liked_by_user = current_reaction is not None and current_reaction.reaction == 'like'
        disliked_by_user = current_reaction is not None and current_reaction.reaction == 'dislike'

        if result == 'removed':
            messages.info(request, 'Your reaction was removed.')
        else:
            messages.success(request, 'Your reaction was updated.')

        if request.headers.get('x-requested-with') == 'XMLHttpRequest' \
        or request.accepts('application/json'):
            return JsonResponse({
                'status': 'success',
                'result': result,
                'likes_count': post.likes_count,
                'dislikes_count': post.dislikes_count,
                'liked_by_user': liked_by_user,
                'disliked_by_user': disliked_by_user,
            })

        return redirect(post.get_absolute_url())
    except Blog.DoesNotExist:
        logger.warning(
            'Reaction attempt on unknown post slug=%s by user=%s', slug, 
            getattr(
                request.user, 'id', None
                )
            )
        error_message = 'The post you tried to react to no longer exists.'
        if request.headers.get('x-requested-with') == 'XMLHttpRequest' \
        or request.accepts('application/json'):
            return JsonResponse({'status': 'error', 'message': error_message}, status=404)
        messages.error(request, error_message)
        return redirect('blog')
    
    except (PermissionDenied, ValueError, PermissionError) as exc:
        logger.warning(
            'Reaction rejected for user=%s on post=%s: %s', 
            getattr(
                request.user, 'id', None
                ), slug, exc
            )
        error_message = str(exc)
        if request.headers.get('x-requested-with') == 'XMLHttpRequest' \
        or request.accepts('application/json'):
            return JsonResponse({'status': 'error', 'message': error_message}, status=400)
        messages.error(request, error_message)
        return redirect('blog')
    
    except Exception:
        logger.exception(
            'Unexpected reaction failure for user=%s on post=%s', 
            getattr(
                request.user, 'id', None
                ), slug
            )
        error_message = 'We could not update the reaction. Please try again.'
        if request.headers.get('x-requested-with') == 'XMLHttpRequest' \
        or request.accepts('application/json'):
            return JsonResponse(
                {
                    'status': 'error', 'message': error_message
                    }, status=500
                )
        messages.error(request, error_message)
        return redirect('blog')


@require_POST
@ratelimit(key='ip', rate='20/h', block=True)
def add_blog_comment(request, slug):
    try:
        post = Blog.objects.get(slug=slug)
        content = (request.POST.get('content') or '').strip()
        BlogService.add_comment(request.user, post, content)
        messages.success(request, 'Your comment was added.')
        return redirect(post.get_absolute_url())
    except Blog.DoesNotExist:
        logger.warning(
            'Comment attempt on unknown post slug=%s by user=%s', slug, 
            getattr(
                request.user, 'id', None
                )
            )
        return redirect('blog')
    except (PermissionDenied, ValueError) as exc:
        logger.warning(
            'Comment rejected for user=%s on post=%s: %s', 
            getattr(
                request.user, 'id', None
                ), slug, exc
            )
        messages.error(request, str(exc))
        return redirect('blog')
    except Exception:
        logger.exception(
            'Unexpected comment failure for user=%s on post=%s', 
            getattr(
                request.user, 'id', None
                ), slug
            )
        messages.error(request, 'We could not add your comment.')
        return redirect('blog')


@ratelimit(key='ip', rate='10/h', block=True)
def writer_login(request):
    # Display the login form with the public reCAPTCHA key and gate the request before auth is attempted.
    context = portfolio_data(request)
    context['recaptcha_site_key'] = getattr(settings, 'RECAPTCHA_SITE_KEY', '')

    if request.user.is_authenticated:
        return redirect('writer_dashboard')

    if request.method == 'POST':
        form = WriterLoginForm(request=request, data=request.POST)
        if form.is_valid():
            result = AuthSecurityService.authenticate_user(
                request,
                username=form.cleaned_data.get('username'),
                password=form.cleaned_data.get('password'),
                captcha_token=form.cleaned_data.get('captcha_token'),
                honeypot=form.cleaned_data.get('website'),
            )
            if result['ok']:
                login(request, result['user'])
                logger.info('Successful writer login after security checks.')
                messages.success(request, 'Welcome back!')
                return redirect('writer_dashboard')
            messages.error(request, result['message'])
            form.add_error(None, result['message'])
        else:
            messages.error(request, 'Please correct the highlighted fields and try again.')
    else:
        form = WriterLoginForm()

    context['form'] = form
    return render(request, 'login.html', context)


@ratelimit(key='ip', rate='5/m', block=True)
def password_reset_request(request):
    # Request a reset link without exposing whether a mailbox exists in the system.
    context = portfolio_data(request)
    form = WriterPasswordResetForm(request.POST or None)

    if request.method == 'POST':
        if form.is_valid():
            try:
                BlogService.request_password_reset(form.cleaned_data['email'], request=request)
            except Exception:
                logger.exception('Password reset request processing failed.')
                messages.error(
                    request, 
                    'We could not process your request right now. Please try again later.'
                    )
                return render(request, 'password_reset.html', {**context, 'form': form})

            logger.info('Password reset request received and processed.')
            return redirect('password_reset_done')

        logger.warning('Password reset request rejected due to invalid form data.')

    context['form'] = form
    return render(request, 'password_reset.html', context)


@ratelimit(key='ip', rate='10/m', block=True)
def password_reset_done_view(request):
    context = portfolio_data(request)
    return render(request, 'password_reset_done.html', context)


@ratelimit(key='ip', rate='10/m', block=True)
def password_reset_confirm_view(request, uidb64=None, token=None):
    # The signed token must resolve to a valid user before the new password can be accepted.
    context = portfolio_data(request)
    user = BlogService.resolve_password_reset_user(uidb64, token)

    if user is None:
        logger.warning('Password reset confirmation request rejected: invalid or expired link.')
        messages.error(request, 'This password reset link is invalid or has expired.')
        return redirect('password_reset')

    form = WriterSetPasswordForm(user, request.POST or None)

    if request.method == 'POST':
        if form.is_valid():
            try:
                success = BlogService.confirm_password_reset(
                    uidb64, token, form.cleaned_data['new_password1']
                    )

            except ValidationError as exc:
                logger.warning(
                    'Password reset confirmation rejected because the new password failed validation.'
                    )
                messages.error(request, exc.messages[0])
                form.add_error(None, exc.messages[0])
                return render(request, 'password_reset_confirm.html', {**context, 'form': form})
            
            except Exception:
                logger.exception('Password reset confirmation processing failed.')
                messages.error(
                    request, 'We could not update your password right now. Please try again later.'
                    )
                return render(request, 'password_reset_confirm.html', {**context, 'form': form})

            if success:
                return redirect('password_reset_complete')

            logger.warning(
                'Password reset confirmation rejected after validation due to an invalid token.'
                )
            messages.error(request, 'This password reset link is invalid or has expired.')
            return redirect('password_reset')

    context['form'] = form
    return render(request, 'password_reset_confirm.html', context)


@ratelimit(key='ip', rate='10/m', block=True)
def password_reset_complete_view(request):
    context = portfolio_data(request)
    return render(request, 'password_reset_complete.html', context)


@ratelimit(key='ip', rate='10/m', block=True)
def verify_account_email(request, uidb64=None, token=None):
    context = portfolio_data(request)
    if AuthSecurityService.verify_account_email(uidb64, token):
        messages.success(
            request, 
            'Your email has been verified successfully. You can now log in.'
            )
        return redirect('login')

    logger.warning('Email verification rejected via a malformed or expired link.')
    messages.error(request, 'This verification link is invalid or has expired.')
    return redirect('login')


@require_POST
@login_required
def writer_logout(request):
    logout(request)
    messages.info(request, 'You have been logged out.')
    return redirect('blog')


@ratelimit(key='ip', rate='5/h', block=True)
def register_writer(request):
    # Registration is validated with forms, CAPTCHA, honeypot checks, and a verification email before activation.
    context = portfolio_data(request)
    context['recaptcha_site_key'] = getattr(settings, 'RECAPTCHA_SITE_KEY', '')

    if request.user.is_authenticated:
        return redirect('writer_dashboard')

    if request.method == 'POST':
        form = WriterRegistrationForm(request.POST)
        if form.is_valid():
            result = AuthSecurityService.register_user(form, request=request)
            if result['ok']:
                WriterProfile.objects.get_or_create(user=result['user'])
                messages.success(
                    request, 
                    'Your author account has been created. ' \
                    'Please check your email to verify your account before logging in.'
                    )
                return redirect('login')
            messages.error(request, result['message'])
            form.add_error(None, result['message'])
    else:
        form = WriterRegistrationForm()

    context['form'] = form
    return render(request, 'register_writer.html', context)
