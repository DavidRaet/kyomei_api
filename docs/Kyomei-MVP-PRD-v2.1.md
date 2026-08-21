# Kyomei MVP: Product Requirements Document

**Version:** 2.1
**Status:** Planning Phase
**Timeline:** MVP launch in 2 months (target: September 2026)

---

## Executive Summary

**Kyomei** (共鳴 — resonance) is a personalized anime recommendation engine built by fans for fans. Instead of endless scrolling through 10,000+ titles, Kyomei matches users with anime that *resonates with their vibe* — their personal frequency of taste.

The MVP validates the core hypothesis: **A smart recommendation system based on user taste profiles surfaces better anime than random browsing.**

**Target User:** Anime fans (beginner to veteran) aged 13–35 who want discovery without the guessing game.

**Success Metric:** User completes vibe check → receives relevant recommendations → rates shows → sees improved recommendations on next visit.

---

## Problem Statement

**Current State:**
- lack of personalized discovery in anime streaming platforms
- Users spend an unnecessary amount of time scrolling before picking a show
- Generic "Top 100" lists don't account for individual taste
- Discovery feels like gambling and watching the first episode is often a miss

**What Kyomei Solves:**
- Smart matching based on a personal taste profile
- Transparent recommendations ("recommended because you like psychological themes")
- Continuously improving algorithm based on user ratings
- Community-informed curation (trending among similar users)

---

## Product Vision (12-Month)

```
MVP (Months 1-2)      → Phase 2 (Months 3-4)    → Phase 3 (Months 5-12)
Discovery Loop        → Community Features        → Advanced ML + Scaling
Solo recommendation   → User insights             → Personalized rankings
Basic ratings         → Social recommendations    → Mobile app + integrations
```

**Long-term:** Become the trusted discovery layer for anime, powering how millions find their next favorite show.

---

## MVP Scope: 3 Phases

## PHASE 1: Foundation (MUST HAVE)

*Core loop: Signup → Vibe Check → Recommendations → Rate → Better Recs*

### 1.1 User Authentication & Account Management

| Feature | Description | Priority |
|---|---|---|
| Sign Up | Email + password registration via Auth0 | P0 |
| Login | Auth0-managed session with JWT | P0 |
| Logout | Clear Auth0 session + redirect to home | P0 |
| User Profile | Store email, name, created_at, updated_at | P0 |
| Password Reset | Auth0-managed email-based reset flow | P1 |

**Success Criteria:**
- User can register with a unique email
- Sessions persist across page refreshes
- Auth errors are clear ("Email already in use")

**Technical Notes:**
- Auth0 handles all password hashing, session storage, and token rotation
- No social login in MVP (add Google/Discord in Phase 2)
- FastAPI backend validates Auth0 JWTs on protected routes via a dependency that fetches Auth0's JWKS endpoint and verifies signature/claims (e.g. using `python-jose` or `pyjwt`)
- PostgreSQL stores user profile records linked to Auth0's `sub` (user ID)

---

### 1.2 Vibe Check Onboarding Survey

| Feature | Description | Priority |
|---|---|---|
| 5-Question Form | Captures user taste profile | P0 |
| Multi-Select Genres | Action, Romance, Comedy, Psychological, Slice-of-Life, Thriller, Drama, Horror, Fantasy, Sci-Fi | P0 |
| Mood Preference | Single select: Uplifting, Intense/Dark, Relaxing, Thought-Provoking | P0 |
| Episode Length | Short (<13), Medium (13–26), Long (26+) | P0 |
| Story Complexity | Light/Fun, Moderate, Deep/Philosophical | P0 |
| Maturity Level | SFW, PG-13, Mature | P0 |
| Form Validation | At least 1 genre + mood required | P0 |
| Save to Database | Store preferences in user_preferences table | P0 |

**Success Criteria:**
- Form completes in under 2 minutes
- All answers persist to database
- User can re-edit preferences anytime
- Form errors are helpful ("Select at least one genre")

