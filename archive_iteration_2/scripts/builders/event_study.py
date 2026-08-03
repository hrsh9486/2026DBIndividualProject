"""Build the named event-study contract."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Mapping, Sequence


def build_event_study_payload(
    events: Sequence[Mapping],
    *,
    sources: Sequence[Mapping[str, str]],
    methodology: str,
    note: str | None = None,
) -> dict:
    event_ids = [event["event_id"] for event in events]
    if len(event_ids) != len(set(event_ids)):
        raise ValueError("Event IDs must be unique")
    for event in events:
        if event["start_date"] > event["end_date"]:
            raise ValueError(f"Event {event['event_id']} ends before it starts")
    metadata = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source": [dict(source) for source in sources],
        "methodology": methodology,
        "event_order": event_ids,
    }
    if note:
        metadata["note"] = note
    return {"metadata": metadata, "events": [dict(event) for event in events]}
