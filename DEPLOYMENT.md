# Deployment Guide - Hyper-Local Food Rescue

This guide covers deploying the Hyper-Local Food Rescue application to production.

## Pre-Deployment Checklist

- [ ] All tests pass: `python manage.py test`
- [ ] No untracked database migrations: `python manage.py makemigrations --check`
- [ ] Collect static files: `python manage.py collectstatic --noinput`
- [ ] Review security settings in settings.py
- [ ] Set up environment variables for sensitive data
- [ ] Configure email service credentials
- [ ] Set up database backups
- [ ] Review and test error pages (404, 500, etc.)

## Environment Setup

### 1. Create .env file (Never commit this)
```
SECRET_KEY=your-secret-key-here
DEBUG=False
ALLOWED_HOSTS=yourdomain.com,www.yourdomain.com
DATABASE_URL=postgresql://user:password@localhost/foodrescue
EMAIL_HOST=smtp.gmail.com
EMAIL_HOST_USER=your-email@gmail.com
EMAIL_HOST_PASSWORD=your-app-password
CSRF_TRUSTED_ORIGINS=https://yourdomain.com,https://www.yourdomain.com
```

### 2. Update settings.py for production
```python
import os
from pathlib import Path

# Load environment variables
from decouple import config

SECRET_KEY = config('SECRET_KEY')
DEBUG = config('DEBUG', default=False, cast=bool)
ALLOWED_HOSTS = config('ALLOWED_HOSTS', cast=lambda v: [s.strip() for s in v.split(',')])

# Database - Use PostgreSQL in production
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': config('DATABASE_NAME', default='foodrescue'),
        'USER': config('DATABASE_USER'),
        'PASSWORD': config('DATABASE_PASSWORD'),
        'HOST': config('DATABASE_HOST', default='localhost'),
        'PORT': config('DATABASE_PORT', default=5432),
    }
}

# Email Configuration
EMAIL_HOST = config('EMAIL_HOST')
EMAIL_HOST_USER = config('EMAIL_HOST_USER')
EMAIL_HOST_PASSWORD = config('EMAIL_HOST_PASSWORD')
EMAIL_PORT = 587
EMAIL_USE_TLS = True

# Security Settings
SECURE_SSL_REDIRECT = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
CSRF_TRUSTED_ORIGINS = config('CSRF_TRUSTED_ORIGINS', cast=lambda v: [s.strip() for s in v.split(',')])

# Static and Media Files
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')
MEDIA_ROOT = os.path.join(BASE_DIR, 'media')

# Logging Configuration
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {process:d} {thread:d} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'file': {
            'level': 'INFO',
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': '/var/log/django/foodrescue.log',
            'maxBytes': 1024 * 1024 * 10,  # 10MB
            'backupCount': 10,
            'formatter': 'verbose',
        },
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'verbose',
        },
    },
    'root': {
        'handlers': ['file', 'console'],
        'level': 'INFO',
    },
}
```

## Deployment Options

### Option 1: Heroku Deployment

1. **Install Heroku CLI**
```bash
curl https://cli.heroku.com/install.sh | sh
```

2. **Create Procfile**
```
web: gunicorn myproject.wsgi
release: python manage.py migrate
```

3. **Create runtime.txt**
```
python-3.11.0
```

4. **Install production dependencies**
```bash
pip install gunicorn whitenoise psycopg2-binary python-decouple
```

5. **Push to Heroku**
```bash
heroku create your-app-name
heroku config:set SECRET_KEY=your-secret-key
heroku config:set DEBUG=False
heroku config:set EMAIL_HOST_USER=your-email
heroku config:set EMAIL_HOST_PASSWORD=your-password
git push heroku main
heroku run python manage.py migrate
heroku run python manage.py createsuperuser
heroku run python manage.py populate_badges
```

### Option 2: DigitalOcean / AWS / Linode (Traditional VPS)

1. **SSH into your server**
```bash
ssh root@your-server-ip
```

2. **Install system dependencies**
```bash
apt-get update
apt-get install -y python3-pip python3-venv postgresql postgresql-contrib nginx supervisor
```

3. **Create application directory**
```bash
mkdir /home/foodrescue
cd /home/foodrescue
```

4. **Clone repository and setup**
```bash
git clone https://github.com/yourusername/food-rescue.git
cd food-rescue
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
pip install gunicorn psycopg2-binary
```