**Technical Notes:**
- Client-side validation in React + server-side verification via a FastAPI `Pydantic` request model (mirrors the same shape enforced client-side)
- Map answers to recommendation algorithm (tag matching)
- 5 questions is fixed for MVP; subject to A/B testing in Phase 2

---

### 1.3 Anime Catalog (via AniList)

| Feature | Description | Priority |
|---|---|---|
| Anime Titles via AniList | Backend connects to the AniList GraphQL API to retrieve Anime information   | P0 |
| Core Metadata | Title, description, genres, episode count, rating, year, poster URL | P0 |
| Genre/Tag Tagging | Each anime tagged with 2–5 genres (AniList provides genre tags) | P0 |
| Community Rating | Average user rating (5-star scale) | P1 |
| Status Field | FINISHED, AIRING, UPCOMING | P1 |

**Success Criteria:**
- successfully connected to the AniList GraphQL API and retrieved anime data
- No missing genres or descriptions
- All poster URLs are valid (no 404s)

**Technical Notes:**
- Script sends GraphQL POST requests to the AniList public API (`https://graphql.anilist.co`) — no API key required
- Fetches in batches: title, genres, synopsis, episode count, poster URL, average score, year, status
- Transforms and inserts records directly into the `anime` PostgreSQL table
- Seed strategy: top 100 by AniList rating first, then expand to 300 with genre diversity
- Genres and tags stored in a normalized structure (separate table or JSONB column)
- Seed script written in Python (`httpx`/`requests` + `asyncpg` or `psycopg`), consistent with the rest of the backend stack

---

### 1.4 Content-Based Recommendation Engine

| Feature | Description | Priority |
|---|---|---|
| Tag Matching Algorithm | Surface anime where genres overlap with user preferences | P0 |
| Rating Boost | Prioritize highly-rated anime (4.5+ stars) | P0 |
| Ranking by Relevance | Return top 10–20 recommendations sorted by match score | P0 |
| Exclude Watched | Don't recommend anime user already rated | P0 |
| Cold Start | First-time users get top-rated anime in preferred genres | P0 |

**Algorithm (Pseudo-code):**
```
For each unrated anime:
  1. Calculate genre overlap score (0-1, based on shared tags)
  2. Apply rating multiplier (high-rated shows scored higher)
  3. Penalize if user rated similar show poorly
  4. Sort by final score
  5. Return top 10 results
```

**Success Criteria:**
- Recommendation query returns in under 200ms
- User sees at least 3 recommendations they recognize
- Recommendations feel relevant (manually validated before launch)

**Technical Notes:**
- Implemented as a raw SQL query (via `asyncpg`) + scoring logic in Python — no ML for MVP
- Async endpoint (`async def`) so recommendation lookups don't block other in-flight requests
- Cache recommendations in-process (e.g. `cachetools` TTL cache) or Redis if latency needs tightening; invalidated on new rating
- Measure: CTR (click-through rate) on recommendations via Amplitude

---

### 1.5 Rating System

| Feature | Description | Priority |
|---|---|---|
| 5-Star Rating | User rates anime (1–5 stars, or skip) | P0 |
| Rate from Anywhere | Rate on detail page, recommendation card, or watchlist | P0 |
| Update Rating | User can change rating anytime | P0 |
| Remove Rating | User can delete rating (resets recommendation signal) | P1 |
| Timestamp Rating | Store when user rated (rated_at field) | P0 |

**Success Criteria:**
- User can rate any anime in under 1 second (quick interaction)
- Recommendations update after each rating (cache invalidated on new rating)
- Ratings persist and are visible on user's profile

**Technical Notes:**
- Stored in `user_ratings` table: (user_id, anime_id, rating, rated_at)
- Recommendation cache invalidated after each new rating
- No public rating display until Phase 2

---

### 1.6 Watchlist / Status Tracking

| Feature | Description | Priority |
|---|---|---|
| Status Categories | Plan to Watch, Watching, Completed, Dropped | P0 |
| Add to Watchlist | User adds anime to any category from detail page | P0 |
| Update Status | Move anime between categories | P0 |
| View Watchlist | Dedicated page showing all categorized anime | P0 |
| Progress Tracking | Track episodes watched for "Watching" category | P1 |
| Timestamps | date_added, date_started, date_completed | P1 |

