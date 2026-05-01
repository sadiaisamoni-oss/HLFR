import json
from django.test import TestCase, Client
from django.contrib.auth.models import User
from django.urls import reverse
from .models import Donation, Badge, UserBadge


class DonationModelTest(TestCase):
    """Test cases for the Donation model"""

    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )

    def test_create_donation(self):
        """Test creating a donation"""
        donation = Donation.objects.create(
            user=self.user,
            food_name='Apple',
            category='produce',
            quantity='5 kg',
            location='Downtown',
            donor_name='John Doe',
            is_mine=True
        )
        self.assertEqual(donation.food_name, 'Apple')
        self.assertEqual(donation.category, 'produce')
        self.assertTrue(donation.is_mine)

    def test_donation_string_representation(self):
        """Test donation string representation"""
        donation = Donation.objects.create(
            user=self.user,
            food_name='Bread',
            category='bakery',
            quantity='2 loaves',
            location='Downtown',
        )
        self.assertEqual(str(donation), 'Bread')


class BadgeModelTest(TestCase):
    """Test cases for the Badge model"""

    def test_create_badge(self):
        """Test creating a badge"""
        badge = Badge.objects.create(
            icon='🌟',
            title='Top Donor',
            description='Share 5 items',
            metric='shared',
            threshold=5,
            is_active=True
        )
        self.assertEqual(badge.title, 'Top Donor')
        self.assertEqual(badge.threshold, 5)

    def test_badge_string_representation(self):
        """Test badge string representation"""
        badge = Badge.objects.create(
            title='Test Badge',
            metric='shared',
            threshold=10
        )
        self.assertIn('Test Badge', str(badge))
        self.assertIn('10+', str(badge))


class UserBadgeModelTest(TestCase):
    """Test cases for the UserBadge model"""

    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        self.badge = Badge.objects.create(
            title='Test Badge',
            metric='shared',
            threshold=5
        )

    def test_create_user_badge(self):
        """Test creating a user badge"""
        user_badge = UserBadge.objects.create(
            user=self.user,
            badge=self.badge
        )
        self.assertEqual(user_badge.user, self.user)
        self.assertEqual(user_badge.badge, self.badge)

    def test_unique_constraint(self):
        """Test that a user can't earn the same badge twice"""
        UserBadge.objects.create(user=self.user, badge=self.badge)
        # Trying to create the same relationship should fail
        with self.assertRaises(Exception):
            UserBadge.objects.create(user=self.user, badge=self.badge)


class DonationViewTest(TestCase):
    """Test cases for donation-related views"""

    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        self.other_user = User.objects.create_user(
            username='otheruser',
            email='other@example.com',
            password='testpass123'
        )

    def test_home_view(self):
        """Test home page view"""
        response = self.client.get(reverse('home'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'index.html')

    def test_list_food_requires_login(self):
        """Test that listing food requires login"""
        response = self.client.get(reverse('list_food'))
        self.assertNotEqual(response.status_code, 200)
        self.assertIn('/signin', response.url)

    def test_list_food_authenticated(self):
        """Test listing food when authenticated"""
        self.client.login(username='testuser', password='testpass123')
        response = self.client.get(reverse('list_food'))
        self.assertEqual(response.status_code, 200)

    def test_create_donation_via_form(self):
        """Test creating a donation through the form"""
        self.client.login(username='testuser', password='testpass123')
        response = self.client.post(reverse('list_food'), {
            'food_name': 'Apples',
            'category': 'produce',
            'quantity': '5 kg',
            'location': 'Downtown',
            'donor_name': 'John'
        })
        self.assertEqual(response.status_code, 302)
        self.assertTrue(Donation.objects.filter(food_name='Apples').exists())


class AvailableFoodViewTest(TestCase):
    """Test cases for browsing available food"""

    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        self.donation = Donation.objects.create(
            user=self.user,
            food_name='Rice',
            category='produce',
            quantity='10 kg',
            location='Central',
            is_mine=True
        )

    def test_available_food_view(self):
        """Test viewing available food"""
        response = self.client.get(reverse('available_food'))
        self.assertEqual(response.status_code, 200)
        self.assertIn(self.donation, response.context['data'])

    def test_search_food(self):
        """Test searching for food"""
        response = self.client.get(
            reverse('available_food'),
            {'searchQuery': 'Rice'}
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn(self.donation, response.context['data'])

    def test_search_no_results(self):
        """Test search with no results"""
        response = self.client.get(
            reverse('available_food'),
            {'searchQuery': 'NonExistent'}
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context['data']), 0)


class ProfileViewTest(TestCase):
    """Test cases for user profile view"""

    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        self.badge = Badge.objects.create(
            title='Test Badge',
            metric='shared',
            threshold=1
        )

    def test_profile_view_authenticated(self):
        """Test profile view for authenticated user"""
        self.client.login(username='testuser', password='testpass123')
        response = self.client.get(reverse('profile'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'profile.html')

    def test_profile_shows_badges(self):
        """Test that profile shows earned badges"""
        UserBadge.objects.create(user=self.user, badge=self.badge)
        self.client.login(username='testuser', password='testpass123')
        response = self.client.get(reverse('profile'))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context['earned_badges']), 1)


