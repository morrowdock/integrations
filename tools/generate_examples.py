"""Regenerate authored synthetic fixtures without SDK dependencies."""
import copy
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1] / "contract/examples"
STAMP = "2026-11-14T12:00:00Z"
base = dict(schema="morrowdock.agent-item/v1", schemaVersion="1.0.0-draft.1",
            id="00000000-0000-4000-8000-000000000001", kind="material", synthetic=True,
            syntheticScope={"scope": "fixture-only", "realAcademicFacts": False},
            course={"code": "TEST 101"}, title="Synthetic fixture", summary="Authored test data only.",
            source={"channel": "manual", "origin": "own", "retrievedAt": STAMP, "timeZone": "UTC"},
            verification={"/title": {"status": "verified", "method": "fixture", "checkedAt": STAMP}},
            coverage={"status": "partial", "note": "Fixture only"}, version=1, createdAt=STAMP)
manifest = []
for i, kind in enumerate(["material", "assignment", "exam", "ai-draft", "verified-submission", "answer"], 1):
    item = copy.deepcopy(base)
    item.update(kind=kind, id=f"00000000-0000-4000-8000-{i:012d}")
    if kind in ("assignment", "exam"):
        item["dates"] = {"due": STAMP, "availableUntil": "2026-11-15T12:00:00Z", "timeZone": "UTC"}
        for field in ("due", "availableUntil"):
            item["verification"][f"/dates/{field}"] = copy.deepcopy(item["verification"]["/title"])
    if kind in ("ai-draft", "verified-submission"):
        item["state"] = {"submission": "draft" if kind == "ai-draft" else "submitted"}
        item["verification"]["/state/submission"] = copy.deepcopy(item["verification"]["/title"])
    if kind == "answer":
        item["inReplyTo"] = "00000000-0000-4000-8000-000000000099"
    name = f"valid/{kind}.json"
    (ROOT / name).write_text(json.dumps(item, indent=2) + "\n")
    manifest.append({"file": name, "valid": True})
    bad = copy.deepcopy(item)
    if i == 1:
        del bad["syntheticScope"]
        error = "required: syntheticScope"
    elif i == 2:
        bad["dates"]["due"] = "tomorrow"
        error = "pattern: /dates/due"
    elif i == 3:
        bad["verification"]["/title"]["method"] = "agent-inference"
        error = "const: synthetic verification method must be fixture"
    elif i == 4:
        bad["state"]["submission"] = "submitted"
        error = "enum: ai-draft cannot be submitted"
    elif i == 5:
        bad["state"]["submission"] = "draft"
        error = "enum: verified-submission must be submitted or graded"
    else:
        del bad["inReplyTo"]
        error = "required: answer needs inReplyTo"
    name = f"invalid/{kind}.json"
    (ROOT / name).write_text(json.dumps(bad, indent=2) + "\n")
    manifest.append({"file": name, "valid": False, "expectedError": error})
(ROOT / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
