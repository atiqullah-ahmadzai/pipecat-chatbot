from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, scoped_session
from sqlalchemy.engine import Engine
from sqlalchemy import event
import os

DATABASE_URL = "sqlite:///./main.db"

if not os.path.exists("main.db"):
    open("main.db", "w").close()

# Configure SQLite to handle datetime properly
@event.listens_for(Engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()

# Create engine with specific configurations
engine = create_engine(
    DATABASE_URL, 
    connect_args={
        "check_same_thread": False,
        "timeout": 30
    },
    pool_pre_ping=True,
    pool_recycle=3600
)

# Create session factory with thread safety
session_factory = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)

# Create scoped session to handle multiple threads safely
SessionLocal = scoped_session(session_factory)

Base = declarative_base()
Base.query = SessionLocal.query_property()