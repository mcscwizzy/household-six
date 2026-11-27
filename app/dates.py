"""Calendar-date interpretation for legacy records."""
from datetime import date, datetime


def local_day(value, zone):
    if not value:
        return None
    try:
        return date.fromisoformat(value)
    except ValueError:
        pass
    try:
        point = datetime.fromisoformat(value)
        return (point.astimezone(zone) if point.tzinfo else point).date()
    except (ValueError, OverflowError):
        return None
