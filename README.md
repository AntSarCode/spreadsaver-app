# SpreadSaver

A community budgeting app to **track purchases**, **apply custom budget rules** (e.g., 50/30/20), **visualize monthly performance**, **earn badges**, and **optionally share budgets in groups**.

---

## Tech Stack
- **Frontend:** Flutter/Dart
- **Backend:** FastAPI (Python 3.11)
- **Database:** PostgreSQL
- **Auth:** JWT (access + refresh)
- **Payments (planned):** Stripe

---

## Monorepo Layout (current)
```
spreadsaver_frontend/              # Flutter app scaffold (ported from Power6Mobile)
  lib/
    screens/                       # login, signup, streak, timeline, (power_)badge, subscription, etc.
    services/                      # api_service.dart, ...
    state/                         # app_state.dart, ...
    ui/, utils/, widgets/          # theme.dart, overlays, components
  pubspec.yaml

spreadsaver_backend/               # FastAPI app scaffold
  app/
    config/                        # settings.py (env-driven)
    database.py                    # SQLAlchemy engine/session
    models/                        # models.py (UUID PKs; includes Badge models)
    routes/                        # auth.py, badge.py, ...
    schemas/                       # Pydantic schemas (WIP)
    services/                      # badge_service.py, budget_service.py, ...
    utils/                         # hash.py, calculations.py, ...
  scripts/                         # init_db.py (bootstrap DB)
  requirements.txt
  runtime.txt
```

> **Note:** Some files in the scaffold are intentionally placeholders and require the fixes listed in **Known Issues & To‑Dos** below.

---

## Quick Start

### Prereqs
- **Flutter SDK** (and Dart) installed and on PATH.
- **Python 3.11**
- **PostgreSQL** running locally (default dev assumption: `localhost:5433`, user `postgres`, password `postgres`, DB `postgres`).

