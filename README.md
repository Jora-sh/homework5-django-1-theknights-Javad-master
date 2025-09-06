# Job Portal

A comprehensive job portal built with Django where employers can post jobs and job seekers can apply with their resumes.

## Features

- User authentication (employer/job seeker)
- Job posting and management
- Resume upload and job application
- Email notifications
- Dashboard for both employers and job seekers
- Search and filter jobs

## Setup and Installation

1. Clone the repository
2. Create a virtual environment: `python -m venv venv`
3. Activate the virtual environment:
   - Windows: `venv\Scripts\activate`
   - Unix/MacOS: `source venv/bin/activate`
4. Install dependencies: `pip install -r requirements.txt`
5. Run migrations: `python manage.py migrate`
6. Create a superuser: `python manage.py createsuperuser`
7. Run the development server: `python manage.py runserver`

## Email Configuration

### Development Environment

By default, in development mode (when `DEBUG=True`), emails are sent to the console instead of actually being delivered. This is configured with:

```python
EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'
```

You'll see email contents printed in the console when they're sent.

### Production Environment

For production deployment, set up proper SMTP settings by configuring the following environment variables:

1. `EMAIL_HOST` - SMTP server (default: 'smtp.gmail.com')
2. `EMAIL_PORT` - SMTP port (default: 587)
3. `EMAIL_HOST_USER` - Your email address
4. `EMAIL_HOST_PASSWORD` - Your email password or app password

For Gmail, you'll need to:

1. Enable 2-Step Verification on your Google account
2. Create an App Password for your application
3. Use that App Password as `EMAIL_HOST_PASSWORD`

In your deployment environment, set `DEBUG=False` to automatically switch to the SMTP backend.

### Email Templates

The system sends emails for:

1. Email verification during registration
2. Welcome email after verification
3. Password reset
4. Job application notifications (to employers)

Email templates are located in `templates/emails/` and can be customized as needed.

## API (REST) Endpoints

The project now includes a simple REST API for account management using Django REST Framework and JWT (Simple JWT).

Added endpoints (prefix /api/accounts/):

- POST /api/accounts/register/ -> create user (email, password, first_name, last_name, role='seeker'|'employer')
- POST /api/accounts/login/ -> obtain JWT (access + refresh)
- POST /api/accounts/token/refresh/ -> refresh access token
- POST /api/accounts/logout/ -> blacklist refresh token (requires refresh token in body)
- GET/PUT /api/accounts/me/ -> get or update current user (requires Authorization: Bearer <access>)

Notes:

- Install dependencies: pip install djangorestframework djangorestframework-simplejwt
- After installing, run migrations to create tables for token blacklist: python manage.py migrate

## License

[MIT License](LICENSE)
