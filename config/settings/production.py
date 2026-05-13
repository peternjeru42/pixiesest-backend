from .base import *  # noqa

DEBUG = False
ALLOWED_HOSTS = env_host_list(
    "ALLOWED_HOSTS",
    ".up.railway.app,localhost,127.0.0.1",
)

for railway_host in (
    env("RAILWAY_PUBLIC_DOMAIN", ""),
    env("RAILWAY_PRIVATE_DOMAIN", ""),
):
    if railway_host and railway_host not in ALLOWED_HOSTS:
        ALLOWED_HOSTS.append(railway_host)

SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
SECURE_SSL_REDIRECT = env_bool("SECURE_SSL_REDIRECT", True)
SECURE_REDIRECT_EXEMPT = [r"^health/$"]
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
CSRF_TRUSTED_ORIGINS = env_origin_list("CSRF_TRUSTED_ORIGINS", "")

for railway_origin in (
    env("RAILWAY_PUBLIC_DOMAIN", ""),
    env("RAILWAY_PRIVATE_DOMAIN", ""),
):
    if railway_origin:
        origin = f"https://{railway_origin}"
        if origin not in CSRF_TRUSTED_ORIGINS:
            CSRF_TRUSTED_ORIGINS.append(origin)
