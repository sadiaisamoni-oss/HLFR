import logging

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from django.core.paginator import Paginator
from django.db.models import Q
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from django.utils.http import url_has_allowed_host_and_scheme
from .models import Donation

audit_logger = logging.getLogger('foodapp.audit')

def home(request):
    total_donations = Donation.objects.filter(is_mine=True).count()
    registered_donor_count = Donation.objects.filter(is_mine=True, user__isnull=False).values('user_id').distinct().count()
    manual_donor_count = (
        Donation.objects.filter(is_mine=True, user__isnull=True)
        .exclude(donor_name__isnull=True)
        .exclude(donor_name__exact='')
        .values('donor_name')
        .distinct()
        .count()
    )
    total_donors = registered_donor_count + manual_donor_count
    my_donations_count = total_donations
    other_donations_count = Donation.objects.filter(is_mine=False, user__isnull=False).exclude(status='cancelled').count()
    rescued_items = total_donations
    weekly_pickups = other_donations_count

    context = {
        'total_donations': total_donations,
        'total_donors': total_donors,
        'my_donations_count': my_donations_count,
        'other_donations_count': other_donations_count,
        'rescued_items': rescued_items,
        'weekly_pickups': weekly_pickups,
    }
    return render(request, 'index.html', context)


@login_required(login_url='signin')
def list_food(request):
    if request.method == 'POST':
        food_name = request.POST.get('food_name')
        category = request.POST.get('category') or 'other'
        quantity = request.POST.get('quantity')
        location = request.POST.get('location')
        donor_name = request.POST.get('donor_name')
        donor_name = donor_name or (request.user.get_full_name() or request.user.username)

        Donation.objects.create(
            user=request.user,
            food_name=food_name,
            category=category,
            quantity=quantity,
            location=location,
            donor_name=donor_name,
            is_mine=True,
        )

        return redirect('my_donations')

    return render(request, 'list-food.html')


def my_donations(request):
    if request.user.is_authenticated:
        listed_data = Donation.objects.filter(user=request.user, is_mine=True).order_by('-id')
        pickup_data = Donation.objects.filter(user=request.user, is_mine=False).exclude(status='cancelled').order_by('-id')
    else:
        listed_data = Donation.objects.filter(is_mine=True).order_by('-id')
        pickup_data = Donation.objects.none()
    total_my = listed_data.count()
    total_all = Donation.objects.filter(is_mine=True).count()
    context = {
        'data': listed_data,
        'pickup_data': pickup_data,
        'total_my': total_my,
        'total_all': total_all,
        'my_share_percent': int((total_my / total_all) * 100) if total_all else 0,
    }
    return render(request, 'my-donations.html', context)


def available_food(request):
    data = Donation.objects.filter(is_mine=True).order_by('-id')
    keyword = request.GET.get('searchQuery', '').strip()
    category = request.GET.get('category', '').strip()

    if keyword:
        data = data.filter(
            Q(food_name__icontains=keyword)
            | Q(quantity__icontains=keyword)
            | Q(location__icontains=keyword)
            | Q(donor_name__icontains=keyword)
        )

    if category:
        data = data.filter(category=category)

    if request.user.is_authenticated:
        my_requests = Donation.objects.filter(user=request.user, is_mine=False).exclude(status='cancelled')
        request_lookup = {
            (
                item.food_name,
                item.category,
                item.quantity,
                item.location,
                item.donor_name,
            ): item.id
            for item in my_requests
        }
        for item in data:
            key = (item.food_name, item.category, item.quantity, item.location, item.donor_name)
            matched_request_id = request_lookup.get(key)
            item.requested_by_user = bool(matched_request_id)
            item.user_request_id = matched_request_id
    else:
        for item in data:
            item.requested_by_user = False
            item.user_request_id = None

    context = {
        'data': data,
        'searchQuery': keyword,
        'category': category,
    }
    return render(request, 'available-food.html', context)


def request_pickup(request, donation_id):
    if request.method != 'POST':
        return redirect('available')

    if not request.user.is_authenticated:
        messages.error(request, 'Please sign in to request a pickup.')
        signin_url = f"{reverse('signin')}?next={reverse('available')}"
        return redirect(signin_url)

    donation = get_object_or_404(Donation, id=donation_id)

    if donation.user_id == request.user.id and donation.user_id is not None:
        messages.error(request, 'You cannot request pickup for your own listing.')
        return redirect('available')

    existing_pickup_request = Donation.objects.filter(
        user=request.user,
        food_name=donation.food_name,
        category=donation.category,
        quantity=donation.quantity,
        location=donation.location,
        donor_name=donation.donor_name,
        is_mine=False,
    ).exists()
    if existing_pickup_request:
        messages.warning(request, 'You have already requested pickup for this listing.')
        return redirect('available')

    Donation.objects.create(
        user=request.user,
        food_name=donation.food_name,
        category=donation.category,
        quantity=donation.quantity,
        location=donation.location,
        donor_name=donation.donor_name,
        is_mine=False,
    )
    messages.success(request, f'Pickup request submitted for {donation.food_name}.')
    return redirect('my_donations')


