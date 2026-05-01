# Generated migration for image field and UserBadge model

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('foodapp', '0005_badge'),
    ]

    operations = [
        migrations.AddField(
            model_name='donation',
            name='image',
            field=models.ImageField(blank=True, null=True, upload_to='donations/%Y/%m/%d/'),
        ),
        migrations.AddField(
            model_name='donation',
            name='created_at',
            field=models.DateTimeField(auto_now_add=True, null=True),
        ),
        migrations.CreateModel(
            name='UserBadge',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('earned_at', models.DateTimeField(auto_now_add=True)),
                ('badge', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='foodapp.badge')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='earned_badges', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'ordering': ['-earned_at'],
                'unique_together': {('user', 'badge')},
            },
        ),
    ]
