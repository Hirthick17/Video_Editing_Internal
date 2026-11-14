"""SQLite connection manager, transaction handler, and schema migration runner."""

import os
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Generator, Optional

from app.config import settings

SCHEMA_PATH = Path(__file__).parent / "schema.sql"


class DatabaseManager:
    """Manages SQLite connections, transactions, and schema setup."""

    def __init__(self, db_path: Optional[Path | str] = None):
        if db_path is None:
            self.db_path = str(settings.sqlite_db_path)
        else:
            self.db_path = str(db_path)

    def get_connection(self) -> sqlite3.Connection:
        """Create a configured SQLite connection with foreign keys and WAL mode."""
        conn = sqlite3.connect(self.db_path, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON;")
        if self.db_path != ":memory:":
            conn.execute("PRAGMA journal_mode = WAL;")
        return conn

    @contextmanager
    def transaction(self) -> Generator[sqlite3.Connection, None, None]:
        """Provide a transactional scope around a series of operations."""
        conn = self.get_connection()
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def initialize_schema(self) -> None:
        """Apply schema DDL to create tables and indexes idempotently."""
        if self.db_path != ":memory:":
            os.makedirs(os.path.dirname(self.db_path), exist_ok=True)

        with open(SCHEMA_PATH, "r", encoding="utf-8") as f:
            ddl = f.read()

        with self.transaction() as conn:
            conn.executescript(ddl)


# Global default manager
default_db_manager = DatabaseManager()

