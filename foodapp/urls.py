from django.contrib.auth import views as auth_views
from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('available/', views.available_food, name='available'),
    path('request-pickup/<int:donation_id>/', views.request_pickup, name='request_pickup'),
    path('cancel-pickup/<int:donation_id>/', views.cancel_my_pickup_request, name='cancel_my_pickup'),
    path('signup/', views.signup, name='signup'),
    path('signin/', views.signin, name='signin'),
    path('password-reset/', auth_views.PasswordResetView.as_view(template_name='registration/password_reset_form.html'), name='password_reset'),
    path('password-reset/done/', auth_views.PasswordResetDoneView.as_view(template_name='registration/password_reset_done.html'), name='password_reset_done'),
    path('reset/<uidb64>/<token>/', auth_views.PasswordResetConfirmView.as_view(template_name='registration/password_reset_confirm.html'), name='password_reset_confirm'),
    path('reset/done/', auth_views.PasswordResetCompleteView.as_view(template_name='registration/password_reset_complete.html'), name='password_reset_complete'),
    path('signout/', views.signout_view, name='signout'),
    path('list-food/', views.list_food, name='list_food'),
    path('my-donations/', views.my_donations, name='my_donations'),
    path('available-food/', views.available_food, name='available_food'),
    path('admin-panel/', views.admin_panel, name='admin_panel'),
    path('admin-panel/delete/<int:donation_id>/', views.admin_delete_donation, name='admin_delete_donation'),
    path('admin-panel/delete-bulk/', views.admin_bulk_delete_donations, name='admin_bulk_delete_donations'),
    path('admin-panel/confirm/<int:donation_id>/', views.confirm_pickup_request, name='confirm_pickup'),
    path('admin-panel/cancel/<int:donation_id>/', views.cancel_pickup_request, name='cancel_pickup'),
    path('profile/', views.profile, name='profile'),
]