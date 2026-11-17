# Contributing

Use an independent branch and a pull request. This repository is Apache-2.0.
Keep fixtures synthetic, use fake course codes, and never add private source
material, credentials, learner state, or other people's data.

Each commit needs a Developer Certificate of Origin sign-off matching its author:
`git commit -s`. By signing, you certify that you have the right to contribute
under the project's license, as described in Developer Certificate of Origin 1.1.
See [DCO text](DCO.txt). CI checks the sign-off trailer for every PR commit.

Every PR must add a NEW non-empty bullet under `## [Unreleased]`, within a standard
category: Added, Changed, Deprecated, Removed, Fixed, or Security. Preserve old
entries. Moving or reformatting an old entry is not a new entry. Comments and
fenced blocks do not count; closing fences allow only whitespace after the
marker. Do not put a change only in a released section. There is no label bypass.

Run both validator suites and SDK/mock tests from the README. Keep packaged
schemas byte-identical to contract/. Change the contract only through an explicit
versioned contract review. Heavy installs and test runs can take several minutes;
run them when the machine is free. Do not merge or push to main from an implementation task.

The changelog checker derives from morrowdock/courses tools/check_changelog.py,
main commit 75b88e23a48283d5cfa3a5caeb9c253049e9aa60 (verified 2026-11-14),
with all-path enforcement, no label exemption, and strict closing-fence handling.

Fixture email addresses must use example.invalid. CI checks test and example files.
The approved author/sign-off identity and co-author trailer in the email checker
are exceptions for Git commit metadata only, never fixture content.
