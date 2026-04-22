from django.contrib import admin
from .models import Badge


@admin.register(Badge)
class BadgeAdmin(admin.ModelAdmin):
    list_display = ('id', 'title', 'metric', 'threshold', 'sort_order', 'is_active')
    list_filter = ('metric', 'is_active')
    search_fields = ('title', 'description')