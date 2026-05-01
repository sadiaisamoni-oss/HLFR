from django.contrib import admin
from .models import Badge, Donation, UserBadge


@admin.register(Donation)
class DonationAdmin(admin.ModelAdmin):
    list_display = ('id', 'food_name', 'donor_name', 'category', 'status', 'is_mine', 'created_at')
    list_filter = ('category', 'status', 'is_mine', 'created_at')
    search_fields = ('food_name', 'donor_name', 'location')
    readonly_fields = ('created_at',)


@admin.register(Badge)
class BadgeAdmin(admin.ModelAdmin):
    list_display = ('id', 'title', 'metric', 'threshold', 'sort_order', 'is_active')
    list_filter = ('metric', 'is_active')
    search_fields = ('title', 'description')


@admin.register(UserBadge)
class UserBadgeAdmin(admin.ModelAdmin):
    list_display = ('user', 'badge', 'earned_at')
    list_filter = ('badge', 'earned_at')
    search_fields = ('user__username', 'badge__title')
    readonly_fields = ('earned_at',)