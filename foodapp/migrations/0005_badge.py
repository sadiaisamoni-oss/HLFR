from django.db import migrations, models


def seed_default_badges(apps, schema_editor):
    Badge = apps.get_model('foodapp', 'Badge')
    defaults = [
        {
            'icon': '🌟',
            'title': 'Top Donor',
            'description': 'Share at least 5 items',
            'metric': 'shared',
            'threshold': 5,
            'sort_order': 1,
            'is_active': True,
        },
        {
            'icon': '🤝',
            'title': 'Community Hero',
            'description': 'Reach 10 total activities',
            'metric': 'activity',
            'threshold': 10,
            'sort_order': 2,
            'is_active': True,
        },
        {
            'icon': '♻️',
            'title': 'Waste Warrior',
            'description': 'Request at least 3 items',
            'metric': 'requested',
            'threshold': 3,
            'sort_order': 3,
            'is_active': True,
        },
        {
            'icon': '🔥',
            'title': 'Momentum Builder',
            'description': 'Complete 3 total activities',
            'metric': 'activity',
            'threshold': 3,
            'sort_order': 4,
            'is_active': True,
        },
    ]

    for entry in defaults:
        Badge.objects.get_or_create(title=entry['title'], defaults=entry)


class Migration(migrations.Migration):

    dependencies = [
        ('foodapp', '0004_donation_status'),
    ]

    operations = [
        migrations.CreateModel(
            name='Badge',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('icon', models.CharField(default='🏅', max_length=20)),
                ('title', models.CharField(max_length=120)),
                ('description', models.CharField(blank=True, max_length=255)),
                ('metric', models.CharField(choices=[('shared', 'Items Shared'), ('requested', 'Items Requested'), ('activity', 'Total Activity'), ('points', 'Community Points')], max_length=20)),
                ('threshold', models.PositiveIntegerField(default=1)),
                ('sort_order', models.PositiveIntegerField(default=0)),
                ('is_active', models.BooleanField(default=True)),
            ],
            options={
                'ordering': ('sort_order', 'id'),
            },
        ),
        migrations.RunPython(seed_default_badges, migrations.RunPython.noop),
    ]
