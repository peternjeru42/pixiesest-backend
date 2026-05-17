# Pixieset-style Django Backend

Production-oriented Django REST Framework backend for a lean client gallery platform.

## Stack

- Django + Django REST Framework
- PostgreSQL metadata database
- Cloudflare R2 private object storage through S3-compatible APIs
- Celery + Redis background jobs
- JWT authentication with `djangorestframework-simplejwt`
- OpenAPI docs with `drf-spectacular`
- Railway deployment target

## Original Quality Rule

Uploaded originals are stored unchanged in R2 under:

`users/{user_id}/collections/{collection_id}/originals/{media_id}.{ext}`

Preview, thumbnail, and ZIP export objects are separate keys. Original single downloads and original ZIP jobs always read `MediaAsset.original_file_key`; they do not use preview or thumbnail keys and do not recompress or resize originals.

## Local Setup

1. Create a virtual environment.

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

2. Create `.env` from `.env.example` and provide PostgreSQL, Redis, and Cloudflare R2 values.

3. Run migrations.

```bash
python manage.py makemigrations
python manage.py migrate
```

4. Create an admin user.

```bash
python manage.py createsuperuser
```

5. Start Django.

```bash
python manage.py runserver
```

6. Start Celery in another shell.

```bash
celery -A config worker -l info
```

## API

- Base API path: `/api/v1/`
- OpenAPI schema: `/api/schema/`
- Swagger UI: `/api/docs/`

Owner/admin endpoints require JWT bearer auth. Public gallery endpoints use signed gallery session tokens via `X-Gallery-Session` where collection visibility requires it.

## Email With Resend

The backend uses Django's normal email settings, so Resend is configured as the SMTP provider. Create a Resend API key, verify the sending domain, then set:

```bash
FRONTEND_URL=https://your-frontend-domain.com
EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
EMAIL_HOST=smtp.resend.com
EMAIL_PORT=587
EMAIL_HOST_USER=resend
RESEND_API_KEY=re_xxxxxxxxx
EMAIL_USE_TLS=True
DEFAULT_FROM_EMAIL="Droptop <no-reply@yourdomain.com>"
```

`EMAIL_HOST_PASSWORD` is also supported, but `RESEND_API_KEY` is preferred for clarity. Local development defaults to Django's console email backend unless `EMAIL_BACKEND` is explicitly set.

## Railway

Set the environment variables from `.env.example` in Railway. The default Railway start command runs migrations then starts Gunicorn:

```bash
python manage.py migrate && gunicorn config.wsgi:application --bind 0.0.0.0:$PORT --workers 3
```

Run a separate Railway worker service for Celery:

```bash
celery -A config worker -l info
```
