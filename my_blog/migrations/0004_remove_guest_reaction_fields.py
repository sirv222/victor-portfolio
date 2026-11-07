import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('my_blog', '0003_alter_blogreaction_unique_together_and_more'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AlterUniqueTogether(
            name='blogreaction',
            unique_together={('post', 'user')},
        ),
        migrations.RemoveConstraint(
            model_name='blogreaction',
            name='unique_blog_user_reaction',
        ),
        migrations.RemoveConstraint(
            model_name='blogreaction',
            name='unique_blog_session_reaction',
        ),
        migrations.RemoveField(
            model_name='blogreaction',
            name='session_key',
        ),
        migrations.AlterField(
            model_name='blogreaction',
            name='user',
            field=models.ForeignKey(
                default=1,
                on_delete=django.db.models.deletion.CASCADE,
                related_name='blog_reactions',
                to=settings.AUTH_USER_MODEL,
            ),
            preserve_default=False,
        ),
    ]
