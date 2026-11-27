"""Household announcements and versioned member acknowledgments."""
from datetime import datetime
import uuid
from zoneinfo import ZoneInfo

from app.calendar_service import parse_date
from app.ledger import ADULT_ROLES
from app.mutations import DomainError, Mutation, clean, expected_version, row, statement

NOTES = """SELECT i.id,i.title,i.details,i.version,i.created_at,a.expires_on,
    COALESCE(a.pinned,0) AS pinned,r.read_version=i.version AS acknowledged,
    (SELECT COUNT(*) FROM announcement_reads ar
     WHERE ar.household_id=i.household_id AND ar.announcement_id=i.id AND ar.read_version=i.version) AS ack_count
    FROM items i LEFT JOIN announcement_settings a ON a.id=i.id AND a.household_id=i.household_id
    LEFT JOIN announcement_reads r ON r.announcement_id=i.id AND r.household_id=i.household_id AND r.member_id=:actor
    WHERE i.household_id=:h AND i.kind='announcement' AND i.deleted_at IS NULL"""


def current_day(user):
    return datetime.now(ZoneInfo(user["timezone"])).date().isoformat()


def visible(record, date):
    return not record["expires_on"] or record["expires_on"] >= date


def payload(item):
    return {**item, "pinned": bool(item["pinned"]), "acknowledged": bool(item["acknowledged"]),
            "ackCount": item["ack_count"]}


def load(database, user, *, archive=False):
    if archive and user["role"] not in ADULT_ROLES:
        raise DomainError(403, "Only an adult can read expired announcements.")
    day = current_day(user)
    condition = "" if archive else " AND (a.expires_on IS NULL OR a.expires_on>=:day)"
    with database.connect() as connection:
        notes = statement(connection, NOTES + condition + " ORDER BY pinned DESC,i.created_at DESC,i.id",
                          actor=user["id"], h=user["household_id"], day=day).mappings()
        return {"items": [payload(item) for item in notes], "date": day}


def write(database, user, operation, target, data):
    if operation != "announcement.ack" and user["role"] not in ADULT_ROLES:
        raise DomainError(403, "Only an adult can publish household announcements.")
    with database.connect() as connection:
        connection.exec_driver_sql("BEGIN IMMEDIATE")
        mutation = Mutation(connection, user, operation, data, target)
        entity = mutation.replay_id
        household, actor = user["household_id"], user["id"]
        record = None
        if not entity:
            entity = target or str(uuid.uuid4())
            keys = {"id": entity, "h": household, "actor": actor}
            version = 1
            if target:
                record = row(connection, NOTES + " AND i.id=:id", **keys)
                if not record or operation == "announcement.ack" and not visible(record, current_day(user)):
                    raise DomainError(404, "This announcement was not found.")
                if record["version"] != expected_version(data):
                    raise DomainError(409, "This announcement changed. Refresh and try again.")
                version = record["version"] + (operation != "announcement.ack")
            if operation == "announcement.ack":
                statement(connection, """INSERT INTO announcement_reads(announcement_id,member_id,household_id,read_version)
                    VALUES(:id,:actor,:h,:v) ON CONFLICT(announcement_id,member_id) DO UPDATE SET
                    read_version=:v,read_at=CURRENT_TIMESTAMP WHERE household_id=:h""", **keys, v=version)
            elif operation == "announcement.archive":
                statement(connection, "UPDATE items SET deleted_at=CURRENT_TIMESTAMP,version=:v WHERE id=:id AND household_id=:h",
                          **keys, v=version)
            else:
                pinned = data.get("pinned", False)
                expiry = data.get("expiresOn", "")
                if type(pinned) is not bool or not isinstance(expiry, str):
                    raise DomainError(422, "Check the pinned status and expiration date.")
                fields = {"title": clean(data.get("title"), 120, required=True),
                          "details": clean(data.get("details"), 1000, required=True), "pinned": int(pinned),
                          "expiry": parse_date(expiry).isoformat() if expiry else None, "v": version}
                if target:
                    statement(connection, """UPDATE items SET title=:title,details=:details,version=:v,
                        updated_at=CURRENT_TIMESTAMP WHERE id=:id AND household_id=:h""", **keys, **fields)
                else:
                    statement(connection, """INSERT INTO items(id,household_id,kind,title,details,created_by)
                        VALUES(:id,:h,'announcement',:title,:details,:actor)""", **keys, **fields)
                statement(connection, """INSERT INTO announcement_settings(id,household_id,pinned,expires_on)
                    VALUES(:id,:h,:pinned,:expiry) ON CONFLICT(id) DO UPDATE SET pinned=:pinned,expires_on=:expiry
                    WHERE household_id=:h""", **keys, **fields)
            mutation.finish(entity, version)
            connection.commit()
        event = None if mutation.replay_id else entity
        if operation == "announcement.archive":
            return 204, None, event
        record = row(connection, NOTES + " AND i.id=:id", id=entity, h=household, actor=actor)
        if not record:
            raise DomainError(404, "This announcement was not found.")
        return 201 if operation == "announcement.create" else 200, payload(record), event
