"""Фонові задачі: нагадування клієнтам, «повторний запис», ранкове зведення власнику."""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, time, timedelta

from .db import parse_dt
from .telegram import ibtn, inline_kb
from .texts import Raw

log = logging.getLogger("barberbot.scheduler")


def in_window(now: datetime, start: time, hours: int) -> bool:
    """Чи зараз у проміжку [start, start + hours] цього дня (щоб не слати «Доброго ранку» о 15:00)."""
    begin = datetime.combine(now.date(), start)
    return begin <= now <= begin + timedelta(hours=hours)


class Scheduler:
    def __init__(self, app):
        self.app = app

    async def run(self) -> None:
        while not self.app.stopping:
            await self.tick_all()
            try:
                await asyncio.wait_for(self.app.stop_event.wait(), timeout=self.app.settings.scheduler_interval_sec)
            except asyncio.TimeoutError:
                pass

    async def tick_all(self) -> None:
        for slug in list(self.app.tenants):
            try:
                await self.reminders(slug)
                await self.nudges(slug)
                await self.digest(slug)
            except Exception:
                log.exception("Помилка планувальника для %s", slug)

    # ---------------------------------------------------------------- нагадування
    async def reminders(self, slug: str) -> None:
        app = self.app
        tenant, db = app.tenants[slug], app.db
        if not tenant.reminder_hours:
            return
        now = tenant.now()
        horizon = now + timedelta(hours=max(tenant.reminder_hours))
        for b in db.bookings_for_reminders(slug, now, horizon):
            sent = {s for s in (b["reminders_sent"] or "").split(",") if s}
            before = set(sent)
            start = parse_dt(b["start_at"])
            changed = parse_dt(b["updated_at"] or b["created_at"])
            due = []
            for hours in tenant.reminder_hours:
                key = str(hours)
                if key in sent:
                    continue
                moment = start - timedelta(hours=hours)
                if now < moment:
                    continue
                sent.add(key)
                if changed > moment:
                    continue  # запис зробили/перенесли вже після цього моменту — це нагадування зайве
                due.append(hours)
            if sent != before:
                db.set_booking_field(b["id"], "reminders_sent", ",".join(sorted(sent, key=int)))
            if due and not b["blocked"]:
                lang = b["lang"] or tenant.lang
                sent_msg = await app.send(tenant, b["tg_id"], app.reminder_text(tenant, b, lang),
                                          app.reminder_kb(tenant, b, lang))
                if sent_msg:
                    db.log_event(slug, b["client_id"], "reminder_sent", now, {"id": b["id"], "hours": min(due)})

    # ---------------------------------------------------------------- повторний запис
    async def nudges(self, slug: str) -> None:
        app = self.app
        tenant, db = app.tenants[slug], app.db
        if not tenant.repeat_enabled:
            return
        now = tenant.now()
        today = now.date().isoformat()
        if not in_window(now, tenant.repeat_send_at, hours=8) or db.kv_get(slug, "nudge_date") == today:
            return
        db.kv_set(slug, "nudge_date", today)
        newest_end = now - timedelta(days=tenant.repeat_after_days)
        oldest_end = newest_end - timedelta(days=14)
        for b in db.nudge_candidates(slug, oldest_end, newest_end, now):
            db.set_booking_field(b["id"], "nudged", 1)
            if b["service_id"] not in tenant.services:
                continue
            lang = b["lang"] or tenant.lang
            weeks = max(1, round((now - parse_dt(b["end_at"])).days / 7))
            name = b["client_name"] or b["first_name"] or ""
            master = b["master_id"] if b["master_id"] in tenant.masters else "any"
            kb = inline_kb([[ibtn(tenant.t(lang, "btn_book_again"), f"nb:{b['service_id']}:{master}")],
                            [ibtn(tenant.t(lang, "btn_no_nudges"), "noff")]])
            sent = await app.send(tenant, b["tg_id"], tenant.t(lang, "nudge", name=name, weeks=weeks,
                                                               service=b["service_title"]), kb)
            if sent:
                db.log_event(slug, b["client_id"], "nudge_sent", now, {"id": b["id"]})

    # ---------------------------------------------------------------- зведення власнику
    async def digest(self, slug: str) -> None:
        app = self.app
        tenant, db = app.tenants[slug], app.db
        if tenant.digest_at is None or not tenant.admins:
            return
        now = tenant.now()
        today = now.date().isoformat()
        if not in_window(now, tenant.digest_at, hours=3) or db.kv_get(slug, "digest_date") == today:
            return
        db.kv_set(slug, "digest_date", today)
        rows = app.bookings[slug].day_bookings(now.date(), include_noshow=False)
        body = app.render_day(tenant, now.date(), rows)
        for admin in tenant.admins:
            await app.send(tenant, admin, tenant.t(tenant.lang, "adm_digest", body=Raw(body)))
