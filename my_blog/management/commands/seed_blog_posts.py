import random
from datetime import timedelta
from io import BytesIO

from django.contrib.auth import get_user_model
from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand
from django.utils import timezone
from PIL import Image, ImageDraw, ImageFont

from my_blog.models import Blog


CATEGORY_TEMPLATES = {
    'Design': [
        'Design systems that scale across product teams',
        'Accessibility patterns every UI team should revisit',
        'How to simplify product onboarding without losing clarity',
        'The value of spacing systems in modern interfaces',
        'Why visual consistency builds user trust',
        'Design critiques that actually improve outcomes',
        'A practical checklist for better landing pages',
        'Creating interfaces that feel premium and usable',
        'How to balance creativity and usability in design',
        'Design decisions that reduce friction for new users',
    ],
    'Development': [
        'Building maintainable code in a fast-moving startup',
        'How clean architecture reduces long-term maintenance cost',
        'Refactoring patterns that improve confidence in code',
        'The best debugging habits for noisy production issues',
        'Writing APIs that survive changing product requirements',
        'Small architecture decisions with large long-term impact',
        'Why test coverage matters more than raw speed',
        'A practical look at code reviews and team quality',
        'Making backend systems easier to scale safely',
        'What shipping small wins teaches engineering teams',
    ],
    'AI': [
        'How teams are using AI without losing product quality',
        'Prompt design patterns for better assistant workflows',
        'AI features that actually improve everyday workflows',
        'The ethics of automation in customer experience',
        'Keeping AI-driven products human-centered',
        'When to rely on rules instead of model predictions',
        'AI adoption lessons from product teams in motion',
        'Designing trustworthy AI-powered user experiences',
        'Why AI workflows need observability and review',
        'The real cost of shipping AI before validation',
    ],
    'Productivity': [
        'The weekly planning habits that reduce context switching',
        'How to ship focused work without burning out',
        'Turning scattered notes into a useful personal system',
        'The art of setting better work boundaries',
        'Why async communication improves team momentum',
        'Better habits for managing large backlogs',
        'How to review progress without chasing perfect plans',
        'Small rituals that make long-term work sustainable',
        'Productivity lessons from engineering teams with strong flow',
        'The difference between busy work and valuable work',
    ],
    'Business': [
        'Identifying the right product problem before building',
        'Why clarity beats complexity in business storytelling',
        'How service-led companies earn trust differently',
        'The business case for investing in developer experience',
        'Pricing decisions that support sustainable growth',
        'Turning customer feedback into stronger product direction',
        'Foundational habits for healthier product leadership',
        'Why communication quality impacts execution speed',
        'Balancing user goals with business realities',
        'A realistic view of building momentum in early-stage work',
    ],
    'Security': [
        'Security mindsets every product team should share',
        'The most overlooked risks in small web applications',
        'How secure defaults reduce operational headaches',
        'Designing authentication systems without unnecessary complexity',
        'Why secure coding habits matter even in small teams',
        'The impact of weak review habits on system trust',
        'Security practices that improve team confidence',
        'How to think about risk before it becomes a breach',
        'Practical lessons from reviewing access control flows',
        'The quiet cost of ignoring data hygiene',
    ],
    'Data': [
        'What good analytics dashboards actually reveal',
        'How to structure product data for real decisions',
        'Turning raw signals into valuable product insight',
        'The difference between tracking events and learning from them',
        'A healthier approach to experiments for small teams',
        'When data becomes a product decision tool instead of noise',
        'Why quality metrics beat vanity metrics over time',
        'Interpreting customer behavior with more context',
        'Lessons from building reliable measurement pipelines',
        'Data strategies that support product thinking',
    ],
    'Creative': [
        'Creative systems that support consistency without rigidity',
        'Turning ideas into repeatable creative direction',
        'What makes personal projects feel authentic and alive',
        'Creative workflow tips for people working alone',
        'Building momentum through small creative experiments',
        'How to keep curiosity alive while shipping work',
        'A better way to manage inspiration without losing focus',
        'Why storytelling matters in technical work too',
        'Creative routines that help ideas become output',
        'The role of reflection in improving creative work',
    ],
    'DevOps': [
        'Reliability habits that make delivery teams calmer',
        'Why deployment pipelines should be transparent and simple',
        'The value of observability in everyday engineering work',
        'How small automation wins reduce operational stress',
        'Making incident response easier through better tooling',
        'What healthy release practices look like in practice',
        'How to design systems that are easier to troubleshoot',
        'Reducing platform complexity without reducing safety',
        'The role of automation in resilient development teams',
        'Why operational clarity is part of product quality',
    ],
    'Leadership': [
        'How strong technical leadership creates calmer teams',
        'The communication habits that improve decision quality',
        'What healthy product direction feels like in practice',
        'Leadership lessons from building cross-functional momentum',
        'Why clarity is the most underrated leadership tool',
        'How to keep a team aligned without micromanaging',
        'The role of trust in high-performing technical teams',
        'Making strategy practical for day-to-day execution',
        'Managing tradeoffs without draining team energy',
        'Why good leadership creates more resilient delivery',
    ],
}


