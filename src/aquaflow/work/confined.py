from dataclasses import dataclass
from datetime import datetime
@dataclass(frozen=True)
class Permit:
    starts:datetime;ends:datetime;gas_test:datetime;attendant:str;entrant:str;rescue:str
def problems(p:Permit,at:datetime,max_age_min:int):
    # Machine-readable denial reasons; never carries personnel identities.
    out=[]
    if p.attendant==p.entrant:out.append("roles_not_separated")
    if not p.rescue:out.append("missing_rescue_contact")
    if not p.starts<=at<p.ends:out.append("outside_permit_window")
    age=(at-p.gas_test).total_seconds()/60
    if age<0:out.append("gas_test_in_future")
    elif age>max_age_min:out.append("gas_test_expired")
    return out
def valid(p:Permit,at:datetime,max_age_min:int):
    return not problems(p,at,max_age_min)
