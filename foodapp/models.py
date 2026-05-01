from django.db import models
from django.contrib.auth.models import User

class Donation(models.Model):
    CATEGORY_CHOICES = [
        ('produce', 'Fresh Produce'),
        ('bakery', 'Bakery'),
        ('prepared', 'Prepared Meals'),
        ('dairy', 'Dairy and Eggs'),
        ('other', 'Other'),
    ]
    
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('confirmed', 'Confirmed'),
        ('cancelled', 'Cancelled'),
    ]

    user = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL, related_name='donations')
    food_name = models.CharField(max_length=200)
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES, default='other')
    quantity = models.CharField(max_length=100)
    location = models.CharField(max_length=200)
    donor_name = models.CharField(max_length=120, default='Manual Entry')
    is_mine = models.BooleanField(default=False)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    image = models.ImageField(upload_to='donations/%Y/%m/%d/', null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, null=True)

    def __str__(self):
        return self.food_name


class Badge(models.Model):
    METRIC_CHOICES = [
        ('shared', 'Items Shared'),
        ('requested', 'Items Requested'),
        ('activity', 'Total Activity'),
        ('points', 'Community Points'),
    ]

    icon = models.CharField(max_length=20, default='🏅')
    title = models.CharField(max_length=120)
    description = models.CharField(max_length=255, blank=True)
    metric = models.CharField(max_length=20, choices=METRIC_CHOICES)
    threshold = models.PositiveIntegerField(default=1)
    sort_order = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ('sort_order', 'id')

    def __str__(self):
        return f'{self.title} ({self.threshold}+)'


class UserBadge(models.Model):
    """Track which user has earned which badge"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='earned_badges')
    badge = models.ForeignKey(Badge, on_delete=models.CASCADE)
    earned_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'badge')
        ordering = ['-earned_at']

    def __str__(self):
        return f'{self.user.username} - {self.badge.title}'
