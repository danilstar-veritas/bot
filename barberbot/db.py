"""Зберігання даних у SQLite (один файл data/bot.db для всіх закладів).

Усі дати/час зберігаються як місцевий час закладу у форматі "YYYY-MM-DD HH:MM".
Звернення до бази відбуваються лише з основного потоку asyncio, тому
перевірка вільного часу і створення запису виконуються атомарно.
"""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime
from pathlib import Path

DT_FMT = "%Y-%m-%d %H:%M"

SCHEMA = """
CREATE TABLE IF NOT EXISTS clients (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    tenant        TEXT NOT NULL,
    tg_id         INTEGER NOT NULL,
    first_name    TEXT,
    last_name     TEXT,
    username      TEXT,
    name          TEXT,
    phone         TEXT,
    lang          TEXT,
    created_at    TEXT NOT NULL,
    last_seen_at  TEXT,
    paused_until  TEXT,
    blocked       INTEGER NOT NULL DEFAULT 0,
    no_nudges     INTEGER NOT NULL DEFAULT 0,
    UNIQUE (tenant, tg_id)
);

CREATE TABLE IF NOT EXISTS bookings (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    tenant           TEXT NOT NULL,
    client_id        INTEGER NOT NULL REFERENCES clients(id),
    service_id       TEXT NOT NULL,
    master_id        TEXT NOT NULL,
    service_title    TEXT NOT NULL,
    master_name      TEXT NOT NULL,
    start_at         TEXT NOT NULL,
    end_at           TEXT NOT NULL,
    price            REAL NOT NULL DEFAULT 0,
    status           TEXT NOT NULL DEFAULT 'active',
    source           TEXT NOT NULL DEFAULT 'buttons',
    created_at       TEXT NOT NULL,
    updated_at       TEXT,
    cancelled_by     TEXT,
    reminders_sent   TEXT NOT NULL DEFAULT '',
    client_confirmed INTEGER NOT NULL DEFAULT 0,
    nudged           INTEGER NOT NULL DEFAULT 0
);
CREATE INDEX IF NOT EXISTS ix_bookings_tenant_start ON bookings (tenant, start_at);
CREATE INDEX IF NOT EXISTS ix_bookings_client ON bookings (client_id);

CREATE TABLE IF NOT EXISTS blocks (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    tenant      TEXT NOT NULL,
    master_id   TEXT,
    start_at    TEXT NOT NULL,
    end_at      TEXT NOT NULL,
    note        TEXT,
    created_at  TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS ix_blocks_tenant ON blocks (tenant, start_at);

CREATE TABLE IF NOT EXISTS history (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    tenant      TEXT NOT NULL,
    client_id   INTEGER NOT NULL,
    role        TEXT NOT NULL,
    content     TEXT NOT NULL,
    created_at  TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS ix_history_client ON history (client_id, id);

CREATE TABLE IF NOT EXISTS events (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    tenant      TEXT NOT NULL,
    client_id   INTEGER,
    kind        TEXT NOT NULL,
    data        TEXT,
    created_at  TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS ix_events_tenant_kind ON events (tenant, kind, created_at);
CREATE INDEX IF NOT EXISTS ix_events_client ON events (client_id, kind, created_at);

CREATE TABLE IF NOT EXISTS relay (
    tenant         TEXT NOT NULL,
    admin_chat_id  INTEGER NOT NULL,
    admin_msg_id   INTEGER NOT NULL,
    client_id      INTEGER NOT NULL,
    created_at     TEXT NOT NULL,
    PRIMARY KEY (tenant, admin_chat_id, admin_msg_id)
);

CREATE TABLE IF NOT EXISTS kv (
    tenant  TEXT NOT NULL,
    key     TEXT NOT NULL,
    value   TEXT,
    PRIMARY KEY (tenant, key)
);
"""


def dt_str(dt: datetime) -> str:
    return dt.strftime(DT_FMT)


def parse_dt(value: str) -> datetime:
    return datetime.strptime(value[:16], DT_FMT)


