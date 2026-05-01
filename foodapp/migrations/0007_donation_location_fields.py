# This migration was removed - Location features removed from Donation model

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('foodapp', '0006_donation_image_userbadge'),
    ]

    operations = [
        # Location fields removed - simplified model
    ]
