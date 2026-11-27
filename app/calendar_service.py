"""Household-local calendar records, recurrence, and iCalendar exchange."""
from datetime import date, datetime, time, timedelta, timezone
import json
import uuid
from zoneinfo import ZoneInfo

from dateutil.rrule import rrulestr
from icalendar import Calendar, Event, Timezone

from app.mutations import DomainError, Mutation, clean, expected_version, row, statement

ONE_DAY = timedelta(days=1)
REPEAT = {"daily": "DAILY", "weekly": "WEEKLY", "monthly": "MONTHLY", "yearly": "YEARLY"}
RULE_FIELDS = {"FREQ", "INTERVAL", "UNTIL", "COUNT", "BYDAY", "BYMONTHDAY", "BYMONTH", "BYSETPOS", "WKST"}
EVENTS_SQL = """SELECT i.id,i.title,i.details,i.version,i.assigned_to,i.due_at,u.display_name,u.color,
    c.starts_at,c.ends_at,c.all_day,c.recurrence_rule,c.exceptions,c.ics_uid
    FROM items i LEFT JOIN calendar_events c ON c.item_id=i.id AND c.household_id=i.household_id
    LEFT JOIN users u ON u.id=i.assigned_to AND u.household_id=i.household_id AND u.disabled_at IS NULL
    WHERE i.household_id=:h AND i.kind='event' AND i.deleted_at IS NULL"""


def parse_date(value):
    try:
        result = date.fromisoformat(value)
        if result.isoformat() == value and 1900 <= result.year <= 2101:
            return result
    except (ValueError, TypeError):
        pass
    raise DomainError(422, "Choose valid calendar dates.")


def local_datetime(value, zone):
    try:
        local = datetime.fromisoformat(value)
        if local.tzinfo is None and "T" in value and 1900 <= local.year <= 2100:
            return attach_zone(local, zone)
    except (ValueError, TypeError, OverflowError):
        pass
    raise DomainError(422, "Choose a valid time in the household timezone.")


def attach_zone(local, zone):
    aware = local.replace(tzinfo=zone, fold=0)
    if aware.astimezone(timezone.utc).astimezone(zone).replace(tzinfo=None) != local:
        raise DomainError(422, "This local time falls in a daylight saving gap.")
    return aware


def validated_rule(rule, start):
    if not rule:
        return None
    try:
        if not isinstance(rule, str) or len(rule) > 250:
            raise ValueError
        parts = [part.split("=", 1) for part in rule.upper().split(";")]
        fields = dict(parts)
        if len(fields) != len(parts) or not fields.keys() <= RULE_FIELDS or fields.get("FREQ") not in REPEAT.values():
            raise ValueError
        if not 1 <= int(fields.get("INTERVAL", "1")) <= 366:
            raise ValueError
        if not 1 <= int(fields.get("COUNT", "1")) <= 5000 or {"COUNT", "UNTIL"} <= fields.keys():
            raise ValueError
        if "UNTIL" in fields and not 1900 <= int(fields["UNTIL"][:4]) <= 2100:
            raise ValueError
        if not isinstance(start, datetime) and "UNTIL" in fields:
            if len(fields["UNTIL"]) != 8:
                raise ValueError
        begin = start if isinstance(start, datetime) else datetime.combine(start, time.min)
        rrulestr(rule.upper(), dtstart=begin)
        return rule.upper()
    except (ValueError, TypeError, IndexError, OverflowError):
        raise DomainError(422, "This calendar recurrence rule is unsupported.") from None