class DB:
    def __init__(self, path: str | Path):
        self.path = str(path)
        if self.path != ":memory:":
            Path(self.path).parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(self.path, isolation_level=None, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        if self.path != ":memory:":
            self.conn.execute("PRAGMA journal_mode=WAL")
        self.conn.execute("PRAGMA foreign_keys=ON")
        self.conn.executescript(SCHEMA)

    def close(self) -> None:
        self.conn.close()

    # ---------------------------------------------------------- basics
    def q(self, sql: str, *args) -> list[sqlite3.Row]:
        return self.conn.execute(sql, args).fetchall()

    def one(self, sql: str, *args) -> sqlite3.Row | None:
        return self.conn.execute(sql, args).fetchone()

    def x(self, sql: str, *args) -> int:
        return self.conn.execute(sql, args).lastrowid

    def scalar(self, sql: str, *args, default=0):
        row = self.conn.execute(sql, args).fetchone()
        return default if row is None or row[0] is None else row[0]

    # ---------------------------------------------------------- clients
    def upsert_client(self, tenant: str, tg_id: int, first_name: str | None, last_name: str | None,
                      username: str | None, lang: str | None, now: datetime) -> sqlite3.Row:
        ts = dt_str(now)
        self.conn.execute(
            """INSERT INTO clients (tenant, tg_id, first_name, last_name, username, lang, created_at, last_seen_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)
               ON CONFLICT (tenant, tg_id) DO UPDATE SET
                   first_name = excluded.first_name, last_name = excluded.last_name,
                   username = excluded.username, lang = excluded.lang,
                   last_seen_at = excluded.last_seen_at, blocked = 0""",
            (tenant, tg_id, first_name, last_name, username, lang, ts, ts),
        )
        return self.get_client_by_tg(tenant, tg_id)

    def get_client(self, client_id: int) -> sqlite3.Row | None:
        return self.one("SELECT * FROM clients WHERE id = ?", client_id)

    def get_client_by_tg(self, tenant: str, tg_id: int) -> sqlite3.Row | None:
        return self.one("SELECT * FROM clients WHERE tenant = ? AND tg_id = ?", tenant, tg_id)

    def set_client_field(self, client_id: int, field: str, value) -> None:
        if field not in {"name", "phone", "paused_until", "blocked", "no_nudges", "lang"}:
            raise ValueError(field)
        self.conn.execute(f"UPDATE clients SET {field} = ? WHERE id = ?", (value, client_id))

    # ---------------------------------------------------------- bookings
    def insert_booking(self, tenant: str, client_id: int, service_id: str, master_id: str, service_title: str,
                       master_name: str, start: datetime, end: datetime, price: float, source: str,
                       now: datetime) -> int:
        return self.x(
            """INSERT INTO bookings (tenant, client_id, service_id, master_id, service_title, master_name,
                                     start_at, end_at, price, status, source, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'active', ?, ?)""",
            tenant, client_id, service_id, master_id, service_title, master_name,
            dt_str(start), dt_str(end), price, source, dt_str(now),
        )

    def get_booking(self, booking_id: int) -> sqlite3.Row | None:
        return self.one("SELECT * FROM bookings WHERE id = ?", booking_id)

    def active_bookings_overlapping(self, tenant: str, start: datetime, end: datetime,
                                    master_id: str | None = None, exclude_id: int | None = None) -> list[sqlite3.Row]:
        sql = ("SELECT * FROM bookings WHERE tenant = ? AND status = 'active' "
               "AND start_at < ? AND end_at > ?")
        args: list = [tenant, dt_str(end), dt_str(start)]
        if master_id is not None:
            sql += " AND master_id = ?"
            args.append(master_id)
        if exclude_id is not None:
            sql += " AND id != ?"
            args.append(exclude_id)
        return self.q(sql + " ORDER BY start_at", *args)

    def bookings_between(self, tenant: str, start: datetime, end: datetime,
                         statuses: tuple[str, ...] = ("active", "no_show")) -> list[sqlite3.Row]:
        marks = ",".join("?" * len(statuses))
        return self.q(
            f"""SELECT b.*, c.first_name, c.last_name, c.username, c.name AS client_name, c.phone, c.tg_id
                FROM bookings b JOIN clients c ON c.id = b.client_id
                WHERE b.tenant = ? AND b.start_at >= ? AND b.start_at < ? AND b.status IN ({marks})
                ORDER BY b.start_at, b.master_id""",
            tenant, dt_str(start), dt_str(end), *statuses,
        )

    def client_upcoming(self, client_id: int, now: datetime) -> list[sqlite3.Row]:
        return self.q(
            "SELECT * FROM bookings WHERE client_id = ? AND status = 'active' AND start_at > ? ORDER BY start_at",
            client_id, dt_str(now),
        )

    def update_booking_status(self, booking_id: int, status: str, by: str | None, now: datetime) -> None:
        self.conn.execute(
            "UPDATE bookings SET status = ?, cancelled_by = ?, updated_at = ? WHERE id = ?",
            (status, by, dt_str(now), booking_id),
        )

    def update_booking_time(self, booking_id: int, master_id: str, master_name: str, start: datetime,
                            end: datetime, now: datetime) -> None:
        self.conn.execute(
            """UPDATE bookings SET master_id = ?, master_name = ?, start_at = ?, end_at = ?, updated_at = ?,
                   reminders_sent = '', client_confirmed = 0 WHERE id = ?""",
            (master_id, master_name, dt_str(start), dt_str(end), dt_str(now), booking_id),
        )

    def set_booking_field(self, booking_id: int, field: str, value) -> None:
        if field not in {"reminders_sent", "client_confirmed", "nudged"}:
            raise ValueError(field)
        self.conn.execute(f"UPDATE bookings SET {field} = ? WHERE id = ?", (value, booking_id))

    def bookings_for_reminders(self, tenant: str, now: datetime, horizon: datetime) -> list[sqlite3.Row]:
        return self.q(
            """SELECT b.*, c.tg_id, c.lang, c.blocked FROM bookings b JOIN clients c ON c.id = b.client_id
               WHERE b.tenant = ? AND b.status = 'active' AND b.start_at > ? AND b.start_at <= ?""",
            tenant, dt_str(now), dt_str(horizon),
        )

    def nudge_candidates(self, tenant: str, oldest_end: datetime, newest_end: datetime,
                         now: datetime) -> list[sqlite3.Row]:
        """Останній завершений візит клієнта був у вікні [oldest_end, newest_end], майбутніх записів немає."""
        return self.q(
            """SELECT b.*, c.tg_id, c.lang, c.first_name, c.name AS client_name
               FROM bookings b JOIN clients c ON c.id = b.client_id
               WHERE b.tenant = ? AND b.status = 'active' AND b.nudged = 0
                 AND b.end_at >= ? AND b.end_at <= ?
                 AND c.blocked = 0 AND c.no_nudges = 0
                 AND b.end_at = (SELECT MAX(b2.end_at) FROM bookings b2
                                 WHERE b2.client_id = b.client_id AND b2.status = 'active' AND b2.end_at <= ?)
                 AND NOT EXISTS (SELECT 1 FROM bookings b3 WHERE b3.client_id = b.client_id
                                 AND b3.status = 'active' AND b3.start_at > ?)""",
            tenant, dt_str(oldest_end), dt_str(newest_end), dt_str(now), dt_str(now),
        )

    # ---------------------------------------------------------- blocks
    def add_block(self, tenant: str, master_id: str | None, start: datetime, end: datetime,
                  note: str, now: datetime) -> int:
        return self.x(
            "INSERT INTO blocks (tenant, master_id, start_at, end_at, note, created_at) VALUES (?, ?, ?, ?, ?, ?)",
            tenant, master_id, dt_str(start), dt_str(end), note, dt_str(now),
        )

    def blocks_overlapping(self, tenant: str, start: datetime, end: datetime,
                           master_id: str | None) -> list[sqlite3.Row]:
        return self.q(
            """SELECT * FROM blocks WHERE tenant = ? AND start_at < ? AND end_at > ?
               AND (master_id IS NULL OR master_id = ?)""",
            tenant, dt_str(end), dt_str(start), master_id,
        )

    def future_blocks(self, tenant: str, now: datetime) -> list[sqlite3.Row]:
        return self.q("SELECT * FROM blocks WHERE tenant = ? AND end_at > ? ORDER BY start_at",
                      tenant, dt_str(now))

    def delete_block(self, tenant: str, block_id: int) -> bool:
        cur = self.conn.execute("DELETE FROM blocks WHERE tenant = ? AND id = ?", (tenant, block_id))
        return cur.rowcount > 0

    # ---------------------------------------------------------- AI history
    def add_history(self, tenant: str, client_id: int, role: str, content, now: datetime) -> None:
        self.conn.execute(
            "INSERT INTO history (tenant, client_id, role, content, created_at) VALUES (?, ?, ?, ?, ?)",
            (tenant, client_id, role, json.dumps(content, ensure_ascii=False), dt_str(now)),
        )

    def load_history(self, client_id: int, since: datetime, limit: int) -> list[dict]:
        rows = self.q(
            "SELECT role, content FROM history WHERE client_id = ? AND created_at >= ? ORDER BY id DESC LIMIT ?",
            client_id, dt_str(since), limit,
        )
        return [{"role": r["role"], "content": json.loads(r["content"])} for r in reversed(rows)]

    def has_recent_history(self, client_id: int, since: datetime) -> bool:
        return self.one("SELECT 1 FROM history WHERE client_id = ? AND created_at >= ? LIMIT 1",
                        client_id, dt_str(since)) is not None

    # ---------------------------------------------------------- events
    def log_event(self, tenant: str, client_id: int | None, kind: str, now: datetime, data=None) -> None:
        payload = None if data is None else json.dumps(data, ensure_ascii=False)
        self.conn.execute(
            "INSERT INTO events (tenant, client_id, kind, data, created_at) VALUES (?, ?, ?, ?, ?)",
            (tenant, client_id, kind, payload, now.strftime("%Y-%m-%d %H:%M:%S")),
        )

    def count_events(self, tenant: str, kind: str, since: datetime, client_id: int | None = None) -> int:
        if client_id is None:
            return self.scalar("SELECT COUNT(*) FROM events WHERE tenant = ? AND kind = ? AND created_at >= ?",
                               tenant, kind, since.strftime("%Y-%m-%d %H:%M:%S"))
        return self.scalar(
            "SELECT COUNT(*) FROM events WHERE client_id = ? AND kind = ? AND created_at >= ?",
            client_id, kind, since.strftime("%Y-%m-%d %H:%M:%S"),
        )

    def events_since(self, tenant: str, kind: str, since: datetime) -> list[sqlite3.Row]:
        return self.q("SELECT * FROM events WHERE tenant = ? AND kind = ? AND created_at >= ?",
                      tenant, kind, since.strftime("%Y-%m-%d %H:%M:%S"))

    def tokens_since(self, tenant: str, since: datetime) -> int:
        total = 0
        for row in self.events_since(tenant, "ai_usage", since):
            d = json.loads(row["data"] or "{}")
            total += int(d.get("input", 0)) + int(d.get("output", 0)) + int(d.get("cache_write", 0)) \
                + int(d.get("cache_read", 0))
        return total

    # ---------------------------------------------------------- relay & kv
    def add_relay(self, tenant: str, admin_chat_id: int, admin_msg_id: int, client_id: int, now: datetime) -> None:
        self.conn.execute(
            "INSERT OR REPLACE INTO relay (tenant, admin_chat_id, admin_msg_id, client_id, created_at) "
            "VALUES (?, ?, ?, ?, ?)",
            (tenant, admin_chat_id, admin_msg_id, client_id, dt_str(now)),
        )

    def get_relay(self, tenant: str, admin_chat_id: int, admin_msg_id: int) -> int | None:
        row = self.one("SELECT client_id FROM relay WHERE tenant = ? AND admin_chat_id = ? AND admin_msg_id = ?",
                       tenant, admin_chat_id, admin_msg_id)
        return row["client_id"] if row else None

    def kv_get(self, tenant: str, key: str, default: str | None = None) -> str | None:
        row = self.one("SELECT value FROM kv WHERE tenant = ? AND key = ?", tenant, key)
        return row["value"] if row else default

    def kv_set(self, tenant: str, key: str, value: str | None) -> None:
        self.conn.execute("INSERT OR REPLACE INTO kv (tenant, key, value) VALUES (?, ?, ?)", (tenant, key, value))
