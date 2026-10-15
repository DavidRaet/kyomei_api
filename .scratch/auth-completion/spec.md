# Kyomei Authentication Implementation Specification

## Overview

Kyomei will use **Clerk** as its external authentication provider.

The authentication architecture will separate responsibilities across three layers:

```text
React
  │
  │ Clerk React SDK
  │ Authentication UX + session/token acquisition
  ▼
FastAPI
  │
  │ Clerk Python SDK
  │ Token verification + trusted identity extraction
  ▼
Kyomei
  │
  │ Application-owned user identity
  ▼
Kyomei Database
```

The implementation should preserve the following architectural boundary:

> Clerk owns authentication and external identity. FastAPI verifies that identity. Kyomei owns application users and application data.

Clerk-specific implementation details should remain isolated from the rest of Kyomei wherever practical.

---

# Feature 1 — Clerk Project Configuration

## Description

Create and configure the Clerk application that will act as Kyomei's authentication provider.

This feature establishes the configuration required by both the React frontend and FastAPI backend before either layer begins using Clerk.

## Tools

- Clerk Dashboard
- Environment variables
- Existing Kyomei secret/environment management

## Primary Tasks

1. Create a Clerk application for Kyomei.
2. Configure the initial authentication methods.
   - Start with the authentication methods Kyomei intends to support at launch.
   - Social authentication such as Google can be added through Clerk without changing Kyomei's core auth architecture.
3. Obtain the development credentials required by the frontend and backend.
4. Configure the frontend with the Clerk publishable key.
5. Configure the backend with the appropriate Clerk server-side credentials.
6. Ensure secrets are excluded from source control.
7. Update `.env.example` files with the required variable names but no actual secret values.
8. Configure separate development and production Clerk credentials when Kyomei is deployed.

The frontend publishable key is intentionally safe for client-side use, while Clerk's secret key and other backend-only credentials must never be exposed to the browser. citeturn222662search1turn319296search0

## Acceptance Criteria

This feature is complete when:

- A Kyomei Clerk application exists.
- At least one sign-in method is configured.
- React can access the Clerk publishable key through environment configuration.
- FastAPI can access its required Clerk configuration through server-side environment variables.
- No Clerk secret is committed to Git.
- `.env.example` documents every required authentication variable.
- Development credentials can be rotated without requiring source-code changes.

---

# Feature 2 — React Authentication Foundation

## Description

Integrate Clerk into the React frontend and establish Clerk as the source of frontend authentication state.

At this stage, the objective is not yet to communicate with protected FastAPI routes. The objective is simply to prove that users can create a session and that React can correctly observe that session.

## Tool

**Clerk React SDK — `@clerk/react`**

Clerk's current React SDK provides `ClerkProvider`, authentication components, hooks, and session utilities. citeturn222662search1turn222662search7

## Primary Tasks

1. Install `@clerk/react`.
2. Add `ClerkProvider` at the React application entry point.
3. Read the Clerk publishable key from frontend environment configuration.
4. Add initial sign-in and sign-up UI.
5. Add sign-out functionality.
6. Add authenticated and unauthenticated UI states.
7. Verify that React can determine:
   - whether Clerk has loaded,
   - whether the current user is signed in,
   - the authenticated Clerk user ID.
8. Ensure loading states are handled before rendering authentication-dependent UI.
9. Decide which application routes require a signed-in user.

## Expected Flow

```text
Visitor
   │
   ▼
React
   │
   ▼
Clerk Sign In
   │
   ▼
Clerk Session
   │
   ▼
React recognizes authenticated user
```

## Acceptance Criteria

This feature is complete when:

- An unauthenticated user can open Kyomei.
- The user can sign up.
- The user can sign in.
- The user can sign out.
- React correctly distinguishes signed-in from signed-out state.
- Refreshing the page does not unexpectedly lose a valid Clerk session.
- Authenticated UI is not shown before Clerk has finished loading its session state.
- No FastAPI endpoint is required for basic sign-in or sign-up.

---

# Feature 3 — Authenticated API Client

## Description

Create the frontend boundary responsible for attaching Clerk authentication credentials to requests sent from React to FastAPI.

Rather than manually calling `getToken()` throughout individual components, Kyomei should centralize authenticated API communication.

## Tool

- Clerk React `useAuth()`
- Existing Kyomei frontend API client

Clerk's `useAuth()` hook exposes `getToken()`, which retrieves the active user's session token for use with external API requests. citeturn222662search3

## Primary Tasks

1. Retrieve Clerk session tokens through `getToken()`.
2. Attach the token to protected FastAPI requests using:

```text
Authorization: Bearer <session-token>
```

3. Create or extend a central Kyomei API client rather than repeating token logic inside components.
4. Distinguish between:
   - public API requests,
   - authenticated API requests.