**Success Criteria:**
- User can organize anime across 4 categories
- Watchlist is persistent and updates in real-time
- User sees count of shows in each category (e.g., "5 Completed")

**Technical Notes:**
- Stored in `user_watchlist` table
- Watchlist is the action layer — where users manage their queue
- Distinct from ratings: a user can rate without watchlisting and vice versa

---

## PHASE 2: Core Engagement (SHOULD HAVE)

*Improve recommendation quality + add transparency*

### 2.1 Recommendation Refinement

| Feature | Description | Priority |
|---|---|---|
| Re-compute on Rating | Algorithm improves as user rates more anime | P1 |
| Pattern Detection | Identify dominant preferences ("user loves psychological shows") | P1 |
| Trending in Your Genre | Surface trending anime among users with similar taste | P1 |

**Technical Notes:**
- Update recommendation score weights based on user's rating history
- Introduce lightweight collaborative filtering ("users who liked X also liked Y")

---

### 2.2 Transparency Layer

| Feature | Description | Priority |
|---|---|---|
| Why This Rec? | Show user why they received each recommendation | P1 |
| Hover/Click for Details | "Recommended because you like: Psychological + Dark themes" | P1 |
| Tag Highlights | Highlight matching tags between user preferences and anime | P1 |

---

### 2.3 Dashboard & Home Feed

| Feature | Description | Priority |
|---|---|---|
| Personalized Feed | Show user's top recommendations first | P0 |
| Quick Stats | "You've rated 12 anime, 5 completed" | P1 |
| Trending This Week | Top-rated anime overall (community signal) | P1 |
| Continue Watching | Shows currently in "Watching" status | P1 |
| Quick Access | Shortcuts to watchlist, search, profile | P0 |

**Success Criteria:**
- Dashboard loads in under 1 second
- User sees actionable content above the fold
- Mobile-responsive design

---

### 2.4 Search & Browse

| Feature | Description | Priority |
|---|---|---|
| Full-Text Search | Search anime by title | P0 |
| Filter by Genre | Multi-select genre filters | P1 |
| Filter by Year | Range slider (2010–2025) | P1 |
| Filter by Status | FINISHED, AIRING, UPCOMING | P1 |
| Filter by Rating | Min rating threshold (3.0+, 4.0+, etc.) | P1 |
| Sort Options | By rating, recency, title (A-Z) | P1 |
| Pagination | 20 results per page | P1 |

**Technical Notes:**
- PostgreSQL full-text search (ILIKE) for MVP; upgrade to Elasticsearch post-MVP
- Cache filter results for performance

---

### 2.5 Anime Detail Page

| Feature | Description | Priority |
|---|---|---|
| Core Info | Title, poster, rating, genres, episode count, synopsis | P0 |
| User Actions | Rate, add to watchlist, update status | P0 |
| Your Rating | Display user's existing rating if present | P1 |
| Community Stats | "87% of users rated this 4+ stars" | P1 |
| Why Recommended? | Explanation of recommendation reasoning | P1 |
| Related Anime | 3–5 similar anime based on genres | P1 |

---

### 2.6 User Profile Page

| Feature | Description | Priority |
|---|---|---|
| Profile Header | User name, member since, stats | P1 |
| Stats Dashboard | Total rated, completed, dropped, avg rating | P1 |
| Preference Editor | Edit vibe check answers anytime | P0 |
| Rating History | All user ratings with timestamps | P1 |
| Quick Watchlist Link | Shortcut to watchlist | P0 |

---

## PHASE 3: Community & Advanced Features (NICE TO HAVE)

*Post-MVP, only if MVP metrics are strong*

### 3.1 Social Recommendations

| Feature | Description | Priority |
|---|---|---|
| Similar Users | "Users like you also rated X highly" | P2 |
| Community Trending | Most-rated anime this week (filtered by genre) | P2 |
| User Reviews | Short-form ratings + optional text review | P2 |

### 3.2 Advanced Recommendation

