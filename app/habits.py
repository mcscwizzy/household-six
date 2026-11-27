"""Member habit tracking with household-local daily streaks."""
from datetime import date, datetime, timedelta
import uuid
from zoneinfo import ZoneInfo

from app.ledger import ADULT_ROLES
from app.mutations import DomainError, Mutation, clean, expected_version, row, statement

HABITS = """SELECT a.id,a.member_id,a.title,a.details,a.version,u.display_name
    FROM habits a JOIN users u ON u.id=a.member_id AND u.household_id=a.household_id
    WHERE a.household_id=:h AND a.archived_at IS NULL AND u.disabled_at IS NULL"""


def local_today(user):
    return datetime.now(ZoneInfo(user["timezone"])).date()


def habits_for(connection, user, entity=None):
    if user["role"] == "display":
        return []
    household, member = user["household_id"], user["id"]
    sql = HABITS
    if user["role"] not in ADULT_ROLES:
        sql += " AND a.member_id=:member"
    if entity:
        sql += " AND a.id=:entity"
    records = statement(connection, sql + " ORDER BY a.title,a.id",
                        h=household, member=member, entity=entity).mappings()
    today = local_today(user)
    result = []
    for habit in records:
        dates = [date.fromisoformat(record["day"]) for record in statement(connection, """SELECT day
             FROM habit_checkins WHERE household_id=:h AND habit_id=:id ORDER BY day DESC""",
             h=household, id=habit["id"]).mappings()]
        expected = today if dates and dates[0] == today else today - timedelta(days=1)
        streak = 0
        for day in dates:
            if day != expected:
                break
            streak += 1
            expected -= timedelta(days=1)
        result.append({**habit, "streak": streak, "checked": bool(dates and dates[0] == today),
                       "days": [day.isoformat() for day in dates[:30]]})
    return result


def load(database, user):
    with database.connect() as connection:
        return {"habits": habits_for(connection, user), "date": local_today(user).isoformat()}


def write(database, user, operation, target, data):
    if user["role"] == "display":
        raise DomainError(403, "This account cannot change habits.")
    household, actor = user["household_id"], user["id"]
    with database.connect() as connection:
        connection.exec_driver_sql("BEGIN IMMEDIATE")
        mutation = Mutation(connection, user, operation, data, target)
        entity = mutation.replay_id
        if not entity:
            entity = target or str(uuid.uuid4())
            params = {"h": household, "actor": actor, "id": entity}
            version = 1
            previous = None
            if target:
                matches = habits_for(connection, user, entity)
                if not matches:
                    raise DomainError(404, "This habit was not found.")
                previous = matches[0]
                version = previous["version"]
                if expected_version(data) != version:
                    raise DomainError(409, "This habit changed. Refresh and try again.")
            if operation == "habit.check":
                day = local_today(user).isoformat()
                if data.get("date") != day:
                    raise DomainError(409, "The household date changed. Refresh and check in again.")
                statement(connection, """INSERT INTO habit_checkins(habit_id,day,household_id,actor_id)
                    VALUES(:id,:day,:h,:actor) ON CONFLICT(habit_id,day) DO NOTHING""", **params, day=day)
            elif operation == "habit.archive":
                version += 1
                statement(connection, "UPDATE habits SET archived_at=CURRENT_TIMESTAMP,version=:v WHERE id=:id AND household_id=:h",
                          **params, v=version)
            else:
                member = clean(data.get("memberId", ""), 64) or actor
                if (user["role"] not in ADULT_ROLES and member != actor) or not row(connection,
                    "SELECT 1 FROM users WHERE id=:member AND household_id=:h AND disabled_at IS NULL AND role<>'display'",
                    **params, member=member):
                    raise DomainError(422, "Choose an enabled member in this household.")
                if previous and previous["member_id"] != member:
                    raise DomainError(422, "Keep the original member for this habit.")
                fields = {"member": member, "title": clean(data.get("title"), 120, required=True),
                          "details": clean(data.get("details", ""), 1000)}
                if previous:
                    version += 1
                    statement(connection, """UPDATE habits SET title=:title, details=:details,version=:v
                        WHERE household_id=:h AND id=:id""", **params, **fields, v=version)
                else:
                    statement(connection, """INSERT INTO habits(id,household_id,member_id,title,details)
                        VALUES(:id,:h,:member,:title,:details)""", **params, **fields)
            mutation.finish(entity, version)
            connection.commit()
        changed = None if mutation.replay_id else entity
        if operation == "habit.archive":
            return 204, None, changed
        result = habits_for(connection, user, entity)
        if not result:
            raise DomainError(404, "This habit was not found.")
        return 201 if operation == "habit.create" else 200, result[0], changed
