"""Exact-cent allowance credits and paid-out entries."""
from decimal import Decimal
import re
import uuid

from app.ledger import ADULT_ROLES
from app.mutations import DomainError, Mutation, clean, expected_version, row, statement

WALLETS = """SELECT u.id,u.display_name,COALESCE(SUM(a.amount_cents),0) AS balance,COUNT(a.id)+1 AS version
    FROM users u LEFT JOIN allowance_entries a ON a.member_id=u.id AND a.household_id=u.household_id
    WHERE u.household_id=:h AND u.disabled_at IS NULL AND u.role<>'display'"""
ENTRIES = """SELECT a.id,a.member_id,a.amount_cents,a.note,a.created_at,u.display_name
    FROM allowance_entries a JOIN users u ON u.id=a.member_id AND u.household_id=a.household_id
    WHERE a.household_id=:h"""


def load(database, user):
    if user["role"] == "display":
        raise DomainError(403, "This account cannot read allowance balances.")
    household, actor = user["household_id"], user["id"]
    adult = user["role"] in ADULT_ROLES
    with database.connect() as connection:
        wallets = statement(connection, WALLETS + ("" if adult else " AND u.id=:actor") +
                            " GROUP BY u.id ORDER BY u.display_name,u.id", h=household, actor=actor).mappings()
        entries = statement(connection, ENTRIES + ("" if adult else " AND a.member_id=:actor") +
                            " ORDER BY a.created_at DESC,a.rowid DESC LIMIT 75", h=household, actor=actor).mappings()
        return {"wallets": [dict(wallet) for wallet in wallets], "entries": [dict(entry) for entry in entries]}


def amount_in_cents(value):
    if not isinstance(value, str) or not re.fullmatch(r"[0-9]{1,5}(?:\.[0-9]{1,2})?", value):
        raise DomainError(422, "Enter a positive amount with up to two decimal places.")
    cents = int(Decimal(value) * 100)
    if not cents:
        raise DomainError(422, "Enter a positive amount.")
    return cents


def write(database, user, operation, target, data):
    if user["role"] not in ADULT_ROLES:
        raise DomainError(403, "Only an adult can record allowance changes.")
    household, actor = user["household_id"], user["id"]
    member = clean(data.get("memberId"), 64, required=True)
    note = clean(data.get("note"), 200, required=True)
    direction = data.get("direction")
    if direction not in ("credit", "paid"):
        raise DomainError(422, "Choose an allowance credit or payout.")
    amount = amount_in_cents(data.get("amount")) * (1 if direction == "credit" else -1)
    values = {"h": household, "member": member, "actor": actor}
    with database.connect() as connection:
        connection.exec_driver_sql("BEGIN IMMEDIATE")
        mutation = Mutation(connection, user, operation, data, member)
        wallet = row(connection, WALLETS + " AND u.id=:member GROUP BY u.id", **values)
        if not wallet:
            raise DomainError(404, "This allowance account was not found.")
        if mutation.replay_id:
            return 201, dict(wallet), None
        version = expected_version(data)
        if wallet["version"] != version:
            raise DomainError(409, "This allowance balance changed. Refresh and try again.")
        if wallet["balance"] + amount < 0:
            raise DomainError(409, "This payout exceeds the current allowance balance.")
        entry = str(uuid.uuid4())
        statement(connection, """INSERT INTO allowance_entries(id,household_id,member_id,actor_id,note,amount_cents)
            VALUES(:id,:h,:member,:actor,:note,:amount)""", **values, id=entry, note=note, amount=amount)
        mutation.finish(entry, version + 1)
        connection.commit()
        return 201, dict(wallet, balance=wallet["balance"] + amount, version=version + 1), entry
