"""Панель адміністратора в Telegram: день із навігацією й фільтром за майстром, картка запису
(перенести, скасувати, неявка, оплата, клієнт), пошук клієнтів і їхня історія, вивантаження в Excel.

AdminPanel — домішка до BotApp: методи працюють із ботом через self (send, render_day тощо).
"""

from __future__ import annotations

from datetime import date, datetime, time, timedelta
from typing import TYPE_CHECKING

from .agent import add_note
from .booking import BookingError
from .config import fmt_hhmm
from .db import parse_dt
from .telegram import ibtn, inline_kb
from .texts import Raw
from .ui import Expired, _rows
from .xlsx import build_xlsx

if TYPE_CHECKING:
    from .app import Ctx

XLSX_MIME = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"


class AdminPanel:
    # ================================================================ день
    async def admin_day(self, ctx: Ctx, day: date, message_id: int | None, master: str = "*") -> None:
        """Записи на день: кнопка на кожен запис, ◀️ / ▶️ між днями, вибір дати, фільтр за майстром."""
        tenant = ctx.tenant
        if master not in tenant.masters:
            master = "*"
        rows = ctx.booking.day_bookings(day)
        if master != "*":
            rows = [r for r in rows if r["master_id"] == master]
        label = tenant.masters[master].name if master != "*" else ""
        text = self.render_day(tenant, day, rows, label)
        buttons = [[ibtn(ctx.at("btn_adm_booking_item", n=n, when=r["start_at"][11:16],
                                client=self._short_name(tenant, r)), f"aK:{r['id']}")]
                   for n, r in enumerate(rows, 1)]
        if buttons:
            text += ctx.at("adm_day_hint")
        prev, nxt = day - timedelta(days=1), day + timedelta(days=1)
        buttons.append([ibtn(ctx.at("btn_day_prev", day=tenant.day_button(prev, tenant.lang)), f"aD:{prev:%Y%m%d}:{master}"),
                        ibtn(ctx.at("btn_day_pick"), f"aDp:{master}"),
                        ibtn(ctx.at("btn_day_next", day=tenant.day_button(nxt, tenant.lang)), f"aD:{nxt:%Y%m%d}:{master}")])
        if len(tenant.masters) > 1:
            choices = [("*", ctx.at("btn_master_all"))] + [(m.id, m.name) for m in tenant.masters.values()]
            buttons += _rows([ibtn(ctx.at("btn_master_selected", name=name) if mid == master else name,
                                   f"aD:{day:%Y%m%d}:{mid}") for mid, name in choices], 3)
        await ctx.show(message_id, text, inline_kb(buttons))

    async def admin_day_picker(self, ctx: Ctx, master: str, message_id: int | None) -> None:
        tenant = ctx.tenant
        today = tenant.today()
        days = [today + timedelta(days=i) for i in range(-7, tenant.days_ahead)]
        buttons = _rows([ibtn(tenant.day_button(d, tenant.lang), f"aD:{d:%Y%m%d}:{master}") for d in days], 3)
        buttons.append([ibtn(ctx.at("btn_back"), f"aD:{today:%Y%m%d}:{master}")])
        await ctx.show(message_id, ctx.at("adm_day_pick"), inline_kb(buttons))

    # ================================================================ картка запису
    def _admin_booking(self, ctx: Ctx, booking_id: int):
        b = ctx.db.get_booking(booking_id)
        if b is None or b["tenant"] != ctx.tenant.slug:
            raise Expired()
        return b

    def booking_card_text(self, tenant, b, client) -> str:
        lang = tenant.lang
        text = tenant.t(lang, "adm_card", id=b["id"], summary=Raw(self._booking_summary(tenant, b, client)),
                        price=tenant.price_str(b["price"]))
        text += tenant.t(lang, f"adm_card_source_{b['source'] if b['source'] in ('ai', 'admin') else 'buttons'}")
        if b["status"] == "no_show":
            text += tenant.t(lang, "adm_card_noshow")
        elif b["status"] == "cancelled":
            by = b["cancelled_by"] if b["cancelled_by"] in ("admin", "unpaid") else "client"
            text += tenant.t(lang, "adm_card_cancelled", by=tenant.t(lang, f"adm_cancelled_by_{by}"))
        elif b["client_confirmed"]:
            text += tenant.t(lang, "adm_card_confirmed")
        if b["prepay"] and b["status"] == "active":
            text += tenant.t(lang, f"adm_prepay_{b['prepay']}")
        if b["note"]:
            text += tenant.t(lang, "adm_note_line", note=b["note"])
        return text

    async def admin_booking_card(self, ctx: Ctx, booking_id: int, message_id: int | None) -> None:
        tenant = ctx.tenant
        b = self._admin_booking(ctx, booking_id)
        client = ctx.db.get_client(b["client_id"])
        start = parse_dt(b["start_at"])
        rows = []
        if b["status"] == "active" and start > tenant.now():
            rows.append([ibtn(ctx.at("btn_adm_resched"), f"aRs:{b['id']}"),
                         ibtn(ctx.at("btn_adm_cancel_short"), f"acx:{b['id']}")])
        if b["status"] == "active" and start.date() <= tenant.today():
            rows.append([ibtn(ctx.at("btn_adm_noshow"), f"ans:{b['id']}")])
        if b["status"] == "active" and b["prepay"] in ("waiting", "claimed"):
            rows.append([ibtn(ctx.at("btn_adm_prepay_ok"), f"aPy:{b['id']}")])
        if client is not None:
            people = [ibtn(ctx.at("btn_adm_client"), f"aC:{client['id']}")]
            if client["tg_id"] > 0:
                people.append(ibtn(ctx.at("btn_adm_write"), f"ar:{client['id']}"))
            rows.append(people)
        await ctx.show(message_id, self.booking_card_text(tenant, b, client), inline_kb(rows))

    # ================================================================ перенесення
    def _resched_target(self, ctx: Ctx, booking_id: int):
        b = self._admin_booking(ctx, booking_id)
        if b["status"] != "active" or parse_dt(b["start_at"]) <= ctx.tenant.now() \
                or b["service_id"] not in ctx.tenant.services:
            raise Expired()
        master = b["master_id"] if b["master_id"] in ctx.tenant.masters else "any"
        return b, master

    async def admin_resched_days(self, ctx: Ctx, booking_id: int, message_id: int | None, prefix: str = "") -> None:
        tenant = ctx.tenant
        b, master = self._resched_target(ctx, booking_id)
        days = ctx.booking.available_days(b["service_id"], master, exclude_id=b["id"], admin=True)
        summary = Raw(self._booking_summary(tenant, b, ctx.db.get_client(b["client_id"])))
        back = [ibtn(ctx.at("btn_back"), f"aKe:{b['id']}")]
        if not days:
            await ctx.show(message_id, ctx.at("adm_resched_none", summary=summary), inline_kb([back]))
            return
        buttons = [ibtn(tenant.day_button(d, tenant.lang), f"aRd:{b['id']}:{d:%Y%m%d}") for d in days]
        text = (prefix + "\n\n" if prefix else "") + ctx.at("adm_resched_day", id=b["id"], summary=summary)
        await ctx.show(message_id, text, inline_kb(_rows(buttons, 3) + [back]))

    async def admin_resched_times(self, ctx: Ctx, booking_id: int, day: date, message_id: int | None,
                                  prefix: str = "") -> None:
        tenant = ctx.tenant
        b, master = self._resched_target(ctx, booking_id)
        slots = ctx.booking.free_slots(b["service_id"], master, day, exclude_id=b["id"], admin=True)
        if not slots:
            await self.admin_resched_days(ctx, booking_id, message_id,
                                          prefix=ctx.at("no_times", day=tenant.day_label(day, tenant.lang)))
            return
        buttons = [ibtn(t, f"aRt:{b['id']}:{day:%Y%m%d}:{t.replace(':', '')}") for t in slots]
        text = (prefix + "\n\n" if prefix else "") + ctx.at(
            "adm_resched_time", id=b["id"], service=b["service_title"], master=b["master_name"],
            day=tenant.day_label(day, tenant.lang))
        await ctx.show(message_id, text, inline_kb(_rows(buttons, 4) + [[ibtn(ctx.at("btn_back"), f"aRs:{b['id']}")]]))

    def _when_full(self, tenant, start: datetime, master: str) -> str:
        return f"{tenant.day_label(start.date(), tenant.lang)}, {fmt_hhmm(start)} · {master}"

    async def admin_resched_confirm(self, ctx: Ctx, booking_id: int, start: datetime, message_id: int | None) -> None:
        tenant = ctx.tenant
        b, master = self._resched_target(ctx, booking_id)
        try:
            _, resolved = ctx.booking.validate_reschedule(b["id"], start, master, None, admin=True)
        except BookingError as e:
            await self._resched_failed(ctx, e, b["id"], start.date(), message_id)
            return
        client = ctx.db.get_client(b["client_id"])
        offline = client is None or client["tg_id"] < 0
        text = ctx.at("adm_resched_confirm", service=b["service_title"], client=self.client_label(tenant, client)
                      if client else "", old=self._when_full(tenant, parse_dt(b["start_at"]), b["master_name"]),
                      new=self._when_full(tenant, start, tenant.masters[resolved].name),
                      who=Raw(ctx.at("adm_cancel_offline" if offline else "adm_cancel_notify")))
        when = f"{start:%Y%m%d}:{start:%H%M}"
        kb = inline_kb([[ibtn(ctx.at("btn_adm_resched_yes"), f"aRy:{b['id']}:{when}")],
                        [ibtn(ctx.at("btn_other_time"), f"aRd:{b['id']}:{start:%Y%m%d}")]])
        await ctx.show(message_id, text, kb)

    async def _resched_failed(self, ctx: Ctx, e: BookingError, booking_id: int, day: date,
                              message_id: int | None) -> None:
        if e.code == "same_time":
            await ctx.show(message_id, ctx.at("adm_resched_same"))
        elif e.code in ("inactive", "not_found", "no_service"):
            raise Expired()
        else:
            await self.admin_resched_times(ctx, booking_id, day, message_id, prefix=ctx.at("slot_taken"))

    async def admin_resched_do(self, ctx: Ctx, booking_id: int, start: datetime, message_id: int | None) -> None:
        tenant = ctx.tenant
        b, master = self._resched_target(ctx, booking_id)
        try:
            old, new = ctx.booking.reschedule(b["id"], start, master, None, admin=True)
        except BookingError as e:
            await self._resched_failed(ctx, e, b["id"], start.date(), message_id)
            return
        client = ctx.db.get_client(new["client_id"])
        offline = client is None or client["tg_id"] < 0
        old_text = self._when_full(tenant, parse_dt(old["start_at"]), old["master_name"])
        await ctx.show(message_id, ctx.at("adm_resched_done", summary=Raw(self._booking_summary(tenant, new, client)),
                                          old=old_text, who=Raw(ctx.at("adm_resched_offline" if offline
                                                                       else "adm_resched_notified"))))
        await self.notify_master_resched(tenant, old, new)
        if client and not offline and not client["blocked"]:
            lang = client["lang"] or tenant.lang
            await self.send(tenant, client["tg_id"], tenant.t(
                lang, "client_rescheduled_by_admin", service=new["service_title"], master=new["master_name"],
                old=f"{tenant.day_label(parse_dt(old['start_at']).date(), lang)}, {old['start_at'][11:16]}",
                new=f"{tenant.day_label(start.date(), lang)}, {fmt_hhmm(start)}"))
            add_note(ctx.db, tenant, client["id"], f"Адміністратор переніс запис №{new['id']} на "
                     f"{start:%d.%m.%Y} о {fmt_hhmm(start)} ({new['master_name']}).", self.settings)

    # ================================================================ клієнти
    async def admin_find(self, ctx: Ctx, query: str) -> None:
        if not query.strip():
            await ctx.send(ctx.at("adm_find_usage"))
            return
        found = ctx.db.search_clients(ctx.tenant.slug, query)
        if not found:
            await ctx.send(ctx.at("adm_find_none", q=query.strip()))
        elif len(found) == 1:
            await self.admin_client_card(ctx, found[0]["id"], None)
        else:
            buttons = [[ibtn(ctx.at("btn_adm_client_item", label=self.client_label(ctx.tenant, c)), f"aC:{c['id']}")]
                       for c in found]
            await ctx.send(ctx.at("adm_find_many", count=len(found)), inline_kb(buttons))

    def _client_name(self, tenant, c) -> str:
        return c["name"] or " ".join(p for p in (c["first_name"], c["last_name"]) if p) \
            or tenant.t(tenant.lang, "adm_client_noname")

    async def admin_client_card(self, ctx: Ctx, client_id: int, message_id: int | None) -> None:
        tenant, db = ctx.tenant, ctx.db
        c = db.get_client(client_id)
        if c is None or c["tenant"] != tenant.slug:
            raise Expired()
        now = tenant.now()
        bookings = db.client_bookings(c["id"])
        done = [b for b in bookings if b["status"] == "active" and parse_dt(b["end_at"]) <= now]
        upcoming = [b for b in bookings if b["status"] == "active" and parse_dt(b["start_at"]) > now]
        notes = list(dict.fromkeys(b["note"] for b in reversed(bookings) if b["note"]))[:3]
        contacts = " · ".join(p for p in (f"@{c['username']}" if c["username"] else "", c["phone"] or "") if p)
        last = Raw(ctx.at("adm_client_last", day=tenant.day_label(parse_dt(done[-1]["start_at"]).date(), tenant.lang),
                          service=done[-1]["service_title"])) if done else ""
        items = "".join(ctx.at("adm_client_upcoming_item", when=self._when_full(tenant, parse_dt(b["start_at"]),
                                                                               b["master_name"]),
                               service=b["service_title"]) for b in upcoming)
        text = ctx.at("adm_client_card", name=self._client_name(tenant, c), contacts=contacts or "—",
                      tg=Raw(ctx.at("adm_client_tg_yes" if c["tg_id"] > 0 else "adm_client_tg_no")),
                      done=len(done), noshow=sum(1 for b in bookings if b["status"] == "no_show"),
                      cancelled=sum(1 for b in bookings if b["status"] == "cancelled"),
                      spent=tenant.price_str(round(sum(b["price"] or 0 for b in done))), last=last,
                      upcoming=Raw(ctx.at("adm_client_upcoming", items=Raw(items))) if upcoming else "",
                      notes=Raw(ctx.at("adm_client_notes", notes="; ".join(notes))) if notes else "")
        buttons = [[ibtn(ctx.at("btn_adm_client_booking", when=f"{b['start_at'][8:10]}.{b['start_at'][5:7]} "
                                                                 f"{b['start_at'][11:16]}", service=b["service_title"]),
                         f"aK:{b['id']}")] for b in upcoming[:10]]
        actions = [ibtn(ctx.at("btn_adm_client_book"), f"aCb:{c['id']}")]
        if c["tg_id"] > 0:
            actions.append(ibtn(ctx.at("btn_adm_write"), f"ar:{c['id']}"))
        buttons.append(actions)
        await ctx.show(message_id, text, inline_kb(buttons))

    async def admin_book_for_client(self, ctx: Ctx, client_id: int) -> None:
        """«📞 Записати» з картки клієнта — /book, де дані клієнта вже заповнено."""
        c = ctx.db.get_client(client_id)
        if c is None or c["tenant"] != ctx.tenant.slug:
            raise Expired()
        self.states[ctx.key] = ("admin_book_client", {
            "client_id": c["id"], "name": self._client_name(ctx.tenant, c), "phone": c["phone"],
            "tg_id": c["tg_id"] if c["tg_id"] > 0 else None, "note": ""})
        await self.admin_book_services(ctx, None)

    # ================================================================ Excel
    async def admin_export(self, ctx: Ctx, args: str) -> None:
        tenant = ctx.tenant
        try:
            days = max(1, min(int(args.strip() or 30), 3650))
        except ValueError:
            await ctx.send(ctx.at("adm_export_usage"))
            return
        today = tenant.today()
        start = today - timedelta(days=days)
        rows = ctx.db.bookings_between(tenant.slug, datetime.combine(start, time.min),
                                       datetime.combine(today, time.min) + timedelta(days=3650),
                                       ("active", "no_show", "cancelled"))
        if not rows:
            await ctx.send(ctx.at("adm_export_empty"))
            return
        now = tenant.now()
        statuses = ctx.at("adm_export_statuses").split("|")      # заплановано|відбувся|не прийшов|скасовано
        sources = ctx.at("adm_export_sources").split("|")        # сам|AI-чат|адмін
        prepays = ctx.at("adm_export_prepay").split("|")         # очікуємо|каже, що оплатив|оплачено
        data = []
        for r in rows:
            if r["status"] == "cancelled":
                status = statuses[3]
            elif r["status"] == "no_show":
                status = statuses[2]
            else:
                status = statuses[1] if parse_dt(r["end_at"]) <= now else statuses[0]
            name = r["client_name"] or " ".join(p for p in (r["first_name"], r["last_name"]) if p)
            data.append([
                f"{r['start_at'][8:10]}.{r['start_at'][5:7]}.{r['start_at'][:4]}", r["start_at"][11:16],
                r["end_at"][11:16], r["master_name"], r["service_title"], r["price"], status, name,
                r["phone"] or "", f"@{r['username']}" if r["username"] else "",
                {"ai": sources[1], "admin": sources[2]}.get(r["source"], sources[0]),
                {"waiting": prepays[0], "claimed": prepays[1], "paid": prepays[2]}.get(r["prepay"], ""),
                r["note"] or "", r["created_at"],
            ])
        content = build_xlsx(ctx.at("adm_export_headers").split("|"), data, sheet=ctx.at("adm_export_sheet"),
                             widths=[11, 7, 7, 12, 30, 9, 13, 20, 16, 18, 10, 18, 30, 17])
        await ctx.api.send_document(ctx.chat_id, f"bookings-{start:%Y-%m-%d}-{today:%Y-%m-%d}.xlsx", content,
                                    caption=ctx.at("adm_export_caption", count=len(data),
                                                   start=f"{start:%d.%m.%Y}", today=f"{today:%d.%m.%Y}"),
                                    mime=XLSX_MIME)
