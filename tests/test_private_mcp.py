"""Optional integration test for the real MCP stdio protocol and scoped grants."""
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest

from app import assistant, database, private_mcp, shopping
from app.mutations import statement


@unittest.skipUnless(os.environ.get("HOUSEHOLD_SIX_MCP_LIVE") == "1", "requires the optional MCP SDK")
class PrivateMcpTest(unittest.IsolatedAsyncioTestCase):
    async def test_scoped_reads_and_proposal_confirmation(self):
        from mcp import Client, StdioServerParameters

        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "household.sqlite3"
            database.migrate(path)
            engine = database.engine(path)
            owner = {"id": "owner", "household_id": "home", "role": "owner", "timezone": "America/Chicago"}
            with engine.begin() as connection:
                for household, user in (("home", "owner"), ("private", "neighbor")):
                    statement(connection, "INSERT INTO households(id,name) VALUES(:id,:id)", id=household)
                    statement(connection, """INSERT INTO users(id,household_id,username,password_hash,display_name,role)
                        VALUES(:id,:h,:id,'unused',:id,'owner')""", h=household, id=user)
                shopping.add_item(connection, {"household_id": "private", "id": "neighbor"}, "default", "secret",
                                  {"title": "Private", "details": "", "category": "", "quantity": "1"})
            grant_id, raw = private_mcp.issue(engine, "owner", {"shopping"})
            _, with_proposals = private_mcp.issue(engine, "owner", {"shopping"}, True)

            def settings(token):
                return StdioServerParameters(command=sys.executable, args=["-m", "app.private_mcp", "serve"],
                                             env={"MCP_ENABLED": "true", "MCP_TOKEN": token, "DATA_DIR": directory})

            async with Client(settings(raw)) as client:
                actual = {tool.name for tool in (await client.list_tools()).tools}
                self.assertEqual(actual, {"household_shopping"})
                response = await client.call_tool("household_shopping")
                self.assertFalse(response.is_error, response.content)
                data = response.structured_content or json.loads(response.content[0].text)
                self.assertEqual(data["lines"], [])
                private_mcp.revoke(engine, "owner", grant_id)
                response = await client.call_tool("household_shopping")
                self.assertTrue(response.is_error)

            async with Client(settings(with_proposals)) as client:
                actual = {tool.name for tool in (await client.list_tools()).tools}
                self.assertEqual(actual, {"household_shopping", "propose_grocery"})
                response = await client.call_tool("propose_grocery", {"title": "Pears", "quantity": "4"})
                self.assertFalse(response.is_error, response.content)
                data = response.structured_content or json.loads(response.content[0].text)
                self.assertEqual(data["status"], "awaiting_confirmation")
            job = assistant.list_jobs(engine, owner)["jobs"][0]
            self.assertEqual(job["state"], "proposal")
            self.assertFalse(shopping.load(engine, owner, "default")["items"])
