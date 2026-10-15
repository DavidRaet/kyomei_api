# 01: Resolve the Kyomei user through CurrentUser

**Repository:** kyomei_api
**Source:** auth-spec.md, Feature 7; Features 1–6 are complete.
**What to build:** A verified session immediately resolves or creates a Kyomei application user through the shared CurrentUser dependency, so every protected business route receives the internal user identity without depending on webhook delivery.
**Blocked by:** None (can start immediately).
**Status:** ready-for-agent

## Context and scope

The existing /v1/me route already calls a concurrency-safe get-or-create operation. Reuse that operation and move its orchestration into the shared authenticated-user boundary. Do not recreate the user table or repeat completed authentication foundations.

## Acceptance criteria

- [ ] CurrentUser includes the verified external identity and resolved internal Kyomei user ID.
- [ ] The first authenticated request requiring an application user provisions it synchronously; subsequent requests reuse its ID without waiting for webhooks.
- [ ] Concurrent first requests for the same external identity resolve to exactly one persisted user.
- [ ] /v1/me obtains the internal ID from CurrentUser and preserves its existing response shape.
- [ ] Authentication is verified before provisioning; invalid sessions never create users.
- [ ] Database unavailability preserves the documented 503 error response, while invalid authentication remains 401.
- [ ] Business routes can override CurrentUser in tests without invoking Clerk; public routes do not acquire an authentication/database requirement.
- [ ] Focused tests cover dependency orchestration, stable identity, concurrency, and errors; the full backend test suite and Ruff pass.
- [ ] Any HTTP boundary changes are documented in both repositories' contracts.

