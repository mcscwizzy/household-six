"""Reward store and point-backed redemption approvals."""
import uuid

from app.ledger import ADULT_ROLES, balance, entry, point_value, reviewed_status
from app.mutations import DomainError, Mutation, clean, expected_version, row, statement

STORE_SQL = """SELECT id,title,details,version,value AS points FROM items
               WHERE household_id=:h AND kind='reward' AND deleted_at IS NULL"""
REQUEST_SQL = """SELECT r.id,r.reward_id,r.member_id,r.title,r.cost,r.status,r.version,r.requested_at,
    r.reviewed_at,u.display_name AS member_name FROM reward_redemptions r
    JOIN users u ON u.id=r.member_id AND u.household_id=r.household_id WHERE r.household_id=:h"""


def load(database, user):
    household, actor = user["household_id"], user["id"]
    with database.connect() as connection:
        rewards = statement(connection, STORE_SQL + " ORDER BY title,id", h=household).mappings()
        filter_clause = "" if user["role"] in ADULT_ROLES else " AND r.member_id=:actor"
        requests = statement(connection, REQUEST_SQL + filter_clause +
                             " ORDER BY r.status<>'pending',r.requested_at DESC,r.id LIMIT 200",
                             h=household, actor=actor).mappings()
        return {"rewards": [dict(reward) for reward in rewards if reward["points"] > 0],
                "legacy": [dict(reward) for reward in statement(connection, STORE_SQL + " AND value=0", h=household).mappings()],
                "requests": [dict(request) for request in requests], "balance": balance(connection, household, actor)}


def reward(connection, household, entity):
    current = row(connection, STORE_SQL + " AND id=:id", h=household, id=entity)
    if not current:
        raise DomainError(404, "This reward was not found.")
    return current


def reward_change(connection, user, operation, target, data):
    household, actor = user["household_id"], user["id"]
    entity = target or str(uuid.uuid4())
    params = {"id": entity, "h": household, "actor": actor}
    version = 1
    if target:
        current = reward(connection, household, target)
        if current["version"] != expected_version(data):
            raise DomainError(409, "This reward changed. Refresh and try again.")
        version = current["version"] + 1
    if operation == "reward.archive":
        statement(connection, "UPDATE items SET deleted_at=CURRENT_TIMESTAMP,version=:v WHERE id=:id AND household_id=:h",
                  **params, v=version)
    else:
        fields = {"title": clean(data.get("title"), 120, required=True),
                  "details": clean(data.get("details", ""), 1000), "points": point_value(data, minimum=1)}
        if target:
            statement(connection, """UPDATE items SET title=:title,details=:details,value=:points,version=:v,
                updated_at=CURRENT_TIMESTAMP WHERE id=:id AND household_id=:h""", **params, **fields, v=version)
        else:
            statement(connection, """INSERT INTO items(id,household_id,kind,title,details,value,created_by)
                VALUES(:id,:h,'reward',:title,:details,:points,:actor)""", **params, **fields)
    return entity, version


def request_redemption(connection, user, target, data):
    household, actor = user["household_id"], user["id"]
    current = reward(connection, household, target)
    cost = current["points"]
    if cost < 1 or expected_version(data) != current["version"]:
        raise DomainError(409, "This reward changed. Refresh and try again.")
    if row(connection, REQUEST_SQL + " AND r.reward_id=:reward AND r.member_id=:actor AND r.status='pending'",
           h=household, reward=target, actor=actor):
        raise DomainError(409, "This reward is already awaiting review.")
    if balance(connection, household, actor) < cost:
        raise DomainError(409, "You need more points for this reward.")
    entity = str(uuid.uuid4())
    statement(connection, """INSERT INTO reward_redemptions(id,household_id,reward_id,member_id,title,cost)
        VALUES(:id,:h,:reward,:actor,:title,:cost)""", id=entity, h=household, reward=target, actor=actor,
              title=current["title"], cost=cost)
    return entity, 1


def review(connection, user, target, data):
    household = user["household_id"]
    current = row(connection, REQUEST_SQL + " AND r.id=:id", h=household, id=target)
    if not current:
        raise DomainError(404, "This redemption request was not found.")
    if expected_version(data) != current["version"] or current["status"] != "pending":
        raise DomainError(409, "This redemption request has already changed.")
    state = reviewed_status(data)
    if state == "approved":
        member, cost = current["member_id"], current["cost"]
        if balance(connection, household, member) < cost:
            raise DomainError(409, "This member does not have enough points.")
        entry(connection, household, member, current["reward_id"], -cost, f"reward.redeem:{target}")
    version = current["version"] + 1
    statement(connection, """UPDATE reward_redemptions SET status=:status,version=:v,reviewed_at=CURRENT_TIMESTAMP
        WHERE id=:id AND household_id=:h""", status=state, v=version, id=target, h=household)
    return target, version


def write(database, user, operation, target, data):
    if operation != "reward.request" and user["role"] not in ADULT_ROLES:
        raise DomainError(403, "Only an adult can manage and review rewards.")
    household = user["household_id"]
    transitions = {"reward.request": request_redemption, "reward.review": review}
    with database.connect() as connection:
        connection.exec_driver_sql("BEGIN IMMEDIATE")
        mutation = Mutation(connection, user, operation, data, target)
        entity = mutation.replay_id
        if not entity:
            entity, version = (transitions[operation](connection, user, target, data) if operation in transitions
                               else reward_change(connection, user, operation, target, data))
            mutation.finish(entity, version)
            connection.commit()
        changed = None if mutation.replay_id else entity
        if operation == "reward.archive":
            return 204, None, changed
        if operation in transitions:
            current = row(connection, REQUEST_SQL + " AND r.id=:id", h=household, id=entity)
        else:
            current = reward(connection, household, entity)
        return 201 if operation in {"reward.create", "reward.request"} else 200, dict(current), changed
