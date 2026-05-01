"""Utility functions for badge awarding and notifications"""

from django.core.mail import send_mail
from django.conf import settings
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from .models import Badge, UserBadge, Donation


def award_badge_to_user(user, badge):
    """Award a badge to a user if they don't already have it"""
    user_badge, created = UserBadge.objects.get_or_create(user=user, badge=badge)
    return created


def check_and_award_badges(user):
    """Check user activity and award badges accordingly"""
    if not user.is_authenticated:
        return

    # Count user donations and activities
    shared_count = Donation.objects.filter(user=user, is_mine=True).count()
    requested_count = Donation.objects.filter(user=user, is_mine=False).exclude(status='cancelled').count()
    total_activity = shared_count + requested_count
    community_points = (shared_count * 10) + (requested_count * 6)

    # Get all active badges
    badges = Badge.objects.filter(is_active=True)

    for badge in badges:
        # Determine if user should earn this badge
        should_award = False

        if badge.metric == 'shared' and shared_count >= badge.threshold:
            should_award = True
        elif badge.metric == 'requested' and requested_count >= badge.threshold:
            should_award = True
        elif badge.metric == 'activity' and total_activity >= badge.threshold:
            should_award = True
        elif badge.metric == 'points' and community_points >= badge.threshold:
            should_award = True

        # Award badge if criteria met
        if should_award:
            created = award_badge_to_user(user, badge)
            if created:
                send_badge_earned_email(user, badge)


def send_badge_earned_email(user, badge):
    """Send email notification when user earns a badge"""
    try:
        subject = f'🎉 You earned the {badge.title} badge!'
        context = {
            'user': user,
            'badge': badge,
        }
        html_message = f"""
        <h2>Congratulations!</h2>
        <p>You've earned the <strong>{badge.title}</strong> badge! {badge.icon}</p>
        <p>{badge.description}</p>
        <p>Keep up the great work in our food rescue community!</p>
        """

        send_mail(
            subject,
            f'You earned the {badge.title} badge! {badge.description}',
            settings.DEFAULT_FROM_EMAIL,
            [user.email],
            html_message=html_message,
            fail_silently=True,
        )
    except Exception as e:
        print(f"Error sending badge email: {e}")


def send_notification_email(user, subject, message):
    """Send a generic notification email"""
    try:
        send_mail(
            subject,
            message,
            settings.DEFAULT_FROM_EMAIL,
            [user.email],
            fail_silently=True,
        )
    except Exception as e:
        print(f"Error sending notification email: {e}")


def send_pickup_request_email(donor_user, food_name, requester_name):
    """Notify donor about a pickup request"""
    try:
        subject = f'New pickup request for {food_name}'
        message = f"""
        Hello {donor_user.get_full_name() or donor_user.username},

        Someone is interested in picking up your {food_name} donation!

        Requester: {requester_name}
        Item: {food_name}

        Please log in to your account to manage this request.

        Thank you for being part of the Hyper-Local Food Rescue community!
        """

        send_mail(
            subject,
            message,
            settings.DEFAULT_FROM_EMAIL,
            [donor_user.email],
            fail_silently=True,
        )
    except Exception as e:
        print(f"Error sending pickup request email: {e}")
