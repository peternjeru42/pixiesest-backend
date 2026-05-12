from .models import ActivityEvent


def log_activity(
    *,
    owner,
    event_type,
    collection=None,
    set=None,
    media_asset=None,
    actor_type="system",
    actor_email="",
    metadata=None,
    request=None,
):
    ip_address = None
    user_agent = ""
    if request is not None:
        ip_address = request.META.get("HTTP_X_FORWARDED_FOR", request.META.get("REMOTE_ADDR", "")).split(",")[0] or None
        user_agent = request.META.get("HTTP_USER_AGENT", "")
    return ActivityEvent.objects.create(
        owner=owner,
        collection=collection,
        set=set,
        media_asset=media_asset,
        event_type=event_type,
        actor_type=actor_type,
        actor_email=actor_email or "",
        metadata=metadata or {},
        ip_address=ip_address,
        user_agent=user_agent,
    )
