"""Small contract helpers. Content is always untrusted data."""
import hashlib
import json
from datetime import datetime, timezone
from importlib.resources import files
from uuid import uuid4

from jsonschema import Draft202012Validator

VERSION = "1.0.0-draft.1"
SCHEMAS = {
    f"morrowdock.agent-{kind}/v1": Draft202012Validator(json.loads(
        files(__package__).joinpath(f"schemas/agent-{kind}.v1.schema.json").read_text()))
    for kind in ("item", "request")
}


def validate(value):
    """Raise ValueError for a schema violation; never include content in errors."""
    name = value.get("schema") if isinstance(value, dict) else None
    validator = SCHEMAS.get(name) if isinstance(name, str) else None
    if validator is None:
        raise ValueError("/schema: unknown schema")
    errors = sorted(validator.iter_errors(value), key=lambda e: str(list(e.path)))
    if errors:
        error = errors[0]
        raise ValueError(f"/{'/'.join(map(str, error.path))}: {error.validator}")
    return value


def now():
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def provenance(channel, *, origin="own", time_zone="UTC", retrieved_at=None, **fields):
    return dict(channel=channel, origin=origin, retrievedAt=retrieved_at or now(),
                timeZone=time_zone, **fields)


def verification(status="unknown", method="other", *, checked_at=None, **fields):
    return dict(status=status, method=method, checkedAt=checked_at or now(), **fields)


def coverage(status="unknown", note=None):
    return {"status": status, **({"note": note} if note is not None else {})}


def build_item(*, kind, course, title, summary, source, verification, synthetic, **fields):
    item = dict(schema="morrowdock.agent-item/v1", schemaVersion=VERSION,
                id=str(uuid4()), kind=kind, course={"code": course}, title=title,
                summary=summary, source=source, verification=verification,
                synthetic=synthetic, coverage=coverage(), version=1, createdAt=now())
    if synthetic:
        item["syntheticScope"] = {"scope": "fixture-only", "realAcademicFacts": False}
    item.update(fields)
    return validate(item)


def sha256(path):
    digest = hashlib.sha256()
    with open(path, "rb") as stream:
        for chunk in iter(lambda: stream.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()
