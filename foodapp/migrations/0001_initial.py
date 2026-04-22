from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='Donation',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('food_name', models.CharField(max_length=200)),
                ('quantity', models.CharField(max_length=100)),
                ('location', models.CharField(max_length=200)),
                ('donor_name', models.CharField(default='Manual Entry', max_length=120)),
                ('is_mine', models.BooleanField(default=False)),
            ],
        ),
    ]