def validate(connection, household, data, zone):
    title = clean(data.get("title"), 120, required=True)
    details = clean(data.get("details", ""), 1000)
    all_day = data.get("allDay", False)
    if type(all_day) is not bool:
        raise DomainError(422, "Choose whether the event lasts all day.")
    if all_day:
        start, end = parse_date(data.get("start")), parse_date(data.get("end"))
    else:
        start, end = (local_datetime(data.get(field), zone) for field in ("start", "end"))
    duration = end - start
    if not timedelta(0) < duration <= timedelta(days=366):
        raise DomainError(422, "The event must end after it starts and span at most one year.")
    assigned_to = clean(data.get("assignedTo", ""), 64) or None
    if assigned_to and not row(connection, """SELECT 1 FROM users WHERE household_id=:h
                    AND id=:id AND disabled_at IS NULL AND role<>'display'""", h=household, id=assigned_to):
        raise DomainError(422, "Choose a member in this household.")
    repeat = data.get("repeat", "")
    if not isinstance(repeat, str) or repeat and repeat not in REPEAT:
        raise DomainError(422, "Choose an available repeat interval.")
    rule = validated_rule(data.get("rule") or (f"FREQ={REPEAT[repeat]}" if repeat else None), start)
    exclusions = data.get("exceptions", [])
    if not isinstance(exclusions, list) or len(exclusions) > 200 or exclusions and not rule:
        raise DomainError(422, "Choose up to 200 skipped dates for a recurring event.")
    exceptions = sorted({parse_date(value).isoformat() for value in exclusions})
    if not all_day:
        start, end = (point.replace(tzinfo=None) for point in (start, end))
    return {"title": title, "details": details, "assigned": assigned_to, "starts": start.isoformat(),
            "ends": end.isoformat(), "all_day": int(all_day), "rule": rule, "exceptions": json.dumps(exceptions)}


def event_data(record, zone):
    start, end = record["starts_at"], record["ends_at"]
    all_day = bool(record["all_day"])
    if not start and record["due_at"]:
        # Alpha records can hold dates, local datetimes, or explicit offsets.
        try:
            legacy = record["due_at"]
            if len(legacy) == 10:
                first = parse_date(legacy)
                last, all_day = first + ONE_DAY, True
            else:
                first = datetime.fromisoformat(legacy)
                if first.tzinfo:
                    first = first.astimezone(zone).replace(tzinfo=None)
                last = first + timedelta(hours=1)
            start, end = first.isoformat(), last.isoformat()
        except (ValueError, OverflowError):
            pass
    return {
        "id": record["id"], "version": record["version"], "title": record["title"], "details": record["details"],
        "assignedTo": record["assigned_to"], "memberName": record["display_name"], "memberColor": record["color"],
        "start": start, "end": end, "allDay": all_day, "rule": record["recurrence_rule"],
        "exceptions": json.loads(record["exceptions"] or "[]"),
    }


def occurrence_points(event, zone, start_window, end_window):
    all_day = event["allDay"]
    if all_day:
        starts = datetime.combine(date.fromisoformat(event["start"]), time.min)
        ends = datetime.combine(date.fromisoformat(event["end"]), time.min)
        low, high = (datetime.combine(d, time.min) for d in (start_window, end_window))
    else:
        starts = attach_zone(datetime.fromisoformat(event["start"]), zone)
        ends = attach_zone(datetime.fromisoformat(event["end"]), zone)
        low, high = (datetime.combine(d, time.min, zone) for d in (start_window, end_window))
    duration = ends - starts
    if event["rule"]:
        occurrences = rrulestr(event["rule"], dtstart=starts).xafter(low - duration, count=440, inc=True)
    else:
        occurrences = (starts,)
    excluded = set(event["exceptions"])
    for start in occurrences:
        if start >= high:
            break
        end = start + duration
        if end <= low or start.date().isoformat() in excluded:
            continue
        if all_day:
            yield start.date().isoformat(), end.date().isoformat(), None
        else:
            local_start, local_end = (point.replace(tzinfo=None) for point in (start, end))
            try:
                attach_zone(local_start, zone)
                attach_zone(local_end, zone)
            except DomainError:
                continue
            iso = start.isoformat()
            yield local_start.isoformat(), local_end.isoformat(), iso[-6:]


