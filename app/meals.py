"""Weekly meals, structured recipes, and exact grocery quantities."""
from datetime import datetime, timedelta
from decimal import Decimal, ROUND_HALF_UP
import json
import re
import uuid
from zoneinfo import ZoneInfo

from app.calendar_service import parse_date
from app.dates import local_day
from app.ledger import ADULT_ROLES
from app.mutations import DomainError, Mutation, clean, expected_version, row, statement
from app.shopping import find_list

SLOTS = ("breakfast", "lunch", "dinner", "snack")
RECIPE_SQL = """SELECT i.id,i.title,i.details,i.version,r.servings,r.instructions FROM items i
    LEFT JOIN recipes r ON i.id=r.id AND i.household_id=r.household_id
    WHERE i.household_id=:h AND i.kind='recipe' AND i.deleted_at IS NULL"""
MEAL_SQL = """SELECT i.id,i.title,i.details,i.version,i.due_at,s.day,s.slot,s.recipe_id,s.servings,recipe.title AS recipe_title
    FROM items i LEFT JOIN meal_slots s ON i.id=s.id AND i.household_id=s.household_id
    LEFT JOIN items recipe ON recipe.id=s.recipe_id AND recipe.household_id=s.household_id AND recipe.kind='recipe'
    WHERE i.household_id=:h AND i.kind='meal' AND i.deleted_at IS NULL"""


def today(user):
    return datetime.now(ZoneInfo(user["timezone"])).date()


def week(day):
    start = day - timedelta(days=day.weekday())
    return start.isoformat(), (start + timedelta(days=7)).isoformat()


def list_recipes(connection, household):
    ingredients = {}
    for item in statement(connection, """SELECT recipe_id,name,quantity,unit,category FROM recipe_ingredients
            WHERE household_id=:h ORDER BY position""", h=household).mappings():
        ingredients.setdefault(item["recipe_id"], []).append({
            key: item[key] for key in ("name", "quantity", "unit", "category")
        })
    return [dict(recipe, ingredients=ingredients.get(recipe["id"], []))
            for recipe in statement(connection, RECIPE_SQL + " ORDER BY i.title,i.id", h=household).mappings()]


def recipes(database, user):
    with database.connect() as connection:
        return {"recipes": list_recipes(connection, user["household_id"])}


def plan(database, user, date_value=None):
    day = parse_date(date_value) if date_value else today(user)
    start, end = week(day)
    household = user["household_id"]
    with database.connect() as connection:
        rows = statement(connection, MEAL_SQL + """ AND (s.day IS NULL OR s.day>=:start AND s.day<:end)
            ORDER BY COALESCE(s.day,i.due_at),i.title,i.id""", h=household, start=start, end=end).mappings()
        meals = []
        zone = ZoneInfo(user["timezone"])
        for item in rows:
            legacy_day = local_day(item["due_at"], zone) if not item["day"] else None
            day_text = item["day"] or (legacy_day.isoformat() if legacy_day else "")
            if not day_text or start <= day_text < end:
                meals.append(dict(item, day=day_text, slot=item["slot"] or "dinner"))
        lists = statement(connection, "SELECT id,name FROM shopping_lists WHERE household_id=:h ORDER BY name",
                          h=household).mappings()
        return {"weekStart": start, "weekEnd": end, "date": day.isoformat(), "meals": meals,
                "recipes": list_recipes(connection, household),
                "lists": [{"id": "default", "name": "Groceries"}, *(dict(item) for item in lists)]}


def servings(data):
    number = data.get("servings")
    if type(number) is not int or not 1 <= number <= 1000:
        raise DomainError(422, "Servings must be a whole number from 1 to 1,000.")
    return number


def decimal_quantity(value):
    if not isinstance(value, str) or not re.fullmatch(r"[0-9]{1,6}(?:\.[0-9]{1,4})?", value) or Decimal(value) <= 0:
        raise DomainError(422, "Ingredient quantities must be positive numbers with up to four decimal places.")
    return format(Decimal(value).normalize(), "f")


def recipe_fields(data):
    instructions = data.get("instructions", "")
    if not isinstance(instructions, str) or len(instructions) > 8000:
        raise DomainError(422, "Keep recipe instructions under 8,000 characters.")
    ingredients = data.get("ingredients")
    if not isinstance(ingredients, list) or not 1 <= len(ingredients) <= 60:
        raise DomainError(422, "Add between 1 and 60 ingredients.")
    parsed = []
    for position, item in enumerate(ingredients):
        if not isinstance(item, dict):
            raise DomainError(422, "Check your recipe ingredients.")
        parsed.append({
            "position": position, "name": clean(item.get("name"), 120, required=True),
            "quantity": decimal_quantity(item.get("quantity")),
            "unit": clean(item.get("unit", ""), 30), "category": clean(item.get("category", ""), 60),
        })
    return instructions.replace("\x00", "").strip(), parsed


