# 02: Enforce ownership across existing protected endpoints

**Repository:** kyomei_api
**Source:** auth-spec.md, Feature 8.
**What to build:** A signed-in user can access only their own existing private API resources, while visitors retain access to public anime discovery.
**Blocked by:** None.
**Status:** ready-for-agent

## Scope

Inventory the implemented endpoints and explicitly classify public versus user-owned behavior. Currently /v1/me is the protected resource and health/anime discovery are public. The spec's preferences, ratings, recommendations, and server-side watchlist endpoints are illustrative or proposed; this ticket does not authorize implementing them.

## Acceptance criteria

- [ ] Every implemented user-owned endpoint depends on CurrentUser and uses its internal Kyomei user ID.
- [ ] Missing or invalid authentication receives the documented 401 response.
- [ ] Client-supplied identity in query parameters, request bodies, or headers cannot change the resource owner.
- [ ] Two authenticated identities resolve to their respective /v1/me identities; add cross-user access tests for any other existing private resources discovered during the inventory.
- [ ] Existing private-resource queries and mutations, if any, scope access to the authenticated internal user ID.
- [ ] Health and all intended public anime endpoints still work without a session.
- [ ] Contracts document the implemented access policy in both repositories; proposed endpoints remain clearly proposed.
- [ ] Focused access-control regression tests, the full backend test suite, and Ruff pass.