def load(database, user, start_value, end_value, member=None):
    zone = ZoneInfo(user["timezone"])
    today = datetime.now(zone).date()
    start = parse_date(start_value) if start_value is not None else today
    end = parse_date(end_value) if end_value is not None else start + timedelta(days=31)
    if not 1 <= (end - start).days <= 62:
        raise DomainError(422, "Choose a date range of up to 62 days.")
    condition = " AND i.assigned_to=:member" if member else ""
    result, unscheduled = [], []
    with database.connect() as connection:
        records = statement(connection, EVENTS_SQL + condition, h=user["household_id"], member=member).mappings()
        for record in records:
            event = event_data(record, zone)
            if not event["start"]:
                unscheduled.append(event)
                continue
            try:
                for begins, ends, offset in occurrence_points(event, zone, start, end):
                    result.append({**event, "occurrenceStart": begins, "occurrenceEnd": ends, "utcOffset": offset})
                    if len(result) > 5000:
                        raise DomainError(422, "Select fewer calendar days to view these events.")
            except DomainError:
                if record["starts_at"]:
                    raise
                unscheduled.append(event)
    result.sort(key=lambda entry: (entry["occurrenceStart"], entry["id"]))
    return {"events": result, "unscheduled": unscheduled, "today": today.isoformat(), "timezone": zone.key}


def save_event(connection, user, entity, fields, version, uid=None):
    params = {**fields, "h": user["household_id"], "id": entity, "actor": user["id"], "v": version, "uid": uid}
    if version == 1:
        statement(connection, """INSERT INTO items(id,household_id,kind,title,details,due_at,assigned_to,created_by)
            VALUES(:id,:h,'event',:title,:details,:starts,:assigned,:actor)""", **params)
    else:
        statement(connection, """UPDATE items SET title=:title,details=:details,due_at=:starts,assigned_to=:assigned,
            version=:v,updated_at=CURRENT_TIMESTAMP WHERE household_id=:h AND id=:id AND kind='event'""", **params)
    statement(connection, """INSERT INTO calendar_events
        (item_id,household_id,starts_at,ends_at,all_day,recurrence_rule,exceptions,ics_uid)
        VALUES(:id,:h,:starts,:ends,:all_day,:rule,:exceptions,:uid)
        ON CONFLICT(item_id) DO UPDATE SET starts_at=:starts,ends_at=:ends,all_day=:all_day,
        recurrence_rule=:rule,exceptions=:exceptions WHERE household_id=:h""", **params)


def write(database, user, operation, target, data):
    if user["role"] not in {"owner", "admin", "adult"}:
        raise DomainError(403, "Only an adult can change household events.")
    household = user["household_id"]
    zone = ZoneInfo(user["timezone"])
    imported = read_ics(data.get("ics"), zone) if operation == "calendar.import" else []
    with database.connect() as connection:
        connection.exec_driver_sql("BEGIN IMMEDIATE")
        mutation = Mutation(connection, user, operation, data, target)
        replay = mutation.replay_id
        if operation == "calendar.import":
            if replay:
                return 201, {"created": int(replay)}, None
            created = 0
            for uid, fields in imported:
                if row(connection, EVENTS_SQL + " AND COALESCE(c.ics_uid,i.id || '@household-six.local')=:uid",
                       h=household, uid=uid):
                    continue
                save_event(connection, user, str(uuid.uuid4()), validate(connection, household, fields, zone), 1, uid)
                created += 1
            mutation.finish(str(created), 1)
            connection.commit()
            return 201, {"created": created}, "import" if created else None
        if operation == "calendar.delete" and replay:
            return 204, None, None
        entity = replay or target or str(uuid.uuid4())
        version = 1
        if target:
            current = row(connection, EVENTS_SQL + " AND i.id=:id", id=entity, h=household)
            if not current:
                raise DomainError(404, "That calendar event was not found.")
            if not replay and expected_version(data) != current["version"]:
                raise DomainError(409, "This event changed on another device. Refresh and try again.")
            version = current["version"] + 1
        if not replay:
            if operation == "calendar.delete":
                statement(connection, """UPDATE items SET deleted_at=CURRENT_TIMESTAMP,version=:v,
                    updated_at=CURRENT_TIMESTAMP WHERE household_id=:h AND id=:id AND kind='event'""",
                          id=entity, h=household, v=version)
            else:
                fields = validate(connection, household, data, zone)
                save_event(connection, user, entity, fields, version)
            mutation.finish(entity, version)
            connection.commit()
        if operation == "calendar.delete":
            return 204, None, entity
        record = row(connection, EVENTS_SQL + " AND i.id=:id", id=entity, h=household)
        if not record:
            raise DomainError(404, "That calendar event was not found.")
        return 201 if operation == "calendar.create" else 200, event_data(record, zone), entity if not replay else None


