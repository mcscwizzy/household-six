"""Household inventory locations, levels, expiry, and stock movements."""
from datetime import datetime
from decimal import Decimal
import re
import uuid
from zoneinfo import ZoneInfo

from app.calendar_service import parse_date
from app.dates import local_day
from app.ledger import ADULT_ROLES
from app.mutations import DomainError, Mutation, clean, expected_version, row, statement

LOCATIONS = ("pantry", "refrigerator", "freezer")
ITEMS = """SELECT i.id,i.title,i.details,i.due_at AS legacy_date,i.version,s.location,s.quantity,s.unit,
    s.threshold,s.expires_on FROM items i LEFT JOIN inventory_stock s ON s.id=i.id AND s.household_id=i.household_id
    WHERE i.household_id=:h AND i.kind='inventory' AND i.deleted_at IS NULL"""


def quantity(value, *, positive=False):
    if not isinstance(value, str) or not re.fullmatch(r"[0-9]{1,6}(?:\.[0-9]{1,4})?", value):
        raise DomainError(422, "Enter a stock quantity with up to four decimal places.")
    number = Decimal(value)
    if positive and not number:
        raise DomainError(422, "Enter a positive stock quantity.")
    return number


def formatted(number):
    return format(number.normalize(), "f")


def exposed(item, user):
    data = dict(item)
    zone = ZoneInfo(user["timezone"])
    date = data["expires_on"] or local_day(data.pop("legacy_date"), zone)
    data.pop("legacy_date", None)
    data["expires_on"] = date.isoformat() if hasattr(date, "isoformat") else date
    data["low"] = bool(data["quantity"] is not None and Decimal(data["quantity"]) <= Decimal(data["threshold"]))
    data["expired"] = bool(data["expires_on"] and data["expires_on"] < datetime.now(zone).date().isoformat())
    return data


def load(database, user, location):
    if location and location not in LOCATIONS:
        raise DomainError(422, "Choose an inventory location.")
    household = user["household_id"]
    condition = " AND s.location=:location" if location else ""
    with database.connect() as connection:
        items = statement(connection, ITEMS + condition + " ORDER BY i.title,i.id",
                          h=household, location=location).mappings()
        movements = statement(connection, """SELECT m.id,m.direction,m.amount,m.unit,m.created_at,i.title
            FROM stock_movements m JOIN items i ON i.id=m.item_id AND i.household_id=m.household_id
            LEFT JOIN inventory_stock s ON s.id=m.item_id AND s.household_id=m.household_id
            WHERE m.household_id=:h""" + condition + " ORDER BY m.created_at DESC,m.id DESC LIMIT 50",
                              h=household, location=location).mappings()
        return {"items": [exposed(item, user) for item in items], "history": [dict(item) for item in movements]}


def find(connection, household, entity):
    current = row(connection, ITEMS + " AND i.id=:id", id=entity, h=household)
    if not current:
        raise DomainError(404, "This inventory item was not found.")
    return current


def save(connection, user, operation, target, data):
    household = user["household_id"]
    entity = target or str(uuid.uuid4())
    params = {"id": entity, "h": household, "actor": user["id"]}
    version = 1
    if target:
        current = find(connection, household, target)
        if current["version"] != expected_version(data):
            raise DomainError(409, "This inventory item changed. Refresh and try again.")
        version = current["version"] + 1
    if operation == "inventory.archive":
        statement(connection, "UPDATE items SET deleted_at=CURRENT_TIMESTAMP,version=:v WHERE id=:id AND household_id=:h",
                  **params, v=version)
    elif operation == "inventory.stock":
        direction = data.get("direction")
        if direction not in ("restock", "use") or current["quantity"] is None:
            raise DomainError(422, "Set the item’s stock details first and choose a stock action.")
        amount = quantity(data.get("amount"), positive=True)
        total = Decimal(current["quantity"]) + (amount if direction == "restock" else -amount)
        if not 0 <= total < Decimal("1000000"):
            raise DomainError(409, "This change would put stock outside the supported range.")
        statement(connection, "UPDATE inventory_stock SET quantity=:q WHERE id=:id AND household_id=:h",
                  **params, q=formatted(total))
        statement(connection, "UPDATE items SET version=:v,updated_at=CURRENT_TIMESTAMP WHERE id=:id AND household_id=:h",
                  **params, v=version)
        statement(connection, """INSERT INTO stock_movements(id,household_id,item_id,actor_id,direction,amount,unit)
            VALUES(:movement,:h,:id,:actor,:direction,:amount,:unit)""", **params,
                  movement=str(uuid.uuid4()), direction=direction, amount=formatted(amount), unit=current["unit"])
    else:
        location = data.get("location")
        if location not in LOCATIONS:
            raise DomainError(422, "Choose an inventory location.")
        expiry = data.get("expiresOn", "")
        expires_on = parse_date(expiry).isoformat() if expiry else None
        fields = {"title": clean(data.get("title"), 120, required=True), "details": clean(data.get("details", ""), 1000),
                  "location": location, "q": formatted(quantity(data.get("quantity"))),
                  "unit": clean(data.get("unit", ""), 40), "limit": formatted(quantity(data.get("threshold", "0"))),
                  "expiry": expires_on, "v": version}
        if target:
            statement(connection, """UPDATE items SET title=:title,details=:details,due_at=:expiry,version=:v,
                updated_at=CURRENT_TIMESTAMP WHERE id=:id AND household_id=:h""", **params, **fields)
        else:
            statement(connection, """INSERT INTO items(id,household_id,kind,title,details,due_at,created_by)
                VALUES(:id,:h,'inventory',:title,:details,:expiry,:actor)""", **params, **fields)
        statement(connection, """INSERT INTO inventory_stock(id,household_id,location,quantity,unit,threshold,expires_on)
            VALUES(:id,:h,:location,:q,:unit,:limit,:expiry) ON CONFLICT(id) DO UPDATE SET
            location=:location,quantity=:q,unit=:unit,threshold=:limit,expires_on=:expiry WHERE household_id=:h""",
                  **params, **fields)
    return entity, version


def write(database, user, operation, target, data):
    if user["role"] not in ADULT_ROLES:
        raise DomainError(403, "Only an adult can change inventory.")
    with database.connect() as connection:
        connection.exec_driver_sql("BEGIN IMMEDIATE")
        mutation = Mutation(connection, user, operation, data, target)
        entity = mutation.replay_id
        if not entity:
            entity, version = save(connection, user, operation, target, data)
            mutation.finish(entity, version)
            connection.commit()
        changed = None if mutation.replay_id else entity
        if operation == "inventory.archive":
            return 204, None, changed
        return (201 if operation == "inventory.create" else 200,
                exposed(find(connection, user["household_id"], entity), user), changed)