def build_post_body(category, title):
    return (
        f"{title} explores how {category.lower()} thinking can improve a real product or workflow. "
        "Good teams do not rely on inspiration alone; they build repeatable systems that make execution clearer. "
        "This article walks through the practical decisions behind creating a better experience, whether you are "
        "working on a startup product, a client project, or a personal product initiative. "
        "By focusing on use cases, priorities, and feedback loops, teams can make progress without adding chaos. "
        "The goal is not perfection, but sustainable quality. "
        "When teams define problems clearly and test decisions early, they reduce rework and sharpen product direction. "
        "This gives space for stronger outcomes across design, engineering, and business operations."
    )


def generate_cover_image(category, title):
    width, height = 1200, 720
    accent_map = {
        'Design': (124, 58, 237),
        'Development': (34, 197, 94),
        'AI': (59, 130, 246),
        'Productivity': (249, 115, 22),
        'Business': (236, 72, 153),
        'Security': (239, 68, 68),
        'Data': (14, 165, 233),
        'Creative': (168, 85, 247),
        'DevOps': (45, 212, 191),
        'Leadership': (251, 191, 36),
    }
    accent = accent_map.get(category, (124, 58, 237))

    seed = sum((index + 1) * ord(character) for index, character in enumerate(title))
    rng = random.Random(seed)

    image = Image.new('RGBA', (width, height), color=(10, 12, 20, 255))
    draw = ImageDraw.Draw(image)

    for y in range(height):
        ratio = y / height
        red = int(10 + (accent[0] - 10) * ratio)
        green = int(12 + (accent[1] - 12) * ratio)
        blue = int(20 + (accent[2] - 20) * ratio)
        draw.line((0, y, width, y), fill=(red, green, blue))

    for index in range(6):
        cx = rng.randint(150, 1050)
        cy = rng.randint(90, 620)
        radius = rng.randint(110, 250)
        alpha = rng.randint(18, 38)
        overlay = Image.new('RGBA', (width, height), (0, 0, 0, 0))
        overlay_draw = ImageDraw.Draw(overlay)
        overlay_draw.ellipse((cx - radius, cy - radius, cx + radius, cy + radius), fill=(accent[0], accent[1], accent[2], alpha))
        image = Image.alpha_composite(image, overlay)

    for i in range(12):
        x1 = rng.randint(0, width)
        y1 = rng.randint(0, height)
        x2 = x1 + rng.randint(80, 240)
        y2 = y1 + rng.randint(-60, 60)
        line_color = (255, 255, 255, 40)
        draw.line((x1, y1, x2, y2), fill=line_color, width=2)

    card_padding = 56
    card = Image.new('RGBA', (width - card_padding * 2, height - card_padding * 2), (12, 15, 25, 180))
    card_draw = ImageDraw.Draw(card)
    card_draw.rounded_rectangle((0, 0, card.width, card.height), radius=34, fill=(10, 13, 22, 185))
    card_draw.rounded_rectangle((20, 20, card.width - 20, card.height - 20), radius=28, outline=(255, 255, 255, 35), width=2)
    image = Image.alpha_composite(image, card)

    draw = ImageDraw.Draw(image)
    label = category.upper()
    pill = (110, 95, 260, 130)
    draw.rounded_rectangle(pill, radius=16, fill=(255, 255, 255, 28))

    try:
        font = ImageFont.truetype('DejaVuSans-Bold.ttf', 42)
        small_font = ImageFont.truetype('DejaVuSans.ttf', 24)
        badge_font = ImageFont.truetype('DejaVuSans-Bold.ttf', 18)
    except OSError:
        font = ImageFont.load_default()
        small_font = ImageFont.load_default()
        badge_font = ImageFont.load_default()

    draw.text((130, 108), label, fill=(255, 255, 255), font=badge_font)

    title_lines = []
    current_line = ''
    for word in title.split():
        candidate = f'{current_line} {word}'.strip()
        if len(candidate) <= 26:
            current_line = candidate
        else:
            title_lines.append(current_line)
            current_line = word
    if current_line:
        title_lines.append(current_line)

    display_lines = title_lines[:3]
    if len(display_lines) > 3:
        display_lines = display_lines[:2]
        display_lines[-1] = display_lines[-1] + '…'

    start_y = 180
    for line in display_lines:
        draw.text((110, start_y), line[:30], fill=(255, 255, 255), font=font)
        start_y += 60

    bottom_bar = Image.new('RGBA', (width, 120), (0, 0, 0, 0))
    bottom_draw = ImageDraw.Draw(bottom_bar)
    bottom_draw.rounded_rectangle((90, 560, 950, 640), radius=24, fill=(255, 255, 255, 18))
    image = Image.alpha_composite(image, bottom_bar)

    draw = ImageDraw.Draw(image)
    draw.text((118, 578), 'INSIGHT • IDEAS • ENGINEERING', fill=(220, 230, 255), font=small_font)

    safe_name = ''.join(ch if ch.isalnum() else '-' for ch in title.lower())
    safe_name = safe_name.strip('-')[:40] or 'blog-cover'

    buffer = BytesIO()
    image = image.convert('RGB')
    image.save(buffer, format='PNG')
    return ContentFile(buffer.getvalue(), name=f'{category.lower()}-{safe_name}.png')


