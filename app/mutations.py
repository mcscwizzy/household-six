"""Common validation, audit, and replay protection for household transactions."""
import hashlib
import json
import uuid

from sqlalchemy import text


class DomainError(ValueError):
    def __init__(self, status, message):
        super().__init__(message)
        self.status = status
        self.public_message = message


def statement(connection, sql, **values):
    return connection.execute(text(sql), values)


def row(connection, sql, **values):
    return statement(connection, sql, **values).mappings().first()


def clean(value, limit, *, required=False):
    if not isinstance(value, str):
        raise DomainError(422, "Check the text fields and try again.")
    result = " ".join(value.replace("\x00", "").split())
    if len(result) > limit or required and not result:
        raise DomainError(422, "Check the required fields and text lengths.")
    return result


def expected_version(data):
    version = data.get("expectedVersion")
    if type(version) is not int or not 1 <= version < 2**63:
        raise DomainError(422, "Refresh this record and try again.")
    return version


class Mutation:
    """Use within a connection holding BEGIN IMMEDIATE."""
    def __init__(self, connection, user, operation, data, target):
        mutation_id = data.get("mutationId")
        try:
            valid_id = isinstance(mutation_id, str) and len(mutation_id) == 36 and str(uuid.UUID(mutation_id)) == mutation_id
        except ValueError:
            valid_id = False
        if not valid_id:
            raise DomainError(422, "This change needs a valid mutation ID.")
        self.connection = connection
        encoded = json.dumps([target, {k: v for k, v in data.items() if k != "csrf"}],
                             sort_keys=True, separators=(",", ":")).encode()
        self.values = {
            "household": user["household_id"], "actor": user["id"], "operation": operation,
            "mutation": mutation_id, "fingerprint": hashlib.sha256(encoded).hexdigest(),
        }
        receipt = row(connection, """SELECT actor_id,operation,entity_id,request_hash
            FROM mutation_receipts WHERE household_id=:household AND mutation_id=:mutation""", **self.values)
        if receipt and (
            receipt["actor_id"] != user["id"] or receipt["operation"] != operation
            or receipt["request_hash"] != self.values["fingerprint"]
        ):
            raise DomainError(409, "This request conflicts with a previous change.")
        self.replay_id = receipt["entity_id"] if receipt else None

    def finish(self, entity_id, version):
        params = {**self.values, "entity": entity_id, "version": version, "audit": str(uuid.uuid4())}
        statement(self.connection, """INSERT INTO mutation_receipts
            (household_id,mutation_id,actor_id,operation,entity_id,result_version,request_hash)
            VALUES(:household,:mutation,:actor,:operation,:entity,:version,:fingerprint)""", **params)
        statement(self.connection, """INSERT INTO audit_log(id,household_id,actor_id,action,object_id)
            VALUES(:audit,:household,:actor,:operation,:entity)""", **params)
