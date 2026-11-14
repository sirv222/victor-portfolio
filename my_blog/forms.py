import logging
import re

from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import (
    AuthenticationForm,
    PasswordResetForm,
    SetPasswordForm,
    UserCreationForm,
)
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.utils.html import strip_tags

from .models import Blog, WriterProfile


logger = logging.getLogger(__name__)


class RecaptchaResponseWidget(forms.HiddenInput):
    def value_from_datadict(self, data, files, name):
        return data.get('g-recaptcha-response') or super().value_from_datadict(data, files, name)


class RequiredFieldLoggingMixin:
    def full_clean(self):
        super().full_clean()

        for field_name, errors in self.errors.as_data().items():
            if any(error.code == 'required' for error in errors):
                logger.warning(
                    'Required form field missing. form=%s field=%s',
                    self.__class__.__name__,
                    field_name,
                )


class BaseSecurityForm(RequiredFieldLoggingMixin, forms.Form):
    def clean(self):
        cleaned_data = super().clean()
        for field_name, value in cleaned_data.items():
            if isinstance(value, str):
                cleaned_data[field_name] = value.strip()
        return cleaned_data


class WriterLoginForm(RequiredFieldLoggingMixin, AuthenticationForm):
    # Hidden fields are used for bot detection and server-side CAPTCHA validation.
    website = forms.CharField(required=False, widget=forms.HiddenInput())
    captcha_token = forms.CharField(
        error_messages={'required': 'Please complete the CAPTCHA verification.'},
        widget=RecaptchaResponseWidget(),
    )
    username = forms.CharField(
        max_length=150,
        strip=True,
        widget=forms.TextInput(attrs={'placeholder': 'Username', 'autocomplete': 'username'}),
    )
    password = forms.CharField(
        strip=True,
        widget=forms.PasswordInput(attrs={'placeholder': 'Password', 'autocomplete': 'current-password'}),
    )

    def clean(self):
        # Validate the visible form inputs plus bot protection checks before authentication proceeds.
        cleaned_data = super().clean()
        username = (cleaned_data.get('username') or '').strip()
        password = (cleaned_data.get('password') or '').strip()

        if not username:
            self.add_error('username', 'Username is required.')
        if not password:
            self.add_error('password', 'Password is required.')
        if cleaned_data.get('website'):
            raise forms.ValidationError('Invalid request.')
        return cleaned_data

    def clean_username(self):
        username = (self.cleaned_data.get('username') or '').strip()
        if not username:
            raise forms.ValidationError('Username is required.')
        if len(username) > 150:
            raise forms.ValidationError('Username is too long.')
        if not re.fullmatch(r'[A-Za-z0-9_.@+-]+', username):
            raise forms.ValidationError('Username contains invalid characters.')
        return username

    def clean_password(self):
        password = self.cleaned_data.get('password') or ''
        if not password.strip():
            raise forms.ValidationError('Password is required.')
        return password.strip()


class WriterRegistrationForm(RequiredFieldLoggingMixin, UserCreationForm):
    # Registration must reject bot traffic and require verification before the account becomes active.
    website = forms.CharField(required=False, widget=forms.HiddenInput())
    captcha_token = forms.CharField(
        error_messages={'required': 'Please complete the CAPTCHA verification.'},
        widget=RecaptchaResponseWidget(),
    )
    email = forms.EmailField(required=True, widget=forms.EmailInput(attrs={'placeholder': 'Email address'}))

    class Meta(UserCreationForm.Meta):
        model = get_user_model()
        fields = ('username', 'email')

    def save(self, commit=True):
        user = super().save(commit=False)
        user.is_active = False
        if commit:
            user.save()
        return user

    def clean_username(self):
        username = (self.cleaned_data.get('username') or '').strip()
        if not username:
            raise forms.ValidationError('Username is required.')
        if len(username) > 150:
            raise forms.ValidationError('Username is too long.')
        if not re.fullmatch(r'[A-Za-z0-9_.@+-]+', username):
            raise forms.ValidationError('Username contains invalid characters.')
        return username

    def clean_email(self):
        email = (self.cleaned_data.get('email') or '').strip().lower()
        if not email:
            raise forms.ValidationError('Email is required.')
        if get_user_model().objects.filter(email__iexact=email).exists():
            raise ValidationError('This email is already in use.')
        return email

    def clean(self):
        # Ensure the password confirmation matches and the honeypot/CAPTCHA checks are still enforced.
        cleaned_data = super().clean()
        password1 = cleaned_data.get('password1')
        password2 = cleaned_data.get('password2')
        if cleaned_data.get('website'):
            raise forms.ValidationError('Invalid request.')
        if password1 and password2 and password1 != password2:
            self.add_error('password2', 'Passwords do not match.')
        return cleaned_data


