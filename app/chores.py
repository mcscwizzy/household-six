"""Schedule chores and review individual completion occurrences."""
from datetime import date, datetime
import uuid
from zoneinfo import ZoneInfo

from app.calendar_service import parse_date
from app.ledger import ADULT_ROLES, entry, point_value, reviewed_status
from app.mutations import DomainError, Mutation, clean, expected_version, row, statement

HISTORY = """SELECT c.id,c.chore_id,c.due_date,c.beneficiary,c.status,c.version,c.submitted_at,c.reviewed_at,
    i.title,i.details,i.assigned_to,i.value AS points,u.display_name AS member_name
    FROM chore_completions c JOIN items i ON i.id=c.id AND i.household_id=c.household_id
    JOIN users u ON u.id=c.beneficiary AND u.household_id=c.household_id
    WHERE c.household_id=:h"""


def occurrence_id(chore_id, day, member):
    return str(uuid.uuid5(uuid.NAMESPACE_URL, f"household-six:chore:{chore_id}:{day}:{member or ''}"))


def scheduled(chore, day):
    elapsed = (day - date.fromisoformat(chore["start_date"])).days
    return elapsed >= 0 and (chore["repeat"] == "daily" or elapsed == 0 or
                             (chore["repeat"] == "weekly" and elapsed % 7 == 0))


def get_assignments(connection, household):
    assignments = {}
    for record in statement(connection, """SELECT a.chore_id,a.member_id,u.display_name
        FROM chore_assignments a JOIN users u ON a.member_id=u.id AND a.household_id=u.household_id
        WHERE a.household_id=:h ORDER BY u.display_name,a.member_id""", h=household).mappings():
        assignments.setdefault(record["chore_id"], []).append(dict(record))
    return assignments


def load(database, user, day_value=None):
    day = parse_date(day_value) if day_value else datetime.now(ZoneInfo(user["timezone"])).date()
    return load_dates(database, user, [day], include_history=True)


def load_dates(database, user, days, *, include_history=False):
    household, actor = user["household_id"], user["id"]
    child = user["role"] == "child"
    with database.connect() as connection:
        assignments = get_assignments(connection, household)
        templates = [dict(record, assignees=assignments.get(record["id"], []))
                     for record in statement(connection, """SELECT * FROM chores
                       WHERE household_id=:h AND archived_at IS NULL ORDER BY routine,title,id""", h=household).mappings()]
        history_filter = " AND c.beneficiary=:actor" if child else ""
        minimum, maximum = min(days).isoformat(), max(days).isoformat()
        completions = statement(connection, HISTORY + " AND c.due_date BETWEEN :min AND :max",
                                h=household, min=minimum, max=maximum).mappings()
        status = {record["id"]: (record["status"], record["version"]) for record in completions}
        board = []
        for day in days:
            due = day.isoformat()
            for template in templates:
                if not scheduled(template, day):
                    continue
                for assignee in template["assignees"] or [{"member_id": None, "display_name": None}]:
                    member = assignee["member_id"]
                    if child and member and member != actor:
                        continue
                    item_id = occurrence_id(template["id"], due, member)
                    state, version = status.get(item_id, ("open", template["version"]))
                    board.append({
                        "id": item_id, "choreId": template["id"], "title": template["title"],
                        "details": template["details"], "date": due, "routine": template["routine"],
                        "assignedTo": member, "memberName": assignee["display_name"], "points": template["points"],
                        "status": state, "version": version, "scheduleVersion": template["version"], "approvalRequired": bool(template["requires_approval"]),
                    })
        result = {"date": maximum, "scheduled": board}
        if include_history:
            if user["role"] == "display":
                history = []
            else:
                history = statement(connection, HISTORY + history_filter +
                                    " ORDER BY c.status<>'pending',c.submitted_at DESC,c.id LIMIT 150",
                                    h=household, actor=actor).mappings()
            result["history"] = [dict(record) for record in history]
            if user["role"] in ADULT_ROLES:
                result["templates"] = templates
        return result


def save_template(connection, user, operation, target, data):
    household = user["household_id"]
    version = 1
    entity = target or str(uuid.uuid4())
    if target:
        current = row(connection, "SELECT version FROM chores WHERE id=:id AND household_id=:h AND archived_at IS NULL",
                      id=target, h=household)
        if not current:
            raise DomainError(404, "That chore schedule was not found.")
        if current["version"] != expected_version(data):
            raise DomainError(409, "This chore has changed. Refresh and try again.")
        version = current["version"] + 1
    if operation == "chore.archive":
        statement(connection, "UPDATE chores SET archived_at=CURRENT_TIMESTAMP,version=:v WHERE id=:id AND household_id=:h",
                  v=version, id=entity, h=household)
        return entity, version

    repeat, routine = data.get("repeat", "once"), data.get("routine", "anytime")
    approval = data.get("approvalRequired", False)
    if repeat not in ("once", "daily", "weekly") or routine not in ("anytime", "morning", "bedtime") or type(approval) is not bool:
        raise DomainError(422, "Choose an available routine and repeat schedule.")
    assignees = data.get("assignees", [])
    if not isinstance(assignees, list) or len(assignees) > 30 or not all(isinstance(value, str) for value in assignees):
        raise DomainError(422, "Choose available household members.")
    assignees = list(dict.fromkeys(assignees))
    for member in assignees:
        if not row(connection, """SELECT 1 FROM users WHERE household_id=:h AND id=:member
                       AND disabled_at IS NULL AND role<>'display'""", h=household, member=member):
            raise DomainError(422, "Choose available household members.")
    params = {
        "id": entity, "h": household, "actor": user["id"], "title": clean(data.get("title"), 120, required=True),
        "details": clean(data.get("details", ""), 1000), "start": parse_date(data.get("start")).isoformat(),
        "repeat": repeat, "routine": routine, "points": point_value(data), "approval": int(approval), "v": version,
    }
    if target:
        statement(connection, """UPDATE chores SET title=:title,details=:details,start_date=:start,
            repeat=:repeat,routine=:routine,points=:points,requires_approval=:approval,version=:v
            WHERE id=:id AND household_id=:h""", **params)
        statement(connection, "DELETE FROM chore_assignments WHERE chore_id=:id AND household_id=:h", **params)
    else:
        statement(connection, """INSERT INTO chores
            (id,household_id,title,details,start_date,repeat,routine,points,requires_approval,created_by)
            VALUES(:id,:h,:title,:details,:start,:repeat,:routine,:points,:approval,:actor)""", **params)
    for member in assignees:
        statement(connection, "INSERT INTO chore_assignments(chore_id,member_id,household_id) VALUES(:id,:member,:h)",
                  **params, member=member)
    return entity, version


def complete(connection, user, target, data):
    household, actor = user["household_id"], user["id"]
    day = parse_date(data.get("date"))
    if day > datetime.now(ZoneInfo(user["timezone"])).date():
        raise DomainError(422, "This chore is scheduled for a later day.")
    chore = row(connection, "SELECT * FROM chores WHERE household_id=:h AND id=:id AND archived_at IS NULL",
                h=household, id=target)
    if not chore or not scheduled(chore, day):
        raise DomainError(404, "This chore occurrence was not found.")
    selected = clean(data.get("assignedTo") or "", 64) or None
    assigned = [record["member_id"] for record in statement(connection,
        "SELECT member_id FROM chore_assignments WHERE household_id=:h AND chore_id=:target",
        h=household, target=target).mappings()]
    if selected not in (assigned or [None]) or (user["role"] == "child" and selected not in (None, actor)):
        raise DomainError(403, "This chore is assigned to a different member.")

    item_id = occurrence_id(target, day.isoformat(), selected)
    prior = row(connection, HISTORY + " AND c.id=:id", h=household, id=item_id)
    current_version = prior["version"] if prior else chore["version"]
    if expected_version(data) != current_version or prior and prior["status"] != "declined":
        raise DomainError(409, "This chore changed or has already been checked off.")
    state = "pending" if chore["requires_approval"] else "approved"
    if prior and data.get("expectedScheduleVersion") != chore["version"]:
        raise DomainError(409, "This chore schedule changed. Refresh and try again.")
    version = current_version + 1
    params = {"id": item_id, "h": household, "actor": actor, "beneficiary": selected or actor,
              "target": target, "title": chore["title"], "details": chore["details"], "day": day.isoformat(),
              "assigned": selected, "points": chore["points"], "state": state, "v": version, "done": int(state == "approved")}
    if prior:
        statement(connection, """UPDATE chore_completions SET beneficiary=:beneficiary,checked_by=:actor,
            status=:state,version=:v,submitted_at=CURRENT_TIMESTAMP,reviewed_at=NULL WHERE id=:id AND household_id=:h""",
                  **params)
        statement(connection, """UPDATE items SET title=:title,details=:details,value=:points,completed=:done,
            version=version+1,updated_at=CURRENT_TIMESTAMP WHERE id=:id AND household_id=:h""", **params)
    else:
        statement(connection, """INSERT INTO items
            (id,household_id,kind,title,details,due_at,assigned_to,value,completed,created_by)
            VALUES(:id,:h,'task',:title,:details,:day,:assigned,:points,:done,:actor)""", **params)
        statement(connection, """INSERT INTO chore_completions
            (id,chore_id,household_id,due_date,beneficiary,checked_by,status,version)
            VALUES(:id,:target,:h,:day,:beneficiary,:actor,:state,:v)""", **params)
    if state == "approved":
        entry(connection, household, selected or actor, item_id, chore["points"], "chore.complete")
    return item_id, version


def review(connection, user, target, data):
    household = user["household_id"]
    current = row(connection, HISTORY + " AND c.id=:id", h=household, id=target)
    if not current:
        raise DomainError(404, "This chore completion was not found.")
    if current["status"] != "pending" or expected_version(data) != current["version"]:
        raise DomainError(409, "This chore completion has already changed.")
    status = reviewed_status(data)
    version = current["version"] + 1
    statement(connection, """UPDATE chore_completions SET status=:state,version=:v,reviewed_at=CURRENT_TIMESTAMP
        WHERE id=:id AND household_id=:h""", state=status, v=version, id=target, h=household)
    if status == "approved":
        statement(connection, "UPDATE items SET completed=1,version=version+1 WHERE id=:id AND household_id=:h",
                  id=target, h=household)
        entry(connection, household, current["beneficiary"], target, current["points"], "chore.complete")
    return target, version


def write(database, user, operation, target, data):
    if operation != "chore.complete" and user["role"] not in ADULT_ROLES:
        raise DomainError(403, "Only an adult can manage and review chores.")
    states = {"chore.complete": complete, "chore.review": review}
    household = user["household_id"]
    with database.connect() as connection:
        connection.exec_driver_sql("BEGIN IMMEDIATE")
        mutation = Mutation(connection, user, operation, data, target)
        entity = mutation.replay_id
        if not entity:
            entity, version = (states[operation](connection, user, target, data) if operation in states
                               else save_template(connection, user, operation, target, data))
            mutation.finish(entity, version)
            connection.commit()
        if operation == "chore.archive":
            return 204, None, None if mutation.replay_id else entity
        if operation in states:
            result = row(connection, HISTORY + " AND c.id=:id", h=household, id=entity)
        else:
            result = row(connection, "SELECT * FROM chores WHERE household_id=:h AND id=:id", h=household, id=entity)
        return 201 if operation == "chore.create" else 200, dict(result), None if mutation.replay_id else entity