5. Handle the case where no authenticated session exists.
6. Define frontend behavior for:
   - `401 Unauthorized`,
   - `403 Forbidden`,
   - temporary authentication failures.
7. Never persist session tokens manually unless there is a specific architectural need.
8. Never log authentication tokens.

## Target Boundary

React components should ideally call something resembling:

```text
api.getRecommendations()
api.getProfile()
api.updatePreferences()
```

rather than knowing how Clerk tokens are retrieved and attached.

The lower-level client should handle:

```text
getToken()
     ↓
Authorization header
     ↓
FastAPI
```

## Acceptance Criteria

This feature is complete when:

- Authenticated frontend API calls contain a Clerk session token.
- Public requests do not require a token.
- Authentication-token handling is centralized instead of duplicated across React components.
- Tokens are not written to application logs.
- Signed-out users cannot accidentally issue requests through authenticated client methods without receiving a controlled failure.
- The frontend has defined behavior for an API `401`.

---

# Feature 4 — FastAPI Clerk Authentication Boundary

## Description

Integrate Clerk's Python SDK into FastAPI so the backend can independently establish whether incoming requests are authenticated.

FastAPI must never trust a user ID supplied directly by React.

Instead:

```text
React claims identity
        │
        ▼
Clerk session token
        │
        ▼
FastAPI verifies token
        │
        ▼
Trusted identity
```

## Tool

**Clerk official Python SDK — `clerk-backend-api`**

Clerk's current Python guidance recommends using the official backend SDK with FastAPI rather than implementing JWT verification manually. `authenticate_request()` can operate directly on FastAPI's request object. citeturn319296search0turn319296search1

## Primary Tasks

1. Add `clerk-backend-api` to the FastAPI project.
2. Add Clerk configuration to the existing Kyomei settings/configuration layer.
3. Create a dedicated authentication module, for example:

```text
app/
  auth/
    dependencies.py
    models.py
```

or an equivalent structure consistent with Kyomei's existing project layout.

4. Implement a FastAPI authentication dependency.

Conceptually:

```text
require_auth(request)
       │
       ▼
Clerk authenticate_request()
       │
       ├── invalid → 401
       │
       └── valid
             │
             ▼
      authenticated identity
```

5. Restrict verification to Clerk session tokens.
6. Validate expected frontend origins / authorized parties.
7. Return `401 Unauthorized` for missing, invalid, or expired authentication.
8. Keep public routes public.
9. Do not log raw `Authorization` headers or JWTs.
10. Add one temporary or permanent protected endpoint for end-to-end testing, such as:

```text
GET /v1/me
```

The FastAPI dependency-injection system is a natural location for this boundary. Clerk's current guidance also recommends explicit session-token restrictions and authorized-party validation. citeturn319296search1

## Acceptance Criteria

This feature is complete when:

- A FastAPI endpoint can require authentication through dependency injection.
- A request without valid authentication receives `401 Unauthorized`.
- A malformed or invalid token receives `401 Unauthorized`.
- A valid Clerk session token successfully authenticates.
- FastAPI can obtain the Clerk user ID from the verified token.
- FastAPI does not trust a user ID merely because React supplied it.
- Public endpoints such as Kyomei's health check remain accessible without authentication.
- Authentication tokens do not appear in application logs.

---

# Feature 5 — Kyomei `CurrentUser` Abstraction

## Description

Prevent Clerk-specific objects and APIs from spreading throughout the FastAPI codebase.

The rest of Kyomei should depend on an internal representation of an authenticated user rather than directly depending on Clerk.

## Tools

- FastAPI dependency injection
- Pydantic / Python domain model
- Clerk Python SDK internally

## Primary Tasks

1. Define an internal authenticated-user representation.

Conceptually:

```text
CurrentUser
├── external_identity_id
└── kyomei_user_id
```

Additional fields should only be added when Kyomei actually needs them.

2. Create a dependency such as:

```text
get_current_user()
```

3. Make `get_current_user()` responsible for:
   - calling the Clerk verification layer,
   - extracting the trusted Clerk identity,
   - resolving the corresponding Kyomei user when necessary,
   - returning the internal `CurrentUser`.

4. Prevent application routes from invoking Clerk directly.

Prefer:

```text
recommendations(
    current_user = Depends(get_current_user)
)
```

instead of:

```text
recommendations(request):
    clerk.authenticate_request(...)
```

5. Keep Clerk-specific exceptions and response handling inside the auth boundary where practical.

## Target Architecture

```text
recommendation routes
profile routes
preference routes
rating routes
        │
        ▼
   CurrentUser
        │
        ▼
 get_current_user()
        │
        ▼
 Clerk adapter
```

## Acceptance Criteria

This feature is complete when:

