from django.core.exceptions import ValidationError
from django.core.validators import (
    MaxValueValidator,
    MinValueValidator,
    URLValidator,
    validate_email,
)
from django.db import models


def validate_social_link(value):
    """Ensure a social link is either a mailto: email or an HTTP/HTTPS URL."""
    if value is None:
        return

    normalized_value = str(value).strip()
    if not normalized_value:
        return

    if normalized_value.startswith('mailto:'):
        email = normalized_value.removeprefix('mailto:').strip()
        try:
           validate_email(email)
        except ValidationError as exc:
           raise ValidationError('Email is not valid.') from exc
        return

    try:
        URLValidator(schemes=['http', 'https'])(normalized_value)
    except ValidationError as exc:
        raise ValidationError(
           'Value must start with "mailto:" or be a valid HTTP/HTTPS URL.'
        ) from exc


class PersonalDetails(models.Model):
    first_name = models.CharField(max_length=300)
    last_name = models.CharField(max_length=300)
    year_of_experience = models.PositiveIntegerField(default=1, null=True, blank=True)
    resume = models.FileField(upload_to='resume/%Y/%m/', blank=True, null=True)
    profile_pics = models.ImageField(upload_to='profile_pics/%Y/%m/', blank=True, null=True)
    profession = models.CharField(max_length=300)
    contributions = models.IntegerField(null=True, blank=True)
    clients = models.IntegerField(null=True, blank=True)

    @property
    def full_name(self):
        return f'{self.first_name} {self.last_name}'.strip()

    def __str__(self):
        return self.full_name


class Contact(models.Model):
    AVAILABILITY_CHOICES = [
        ('AVAILABLE', 'AVAILABLE'),
        ('BUSY', 'BUSY'),
    ]

    address = models.TextField()
    email = models.EmailField()
    phone = models.CharField(max_length=300)
    availability = models.CharField(max_length=300, choices=AVAILABILITY_CHOICES)

    def __str__(self):
        return self.email


class SocialLinks(models.Model):
    name = models.CharField(max_length=300)
    logo = models.CharField(max_length=300, blank=True, null=True)
    link = models.CharField(
        max_length=300,
        blank=True,
        null=True,
        validators=[validate_social_link],
    )
    contact = models.ForeignKey(
        Contact,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='socials',
    )

    def __str__(self):
        return self.name


class Technology(models.Model):
    name = models.CharField(max_length=300)
    logo = models.CharField(max_length=300, blank=True, null=True)
    knowledge_percent = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        validators=[MinValueValidator(1), MaxValueValidator(100)],
        null=True,
        blank=True,
    )
    year_of_experience = models.PositiveIntegerField(default=1, null=True, blank=True)

    def __str__(self):
        return self.name


class Skill(models.Model):
    visual_rep = models.CharField(max_length=50, blank=True, null=True)
    name = models.CharField(max_length=300)
    skill_stack = models.ManyToManyField(Technology, related_name='skills')
    description = models.TextField(blank=True, null=True)

    def __str__(self):
        return self.name


class ProjectCategory(models.Model):
    CATEGORY_CHOICES = [
        ('web', 'web'),
        ('mobile', 'mobile'),
        ('data', 'data'),
        ('oss', 'oss'),
    ]

    choice = models.CharField(
        max_length=300,
        null=True,
        blank=True,
        choices=CATEGORY_CHOICES,
    )

    def __str__(self):
        return self.choice or 'Uncategorized'


class Projects(models.Model):
    date = models.DateField(auto_now_add=True, blank=True, null=True)
    project_visual = models.ImageField(upload_to='projects/%Y/%m/', blank=True, null=True)
    project_title = models.CharField(max_length=300)
    project_description = models.TextField()
    project_stack = models.ManyToManyField(Technology)
    project_url = models.URLField(null=True, blank=True)
    project_code = models.URLField(null=True, blank=True)
    project_category = models.ManyToManyField(ProjectCategory, related_name='projects')

    def __str__(self):
        return self.project_title


class About(models.Model):
    heading = models.TextField()
    body = models.TextField()

    def __str__(self):
        return self.heading[:50]


class Experience(models.Model):
    start_date = models.DateField()
    date = models.DateField(blank=True, null=True)
    role = models.CharField(max_length=300)
    company = models.CharField(max_length=300)
    role_description = models.TextField()

    @property
    def end_date(self):
        if self.date is not None:
           return self.date
        return 'Present'

    def __str__(self):
        return self.company


class Education(models.Model):
    start_date = models.DateField()
    date = models.DateField(null=True, blank=True)
    certificate_title = models.CharField(max_length=500)
    institution = models.CharField(max_length=500)
    certificate_description = models.TextField()

    @property
    def end_date(self):
        if self.date is not None:
           return self.date
        return 'Present'

    def __str__(self):
        return self.institution


class Value(models.Model):
    value_name = models.CharField(max_length=500)
    value_description = models.TextField()

    def __str__(self):
        return self.value_name


class FAQ(models.Model):
    question = models.TextField()
    answer = models.TextField()

    def __str__(self):
        return self.question