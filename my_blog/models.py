from django.conf import settings
from django.db import models
from django.urls import reverse
from django.utils import timezone
from django.utils.text import slugify


class WriterProfile(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='writer_profile',
    )
    bio = models.TextField(blank=True, default='')
    avatar = models.ImageField(upload_to='writers/%Y/%m/', blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.user.get_full_name() or self.user.username


class Blog(models.Model):
    STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('published', 'Published'),
    ]

    title = models.CharField(max_length=300)
    slug = models.SlugField(max_length=350, unique=True, blank=True)
    excerpt = models.TextField(blank=True, default='')
    content = models.TextField()
    cover_image = models.ImageField(upload_to='blog/%Y/%m/', blank=True, null=True)
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='blog_posts',
    )
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    publish_date = models.DateTimeField(blank=True, null=True)

    class Meta:
        ordering = ['-publish_date', '-created_at']

    def __str__(self):
        return self.title

    def get_absolute_url(self):
        return reverse('blog_post_detail', kwargs={'slug': self.slug})

    @property
    def likes_count(self):
        return self.reactions.filter(reaction='like').count()

    @property
    def dislikes_count(self):
        return self.reactions.filter(reaction='dislike').count()

    @property
    def comments_count(self):
        return self.comments.count()

    def save(self, *args, **kwargs):
        if not self.slug:
            base_slug = slugify(self.title)
            slug = base_slug or 'blog-post'
            counter = 1
            candidate = slug
            while Blog.objects.filter(slug=candidate).exclude(pk=self.pk).exists():
                candidate = f'{slug}-{counter}'
                counter += 1
            self.slug = candidate

        if self.status == 'published' and not self.publish_date:
            self.publish_date = timezone.now()
        elif self.status != 'published':
            self.publish_date = None

        super().save(*args, **kwargs)


class BlogReaction(models.Model):
    REACTION_CHOICES = [
        ('like', 'Like'),
        ('dislike', 'Dislike'),
    ]

    post = models.ForeignKey(Blog, on_delete=models.CASCADE, related_name='reactions')
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='blog_reactions',
        null=True,
        blank=True,
    )
    session_key = models.CharField(max_length=64, blank=True, null=True, db_index=True)
    reaction = models.CharField(max_length=10, choices=REACTION_CHOICES)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['post', 'user'],
                condition=models.Q(user__isnull=False),
                name='unique_blog_user_reaction',
            ),
            models.UniqueConstraint(
                fields=['post', 'session_key'],
                condition=models.Q(session_key__isnull=False),
                name='unique_blog_session_reaction',
            ),
        ]

    def __str__(self):
        actor = self.user.username if self.user else f'session:{self.session_key}'
        return f'{actor} {self.reaction}d {self.post.title}'


class BlogComment(models.Model):
    post = models.ForeignKey(Blog, on_delete=models.CASCADE, related_name='comments')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='blog_comments')
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f'Comment on {self.post.title}' 