### 1) Backend (FastAPI)
1. Create and activate a virtual env:
   ```bash
   cd spreadsaver_backend
   python -m venv .venv
   source .venv/bin/activate  # Windows: .venv\\Scripts\\activate
   ```
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   # If using async engine (recommended), also install asyncpg
   pip install asyncpg
   ```
3. Create a `.env` file (see sample below) or edit the provided `.env.example`:
   ```ini
   # JWT
   SECRET_KEY=change-me
   REFRESH_SECRET_KEY=change-me-too
   ACCESS_TOKEN_EXPIRE_MINUTES=60
   REFRESH_TOKEN_EXPIRE_DAYS=7

   # DB (async recommended)
   DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5433/postgres

   # CORS
   ALLOWED_ORIGINS=*

   # Stripe (Phase 6)
   STRIPE_SECRET_KEY=
   STRIPE_PUBLISHABLE_KEY=
   STRIPE_WEBHOOK_SECRET=
   STRIPE_SUCCESS_URL=http://localhost:5173/subscribe?success=1
   STRIPE_CANCEL_URL=http://localhost:5173/subscribe?canceled=1
   ```
4. Initialize the database (temporary bootstrap without Alembic):
   ```bash
   python -m scripts.init_db
   ```
5. Run the API:
   ```bash
   uvicorn app.main:app --reload
   # API at http://127.0.0.1:8000
   ```

### 2) Frontend (Flutter)
1. Install packages:
   ```bash
   cd spreadsaver_frontend
   flutter pub add provider http shared_preferences url_launcher flutter_secure_storage
   flutter pub get
   ```
2. Set API base URL:
   - Create `lib/config.dart` (or update `services/api_service.dart`) with your backend URL:
     ```dart
     const String kApiBaseUrl = 'http://127.0.0.1:8000';
     ```
3. Run the app (web or device):
   ```bash
   flutter run -d chrome
   # or
   flutter run
   ```

---

## Implemented So Far (based on current scaffold)
- **Models:** Core budgeting entities plus **Badge**, **UserBadge**, and **BadgeAssignRequest** added to `app/models/models.py` ✅
- **Schemas:** Badge-related schemas scaffolded in canvas (`/backend/app/schemas/schemas.py`) ✅
- **Auth Routes:** `routes/auth.py` scaffolded in canvas (username/email + password; JWT) ✅
- **Frontend scaffold:** Port of Power6Mobile with login/signup/screens, theme, widgets ✅

> Roadmap reference (2025‑07‑27) indicates Phases 1–2 are next up: backend auth & user system, then core budget logic.

---

## API (initial)
- `POST /auth/register` → `{ access_token, refresh_token, token_type }`
- `POST /auth/login` → `{ access_token, refresh_token, token_type }`
- `POST /auth/refresh` → `{ access_token, refresh_token, token_type }`
- `GET  /auth/me` → user profile (auth required)
- `GET/POST /badges` (planned)

> More routes (categories, purchases, summaries, groups) will be added as services solidify.

---

## Mapping from Power6 → SpreadSaver (Porting Checklist)
- **Terminology:**
  - `Task` → `Purchase`
  - `Streak` → `BudgetSummary` (or progress card)
  - `Power Badge` screens → `Badge` screens
- **Screens:**
  - Replace/rename `task_*` screens to `purchase_*` (input/review).
  - `streak_screen.dart` → budget dashboard / month summary.
  - Keep `login`, `signup`, `subscription` (for eventual Stripe gating).
- **State/Services:**
  - Point API client to SpreadSaver endpoints (`kApiBaseUrl`).
  - Replace Power6-specific DTOs with SpreadSaver schemas.
- **Theming:**
  - Reuse `theme.dart`, overlays, and widgets; rename labels where needed.

---

## Known Issues & To‑Dos (as of 2025‑10‑04)
**Backend**
- `app/main.py` imports `api.api_router`, but the repo currently organizes routers under `app/routes/`. Either:
  - create `app/api/api_router.py` that includes all routers, **or**
  - import routers directly in `app/main.py` (e.g., `from app.routes import auth, badge` then `app.include_router(auth.router)` etc.).
- `app/database.py` uses `from config.config import settings`; should be `from app.config.settings import settings`.
- `DATABASE_URL` uses async engine; ensure the URL uses `postgresql+asyncpg://` and that `asyncpg` is installed.
- `app/models/models.py` imports `from database import Base`; should be `from app.database import Base`.
- Some files contain placeholder ellipses (`...`) or truncated lines and must be completed (e.g., `schemas/schemas.py`).
- Align ID types: models currently use **UUID** PKs; ensure schemas and foreign keys match consistently.

**Frontend**
- `pubspec.yaml` must be cleaned of placeholder `...` lines and aligned with actual imports (add `provider`, etc.).
- `main.dart` references both `badge_screen.dart` and `power_badge_screen.dart`; standardize to `badge_screen.dart`.
- Update services to call SpreadSaver endpoints and auth flow; remove Power6-specific names.

---

## Environment Variables
See `.env.example` for the full list. Key values:
- `SECRET_KEY`, `REFRESH_SECRET_KEY`, `ACCESS_TOKEN_EXPIRE_MINUTES`, `REFRESH_TOKEN_EXPIRE_DAYS`
- `DATABASE_URL` (e.g., `postgresql+asyncpg://postgres:postgres@localhost:5433/postgres`)
- `ALLOWED_ORIGINS` (CSV or `*`)
- `STRIPE_*` (Phase 6)

---

## Roadmap (excerpt)
- **Phase 1 – Backend Foundation:** scaffold, DB models, requirements, `.env` ✔︎ in progress
- **Phase 2 – Auth & User System:** JWT register/login, user CRUD, tier logic
- **Phase 3 – Core Budget Logic:** categories, purchases, rules, monthly summaries, diff reports
- **Phase 4 – Badge Engine:** rule evaluation, award logic, admin assignment tools
- **Phase 5 – Group Sync:** groups, roles, shared dashboards
- **Phase 6 – Monetization:** Stripe + gating

Full roadmap lives in `SpreadSaver_Roadmap_Revised.txt`.

---

## Dev Tips
- Use `generate_hash.py` to create bcrypt hashes when seeding admin users.
- Consider adding **Alembic** for migrations once models stabilize.
- Run `flutter doctor` to validate your Flutter toolchain.

---

## License
TBD (private during development).