| Feature | Description | Priority |
|---|---|---|
| Collaborative Filtering | Cosine similarity between user vectors | P2 |
| A/B Testing Framework | Test multiple recommendation algorithms | P2 |
| Feedback Loop | Track which recs lead to completed watches | P2 |

### 3.3 Mobile App

| Feature | Description | Priority |
|---|---|---|
| React Native App | iOS/Android native experience | P3 |
| Offline Watchlist | Access watchlist without internet | P3 |
| Push Notifications | "New episode of your watching shows!" | P3 |

### 3.4 Third-Party Integrations

| Feature | Description | Priority |
|---|---|---|
| AniList Import | Bulk import user's AniList ratings | P2 |
| MyAnimeList Import | Bulk import MAL ratings | P2 |
| Streaming Links | "Watch on: Netflix, Crunchyroll, etc." | P2 |
| Discord Bot | `/anime recommend` command | P3 |

### 3.5 Creator Tools

| Feature | Description | Priority |
|---|---|---|
| Curated Lists | Users create public lists ("Best Slice-of-Life") | P2 |
| List-Based Trending | "Trending in Isekai" from community curation | P2 |

---

## User Stories (MVP Priority)

### P0: Core Loop

```
As a new user
I want to sign up with my email
So that I can create a personalized anime profile

As a new user
I want to complete a quick 5-question vibe check
So that the system understands my anime taste

As an authenticated user
I want to see recommendations based on my vibe
So that I can find anime that matches my preferences

As an authenticated user
I want to rate anime (1-5 stars)
So that the system learns what I like

As an authenticated user
I want to add anime to my watchlist
So that I can track what I plan to watch, am watching, or have completed

As an authenticated user
I want to see why I'm getting a recommendation
So that I trust the recommendation system

As a returning user
I want to see improved recommendations after rating more anime
So that the system gets better at predicting my taste
```

### P1: Engagement

```
As a user
I want to search for anime by title or genre
So that I can explore outside my personalized feed

As a user
I want to see my stats (anime watched, rating distribution)
So that I can track my progress

As a user
I want to edit my vibe check preferences anytime
So that I can refine how recommendations work

As a user
I want to see what's trending this week
So that I can discover new popular shows
```

### P2: Community (Post-MVP)

```
As a user
I want to see what similar users are watching
So that I discover shows through community signal

As a user
I want to see short reviews from other users
So that I can understand why they liked/disliked a show
```

---

## Non-Functional Requirements

| Requirement | Target | Notes |
|---|---|---|
| Performance | <1s page load, <200ms API response | FastAPI's async (ASGI) model keeps I/O-bound recommendation calls fast without blocking |
| Uptime | 99.5% (MVP on single Railway service) | Upgrade infrastructure in Phase 3 |
| Database | PostgreSQL, 5 core tables, <10MB initial | Indexes on user_id, anime_id |
| Security | HTTPS, Auth0 JWT validation, no sensitive data in logs | OWASP compliance |
| Scalability | 100–1,000 concurrent users | Uvicorn/Gunicorn worker processes + async I/O handle concurrency comfortably at this scale |
| Browser Support | Chrome, Firefox, Safari (last 2 versions) | Mobile-responsive (no native app yet) |
| Accessibility | WCAG 2.1 AA (contrast, keyboard nav, alt text) | Test with accessibility tools |
| Error Monitoring | Sentry on both FastAPI backend and React frontend | Capture exceptions, crashes, and JS exceptions |
| Product Analytics | Amplitude for behavioral tracking | Vibe check completion, recommendation CTR, return rate |

---

## Success Metrics (MVP Launch)

### Primary Metrics

| Metric | Target | Rationale |
|---|---|---|
| Vibe Check Completion Rate | >80% of sign-ups | If users skip, recommendation fails |
| Rating Engagement | >5 ratings per user (first week) | Signal that recommendations matter |
| Recommendation CTR | >30% (users click recommended anime) | Validation of algorithm quality |
| Return Rate | >40% (users return after 1 week) | App retention signal |

### Secondary Metrics

