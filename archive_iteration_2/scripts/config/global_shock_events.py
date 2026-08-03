"""Pre-registered market shock windows; never selected after inspecting results."""

from dataclasses import dataclass
from datetime import date


@dataclass(frozen=True, slots=True)
class ShockEvent:
    event_id: str
    label: str
    start_date: date
    end_date: date
    rationale: str


GLOBAL_SHOCK_EVENTS = (
    ShockEvent("em-selloff-2018", "2018 emerging-market sell-off", date(2018, 2, 1), date(2018, 10, 31), "Global dollar strength and risk reduction across emerging markets."),
    ShockEvent("covid-2020", "COVID-19 global market shock", date(2020, 2, 19), date(2020, 3, 23), "Peak-to-trough global pandemic sell-off window."),
    ShockEvent("global-tightening-2022", "2022 global monetary tightening", date(2022, 1, 3), date(2022, 6, 17), "Rapid global rate repricing and portfolio outflows."),
)
