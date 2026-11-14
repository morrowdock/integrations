# Morrowdock integrations

Status: early preview (2026-11-14). The contract is a draft.

Morrowdock is an open learning studio. Integrations are optional, swappable sources that bring learning materials into a learner's private Morrowdock Materials inbox: an AI agent, a course system, a file drive, a calendar, email, or anything else. Each learner decides which integrations to turn on, or writes their own.

Every integration speaks one open contract:

- `morrowdock.agent-item/v1`: one material, fact or note, with its source, per-field verification and coverage.
- `morrowdock.agent-request/v1`: a request from Morrowdock to an integration ("fetch", "check-changes", "summarize").

Content is always untrusted data. A consumer never follows instructions found inside an item. Integrations never send passwords, tokens, cookies, private feed URLs, or data about other people.

This repository will hold the contract schemas, a validator, a small SDK, example integrations and a local mock relay for testing. No learner data and no credentials belong here.

## Licence

Code: Apache-2.0 (see LICENSE). The schemas are part of the code.