def read_ics(raw, zone):
    if not isinstance(raw, str) or not raw or len(raw.encode("utf-8")) > 128_000:
        raise DomainError(422, "Choose an iCalendar file up to 128 KB.")
    try:
        calendar = Calendar.from_ical(raw)
        parts = calendar.walk("VEVENT")
        if not 1 <= len(parts) <= 100:
            raise DomainError(422, "Import between 1 and 100 events at a time.")
        records = []
        for part in parts:
            if any(field in part for field in ("RDATE", "EXRULE", "RECURRENCE-ID")):
                raise DomainError(422, "This iCalendar file uses recurrence features beyond skipped dates.")
            start = part.decoded("DTSTART")
            all_day = not isinstance(start, datetime)
            end = part.decoded("DTEND", None)
            if end is None:
                end = start + part.decoded("DURATION", ONE_DAY if all_day else timedelta(hours=1))
            if (not isinstance(end, datetime)) != all_day:
                raise ValueError

            def local(point):
                if isinstance(point, datetime) and point.tzinfo:
                    return point.astimezone(zone).replace(tzinfo=None)
                return point

            rule = part.get("RRULE")
            exceptions = part.get("EXDATE", [])
            if not isinstance(exceptions, list):
                exceptions = [exceptions]
            excluded = []
            for entry in exceptions:
                for item in entry.dts:
                    point = local(item.dt)
                    excluded.append((point.date() if isinstance(point, datetime) else point).isoformat())
            uid = clean(str(part.get("UID", "")), 255, required=True)
            records.append((uid, {
                "title": str(part.get("SUMMARY", "Untitled event")), "details": str(part.get("DESCRIPTION", "")),
                "allDay": all_day, "start": local(start).isoformat(), "end": local(end).isoformat(),
                "rule": rule.to_ical().decode("ascii") if rule else None, "exceptions": excluded,
            }))
        return records
    except DomainError:
        raise
    except (ValueError, TypeError, KeyError, AttributeError, RecursionError, OverflowError):
        raise DomainError(422, "That iCalendar file could not be read.") from None


def export_ics(database, user):
    zone = ZoneInfo(user["timezone"])
    calendar = Calendar()
    calendar.add("prodid", "-//Household Six//Calendar//EN")
    calendar.add("version", "2.0")
    # Include the household timezone so LAN and standalone calendar clients can resolve wall times.
    calendar.add_component(Timezone.from_tzinfo(zone, first_date=date(1900, 1, 1), last_date=date(2101, 1, 1)))
    with database.connect() as connection:
        for record in statement(connection, EVENTS_SQL, h=user["household_id"]).mappings():
            event = event_data(record, zone)
            if not event["start"]:
                continue
            component = Event()
            component.add("uid", record["ics_uid"] or f"{event['id']}@household-six.local")
            component.add("summary", event["title"])
            component.add("description", event["details"])
            component.add("dtstamp", datetime.now(timezone.utc))
            if event["allDay"]:
                start, end = (date.fromisoformat(event[field]) for field in ("start", "end"))
            else:
                start, end = (datetime.fromisoformat(event[field]).replace(tzinfo=zone) for field in ("start", "end"))
            component.add("dtstart", start)
            component.add("dtend", end)
            if event["rule"]:
                component.add("rrule", event["rule"])
                for value in event["exceptions"]:
                    day = date.fromisoformat(value)
                    exception = datetime.combine(day, start.timetz()) if isinstance(start, datetime) else day
                    component.add("exdate", exception)
            calendar.add_component(component)
    return calendar.to_ical()
