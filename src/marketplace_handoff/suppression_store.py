import sqlite3
from pathlib import Path


def normalize_phone(phone: str) -> str:
    digits = "".join(character for character in phone if character.isdigit())
    if len(digits) < 7:
        raise ValueError("phone must contain at least seven digits")
    return f"+{digits}"


class SuppressionStore:
    def __init__(self, database: str | Path = "marketplace-suppressions.sqlite3") -> None:
        self.connection = sqlite3.connect(str(database), check_same_thread=False)
        self.connection.execute(
            """
            CREATE TABLE IF NOT EXISTS sms_suppressions (
                phone TEXT PRIMARY KEY,
                source TEXT NOT NULL,
                recorded_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        self.connection.commit()

    def add(self, phone: str, source: str) -> str:
        normalized = normalize_phone(phone)
        self.connection.execute(
            """
            INSERT INTO sms_suppressions (phone, source)
            VALUES (?, ?)
            ON CONFLICT(phone) DO UPDATE SET source = excluded.source
            """,
            (normalized, source),
        )
        self.connection.commit()
        return normalized

    def contains(self, phone: str) -> bool:
        normalized = normalize_phone(phone)
        row = self.connection.execute(
            "SELECT 1 FROM sms_suppressions WHERE phone = ?", (normalized,)
        ).fetchone()
        return row is not None

    def close(self) -> None:
        self.connection.close()

    def __enter__(self) -> "SuppressionStore":
        return self

    def __exit__(self, exc_type: object, exc_value: object, traceback: object) -> None:
        self.close()
