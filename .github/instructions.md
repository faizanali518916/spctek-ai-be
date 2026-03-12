# SPCTEK AI — Backend Copilot Instructions

## Project Overview

This is the **SPCTEK AI backend** — a FastAPI-based REST API powering the SPCTEK AI platform. It handles authentication, contact management, and an AI-driven Amazon reinstatement report generator using Google Gemini.

---

## Tech Stack

| Layer      | Technology                                   |
| ---------- | -------------------------------------------- |
| Framework  | FastAPI (async)                              |
| Runtime    | Python 3.11+ with `uvicorn`                  |
| ORM        | SQLAlchemy 2.0 (async) with `asyncpg`        |
| Database   | PostgreSQL (async via `asyncpg` / `psycopg`) |
| Migrations | Alembic                                      |
| Auth       | JWT (`python-jose`) + bcrypt (`passlib`)     |
| AI         | Google Gemini via `google-genai`             |
| PDF        | ReportLab                                    |
| Email      | SMTP (`aiosmtplib` / `smtplib`)              |
| Config     | `pydantic-settings` + `.env` file            |

---

## Project Structure

```
app/
├── main.py              # FastAPI app factory, CORS, middleware, lifespan
├── config.py            # Settings (pydantic-settings, reads .env)
├── database.py          # Async SQLAlchemy engine, session, Base
├── models/
│   ├── user.py          # User ORM model (UUID PK, email, hashed_password)
│   └── contact.py       # Contact / lead ORM model
├── routers/
│   ├── auth.py          # /api/auth — register, login, me
│   ├── contacts.py      # /api/contacts — contact form submissions
│   └── reinstatement.py # /api/reinstatement — AI report generation
├── schemas/
│   ├── user.py          # Pydantic request/response models for users
│   ├── contact.py       # Pydantic models for contacts
│   └── reinstatement.py # Pydantic models for reinstatement input/output
├── services/
│   ├── gemini_client.py # Google Gemini wrapper (generate function)
│   ├── reinstatement.py # Core report-generation business logic
│   ├── email.py         # Email sending service
│   ├── formatter.py     # Text/data formatting helpers
│   └── instructions.py  # Prompt-engineering instructions for the AI
└── utils/
    └── security.py      # Password hashing, JWT creation/verification
```

---

## Coding Conventions

### General

- All route handlers must be `async def`.
- Use `Annotated` dependency injection everywhere (FastAPI best practice).
- Never use `print()` — always use the standard `logging` module.
- Raise `HTTPException` with appropriate status codes instead of returning error dicts.
- All IDs use `UUID` (PostgreSQL `UUID` type, Python `uuid.UUID`).

### Models

- All ORM models inherit from `app.database.Base`.
- Use SQLAlchemy 2.0 `Mapped[T]` and `mapped_column()` style — **not** the legacy 1.x `Column()` style.
- Timestamps should be `DateTime(timezone=True)` with `server_default=func.now()`.

### Schemas (Pydantic)

- Use Pydantic v2 (`model_config`, `model_validator`, `Field` with v2 syntax).
- Separate schemas for create input (`UserCreate`), read output (`UserRead`), and tokens (`Token`).
- Never expose `hashed_password` in response schemas.

### Routers

- Each domain (auth, contacts, reinstatement) lives in its own router file.
- Prefix all routers with `/api` in `main.py`.
- Group related endpoints using `APIRouter(prefix="...", tags=["..."])`.

### Security

- Passwords hashed with bcrypt via `passlib`.
- JWT tokens use HS256. Access token expiry is configurable via `ACCESS_TOKEN_EXPIRE_MINUTES`.
- `decode_access_token` returns `None` on failure — callers must check and raise `401`.
- Never log raw passwords or tokens.

### Configuration

- All secrets and environment-specific values live in `.env` (never hardcoded).
- Access config via `get_settings()` which is `@lru_cache`-decorated — do **not** call `Settings()` directly.
- Required env vars: `DATABASE_URL`, `SECRET_KEY`, `GOOGLE_API_KEY`, `SMTP_USER`, `SMTP_PASS`.

---

## AI / Gemini Integration

