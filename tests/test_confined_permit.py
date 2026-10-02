import unittest
from datetime import datetime, timedelta

from aquaflow.work.confined import (
    Permit, valid, deny_reasons,
    ROLE_SEPARATION_VIOLATION, GAS_TEST_STALE,
)
from aquaflow.workflow_rules import evaluate

AT = datetime(2026, 10, 2, 12, 0, 0)
STARTS = AT - timedelta(hours=1)
ENDS = AT + timedelta(hours=1)
GAS_FRESH = AT - timedelta(minutes=15)
GAS_STALE = AT - timedelta(hours=4)
MAX_AGE_MIN = 30


def permit(attendant="Alice", entrant="Bob", rescue="Carol", gas_test=GAS_FRESH,
           starts=STARTS, ends=ENDS):
    return Permit(starts, ends, gas_test, attendant, entrant, rescue)


class ConfinedPermitTests(unittest.TestCase):
    def test_same_attendant_and_entrant_denied(self):
        p = permit(attendant="Alice", entrant="Alice")
        self.assertFalse(valid(p, AT, MAX_AGE_MIN))
        self.assertIn(ROLE_SEPARATION_VIOLATION, deny_reasons(p, AT, MAX_AGE_MIN))

    def test_stale_gas_test_denied_even_with_distinct_roles(self):
        p = permit(gas_test=GAS_STALE)
        self.assertFalse(valid(p, AT, MAX_AGE_MIN))
        self.assertIn(GAS_TEST_STALE, deny_reasons(p, AT, MAX_AGE_MIN))

    def test_three_distinct_roles_valid_permit_accepted(self):
        p = permit(attendant="Alice", entrant="Bob", rescue="Carol")
        self.assertTrue(valid(p, AT, MAX_AGE_MIN))
        self.assertEqual(deny_reasons(p, AT, MAX_AGE_MIN), ())

    def test_denial_reasons_do_not_leak_personnel_information(self):
        p = permit(attendant="Alice", entrant="Alice", gas_test=GAS_STALE)
        result = evaluate("confined_permit", {
            "permit": {
                "starts": STARTS.isoformat(), "ends": ENDS.isoformat(),
                "gas_test": GAS_STALE.isoformat(),
                "attendant": "Alice", "entrant": "Alice", "rescue": "Carol",
            },
            "at": AT.isoformat(), "max_age": MAX_AGE_MIN,
        })
        self.assertEqual(result["decision"], "deny")
        self.assertFalse(result["value"])
        self.assertIn(ROLE_SEPARATION_VIOLATION, result["reasons"])
        self.assertIn(GAS_TEST_STALE, result["reasons"])
        self.assertNotIn("Alice", str(result["reasons"]))
        self.assertNotIn("Carol", str(result["reasons"]))

    def test_valid_permit_workflow_decision(self):
        result = evaluate("confined_permit", {
            "permit": {
                "starts": STARTS.isoformat(), "ends": ENDS.isoformat(),
                "gas_test": GAS_FRESH.isoformat(),
                "attendant": "Alice", "entrant": "Bob", "rescue": "Carol",
            },
            "at": AT.isoformat(), "max_age": MAX_AGE_MIN,
        })
        self.assertEqual(result["decision"], "enter")
        self.assertTrue(result["value"])
        self.assertTrue(result["evidence"]["role_separation"])
        self.assertEqual(result["reasons"], [])


if __name__ == "__main__":
    unittest.main()
