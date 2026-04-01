# SpcAiWebBE

SPCTEK AI website backend API built with FastAPI, PostgreSQL, and SQLAlchemy.

## Tech Stack

- **Framework**: FastAPI
- **Database**: PostgreSQL with asyncpg driver
- **ORM**: SQLAlchemy (async)
- **Authentication**: JWT with bcrypt password hashing
- **Migration Tool**: Alembic
- **Python**: 3.9+

## Prerequisites

- Python 3.9 or higher
- PostgreSQL 12+ installed and running
- Virtual environment activated
- `.env` file with `DATABASE_URL` configured

## Project Setup

### 1. Create and Activate Virtual Environment

```powershell
# Create virtual environment
python -m venv venv

# Activate virtual environment
.\venv\Scripts\activate
```

### 2. Install Dependencies

```powershell
pip install -r requirements.txt
```

### 3. Configure Environment

Create a `.env` file in the backend directory:

```env
DATABASE_URL=postgresql+asyncpg://postgres:password@localhost:5432/spctek_ai
```

## Running the Application

### Start the Development Server

```powershell
# Activate the virtual environment (if not already active)
.\venv\Scripts\activate

# Run the API server
uvicorn app.main:app --reload
```

The API will be available at `http://localhost:8000`

- API docs: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

## Database Management

### Initialize Database

```powershell
# Create the database (if it doesn't exist)
createdb -U postgres spctek_ai
```

### Run Migrations

```powershell
# Apply all pending migrations
alembic upgrade head

# Check current migration version
alembic current

# View migration history
alembic history
```

### Create Migrations

```powershell
# Generate a new migration after model changes
alembic revision --autogenerate -m "Description of changes"

# Then apply it
alembic upgrade head
```

### Clear Database

```powershell
# Drop all tables (caution: deletes all data)
alembic downgrade base

# Reinitialize database to current version
alembic upgrade head
```

Or manually reset:

```powershell
# Using psql
psql -U postgres -d spctek_ai -c "DROP SCHEMA public CASCADE; CREATE SCHEMA public;"

# Then reapply migrations
alembic upgrade head
```

## User Management

### Create Admin User

```powershell
# Interactive script to create users
python app/utils/add_user.py
```

This script will prompt you to:

- Enter email address
- Enter username
- Choose user role (BASIC/ADMIN)
- Set password

## API Endpoints

### Authentication

- `POST /api/auth/login` - Login with email/password, returns JWT token
- `POST /api/auth/register` - Register new user (if enabled)

### Contacts (Public)

- `POST /api/contacts/` - Submit contact form
- `GET /api/contacts/` - Get all contacts (admin only)

### Blogs (Public)

- `GET /api/blogs/` - List all blog posts
- `POST /api/blogs/` - Create blog post (admin only)

### Reinstatement

- `POST /api/reinstatement/` - Submit reinstatement request

## Project Structure

```
backend/
├── app/
│   ├── __init__.py
│   ├── main.py                 # FastAPI app initialization
│   ├── config.py               # Configuration and environment setup
│   ├── database.py             # Database connection and session
│   ├── dependencies.py         # Dependency injection
│   ├── models/                 # SQLAlchemy models
│   │   ├── user.py
│   │   ├── blog.py
│   │   ├── contact.py
│   │   └── ...
│   ├── routers/                # API route handlers
│   │   ├── auth.py
│   │   ├── blogs.py
│   │   ├── contacts.py
│   │   └── ...
│   ├── schemas/                # Pydantic request/response schemas
│   │   ├── user.py
│   │   ├── blog.py
│   │   ├── contact.py
│   │   └── ...
│   ├── services/               # Business logic
│   │   ├── auth.py
│   │   ├── email.py
│   │   └── ...
│   └── utils/                  # Utility scripts
│       ├── add_user.py         # User creation CLI
│       └── ...
├── migrations/                 # Alembic database migrations
├── alembic.ini                # Alembic configuration
├── requirements.txt           # Python dependencies
└── README.md                  # This file
```

## Common Tasks

### Reset Database to Fresh State

```powershell
# Downgrade to base (remove all tables)
alembic downgrade base

# Upgrade to current version (recreate all tables)
alembic upgrade head

# Create admin user
python app/utils/add_user.py
```

### Check Database Status

```powershell
# View current migration version
alembic current

# View all applied migrations
alembic history --verbose

# Test database connection
python app/utils/ping-db.py
```

### Development Workflow

```powershell
# 1. Make model changes in app/models/
# 2. Create migration
alembic revision --autogenerate -m "Add new field to user"

# 3. Review migration in migrations/versions/
# 4. Apply migration
alembic upgrade head

# 5. Restart server
# (uvicorn will auto-reload if running with --reload)
```

## Troubleshooting

### Connection Refused

```
sqlalchemy.exc.InterfaceError: connection is closed
```

**Solution**: Ensure PostgreSQL is running and DATABASE_URL is correct in `.env`

```powershell
# Check PostgreSQL service
Get-Service postgresql* | Select-Object Status, Name

# Start PostgreSQL service
Start-Service postgresql-x64-15  # adjust version number
```

### Database Does Not Exist

```
FATAL: database "spctek_ai" does not exist
```

**Solution**: Create the database

```powershell
createdb -U postgres spctek_ai
```

### Migration Conflicts

If migrations are out of sync:

```powershell
# View migration history
alembic history --verbose

# Check current head version
alembic current

# Downgrade and reapply if needed
alembic downgrade base
alembic upgrade head
```

## Environment Variables

| Variable                   | Description                  | Example                                                       |
| -------------------------- | ---------------------------- | ------------------------------------------------------------- |
| `DATABASE_URL`             | PostgreSQL connection string | `postgresql+asyncpg://postgres:pass@localhost:5432/spctek_ai` |
| `JWT_SECRET_KEY`           | Secret key for JWT tokens    | `your-secret-key-here`                                        |
| `JWT_ALGORITHM`            | JWT algorithm                | `HS256`                                                       |
| `ACCESS_TOKEN_EXPIRE_DAYS` | Token expiration time        | `7`                                                           |

## Contributing

1. Create a new branch for features/fixes
2. Make model changes in `app/models/`
3. Generate migration: `alembic revision --autogenerate -m "description"`
4. Test thoroughly
5. Commit changes

## License

Proprietary - SPCTEK AI
