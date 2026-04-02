from __future__ import annotations

import hashlib
import json
import sqlite3
from dataclasses import dataclass
from pathlib import Path

from .categories import categorize_transaction
from .config import DB_PATH, LEGACY_CACHE_PATH, PARSER_VERSION
from .parsers import parse_statement_file, scan_statement_files
from .utils import utc_now_text


@dataclass
class FileImportResult:
    file_id: int
    source: str
    path: str
    status: str
    raw_count: int
    canonical_count: int = 0

    @property
    def deduped_count(self) -> int:
        return self.raw_count - self.canonical_count


@dataclass
class ImportResult:
    file_results: list[FileImportResult]
    removed_files: list[str]
    total_occurrences: int
    total_transactions: int

    @property
    def total_duplicates(self) -> int:
        return self.total_occurrences - self.total_transactions


def connect_db(db_path: Path | str = DB_PATH) -> sqlite3.Connection:
    db_path = Path(db_path)
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    init_db(conn)
    return conn


def init_db(conn: sqlite3.Connection) -> None:
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS source_files (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            path TEXT NOT NULL UNIQUE,
            source TEXT NOT NULL,
            size INTEGER NOT NULL,
            modified_time REAL NOT NULL,
            sha256 TEXT NOT NULL,
            parser_version TEXT NOT NULL,
            last_imported_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS transaction_occurrences (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            file_id INTEGER NOT NULL REFERENCES source_files(id) ON DELETE CASCADE,
            source TEXT NOT NULL,
            occurred_at TEXT NOT NULL,
            year INTEGER NOT NULL,
            month INTEGER NOT NULL,
            day INTEGER NOT NULL,
            tx_type TEXT NOT NULL,
            direction TEXT NOT NULL,
            pay_method TEXT NOT NULL,
            amount REAL NOT NULL,
            counterparty TEXT NOT NULL,
            category TEXT NOT NULL,
            dedup_key TEXT NOT NULL,
            raw_json TEXT NOT NULL
        );

        CREATE INDEX IF NOT EXISTS idx_occurrences_file_id ON transaction_occurrences(file_id);
        CREATE INDEX IF NOT EXISTS idx_occurrences_dedup_key ON transaction_occurrences(dedup_key);
        CREATE INDEX IF NOT EXISTS idx_occurrences_occurred_at ON transaction_occurrences(occurred_at);

        CREATE TABLE IF NOT EXISTS transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            canonical_occurrence_id INTEGER NOT NULL UNIQUE REFERENCES transaction_occurrences(id) ON DELETE CASCADE,
            dedup_key TEXT NOT NULL UNIQUE,
            source TEXT NOT NULL,
            occurred_at TEXT NOT NULL,
            year INTEGER NOT NULL,
            month INTEGER NOT NULL,
            day INTEGER NOT NULL,
            tx_type TEXT NOT NULL,
            direction TEXT NOT NULL,
            pay_method TEXT NOT NULL,
            amount REAL NOT NULL,
            counterparty TEXT NOT NULL,
            category TEXT NOT NULL,
            duplicate_count INTEGER NOT NULL DEFAULT 1
        );

        CREATE INDEX IF NOT EXISTS idx_transactions_occurred_at ON transactions(occurred_at);
        CREATE INDEX IF NOT EXISTS idx_transactions_year_month ON transactions(year, month);
        CREATE INDEX IF NOT EXISTS idx_transactions_category ON transactions(category);
        CREATE INDEX IF NOT EXISTS idx_transactions_counterparty ON transactions(counterparty);
        """
    )


def _sha256_for_file(filepath: Path) -> str:
    digest = hashlib.sha256()
    with filepath.open("rb") as file_obj:
        while True:
            chunk = file_obj.read(1024 * 1024)
            if not chunk:
                break
            digest.update(chunk)
    return digest.hexdigest()


def _load_legacy_cache() -> dict[str, list[dict[str, object]]]:
    if not LEGACY_CACHE_PATH.exists():
        return {}
    try:
        return json.loads(LEGACY_CACHE_PATH.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _lookup_legacy_transactions(
    legacy_cache: dict[str, list[dict[str, object]]],
    filepath: Path,
    modified_time: float,
) -> list[dict[str, object]] | None:
    exact_key = f"{filepath}|{modified_time}"
    if exact_key in legacy_cache:
        return legacy_cache[exact_key]

    prefix = f"{filepath}|"
    for cache_key, transactions in legacy_cache.items():
        if not cache_key.startswith(prefix):
            continue
        try:
            cached_mtime = float(cache_key[len(prefix):])
        except ValueError:
            continue
        if abs(cached_mtime - modified_time) < 1e-6:
            return transactions
    return None


def _normalize_legacy_transactions(transactions: list[dict[str, object]]) -> list[dict[str, object]]:
    normalized: list[dict[str, object]] = []
    for tx in transactions:
        tx_copy = dict(tx)
        tx_copy["category"] = tx_copy.get("category") or categorize_transaction(tx_copy)
        normalized.append(tx_copy)
    return normalized


def _ensure_source_file(
    conn: sqlite3.Connection,
    *,
    path: str,
    source: str,
    size: int,
    modified_time: float,
    sha256: str,
) -> tuple[int, bool]:
    existing = conn.execute(
        "SELECT id, sha256, parser_version FROM source_files WHERE path = ?",
        (path,),
    ).fetchone()
    changed = existing is None or existing["sha256"] != sha256 or existing["parser_version"] != PARSER_VERSION
    now_text = utc_now_text()
    if existing is None:
        cursor = conn.execute(
            """
            INSERT INTO source_files(path, source, size, modified_time, sha256, parser_version, last_imported_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (path, source, size, modified_time, sha256, PARSER_VERSION, now_text),
        )
        return int(cursor.lastrowid), True

    conn.execute(
        """
        UPDATE source_files
        SET source = ?, size = ?, modified_time = ?, sha256 = ?, parser_version = ?, last_imported_at = ?
        WHERE id = ?
        """,
        (source, size, modified_time, sha256, PARSER_VERSION, now_text, existing["id"]),
    )
    return int(existing["id"]), changed


