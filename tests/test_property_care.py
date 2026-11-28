"""Scoped maintenance and vehicle service records."""
import importlib
import tempfile
import unittest
from pathlib import Path

from app import database


class PropertyCareTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.care = importlib.import_module("app.property_care")

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="household-six-property-care-")
        self.path = Path(self.temp.name) / "household.sqlite3"
        database.migrate(self.path)
        self.engine = database.engine(self.path)
        with self.engine.begin() as con:
            con.exec_driver_sql("INSERT INTO households(id,name) VALUES('home','Home'),('other','Other')")
            con.exec_driver_sql("""INSERT INTO users(id,household_id,username,password_hash,display_name,role)
                VALUES('owner','home','owner','unused','Owner','owner'),
                      ('child','home','child','unused','Child','child'),
                      ('foreign','other','foreign','unused','Foreign','owner')""")

    def tearDown(self):
        database.engine.cache_clear()
        self.temp.cleanup()

    def actor(self, member="owner"):
        with self.engine.connect() as con:
            return dict(con.exec_driver_sql(
                "SELECT id,household_id,role FROM users WHERE id=?", (member,),
            ).mappings().one())

    def mutation(self, suffix, **fields):
        return {"mutationId": f"123e4567-e89b-42d3-a456-{suffix:012d}", **fields}

    def test_templates_are_inert_until_adult_creates_a_schedule(self):
        templates = self.care.maintenance_templates()
        self.assertTrue({"HVAC filter", "Smoke detector", "Lawn maintenance", "Gutters",
                         "Water filter", "Generator", "Septic system"}.issubset(
                             {template["title"] for template in templates}))
        self.assertEqual(self.care.load(self.engine, self.actor())["schedules"], [])
        with self.assertRaises(self.care.DomainError) as denied:
            self.care.write(self.engine, self.actor("child"), "maintenance.create", None,
                            self.mutation(1, title="Filter", category="hvac", dueOn="2026-12-01"))
        self.assertEqual(denied.exception.status, 403)

    def test_maintenance_schedule_completion_keeps_scoped_history(self):
        created = self.care.write(self.engine, self.actor(), "maintenance.create", None,
            self.mutation(2, title="HVAC filter", category="hvac", dueOn="2026-12-01",
                          frequency="monthly", intervalCount=3, assignedTo="child", estimatedCostCents=0,
                          instructions="Use 16x25x1", notes="Upstairs return"))
        schedule_id = created[1]["id"]
        self.assertEqual(created[1]["dueOn"], "2026-12-01")
        completed = self.care.write(self.engine, self.actor(), "maintenance.complete", schedule_id,
            self.mutation(3, expectedVersion=1, performedOn="2026-12-01", costCents=2400,
                          notes="Changed filter"))
        self.assertEqual(completed[1]["dueOn"], "2027-03-01")
        self.assertEqual(self.care.load(self.engine, self.actor())["history"][0]["costCents"], 2400)
        self.assertEqual(self.care.load(self.engine, self.actor("child"))["schedules"][0]["assignedTo"], "child")
        with self.assertRaises(self.care.DomainError) as foreign:
            self.care.write(self.engine, self.actor("foreign"), "maintenance.complete", schedule_id,
                            self.mutation(4, expectedVersion=2, performedOn="2027-03-01", costCents=0))
        self.assertEqual(foreign.exception.status, 404)

    def test_vehicle_service_records_validate_and_advance_odometer_schedules(self):
        vehicle = self.care.write(self.engine, self.actor(), "vehicle.create", None,
            self.mutation(5, make="Toyota", model="Prius", year=2022, fuel="hybrid",
                          odometer=28000, nickname="Blue car"))[1]
        service = self.care.write(self.engine, self.actor(), "vehicle.service.create", None,
            self.mutation(6, vehicleId=vehicle["id"], serviceType="Tire rotation",
                          performedOn="2026-11-27", odometer=28000, dueOdometer=33000,
                          intervalMiles=5000, costCents=7500, notes="Rotate and inspect"))[1]
        self.assertEqual(service["dueOdometer"], 33000)
        self.assertEqual(self.care.load(self.engine, self.actor())["vehicles"][0]["odometer"], 28000)
        with self.assertRaises(self.care.DomainError):
            self.care.write(self.engine, self.actor(), "vehicle.service.create", None,
                self.mutation(7, vehicleId=vehicle["id"], serviceType="Battery", performedOn="2026-11-26",
                              odometer=27000, costCents=0))

    def test_one_time_completion_is_durable_and_idempotent_after_schedule_closes(self):
        schedule = self.care.write(self.engine, self.actor(), "maintenance.create", None,
            self.mutation(8, title="Replace smoke alarm battery", category="safety", dueOn="2026-12-01",
                          frequency="once"))[1]
        request = self.mutation(9, expectedVersion=1, performedOn="2026-12-01", costCents=1200)
        first = self.care.write(self.engine, self.actor(), "maintenance.complete", schedule["id"], request)
        replay = self.care.write(self.engine, self.actor(), "maintenance.complete", schedule["id"], request)
        self.assertEqual(first[1], replay[1])
        self.assertFalse(first[1]["active"])
        self.assertEqual(self.care.load(self.engine, self.actor())["schedules"], [])


if __name__ == "__main__":
    unittest.main()
