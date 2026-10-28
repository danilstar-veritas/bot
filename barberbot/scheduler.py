"""Фонові задачі: нагадування клієнтам, «повторний запис», ранкове зведення власнику."""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, time, timedelta

from .agent import add_note
from .booking import BookingError
from .config import fmt_hhmm
from .db import parse_dt
from .stats import day_report
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
                await self.prepay_timeouts(slug)
                await self.reminders(slug)
                await self.nudges(slug)
                await self.digest(slug)
                await self.master_digest(slug)
                await self.master_heads_up(slug)
                await self.evening_report(slug)
            except Exception:
                log.exception("Помилка планувальника для %s", slug)

    # ---------------------------------------------------------------- неоплачені записи
    async def prepay_timeouts(self, slug: str) -> None:
        """Через prepay_hours після запису: не сплатили — скасувати; клієнт каже, що сплатив, а адмін ще
        не підтвердив, — не скасовуємо (гроші могли вже прийти), а один раз нагадуємо адмінам."""
        app = self.app
        tenant, db = app.tenants[slug], app.db
        if not tenant.prepay_enabled:
            return
        now = tenant.now()
        deadline = now - timedelta(hours=tenant.prepay_hours)
        for b in db.unpaid_overdue(slug, deadline, now, prepay="claimed"):
            key = f"prepay_reminded:{b['id']}"
            if db.kv_get(slug, key):
                continue
            db.kv_set(slug, key, "1")
            kb = inline_kb([[ibtn(tenant.t(tenant.lang, "btn_adm_prepay_ok"), f"aPy:{b['id']}")],
                            [ibtn(tenant.t(tenant.lang, "btn_adm_cancel_booking"), f"acx:{b['id']}")]])
            await app.notify_admins(tenant, tenant.t(
                tenant.lang, "adm_prepay_overdue", hours=tenant.prepay_hours,
                booking=Raw(app._booking_summary(tenant, b, db.get_client(b["client_id"])))), kb)
        for b in db.unpaid_overdue(slug, deadline, now, prepay="waiting"):
            try:
                app.bookings[slug].cancel(b["id"], "unpaid")
            except BookingError:
                continue
            start = parse_dt(b["start_at"])
            if b["tg_id"] > 0 and not b["blocked"]:
                lang = b["lang"] or tenant.lang
                await app.send(tenant, b["tg_id"], tenant.t(
                    lang, "client_cancelled_unpaid", **tenant.booking_names(b, lang),
                    day=tenant.day_label(start.date(), lang), time=fmt_hhmm(start)), tag="event")
            await app.notify_master(tenant, b, "mst_cancelled")
            client = db.get_client(b["client_id"])
            await app.notify_admins(tenant, tenant.t(tenant.lang, "adm_cancelled_unpaid", hours=tenant.prepay_hours,
                                                     booking=Raw(app._booking_summary(tenant, b, client))))
            add_note(db, tenant, b["client_id"],
                     f"Запис №{b['id']} скасовано автоматично: передоплату не отримано вчасно.", app.settings)

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
                                          app.reminder_kb(tenant, b, lang), tag="event")
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
            sent = await app.send(tenant, b["tg_id"], tenant.t(
                lang, "nudge", name=name, weeks=weeks,
                service=tenant.service_title(b["service_id"], lang, b["service_title"])), kb)
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

    # ---------------------------------------------------------------- майстрам
    async def master_digest(self, slug: str) -> None:
        """Зранку кожному підключеному майстру — його записи на сьогодні (якщо він сьогодні працює)."""
        app = self.app
        tenant, db = app.tenants[slug], app.db
        if tenant.digest_at is None:
            return
        now = tenant.now()
        today = now.date().isoformat()
        if not in_window(now, tenant.digest_at, hours=3):
            return
        for master_id in app.master_links(tenant):
            chat = app.master_chat(tenant, master_id)
            key = f"master_digest:{master_id}"
            if chat is None or db.kv_get(slug, key) == today:
                continue
            db.kv_set(slug, key, today)
            rows = [r for r in app.bookings[slug].day_bookings(now.date(), include_noshow=False)
                    if r["master_id"] == master_id]
            master = tenant.masters[master_id]
            if not rows and not tenant.master_intervals(master, now.date()):
                continue  # вихідний і записів немає
            body = app.master_day_text(tenant, master_id, now.date(), rows)
            await app.send(tenant, chat, tenant.t(tenant.lang, "mst_digest", name=master.name, body=Raw(body)))

    async def master_heads_up(self, slug: str) -> None:
        """За master_heads_up_min хвилин до візиту — коротке нагадування майстру, хто зараз прийде."""
        app = self.app
        tenant, db = app.tenants[slug], app.db
        minutes = tenant.master_heads_up_min
        if not minutes:
            return
        links = app.master_links(tenant)
        if not links:
            return
        now = tenant.now()
        for b in db.bookings_between(slug, now, now + timedelta(minutes=minutes) + timedelta(seconds=1),
                                     ("active",)):
            if b["master_reminded"] or b["master_id"] not in links or parse_dt(b["start_at"]) <= now:
                continue
            db.set_booking_field(b["id"], "master_reminded", 1)
            start = parse_dt(b["start_at"])
            text = tenant.t(tenant.lang, "mst_heads_up", time=fmt_hhmm(start),
                            min=max(1, int((start - now).total_seconds() // 60)),
                            client=app.client_label(tenant, b), service=b["service_title"])
            if b["note"]:
                text += tenant.t(tenant.lang, "adm_note_line", note=b["note"])
            # Нагадування особисте — надсилаємо і майстрові-адміністратору.
            await app.send(tenant, links[b["master_id"]], text,
                           inline_kb([[ibtn(tenant.t(tenant.lang, "btn_adm_open"), f"mK:{b['id']}")]]))

    # ---------------------------------------------------------------- вечірній підсумок
    async def evening_report(self, slug: str) -> None:
        app = self.app
        tenant, db = app.tenants[slug], app.db
        if tenant.report_at is None or not tenant.admins:
            return
        now = tenant.now()
        today = now.date().isoformat()
        if not in_window(now, tenant.report_at, hours=3) or db.kv_get(slug, "report_date") == today:
            return
        db.kv_set(slug, "report_date", today)
        await app.notify_admins(tenant, tenant.t(tenant.lang, "adm_evening_report", **day_report(db, tenant, now.date())))
