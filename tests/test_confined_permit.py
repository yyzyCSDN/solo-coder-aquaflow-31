import json
import unittest
from datetime import datetime, timezone

from aquaflow.api import AquaFlowService
from aquaflow.work.confined import Permit, problems, valid

STARTS = "2026-10-02T08:00:00+00:00"
ENDS = "2026-10-02T16:00:00+00:00"
GAS_TEST = "2026-10-02T09:30:00+00:00"
AT = "2026-10-02T10:00:00+00:00"


def payload(**permit_overrides):
    permit = {
        "starts": STARTS,
        "ends": ENDS,
        "gas_test": GAS_TEST,
        "attendant": "emp-attendant",
        "entrant": "emp-entrant",
        "rescue": "emp-rescue",
    }
    permit.update(permit_overrides)
    return {"permit": permit, "at": AT, "max_age": 60}


class ConfinedPermitWorkflowTest(unittest.TestCase):
    def setUp(self):
        self.service = AquaFlowService()

    def test_same_person_cannot_hold_attendant_and_entrant_roles(self):
        result = self.service.run_workflow("confined_permit", payload(entrant="emp-attendant"))
        self.assertEqual(result["decision"], "deny")
        self.assertFalse(result["value"])
        self.assertIn("roles_not_separated", result["evidence"]["reasons"])
        self.assertFalse(result["evidence"]["role_separation"])

    def test_denial_is_explainable_without_leaking_personnel(self):
        result = self.service.run_workflow("confined_permit", payload(entrant="emp-attendant"))
        blob = json.dumps(result)
        for identity in ("emp-attendant", "emp-entrant", "emp-rescue"):
            self.assertNotIn(identity, blob)

    def test_expired_gas_test_denies_entry(self):
        stale = payload(gas_test="2026-10-02T07:00:00+00:00")  # 180 min old > 60
        result = self.service.run_workflow("confined_permit", stale)
        self.assertEqual(result["decision"], "deny")
        self.assertEqual(result["evidence"]["reasons"], ["gas_test_expired"])

    def test_future_gas_test_denies_entry(self):
        future = payload(gas_test="2026-10-02T10:15:00+00:00")
        result = self.service.run_workflow("confined_permit", future)
        self.assertEqual(result["decision"], "deny")
        self.assertIn("gas_test_in_future", result["evidence"]["reasons"])

    def test_outside_permit_window_denies_entry(self):
        early = payload()
        early["at"] = "2026-10-02T07:59:00+00:00"
        result = self.service.run_workflow("confined_permit", early)
        self.assertEqual(result["decision"], "deny")
        self.assertIn("outside_permit_window", result["evidence"]["reasons"])

    def test_missing_rescue_contact_denies_entry(self):
        result = self.service.run_workflow("confined_permit", payload(rescue=""))
        self.assertEqual(result["decision"], "deny")
        self.assertIn("missing_rescue_contact", result["evidence"]["reasons"])

    def test_distinct_roles_valid_window_and_fresh_gas_allows_entry(self):
        result = self.service.run_workflow("confined_permit", payload())
        self.assertEqual(result["decision"], "enter")
        self.assertTrue(result["value"])
        self.assertEqual(result["evidence"]["reasons"], [])
        self.assertTrue(result["evidence"]["role_separation"])


class ConfinedPermitRuleTest(unittest.TestCase):
    def permit(self, **overrides):
        values = {
            "starts": datetime(2026, 10, 2, 8, tzinfo=timezone.utc),
            "ends": datetime(2026, 10, 2, 16, tzinfo=timezone.utc),
            "gas_test": datetime(2026, 10, 2, 9, 30, tzinfo=timezone.utc),
            "attendant": "a",
            "entrant": "b",
            "rescue": "c",
        }
        values.update(overrides)
        return Permit(**values)

    def test_valid_enforces_role_separation(self):
        at = datetime(2026, 10, 2, 10, tzinfo=timezone.utc)
        self.assertFalse(valid(self.permit(entrant="a"), at, 60))
        self.assertTrue(valid(self.permit(), at, 60))

    def test_problems_reports_every_violation(self):
        at = datetime(2026, 10, 2, 17, tzinfo=timezone.utc)
        permit = self.permit(entrant="a", rescue="", gas_test=datetime(2026, 10, 2, 6, tzinfo=timezone.utc))
        self.assertEqual(
            problems(permit, at, 60),
            ["roles_not_separated", "missing_rescue_contact", "outside_permit_window", "gas_test_expired"],
        )

    def test_gas_test_age_boundary_is_inclusive(self):
        at = datetime(2026, 10, 2, 10, 30, tzinfo=timezone.utc)  # exactly 60 min
        self.assertTrue(valid(self.permit(), at, 60))
        self.assertFalse(valid(self.permit(), at, 59))


if __name__ == "__main__":
    unittest.main()
