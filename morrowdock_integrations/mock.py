"""Loopback-only, in-memory synthetic relay. Not a production service."""
import argparse
import hashlib
import hmac
import json
import os
from http.server import BaseHTTPRequestHandler, HTTPServer
from uuid import uuid4
from . import validate, now, VERSION, SCHEMAS
from jsonschema import Draft202012Validator

MAX_BODY = 26214400


def make_server(token, port=0):
    request_id = str(uuid4())
    seed = dict(schema="morrowdock.agent-request/v1", schemaVersion=VERSION,
                id=request_id, kind="fetch", ask="Fetch the synthetic TEST 101 fixture.",
                course={"code": "TEST 101"}, synthetic=True,
                syntheticScope={"scope": "fixture-only", "realAcademicFacts": False},
                createdBy="app", createdAt=now(), expiresAt="2099-01-01T00:00:00Z", status="open")
    validate(seed)
    items, uploads, requests = {}, {}, {request_id: seed}
    attachment_schema = SCHEMAS["morrowdock.agent-item/v1"].schema["properties"]["attachments"]["items"]

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass  # Never log credentials, paths, or content.

        def reply(self, code, value):
            data = json.dumps(value).encode()
            self.send_response(code)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

        def dispatch(self):
            if not hmac.compare_digest(self.headers.get("Authorization", "").encode(),
                                       ("Bearer " + token).encode()):
                return self.reply(401, {"error": "unauthorized"})
            try:
                length = int(self.headers.get("Content-Length", "0"))
                if length < 0 or length > MAX_BODY:
                    return self.reply(413, {"error": "body too large"})
                body = self.rfile.read(length)
                if self.command == "GET" and self.path == "/v1/status":
                    return self.reply(200, {"status": "ok", "items": len(items), "mock": True})
                if self.command == "GET" and self.path == "/v1/requests?status=open":
                    return self.reply(200, {"requests": [r for r in requests.values() if r["status"] == "open"]})
                if self.command == "PUT" and self.path.startswith("/v1/uploads/"):
                    uid = self.path.removeprefix("/v1/uploads/")
                    if uid not in uploads:
                        return self.reply(404, {"error": "unknown upload"})
                    meta = uploads[uid]["metadata"]
                    if len(body) != meta["size"] or hashlib.sha256(body).hexdigest() != meta["sha256"]:
                        raise ValueError()
                    uploads[uid]["data"] = body
                    return self.reply(200, {"uploadId": uid})
                if self.command != "POST":
                    return self.reply(404, {"error": "unknown route"})
                data = json.loads(body)
                if self.path == "/v1/uploads":
                    uid = uuid4().hex
                    Draft202012Validator(attachment_schema).validate(dict(data, uploadId=uid))
                    uploads[uid] = {"metadata": data, "data": None}
                    return self.reply(201, {"uploadId": uid, "putPath": "/v1/uploads/" + uid})
                answer_id = None
                if self.path.startswith("/v1/requests/") and self.path.endswith("/answer"):
                    answer_id = self.path.split("/")[3]
                    if answer_id not in requests:
                        return self.reply(404, {"error": "unknown request"})
                    if requests[answer_id]["status"] != "open":
                        return self.reply(409, {"error": "request not open"})
                    if data.get("kind") != "answer" or data.get("inReplyTo") != answer_id:
                        raise ValueError()
                elif self.path != "/v1/items":
                    return self.reply(404, {"error": "unknown route"})
                validate(data)
                if data["schema"] != "morrowdock.agent-item/v1" or not data["synthetic"]:
                    raise ValueError()
                for attachment in data.get("attachments", []):
                    uploaded = uploads.get(attachment["uploadId"])
                    if (not uploaded or uploaded["data"] is None or
                        uploaded["metadata"] != {k: v for k, v in attachment.items() if k != "uploadId"}):
                        raise ValueError()
                if data["id"] in items:
                    return self.reply(409, {"error": "duplicate item"})
                items[data["id"]] = data
                if answer_id:
                    requests[answer_id].update(status="answered", answeredBy=[data["id"]])
                    validate(requests[answer_id])
                return self.reply(201, {"id": data["id"]})
            except Exception:
                return self.reply(400, {"error": "invalid request"})

        do_GET = do_POST = do_PUT = dispatch

    server = HTTPServer(("127.0.0.1", port), Handler)
    server.timeout = 5
    return server


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=8765)
    args = parser.parse_args()
    token = os.environ.get("MORROWDOCK_TOKEN")
    if not token:
        parser.error("Set MORROWDOCK_TOKEN to a disposable local value")
    server = make_server(token, args.port)
    print(f"Synthetic mock relay on loopback port {server.server_port}", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
