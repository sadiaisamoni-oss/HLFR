# Quick Start Guide

## 🚀 Get Started in 5 Minutes

### Prerequisites
- Python 3.8+
- pip
- Git

### Step 1: Clone and Setup (2 minutes)
```bash
cd "Hyper-Local Food Rescue"
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### Step 2: Database Setup (1 minute)
```bash
python manage.py migrate
python manage.py populate_badges
python manage.py createsuperuser  # Create admin account
```

### Step 3: Run Server (1 minute)
```bash
python manage.py runserver
```

Visit `http://localhost:8000` 🎉

---

## Key Endpoints

| URL | Purpose |
|-----|---------|
| `/` | Home page |
| `/signup/` | Register |
| `/signin/` | Login |
| `/list-food/` | Donate food |
| `/available-food/` | Browse food |
| `/my-donations/` | My donations & requests |
| `/profile/` | User profile (see badges) |
| `/admin-panel/` | Admin dashboard |
| `/admin/` | Django admin |
| `/api/chatbot/` | Chatbot API |

---

## Default Test Accounts

**Admin Account:**
- Create your own with: `python manage.py createsuperuser`

**Test User:**
```
Email: test@example.com
Password: testpass123
```

---

## File Structure Highlights

```
Hyper-Local Food Rescue/
├── foodapp/                     # Main app
│   ├── models.py               # Database models
│   ├── views.py                # Business logic
│   ├── forms.py                # Form classes
│   ├── utils.py                # Helper functions
│   ├── tests.py                # Test suite
│   └── management/
│       └── commands/
│           └── populate_badges.py
├── myproject/                   # Project settings
│   ├── settings.py             # Configuration
│   ├── urls.py                 # URL routing
│   └── wsgi.py                 # WSGI config
├── templates/                   # HTML templates
├── static/                      # CSS, JavaScript
├── requirements.txt            # Python packages
├── README.md                   # Full documentation
├── DEPLOYMENT.md               # Deploy guide
└── COMPLETION_SUMMARY.md       # Feature summary
```

---

## Common Tasks

### Run Tests
```bash
python manage.py test
python manage.py test --verbosity=2  # Detailed
```

### Create Test Data
```bash
python manage.py shell
```
```python
from django.contrib.auth.models import User
from foodapp.models import Donation

user = User.objects.create_user('donor@example.com', 'donor@example.com', 'pass')
Donation.objects.create(
    user=user,
    food_name='Apples',
    category='produce',
    quantity='5 kg',
    location='Downtown',
    is_mine=True
)
```

### Populate Badges
```bash
python manage.py populate_badges
```

### Access Admin Interface
1. Go to `http://localhost:8000/admin/`
2. Login with superuser account
3. Manage donations, badges, users

---

## Features Demo

### 1. List Food (Donation)
1. Login at `/signin/`
2. Go to `/list-food/`
3. Fill form and upload image
4. Submit → item appears in `/available-food/`

### 2. Request Pickup
1. Browse `/available-food/`
2. Click "Request Pickup"
3. Check `/my-donations/` for your requests
4. Donor gets email notification

### 3. Earn Badges
1. Share 5 items → Get "Top Donor" badge 🌟
2. Request 3 items → Get "Waste Warrior" badge ♻️
3. Total 10 activities → Get "Community Hero" badge 🤝
4. View badges on `/profile/`

### 4. Chatbot
1. Use chatbot widget in bottom-right
2. Ask: "How can I donate?"
3. Get instant response

---

## Troubleshooting

### Port 8000 already in use
```bash
python manage.py runserver 8001  # Use different port
```

### Database locked
```bash
rm db.sqlite3
python manage.py migrate
python manage.py populate_badges
```

### Import errors
```bash
pip install -r requirements.txt --upgrade
```

### Media files not uploading
```bash
mkdir -p media/donations
chmod 755 media
```

---

## Email Setup (Optional)

To enable email notifications:

1. Update `myproject/settings.py`:
```python
EMAIL_HOST_USER = 'your-email@gmail.com'
EMAIL_HOST_PASSWORD = 'your-app-password'
```

2. For Gmail:
   - Enable 2FA on Google Account
   - Generate app password at https://myaccount.google.com/apppasswords
   - Use that password above

---

## Next Steps

1. ✅ Run the application locally
2. ✅ Test all features
3. ✅ Run the test suite
4. ✅ Read DEPLOYMENT.md for production setup
5. ✅ Configure email for your domain
6. ✅ Deploy to production!

---

## Important Files to Review

1. **models.py** - Database schema
2. **views.py** - Request handlers
3. **utils.py** - Helper functions (badges, email, location)
4. **forms.py** - Form validation
5. **tests.py** - Test examples
6. **README.md** - Complete documentation

---

## Documentation

- **README.md** - Features and usage
- **DEPLOYMENT.md** - Production deployment
- **COMPLETION_SUMMARY.md** - What was built
- This file - Quick reference

---

**Happy coding!** 🎉

For questions or issues, check the documentation files or review the test cases for examples.