@login_required(login_url='signin')
def cancel_my_pickup_request(request, donation_id):
    """Allow a user to cancel their own pickup request."""
    if request.method != 'POST':
        return redirect('my_donations')

    pickup_request = get_object_or_404(Donation, id=donation_id, user=request.user, is_mine=False)
    if pickup_request.status == 'cancelled':
        messages.warning(request, 'This pickup request is already cancelled.')
    else:
        pickup_request.status = 'cancelled'
        pickup_request.save(update_fields=['status'])
        messages.success(request, f'Pickup request for {pickup_request.food_name} cancelled.')
        audit_logger.info(
            'user_cancel_pickup user=%s donation_id=%s food_name=%s',
            request.user.username,
            pickup_request.id,
            pickup_request.food_name,
        )

    next_url = request.POST.get('next', '').strip()
    if next_url and url_has_allowed_host_and_scheme(next_url, allowed_hosts={request.get_host()}):
        return redirect(next_url)
    return redirect('my_donations')


def signup(request):
    if request.user.is_authenticated:
        return redirect('profile')

    if request.method == 'POST':
        first_name = request.POST.get('first_name', '').strip()
        last_name = request.POST.get('last_name', '').strip()
        email = request.POST.get('email', '').strip().lower()
        password = request.POST.get('password', '')
        confirm_password = request.POST.get('confirm_password', '')

        if not email or not password:
            messages.error(request, 'Email and password are required.')
            return render(request, 'signup.html')

        if password != confirm_password:
            messages.error(request, 'Passwords do not match.')
            return render(request, 'signup.html')

        if User.objects.filter(username=email).exists():
            messages.error(request, 'An account with this email already exists.')
            return render(request, 'signup.html')

        User.objects.create_user(username=email, email=email, password=password, first_name=first_name, last_name=last_name)
        messages.success(request, 'Account created successfully. Please sign in.')
        return redirect('signin')

    return render(request, 'signup.html')


def signin(request):
    next_url = request.GET.get('next', '').strip() or request.POST.get('next', '').strip()

    if request.user.is_authenticated:
        if next_url and url_has_allowed_host_and_scheme(next_url, allowed_hosts={request.get_host()}):
            return redirect(next_url)
        return redirect('profile')

    if request.method == 'POST':
        email = request.POST.get('email', '').strip().lower()
        password = request.POST.get('password', '')
        user = authenticate(request, username=email, password=password)

        if user is not None:
            login(request, user)
            if request.POST.get('remember'):
                request.session.set_expiry(60 * 60 * 24 * 14)
            else:
                request.session.set_expiry(0)
            if next_url and url_has_allowed_host_and_scheme(next_url, allowed_hosts={request.get_host()}):
                return redirect(next_url)
            return redirect('profile')

        messages.error(request, 'Login failed. Check your email and password.')

    return render(request, 'signin.html', {'next': next_url})


def signout_view(request):
    logout(request)
    return redirect('home')


def profile(request):
    total_donations = Donation.objects.count()

    if request.user.is_authenticated:
        my_donations_count = Donation.objects.filter(user=request.user, is_mine=True).count()
        received_items = Donation.objects.filter(user=request.user, is_mine=False).exclude(status='cancelled').count()
        latest_donor = request.user.get_full_name() or request.user.username or 'Community Member'
        recent_donations = Donation.objects.filter(user=request.user).order_by('-id')[:5]
        profile_location = request.user.email or 'Local Community'
    else:
        my_donations_count = Donation.objects.filter(is_mine=True).count()
        received_items = Donation.objects.filter(is_mine=False, user__isnull=False).exclude(status='cancelled').count()
        latest_donor = Donation.objects.order_by('-id').values_list('donor_name', flat=True).first() or 'Community Member'
        recent_donations = Donation.objects.order_by('-id')[:5]
        profile_location = 'Local Community'

    activity_total = my_donations_count + received_items
    community_points = (my_donations_count * 10) + (received_items * 6)

    if activity_total:
        rating = f"{min(5.0, 3.0 + (my_donations_count * 0.2) + (received_items * 0.1)):.1f}"
    else:
        rating = '0.0'

    monthly_goal_target = 20
    community_goal_target = 50
    monthly_goal_percent = min(100, int((my_donations_count / monthly_goal_target) * 100))
    community_goal_percent = min(100, int((activity_total / community_goal_target) * 100))

    context = {
        'profile_name': latest_donor,
        'profile_location': profile_location,
        'items_shared': my_donations_count,
        'items_received': received_items,
        'community_points': community_points,
        'rating': rating,
        'recent_donations': recent_donations,
        'monthly_goal_percent': monthly_goal_percent,
        'community_goal_percent': community_goal_percent,
        'monthly_goal_target': monthly_goal_target,
        'community_goal_target': community_goal_target,
    }
    return render(request, 'profile.html', context)


