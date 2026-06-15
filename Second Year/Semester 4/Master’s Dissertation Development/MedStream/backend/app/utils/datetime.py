from datetime import datetime, timezone


def now_utc():
    return datetime.now(timezone.utc)


def to_utc(dt):
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt
