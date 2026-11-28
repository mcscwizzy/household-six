"""Household-scoped home maintenance and vehicle service records."""
from calendar import monthrange
from datetime import date, timedelta
import re
import uuid

from app.calendar_service import parse_date
from app.ledger import ADULT_ROLES
from app.mutations import DomainError, Mutation, clean, expected_version, row, statement

FREQUENCIES = {"once", "daily", "weekly", "monthly", "quarterly", "yearly"}
SEASONS = {"", "spring", "summer", "fall", "winter"}
FUELS = {"gasoline", "diesel", "hybrid", "electric"}
VIN = re.compile(r"^[A-HJ-NPR-Z0-9]{17}$", re.I)
TEMPLATES = (
    {"title": "HVAC filter", "category": "hvac", "frequency": "quarterly", "season": ""},
    {"title": "Smoke detector", "category": "safety", "frequency": "monthly", "season": ""},
    {"title": "Lawn maintenance", "category": "lawn", "frequency": "weekly", "season": "summer"},
    {"title": "Gutters", "category": "gutters", "frequency": "yearly", "season": "fall"},
    {"title": "Water filter", "category": "water", "frequency": "quarterly", "season": ""},
    {"title": "Generator", "category": "generator", "frequency": "yearly", "season": "fall"},
    {"title": "Septic system", "category": "septic", "frequency": "yearly", "season": "summer"},
)


def maintenance_templates():
    """Return suggestions only; templates never create active database records."""
    return [dict(template) for template in TEMPLATES]


def _money(value):
    if type(value) is not int or value < 0 or value > 1_000_000_000:
        raise DomainError(422, "Enter a nonnegative cost in cents.")
    return value


def _integer(value, name, low=0, high=2_000_000, *, allow_none=False):
    if allow_none and value is None:
        return None
    if type(value) is not int or not low <= value <= high:
        raise DomainError(422, f"Check the {name} value and try again.")
    return value


def _date(value, label):
    if not isinstance(value, str):
        raise DomainError(422, f"Enter a valid {label} date.")
    try:
        return parse_date(value).isoformat()
    except (ValueError, TypeError):
        raise DomainError(422, f"Enter a valid {label} date.") from None


def _next_date(value, frequency, count):
    current = date.fromisoformat(value)
    if frequency == "once":
        return None
    if frequency == "daily":
        next_day = current + timedelta(days=count)
    elif frequency == "weekly":
        next_day = current + timedelta(days=7 * count)
    else:
        months = count * {"monthly": 1, "quarterly": 3, "yearly": 12}[frequency]
        month_index = current.year * 12 + current.month - 1 + months
        year, month = divmod(month_index, 12)
        month += 1
        next_day = current.replace(year=year, month=month, day=min(current.day, monthrange(year, month)[1]))
    return next_day.isoformat()


def _validate_member(connection, household, member_id):
    if member_id in (None, ""):
        return None
    if not isinstance(member_id, str) or not row(connection,
            "SELECT id FROM users WHERE id=:id AND household_id=:h AND disabled_at IS NULL", id=member_id, h=household):
        raise DomainError(422, "Choose an active household member.")
    return member_id


def _maintenance_rows(connection, household):
    return statement(connection, """SELECT s.id,s.asset_id,s.title,s.frequency,s.interval_count,s.due_on,
        s.season,s.assigned_to,u.display_name assigned_name,s.estimated_cost_cents,s.version,
        a.title asset_title,a.category,a.location,a.instructions,a.notes,
        (SELECT COUNT(*) FROM maintenance_history mh WHERE mh.schedule_id=s.id AND mh.household_id=s.household_id) history_count,
        (SELECT COALESCE(SUM(cost_cents),0) FROM maintenance_history mh WHERE mh.schedule_id=s.id AND mh.household_id=s.household_id) total_cost_cents
        FROM maintenance_schedules s JOIN maintenance_assets a ON a.id=s.asset_id AND a.household_id=s.household_id
        LEFT JOIN users u ON u.id=s.assigned_to AND u.household_id=s.household_id
        WHERE s.household_id=:h AND s.active=1 AND a.archived_at IS NULL
        ORDER BY s.due_on,s.title,s.id""", h=household).mappings()


def _maintenance_payload(record):
    value = dict(record)
    for key in ("estimated_cost_cents", "total_cost_cents"):
        value["estimatedCostCents" if key == "estimated_cost_cents" else "totalCostCents"] = value.pop(key)
    for key, target in (("due_on", "dueOn"), ("asset_id", "assetId"), ("asset_title", "assetTitle"),
                        ("interval_count", "intervalCount"), ("assigned_to", "assignedTo"),
                        ("assigned_name", "assignedName"), ("history_count", "historyCount")):
        value[target] = value.pop(key)
    return value


def _vehicle_payload(record):
    value = dict(record)
    for key, target in (("registration_due", "registrationDue"), ("odometer", "odometer")):
        value[target] = value.pop(key)
    return value


def load(database, user):
    household = user["household_id"]
    with database.connect() as connection:
        schedules = [_maintenance_payload(r) for r in _maintenance_rows(connection, household)]
        history = statement(connection, """SELECT h.id,h.schedule_id scheduleId,h.asset_id assetId,a.title assetTitle,
            h.performed_on performedOn,h.cost_cents costCents,h.notes,h.performed_by performedBy,u.display_name performedByName
            FROM maintenance_history h JOIN maintenance_assets a ON a.id=h.asset_id AND a.household_id=h.household_id
            JOIN users u ON u.id=h.performed_by AND u.household_id=h.household_id
            WHERE h.household_id=:h ORDER BY h.performed_on DESC,h.created_at DESC LIMIT 100""", h=household).mappings()
        vehicles = statement(connection, """SELECT id,make,model,year,vin,fuel,nickname,odometer,registration_due,notes,version
            FROM vehicles WHERE household_id=:h AND archived_at IS NULL ORDER BY make,model,year DESC,id""", h=household).mappings()
        service_rows = statement(connection, """SELECT id,vehicle_id vehicleId,service_type serviceType,performed_on performedOn,
            odometer,due_on dueOn,due_odometer dueOdometer,interval_months intervalMonths,interval_miles intervalMiles,
            cost_cents costCents,notes FROM vehicle_services WHERE household_id=:h
            ORDER BY performed_on DESC,created_at DESC LIMIT 250""", h=household).mappings()
        return {"schedules": schedules, "history": [dict(r) for r in history],
                "vehicles": [_vehicle_payload(r) for r in vehicles], "services": [dict(r) for r in service_rows],
                "templates": maintenance_templates()}


def _asset(connection, household, asset_id):
    asset = row(connection, "SELECT * FROM maintenance_assets WHERE id=:id AND household_id=:h AND archived_at IS NULL",
                 id=asset_id, h=household)
    if not asset:
        raise DomainError(404, "This maintenance record was not found.")
    return asset


def _schedule(connection, household, schedule_id):
    record = row(connection, "SELECT * FROM maintenance_schedules WHERE id=:id AND household_id=:h AND active=1",
                  id=schedule_id, h=household)
    if not record:
        raise DomainError(404, "This maintenance record was not found.")
    return record


def _vehicle(connection, household, vehicle_id):
    record = row(connection, "SELECT * FROM vehicles WHERE id=:id AND household_id=:h AND archived_at IS NULL",
                 id=vehicle_id, h=household)
    if not record:
        raise DomainError(404, "This vehicle was not found.")
    return record


def _maintenance_save(connection, user, operation, target, data):
    household, actor = user["household_id"], user["id"]
    if operation == "maintenance.complete":
        current = _schedule(connection, household, target)
        if current["version"] != expected_version(data):
            raise DomainError(409, "This maintenance schedule changed. Refresh and try again.")
        performed = _date(data.get("performedOn"), "completion")
        cost = _money(data.get("costCents", 0))
        notes = clean(data.get("notes", ""), 2000)
        next_due = _next_date(performed, current["frequency"], current["interval_count"])
        statement(connection, """INSERT INTO maintenance_history(id,mutation_id,household_id,schedule_id,asset_id,performed_by,
            performed_on,cost_cents,notes) VALUES(:id,:mutation,:h,:schedule,:asset,:actor,:day,:cost,:notes)""",
            id=str(uuid.uuid4()), mutation=data["mutationId"], h=household, schedule=target, asset=current["asset_id"], actor=actor,
            day=performed, cost=cost, notes=notes)
        if next_due:
            statement(connection, """UPDATE maintenance_schedules SET due_on=:due,version=version+1
                WHERE id=:id AND household_id=:h AND version=:version""", due=next_due, id=target, h=household,
                version=current["version"])
        else:
            statement(connection, """UPDATE maintenance_schedules SET active=0,version=version+1
                WHERE id=:id AND household_id=:h AND version=:version""", id=target, h=household, version=current["version"])
        return target, current["version"] + 1

    asset_id = None
    current = _schedule(connection, household, target) if target else None
    if current and current["version"] != expected_version(data):
        raise DomainError(409, "This maintenance schedule changed. Refresh and try again.")
    title = clean(data.get("title"), 120, required=True)
    category = clean(data.get("category"), 40, required=True).lower()
    if not re.fullmatch(r"[a-z][a-z0-9_-]{0,39}", category):
        raise DomainError(422, "Choose a valid maintenance category.")
    asset_title = clean(data.get("assetTitle", title), 120, required=True)
    location = clean(data.get("location", ""), 120)
    instructions = clean(data.get("instructions", ""), 3000)
    asset_notes = clean(data.get("assetNotes", ""), 2000)
    frequency = data.get("frequency", "once")
    if frequency not in FREQUENCIES:
        raise DomainError(422, "Choose a supported maintenance frequency.")
    interval = _integer(data.get("intervalCount", 1), "interval", 1, 120)
    due_on = _date(data.get("dueOn"), "maintenance")
    season = data.get("season", "")
    if season not in SEASONS:
        raise DomainError(422, "Choose a supported season.")
    assigned_to = _validate_member(connection, household, data.get("assignedTo"))
    estimated = _money(data.get("estimatedCostCents", 0))
    if current:
        asset_id = current["asset_id"]
        statement(connection, """UPDATE maintenance_assets SET title=:title,category=:category,location=:location,
            instructions=:instructions,notes=:notes WHERE id=:id AND household_id=:h""", title=asset_title,
            category=category, location=location, instructions=instructions, notes=asset_notes, id=asset_id, h=household)
        statement(connection, """UPDATE maintenance_schedules SET title=:title,frequency=:frequency,interval_count=:interval,
            due_on=:due,season=:season,assigned_to=:assigned,estimated_cost_cents=:cost,version=version+1
            WHERE id=:id AND household_id=:h AND version=:version""", title=title, frequency=frequency, interval=interval,
            due=due_on, season=season, assigned=assigned_to, cost=estimated, id=target, h=household, version=current["version"])
        return target, current["version"] + 1
    asset_id, schedule_id = str(uuid.uuid4()), str(uuid.uuid4())
    statement(connection, """INSERT INTO maintenance_assets(id,household_id,title,category,location,instructions,notes,created_by)
        VALUES(:id,:h,:title,:category,:location,:instructions,:notes,:actor)""", id=asset_id, h=household,
        title=asset_title, category=category, location=location, instructions=instructions, notes=asset_notes, actor=actor)
    statement(connection, """INSERT INTO maintenance_schedules(id,household_id,asset_id,title,frequency,interval_count,due_on,
        season,assigned_to,estimated_cost_cents) VALUES(:id,:h,:asset,:title,:frequency,:interval,:due,:season,:assigned,:cost)""",
        id=schedule_id, h=household, asset=asset_id, title=title, frequency=frequency, interval=interval,
        due=due_on, season=season, assigned=assigned_to, cost=estimated)
    return schedule_id, 1


def _vehicle_save(connection, user, operation, target, data):
    household = user["household_id"]
    if operation == "vehicle.service.create":
        vehicle_id = data.get("vehicleId")
        current = _vehicle(connection, household, vehicle_id)
        service_type = clean(data.get("serviceType"), 120, required=True)
        performed = _date(data.get("performedOn"), "service")
        odometer = _integer(data.get("odometer"), "odometer")
        if odometer < current["odometer"]:
            raise DomainError(422, "The service odometer cannot be lower than the vehicle history.")
        due_on = _date(data["dueOn"], "next service") if data.get("dueOn") else None
        due_odometer = _integer(data.get("dueOdometer"), "next odometer", allow_none=True)
        interval_months = _integer(data.get("intervalMonths"), "month interval", 1, 120, allow_none=True)
        interval_miles = _integer(data.get("intervalMiles"), "mileage interval", 1, 500000, allow_none=True)
        if due_on is None and due_odometer is None and (interval_months or interval_miles):
            if interval_months:
                due_on = _next_date(performed, "monthly", interval_months)
            if interval_miles:
                due_odometer = odometer + interval_miles
        cost = _money(data.get("costCents", 0))
        notes = clean(data.get("notes", ""), 2000)
        service_id = str(uuid.uuid4())
        statement(connection, """INSERT INTO vehicle_services(id,household_id,vehicle_id,service_type,performed_on,
            odometer,due_on,due_odometer,interval_months,interval_miles,cost_cents,notes)
            VALUES(:id,:h,:vehicle,:type,:performed,:odometer,:due,:due_odometer,:months,:miles,:cost,:notes)""",
            id=service_id, h=household, vehicle=vehicle_id, type=service_type, performed=performed, odometer=odometer,
            due=due_on, due_odometer=due_odometer, months=interval_months, miles=interval_miles, cost=cost, notes=notes)
        statement(connection, """UPDATE vehicles SET odometer=:odometer,version=version+1
            WHERE id=:id AND household_id=:h AND odometer<=:odometer""", odometer=odometer, id=vehicle_id, h=household)
        return service_id, 1
    current = _vehicle(connection, household, target) if target else None
    if current and current["version"] != expected_version(data):
        raise DomainError(409, "This vehicle profile changed. Refresh and try again.")
    make, model = clean(data.get("make"), 80, required=True), clean(data.get("model"), 100, required=True)
    year = _integer(data.get("year"), "model year", 1886, date.today().year + 2)
    fuel = data.get("fuel")
    if fuel not in FUELS:
        raise DomainError(422, "Choose gasoline, diesel, hybrid, or electric.")
    vin = clean(data.get("vin", ""), 17).upper()
    if vin and not VIN.fullmatch(vin):
        raise DomainError(422, "Enter a valid 17-character VIN or leave it blank.")
    nickname = clean(data.get("nickname", ""), 80)
    odometer = _integer(data.get("odometer", current["odometer"] if current else 0), "odometer")
    if current and odometer < current["odometer"]:
        raise DomainError(422, "The odometer cannot go backward.")
    registration = _date(data["registrationDue"], "registration") if data.get("registrationDue") else None
    notes = clean(data.get("notes", ""), 2000)
    if current:
        statement(connection, """UPDATE vehicles SET make=:make,model=:model,year=:year,vin=:vin,fuel=:fuel,nickname=:nickname,
            odometer=:odometer,registration_due=:registration,notes=:notes,version=version+1
            WHERE id=:id AND household_id=:h AND version=:version""", make=make, model=model, year=year, vin=vin,
            fuel=fuel, nickname=nickname, odometer=odometer, registration=registration, notes=notes,
            id=target, h=household, version=current["version"])
        return target, current["version"] + 1
    entity = str(uuid.uuid4())
    statement(connection, """INSERT INTO vehicles(id,household_id,make,model,year,vin,fuel,nickname,odometer,registration_due,notes)
        VALUES(:id,:h,:make,:model,:year,:vin,:fuel,:nickname,:odometer,:registration,:notes)""", id=entity, h=household,
        make=make, model=model, year=year, vin=vin, fuel=fuel, nickname=nickname, odometer=odometer,
        registration=registration, notes=notes)
    return entity, 1


def write(database, user, operation, target, data):
    if user["role"] not in ADULT_ROLES:
        raise DomainError(403, "Only a household adult can change maintenance or vehicle records.")
    with database.connect() as connection:
        connection.exec_driver_sql("BEGIN IMMEDIATE")
        mutation = Mutation(connection, user, operation, data, target)
        entity = mutation.replay_id
        if not entity:
            if operation.startswith("maintenance."):
                if operation == "maintenance.archive":
                    current = _schedule(connection, user["household_id"], target)
                    if current["version"] != expected_version(data):
                        raise DomainError(409, "This maintenance schedule changed. Refresh and try again.")
                    statement(connection, "UPDATE maintenance_schedules SET active=0,version=version+1 WHERE id=:id AND household_id=:h",
                              id=target, h=user["household_id"])
                    entity, version = target, current["version"] + 1
                else:
                    entity, version = _maintenance_save(connection, user, operation, target, data)
            else:
                if operation == "vehicle.archive":
                    current = _vehicle(connection, user["household_id"], target)
                    if current["version"] != expected_version(data):
                        raise DomainError(409, "This vehicle profile changed. Refresh and try again.")
                    statement(connection, "UPDATE vehicles SET archived_at=CURRENT_TIMESTAMP,version=version+1 WHERE id=:id AND household_id=:h",
                              id=target, h=user["household_id"])
                    entity, version = target, current["version"] + 1
                else:
                    entity, version = _vehicle_save(connection, user, operation, target, data)
            mutation.finish(entity, version)
            connection.commit()
        if operation == "maintenance.archive" or operation == "vehicle.archive":
            return 204, None, None if mutation.replay_id else entity
        loaded = load(database, user)
        result = next((record for record in loaded["schedules"] if record["id"] == entity), None)
        if operation == "maintenance.complete" and result is None:
            # A one-time schedule is archived at completion; return the persisted completion on retries.
            with database.connect() as connection:
                result = row(connection, """SELECT h.schedule_id id,s.title,h.performed_on performedOn,
                    h.cost_cents costCents,h.notes,h.performed_by performedBy
                    FROM maintenance_history h JOIN maintenance_schedules s ON s.id=h.schedule_id AND s.household_id=h.household_id
                    WHERE h.household_id=:h AND h.mutation_id=:mutation""", h=user["household_id"], mutation=data["mutationId"])
                receipt = row(connection, """SELECT result_version FROM mutation_receipts
                    WHERE household_id=:h AND mutation_id=:mutation""", h=user["household_id"], mutation=data["mutationId"])
            if result:
                result = {**dict(result), "version": receipt["result_version"], "dueOn": None, "active": False}
        if operation.startswith("vehicle.") and operation != "vehicle.service.create":
            result = next((record for record in loaded["vehicles"] if record["id"] == entity), None)
        elif operation == "vehicle.service.create":
            result = next((record for record in loaded["services"] if record["id"] == entity), None)
        if not result:
            raise DomainError(404, "This household record was not found.")
        return (201 if operation.endswith(".create") else 200), result, None if mutation.replay_id else entity