- Protected business routes can receive a `CurrentUser`.
- Business routes do not call the Clerk SDK directly.
- Clerk-specific token verification exists in one clearly defined authentication layer.
- Replacing Clerk would primarily require modifications inside that authentication layer rather than throughout the application.
- Tests can replace or override `get_current_user()` without contacting Clerk.

---

# Feature 6 — Kyomei Application User

## Description

Create the separation between a Clerk identity and a Kyomei application user.

Clerk will remain the source of authentication identity.

Kyomei's database will remain the source of application-specific data.

## Tools

- Existing Kyomei database
- ORM/database layer
- Clerk verified user ID

## Primary Tasks

1. Define or extend Kyomei's application user table.

Conceptually:

```text
users

id
clerk_user_id
created_at
updated_at
```

Additional profile fields should only be stored if Kyomei owns or requires them.

2. Add a unique constraint on `clerk_user_id`.
3. Index `clerk_user_id` because authenticated requests will frequently resolve users through this field.
4. Determine how the initial Kyomei user record is created.
5. Associate Kyomei-owned resources with the internal Kyomei user ID.

For example:

```text
users
  id = 42
  clerk_user_id = user_xyz
           │
           ├──────── preferences.user_id = 42
           ├──────── ratings.user_id = 42
           └──────── recommendations.user_id = 42
```

6. Avoid using Clerk metadata as the primary persistence mechanism for:
   - anime preferences,
   - recommendation history,
   - ratings,
   - recommendation-engine state,
   - other Kyomei-specific data.

Clerk itself recommends storing application-specific user data in your own database when appropriate and using the Clerk ID as the mapping key. citeturn222662search0

## Acceptance Criteria

This feature is complete when:

- Every persisted Kyomei user can be mapped to one Clerk identity.
- `clerk_user_id` is unique.
- Kyomei resources reference the application's user ID rather than using Clerk IDs as foreign keys everywhere.
- Authentication data and recommendation-domain data have separate ownership.
- Deleting or replacing Clerk-specific integration would not require migrating the primary keys of recommendation-domain tables.

---

# Feature 7 — User Provisioning

## Description

Define how an authenticated Clerk identity becomes a Kyomei application user.

This feature should avoid making Kyomei dependent on asynchronous webhook delivery for its critical first-login flow.

## Tools

- FastAPI
- Kyomei database
- Clerk verified identity
- Optional Clerk webhooks later

## Primary Tasks

Use a synchronous **get-or-create / ensure-user** flow when an authenticated user first accesses functionality requiring a Kyomei user.

Conceptually:

```text
Verified Clerk user
       │
       ▼
Find users.clerk_user_id
       │
       ├── exists ─────────► return Kyomei user
       │
       └── missing
              │
              ▼
        create Kyomei user
              │
              ▼
        return Kyomei user
```

1. Resolve `clerk_user_id` from the verified session.
2. Search Kyomei's user table.
3. Create the record if it does not yet exist.
4. Make creation safe against duplicate/concurrent requests.
5. Return the resulting application user through `get_current_user()`.

Webhooks should not be required for this critical synchronous path because Clerk webhooks are asynchronous and eventually consistent; Clerk explicitly warns against relying on webhook delivery for flows that must complete immediately. citeturn222662search0turn222662search2

## Acceptance Criteria

This feature is complete when:

- A newly authenticated Clerk user can immediately use Kyomei without waiting for a webhook.
- The first authenticated request creates the corresponding Kyomei user when necessary.
- Subsequent requests reuse the existing user.
- Concurrent requests cannot create duplicate Kyomei users for the same Clerk identity.
- Temporary webhook delays or outages do not prevent first-time users from using Kyomei.

---

# Feature 8 — Protected Kyomei Routes

## Description

Apply authentication to Kyomei endpoints whose behavior or data belongs to a particular user.

Authentication should be added based on resource ownership, not globally without consideration.

## Tools

- FastAPI dependency injection
- `CurrentUser`

## Primary Tasks

Classify existing and future endpoints.

### Public

Examples may include:

```text
GET /health
GET /v1/anime/search
GET /v1/anime/{mal_id}
```

assuming anime discovery remains public.

### Authenticated

Examples may include:

```text
GET    /v1/me
GET    /v1/preferences
PUT    /v1/preferences
GET    /v1/recommendations
POST   /v1/ratings
DELETE /v1/ratings/{id}
```

1. Add `CurrentUser` dependencies to protected routes.
2. Scope database queries to the authenticated application's user ID.
3. Never accept arbitrary user IDs from the frontend when the resource should belong to the current user.
4. Prefer:

```text
GET /v1/me/preferences
```

or:

```text
GET /v1/preferences
```

over:

```text
GET /v1/users/{user_id}/preferences
```