class Command(BaseCommand):
    help = 'Populate the blog table with 100 published posts across several categories.'

    def handle(self, *args, **options):
        User = get_user_model()
        author = User.objects.filter(is_staff=True).first() or User.objects.order_by('id').first()

        if author is None:
            author = User.objects.create_user(username='seed_blog_author', password='SecurePass123!')

        published_ids = list(Blog.objects.filter(status='published').order_by('-publish_date').values_list('id', flat=True))
        if len(published_ids) > 100:
            extra_ids = published_ids[100:]
            Blog.objects.filter(id__in=extra_ids).delete()
            self.stdout.write(self.style.WARNING(f'Removed {len(extra_ids)} extra published posts to keep the blog list at 100 total.'))

        created_count = 0
        for category_index, (category, titles) in enumerate(CATEGORY_TEMPLATES.items(), start=1):
            for item_index, base_title in enumerate(titles, start=1):
                if Blog.objects.filter(status='published').count() >= 100:
                    break

                title = f'{base_title} [{category}]'
                if Blog.objects.filter(title=title).exists():
                    continue

                excerpt = (
                    f"A practical look at {category.lower()} strategy, workflow, and real-world execution for modern teams."
                )
                content = build_post_body(category, base_title)
                days_ago = ((category_index - 1) * 10) + item_index

                Blog.objects.create(
                    title=title,
                    excerpt=excerpt,
                    content=content,
                    cover_image=generate_cover_image(category, title),
                    author=author,
                    status='published',
                    publish_date=timezone.now() - timedelta(days=days_ago),
                )
                created_count += 1
            if Blog.objects.filter(status='published').count() >= 100:
                break

        for post in Blog.objects.filter(status='published'):
            if not post.cover_image:
                category = 'Design'
                if ' [' in post.title and post.title.endswith(']'):
                    category = post.title.rsplit('[', 1)[1][:-1]
                post.cover_image = generate_cover_image(category, post.title)
                post.save(update_fields=['cover_image'])

        final_total = Blog.objects.filter(status='published').count()
        self.stdout.write(
            self.style.SUCCESS(
                f'Created {created_count} new posts. Blog database is now at {final_total} published posts and every post has a cover image.'
            )
        )
