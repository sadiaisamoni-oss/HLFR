"""Management command to populate initial badges"""

from django.core.management.base import BaseCommand
from foodapp.models import Badge


class Command(BaseCommand):
    help = 'Populate initial badges for the application'

    def handle(self, *args, **kwargs):
        badges_data = [
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
            {
                'icon': '👑',
                'title': 'Generous Soul',
                'description': 'Share 10 or more items',
                'metric': 'shared',
                'threshold': 10,
                'sort_order': 5,
                'is_active': True,
            },
            {
                'icon': '💎',
                'title': 'Platinum Member',
                'description': 'Earn 100+ community points',
                'metric': 'points',
                'threshold': 100,
                'sort_order': 6,
                'is_active': True,
            },
        ]

        for badge_data in badges_data:
            badge, created = Badge.objects.get_or_create(
                title=badge_data['title'],
                defaults=badge_data
            )
            if created:
                self.stdout.write(
                    self.style.SUCCESS(f'Created badge: {badge.title}')
                )
            else:
                self.stdout.write(
                    self.style.WARNING(f'Badge already exists: {badge.title}')
                )

        self.stdout.write(
            self.style.SUCCESS('Successfully populated badges!')
        )