def _replace_file_occurrences(
    conn: sqlite3.Connection,
    file_id: int,
    transactions: list[dict[str, object]],
) -> None:
    conn.execute("DELETE FROM transaction_occurrences WHERE file_id = ?", (file_id,))
    conn.executemany(
        """
        INSERT INTO transaction_occurrences(
            file_id, source, occurred_at, year, month, day, tx_type, direction,
            pay_method, amount, counterparty, category, dedup_key, raw_json
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        [
            (
                file_id,
                tx["source"],
                tx["full_dt"],
                tx["year"],
                tx["month"],
                tx["day"],
                tx["type"],
                tx["direction"],
                tx["pay_method"],
                tx["amount"],
                tx["counterparty"],
                tx["category"],
                tx["_dedup_key"],
                json.dumps(tx, ensure_ascii=False, separators=(",", ":")),
            )
            for tx in transactions
        ],
    )


def rebuild_transactions(conn: sqlite3.Connection) -> None:
    conn.execute("DELETE FROM transactions")
    conn.execute(
        """
        INSERT INTO transactions(
            canonical_occurrence_id, dedup_key, source, occurred_at, year, month, day,
            tx_type, direction, pay_method, amount, counterparty, category, duplicate_count
        )
        SELECT
            o.id,
            o.dedup_key,
            o.source,
            o.occurred_at,
            o.year,
            o.month,
            o.day,
            o.tx_type,
            o.direction,
            o.pay_method,
            o.amount,
            o.counterparty,
            o.category,
            grouped.duplicate_count
        FROM transaction_occurrences AS o
        JOIN (
            SELECT dedup_key, MIN(id) AS canonical_occurrence_id, COUNT(*) AS duplicate_count
            FROM transaction_occurrences
            GROUP BY dedup_key
        ) AS grouped
          ON grouped.canonical_occurrence_id = o.id
        ORDER BY o.occurred_at, o.id
        """
    )


def import_workspace(conn: sqlite3.Connection, force: bool = False) -> ImportResult:
    file_results: list[FileImportResult] = []
    scanned_files = scan_statement_files()
    scanned_paths = {str(path) for _, path in scanned_files}
    removed_files: list[str] = []
    legacy_cache = _load_legacy_cache()

    existing_paths = conn.execute("SELECT path FROM source_files").fetchall()
    for row in existing_paths:
        if row["path"] not in scanned_paths:
            removed_files.append(row["path"])
            conn.execute("DELETE FROM source_files WHERE path = ?", (row["path"],))

    data_changed = bool(removed_files)

    for source, filepath in scanned_files:
        stats = filepath.stat()
        sha256 = _sha256_for_file(filepath)
        file_id, changed = _ensure_source_file(
            conn,
            path=str(filepath),
            source=source,
            size=stats.st_size,
            modified_time=stats.st_mtime,
            sha256=sha256,
        )

        if force or changed:
            legacy_transactions = _lookup_legacy_transactions(legacy_cache, filepath, stats.st_mtime)
            if legacy_transactions is not None:
                transactions = _normalize_legacy_transactions(legacy_transactions)
            else:
                transactions = parse_statement_file(source, filepath)
            _replace_file_occurrences(conn, file_id, transactions)
            file_results.append(
                FileImportResult(
                    file_id=file_id,
                    source=source,
                    path=str(filepath),
                    status="parsed",
                    raw_count=len(transactions),
                )
            )
            data_changed = True
        else:
            raw_count = conn.execute(
                "SELECT COUNT(*) AS total FROM transaction_occurrences WHERE file_id = ?",
                (file_id,),
            ).fetchone()["total"]
            file_results.append(
                FileImportResult(
                    file_id=file_id,
                    source=source,
                    path=str(filepath),
                    status="cached",
                    raw_count=raw_count,
                )
            )

    if data_changed or conn.execute("SELECT COUNT(*) AS total FROM transactions").fetchone()["total"] == 0:
        rebuild_transactions(conn)

    canonical_by_file = {
        row["file_id"]: row["total"]
        for row in conn.execute(
            """
            SELECT o.file_id, COUNT(*) AS total
            FROM transactions AS t
            JOIN transaction_occurrences AS o ON o.id = t.canonical_occurrence_id
            GROUP BY o.file_id
            """
        ).fetchall()
    }

    for result in file_results:
        result.canonical_count = int(canonical_by_file.get(result.file_id, 0))

    total_occurrences = conn.execute(
        "SELECT COUNT(*) AS total FROM transaction_occurrences"
    ).fetchone()["total"]
    total_transactions = conn.execute(
        "SELECT COUNT(*) AS total FROM transactions"
    ).fetchone()["total"]
    conn.commit()

    return ImportResult(
        file_results=file_results,
        removed_files=removed_files,
        total_occurrences=int(total_occurrences),
        total_transactions=int(total_transactions),
    )


def fetch_duplicate_groups(
    conn: sqlite3.Connection,
    *,
    source: str | None = None,
    limit: int = 50,
) -> list[sqlite3.Row]:
    where_clause = ""
    params: list[object] = []
    if source:
        where_clause = "WHERE o.source = ?"
        params.append(source)
    params.append(limit)
    return conn.execute(
        f"""
        SELECT
            o.dedup_key,
            MIN(o.occurred_at) AS occurred_at,
            MIN(o.direction) AS direction,
            MIN(o.amount) AS amount,
            MIN(o.counterparty) AS counterparty,
            MIN(o.tx_type) AS tx_type,
            COUNT(*) AS duplicate_count,
            GROUP_CONCAT(sf.path, ' || ') AS file_paths
        FROM transaction_occurrences AS o
        JOIN source_files AS sf ON sf.id = o.file_id
        {where_clause}
        GROUP BY o.dedup_key
        HAVING COUNT(*) > 1
        ORDER BY duplicate_count DESC, occurred_at DESC
        LIMIT ?
        """,
        tuple(params),
    ).fetchall()
