"""Domain and persistence regression tests using disposable SQLite databases."""
import os
import sqlite3
import tempfile
import unittest
from pathlib import Path


class HouseholdServiceTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory(prefix="household-six-test-")
        os.environ["DATA_DIR"] = cls.temp.name
        from app import server
        cls.service = server
        server.migrate()

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def setUp(self):
        s = self.service
        self.con = s.connect()
        self.con.execute("PRAGMA foreign_keys=ON")
        self.con.execute("DELETE FROM audit_log")
        self.con.execute("DELETE FROM points_ledger")
        self.con.execute("DELETE FROM items")
        self.con.execute("DELETE FROM sessions")
        self.con.execute("DELETE FROM users")
        self.con.execute("DELETE FROM households")
        self.con.execute("INSERT INTO households(id,name) VALUES('home','Home')")
        self.con.execute("INSERT INTO households(id,name) VALUES('other','Other')")
        self.con.execute("INSERT INTO users(id,household_id,username,password_hash,display_name,role) VALUES('parent','home','parent','unused','Parent','owner')")
        self.con.execute("INSERT INTO users(id,household_id,username,password_hash,display_name,role) VALUES('child','home','child','unused','Child','child')")
        self.con.execute("INSERT INTO users(id,household_id,username,password_hash,display_name,role) VALUES('other-user','other','other','unused','Other','owner')")
        self.con.commit()

    def tearDown(self):
        self.con.close()

    def test_password_hash_is_salted_and_verifiable(self):
        s=self.service
        one=s.pw_hash("correct horse battery staple")
        two=s.pw_hash("correct horse battery staple")
        self.assertNotEqual(one,two)
        self.assertTrue(s.verify_password("correct horse battery staple",one))
        self.assertFalse(s.verify_password("wrong",one))

    def test_csrf_tokens_from_multiple_open_tabs_remain_valid(self):
        s=self.service
        self.con.execute("INSERT INTO sessions(id_hash,user_id,csrf_hash,expires_at) VALUES('session-hash','parent',?,'2999-01-01T00:00:00+00:00')", (s.digest("old"),))
        self.con.execute("INSERT INTO csrf_tokens(session_id_hash,token_hash) VALUES('session-hash',?)", (s.digest("old"),))
        self.con.execute("INSERT INTO csrf_tokens(session_id_hash,token_hash) VALUES('session-hash',?)", (s.digest("new"),))
        self.con.commit()
        self.assertTrue(s.valid_csrf(self.con,"session-hash","old"))
        self.assertTrue(s.valid_csrf(self.con,"session-hash","new"))

    def test_household_queries_do_not_leak_other_household(self):
        s=self.service
        self.con.execute("INSERT INTO items(id,household_id,kind,title,created_by) VALUES('private','other','task','Private task','other-user')")
        self.con.execute("INSERT INTO items(id,household_id,kind,title,created_by) VALUES('mine','home','task','Home task','parent')")
        self.con.commit()
        self.assertEqual([row["id"] for row in s.list_items(self.con,"home","task")],["mine"])
        self.assertEqual(s.complete_item(self.con,"private","home","parent","owner"),None)

    def test_repeated_completion_awards_points_once(self):
        s=self.service
        self.con.execute("INSERT INTO items(id,household_id,kind,title,assigned_to,value,created_by) VALUES('chore','home','task','Feed the cat','child',4,'parent')")
        self.con.commit()
        self.con.execute("BEGIN IMMEDIATE")
        first=s.complete_item(self.con,"chore","home","parent","owner")
        self.con.commit()
        self.con.execute("BEGIN IMMEDIATE")
        second=s.complete_item(self.con,"chore","home","parent","owner")
        self.con.commit()
        total=self.con.execute("SELECT SUM(amount) FROM points_ledger WHERE member_id='child'").fetchone()[0]
        self.assertEqual(first["version"],2)
        self.assertEqual(second["version"],2)
        self.assertEqual(total,4)

    def test_child_cannot_complete_another_members_task(self):
        s=self.service
        self.con.execute("INSERT INTO users(id,household_id,username,password_hash,display_name,role) VALUES('sibling','home','sibling','unused','Sibling','child')")
        self.con.execute("INSERT INTO items(id,household_id,kind,title,assigned_to,created_by) VALUES('sibling-task','home','task','Sibling task','sibling','parent')")
        self.con.commit()
        with self.assertRaises(PermissionError):
            s.complete_item(self.con,"sibling-task","home","child","child")

    def test_calendar_event_is_not_a_completable_task(self):
        s=self.service
        self.con.execute("INSERT INTO items(id,household_id,kind,title,created_by) VALUES('event','home','event','Birthday','parent')")
        self.con.commit()
        with self.assertRaises(PermissionError):
            s.complete_item(self.con,"event","home","parent","owner")

    def test_read_only_display_cannot_complete_item(self):
        s=self.service
        self.con.execute("INSERT INTO items(id,household_id,kind,title,created_by) VALUES('display-task','home','task','Stay read-only','parent')")
        self.con.commit()
        with self.assertRaises(PermissionError):
            s.complete_item(self.con,"display-task","home","other-user","display")

    def test_only_owner_can_create_an_administrator(self):
        s=self.service
        self.assertTrue(s.can_create_member("owner", "admin"))
        self.assertFalse(s.can_create_member("admin", "admin"))
        self.assertFalse(s.can_create_member("adult", "adult"))
        self.assertFalse(s.can_create_member("child", "child"))
        self.assertFalse(s.can_create_member("display", "child"))

    def test_child_and_display_creation_permissions_are_limited(self):
        s=self.service
        self.assertTrue(s.can_create_item("child", "task"))
        self.assertTrue(s.can_create_item("child", "shopping"))
        self.assertFalse(s.can_create_item("child", "reward"))
        self.assertFalse(s.can_create_item("child", "event"))
        self.assertFalse(s.can_create_item("display", "task"))

    def test_completion_rejects_a_stale_entity_version(self):
        s=self.service
        self.con.execute("INSERT INTO items(id,household_id,kind,title,created_by) VALUES('versioned','home','task','Versioned task','parent')")
        self.con.commit()
        with self.assertRaises(s.ConflictError):
            s.complete_item(self.con,"versioned","home","parent","owner",expected_version=0)

    def test_mutation_receipts_reject_reuse_of_an_operation_id(self):
        self.con.execute("INSERT INTO items(id,household_id,kind,title,created_by) VALUES('receipt-item','home','task','Receipt task','parent')")
        values=("home","operation-1","parent","item.complete","receipt-item",2)
        self.con.execute("INSERT INTO mutation_receipts(household_id,mutation_id,actor_id,operation,entity_id,result_version) VALUES(?,?,?,?,?,?)", values)
        with self.assertRaises(sqlite3.IntegrityError):
            self.con.execute("INSERT INTO mutation_receipts(household_id,mutation_id,actor_id,operation,entity_id,result_version) VALUES(?,?,?,?,?,?)", values)

    def test_mutation_identifiers_must_be_canonical_uuids(self):
        self.assertTrue(self.service.valid_mutation_id("123e4567-e89b-12d3-a456-426614174000"))
        self.assertFalse(self.service.valid_mutation_id("same-id"))
        self.assertFalse(self.service.valid_mutation_id("123E4567-E89B-12D3-A456-426614174000"))

    def test_expired_or_disabled_sessions_are_rejected(self):
        s=self.service
        self.con.execute("INSERT INTO sessions(id_hash,user_id,csrf_hash,expires_at) VALUES('active-hash','parent','csrf','2999-01-01T00:00:00+00:00')")
        self.con.execute("INSERT INTO sessions(id_hash,user_id,csrf_hash,expires_at) VALUES('expired-hash','parent','csrf','2000-01-01T00:00:00+00:00')")
        self.con.commit()
        self.assertIsNotNone(s.lookup_session(self.con,"active-hash"))
        self.assertIsNone(s.lookup_session(self.con,"expired-hash"))
        self.con.execute("UPDATE users SET disabled_at='2026-11-27T00:00:00+00:00' WHERE id='parent'")
        self.con.commit()
        self.assertIsNone(s.lookup_session(self.con,"active-hash"))

    def test_migrations_are_recorded_and_preserve_alpha_records(self):
        s=self.service
        original_dir, original_path=s.DATA_DIR, s.DB_PATH
        with tempfile.TemporaryDirectory(prefix="hs-alpha-upgrade-") as temp:
            try:
                s.DATA_DIR=Path(temp)/"data"
                s.DATA_DIR.mkdir()
                s.DB_PATH=s.DATA_DIR/"household.sqlite3"
                legacy=s.connect()
                legacy.executescript((Path(__file__).resolve().parents[1]/"migrations/001_initial.sql").read_text())
                legacy.execute("INSERT INTO households(id,name,timezone) VALUES('legacy-home','Old Home','America/Chicago')")
                legacy.execute("INSERT INTO users(id,household_id,username,password_hash,display_name,role) VALUES('legacy-parent','legacy-home','parent','salt.hash','Parent','owner')")
                legacy.execute("INSERT INTO users(id,household_id,username,password_hash,display_name,role) VALUES('legacy-child','legacy-home','child','child-hash','Child','child')")
                legacy.execute("INSERT INTO items(id,household_id,kind,title,assigned_to,value,created_by,created_at) VALUES('legacy-task','legacy-home','task','Keep this task','legacy-child',3,'legacy-parent','2020-01-02 03:04:05')")
                legacy.execute("INSERT INTO points_ledger(id,household_id,member_id,item_id,amount,reason) VALUES('legacy-ledger','legacy-home','legacy-child','legacy-task',3,'task.complete')")
                legacy.commit()
                legacy.close()

                s.migrate()
                upgraded=s.connect()
                self.assertEqual(upgraded.execute("SELECT password_hash FROM users WHERE id='legacy-parent'").fetchone()[0], "salt.hash")
                task=upgraded.execute("SELECT assigned_to,created_at FROM items WHERE id='legacy-task'").fetchone()
                self.assertEqual((task["assigned_to"],task["created_at"]), ("legacy-child", "2020-01-02 03:04:05"))
                ledger=upgraded.execute("SELECT id,amount FROM points_ledger WHERE id='legacy-ledger'").fetchone()
                self.assertEqual((ledger["id"],ledger["amount"]), ("legacy-ledger",3))
                versions={row[0] for row in upgraded.execute("SELECT version FROM schema_migrations")}
                self.assertEqual(versions, {1, 2})
                self.assertIn("disabled_at", {row[1] for row in upgraded.execute("PRAGMA table_info(users)")})
                upgraded.close()
            finally:
                s.DATA_DIR, s.DB_PATH=original_dir, original_path

    def test_event_hub_only_notifies_subscribers_in_that_household(self):
        s=self.service
        mine=s.EVENTS.subscribe("home")
        theirs=s.EVENTS.subscribe("other")
        s.EVENTS.publish("home",{"kind":"task","id":"one","action":"created"})
        self.assertEqual(mine.get_nowait(),'{"kind":"task","id":"one","action":"created"}')
        self.assertTrue(theirs.empty())
        s.EVENTS.unsubscribe("home",mine)
        s.EVENTS.unsubscribe("other",theirs)


if __name__ == "__main__":
    unittest.main()