- The Gemini client lives in `services/gemini_client.py`.
- Use `generate(prompt, model=None)` — it wraps the `google-genai` SDK and handles errors.
- Default model: `gemini-3-flash-preview` (fallback chain: `gemini-2.0-flash` → `gemini-1.5-flash`).
- Prompt engineering / system instructions live in `services/instructions.py` — keep prompt templates there, not scattered in business logic.
- Gemini errors should be caught and re-raised as `RuntimeError` (as already done).

---

## Database

- Async engine via `create_async_engine` with `asyncpg`. SSL is enabled for remote connections.
- Session factory: `async_session` — always use the `get_db` dependency in route handlers.
- Schema is auto-created via `Base.metadata.create_all` on startup (via `lifespan`).
- For production, use **Alembic** migrations — do not rely on `create_all` dropping/recreating tables.
- Connection string format: `postgresql+asyncpg://user:pass@host:port/dbname`

---

## Environment Variables

| Variable                      | Description                                            | Default                                                           |
| ----------------------------- | ------------------------------------------------------ | ----------------------------------------------------------------- |
| `DATABASE_URL`                | PostgreSQL async connection string                     | `postgresql+asyncpg://postgres:postgres@localhost:5432/spctek_ai` |
| `SECRET_KEY`                  | JWT signing secret — **must be changed in production** | `change-me`                                                       |
| `ALGORITHM`                   | JWT algorithm                                          | `HS256`                                                           |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | Token TTL                                              | `60`                                                              |
| `CORS_ORIGINS`                | Comma-separated allowed origins                        | `http://localhost:3000`                                           |
| `GOOGLE_API_KEY`              | Google Gemini API key                                  | _(empty)_                                                         |
| `SMTP_HOST`                   | Email SMTP host                                        | `smtp.gmail.com`                                                  |
| `SMTP_PORT`                   | Email SMTP port                                        | `587`                                                             |
| `SMTP_USER`                   | Email sender address                                   | _(empty)_                                                         |
| `SMTP_PASS`                   | Email sender password / app password                   | _(empty)_                                                         |
| `FROM_NAME`                   | Display name for sent emails                           | `SPCTEK AI`                                                       |

---

## Running Locally

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Set up environment
cp .env.example .env   # then fill in your values

# 3. Start the dev server
uvicorn app.main:app --reload --port 8000
```

API docs available at `http://localhost:8000/docs` (Swagger) and `/redoc`.

---

## API Endpoints Summary

| Method | Path                         | Description                      | Auth       |
| ------ | ---------------------------- | -------------------------------- | ---------- |
| `POST` | `/api/auth/register`         | Register a new user              | None       |
| `POST` | `/api/auth/login`            | Login (returns JWT)              | None       |
| `GET`  | `/api/auth/me`               | Get current user profile         | Bearer JWT |
| `POST` | `/api/contacts`              | Submit a contact / lead form     | None       |
| `POST` | `/api/reinstatement/analyze` | Generate AI reinstatement report | None       |
| `GET`  | `/api/health`                | Health check                     | None       |

---

## Key Patterns to Follow

1. **Dependency injection via `Depends()`** for `get_db` and `get_current_user`.
2. **Async all the way** — no blocking I/O in route handlers or services.
3. **Never commit secrets** — use `.env` and ensure it is in `.gitignore`.
4. **Keep services pure** — business logic goes in `services/`, not in routers.
5. **Input validation at the schema level** using Pydantic — don't re-validate in services.
6. **Error messages should not leak internals** — return user-friendly strings.

---

## Testing

- Place tests in a `tests/` directory at the project root.
- Use `pytest` with `pytest-asyncio` for async tests.
- Use `httpx.AsyncClient` with FastAPI's `app` for integration tests.
- Mock external services (Gemini, SMTP) with `unittest.mock`.

---

## Common Mistakes to Avoid

- ❌ Using `Session` (sync) instead of `AsyncSession`.
- ❌ `await db.execute(...)` without `result.scalars()` / `result.scalar_one_or_none()`.
- ❌ Importing `Settings()` directly — always use `get_settings()`.
- ❌ Hardcoding CORS origins — keep them in `CORS_ORIGINS` env var.
- ❌ Forgetting `await db.commit()` after mutations.
- ❌ Catching bare `Exception` without re-raising or at least logging.
