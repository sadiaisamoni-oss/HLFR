from django.contrib import admin
from django.urls import path
from django.shortcuts import render

# Functions to show pages
def home(request):
    return render(request, 'index.html')

def available_food(request):
    return render(request, 'available-food.html')

def signup(request):
    return render(request, 'signup.html')

def signin(request):
    return render(request, 'signin.html')

def list_food(request):
    return render(request, 'list-food.html')

def my_donations(request):
    return render(request, 'my-donations.html')

def admin_panel(request):
    return render(request, 'admin-dashboard.html')

def profile(request):
    return render(request, 'profile.html')

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', home, name='home'),                     
    path('available/', available_food, name='available'), 
    path('signup/', signup, name='signup'),
    path('signin/', signin, name='signin'),
    path('list-food/', list_food, name='list_food'),
    path('my-donations/', my_donations, name='my_donations'),
    path('admin-panel/', admin_panel, name='admin_panel'),
    path('profile/', profile, name='profile'),
]