def current_entity(connection, household, operation, entity):
    recipe = operation.startswith("recipe.")
    sql = RECIPE_SQL if recipe else MEAL_SQL
    selected = row(connection, sql + " AND i.id=:id", h=household, id=entity)
    if not selected:
        raise DomainError(404, "This recipe or meal was not found.")
    return dict(selected)


def save(connection, user, operation, target, data):
    household, actor = user["household_id"], user["id"]
    entity = target or str(uuid.uuid4())
    is_recipe = operation.startswith("recipe.")
    params = {"id": entity, "h": household, "actor": actor, "kind": "recipe" if is_recipe else "meal"}
    version = 1
    if target:
        record = current_entity(connection, household, operation, target)
        if expected_version(data) != record["version"]:
            raise DomainError(409, "This record changed. Refresh and try again.")
        version = record["version"] + 1
    if operation.endswith(".archive"):
        statement(connection, "UPDATE items SET deleted_at=CURRENT_TIMESTAMP,version=:v WHERE id=:id AND household_id=:h",
                  **params, v=version)
        return entity, version

    count = servings(data)
    details = clean(data.get("details", ""), 1000)
    if is_recipe:
        title = clean(data.get("title"), 120, required=True)
        instructions, ingredients = recipe_fields(data)
        day = None
    else:
        day = parse_date(data.get("date")).isoformat()
        recipe_id = clean(data.get("recipeId", ""), 64) or None
        slot = data.get("slot")
        if slot not in SLOTS:
            raise DomainError(422, "Choose a meal slot.")
        recipe = (row(connection, """SELECT i.title FROM items i JOIN recipes r
            ON r.id=i.id AND r.household_id=i.household_id
            WHERE i.household_id=:h AND i.id=:id AND i.kind='recipe'
            AND (i.deleted_at IS NULL OR i.id=:retained)""", h=household, id=recipe_id,
                      retained=record["recipe_id"] if target else None) if recipe_id else None)
        if recipe_id and not recipe:
            raise DomainError(422, "Choose a recipe from this household.")
        title = clean(data.get("title", ""), 120) or (recipe["title"] if recipe else "")
        if not title:
            raise DomainError(422, "Give this meal a name or choose a recipe.")
    values = {**params, "title": title, "details": details, "day": day, "v": version, "count": count}
    if target:
        statement(connection, """UPDATE items SET title=:title,details=:details,due_at=:day,version=:v,
            updated_at=CURRENT_TIMESTAMP WHERE id=:id AND household_id=:h""", **values)
    else:
        statement(connection, """INSERT INTO items(id,household_id,kind,title,details,due_at,created_by)
            VALUES(:id,:h,:kind,:title,:details,:day,:actor)""", **values)
    if is_recipe:
        statement(connection, """INSERT INTO recipes(id,household_id,servings,instructions) VALUES(:id,:h,:count,:instructions)
            ON CONFLICT(id) DO UPDATE SET servings=:count,instructions=:instructions WHERE household_id=:h""",
                  **values, instructions=instructions)
        statement(connection, "DELETE FROM recipe_ingredients WHERE household_id=:h AND recipe_id=:id", **values)
        for item in ingredients:
            statement(connection, """INSERT INTO recipe_ingredients(recipe_id,position,household_id,name,quantity,unit,category)
                VALUES(:id,:position,:h,:name,:quantity,:unit,:category)""", **values, **item)
    else:
        statement(connection, """INSERT INTO meal_slots(id,household_id,day,slot,recipe_id,servings)
            VALUES(:id,:h,:day,:slot,:recipe,:count) ON CONFLICT(id) DO UPDATE SET
            day=:day,slot=:slot,recipe_id=:recipe,servings=:count WHERE household_id=:h""",
                  **values, slot=slot, recipe=recipe_id)
    return entity, version


