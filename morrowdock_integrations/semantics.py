"""Stateless semantic checks applied only after JSON Schema validation."""
import re
from datetime import datetime
from functools import lru_cache
from zoneinfo import available_timezones

# RFC 3339 profile: explicit seconds and offset, no leap-second representation.
STAMP = re.compile(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d{1,6})?(?:Z|[+-]\d{2}:\d{2})", re.ASCII)


@lru_cache(maxsize=1)
def time_zones():
    return available_timezones() | {"UTC"}


def check_fields(value, schema):
    """Walk schema-declared fields, so text resembling a date is not interpreted."""
    reference = schema.get("$ref")
    if reference == "#/$defs/dateTime":
        if not STAMP.fullmatch(value):
            raise ValueError("semantic: invalid RFC 3339 dateTime")
        if int(value[11:13]) > 23 or int(value[14:16]) > 59 or int(value[17:19]) > 59:
            raise ValueError("semantic: invalid clock time")
        if value[-1] != "Z" and (int(value[-5:-3]) > 23 or int(value[-2:]) > 59):
            raise ValueError("semantic: invalid UTC offset")
        try:
            datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            raise ValueError("semantic: invalid calendar dateTime") from None
    if reference == "#/$defs/timeZone" and value not in time_zones():
        raise ValueError("semantic: unknown IANA timeZone")
    if isinstance(value, dict):
        for key, child in value.items():
            child_schema = schema.get("properties", {}).get(key, schema.get("additionalProperties", {}))
            if isinstance(child_schema, dict):
                check_fields(child, child_schema)
    elif isinstance(value, list) and isinstance(schema.get("items"), dict):
        for child in value:
            check_fields(child, schema["items"])


def resolves(item, pointer):
    current = item
    # The unchanged schema limits pointer segments; decode for JSON Pointer semantics.
    for segment in pointer.split("/")[1:]:
        key = segment.replace("~1", "/").replace("~0", "~")
        if isinstance(current, dict) and key in current:
            current = current[key]
        elif isinstance(current, list) and re.fullmatch(r"0|[1-9][0-9]*", key) and int(key) < len(current):
            current = current[int(key)]
        else:
            return False
    return True


def validate_semantics(value, schema):
    check_fields(value, schema)
    for pointer in value.get("verification", {}):
        if not resolves(value, pointer):
            raise ValueError("semantic: verification pointer does not resolve")
    if value.get("status") == "answered" and not value["answeredBy"]:
        raise ValueError("semantic: answered request needs at least one answer")
