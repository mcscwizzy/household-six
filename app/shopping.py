"""Household shopping lists over the existing completion and offline item IDs."""
import uuid

from sqlalchemy.exc import IntegrityError

from app.mutations import DomainError, Mutation, clean, expected_version, row, statement

DEFAULT_LIST = {"id": "default", "name": "Groceries"}
ITEM_FIELDS = "id,kind,title,details,completed,version,quantity,category,shopping_list_id"


def find_list(connection, household, list_id):
    if list_id == "default":
        return DEFAULT_LIST
    result = row(connection, "SELECT id,name FROM shopping_lists WHERE household_id=:h AND id=:id",
                 h=household, id=list_id)
    if not result:
        raise DomainError(404, "That shopping list was not found.")
    return dict(result)


def items(condition):
    return f"SELECT {ITEM_FIELDS} FROM items WHERE household_id=:h AND kind='shopping' AND deleted_at IS NULL AND {condition}"


def find_item(connection, household, item_id):
    item = row(connection, items("id=:id"), h=household, id=item_id)
    if not item:
        raise DomainError(404, "That shopping item was not found.")
    return dict(item)


def load(database, user, list_id):
    household = user["household_id"]
    with database.connect() as connection:
        selected = find_list(connection, household, list_id)
        lists = statement(connection, "SELECT id,name FROM shopping_lists WHERE household_id=:h ORDER BY name,id",
                          h=household).mappings()
        result = statement(connection, items("shopping_list_id IS :id") +
                           " ORDER BY completed, category COLLATE NOCASE,title COLLATE NOCASE,id",
                           h=household, id=None if list_id == "default" else list_id).mappings()
        return {"lists": [DEFAULT_LIST, *(dict(entry) for entry in lists)], "list": selected,
                "items": [dict(item) for item in result]}


def write(database, user, operation, target, data):
    if user["role"] == "display" or operation == "shopping.list.create" and user["role"] == "child":
        raise DomainError(403, "This account cannot make that shopping change.")
    household = user["household_id"]
    with database.connect() as connection:
        connection.exec_driver_sql("BEGIN IMMEDIATE")
        mutation = Mutation(connection, user, operation, data, target)
        if mutation.replay_id:
            if operation == "shopping.item.delete":
                return 204, None, None
            if operation == "shopping.list.create":
                return 201, find_list(connection, household, mutation.replay_id), None
            return (201 if operation == "shopping.item.create" else 200,
                    find_item(connection, household, mutation.replay_id), None)

        entity = target if operation in {"shopping.item.update", "shopping.item.delete"} else str(uuid.uuid4())
        version = 1
        if operation == "shopping.list.create":
            result = {"id": entity, "name": clean(data.get("name"), 60, required=True)}
            if result["name"].casefold() == DEFAULT_LIST["name"].casefold():
                raise DomainError(409, "That list name is already in use.")
            try:
                statement(connection, "INSERT INTO shopping_lists(id, household_id, name) VALUES(:id, :h, :name)",
                          h=household, **result)
            except IntegrityError:
                raise DomainError(409, "That list name is already in use.") from None
        elif operation == "shopping.item.delete":
            version = check_version(connection, household, entity, data) + 1
            statement(connection, """UPDATE items SET deleted_at=CURRENT_TIMESTAMP,
                updated_at=CURRENT_TIMESTAMP,version=:version WHERE id=:id AND household_id=:h""",
                      id=entity, h=household, version=version)
            result = None
        else:
            fields = {
                "title": clean(data.get("title"), 120, required=True),
                "quantity": clean(data.get("quantity", ""), 40), "category": clean(data.get("category", ""), 60),
                "details": clean(data.get("details", ""), 1000),
            }
            if operation == "shopping.item.create":
                find_list(connection, household, target)
                statement(connection, """INSERT INTO items
                    (id,household_id,kind,title,details,quantity,category,shopping_list_id,created_by)
                    VALUES(:id,:h,'shopping',:title,:details,:quantity,:category,:list,:actor)""",
                          id=entity, h=household, list=None if target == "default" else target, actor=user["id"], **fields)
            else:
                version = check_version(connection, household, entity, data) + 1
                statement(connection, """UPDATE items SET title=:title,details=:details,quantity=:quantity,
                    category=:category,updated_at=CURRENT_TIMESTAMP,version=:version WHERE id=:id AND household_id=:h""",
                          id=entity, h=household, version=version, **fields)
            result = find_item(connection, household, entity)
        mutation.finish(entity, version)
        connection.commit()
        status = 204 if result is None else 201 if operation.endswith(".create") else 200
        return status, result, entity


def check_version(connection, household, entity, data):
    version = expected_version(data)
    if find_item(connection, household, entity)["version"] != version:
        raise DomainError(409, "This item changed on another device. Refresh and try again.")
    return version
