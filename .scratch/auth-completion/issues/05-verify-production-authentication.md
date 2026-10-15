# 05: Verify production authentication end to end

**Repositories:** kyomei_api (coordination owner) and kyomei_0.
**Source:** auth-spec.md, Feature 10.
**What to build:** The deployed frontend and API support sign-up, sign-in, application-user resolution, protected access, and sign-out using the intended production Clerk environment.
**Blocked by:** 03 — Complete backend authentication regression coverage (kyomei_api); 04 — Complete frontend authentication regression coverage (kyomei_0).
**Status:** ready-for-agent

## Scope

Verify and finish production configuration already established by Features 1–6. Coordinate both deployments and Clerk configuration. Record sanitized verification evidence; never put credentials or session tokens in tickets.

## Acceptance criteria

- [ ] Production and development use separate Clerk credentials; required variable names and deployment setup are documented without secret values.
- [ ] Backend credentials are stored in deployment secret management; the frontend build contains only publishable authentication configuration.
- [ ] The backend authorizes the intended production frontend party, and CORS permits its required authenticated requests and preflights.
- [ ] Both deployments use HTTPS and the frontend calls the intended production API.
- [ ] A new production user can sign up/sign in, call /v1/me through the centralized authenticated client, and immediately receive a stable internal Kyomei user ID.
- [ ] A repeat request returns the same ID, and a second user resolves to a distinct identity.
- [ ] Missing and invalid production sessions receive 401; signing out clears protected UI access and subsequent ordinary client requests cannot retrieve protected data.
- [ ] Verify the intended session invalidation behavior explicitly; do not assume every previously issued token becomes invalid immediately on browser sign-out.
- [ ] Public discovery still works when signed out.
- [ ] Error responses, application logs, source control, and frontend build artifacts reveal no backend secrets or raw tokens.
- [ ] Sanitized evidence records deployed versions, tested origins, scenarios, outcomes, and any required human dashboard steps.
- [ ] Required backend checks and frontend type checking, lint, tests, and build pass for any configuration or code changed.

