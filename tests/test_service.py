"""Dependency-free domain and persistence tests (socket use is sandbox-blocked)."""
import os
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

    def test_read_only_display_cannot_complete_item(self):
        s=self.service
        self.con.execute("INSERT INTO items(id,household_id,kind,title,created_by) VALUES('display-task','home','task','Stay read-only','parent')")
        self.con.commit()
        with self.assertRaises(PermissionError):
            s.complete_item(self.con,"display-task","home","other-user","display")

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
