"""Статистика для власника закладу (/stats) — головний аргумент для продажу."""

from __future__ import annotations

import json
from datetime import timedelta

from .config import Settings, Tenant, fmt_num
from .db import DB, dt_str, parse_dt


def compute_stats(db: DB, tenant: Tenant, settings: Settings, days: int = 30) -> dict:
    now = tenant.now()
    since = now - timedelta(days=days)
    since_ev = since.strftime("%Y-%m-%d %H:%M:%S")
    admins = set(tenant.admins)
    slug = tenant.slug

    created = [r for r in db.q(
        """SELECT b.*, c.tg_id FROM bookings b JOIN clients c ON c.id = b.client_id
           WHERE b.tenant = ? AND b.created_at >= ?""", slug, dt_str(since)) if r["tg_id"] not in admins]
    by_ai = sum(1 for r in created if r["source"] == "ai")
    by_buttons = sum(1 for r in created if r["source"] == "buttons")
    by_admin = sum(1 for r in created if r["source"] == "admin")
    night = sum(1 for r in created if parse_dt(r["created_at"]).hour >= 22 or parse_dt(r["created_at"]).hour < 8)
    cancelled = sum(1 for r in created if r["status"] == "cancelled")

    visits = [r for r in db.q(
        """SELECT b.*, c.tg_id FROM bookings b JOIN clients c ON c.id = b.client_id
           WHERE b.tenant = ? AND b.start_at >= ?""", slug, dt_str(since))
        if r["tg_id"] not in admins]
    done = sum(1 for r in visits if r["status"] == "active" and parse_dt(r["end_at"]) <= now)
    noshow = sum(1 for r in visits if r["status"] == "no_show")
    upcoming = db.scalar("SELECT COUNT(*) FROM bookings WHERE tenant = ? AND status = 'active' AND start_at > ?",
                         slug, dt_str(now))

    def client_ids(kind: str) -> set[int]:
        rows = db.q("""SELECT DISTINCT e.client_id, c.tg_id FROM events e JOIN clients c ON c.id = e.client_id
                       WHERE e.tenant = ? AND e.kind = ? AND e.created_at >= ?""", slug, kind, since_ev)
        return {r["client_id"] for r in rows if r["tg_id"] not in admins}

    wrote = client_ids("msg_in")
    handed = client_ids("handoff")
    handoffs = db.count_events(slug, "handoff", since)
    auto_rate = f"{round(100 * (len(wrote) - len(wrote & handed)) / len(wrote))}%" if wrote else "—"

    tokens = {"input": 0, "output": 0, "cache_read": 0, "cache_write": 0}
    for row in db.events_since(slug, "ai_usage", since):
        data = json.loads(row["data"] or "{}")
        for k in tokens:
            tokens[k] += int(data.get(k, 0) or 0)
    cost = (tokens["input"] * settings.price_input + tokens["output"] * settings.price_output
            + tokens["cache_read"] * settings.price_cache_read
            + tokens["cache_write"] * settings.price_cache_write) / 1_000_000

    return {
        "days": days,
        "created": len(created), "by_ai": by_ai, "by_buttons": by_buttons, "by_admin": by_admin, "night": night,
        "done": done, "noshow": noshow, "cancelled": cancelled, "upcoming": upcoming,
        "clients": len(wrote), "handoffs": handoffs, "auto_rate": auto_rate,
        "reminders": db.count_events(slug, "reminder_sent", since),
        "confirmed": db.count_events(slug, "reminder_confirmed", since),
        "ai_calls": db.count_events(slug, "ai_message", since),
        "tokens": fmt_num(sum(tokens.values())),
        "cost": f"{cost:.2f}",
    }