@login_required(login_url='signin')
def admin_panel(request):
    if not request.user.is_staff:
        messages.error(request, 'This page is restricted to staff users.')
        return redirect('home')

    donations = Donation.objects.all().order_by('-id')
    query = request.GET.get('q', '').strip()
    if query:
        donations = donations.filter(
            Q(food_name__icontains=query)
            | Q(donor_name__icontains=query)
            | Q(quantity__icontains=query)
            | Q(location__icontains=query)
            | Q(category__icontains=query)
            | Q(user__username__icontains=query)
        )

    paginator = Paginator(donations, 10)
    page_obj = paginator.get_page(request.GET.get('page'))

    can_manage = request.user.is_authenticated and request.user.is_staff
    context = {
        'total_donations': Donation.objects.count(),
        'my_donations_count': Donation.objects.filter(is_mine=True).count(),
        'other_donations_count': Donation.objects.filter(is_mine=False).exclude(status='cancelled').count(),
        'total_donors': Donation.objects.filter(is_mine=True, user__isnull=False).values('user_id').distinct().count(),
        'donations': page_obj.object_list,
        'can_manage': can_manage,
        'query': query,
        'page_obj': page_obj,
    }
    return render(request, 'admin-dashboard.html', context)


@login_required(login_url='signin')
def admin_delete_donation(request, donation_id):
    if not request.user.is_staff:
        messages.error(request, 'Staff access is required to delete listings.')
        return redirect('home')

    if request.method != 'POST':
        return redirect('admin_panel')

    donation = get_object_or_404(Donation, id=donation_id)
    deleted_id = donation.id
    food_name = donation.food_name
    donation.delete()
    audit_logger.info(
        'single_delete user=%s donation_id=%s food_name=%s',
        request.user.username,
        deleted_id,
        food_name,
    )
    messages.success(request, f'{food_name} was deleted successfully.')
    return redirect('admin_panel')


@login_required(login_url='signin')
def admin_bulk_delete_donations(request):
    if not request.user.is_staff:
        messages.error(request, 'Staff access is required for bulk delete.')
        return redirect('home')

    if request.method != 'POST':
        return redirect('admin_panel')

    raw_ids = request.POST.get('ids', '').strip()
    if not raw_ids:
        messages.error(request, 'Select at least one listing to delete.')
        return redirect('admin_panel')

    donation_ids = sorted({int(item) for item in raw_ids.split(',') if item.isdigit()})
    if not donation_ids:
        messages.error(request, 'No valid listing selection was provided.')
        return redirect('admin_panel')

    existing_ids = list(Donation.objects.filter(id__in=donation_ids).values_list('id', flat=True))
    deleted_count, _ = Donation.objects.filter(id__in=donation_ids).delete()
    if deleted_count:
        audit_logger.info(
            'bulk_delete user=%s donation_ids=%s deleted_count=%s',
            request.user.username,
            existing_ids,
            deleted_count,
        )
        messages.success(request, f'{deleted_count} listing(s) were deleted successfully.')
    else:
        messages.warning(request, 'The selected listings were not found.')
    return redirect('admin_panel')


@login_required(login_url='signin')
def confirm_pickup_request(request, donation_id):
    """Confirm a pending pickup request (staff only)"""
    if not request.user.is_staff:
        messages.error(request, 'Staff access is required.')
        return redirect('home')

    if request.method != 'POST':
        return redirect('admin_panel')

    donation = get_object_or_404(Donation, id=donation_id, is_mine=False)
    if donation.status != 'pending':
        messages.warning(request, 'Only pending requests can be confirmed.')
        return redirect('admin_panel')

    donation.status = 'confirmed'
    donation.save()
    messages.success(request, f'Pickup request for {donation.food_name} confirmed.')
    audit_logger.info(
        'confirm_pickup user=%s donation_id=%s food_name=%s',
        request.user.username,
        donation_id,
        donation.food_name,
    )
    return redirect('admin_panel')


@login_required(login_url='signin')
def cancel_pickup_request(request, donation_id):
    """Cancel a pending pickup request (staff only)"""
    if not request.user.is_staff:
        messages.error(request, 'Staff access is required.')
        return redirect('home')

    if request.method != 'POST':
        return redirect('admin_panel')

    donation = get_object_or_404(Donation, id=donation_id, is_mine=False)
    if donation.status == 'cancelled':
        messages.warning(request, 'This request is already cancelled.')
        return redirect('admin_panel')

    donation.status = 'cancelled'
    donation.save()
    messages.success(request, f'Pickup request for {donation.food_name} cancelled.')
    audit_logger.info(
        'cancel_pickup user=%s donation_id=%s food_name=%s',
        request.user.username,
        donation_id,
        donation.food_name,
    )
    return redirect('admin_panel')

# Create views here.