| Metric | Target | Rationale |
|---|---|---|
| Avg Recommendation Score | >3.5/5 (user rating of rec quality) | Post-MVP: ask users "how good was this rec?" |
| Watchlist Utilization | >60% of users use it | Core feature adoption |
| Search Usage | <20% of discovery (vs recommendations) | If too high, algorithm isn't strong enough |

---

## Out of Scope (MVP)

- ❌ **Real-time notifications** — Phase 3
- ❌ **Image recognition** — Anime detection from screenshots
- ❌ **Payment/Subscription** — Free forever for MVP
- ❌ **Mobile app** — Web app only (React)
- ❌ **Advanced ML** — Collaborative filtering in Phase 2
- ❌ **Third-party integrations** — AniList/MAL sync in Phase 3
- ❌ **Streaming rights** — Don't embed or verify where to watch
- ❌ **User-generated content** — No reviews or comments in MVP
- ❌ **Social features** — Following, messaging, etc.
- ❌ **Anthropic Claude / LLM** — Noted as a planned integration post-MVP (candidates: recommendation explanations, conversational discovery)
- ❌ **Social login** — Email-only for MVP; Google/Discord OAuth in Phase 2

---

## Technical Architecture (MVP)

### Frontend
- **React (TypeScript)** — SPA served as compiled static files
- **Pages in scope:** Auth (Login/Signup), Onboarding/Vibe Check, Dashboard/Home Feed, Anime Detail, Search & Browse, Watchlist, User Profile

### Backend
- **Python + FastAPI** — REST API server (ASGI, running under Uvicorn)
- **Pydantic** — Request/response validation; models map closely to the TypeScript interfaces already defined in `CONTRACT.md`, reducing request/response drift between frontend and backend
- **Auth0** — Authentication and session management; FastAPI validates JWTs on protected routes via a dependency that verifies tokens against Auth0's JWKS endpoint
- **Raw SQL (via `asyncpg`)** — Database queries written directly against PostgreSQL; no full ORM for MVP, keeping query behavior transparent and easy to profile
- **Alembic** — Database migration management (Python-native equivalent of golang-migrate)
- **Auto-generated OpenAPI docs** — Free with FastAPI (`/docs`, `/openapi.json`); useful for verifying the contract and for future TypeScript type generation

### Database
- **PostgreSQL** (hosted on Railway)
- 5 core tables: `users`, `user_preferences`, `anime`, `user_ratings`, `user_watchlist`
- Indexes on `user_id`, `anime_id`

### External Services
- **Resend** — Transactional email (password reset, welcome flow)
- **Vercel Blob** — File/blob storage (poster images if self-hosted)
- **Sentry** — Error monitoring and crash reporting (FastAPI + React)
- **Amplitude** — Product analytics and behavioral tracking
- **AniList** — Anime metadata GraphQL API; primary and sole anime data source (no fallback — see Design Decisions)

### Deployment
- **Railway** — Hosts both the FastAPI backend and PostgreSQL database
- FastAPI serves the compiled React `dist/` as static files via `StaticFiles` (single Railway service), or the frontend is deployed separately to Vercel if preferred
- **GitHub Actions** — CI/CD pipeline (lint, test, build, deploy to Railway on merge to main)

---

## Database Schema (5 Core Tables)

