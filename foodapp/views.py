import logging
import json
import re

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from django.core.paginator import Paginator
from django.db.models import Q
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from django.http import JsonResponse
from django.utils import timezone
from django.utils.http import url_has_allowed_host_and_scheme
from .models import Donation, UserBadge
from .forms import DonationForm, DonationSearchForm
from .utils import check_and_award_badges, send_pickup_request_email
from django.conf import settings

logger = logging.getLogger('foodapp.chatbot')

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
        form = DonationForm(request.POST, request.FILES)
        if form.is_valid():
            donation = form.save(commit=False)
            donation.user = request.user
            donation.is_mine = True
            donation.donor_name = donation.donor_name or (request.user.get_full_name() or request.user.username)
            donation.save()

            # Award badges for this action
            check_and_award_badges(request.user)

            messages.success(request, f'{donation.food_name} has been listed successfully!')
            audit_logger.info(
                'food_listed user=%s donation_id=%s food_name=%s',
                request.user.username,
                donation.id,
                donation.food_name,
            )
            return redirect('my_donations')
        else:
            messages.error(request, 'Please correct the errors in the form.')
    else:
        form = DonationForm()

    context = {'form': form}
    return render(request, 'list-food.html', context)


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

    pickup_request = Donation.objects.create(
        user=request.user,
        food_name=donation.food_name,
        category=donation.category,
        quantity=donation.quantity,
        location=donation.location,
        donor_name=donation.donor_name,
        is_mine=False,
    )

    # Award badges for requesting food
    check_and_award_badges(request.user)

    # Send email notification to donor if they exist
    if donation.user and donation.user.email:
        send_pickup_request_email(
            donation.user,
            donation.food_name,
            request.user.get_full_name() or request.user.username
        )

    messages.success(request, f'Pickup request submitted for {donation.food_name}.')
    audit_logger.info(
        'pickup_requested user=%s donation_id=%s food_name=%s',
        request.user.username,
        pickup_request.id,
        donation.food_name,
    )
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
        recent_donations = Donation.objects.filter(user=request.user, is_mine=True).order_by('-id')[:5]
        profile_location = request.user.email or 'Local Community'
        earned_badges = request.user.earned_badges.all().select_related('badge').order_by('-earned_at')
    else:
        my_donations_count = Donation.objects.filter(is_mine=True).count()
        received_items = Donation.objects.filter(is_mine=False, user__isnull=False).exclude(status='cancelled').count()
        latest_donor = Donation.objects.order_by('-id').values_list('donor_name', flat=True).first() or 'Community Member'
        recent_donations = Donation.objects.filter(is_mine=True).order_by('-id')[:5]
        profile_location = 'Local Community'
        earned_badges = []

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
        'earned_badges': earned_badges,
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

    donation = get_object_or_404(Donation, id=donation_id)
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

    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        return JsonResponse({
            'success': True,
            'action': 'confirmed',
            'donation_id': donation.id,
            'food_name': donation.food_name,
            'status': donation.status,
            'message': f'Pickup request for {donation.food_name} confirmed.',
        })

    return redirect('admin_panel')


@login_required(login_url='signin')
def cancel_pickup_request(request, donation_id):
    """Cancel a pending pickup request (staff only)"""
    if not request.user.is_staff:
        messages.error(request, 'Staff access is required.')
        return redirect('home')

    if request.method != 'POST':
        return redirect('admin_panel')

    donation = get_object_or_404(Donation, id=donation_id)
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

    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        return JsonResponse({
            'success': True,
            'action': 'cancelled',
            'donation_id': donation.id,
            'food_name': donation.food_name,
            'status': donation.status,
            'message': f'Pickup request for {donation.food_name} cancelled.',
        })

    return redirect('admin_panel')


