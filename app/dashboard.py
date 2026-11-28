"""Build the household's Today view at the server's local date boundary."""
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from app import calendar_service, chores as chore_service
from app.dates import local_day
from app.ledger import ADULT_ROLES
from app.mutations import statement


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

    board = chore_service.load_dates(database, user, [day - timedelta(days=offset) for offset in range(29, -1, -1)])
    scheduled = [entry for entry in board['scheduled'] if entry['date'] == today]
    scheduled_overdue = [entry for entry in board['scheduled'] if entry['date'] < today and entry['status'] in {'open', 'declined'}]
    chores, overdue, unscheduled, meals = [], [], [], []
    household = user["household_id"]
    with database.connect() as connection:
        records = statement(connection, """SELECT i.id,i.kind,i.title,i.details,i.due_at,i.assigned_to,
             i.completed,i.value,i.version,u.display_name AS assigned_name,ms.slot,ms.servings
             FROM items i LEFT JOIN users u ON u.id=i.assigned_to AND u.household_id=i.household_id
             LEFT JOIN meal_slots ms ON ms.id=i.id AND ms.household_id=i.household_id
             WHERE i.household_id=:h AND i.kind IN ('task','meal') AND i.deleted_at IS NULL
             AND NOT EXISTS (SELECT 1 FROM chore_completions c WHERE c.id=i.id AND c.household_id=i.household_id)
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
        care = {"maintenance": [], "vehicleReminders": []}
        if user["role"] in ADULT_ROLES:
            maintenance = statement(connection, """SELECT s.id,s.title,s.due_on dueOn,s.season,
                a.category,u.display_name assignedName FROM maintenance_schedules s
                JOIN maintenance_assets a ON a.id=s.asset_id AND a.household_id=s.household_id
                LEFT JOIN users u ON u.id=s.assigned_to AND u.household_id=s.household_id
                WHERE s.household_id=:h AND s.active=1 AND a.archived_at IS NULL AND s.due_on<=:end
                ORDER BY s.due_on,s.title LIMIT 30""", h=household, end=end).mappings()
            service_due = statement(connection, """SELECT v.id vehicleId,v.nickname,v.make,v.model,
                s.service_type serviceType,s.due_on dueOn,s.due_odometer dueOdometer,v.odometer
                FROM vehicle_services s JOIN vehicles v ON v.id=s.vehicle_id AND v.household_id=s.household_id
                WHERE s.household_id=:h AND v.archived_at IS NULL AND
                (s.due_on<=:end OR s.due_odometer IS NOT NULL AND s.due_odometer<=v.odometer+1000)
                ORDER BY COALESCE(s.due_on,'9999-12-31'),s.due_odometer LIMIT 30""", h=household, end=end).mappings()
            registrations = statement(connection, """SELECT id vehicleId,nickname,make,model,
                'Registration renewal' serviceType,registration_due dueOn,NULL dueOdometer,odometer
                FROM vehicles WHERE household_id=:h AND archived_at IS NULL AND registration_due<=:end
                ORDER BY registration_due LIMIT 30""", h=household, end=end).mappings()
            care = {"maintenance": [dict(entry) for entry in maintenance],
                    "vehicleReminders": [dict(entry) for entry in list(service_due) + list(registrations)]}
        return {"date": today, "appointments": appointments, "upcoming": upcoming,
                "chores": chores, "overdue": overdue, "scheduledChores": scheduled, "scheduledOverdue": scheduled_overdue, "unscheduled": unscheduled, "meals": meals,
                "shopping": [dict(entry) for entry in shopping], "balances": [dict(entry) for entry in balances], **care}