```sql
-- Users (linked to Auth0 sub)
CREATE TABLE users (
  id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  auth0_id    TEXT UNIQUE NOT NULL,
  email       TEXT UNIQUE NOT NULL,
  name        TEXT,
  created_at  TIMESTAMPTZ DEFAULT NOW(),
  updated_at  TIMESTAMPTZ DEFAULT NOW()
);

-- User taste profile from vibe check
CREATE TABLE user_preferences (
  id               UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id          UUID REFERENCES users(id) ON DELETE CASCADE,
  genres           TEXT[],         -- multi-select genres
  mood             TEXT,           -- Uplifting / Intense / Relaxing / Thought-Provoking
  episode_length   TEXT,           -- Short / Medium / Long
  story_complexity TEXT,           -- Light / Moderate / Deep
  maturity_level   TEXT,           -- SFW / PG-13 / Mature
  updated_at       TIMESTAMPTZ DEFAULT NOW()
);

-- Anime catalog (seeded from AniList)
CREATE TABLE anime (
  id             UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  anilist_id     INTEGER UNIQUE,
  title          TEXT NOT NULL,
  description    TEXT,
  genres         TEXT[],
  tags           TEXT[],
  episode_count  INTEGER,
  avg_rating     NUMERIC(3,2),
  year           INTEGER,
  status         TEXT,             -- FINISHED / AIRING / UPCOMING
  poster_url     TEXT,
  created_at     TIMESTAMPTZ DEFAULT NOW()
);

-- User ratings
CREATE TABLE user_ratings (
  id        UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id   UUID REFERENCES users(id) ON DELETE CASCADE,
  anime_id  UUID REFERENCES anime(id) ON DELETE CASCADE,
  rating    SMALLINT CHECK (rating BETWEEN 1 AND 5),
  rated_at  TIMESTAMPTZ DEFAULT NOW(),
  UNIQUE (user_id, anime_id)
);

-- User watchlist
CREATE TABLE user_watchlist (
  id             UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id        UUID REFERENCES users(id) ON DELETE CASCADE,
  anime_id       UUID REFERENCES anime(id) ON DELETE CASCADE,
  status         TEXT NOT NULL,    -- plan_to_watch / watching / completed / dropped
  date_added     TIMESTAMPTZ DEFAULT NOW(),
  date_started   TIMESTAMPTZ,
  date_completed TIMESTAMPTZ,
  UNIQUE (user_id, anime_id)
);

-- Indexes
CREATE INDEX idx_user_ratings_user_id  ON user_ratings(user_id);
CREATE INDEX idx_user_ratings_anime_id ON user_ratings(anime_id);
CREATE INDEX idx_user_watchlist_user_id ON user_watchlist(user_id);
```

---

## REST API Endpoints (MVP)

### Auth
| Method | Endpoint | Description |
|---|---|---|
| POST | `/api/auth/callback` | Auth0 callback handler |
| POST | `/api/auth/logout` | Clear session |

### Users
| Method | Endpoint | Description |
|---|---|---|
| GET | `/api/users/me` | Get current user profile |
| PUT | `/api/users/me` | Update profile |

### Preferences
| Method | Endpoint | Description |
|---|---|---|
| GET | `/api/preferences` | Get user vibe check preferences |
| POST | `/api/preferences` | Create or update preferences |

### Recommendations
| Method | Endpoint | Description |
|---|---|---|
| GET | `/api/recommendations` | Get personalized recommendations |

### Anime
| Method | Endpoint | Description |
|---|---|---|
| GET | `/api/anime` | Search and browse with filters |
| GET | `/api/anime/:id` | Get anime detail |

### Ratings
| Method | Endpoint | Description |
|---|---|---|
| POST | `/api/ratings` | Create or update a rating |
| DELETE | `/api/ratings/:animeId` | Remove a rating |

### Watchlist
| Method | Endpoint | Description |
|---|---|---|
| GET | `/api/watchlist` | Get user's watchlist |
| POST | `/api/watchlist` | Add anime to watchlist |
| PUT | `/api/watchlist/:animeId` | Update watchlist status |
| DELETE | `/api/watchlist/:animeId` | Remove from watchlist |

---

## Project Structure (Rough Outline)

```
kyomei/
├── kyomei_api/                # FastAPI backend (Python)
│   ├── main.py                # FastAPI app entry point / ASGI app
│   ├── routers/                # Route handlers (auth, users, preferences,
│   │                           #   recommendations, anime, ratings, watchlist)
│   ├── auth/                  # Auth0 JWT verification dependency (JWKS lookup)
│   ├── db/                    # Raw SQL queries (asyncpg) + connection pool
│   ├── recommendations/       # Tag-matching scoring logic
│   ├── schemas/               # Pydantic request/response models
│   └── models/                # Data classes / DB row mappings
├── migrations/                 # Alembic migration files
├── web/                        # Compiled React dist (served by FastAPI StaticFiles)
├── frontend/                   # React (TypeScript) source
│   ├── src/
│   │   ├── pages/
│   │   ├── components/
│   │   └── lib/
│   └── package.json
├── .github/
│   └── workflows/
│       └── deploy.yml          # GitHub Actions CI/CD
├── requirements.txt / pyproject.toml   # Python dependencies
└── railway.toml                 # Railway deployment config
```

