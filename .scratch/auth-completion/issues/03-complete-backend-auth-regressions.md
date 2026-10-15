# 03: Complete backend authentication regression coverage

**Repository:** kyomei_api
**Source:** auth-spec.md, Feature 9 — backend.
**What to build:** An automated regression suite detects broken authentication, provisioning, and user isolation before a backend change can ship.
**Blocked by:** 01 — Resolve the Kyomei user through CurrentUser; 02 — Enforce ownership across existing protected endpoints.
**Status:** ready-for-agent

## Scope

Audit and extend existing authentication and user-persistence tests rather than duplicating them. Keep business tests independent of live Clerk. Preserve realistic PostgreSQL integration coverage for unique constraints and concurrent provisioning.

## Acceptance criteria

- [ ] Public endpoints succeed without tokens; each existing protected endpoint rejects missing and invalid tokens.
- [ ] Adapter-boundary tests cover malformed/expired tokens, wrong authorized party, and non-session credentials using controlled verification responses or fixtures.
- [ ] At least one protected-route rejection test exercises the real authentication dependency, so removing that dependency would make the test fail.
- [ ] Valid authentication resolves the expected internal user; first requests provision it and later requests reuse it.
- [ ] Separate database sessions concurrently provisioning one external identity produce one user row and one stable ID.
- [ ] Two users receive distinct identities, and attempts to supply another user's identity do not grant access; exercise actual cross-user resources if present.
- [ ] Database outages and authentication failures preserve documented status codes and safe error bodies.
- [ ] Tests verify raw tokens are absent from logs; ordinary unit tests require no live Clerk calls.
- [ ] PostgreSQL integration prerequisites are documented and those tests run in the designated integration environment rather than silently substituting mocks for concurrency.
- [ ] The full backend test suite and Ruff pass.

