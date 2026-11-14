# Morrowdock integrations

**Early preview, contract draft. Apache-2.0.**

An integration is an optional, swappable source that feeds a learner's private
Morrowdock Materials inbox through one open contract. People can use these
integrations or build their own. The intended first-party sources are Canvas,
Google Drive, calendar ICS, email-in, share sheet, and manual upload. The first
agent integration is the owner's own AI agent. Community integrations can use
Moodle, Notion, or another AI agent.

This first version supplies the draft contract, validators, a small Python SDK,
a local mock relay, and synthetic folder and ICS examples. Canvas, Drive,
email-in, share sheet, production storage, and a hosted service are not
implemented here. No account is needed to test the mock.

## Quick start

Use Python 3.11+ and Node 22+. From this checkout:

```sh
python -m venv .venv
. .venv/bin/activate
pip install -e .
npm ci --ignore-scripts
python -m morrowdock_integrations validate contract/examples/valid/material.json
npx --no-install morrowdock-validate contract/examples/valid/material.json
export MORROWDOCK_TOKEN="$(python -c 'import secrets; print(secrets.token_urlsafe(32))')"
export MORROWDOCK_BASE_URL=http://127.0.0.1:8765
python -m morrowdock_integrations.mock
```

In another terminal, activate the same environment and set the same disposable
local token and base URL. Then run:

```sh
python examples/folder-integration/run.py examples/folder-integration/demo --once
python examples/ics-integration/run.py examples/ics-integration/demo.ics
```

Omit `--once` to poll for new or changed PDF/Markdown files every two seconds.
The folder example requires the SYNTHETIC_ONLY marker. Use only authored demo
files; the marker cannot establish whether a file contains private data.
Polling deduplication lasts for one process. A restart may send new observations.
The ICS example supports only the documented UTC fixture subset, rejecting
recurrence, TZID, folding and other unsupported properties. It never fetches URLs.

The npm package is not published. `npx morrowdock-validate <file>` resolves the
local binary after `npm ci`; `--no-install` prevents accidental registry lookup.
The Python package is also a local preview, not a released registry package.

On the shared Morrowdock laptop, wrap **every install, build, or test** with
`~/.local/bin/md-heavy <label> <command...>`; the commands above describe portable
setup for other contributors. Do not change the host's home-service containers.

## Write your own

1. Read [the contract](contract/CONTRACT.md) and [REST interface](contract/REST.md).
2. Collect only owner-authorized material. Preserve source time and per-field
   verification. Treat every fetched body as untrusted data.
3. Build with `build_item`, `provenance`, `verification`, and `coverage` from
   `morrowdock_integrations`. Use `sha256` for attachment bytes.
4. Set a base URL and a token environment variable. `Client(base_url)` supports
   `upload(path, mime)`, `send(item)`, `requests()`, `answer(id, item)`, and `status()`.
   All item sends validate locally first. The token is never logged.
5. Run synthetic round trips against the mock, then implement the appropriate
   source connector. A real relay must enforce authorization, retention, expiry,
   rate limits, upload limits and isolation before accepting real material.

See [agent integration](examples/agent-integration.md),
[contribution rules](CONTRIBUTING.md), and [security reporting](SECURITY.md).
Credit: Collin Craig.

## Tests

```sh
python -m unittest discover -s tests -v
npm test
bash tools/secret_scan.sh
```

The Python suite checks the same fixture manifest with both validators and tests
SDK/mock round trips, upload hashes, authentication, source examples and changelog
rules. JSON Schema validation cannot establish that a claim is true or safe.
