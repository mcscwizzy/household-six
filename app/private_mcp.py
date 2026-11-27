"""Local, stdio-only MCP server with scoped credentials and proposal review."""
import argparse
from datetime import datetime, timedelta, timezone
import hashlib
import json
import os
from pathlib import Path
import secrets
import uuid

from app import assistant, database
from app.ledger import ADULT_ROLES
from app.mutations import DomainError, clean, row, statement

READ_SCOPES = {"calendar", "chores", "shopping", "meals", "rewards"}


def enabled():
    return os.environ.get("MCP_ENABLED", "false").lower() == "true"


def token_hash(token):
    return hashlib.sha256(token.encode()).hexdigest()


def audit(connection, actor, action, object_id=None):
    statement(connection, """INSERT INTO audit_log(id,household_id,actor_id,action,object_id)
        VALUES(:id,:household,:actor,:action,:object)""", id=str(uuid.uuid4()), household=actor["household_id"],
              actor=actor["id"], action=action, object=object_id)


def issue(engine, username, scopes, proposals=False, days=30):
    if not scopes or not scopes <= READ_SCOPES or not 1 <= days <= 90 or proposals and "shopping" not in scopes:
        raise DomainError(422, "Choose valid scopes and a credential lifetime of 1 to 90 days.")
    raw = secrets.token_urlsafe(40)
    grant_id = str(uuid.uuid4())
    expiry = (datetime.now(timezone.utc) + timedelta(days=days)).strftime("%Y-%m-%d %H:%M:%S")
    with engine.begin() as connection:
        actor = row(connection, """SELECT id,household_id,role FROM users WHERE username=:name COLLATE NOCASE
                AND disabled_at IS NULL""", name=username)
        if not actor or actor["role"] not in ADULT_ROLES:
            raise DomainError(403, "Choose an enabled adult account.")
        result = scopes | ({"propose_grocery"} if proposals else set())
        statement(connection, """INSERT INTO mcp_grants(token_hash,id,household_id,actor_id,scopes,expires_at)
            VALUES(:hash,:id,:household,:actor,:scopes,:expiry)""", hash=token_hash(raw), id=grant_id,
                  household=actor["household_id"], actor=actor["id"], scopes=",".join(sorted(result)), expiry=expiry)
        audit(connection, actor, "mcp.grant.issue", grant_id)
    return grant_id, raw


def revoke(engine, username, grant_id):
    with engine.begin() as connection:
        actor = row(connection, """SELECT u.id,u.household_id,u.role FROM users u JOIN mcp_grants g
            ON g.actor_id=u.id AND g.household_id=u.household_id WHERE g.id=:id AND u.username=:name COLLATE NOCASE""",
                    id=grant_id, name=username)
        if not actor:
            raise DomainError(404, "This credential was not found.")
        statement(connection, """UPDATE mcp_grants SET revoked_at=CURRENT_TIMESTAMP
            WHERE id=:id AND household_id=:h AND actor_id=:actor AND revoked_at IS NULL""",
                  id=grant_id, h=actor["household_id"], actor=actor["id"])
        audit(connection, actor, "mcp.grant.revoke", grant_id)


def grant(connection, raw, scope=None):
    if not 30 <= len(raw) <= 120:
        raise DomainError(403, "This MCP credential was not accepted.")
    actor = row(connection, """SELECT u.id,u.role,u.household_id,h.timezone,g.scopes,g.id AS grant_id
        FROM mcp_grants g JOIN users u ON u.id=g.actor_id AND u.household_id=g.household_id
        JOIN households h ON h.id=g.household_id WHERE g.token_hash=:hash
        AND g.revoked_at IS NULL AND g.expires_at>CURRENT_TIMESTAMP AND u.disabled_at IS NULL""", hash=token_hash(raw))
    if not actor or actor["role"] not in ADULT_ROLES:
        raise DomainError(403, "This MCP credential was not accepted.")
    authorized = set(actor["scopes"].split(","))
    if scope and scope not in authorized:
        raise DomainError(403, "This MCP credential does not allow that action.")
    return dict(actor, authorized=authorized)


def proposed_grocery(engine, raw, title, quantity, category):
    fields = {
        "title": clean(title, 120, required=True),
        "quantity": clean(quantity, 40),
        "category": clean(category, 60),
    }
    with engine.connect() as connection:
        connection.exec_driver_sql("BEGIN IMMEDIATE")
        actor = grant(connection, raw, "propose_grocery")
        household = actor["household_id"]
        assistant.admit(connection, household, False)
        proposal_id = str(uuid.uuid4())
        statement(connection, """INSERT INTO assistant_jobs(id,household_id,actor_id,kind,state,result,expires_at)
            VALUES(:id,:h,:actor,'grocery','proposal',:result,datetime('now','+1 day'))""", id=proposal_id, h=household,
                  actor=actor["id"], result=json.dumps({"kind": "grocery", "data": {"items": [fields]}}))
        audit(connection, actor, "mcp.proposal.create", proposal_id)
        connection.commit()
    return {"status": "awaiting_confirmation", "proposal": proposal_id}


def create_server(engine, raw):
    from mcp.server import MCPServer
    from mcp.server.mcpserver.exceptions import ToolError

    with engine.connect() as connection:
        actor = grant(connection, raw)
    server = MCPServer("Household Six")

    for topic in sorted(actor["authorized"] & READ_SCOPES):
        def make_reader(section):
            def reader() -> dict:
                """Read the current household summary for this section."""
                try:
                    with engine.begin() as connection:
                        current = grant(connection, raw, section)
                        audit(connection, current, f"mcp.read.{section}", current["grant_id"])
                    return assistant.question_answer(engine, current, section)
                except DomainError as error:
                    raise ToolError(str(error)) from None
                except Exception:
                    raise ToolError("The household summary could not be read.") from None
            return reader

        server.tool(name=f"household_{topic}")(make_reader(topic))

    if "propose_grocery" in actor["authorized"]:
        @server.tool()
        def propose_grocery(title: str, quantity: str = "", category: str = "") -> dict:
            """Submit one grocery item for the associated household member to review in Six."""
            try:
                return proposed_grocery(engine, raw, title, quantity, category)
            except DomainError as error:
                raise ToolError(str(error)) from None
            except Exception:
                raise ToolError("The household proposal could not be submitted.") from None

    return server


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("serve")
    add = sub.add_parser("issue")
    add.add_argument("username")
    add.add_argument("--scopes", default="calendar,chores,shopping,meals,rewards")
    add.add_argument("--allow-grocery-proposals", action="store_true")
    add.add_argument("--days", type=int, default=30)
    remove = sub.add_parser("revoke")
    remove.add_argument("username")
    remove.add_argument("grant_id")
    args = parser.parse_args()
    if not enabled():
        raise SystemExit("Private MCP is disabled.")
    path = Path(os.environ.get("DATA_DIR", database.ROOT / "data")) / "household.sqlite3"
    if not path.is_file():
        raise SystemExit("Initialize Household Six before configuring MCP.")
    engine = database.engine(path)
    try:
        if args.command == "issue":
            grant_id, raw = issue(engine, args.username, set(args.scopes.split(",")), args.allow_grocery_proposals, args.days)
            print(f"Credential ID {grant_id}")
            print(f"MCP_TOKEN={raw}")
        elif args.command == "revoke":
            revoke(engine, args.username, args.grant_id)
        else:
            create_server(engine, os.environ.get("MCP_TOKEN", "")).run()
    except DomainError as error:
        raise SystemExit(str(error)) from None
    except ImportError:
        raise SystemExit("Install requirements-optional.lock to use MCP.") from None


if __name__ == "__main__":
    main()