5. **Create PostgreSQL database**
```bash
sudo -u postgres psql
CREATE DATABASE foodrescue;
CREATE USER foodrescue_user WITH PASSWORD 'your-secure-password';
ALTER ROLE foodrescue_user SET client_encoding TO 'utf8';
ALTER ROLE foodrescue_user SET default_transaction_isolation TO 'read committed';
ALTER ROLE foodrescue_user SET default_transaction_deferrable TO on;
ALTER ROLE foodrescue_user SET timezone TO 'UTC';
GRANT ALL PRIVILEGES ON DATABASE foodrescue TO foodrescue_user;
\q
```

6. **Run migrations**
```bash
python manage.py migrate
python manage.py createsuperuser
python manage.py populate_badges
python manage.py collectstatic --noinput
```

7. **Configure Gunicorn**

Create `/etc/supervisor/conf.d/foodrescue.conf`:
```ini
[program:foodrescue]
directory=/home/foodrescue/food-rescue
command=/home/foodrescue/food-rescue/venv/bin/gunicorn --workers 3 --bind 0.0.0.0:8000 myproject.wsgi
autostart=true
autorestart=true
stderr_logfile=/var/log/foodrescue/err.log
stdout_logfile=/var/log/foodrescue/out.log
```

8. **Configure Nginx**

Create `/etc/nginx/sites-available/foodrescue`:
```nginx
upstream foodrescue {
    server 0.0.0.0:8000;
}

server {
    listen 80;
    server_name yourdomain.com www.yourdomain.com;

    location /static/ {
        alias /home/foodrescue/food-rescue/staticfiles/;
    }

    location /media/ {
        alias /home/foodrescue/food-rescue/media/;
    }

    location / {
        proxy_pass http://foodrescue;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

Enable the site:
```bash
sudo ln -s /etc/nginx/sites-available/foodrescue /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl restart nginx
```

9. **Setup SSL with Let's Encrypt**
```bash
apt-get install certbot python3-certbot-nginx
certbot --nginx -d yourdomain.com -d www.yourdomain.com
```

10. **Start services**
```bash
supervisorctl reread
supervisorctl update
supervisorctl start foodrescue
```

## Post-Deployment

### 1. Create admin user
```bash
python manage.py createsuperuser
```

### 2. Populate badges
```bash
python manage.py populate_badges
```

### 3. Test the application
- Visit https://yourdomain.com
- Log in to admin at https://yourdomain.com/admin
- Test email functionality
- Verify image uploads work

### 4. Setup monitoring and backups

Monitor with:
- New Relic
- Sentry for error tracking
- DataDog or similar

Backup with:
```bash
# Daily PostgreSQL backup
0 2 * * * /usr/bin/pg_dump foodrescue | gzip > /backups/foodrescue_$(date +\%Y\%m\%d).sql.gz

# Backup media files
0 3 * * * tar -czf /backups/media_$(date +\%Y\%m\%d).tar.gz /home/foodrescue/food-rescue/media/
```

## Troubleshooting Deployment

### 502 Bad Gateway
- Check Gunicorn is running: `supervisorctl status`
- Check Gunicorn logs: `tail -f /var/log/foodrescue/err.log`
- Restart Gunicorn: `supervisorctl restart foodrescue`

### Static files not loading
```bash
python manage.py collectstatic --noinput --clear
```

### Email not sending
- Check credentials in .env
- Verify SMTP service is accessible
- Check EMAIL_BACKEND in settings.py

### Database connection errors
- Verify PostgreSQL is running
- Check DATABASE_URL in .env
- Verify firewall rules

## Performance Optimization

### Caching
```python
CACHES = {
    'default': {
        'BACKEND': 'django_redis.cache.RedisCache',
        'LOCATION': 'redis://127.0.0.1:6379/1',
    }
}
```

### Database optimization
- Create indexes on frequently queried fields
- Use `select_related()` and `prefetch_related()` in views
- Enable query caching

### Static files
- Use CDN (CloudFlare, AWS CloudFront)
- Enable gzip compression
- Minify CSS and JavaScript

## Security Hardening

1. Update Django security settings
2. Enable rate limiting
3. Setup WAF (Web Application Firewall)
4. Regular security updates
5. SQL injection prevention (already handled by Django ORM)
6. CSRF protection enabled
7. XSS protection enabled

## Monitoring

Setup alerts for:
- High CPU/Memory usage
- Database connection pool exhausted
- Email sending failures
- Error rates above threshold
- API response time degradation