def chatbot_api(request):
    """API endpoint for chatbot responses"""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'Method not allowed'}, status=405)

    try:
        data = json.loads(request.body)
        user_message = data.get('message', '').strip().lower()
        
        # Auto-donation entry: detect donation patterns and create Donation record
        food_name = None
        quantity = None
        location = None
        
        # Pattern 1: "I have 2kg rice at Dhaka"
        m = re.search(r"(?:i\s+)?have\s+([0-9.]+\s*[a-z]*)\s+([a-z\s\u0980-\u09FF]+?)\s+(?:at|to donate|to|donate at)\s+([a-z\s\u0980-\u09FF]+)", user_message, re.IGNORECASE)
        if m:
            quantity, food_name, location = m.groups()
        
        # Pattern 2: "donate 5kg potatoes in Mirpur"
        if not m:
            m = re.search(r"donate\s+([0-9.]+\s*[a-z]*)\s+([a-z\s\u0980-\u09FF]+?)\s+(?:at|in)\s+([a-z\s\u0980-\u09FF]+)", user_message, re.IGNORECASE)
            if m:
                quantity, food_name, location = m.groups()
        
        # Pattern 3: "donate eggs (10) at Gulshan" — food name, then qty in parens
        if not m:
            m = re.search(r"(?:i\s+)?(?:want to\s+)?donate\s+([a-z\s\u0980-\u09FF]+?)\s+\(([0-9.]+\s*[a-z]*)\)\s+(?:at|in|to)\s+([a-z\s\u0980-\u09FF]+)", user_message, re.IGNORECASE)
            if m:
                food_name, quantity, location = m.groups()
        
        # If any donation pattern matched, create record
        if food_name and quantity and location:
            food_name = food_name.strip()
            quantity = quantity.strip()
            location = location.strip()
            
            # Determine category from food name
            category = 'other'
            category_keywords = {
                'dairy': ['milk', 'cheese', 'butter', 'yogurt', 'egg', 'eggs', 'dairy'],
                'bakery': ['bread', 'cake', 'cookie', 'cookies', 'pastry', 'bakery'],
                'produce': ['rice', 'potato', 'vegetable', 'fruit', 'produce', 'carrot', 'apple', 'banana'],
                'prepared': ['cooked', 'meal', 'rice', 'curry', 'prepared'],
            }
            for cat, keywords in category_keywords.items():
                if any(kw in food_name.lower() for kw in keywords):
                    category = cat
                    break
            
            # Create Donation record
            donation = Donation.objects.create(
                food_name=food_name.title(),
                category=category,
                quantity=quantity,
                location=location.title(),
                donor_name='Chatbot Entry',
                is_mine=True,
                status='confirmed',
                user=request.user if request.user.is_authenticated else None
            )
            
            list_url = reverse('available')
            reply = (
                f'Great! I\'ve added "{food_name.title()}" ({quantity}) at {location.title()} to available food.\n'
                f'Community members can now request pickup: {list_url}'
            )
            logger.info(f'Auto-donation created: Donation #{donation.id} from chatbot entry')
            return JsonResponse({'success': True, 'reply': reply, 'timestamp': str(timezone.now())})
        
        # Quick direct lookup for short/single-token queries (treat as food name)
        tokens_quick = re.findall(r"[\w\u0980-\u09FF]+", user_message)
        if tokens_quick and len(tokens_quick) <= 3:
            all_qs = Donation.objects.filter(is_mine=True).filter(
                Q(food_name__icontains=user_message) | Q(food_name__iexact=user_message)
            )
            active_qs = all_qs.exclude(status='cancelled')

            if active_qs.exists():
                item = active_qs.order_by('-id').first()
                browse_url = reverse('available')
                reply = (
                    f'Yes — "{item.food_name}" is available (Qty: {item.quantity}).\nLocation: {item.location}.\n'
                    f'Request pickup from the Browse page: {browse_url} and click Request Pickup on the listing.'
                )
                return JsonResponse({'success': True, 'reply': reply, 'timestamp': str(timezone.now())})
            # If no active shared listings, check for any records (requests or past listings)
            any_qs = Donation.objects.filter(
                Q(food_name__icontains=user_message) | Q(food_name__iexact=user_message)
            )
            if any_qs.exists():
                # There are records but no active listings
                item = any_qs.order_by('-id').first()
                # If it's a request (is_mine=False) tell user it's not currently available
                if not item.is_mine:
                    reply = (
                        f'There is interest in "{item.food_name}" (a pickup request exists), but no active listing right now. '
                        f'If you have this item, please consider donating via the List Food page.'
                    )
                else:
                    reply = (
                        f'There was a listing for "{item.food_name}" (Qty: {item.quantity}) at {item.location}, '
                        f'but it is not currently available. Try checking back or search for similar items on the Browse page.'
                    )
                return JsonResponse({'success': True, 'reply': reply, 'timestamp': str(timezone.now())})

        # Handle common 'how' questions first (donate/find/safety) to return helpful instructions
        if user_message.startswith('how') or user_message.startswith('what') or user_message.startswith('is'):
            if 'donate' in user_message:
                list_url = reverse('list_food')
                reply = f'To donate food, go to: {list_url}. Fill the form with food name, quantity and location.'
                return JsonResponse({'success': True, 'reply': reply, 'timestamp': str(timezone.now())})
            if 'find' in user_message or 'browse' in user_message or 'near me' in user_message:
                browse_url = reverse('available')
                reply = f'To find food near you, open the Browse page: {browse_url}. Use the search box and filters (category, location) to narrow results.'
                return JsonResponse({'success': True, 'reply': reply, 'timestamp': str(timezone.now())})
            if 'safety' in user_message or 'safe' in user_message:
                reply = 'Always check expiry dates, inspect food condition, and follow safe food-handling practices before accepting items.'
                return JsonResponse({'success': True, 'reply': reply, 'timestamp': str(timezone.now())})

        # Location-based queries: detect patterns like 'near X', 'around X', 'in X', 'nearest X'
        loc_match = re.search(r"\b(?:near|around|around\s+the|nearest|nearby|in|surrounding|surrounds)\s+(?:the\s+)?([\w\u0980-\u09FF\s\-]+)", user_message)
        if loc_match:
            extracted = loc_match.group(1).strip().strip('?.!,')
            if extracted:
                # Extract the last word as the location (to avoid capturing unrelated words; "food around dhaka" -> "dhaka")
                words = extracted.split()
                place = words[-1]  # take last word only
                # search for active shared listings whose location contains the place
                nearby_qs = Donation.objects.filter(is_mine=True).exclude(status='cancelled').filter(location__icontains=place).order_by('-id')[:5]
                if nearby_qs:
                    parts = []
                    for it in nearby_qs:
                        parts.append(f'"{it.food_name}" ({it.quantity}) — {it.location}')
                    browse = reverse('available')
                    reply = f'Found {len(parts)} listing(s) near "{place}":\n' + '\n'.join(parts) + f'\n\nOpen {browse} to request pickup for any listing.'
                else:
                    reply = f'Sorry, I could not find active listings near "{place}" right now. Try a nearby neighborhood or check back later.'
                return JsonResponse({'success': True, 'reply': reply, 'timestamp': str(timezone.now())})

        # No hardcoded-only behaviour: detect intent then consult DB
        # English-only intent keywords
        donate_keywords = ['donate', 'donating', 'give', 'giving']
        receive_keywords = ['receive', 'get', 'want', 'need', 'request', 'pickup', 'collect', 'find']

        # If user intends to donate, point to the listing form (no static, give real URL)
        if any(k in user_message for k in donate_keywords):
            list_url = reverse('list_food')
            reply = f'Thank you for wanting to donate — please list your item here: {list_url}. Include food name, quantity and location.'
            return JsonResponse({'success': True, 'reply': reply, 'timestamp': str(timezone.now())})

        # If user intends to receive/find food, search the Donation DB
        if any(k in user_message for k in receive_keywords):
            queryset = Donation.objects.filter(is_mine=True).exclude(status='cancelled')
            synonym_map = {
                'milk': 'dairy',
                'dairy': 'dairy',
                'cheese': 'dairy',
                'butter': 'dairy',
                'yogurt': 'dairy',
                'egg': 'dairy',
                'eggs': 'dairy',
                'bread': 'bakery',
                'cake': 'bakery',
                'cookie': 'bakery',
                'cookies': 'bakery',
                'rice': 'produce',
                'potato': 'produce',
                'potatoes': 'produce',
                'vegetable': 'produce',
                'vegetables': 'produce',
                'fruit': 'produce',
                'fruits': 'produce',
            }

            # direct filter using common fields
            matches = list(queryset.filter(
                Q(food_name__icontains=user_message) |
                Q(category__icontains=user_message) |
                Q(location__icontains=user_message)
            )[:5])

            # token fuzzy match (including Bengali tokens)
            if not matches:
                stopwords = {
                    'i', 'want', 'need', 'get', 'give', 'receive', 'pickup', 'collect',
                    'find', 'food', 'item', 'items', 'please', 'show', 'me', 'a', 'an', 'the',
                    'to', 'for', 'of', 'is', 'are', 'there', 'available', 'in', 'at', 'on'
                }
                tokens = [
                    token for token in re.findall(r"[\w\u0980-\u09FF]+", user_message)
                    if len(token) >= 3 and token not in stopwords
                ]
                mapped_category_terms = [synonym_map[token] for token in tokens if token in synonym_map]
                search_terms = tokens + mapped_category_terms
                requested_term = tokens[0] if tokens else 'that item'
                focus_term = mapped_category_terms[0] if mapped_category_terms else None
                for item in queryset:
                    text = ' '.join([
                        str(item.food_name or ''),
                        str(item.donor_name or ''),
                        str(item.category or ''),
                        str(item.location or ''),
                    ]).lower()
                    for t in search_terms:
                        if re.search(rf'\b{re.escape(t)}\b', text):
                            matches.append(item)
                            break
                    if matches:
                        break

            if matches:
                item = matches[0]
                browse_url = reverse('available')
                reply = (
                    f'Yes — "{item.food_name}" is available (Qty: {item.quantity}).\nLocation: {item.location}.\n'
                    f'Request pickup from the Browse page: {browse_url} and click Request Pickup on the listing.'
                )
                return JsonResponse({'success': True, 'reply': reply, 'timestamp': str(timezone.now())})
            else:
                if focus_term:
                    reply = f'No {requested_term} ({focus_term}) listings found right now. Try another term, or browse the Available Food page for current listings.'
                else:
                    reply = f'No {requested_term} listings found right now. Try another term, or browse the Available Food page for current listings.'

            return JsonResponse({'success': True, 'reply': reply, 'timestamp': str(timezone.now())})

        # Fallback short answers (still not hardcoded-only; used when no DB intent)
        responses = {
            'how does it work': 'Donors list food; community members request pickups. Free and local.',
            'badges': 'Earn badges by sharing and requesting food.',
            'safety': 'Inspect food carefully and follow safe handling practices.',
            'contact': 'Reach support via the help page or email support@hyperlocalfoodrescue.local',
            'default': "I'm here to help — try asking to 'donate' or 'find' food."
        }

        reply = responses.get('default')
        for key in responses:
            if key != 'default' and key in user_message:
                reply = responses[key]
                break

        return JsonResponse({'success': True, 'reply': reply, 'timestamp': str(timezone.now())})

    except ValueError as e:
        logger.warning('Invalid JSON in chatbot_api: %s', e)
        return JsonResponse({'success': False, 'error': 'Invalid request data'}, status=400)
    except Exception as e:
        logger.exception('Unhandled error in chatbot_api')
        message = 'Sorry, something went wrong. Please try again later.'
        if getattr(settings, 'DEBUG', False):
            return JsonResponse({'success': False, 'error': message, 'detail': str(e)}, status=500)
        return JsonResponse({'success': False, 'error': message}, status=500)

    return JsonResponse({'error': 'POST method required'}, status=405)