class BlogPostForm(RequiredFieldLoggingMixin, forms.ModelForm):
    class Meta:
        model = Blog
        fields = ('title', 'excerpt', 'content', 'cover_image', 'status')
        widgets = {
            'title': forms.TextInput(attrs={'placeholder': 'Post title'}),
            'excerpt': forms.Textarea(attrs={'rows': 3, 'placeholder': 'A short summary of your post'}),
            'content': forms.Textarea(attrs={'rows': 12, 'placeholder': 'Write your article here'}),
            'status': forms.Select(),
        }

    def clean_title(self):
        title = (self.cleaned_data.get('title') or '').strip()
        if not title:
            raise forms.ValidationError('Title is required.')
        if len(title) > 300:
            raise forms.ValidationError('Title is too long.')
        return title

    def clean_excerpt(self):
        excerpt = self.cleaned_data.get('excerpt') or ''
        cleaned = strip_tags(excerpt).strip()
        if len(cleaned) > 1000:
            raise forms.ValidationError('Excerpt is too long.')
        return cleaned

    def clean_content(self):
        content = self.cleaned_data.get('content') or ''
        cleaned = strip_tags(content).strip()
        if not cleaned:
            raise forms.ValidationError('Content is required.')
        if len(cleaned) < 50:
            raise forms.ValidationError('Content must be at least 50 characters long.')
        return cleaned

    def clean_status(self):
        status = self.cleaned_data.get('status')
        if status not in dict(Blog.STATUS_CHOICES):
            raise forms.ValidationError('Invalid publication status.')
        return status


class WriterProfileForm(RequiredFieldLoggingMixin, forms.ModelForm):
    class Meta:
        model = WriterProfile
        fields = ('bio', 'avatar')
        widgets = {
            'bio': forms.Textarea(attrs={'rows': 6, 'placeholder': 'Tell readers about yourself'}),
        }

    def clean_bio(self):
        bio = self.cleaned_data.get('bio') or ''
        cleaned = strip_tags(bio).strip()
        if len(cleaned) > 2000:
            raise forms.ValidationError('Bio is too long.')
        return cleaned


class WriterPasswordResetForm(RequiredFieldLoggingMixin, PasswordResetForm):
    def clean_email(self):
        email = (self.cleaned_data.get('email') or '').strip().lower()
        if not email:
            raise forms.ValidationError('Email is required.')
        if not get_user_model().objects.filter(email__iexact=email).exists():
            return email
        return email


class WriterSetPasswordForm(RequiredFieldLoggingMixin, SetPasswordForm):
    def clean_new_password2(self):
        password2 = self.cleaned_data.get('new_password2')
        if password2:
            try:
                validate_password(password2, user=self.user)
            except ValidationError as exc:
                raise forms.ValidationError(exc.messages[0])
        return password2

    def clean(self):
        cleaned_data = super().clean()
        password1 = cleaned_data.get('new_password1')
        password2 = cleaned_data.get('new_password2')

        if password1 and password2 and password1 != password2:
            self.add_error('new_password2', 'The two password fields didn’t match.')

        return cleaned_data


class AuthorPasswordChangeForm(RequiredFieldLoggingMixin, forms.Form):
    old_password = forms.CharField(
        label='Current password',
        strip=False,
        widget=forms.PasswordInput(attrs={'placeholder': 'Current password', 'autocomplete': 'current-password'}),
    )
    new_password1 = forms.CharField(
        label='New password',
        strip=False,
        widget=forms.PasswordInput(attrs={'placeholder': 'New password', 'autocomplete': 'new-password'}),
    )
    new_password2 = forms.CharField(
        label='Confirm new password',
        strip=False,
        widget=forms.PasswordInput(attrs={'placeholder': 'Confirm new password', 'autocomplete': 'new-password'}),
    )

    def __init__(self, user, *args, **kwargs):
        self.user = user
        super().__init__(*args, **kwargs)

    def clean_old_password(self):
        old_password = self.cleaned_data.get('old_password')
        if not self.user.check_password(old_password):
            raise forms.ValidationError('Your current password is incorrect.')
        return old_password

    def clean(self):
        cleaned_data = super().clean()
        password1 = cleaned_data.get('new_password1')
        password2 = cleaned_data.get('new_password2')

        if password1 and password2 and password1 != password2:
            self.add_error('new_password2', 'New passwords do not match.')

        if password1:
            try:
                validate_password(password1, user=self.user)
            except ValidationError as exc:
                self.add_error('new_password1', exc.messages[0])

        return cleaned_data

    def save(self):
        password = self.cleaned_data['new_password1']
        self.user.set_password(password)
        self.user.save(update_fields=['password'])
        return self.user
