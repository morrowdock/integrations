# REST preview interface

Status: proposed integration interface, implemented by the synthetic mock and SDK
on 2026-11-14. This is not a claim that a production service offers these routes.
The base URL comes from caller configuration, never from item content.
All requests require `Authorization: Bearer <environment-supplied token>`.
Use HTTPS except for a loopback mock. The SDK does not follow redirects or log
credentials. No real service host is embedded. Example remote host: example.invalid.

| Method and path | Request | Successful response |
| --- | --- | --- |
| POST /v1/items | JSON agent item | 201: `{"id":"item UUID"}` |
| POST /v1/uploads | JSON `{name,mime,size,sha256}` using attachment constraints | 201: `{uploadId,putPath}` |
| PUT /v1/uploads/{uploadId} | Exact raw attachment bytes | 200: `{uploadId}` |
| GET /v1/requests?status=open | No body | 200: `{"requests":[request records]}` |
| POST /v1/requests/{id}/answer | Valid kind=answer item with matching inReplyTo | 201: `{id}`; request becomes answered |
| GET /v1/status | No body | 200: `{"status":"ok","items":0,"mock":true}` in the mock |

Upload first, PUT its bytes, then attach the returned uploadId and original
metadata to an item. The SDK constructs the same-origin PUT path from uploadId;
it never sends a bearer token to a returned external upload URL. SHA-256 and
byte size must match. An item cannot refer to an unknown or incomplete upload.

Errors: 400 invalid input, 401 missing/wrong token, 404 unknown route/resource,
409 duplicate item or closed request, 413 body exceeds 25 MiB. Error bodies use
`{"error":"short generic description"}` and do not echo content or credentials.
The SDK raises a generic RuntimeError for transport/server failures. It does not
retry writes automatically. Callers must reconcile an uncertain write before
retrying; the mock rejects duplicate IDs.

The mock binds only 127.0.0.1, stores bytes and records in memory, accepts only
synthetic items, and seeds one synthetic TEST 101 request at startup. Stop it to
erase all data. It makes no outbound network calls. It is single-threaded and
is not hardened against hostile clients. Requests have a far-future fixture
expiry; production agents and relays must enforce real expiry. No route here
submits coursework or approves AI drafts.
