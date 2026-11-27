"""Shared ledger operations used by transactional chore and reward flows."""
import uuid

from app.mutations import DomainError, row, statement

ADULT_ROLES = {"owner", "admin", "adult"}


def point_value(data, *, minimum=0):
    value = data.get("points", 0)
    if type(value) is not int or not minimum <= value <= 10_000:
        raise DomainError(422, f"Choose a point value from {minimum:,} to 10,000.")
    return value


def balance(connection, household, member):
    return row(connection, """SELECT COALESCE(SUM(amount),0) AS total FROM points_ledger
        WHERE household_id=:h AND member_id=:member""", h=household, member=member)["total"]


def entry(connection, household, member, item, amount, reason):
    if amount:
        statement(connection, """INSERT INTO points_ledger(id,household_id,member_id,item_id,amount,reason)
            VALUES(:id,:h,:member,:item,:amount,:reason)""", id=str(uuid.uuid4()), h=household,
                  member=member, item=item, amount=amount, reason=reason)


def reviewed_status(data):
    approved = data.get("approved")
    if type(approved) is not bool:
        raise DomainError(422, "Choose approve or decline.")
    return "approved" if approved else "declined"
