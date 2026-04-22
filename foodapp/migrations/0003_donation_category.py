from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('foodapp', '0002_donation_user'),
    ]

    operations = [
        migrations.AddField(
            model_name='donation',
            name='category',
            field=models.CharField(choices=[('produce', 'Fresh Produce'), ('bakery', 'Bakery'), ('prepared', 'Prepared Meals'), ('dairy', 'Dairy and Eggs'), ('other', 'Other')], default='other', max_length=20),
        ),
    ]
