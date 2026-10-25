"""Бізнес-логіка записів: вільний час, створення, перенесення, скасування.

Записи створює лише цей код — ні кнопки, ні AI не можуть обійти перевірки.
"""

from __future__ import annotations

import sqlite3
from datetime import date, datetime, time, timedelta

from .config import Master, Service, Tenant, fmt_hhmm
from .db import DB, parse_dt
from .slots import Interval, free_starts


class BookingError(Exception):
    """code: no_service, no_master, master_no_service, past, too_soon, too_far, slot_taken,
    too_many, week_limit, duplicate, not_found, inactive, too_late, same_time"""

    def __init__(self, code: str, **info):
        super().__init__(code)
        self.code = code
        self.info = info


class BookingService:
    def __init__(self, tenant: Tenant, db: DB):
        self.tenant = tenant
        self.db = db

    # ------------------------------------------------------------ basics
    @property
    def slug(self) -> str:
        return self.tenant.slug

    def service(self, service_id: str) -> Service:
        svc = self.tenant.services.get(service_id)
        if svc is None:
            raise BookingError("no_service")
        return svc

    def master(self, master_id: str) -> Master:
        m = self.tenant.masters.get(master_id)
        if m is None:
            raise BookingError("no_master")
        return m

    def last_day(self) -> date:
        return self.tenant.today() + timedelta(days=self.tenant.days_ahead - 1)

    def horizon_days(self) -> list[date]:
        today = self.tenant.today()
        return [today + timedelta(days=i) for i in range(self.tenant.days_ahead)]

    def not_before(self, admin: bool = False) -> datetime:
        """Найраніший час запису. Адміністратор може записати й на найближчий вільний час."""
        return self.tenant.now() if admin else self.tenant.now() + timedelta(minutes=self.tenant.min_lead_min)

    def masters_for_sel(self, service_id: str, master_sel: str | None) -> list[Master]:
        svc = self.service(service_id)
        if svc.hidden and not svc.base_id:
            raise BookingError("no_service")  # послуга «лише додатком» — окремо на неї не записують
        if master_sel in (None, "", "any"):
            return self.tenant.masters_for(service_id)
        m = self.master(master_sel)
        if service_id not in m.services:
            raise BookingError("master_no_service", master=m.name)
        return [m]

    # ------------------------------------------------------------ free time
    def _busy(self, master_id: str, day: date, exclude_id: int | None = None) -> list[Interval]:
        day_start = datetime.combine(day, time.min)
        day_end = day_start + timedelta(days=1)
        buf = timedelta(minutes=self.tenant.buffer_min)
        busy: list[Interval] = []
        for b in self.db.active_bookings_overlapping(self.slug, day_start - buf, day_end + buf, master_id, exclude_id):
            busy.append((parse_dt(b["start_at"]) - buf, parse_dt(b["end_at"]) + buf))
        for bl in self.db.blocks_overlapping(self.slug, day_start, day_end, master_id):
            busy.append((parse_dt(bl["start_at"]), parse_dt(bl["end_at"])))
        return busy

    def master_slots(self, service: Service, master: Master, day: date,
                     exclude_id: int | None = None, admin: bool = False) -> list[datetime]:
        if service.id not in master.services:
            return []
        if day < self.tenant.today() or day > self.last_day():
            return []
        work = self.tenant.master_intervals(master, day)
        if not work:
            return []
        return free_starts(work, self._busy(master.id, day, exclude_id), service.duration,
                           self.tenant.slot_step_min, self.not_before(admin))

    def free_slots(self, service_id: str, master_sel: str | None, day: date,
                   exclude_id: int | None = None, admin: bool = False) -> dict[str, list[str]]:
        """{"10:00": ["andriy", "oleg"], "10:30": ["oleg"], ...} — у порядку часу."""
        service = self.service(service_id)
        result: dict[str, list[str]] = {}
        for m in self.masters_for_sel(service_id, master_sel):
            for t in self.master_slots(service, m, day, exclude_id, admin):
                result.setdefault(fmt_hhmm(t), []).append(m.id)
        return dict(sorted(result.items()))

    def available_days(self, service_id: str, master_sel: str | None, exclude_id: int | None = None,
                       limit: int | None = None, admin: bool = False) -> list[date]:
        days: list[date] = []
        for d in self.horizon_days():
            if self.free_slots(service_id, master_sel, d, exclude_id, admin):
                days.append(d)
                if limit and len(days) >= limit:
                    break
        return days

    def _day_load(self, master_id: str, day: date) -> int:
        start = datetime.combine(day, time.min)
        return len(self.db.active_bookings_overlapping(self.slug, start, start + timedelta(days=1), master_id))

    def resolve_master(self, service_id: str, master_sel: str | None, start: datetime,
                       exclude_id: int | None = None, admin: bool = False) -> str | None:
        """Конкретний майстер, вільний на цей час.

        Для «будь-якого» — той, у кого найменше майбутніх записів; при рівності — у кого менше записів
        цього дня, далі — кому найдавніше давали запис (по черзі), і лише потім — порядок у налаштуваннях.
        """
        service = self.service(service_id)
        now = self.tenant.now()
        candidates = []
        for m in self.masters_for_sel(service_id, master_sel):
            if start in self.master_slots(service, m, start.date(), exclude_id, admin):
                candidates.append((self.db.master_upcoming_count(self.slug, m.id, now, exclude_id),
                                   self._day_load(m.id, start.date()),
                                   self.db.master_last_booked(self.slug, m.id),
                                   list(self.tenant.masters).index(m.id), m.id))
        if not candidates:
            return None
        return min(candidates)[-1]

    def _check_week_limit(self, client_id: int, start: datetime, exclude_id: int | None = None) -> None:
        """Не більше max_per_week записів одного клієнта на календарний тиждень (пн–нд) за датою візиту."""
        limit = self.tenant.max_per_week
        if not limit:
            return
        monday = datetime.combine(start.date() - timedelta(days=start.weekday()), time.min)
        count = self.db.client_bookings_count(client_id, monday, monday + timedelta(days=7), exclude_id)
        if count >= limit:
            raise BookingError("week_limit", count=count, limit=limit)

    def _check_window(self, start: datetime, admin: bool = False) -> None:
        now = self.tenant.now()
        if start <= now:
            raise BookingError("past")
        if start < self.not_before(admin):
            raise BookingError("too_soon", minutes=self.tenant.min_lead_min)
        if start.date() > self.last_day():
            raise BookingError("too_far", days=self.tenant.days_ahead)

    # ------------------------------------------------------------ create
    def validate_new(self, client_id: int, service_id: str, master_sel: str | None,
                     start: datetime, admin: bool = False) -> str:
        """Перевіряє, чи можна записатися. Повертає id конкретного майстра.

        admin=True — записує адміністратор: без ліміту записів на клієнта і без мінімального часу до початку.
        """
        self.masters_for_sel(service_id, master_sel)
        service = self.service(service_id)
        now = self.tenant.now()
        upcoming = self.db.client_upcoming(client_id, now)
        end = start + timedelta(minutes=service.duration)
        for b in upcoming:
            if parse_dt(b["start_at"]) < end and start < parse_dt(b["end_at"]):
                raise BookingError("duplicate", booking_id=b["id"])
        if not admin and self.tenant.max_active_per_client and len(upcoming) >= self.tenant.max_active_per_client:
            raise BookingError("too_many", count=len(upcoming))
        if not admin:
            self._check_week_limit(client_id, start)
        self._check_window(start, admin)
        master_id = self.resolve_master(service_id, master_sel, start, admin=admin)
        if master_id is None:
            raise BookingError("slot_taken")
        return master_id

    def create(self, client_id: int, service_id: str, master_id: str, start: datetime,
               source: str) -> sqlite3.Row:
        resolved = self.validate_new(client_id, service_id, master_id, start, admin=source == "admin")
        service = self.service(service_id)
        master = self.master(resolved)
        now = self.tenant.now()
        end = start + timedelta(minutes=service.duration)
        booking_id = self.db.insert_booking(self.slug, client_id, service.id, master.id, service.title,
                                            master.name, start, end, service.price, source, now)
        if self.tenant.prepay_enabled and source in ("buttons", "ai"):
            # Записався сам — потрібна передоплата (запис, зроблений адміном, її не потребує).
            self.db.set_booking_field(booking_id, "prepay", "waiting")
        self.db.log_event(self.slug, client_id, "booking_created", now, {"id": booking_id, "source": source})
        return self.db.get_booking(booking_id)

    # ------------------------------------------------------------ cancel / reschedule
    def _own_active(self, booking_id: int, client_id: int | None) -> sqlite3.Row:
        b = self.db.get_booking(booking_id)
        if b is None or b["tenant"] != self.slug or (client_id is not None and b["client_id"] != client_id):
            raise BookingError("not_found")
        if b["status"] != "active" or parse_dt(b["start_at"]) <= self.tenant.now():
            raise BookingError("inactive")
        return b

    def _check_late(self, booking: sqlite3.Row) -> None:
        hours = self.tenant.cancel_min_hours
        if hours and parse_dt(booking["start_at"]) - self.tenant.now() < timedelta(hours=hours):
            raise BookingError("too_late", hours=hours)

    def validate_cancel(self, booking_id: int, client_id: int | None) -> sqlite3.Row:
        b = self._own_active(booking_id, client_id)
        if client_id is not None:
            self._check_late(b)
        return b

    def cancel(self, booking_id: int, by: str, client_id: int | None = None) -> sqlite3.Row:
        b = self.validate_cancel(booking_id, client_id if by == "client" else None)
        now = self.tenant.now()
        self.db.update_booking_status(b["id"], "cancelled", by, now)
        self.db.log_event(self.slug, b["client_id"], "booking_cancelled", now, {"id": b["id"], "by": by})
        return self.db.get_booking(b["id"])

    def validate_reschedule(self, booking_id: int, start: datetime, master_sel: str | None,
                            client_id: int | None, admin: bool = False) -> tuple[sqlite3.Row, str]:
        """client_id=None — переносить адміністратор; admin=True — ще й без мінімального часу до початку."""
        b = self._own_active(booking_id, client_id)
        if client_id is not None:
            self._check_late(b)
            self._check_week_limit(b["client_id"], start, exclude_id=b["id"])
        self.service(b["service_id"])
        if master_sel in (None, ""):
            master_sel = b["master_id"] if b["master_id"] in self.tenant.masters else "any"
        self._check_window(start, admin)
        resolved = self.resolve_master(b["service_id"], master_sel, start, exclude_id=b["id"], admin=admin)
        if resolved is None:
            raise BookingError("slot_taken")
        if resolved == b["master_id"] and start == parse_dt(b["start_at"]):
            raise BookingError("same_time")
        return b, resolved

    def reschedule(self, booking_id: int, start: datetime, master_sel: str | None,
                   client_id: int | None, admin: bool = False) -> tuple[sqlite3.Row, sqlite3.Row]:
        """Повертає (старий запис, оновлений запис)."""
        old, master_id = self.validate_reschedule(booking_id, start, master_sel, client_id, admin)
        service = self.service(old["service_id"])
        master = self.master(master_id)
        now = self.tenant.now()
        self.db.update_booking_time(old["id"], master.id, master.name, start,
                                    start + timedelta(minutes=service.duration), now)
        self.db.log_event(self.slug, old["client_id"], "booking_rescheduled", now,
                          {"id": old["id"], "from": old["start_at"]})
        return old, self.db.get_booking(old["id"])

    # ------------------------------------------------------------ other
    def upcoming_for_client(self, client_id: int) -> list[sqlite3.Row]:
        return self.db.client_upcoming(client_id, self.tenant.now())

    def day_bookings(self, day: date, include_noshow: bool = True) -> list[sqlite3.Row]:
        start = datetime.combine(day, time.min)
        statuses = ("active", "no_show") if include_noshow else ("active",)
        return self.db.bookings_between(self.slug, start, start + timedelta(days=1), statuses)

    def prepay_deadline(self, booking) -> datetime:
        """До коли треба внести передоплату: через prepay_hours після запису, але не пізніше початку візиту."""
        return min(parse_dt(booking["created_at"]) + timedelta(hours=self.tenant.prepay_hours),
                   parse_dt(booking["start_at"]))

    def mark_no_show(self, booking_id: int) -> sqlite3.Row:
        b = self.db.get_booking(booking_id)
        if b is None or b["tenant"] != self.slug or b["status"] not in ("active", "no_show"):
            raise BookingError("not_found")
        now = self.tenant.now()
        self.db.update_booking_status(booking_id, "no_show", "admin", now)
        self.db.log_event(self.slug, b["client_id"], "no_show", now, {"id": booking_id})
        return self.db.get_booking(booking_id)

    def add_block(self, master_id: str | None, start: datetime, end: datetime,
                  note: str) -> tuple[int, list[sqlite3.Row]]:
        now = self.tenant.now()
        block_id = self.db.add_block(self.slug, master_id, start, end, note, now)
        conflicts = self.db.active_bookings_overlapping(self.slug, start, end, master_id)
        return block_id, conflicts
