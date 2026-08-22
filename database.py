import os
from dotenv import load_dotenv
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import sessionmaker, declarative_base

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

if DATABASE_URL:
    # Render database URLs sometimes start with postgres://, but SQLAlchemy requires postgresql://
    if DATABASE_URL.startswith("postgres://"):
        DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)
else:
    # Fallback to local SQLite database if no database url is configured
    DATABASE_URL = "sqlite:///./test_db.sqlite"

# Handle sqlite specific settings
connect_args = {}
if DATABASE_URL.startswith("sqlite"):
    connect_args = {"check_same_thread": False}

engine = create_engine(
    DATABASE_URL,
    connect_args=connect_args,
    pool_pre_ping=True if not DATABASE_URL.startswith("sqlite") else False
)


def ensure_user_verification_columns():
    """Safely add email-verification columns to existing users tables without dropping data."""
    try:
        inspector = inspect(engine)
        if not inspector.has_table("users"):
            return

        existing_columns = {col["name"] for col in inspector.get_columns("users")}
        required_columns = {
            "is_verified": "BOOLEAN NOT NULL DEFAULT FALSE",
            "verification_token_hash": "VARCHAR(255)",
            "verification_token_expires_at": "TIMESTAMP WITH TIME ZONE",
            "verification_token_sent_at": "TIMESTAMP WITH TIME ZONE",
        }

        with engine.begin() as conn:
            for column_name, column_sql in required_columns.items():
                if column_name not in existing_columns:
                    conn.execute(text(f"ALTER TABLE users ADD COLUMN IF NOT EXISTS {column_name} {column_sql}"))

            if "is_verified" in existing_columns:
                conn.execute(text("UPDATE users SET is_verified = FALSE WHERE is_verified IS NULL"))
    except Exception:
        # Let the app keep booting in local/dev setups, but do not silently ignore real DB problems.
        # The migration should be visible in logs while preserving user data.
        import logging
        logging.getLogger(__name__).exception("Failed to ensure users verification columns exist")


SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)

Base = declarative_base()

ensure_user_verification_columns()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

