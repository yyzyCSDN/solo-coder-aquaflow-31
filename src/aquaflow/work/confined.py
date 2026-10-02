from dataclasses import dataclass
from datetime import datetime

@dataclass(frozen=True)
class Permit:
    starts:datetime;ends:datetime;gas_test:datetime;attendant:str;entrant:str;rescue:str

# Stable, non-personal reason codes. They must never carry names or other
# personnel identifiers so a denied permit can be explained without leaking
# who was assigned.
RESCUE_CONTACT_REQUIRED="rescue_contact_required"
ROLE_ASSIGNMENT_REQUIRED="role_assignment_required"
ROLE_SEPARATION_VIOLATION="role_separation_violation"
OUTSIDE_PERMIT_WINDOW="outside_permit_window"
GAS_TEST_STALE="gas_test_stale"
GAS_TEST_IN_FUTURE="gas_test_in_future"

def deny_reasons(p:Permit,at:datetime,max_age_min:int)->tuple[str,...]:
    reasons=[]
    if not p.rescue:reasons.append(RESCUE_CONTACT_REQUIRED)
    # Attendant and entrant must be two different, named people.
    if not p.attendant or not p.entrant:
        reasons.append(ROLE_ASSIGNMENT_REQUIRED)
    elif p.attendant==p.entrant:
        reasons.append(ROLE_SEPARATION_VIOLATION)
    if not p.starts<=at<p.ends:reasons.append(OUTSIDE_PERMIT_WINDOW)
    age=(at-p.gas_test).total_seconds()/60
    if age<0:reasons.append(GAS_TEST_IN_FUTURE)
    elif age>max_age_min:reasons.append(GAS_TEST_STALE)
    return tuple(reasons)

def valid(p:Permit,at:datetime,max_age_min:int)->bool:
    return not deny_reasons(p,at,max_age_min)
