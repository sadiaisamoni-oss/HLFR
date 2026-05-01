# Hyper-Local Food Rescue Platform

A Django-based web application that connects food donors with community members to reduce food waste and fight hunger.

## Features

### Core Features
- **Food Donation Listing**: Donors can list surplus food items with photos
- **Food Discovery**: Community members can browse and search for available food
- **Pickup Requests**: Users can request pickups of available food items
- **User Profiles**: Track donations, pickups, and earned badges
- **Admin Dashboard**: Manage donations, confirm/cancel requests, and monitor activity

### Advanced Features
- **Badge System**: Users earn badges for participation (Top Donor, Community Hero, Waste Warrior, etc.)
- **Image Upload**: Attach photos to food listings for better visibility
- **Email Notifications**: Receive email alerts for pickup requests and badge achievements
- **Chatbot Support**: AI-powered chatbot to answer common questions
- **Activity Tracking**: Track community points and rating system
- **Audit Logging**: Comprehensive logging of all user actions

## Installation

### Prerequisites
- Python 3.8+
- pip
- Virtual environment tool (venv or virtualenv)

### Setup Instructions

1. **Clone the repository**
```bash
cd "Hyper-Local Food Rescue"
```

2. **Create and activate virtual environment**
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. **Install dependencies**
```bash
pip install -r requirements.txt
```

4. **Configure email (Optional but recommended)**
Edit `myproject/settings.py` and update:
```python
EMAIL_HOST_USER = 'your-email@gmail.com'
EMAIL_HOST_PASSWORD = 'your-app-password'  # Use Gmail app password
```

5. **Run migrations**
```bash
python manage.py migrate
```

6. **Populate initial badges**
```bash
python manage.py populate_badges
```

7. **Create superuser account**
```bash
python manage.py createsuperuser
```

8. **Run development server**
```bash
python manage.py runserver
```

Visit `http://localhost:8000` to access the application.

## Usage

### For Donors
1. Sign up or log in
2. Navigate to "List Food"
3. Fill in food details (name, category, quantity, location)
4. Optionally upload a photo
5. Submit to list the food
6. Manage your listings from "My Donations"
7. View pickup requests from community members

### For Recipients
1. Sign up or log in
2. Navigate to "Browse Food"
3. Search or filter by category
4. Click "Request Pickup" for items you want
5. Manage your requests from "My Donations"
6. Track received items in your profile

### For Admins
1. Log in as staff user
2. Visit the admin dashboard at `/admin-panel/`
3. Manage all donations (view, edit, delete)
4. Confirm or cancel pickup requests
5. Monitor community activity

## API Endpoints

### Chatbot API
- **URL**: `/api/chatbot/`
- **Method**: POST
- **Payload**: `{"message": "user question"}`
- **Response**: `{"success": true, "reply": "chatbot response"}`

## Running Tests

```bash
python manage.py test
```

For detailed test output:
```bash
python manage.py test --verbosity=2
```

## Project Structure

```
foodapp/
├── models.py              # Database models (Donation, Badge, UserBadge)
├── views.py              # Request handlers and logic
├── forms.py              # Form classes for donations
├── urls.py               # URL routing
├── admin.py              # Admin interface configuration
├── utils.py              # Utility functions (badges, emails)
├── tests.py              # Unit and integration tests
├── management/
│   └── commands/
│       └── populate_badges.py  # Command to seed initial badges
└── migrations/           # Database migrations

templates/               # HTML templates
├── index.html          # Home page
├── list-food.html      # Donation form
├── available-food.html # Browse donations
├── my-donations.html   # User's donations and requests
├── profile.html        # User profile with badges
├── admin-dashboard.html # Admin control panel
└── registration/       # Password reset templates

static/                 # Static files
├── style.css          # Styling
├── chatbot.js         # Chatbot functionality
```

## Models

### Donation
- Represents a food item listing or pickup request
- Fields: user, food_name, category, quantity, location, donor_name, status, image, created_at
- Statuses: pending, confirmed, cancelled

### Badge
- Represents an achievement badge
- Fields: icon, title, description, metric, threshold, sort_order, is_active
- Metrics: shared (items donated), requested, activity (total), points (community points)

### UserBadge
- Tracks earned badges by users
- Links User to Badge with earned_at timestamp
- Enforces unique constraint (user can't earn same badge twice)

## Email Configuration

The application uses SMTP for email notifications. For Gmail:

1. Enable 2-Factor Authentication on your Google account
2. Generate an App Password at https://myaccount.google.com/apppasswords
3. Use the app password in settings instead of your regular password

For other email providers, adjust the EMAIL_HOST and EMAIL_PORT accordingly.

## Troubleshooting

### Migration Issues
```bash
python manage.py migrate --fake-initial
```

### Permission Denied (Media Upload)
Ensure the `media/` directory exists and has write permissions:
```bash
mkdir -p media
chmod 755 media
```

### Email Not Sending
- Check EMAIL_HOST_USER and EMAIL_HOST_PASSWORD in settings.py
- Verify SMTP is enabled for your email provider
- Check EMAIL_BACKEND setting (should be smtp.EmailBackend)

## Contributing

1. Create a new branch for your feature
2. Make your changes
3. Write/update tests
4. Run test suite to ensure everything passes
5. Submit a pull request

## License

This project is open-source and available for community use.

## Support

For issues or questions, please contact the development team or visit the help section in the application.

## Future Enhancements

- [ ] Map-based location search
- [ ] Real-time notifications
- [ ] Messaging system between users
- [ ] Rating and review system
- [ ] Donation calendar
- [ ] Mobile app
- [ ] Advanced analytics dashboard
- [ ] Integration with food banks