def grocery_targets(connection, household, start, end):
    rows = statement(connection, """SELECT g.name,g.quantity,g.unit,g.category,m.servings AS planned,r.servings
        FROM meal_slots m JOIN items i ON i.id=m.id AND i.household_id=m.household_id
        JOIN recipes r ON r.id=m.recipe_id AND r.household_id=m.household_id
        JOIN recipe_ingredients g ON g.recipe_id=r.id AND g.household_id=r.household_id
        WHERE m.household_id=:h AND i.deleted_at IS NULL AND m.day>=:start AND m.day<:end
        ORDER BY m.day,m.id,g.position""", h=household, start=start, end=end).mappings()
    totals = {}
    for ingredient in rows:
        key = json.dumps([ingredient[field].casefold() for field in ("name", "unit")], separators=(",", ":"))
        amount = Decimal(ingredient["quantity"]) * ingredient["planned"] / ingredient["servings"]
        if key in totals:
            totals[key]["total"] += amount
        else:
            totals[key] = {**ingredient, "total": amount}
    return totals


def sync_groceries(connection, user, data):
    household, actor = user["household_id"], user["id"]
    start, end = week(parse_date(data.get("date")))
    list_key = clean(data.get("listId"), 64, required=True)
    find_list(connection, household, list_key)
    params = {"h": household, "list_key": list_key, "start": start, "actor": actor,
              "list_id": None if list_key == "default" else list_key}
    existing = {item["ingredient_key"]: dict(item) for item in statement(connection, """SELECT gs.ingredient_key,
        i.id,i.title,i.quantity,i.category,i.completed,i.deleted_at FROM grocery_sources gs
        JOIN items i ON i.id=gs.item_id AND i.household_id=gs.household_id AND i.kind='shopping'
        WHERE gs.household_id=:h AND gs.list_key=:list_key AND gs.week_start=:start""", **params).mappings()}
    totals = grocery_targets(connection, household, start, end)
    result = {"created": 0, "updated": 0, "removed": 0}
    for key, ingredient in totals.items():
        amount = ingredient["total"].quantize(Decimal(".0001"), rounding=ROUND_HALF_UP) or Decimal(".0001")
        quantity = " ".join(filter(None, [format(amount.normalize(), "f"), ingredient["unit"]]))
        fields = {"title": ingredient["name"], "quantity": quantity, "category": ingredient["category"]}
        current = existing.pop(key, None)
        if current and not current["deleted_at"]:
            if any(current[field] != value for field, value in fields.items()):
                statement(connection, """UPDATE items SET title=:title,quantity=:quantity,category=:category,
                    completed=0,version=version+1,updated_at=CURRENT_TIMESTAMP WHERE id=:id AND household_id=:h""",
                          **params, **fields, id=current["id"])
                result["updated"] += 1
            continue
        item_id = str(uuid.uuid4())
        statement(connection, """INSERT INTO items
            (id,household_id,kind,title,quantity,category,shopping_list_id,created_by)
            VALUES(:id,:h,'shopping',:title,:quantity,:category,:list_id,:actor)""", **params, **fields, id=item_id)
        statement(connection, """INSERT INTO grocery_sources(household_id,list_key,week_start,ingredient_key,item_id)
            VALUES(:h,:list_key,:start,:key,:id) ON CONFLICT(household_id,list_key,week_start,ingredient_key)
            DO UPDATE SET item_id=:id""", **params, key=key, id=item_id)
        result["created"] += 1
    for entry in existing.values():
        if not entry["completed"] and not entry["deleted_at"]:
            statement(connection, """UPDATE items SET deleted_at=CURRENT_TIMESTAMP,version=version+1,
                updated_at=CURRENT_TIMESTAMP WHERE household_id=:h AND id=:id""", **params, id=entry["id"])
            result["removed"] += 1
    return result


def write(database, user, operation, target, data):
    if user["role"] not in ADULT_ROLES:
        raise DomainError(403, "Only an adult can change recipes and meal plans.")
    with database.connect() as connection:
        connection.exec_driver_sql("BEGIN IMMEDIATE")
        mutation = Mutation(connection, user, operation, data, target)
        entity = mutation.replay_id
        if operation == "meal.groceries":
            if entity:
                return 200, json.loads(entity), None
            synced = sync_groceries(connection, user, data)
            mutation.finish(json.dumps(synced), 1)
            connection.commit()
            return 200, synced, "groceries" if any(synced.values()) else None
        if not entity:
            entity, version = save(connection, user, operation, target, data)
            mutation.finish(entity, version)
            connection.commit()
        event = None if mutation.replay_id else entity
        if operation.endswith(".archive"):
            return 204, None, event
        result = current_entity(connection, user["household_id"], operation, entity)
        return 201 if operation.endswith(".create") else 200, result, event