when users are only supposed to retrieve their own data.

## Acceptance Criteria

This feature is complete when:

- Every user-owned endpoint requires authentication.
- Unauthenticated users receive `401` when requesting protected resources.
- User A cannot access User B's private Kyomei data by manipulating request parameters.
- Public anime endpoints continue functioning without authentication where intended.
- Routes obtain user identity through `CurrentUser`, not frontend-supplied identity fields.

---

# Feature 9 — Authentication Test Coverage

## Description

Add automated tests around Kyomei's authentication boundary so future changes cannot silently disable authentication or resource isolation.

## Tools

- Pytest
- FastAPI `TestClient` or existing testing stack
- FastAPI dependency overrides
- Frontend testing tools where appropriate

## Primary Tasks

### Backend

Test:

1. Public endpoint without token → success.
2. Protected endpoint without token → `401`.
3. Protected endpoint with invalid token → `401`.
4. Protected endpoint with valid authentication → success.
5. Valid authentication resolves the expected Kyomei user.
6. First authenticated request creates the application user.
7. Subsequent requests do not create duplicates.
8. User A cannot retrieve User B's private resources.

Avoid making the entire unit-test suite dependent on Clerk's live infrastructure. Tests below the Clerk adapter should override or mock the authentication dependency.

### Frontend

Test the important application behavior:

1. signed-out rendering,
2. signed-in rendering,
3. protected UI behavior,
4. authenticated API-client behavior,
5. handling of `401` responses.

## Acceptance Criteria

This feature is complete when:

- Authentication failures and successes have automated coverage.
- Resource isolation between two users has automated coverage.
- Normal backend unit tests can run without contacting Clerk.
- A regression that accidentally removes authentication from an important protected route causes a test failure.

---

# Feature 10 — Production Authentication Configuration

## Description

Prepare the completed authentication system for Kyomei's deployed environments.

## Tools

- Clerk production configuration
- Railway or current FastAPI deployment platform
- Frontend deployment platform
- CORS configuration
- Environment/secrets management

## Primary Tasks

1. Configure production Clerk credentials separately from development.
2. Configure the production frontend origin as an authorized party.
3. Verify FastAPI CORS configuration against the deployed frontend.
4. Store all backend Clerk secrets in deployment secret management.
5. Confirm the production frontend contains only publishable Clerk configuration.
6. Verify HTTPS is used in production.
7. Verify authentication errors do not reveal sensitive token information.
8. Verify logs never contain raw tokens or secret keys.
9. Run an end-to-end production authentication test:

```text
Sign up
   ↓
Sign in
   ↓
React obtains session
   ↓
React calls FastAPI
   ↓
FastAPI verifies identity
   ↓
Kyomei user resolved
   ↓
Protected resource returned
   ↓
Sign out
   ↓
Protected request rejected
```

## Acceptance Criteria

This feature is complete when:

- Production authentication succeeds end-to-end.
- Production and development credentials are separate.
- Backend secrets are not present in the frontend build.
- FastAPI accepts requests from the intended production frontend.
- Invalid or missing production sessions receive `401`.
- Signing out prevents subsequent protected API access.
- No authentication secrets or raw tokens appear in source control or application logs.

---

# Overall Authentication Definition of Done

Kyomei authentication is considered implemented when the following complete flow works:

```text
                     CLERK
                       │
              authentication provider
                       │
                       ▼
┌────────────────────────────────────┐
│               React                │
│                                    │
│  sign up / sign in / sign out      │
│  Clerk session                     │
│  getToken()                        │
└─────────────────┬──────────────────┘
                  │
                  │ Bearer session token
                  ▼
┌────────────────────────────────────┐
│              FastAPI               │
│                                    │
│  Clerk verification                │
│          ↓                         │
│  CurrentUser                       │
│          ↓                         │
│  Kyomei application user           │
└─────────────────┬──────────────────┘
                  │
                  ▼
┌────────────────────────────────────┐
│          Kyomei Database           │
│                                    │
│ user                               │
│ preferences                        │
│ ratings                            │
│ recommendation state               │
└────────────────────────────────────┘
```

The implementation is complete only when:

- Clerk handles user authentication and session management.
- React can obtain authentication state and credentials.
- React securely sends session credentials to FastAPI.
- FastAPI independently verifies every protected request.
- FastAPI exposes an internal `CurrentUser` abstraction to business logic.
- Clerk identity and Kyomei application-user identity remain distinct.
- Kyomei owns all recommendation-domain user data.
- User-owned API resources are scoped to the authenticated user.
- Public endpoints remain public where intended.
- Authentication and user isolation have automated test coverage.
- The production deployment works end-to-end.
- Clerk-specific implementation details remain concentrated inside the authentication boundary rather than spread throughout Kyomei.