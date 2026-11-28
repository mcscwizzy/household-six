"""Household account authorization and session lifecycle regression tests."""
import importlib
import importlib.util
import tempfile
import unittest
from pathlib import Path

from app import database


class AccountAdministrationTest(unittest.TestCase):
    OWNER_SESSION = "11111111-1111-4111-8111-111111111111"
    CHILD_SESSION = "22222222-2222-4222-8222-222222222222"
    FOREIGN_SESSION = "33333333-3333-4333-8333-333333333333"

    @classmethod
    def setUpClass(cls):
        cls.permissions_spec = importlib.util.find_spec("app.permissions")
        cls.accounts_spec = importlib.util.find_spec("app.accounts")

    def test_permission_matrix_is_explicit_for_every_household_role(self):
        self.assertIsNotNone(self.permissions_spec, "the role permission matrix is not implemented")
        permissions = importlib.import_module("app.permissions")
        roles = {"owner", "admin", "adult", "child", "display"}
        self.assertEqual(set(permissions.ROLE_PERMISSIONS), roles)
        self.assertTrue(all(permissions.allowed(role, "calendar.read") for role in roles))
        self.assertTrue(all(permissions.allowed(role, "display.read") for role in roles))
        self.assertTrue(all(permissions.allowed(role, "calendar.write") for role in {"owner", "admin", "adult"}))
        self.assertFalse(permissions.allowed("child", "calendar.write"))
        self.assertTrue(permissions.allowed("child", "chore.complete.assigned"))
        self.assertTrue(permissions.allowed("child", "shopping.write"))
        self.assertTrue(permissions.allowed("child", "allowance.read"))
        self.assertFalse(permissions.allowed("child", "vehicles.read"))
        self.assertFalse(permissions.allowed("child", "budget.read"))
        self.assertFalse(permissions.allowed("display", "private.document.read"))
        self.assertFalse(permissions.allowed("unknown", "calendar.read"))

    def setUp(self):
        self.accounts = importlib.import_module("app.accounts") if self.accounts_spec else None
        self.temp = tempfile.TemporaryDirectory(prefix="household-six-accounts-")
        self.path = Path(self.temp.name) / "household.sqlite3"
        database.migrate(self.path)
        self.engine = database.engine(self.path)
        with self.engine.begin() as con:
            con.exec_driver_sql("INSERT INTO households(id,name) VALUES('home','Home')")
            con.exec_driver_sql("INSERT INTO households(id,name) VALUES('other','Other')")
            con.exec_driver_sql("""INSERT INTO users(id,household_id,username,password_hash,display_name,role)
                VALUES('owner','home','owner','old-owner-hash','Owner','owner'),
                      ('admin','home','admin','old-admin-hash','Admin','admin'),
                      ('adult','home','adult','old-adult-hash','Adult','adult'),
                      ('child','home','child','old-child-hash','Child','child'),
                      ('sibling','home','sibling','sibling-hash','Sibling','child'),
                      ('foreign','other','foreign','foreign-hash','Foreign','owner')""")
            con.exec_driver_sql("""INSERT INTO sessions(id_hash,device_id,user_id,csrf_hash,expires_at)
                VALUES(?,?,?,?, '2999-01-01'),(?,?,?,?, '2999-01-01'),(?,?,?,?, '2999-01-01')""",
                ("a" * 64, self.OWNER_SESSION, "owner", "csrf", "b" * 64, self.CHILD_SESSION, "child", "csrf",
                 "c" * 64, self.FOREIGN_SESSION, "foreign", "csrf"))

    def tearDown(self):
        database.engine.cache_clear()
        self.temp.cleanup()

    def actor(self, member="owner"):
        with self.engine.connect() as con:
            row = con.exec_driver_sql("SELECT id,household_id,role FROM users WHERE id=?", (member,)).mappings().one()
        return dict(row)

    def test_profile_edits_are_household_scoped_and_cannot_change_roles(self):
        profile = self.accounts.update_profile(self.engine, self.actor(), "child", {
            "displayName": "Sam", "color": "#54768C", "avatar": "fox",
        })
        self.assertEqual((profile["displayName"], profile["color"], profile["avatar"]), ("Sam", "#54768C", "fox"))
        with self.assertRaises(self.accounts.DomainError) as denied:
            self.accounts.update_profile(self.engine, self.actor("admin"), "owner", {"displayName": "Changed"})
        self.assertEqual(denied.exception.status, 403)
        with self.assertRaises(self.accounts.DomainError) as foreign:
            self.accounts.update_profile(self.engine, self.actor(), "foreign", {"displayName": "Changed"})
        self.assertEqual(foreign.exception.status, 404)
        with self.assertRaises(self.accounts.DomainError):
            self.accounts.update_profile(self.engine, self.actor(), "child", {"role": "admin"})

    def test_disable_revokes_sessions_and_reactivation_does_not_restore_them(self):
        self.accounts.set_disabled(self.engine, self.actor("admin"), "child", True)
        with self.engine.connect() as con:
            disabled = con.exec_driver_sql("SELECT disabled_at FROM users WHERE id='child'").scalar_one()
            sessions = con.exec_driver_sql("SELECT COUNT(*) FROM sessions WHERE user_id='child'").scalar_one()
        self.assertIsNotNone(disabled)
        self.assertEqual(sessions, 0)
        self.accounts.set_disabled(self.engine, self.actor(), "child", False)
        with self.engine.connect() as con:
            self.assertIsNone(con.exec_driver_sql("SELECT disabled_at FROM users WHERE id='child'").scalar_one())
            self.assertEqual(con.exec_driver_sql("SELECT COUNT(*) FROM sessions WHERE user_id='child'").scalar_one(), 0)

    def test_administrator_cannot_disable_an_owner_or_another_administrator(self):
        for target in ("owner", "admin"):
            with self.subTest(target=target), self.assertRaises(self.accounts.DomainError) as denied:
                self.accounts.set_disabled(self.engine, self.actor("admin"), target, True)
            self.assertEqual(denied.exception.status, 403)

    def test_administrator_password_reset_revokes_only_target_sessions(self):
        self.accounts.reset_password(self.engine, self.actor("admin"), "child", "new-child-passphrase")
        with self.engine.connect() as con:
            child_hash = con.exec_driver_sql("SELECT password_hash FROM users WHERE id='child'").scalar_one()
            child_sessions = con.exec_driver_sql("SELECT COUNT(*) FROM sessions WHERE user_id='child'").scalar_one()
            owner_sessions = con.exec_driver_sql("SELECT COUNT(*) FROM sessions WHERE user_id='owner'").scalar_one()
        from app.security import verify_password
        self.assertTrue(verify_password("new-child-passphrase", child_hash))
        self.assertEqual((child_sessions, owner_sessions), (0, 1))

    def test_administrator_cannot_reset_owner_or_administrator_password(self):
        for target in ("owner", "admin"):
            with self.subTest(target=target), self.assertRaises(self.accounts.DomainError) as denied:
                self.accounts.reset_password(self.engine, self.actor("admin"), target, "new-long-passphrase")
            self.assertEqual(denied.exception.status, 403)

    def test_session_list_and_revocation_are_household_scoped(self):
        sessions = self.accounts.list_sessions(self.engine, self.actor("child"))
        self.assertEqual([session["id"] for session in sessions], [self.CHILD_SESSION])
        with self.assertRaises(self.accounts.DomainError) as foreign:
            self.accounts.revoke_session(self.engine, self.actor("child"), self.FOREIGN_SESSION)
        self.assertEqual(foreign.exception.status, 404)
        self.accounts.revoke_session(self.engine, self.actor("child"), self.CHILD_SESSION)
        with self.engine.connect() as con:
            self.assertEqual(con.exec_driver_sql("SELECT COUNT(*) FROM sessions WHERE device_id=?", (self.CHILD_SESSION,)).scalar_one(), 0)
            self.assertEqual(con.exec_driver_sql("SELECT COUNT(*) FROM sessions WHERE device_id=?", (self.FOREIGN_SESSION,)).scalar_one(), 1)


if __name__ == "__main__":
    unittest.main()
