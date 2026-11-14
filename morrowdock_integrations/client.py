"""REST client. No implicit host, redirects, retries, or credential logging."""
import json
import os
from urllib.parse import urlsplit, quote
from urllib.request import Request, build_opener, HTTPRedirectHandler
from urllib.error import URLError
from . import validate, sha256
from pathlib import Path


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        return None


class Client:
    def __init__(self, base_url, *, token_env="MORROWDOCK_TOKEN", timeout=10):
        url = urlsplit(base_url)
        if (url.scheme not in ("http", "https") or not url.hostname or url.username
                or url.password or url.query or url.fragment
                or (url.scheme == "http" and url.hostname not in ("127.0.0.1", "localhost", "::1"))):
            raise ValueError("Use HTTPS, or HTTP on loopback for the mock")
        self.base_url = base_url.rstrip("/")
        self._token = os.environ[token_env]
        if not self._token or any(c in self._token for c in "\r\n"):
            raise ValueError("Invalid bearer token")
        self.timeout = timeout
        self._opener = build_opener(NoRedirect)

    def _call(self, method, path, data=None, *, binary=False):
        if not path.startswith("/v1/") or path.startswith("//"):
            raise ValueError("Invalid relay path")
        body = data if binary else (json.dumps(data).encode() if data is not None else None)
        request = Request(self.base_url + path, data=body, method=method,
                          headers={"Authorization": "Bearer " + self._token,
                                   "Content-Type": "application/octet-stream" if binary else "application/json"})
        try:
            with self._opener.open(request, timeout=self.timeout) as response:
                return json.load(response)
        except (URLError, ValueError, OSError):
            raise RuntimeError("Relay request failed") from None

    def send(self, item):
        validate(item)
        if item["schema"] != "morrowdock.agent-item/v1":
            raise ValueError("Expected item")
        return self._call("POST", "/v1/items", item)

    def upload(self, path, mime):
        path = Path(path)
        metadata = dict(name=path.name, mime=mime, size=path.stat().st_size, sha256=sha256(path))
        result = self._call("POST", "/v1/uploads", metadata)
        upload_id = result["uploadId"]
        import re
        if not re.fullmatch(r"[A-Za-z0-9_-]{16,64}", upload_id):
            raise ValueError("Invalid upload ID")
        self._call("PUT", "/v1/uploads/" + upload_id, path.read_bytes(), binary=True)
        return dict(uploadId=upload_id, **metadata)

    def requests(self):
        result = self._call("GET", "/v1/requests?status=open")
        for request in result["requests"]:
            validate(request)
            if request["schema"] != "morrowdock.agent-request/v1":
                raise ValueError("Expected request")
        return result["requests"]

    def answer(self, request_id, item):
        validate(item)
        if item.get("kind") != "answer" or item.get("inReplyTo") != request_id:
            raise ValueError("Answer must refer to the request")
        return self._call("POST", f"/v1/requests/{quote(request_id, safe='')}/answer", item)

    def status(self):
        return self._call("GET", "/v1/status")
