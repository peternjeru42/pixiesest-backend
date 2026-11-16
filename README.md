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

## Payments With Paystack

Droptop creates the Basic, Plus, and Pro monthly plans in Paystack automatically. Keep both Paystack values on the Railway backend and worker services; neither value belongs in the Next.js frontend:

```bash
PAYSTACK_SECRET_KEY=sk_test_xxxxx
PAYSTACK_WEBHOOK_SECRET=whsec_xxxxx
```

Use test values until checkout, renewal, cancellation, and failed-payment behavior have been accepted. Replace both with live-mode values for production. Configure the Paystack webhook destination as:

```text
https://<your-railway-backend-domain>/api/v1/billing/webhooks/paystack/
```

The webhook handler validates the timestamped `Paystack-Signature` header and supports the legacy `x-paystack-signature` during Paystack's transition. It stores each delivery before queueing work, ignores duplicate deliveries, and retries unprocessed events through Celery Beat.

The hosted checkout callback is:

```text
https://<your-frontend-domain>/billing/callback
```

`FRONTEND_URL` must match that frontend origin. Initial payments are also verified directly with Paystack before access is granted; browser callback parameters are never trusted on their own.

## Railway

Set the environment variables from `.env.example` in Railway. The backend uses
the Docker image's default start command:

```bash
sh ./start.sh
```

Run a separate Railway worker service for Celery. The worker script also runs the
periodic export cleanup scheduler; run exactly one worker service with `--beat`:

```bash
sh ./worker.sh
```

Set the Celery worker service's Railway **Config File Path** to
`/railway.worker.toml`; the backend service continues to use `/railway.toml`.

The production defaults use one Gunicorn worker and one Celery child process to
bound idle and peak memory. Increase `WEB_CONCURRENCY` or
`CELERY_WORKER_CONCURRENCY` only after checking Railway metrics. Configure the
backend and worker with Railway's private `DATABASE_URL` and `REDIS_URL`
reference variables (hosts should end in `.railway.internal`), not public URLs.

In Railway, also verify that the production environment has one replica per
service, remove unused PR/staging environments, and configure usage alerts and a
hard spending limit under Workspace settings.