---

## Risks & Mitigations

| Risk | Impact | Mitigation |
|---|---|---|
| Backend/product logic learned simultaneously slows development | Medium | FastAPI/Python reuses existing ML/data experience (e.g. PawPal RAG pipeline), so only the recommendation logic is new — not the language/ecosystem too |
| Auth0 JWT validation misconfiguration | High — security gap | Follow Auth0's Python (FastAPI) integration guide; test with expired/invalid tokens |
| Schema design mistakes | High — hard to fix post-deploy | Validate schema manually in PostgreSQL sandbox before first migration |
| Poor recommendation quality | High — kills engagement | Manually validate algorithm on 10+ test profiles before launch |
| AniList rate limiting during seed | Low — one-time script | Add delay between batch requests in seed script |
| Recommendation cache staleness | Medium — stale recs | Invalidate cache on every new rating event |
| Performance bottlenecks | Medium — affects retention | Indexes on user_id, anime_id; profile slow queries with EXPLAIN ANALYZE; use async endpoints for I/O-bound calls |
| Concurrency under real load (Python/FastAPI vs. Go) | Medium — deferred, not blocking for MVP | Use async I/O consistently and add Uvicorn worker processes if load testing shows contention; revisit with Go only if this becomes a proven bottleneck post-MVP |

---

## Design Decisions

### Switching Kyomei's Backend from Go to FastAPI

**Why I made it:**
The `POST /v1/recommendations` endpoint — the one that matters most in the contract — is fundamentally a data-shaping and ranking problem, which plays to Python's strengths rather than Go's. I already have direct, relevant experience with Python's ML/data ecosystem from PawPal's RAG pipeline, so FastAPI lets me ship the recommendation logic using tools I've already exercised instead of learning Go's ecosystem and idioms at the same time as the actual product logic. Within "Python," FastAPI specifically beat Flask because it's async-native (ASGI), its Pydantic validation maps almost 1:1 to the TypeScript interfaces already locked into `CONTRACT.md`, and it gives auto-generated OpenAPI docs for free.

**Tradeoffs considered & my response:**
- **Resume signal** — a half-finished Go backend under a tight MVP timeline sends a weaker signal than a working, well-scoped Python service. *Response:* I'm not abandoning Go — I'm decoupling "what ships Kyomei" from "what builds my backend-engineering resume line," and I'll demonstrate high-performance Go API design intentionally on a separate, purpose-built side project instead of forcing it into a timeline-sensitive MVP.
- **Lost Go learning rep on this project** — the Go scaffold (`go.mod`, `docs/go-backend-setup-checklist.md`) becomes dead weight to delete or archive, and this specific project no longer builds Go reps. *Response:* accepted as a sunk cost; the MVP's job is to validate the recommendation hypothesis, not to be a Go learning vehicle — that goal moves to a dedicated future project where I can showcase concurrency/performance on purpose rather than incidentally.
- **Concurrency under real load** — Python/FastAPI needs more deliberate handling (async I/O, worker processes) than Go gives by default under concurrent load. *Response:* manageable and deferrable at MVP scale (100–1,000 concurrent users); I'll use async endpoints consistently and add Uvicorn workers if load testing surfaces contention, revisiting Go later only if this becomes a proven, not hypothetical, bottleneck.
- **Interface risk between frontend and backend** — swapping frameworks could have introduced drift at the API boundary. *Response:* none realized — `CONTRACT.md` was written framework-agnostic from the start, so the swap costs nothing at the interface layer.

### Dropping Jikan as a Fallback Data Source