class ChatbotAPITest(TestCase):
    """Test cases for chatbot API"""

    def setUp(self):
        self.client = Client()

    def test_chatbot_api_donate_question(self):
        """Test chatbot responds to donation question"""
        response = self.client.post(
            reverse('chatbot_api'),
            json.dumps({'message': 'How can I donate?'}),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data['success'])
        self.assertIn('reply', data)

    def test_chatbot_api_invalid_method(self):
        """Test chatbot API with invalid method"""
        response = self.client.get(reverse('chatbot_api'))
        self.assertEqual(response.status_code, 405)

    def test_chatbot_api_location_found(self):
        """Location query returns nearby listings when present"""
        donor = User.objects.create_user(username='donor', email='donor@example.com', password='pass')
        Donation.objects.create(
            user=donor,
            food_name='Mango',
            category='produce',
            quantity='3 kg',
            location='Dhaka Central',
            is_mine=True
        )
        response = self.client.post(
            reverse('chatbot_api'),
            json.dumps({'message': 'is there food near dhaka'}),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data['success'])
        self.assertIn('Found', data['reply'] or '') or self.assertIn('Mango', data['reply'])

    def test_chatbot_api_location_not_found(self):
        """Location query gracefully returns no-results message"""
        response = self.client.post(
            reverse('chatbot_api'),
            json.dumps({'message': 'is there food around Nowhereville'}),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data['success'])
        self.assertIn('could not find', data['reply'].lower())

    def test_chatbot_api_ignores_short_false_match_tokens(self):
        """Short common words should not cause unrelated listings to match"""
        donor = User.objects.create_user(username='donor2', email='donor2@example.com', password='pass')
        Donation.objects.create(
            user=donor,
            food_name='Bakery items',
            category='bakery',
            quantity='2',
            location='Sector-10,Uttara',
            is_mine=True
        )
        response = self.client.post(
            reverse('chatbot_api'),
            json.dumps({'message': 'i want milk'}),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data['success'])
        self.assertNotIn('Bakery items', data['reply'])
        self.assertIn('No milk (dairy) listings found', data['reply'])

    def test_chatbot_api_milk_maps_to_dairy_listing(self):
        """Milk-like requests should match a dairy listing when available"""
        donor = User.objects.create_user(username='donor3', email='donor3@example.com', password='pass')
        Donation.objects.create(
            user=donor,
            food_name='Fresh Eggs',
            category='dairy',
            quantity='12 pcs',
            location='Dhaka',
            is_mine=True
        )
        response = self.client.post(
            reverse('chatbot_api'),
            json.dumps({'message': 'i want milk'}),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data['success'])
        self.assertIn('Fresh Eggs', data['reply'])

    def test_chatbot_api_milk_no_match_is_contextual(self):
        """Milk requests without a match should mention milk in the reply"""
        response = self.client.post(
            reverse('chatbot_api'),
            json.dumps({'message': 'i want milk'}),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data['success'])
        self.assertIn('No milk (dairy) listings found', data['reply'])

    def test_chatbot_api_invalid_json_returns_error(self):
        """POSTing invalid JSON returns structured error and non-200 status"""
        response = self.client.post(reverse('chatbot_api'), b'invalid json', content_type='application/json')
        self.assertIn(response.status_code, (400, 500))
        data = response.json()
        self.assertFalse(data.get('success', True))
        self.assertIn('error', data)

    def test_chatbot_auto_donation_pattern_1(self):
        """'I have Xkg food at Location' should auto-create donation"""
        response = self.client.post(
            reverse('chatbot_api'),
            json.dumps({'message': 'I have 2kg rice at Dhaka'}),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data['success'])
        self.assertIn('Great!', data['reply'])
        
        # Verify donation was created
        donation = Donation.objects.filter(donor_name='Chatbot Entry', food_name__icontains='rice').first()
        self.assertIsNotNone(donation)
        self.assertEqual(donation.quantity.strip(), '2kg')
        self.assertEqual(donation.category, 'produce')
        self.assertTrue(donation.is_mine)

    def test_chatbot_auto_donation_pattern_2(self):
        """'donate Xkg food in Location' should auto-create donation"""
        response = self.client.post(
            reverse('chatbot_api'),
            json.dumps({'message': 'donate 5kg vegetables in Mirpur'}),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data['success'])
        
        donation = Donation.objects.filter(donor_name='Chatbot Entry', food_name__icontains='vegetables').first()
        self.assertIsNotNone(donation)
        self.assertEqual(donation.category, 'produce')

    def test_chatbot_auto_donation_pattern_3(self):
        """'donate food (Qty) at Location' should auto-create donation"""
        response = self.client.post(
            reverse('chatbot_api'),
            json.dumps({'message': 'donate milk (5L) at Banani'}),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data['success'])
        
        donation = Donation.objects.filter(donor_name='Chatbot Entry', food_name__icontains='milk').first()
        self.assertIsNotNone(donation)
        self.assertEqual(donation.category, 'dairy')
