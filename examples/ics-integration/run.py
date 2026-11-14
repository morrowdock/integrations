"""Strict synthetic ICS subset: UTC VEVENTs, no recurrence or external fetches."""
import argparse
import os
from datetime import datetime
from pathlib import Path
from morrowdock_integrations import build_item, provenance, verification
from morrowdock_integrations.client import Client


def stamp(value):
    return datetime.strptime(value, "%Y%m%dT%H%M%SZ").strftime("%Y-%m-%dT%H:%M:%SZ")


def parse(text):
    lines = text.replace("\r\n", "\n").strip().splitlines()
    if lines[:3] != ["BEGIN:VCALENDAR", "VERSION:2.0", "X-MORROWDOCK-SYNTHETIC:TRUE"] or lines[-1] != "END:VCALENDAR":
        raise ValueError("Requires the synthetic calendar subset")
    event = None
    for line in lines[3:-1]:
        if line == "BEGIN:VEVENT" and event is None:
            event = {}
        elif line == "END:VEVENT" and event is not None:
            if not {"UID", "SUMMARY", "DTSTART", "CATEGORIES"} <= event.keys():
                raise ValueError("Incomplete event")
            kind = event["CATEGORIES"].lower()
            if kind not in ("exam", "assignment"):
                raise ValueError("Unsupported event category")
            dates = {"timeZone": "UTC", "start": stamp(event["DTSTART"])}
            for source, target in [("DTEND", "end"), ("X-MORROWDOCK-DUE", "due"),
                                   ("X-MORROWDOCK-AVAILABLE-UNTIL", "availableUntil")]:
                if source in event:
                    dates[target] = stamp(event[source])
            yield build_item(kind=kind, course="TEST 101", title=event["SUMMARY"],
                             summary="Synthetic calendar fixture.", synthetic=True,
                             source=provenance("ics"), dates=dates,
                             verification={"/title": verification("verified", "fixture"),
                                           "/kind": verification("verified", "fixture"),
                                           **{f"/dates/{key}": verification("verified", "fixture") for key in dates}})
            event = None
        else:
            key, sep, value = line.partition(":")
            if event is None or not sep or key in event or key not in {
                "UID", "SUMMARY", "DTSTART", "DTEND", "CATEGORIES", "X-MORROWDOCK-DUE", "X-MORROWDOCK-AVAILABLE-UNTIL"
            }:
                raise ValueError("Unsupported ICS feature; no silent time or recurrence conversion")
            event[key] = value
    if event is not None:
        raise ValueError("Unclosed event")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("file", type=Path)
    args = parser.parse_args()
    items = list(parse(args.file.read_text()))
    client = Client(os.environ["MORROWDOCK_BASE_URL"])
    for item in items:
        client.send(item)