**Why I made it:**
A Jikan REST client (`app/jikan/client.py`) was implemented as the fallback data source per the original BFF design (AniList primary → Jikan fallback on error/timeout), mirroring the frontend's client-side pattern. After finishing it, I removed it and made AniList the sole upstream source for `kyomei_api`. Jikan is not a first-party MyAnimeList API — it's an unofficial scraper/wrapper around MyAnimeList's own website, which makes it flaky and prone to breaking whenever MAL's HTML or rate-limiting changes. A fallback exists to add resilience; a flaky fallback is counterproductive — it doesn't add real redundancy, and if AniList goes down, a Jikan fallback that's *also* unreliable just becomes a second shared point of failure rather than a safety net.

**Tradeoffs considered & my response:**
- **Loss of graceful degradation** — without a fallback, an AniList outage means `kyomei_api`'s anime endpoints fail outright instead of degrading to a secondary source. *Response:* accepted for MVP scope; AniList has been more stable in practice than scraping MAL, and the in-memory TTL cache already absorbs short blips. Revisit with a real, first-party fallback source if AniList reliability becomes a proven problem post-MVP, rather than reaching for Jikan again.
- **Sunk work** — the Jikan client and its smoke test (`scripts/smoke_test_jikan.py`) were fully implemented before being removed. *Response:* accepted as a learning cost, not wasted: it validated that the `Provider` abstraction (`app/anime/provider.py`) actually supports swapping or removing upstream implementations without touching call sites.

---

## Definition of Done (MVP)

- [ ] All P0 features implemented and tested
- [ ] Database schema validated with 300+ anime (via seed script)
- [ ] Auth0 JWT validation working end-to-end on all protected routes
- [ ] REST API fully functional (React → FastAPI → PostgreSQL → React)
- [ ] Recommendation algorithm manually validated (produces relevant results)
- [ ] Authentication fully functional (signup, login, logout, password reset)
- [ ] Mobile-responsive design verified across Chrome, Firefox, Safari
- [ ] TypeScript strict mode passes (no `any` types)
- [ ] Sentry configured on backend and frontend
- [ ] Amplitude events firing for key actions (vibe check complete, rating submitted, rec clicked)
- [ ] Alembic migrations run cleanly from fresh database
- [ ] GitHub Actions pipeline deploys to Railway on merge to main
- [ ] Production deployment successful

---

## Post-MVP Roadmap

### Phase 2 (Months 3-4): Community & Polish
- Collaborative filtering recommendations
- User reviews and short ratings
- Advanced filters (year, episode length, animation style)
- Trending section
- Preference re-tuning based on feedback
- Social login (Google, Discord via Auth0)
- Anthropic Claude integration (recommendation explanations or conversational discovery)
- Generate TypeScript types directly from FastAPI's auto-generated OpenAPI spec

### Phase 3 (Months 5-6): Scale & Expand
- Mobile app (React Native)
- Third-party integrations (AniList, MAL import)
- Advanced analytics dashboard
- Creator tools (curated lists)
- Push notifications

### Phase 4 (Months 7-12): Monetization & Growth
- Premium features (advanced stats, curated playlists)
- Partnerships with streaming platforms
- Marketing and community growth
- Discord bot, Reddit integration

---

## Glossary

| Term | Definition |
|---|---|
| Vibe Check | 5-question survey capturing user taste profile |
| Tag Matching | Algorithm that matches anime genres to user preferences |
| CTR | Click-through rate (% of users who click a recommendation) |
| Watchlist | User's personalized queue (Plan to Watch → Watching → Completed → Dropped) |
| Collaborative Filtering | Recommendation based on "users like you also liked X" |
| Content-Based | Recommendation based on anime metadata (genres, tags) |
| Cold Start | First recommendations for brand-new users (no rating history yet) |
| Alembic | Python-native database migration tool used to manage schema changes via versioned migration scripts |
| Auth0 sub | Auth0's unique user identifier used to link Auth0 accounts to internal user records |
| JWKS | JSON Web Key Set — Auth0's public keys used by FastAPI to verify JWTs |
| ASGI | Asynchronous Server Gateway Interface — the async server standard FastAPI runs on (via Uvicorn) |

---

**Document Owner:** @David Raet
**Version:** 2.1
**Last Updated:** August 10th, 2026