@login_required
def chatbot_llm_api(request):
    """LLM-powered chatbot with conversation context and function-calling"""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'Method not allowed'}, status=405)

    try:
        from foodapp.llm_chatbot import llm_chatbot
        
        data = json.loads(request.body)
        user_message = data.get('message', '').strip()
        
        if not user_message:
            return JsonResponse({'success': False, 'error': 'Message cannot be empty'}, status=400)
        
        # Use session ID from request or generate one
        session_id = f"user_{request.user.id}" if request.user.is_authenticated else data.get('session_id', 'anonymous')
        
        # Process message through LLM
        reply, action = llm_chatbot.process_message(user_message, session_id)
        
        # If LLM suggested an action, execute it
        if action:
            action_reply = llm_chatbot.handle_action(action, user_id=request.user.id if request.user.is_authenticated else None)
            # Append action result to reply
            reply = f"{reply}\n\n{action_reply}" if reply else action_reply
            logger.info(f'LLM action executed: {action.get("action")} for user {request.user.id}')
        
        return JsonResponse({
            'success': True,
            'reply': reply,
            'session_id': session_id,
            'timestamp': str(timezone.now()),
            'action': action.get('action') if action else None
        })
        
    except ImportError:
        # LLM not available, provide helpful message
        return JsonResponse({
            'success': False,
            'error': 'LLM assistant is not available. Ensure Ollama is running with: ollama serve',
            'fallback_message': 'Please use the standard chatbot or list your food manually.'
        }, status=503)
    except json.JSONDecodeError:
        logger.warning('Invalid JSON in chatbot_llm_api')
        return JsonResponse({'success': False, 'error': 'Invalid request data'}, status=400)
    except Exception as e:
        logger.exception('Error in chatbot_llm_api')
        return JsonResponse({'success': False, 'error': 'Internal server error', 'detail': str(e) if getattr(settings, 'DEBUG', False) else ''}, status=500)


# Create views here.


