"""Build the household's Today view at the server's local date boundary."""
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

from app import calendar_service
from app.mutations import statement


def local_day(value, zone):
    if not value:
        return None
    try:
        if len(value) == 10:
            return date.fromisoformat(value)
        point = datetime.fromisoformat(value)
        return (point.astimezone(zone) if point.tzinfo else point).date()
    except (ValueError, OverflowError):
        return None


def load(database, user):
    zone = ZoneInfo(user["timezone"])
    day = datetime.now(zone).date()
    today = day.isoformat()
    end = (day + timedelta(days=8)).isoformat()
    calendar = calendar_service.load(database, user, today, end)
    appointments, upcoming = [], []
    for entry in calendar["events"]:
        start = entry["occurrenceStart"][:10]
        collection = appointments if start <= today else upcoming
        collection.append(entry)

    chores, overdue, unscheduled, meals = [], [], [], []
    household = user["household_id"]
    with database.connect() as connection:
        records = statement(connection, """SELECT i.id,i.kind,i.title,i.details,i.due_at,i.assigned_to,
             i.completed,i.value,i.version,u.display_name AS assigned_name
             FROM items i LEFT JOIN users u ON u.id=i.assigned_to AND u.household_id=i.household_id
             WHERE i.household_id=:h AND i.kind IN ('task','meal') AND i.deleted_at IS NULL
             ORDER BY i.completed,i.due_at,i.created_at,i.id""", h=household).mappings()
        for record in records:
            due = local_day(record["due_at"], zone)
            if record["kind"] == "meal":
                if due == day:
                    meals.append(dict(record))
            elif due == day:
                chores.append(dict(record))
            elif not record["completed"]:
                if due is None:
                    unscheduled.append(dict(record))
                elif due < day:
                    overdue.append(dict(record))
        shopping = statement(connection, """SELECT COALESCE(s.name,'Groceries') AS name,
            COALESCE(s.id,'default') AS id,COUNT(*) AS total,SUM(i.completed=0) AS open
            FROM items i LEFT JOIN shopping_lists s ON s.id=i.shopping_list_id AND s.household_id=i.household_id
            WHERE i.household_id=:h AND i.kind='shopping' AND i.deleted_at IS NULL
            GROUP BY s.id,s.name ORDER BY name,id""", h=household).mappings()
        balances = statement(connection, """SELECT u.id,u.display_name,u.role,u.color,COALESCE(SUM(p.amount),0) AS points
            FROM users u LEFT JOIN points_ledger p ON p.member_id=u.id AND p.household_id=u.household_id
            WHERE u.household_id=:h AND u.disabled_at IS NULL AND u.role<>'display'
            GROUP BY u.id ORDER BY u.created_at,u.id""", h=household).mappings()
        return {"date": today, "appointments": appointments, "upcoming": upcoming,
                "chores": chores, "overdue": overdue, "unscheduled": unscheduled, "meals": meals,
                "shopping": [dict(entry) for entry in shopping], "balances": [dict(entry) for entry in balances]}
