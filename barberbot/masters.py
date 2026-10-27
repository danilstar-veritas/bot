"""Майстри в боті: підключення за одноразовим посиланням, свій день і тиждень, неявка,
закрити/відкрити свій час, сповіщення майстру про записи.

MasterPanel — домішка до BotApp, як і AdminPanel. Зв'язок «майстер → Telegram» зберігається в kv:
master_tg:{id майстра} = Telegram ID, запрошення — master_invite:{код} = {master, until}.
"""

from __future__ import annotations

import json
import logging
import secrets
from datetime import date, datetime, time, timedelta
from typing import TYPE_CHECKING

from .config import fmt_hhmm
from .db import parse_dt
from .telegram import NetworkError, TelegramError, ibtn, inline_kb, reply_kb
from .texts import Raw
from .ui import Expired, _d, _int, _rows, _t

if TYPE_CHECKING:
    from .app import Ctx
    from .config import Tenant

log = logging.getLogger("barberbot")

MASTER_COMMANDS = ["start", "my", "myweek", "off", "offs", "myid"]
MASTER_MENU = ("btn_mst_day", "btn_mst_week", "btn_mst_off", "btn_mst_offs")
INVITE_HOURS = 48
OFF_DAYS = 28  # на скільки днів уперед майстер може закрити свій час


class MasterPanel:
    # ================================================================ зв'язок майстер ↔ Telegram
    def master_links(self, tenant: Tenant) -> dict[str, int]:
        """id майстра → Telegram ID (лише майстри, які є в налаштуваннях закладу)."""
        links = {}
        for key, value in self.db.kv_prefix(tenant.slug, "master_tg:").items():
            mid = key.split(":", 1)[1]
            if mid in tenant.masters and value:
                links[mid] = int(value)
        return links

    def master_of(self, tenant: Tenant, user_id: int) -> str | None:
        return next((mid for mid, tg in self.master_links(tenant).items() if tg == user_id), None)

    async def bot_username(self, tenant: Tenant) -> str:
        if not self.usernames.get(tenant.slug):
            try:
                me = await self.apis[tenant.slug].call("getMe")
                self.usernames[tenant.slug] = me.get("username", "")
            except (TelegramError, NetworkError):
                return ""
        return self.usernames[tenant.slug]

    async def chat_commands(self, tenant: Tenant, chat_id: int, master: bool) -> None:
        """Меню команд у чаті конкретної людини: адмінські, майстра, обидва або звичайне."""
        from .app import ADMIN_COMMANDS

        names = list(ADMIN_COMMANDS) if chat_id in tenant.admins else []
        if master:
            names += [c for c in MASTER_COMMANDS if c not in names]
        scope = {"type": "chat", "chat_id": chat_id}
        api = self.apis[tenant.slug]
        if names:
            await api.call("setMyCommands", scope=scope,
                           commands=[{"command": c, "description": tenant.t(tenant.lang, f"cmd_{c}")} for c in names])
        else:
            await api.call("deleteMyCommands", scope=scope)

    async def _chat_commands_quiet(self, tenant: Tenant, chat_id: int, master: bool) -> None:
        try:
            await self.chat_commands(tenant, chat_id, master)
        except (TelegramError, NetworkError) as e:
            log.info("[%s] Меню команд для %s: %s", tenant.name, chat_id, e)

    # ================================================================ адмін: /masters
    async def admin_masters(self, ctx: Ctx, message_id: int | None) -> None:
        tenant = ctx.tenant
        links = self.master_links(tenant)
        items, buttons = "", []
        for m in tenant.masters.values():
            tg = links.get(m.id)
            if tg:
                client = ctx.db.get_client_by_tg(tenant.slug, tg)
                who = self.client_label(tenant, client) if client else str(tg)
                items += ctx.at("adm_masters_on", name=m.name, who=who)
                buttons.append(ibtn(ctx.at("btn_adm_master_unlink", name=m.name), f"aMu:{m.id}"))
            else:
                items += ctx.at("adm_masters_off", name=m.name)
                buttons.append(ibtn(ctx.at("btn_adm_master_invite", name=m.name), f"aMi:{m.id}"))
        await ctx.show(message_id, ctx.at("adm_masters", items=Raw(items)), inline_kb(_rows(buttons, 1)))

    async def admin_master_invite(self, ctx: Ctx, master_id: str) -> None:
        tenant = ctx.tenant
        master = tenant.masters.get(master_id)
        if master is None:
            raise Expired()
        username = await self.bot_username(tenant)
        if not username:
            await ctx.send(ctx.at("adm_master_no_username"))
            return
        # Попередні невикористані запрошення цього майстра більше не діють.
        for key, raw in ctx.db.kv_prefix(tenant.slug, "master_invite:").items():
            try:
                if json.loads(raw)["master"] == master_id:
                    ctx.db.kv_delete(tenant.slug, key)
            except (ValueError, KeyError, TypeError):
                ctx.db.kv_delete(tenant.slug, key)
        code = secrets.token_urlsafe(12)
        until = tenant.now() + timedelta(hours=INVITE_HOURS)
        ctx.db.kv_set(tenant.slug, f"master_invite:{code}",
                      json.dumps({"master": master_id, "until": until.isoformat()}))
        await ctx.send(ctx.at("adm_master_invite", name=master.name, hours=INVITE_HOURS,
                              link=f"https://t.me/{username}?start=m{code}"))

    async def admin_master_unlink(self, ctx: Ctx, master_id: str, message_id: int | None, confirmed: bool) -> None:
        tenant = ctx.tenant
        master = tenant.masters.get(master_id)
        tg = self.master_links(tenant).get(master_id)
        if master is None or tg is None:
            raise Expired()
        if not confirmed:
            kb = inline_kb([[ibtn(ctx.at("btn_adm_yes_unlink"), f"aMuy:{master_id}"), ibtn(ctx.at("btn_no"), "aM")]])
            await ctx.show(message_id, ctx.at("adm_master_unlink_ask", name=master.name), kb)
            return
        ctx.db.kv_delete(tenant.slug, f"master_tg:{master_id}")
        await ctx.show(message_id, ctx.at("adm_master_unlinked", name=master.name))
        if tg == ctx.chat_id:
            # Адмін відключив сам себе: редагування не змінює нижнє меню, тож надсилаємо нове — клієнтське.
            ctx.master_id = None
            await ctx.send(ctx.t("mst_unlinked"), self.main_kb(ctx))
        else:
            await self.send(tenant, tg, tenant.t(tenant.lang, "mst_unlinked"), self.client_kb(ctx, tenant.lang))
        await self._chat_commands_quiet(tenant, tg, master=False)

    # ================================================================ майстер підключається
    async def master_join(self, ctx: Ctx, code: str) -> None:
        tenant, db = ctx.tenant, ctx.db
        key = f"master_invite:{code}"
        raw = db.kv_get(tenant.slug, key)
        try:
            invite = json.loads(raw) if raw else None
            if invite and datetime.fromisoformat(invite["until"]) < tenant.now():
                invite = None
        except (ValueError, KeyError, TypeError):
            invite = None
        if not invite or invite.get("master") not in tenant.masters:
            await ctx.send(ctx.t("mst_invite_bad"), self.main_kb(ctx))
            return
        db.kv_delete(tenant.slug, key)
        master = tenant.masters[invite["master"]]
        links = self.master_links(tenant)
        # Одна людина — один майстер: якщо цей Telegram уже був прив'язаний до іншого майстра — відв'язуємо.
        for mid, tg in links.items():
            if tg == ctx.user_id and mid != master.id:
                db.kv_delete(tenant.slug, f"master_tg:{mid}")
        previous = links.get(master.id)
        db.kv_set(tenant.slug, f"master_tg:{master.id}", str(ctx.user_id))
        ctx.master_id = master.id
        if previous and previous != ctx.user_id:
            await self.send(tenant, previous, tenant.t(tenant.lang, "mst_unlinked"), self.client_kb(ctx, tenant.lang))
            await self._chat_commands_quiet(tenant, previous, master=False)
        await ctx.send(ctx.at("mst_joined", name=master.name) + self.master_start_text(ctx), self.master_kb(ctx))
        await self._chat_commands_quiet(tenant, ctx.user_id, master=True)
        await self.notify_admins(tenant, ctx.at("adm_master_joined", name=master.name,
                                                who=self.client_label(tenant, ctx.client)))

    # ================================================================ меню майстра
    def master_kb(self, ctx: Ctx) -> dict:
        return reply_kb([[ctx.at("btn_mst_day"), ctx.at("btn_mst_week")],
                         [ctx.at("btn_mst_off"), ctx.at("btn_mst_offs")]])

    def client_kb(self, ctx: Ctx, lang: str) -> dict:
        t = ctx.tenant.t
        return reply_kb([[t(lang, "btn_book"), t(lang, "btn_my")], [t(lang, "btn_prices"), t(lang, "btn_contacts")]])

    def master_start_text(self, ctx: Ctx) -> str:
        return ctx.at("mst_start", name=ctx.tenant.masters[ctx.master_id].name, shop=ctx.tenant.name)

    def master_menu_key(self, ctx: Ctx, text: str) -> str | None:
        if not text:
            return None
        return next((key for key in MASTER_MENU if text in ctx.tenant.all_labels(key)), None)

    async def run_master_menu(self, ctx: Ctx, key: str) -> None:
        if key == "btn_mst_day":
            await self.master_day(ctx, ctx.tenant.today(), None)
        elif key == "btn_mst_week":
            await self.master_week(ctx)
        elif key == "btn_mst_off":
            await self.master_off_days(ctx, None)
        else:
            await self.master_blocks(ctx, None)

    async def master_command(self, ctx: Ctx, cmd: str) -> None:
        await self.run_master_menu(ctx, {"my": "btn_mst_day", "myweek": "btn_mst_week", "off": "btn_mst_off",
                                         "offs": "btn_mst_offs"}[cmd])

    # ================================================================ мій день / тиждень
    def _master_rows(self, ctx: Ctx, day: date, include_noshow: bool = True) -> list:
        return [r for r in ctx.booking.day_bookings(day, include_noshow) if r["master_id"] == ctx.master_id]

    def master_day_text(self, tenant: Tenant, master_id: str, day: date, rows) -> str:
        """Записи майстра на день + графік і закритий час."""
        master = tenant.masters[master_id]
        text = self.render_day(tenant, day, rows, master.name)
        if not tenant.master_intervals(master, day):
            text += tenant.t(tenant.lang, "mst_day_off")
        start = datetime.combine(day, time.min)
        ranges = [self._block_range(tenant, bl) for bl in
                  self.db.blocks_overlapping(tenant.slug, start, start + timedelta(days=1), master_id)]
        if ranges:
            text += tenant.t(tenant.lang, "mst_day_blocks", ranges=", ".join(ranges))
        return text

    async def master_day(self, ctx: Ctx, day: date, message_id: int | None) -> None:
        tenant = ctx.tenant
        rows = self._master_rows(ctx, day)
        text = self.master_day_text(tenant, ctx.master_id, day, rows)
        buttons = [[ibtn(ctx.at("btn_adm_booking_item", n=n, when=r["start_at"][11:16],
                                client=self._short_name(tenant, r)), f"mK:{r['id']}")]
                   for n, r in enumerate(rows, 1)]
        if buttons:
            text += ctx.at("mst_day_hint")
        prev, nxt = day - timedelta(days=1), day + timedelta(days=1)
        buttons.append([ibtn(ctx.at("btn_day_prev", day=tenant.day_button(prev, tenant.lang)), f"mD:{prev:%Y%m%d}"),
                        ibtn(ctx.at("btn_day_pick"), "mDp"),
                        ibtn(ctx.at("btn_day_next", day=tenant.day_button(nxt, tenant.lang)), f"mD:{nxt:%Y%m%d}")])
        await ctx.show(message_id, text, inline_kb(buttons))

    async def master_day_picker(self, ctx: Ctx, message_id: int | None) -> None:
        tenant = ctx.tenant
        today = tenant.today()
        days = [today + timedelta(days=i) for i in range(-7, tenant.days_ahead)]
        buttons = _rows([ibtn(tenant.day_button(d, tenant.lang), f"mD:{d:%Y%m%d}") for d in days], 3)
        buttons.append([ibtn(ctx.at("btn_back"), f"mD:{today:%Y%m%d}")])
        await ctx.show(message_id, ctx.at("adm_day_pick"), inline_kb(buttons))

    async def master_week(self, ctx: Ctx) -> None:
        tenant = ctx.tenant
        rows = [r for r in self._active_from(tenant, tenant.today(), 7) if r["master_id"] == ctx.master_id]
        text, numbered = self._render_list(tenant, "mst_week_header", rows)
        buttons = []
        for n, r in numbered:
            when = f"{tenant.weekday_short(date.fromisoformat(r['start_at'][:10]), tenant.lang)} " \
                   f"{r['start_at'][8:10]}.{r['start_at'][5:7]} {r['start_at'][11:16]}"
            buttons.append([ibtn(ctx.at("btn_adm_booking_item", n=n, when=when, client=self._short_name(tenant, r)),
                                 f"mK:{r['id']}")])
        if buttons:
            text += ctx.at("mst_day_hint")
        await ctx.send(text, inline_kb(buttons[:90]) if buttons else None)

    # ================================================================ картка запису майстра
    def _master_booking(self, ctx: Ctx, booking_id: int):
        b = ctx.db.get_booking(booking_id)
        if b is None or b["tenant"] != ctx.tenant.slug or b["master_id"] != ctx.master_id:
            raise Expired()
        return b

    async def master_booking_card(self, ctx: Ctx, booking_id: int, message_id: int | None) -> None:
        tenant = ctx.tenant
        b = self._master_booking(ctx, booking_id)
        client = ctx.db.get_client(b["client_id"])
        rows = []
        if b["status"] == "active" and parse_dt(b["start_at"]).date() <= tenant.today():
            rows.append([ibtn(ctx.at("btn_adm_noshow"), f"mN:{b['id']}")])
        rows.append([ibtn(ctx.at("btn_mst_to_day"), f"mD:{b['start_at'][:10].replace('-', '')}")])
        await ctx.show(message_id, self.booking_card_text(tenant, b, client), inline_kb(rows))

    async def master_no_show(self, ctx: Ctx, booking_id: int, message_id: int | None) -> str:
        tenant = ctx.tenant
        b = self._master_booking(ctx, booking_id)
        if b["status"] != "active" or parse_dt(b["start_at"]).date() > tenant.today():
            raise Expired()
        b = ctx.booking.mark_no_show(b["id"])
        client = ctx.db.get_client(b["client_id"])
        await self.master_booking_card(ctx, b["id"], message_id)
        await self.notify_admins(tenant, ctx.at("adm_master_noshow", master=tenant.masters[ctx.master_id].name,
                                                booking=Raw(self._booking_summary(tenant, b, client))),
                                 inline_kb([[ibtn(ctx.at("btn_adm_open"), f"aK:{b['id']}")]]))
        return ctx.at("adm_noshow_done", client=self._short_name(tenant, client), time=b["start_at"][11:16])

    # ================================================================ закрити свій час
    def _block_range(self, tenant: Tenant, bl) -> str:
        start, end = parse_dt(bl["start_at"]), parse_dt(bl["end_at"])
        if start.time() == time.min and end - start >= timedelta(days=1):
            return tenant.t(tenant.lang, "adm_whole_day")
        return f"{fmt_hhmm(start)}–{fmt_hhmm(end)}"

    def _off_day(self, ctx: Ctx, value: str) -> date:
        day = _d(value)
        today = ctx.tenant.today()
        if not today <= day < today + timedelta(days=OFF_DAYS):
            raise Expired()
        return day

    def _work_bounds(self, ctx: Ctx, day: date) -> tuple[datetime, datetime] | None:
        intervals = ctx.tenant.master_intervals(ctx.tenant.masters[ctx.master_id], day)
        return (intervals[0][0], intervals[-1][1]) if intervals else None

    async def master_off_days(self, ctx: Ctx, message_id: int | None) -> None:
        tenant = ctx.tenant
        today = tenant.today()
        buttons = [ibtn(tenant.day_button(today + timedelta(days=i), tenant.lang),
                        f"mOd:{today + timedelta(days=i):%Y%m%d}") for i in range(OFF_DAYS)]
        await ctx.show(message_id, ctx.at("mst_off_day"), inline_kb(_rows(buttons, 4)))

    async def master_off_start(self, ctx: Ctx, day: date, message_id: int | None) -> None:
        tenant = ctx.tenant
        bounds = self._work_bounds(ctx, day)
        step = timedelta(minutes=tenant.slot_step_min)
        now = tenant.now()
        times = []
        if bounds:
            t = bounds[0]
            while t < bounds[1]:
                if t + step > now:
                    times.append(ibtn(fmt_hhmm(t), f"mOs:{day:%Y%m%d}:{t:%H%M}"))
                t += step
        hours = f"{fmt_hhmm(bounds[0])}–{fmt_hhmm(bounds[1])}" if bounds else ctx.at("mst_off_no_work")
        rows = [[ibtn(ctx.at("btn_mst_whole_day"), f"mOe:{day:%Y%m%d}:w")]] + _rows(times, 4)
        rows.append([ibtn(ctx.at("btn_back"), "mO")])
        await ctx.show(message_id, ctx.at("mst_off_range" if times else "mst_off_whole_only",
                                          day=tenant.day_label(day, tenant.lang), hours=hours), inline_kb(rows))

    async def master_off_end(self, ctx: Ctx, day: date, start: time, message_id: int | None) -> None:
        tenant = ctx.tenant
        bounds = self._work_bounds(ctx, day)
        begin = datetime.combine(day, start)
        if bounds is None or not bounds[0] <= begin < bounds[1]:
            raise Expired()
        step = timedelta(minutes=tenant.slot_step_min)
        ends, t = [], begin + step
        while t <= bounds[1]:
            ends.append(ibtn(fmt_hhmm(t), f"mOe:{day:%Y%m%d}:{start:%H%M}:{t:%H%M}"))
            t += step
        if not ends or ends[-1]["text"] != fmt_hhmm(bounds[1]):  # кінець зміни не на кроці сітки
            ends.append(ibtn(fmt_hhmm(bounds[1]), f"mOe:{day:%Y%m%d}:{start:%H%M}:{bounds[1]:%H%M}"))
        await ctx.show(message_id, ctx.at("mst_off_end", day=tenant.day_label(day, tenant.lang),
                                          start=fmt_hhmm(start)),
                       inline_kb(_rows(ends, 4) + [[ibtn(ctx.at("btn_back"), f"mOd:{day:%Y%m%d}")]]))

    def _off_range(self, ctx: Ctx, a: list[str]) -> tuple[datetime, datetime, str]:
        """Дані кнопки → (початок, кінець, підпис): [день, "w"] — увесь день, [день, з, до] — проміжок."""
        day = self._off_day(ctx, a[0])
        if a[1:] == ["w"]:
            start = datetime.combine(day, time.min)
            return start, start + timedelta(days=1), ctx.at("adm_whole_day")
        if len(a) != 3:
            raise Expired()
        start = datetime.combine(day, _t(a[1]))
        end = datetime.combine(day, _t(a[2]))
        if end <= start or end <= ctx.tenant.now():
            raise Expired()
        return start, end, f"{fmt_hhmm(start)}–{fmt_hhmm(end)}"

    def _conflict_lines(self, tenant: Tenant, rows) -> str:
        lines = []
        for b in rows:
            client = self.db.get_client(b["client_id"])
            lines.append(f"\n• {b['start_at'][11:16]} · {b['service_title']} · "
                         f"{self.client_label(tenant, client) if client else ''}")
        return "".join(lines)

    async def master_off_confirm(self, ctx: Ctx, a: list[str], message_id: int | None) -> None:
        tenant = ctx.tenant
        start, end, rng = self._off_range(ctx, a)
        conflicts = ctx.db.active_bookings_overlapping(tenant.slug, start, end, ctx.master_id)
        warn = Raw(ctx.at("mst_off_conflicts", lines=self._conflict_lines(tenant, conflicts))) if conflicts else ""
        kb = inline_kb([[ibtn(ctx.at("btn_mst_off_yes"), "mOy:" + ":".join(a))],
                        [ibtn(ctx.at("btn_back"), f"mOd:{a[0]}")]])
        await ctx.show(message_id, ctx.at("mst_off_confirm", day=tenant.day_label(start.date(), tenant.lang), range=rng,
                                          conflicts=warn), kb)

    async def master_off_do(self, ctx: Ctx, a: list[str], message_id: int | None) -> None:
        tenant = ctx.tenant
        start, end, rng = self._off_range(ctx, a)
        master = tenant.masters[ctx.master_id]
        day = tenant.day_label(start.date(), tenant.lang)
        same = [bl for bl in ctx.db.blocks_overlapping(tenant.slug, start, end, ctx.master_id)
                if bl["master_id"] == ctx.master_id and bl["start_at"] == f"{start:%Y-%m-%d %H:%M}"
                and bl["end_at"] == f"{end:%Y-%m-%d %H:%M}"]
        if same:  # повторне натискання
            await ctx.show(message_id, ctx.at("mst_off_done", day=day, range=rng))
            return
        _, conflicts = ctx.booking.add_block(ctx.master_id, start, end, master.name, created_by="master")
        text = ctx.at("mst_off_done", day=day, range=rng)
        lines = self._conflict_lines(tenant, conflicts)
        if conflicts:
            text += ctx.at("mst_off_done_conflicts", lines=lines)
        await ctx.show(message_id, text)
        note = ctx.at("adm_master_off", master=master.name, day=day, range=rng)
        kb = None
        if conflicts:
            note += ctx.at("adm_master_off_conflicts", lines=lines)
            kb = inline_kb([[ibtn(ctx.at("btn_adm_booking_item", n=n, when=b["start_at"][11:16],
                                         client=self._short_name(tenant, ctx.db.get_client(b["client_id"]))),
                                  f"aK:{b['id']}")] for n, b in enumerate(conflicts[:20], 1)])
        await self.notify_admins(tenant, note, kb)

    async def master_blocks(self, ctx: Ctx, message_id: int | None) -> None:
        tenant = ctx.tenant
        rows = [bl for bl in ctx.db.future_blocks(tenant.slug, tenant.now())
                if bl["master_id"] in (ctx.master_id, None)]
        if not rows:
            await ctx.show(message_id, ctx.at("mst_offs_empty"))
            return
        buttons, others = [], ""
        for bl in rows[:40]:
            label = f"{tenant.day_button(parse_dt(bl['start_at']).date(), tenant.lang)} {self._block_range(tenant, bl)}"
            if bl["master_id"] == ctx.master_id and bl["created_by"] == "master":
                buttons.append([ibtn(ctx.at("btn_mst_block_item", label=label), f"mBd:{bl['id']}")])
            else:
                others += f"\n• {label}"
        text = ctx.at("mst_offs_header") if buttons else ctx.at("mst_offs_header_none")
        if others:
            text += ctx.at("mst_offs_admin", lines=others)
        await ctx.show(message_id, text, inline_kb(buttons) if buttons else None)

    async def master_block_delete(self, ctx: Ctx, block_id: int, message_id: int | None) -> str:
        tenant = ctx.tenant
        bl = ctx.db.get_block(tenant.slug, block_id)
        if bl is None or bl["master_id"] != ctx.master_id or bl["created_by"] != "master":
            raise Expired()
        ctx.db.delete_block(tenant.slug, block_id)
        await self.master_blocks(ctx, message_id)
        await self.notify_admins(tenant, ctx.at(
            "adm_master_on", master=tenant.masters[ctx.master_id].name,
            day=tenant.day_label(parse_dt(bl["start_at"]).date(), tenant.lang), range=self._block_range(tenant, bl)))
        return ctx.at("alert_mst_opened")

    # ================================================================ AI для майстра
    def master_ai_brief(self, ctx: Ctx) -> str:
        """Динамічна частина промпту, коли AI пише майстер: хто він, зараз, його записи й закритий час."""
        tenant = ctx.tenant
        master = tenant.masters[ctx.master_id]
        now = tenant.now()
        lines = ["## Зараз", f"{tenant.day_label(now.date(), 'uk')}, {fmt_hhmm(now)} (місцевий час закладу).", "",
                 f"## Майстер\nІмʼя: {master.name} (id {master.id}). "
                 f"Графік: {tenant.schedule_summary('uk', master).replace(chr(10), '; ')}.", "",
                 "Записи майстра на 7 днів (час · послуга · клієнт):"]
        rows = [r for r in self._active_from(tenant, now.date(), 7) if r["master_id"] == master.id]
        for r in rows:
            name = self._short_name(tenant, r)
            day = tenant.day_label(date.fromisoformat(r["start_at"][:10]), "uk")
            lines.append(f"- {day} {r['start_at'][11:16]}–{r['end_at'][11:16]} · {r['service_title']} · {name}"
                         + (f" · коментар: {r['note']}" if r["note"] else ""))
        if not rows:
            lines.append("- записів немає")
        blocks = [bl for bl in ctx.db.future_blocks(tenant.slug, now) if bl["master_id"] in (master.id, None)]
        if blocks:
            lines.append("Закритий час:")
            lines += [f"- {tenant.day_label(parse_dt(bl['start_at']).date(), 'uk')} {self._block_range(tenant, bl)}"
                      for bl in blocks[:20]]
        return "\n".join(lines)

    # ================================================================ кнопки майстра
    async def master_callback(self, ctx: Ctx, op: str, a: list[str], message_id: int | None) -> str | None:
        if op == "mD" and len(a) == 1:
            await self.master_day(ctx, _d(a[0]), message_id)
        elif op == "mDp":
            await self.master_day_picker(ctx, message_id)
        elif op == "mK" and len(a) == 1:
            await self.master_booking_card(ctx, _int(a[0]), None)
        elif op == "mN" and len(a) == 1:
            return await self.master_no_show(ctx, _int(a[0]), message_id)
        elif op == "mO":
            await self.master_off_days(ctx, message_id)
        elif op == "mOd" and len(a) == 1:
            await self.master_off_start(ctx, self._off_day(ctx, a[0]), message_id)
        elif op == "mOs" and len(a) == 2:
            await self.master_off_end(ctx, self._off_day(ctx, a[0]), _t(a[1]), message_id)
        elif op == "mOe" and len(a) in (2, 3):
            await self.master_off_confirm(ctx, a, message_id)
        elif op == "mOy" and len(a) in (2, 3):
            await self.master_off_do(ctx, a, message_id)
        elif op == "mB":
            await self.master_blocks(ctx, message_id)
        elif op == "mBd" and len(a) == 1:
            return await self.master_block_delete(ctx, _int(a[0]), message_id)
        else:
            raise Expired()
        return None

    # ================================================================ сповіщення майстру
    def master_chat(self, tenant: Tenant, master_id: str, skip_admins: bool = True) -> int | None:
        """Telegram майстра. Майстрові-адміністратору зазвичай не дублюємо: він і так отримує сповіщення адміна."""
        tg = self.master_links(tenant).get(master_id)
        if tg is None or (skip_admins and tg in tenant.admins):
            return None
        return tg

    async def notify_master(self, tenant: Tenant, b, key: str, **extra) -> None:
        chat = self.master_chat(tenant, b["master_id"])
        if chat is None:
            return
        start = parse_dt(b["start_at"])
        client = self.db.get_client(b["client_id"])
        text = tenant.t(tenant.lang, key, day=tenant.day_label(start.date(), tenant.lang), time=fmt_hhmm(start),
                        service=b["service_title"],
                        client=self.client_label(tenant, client) if client else tenant.t(tenant.lang,
                                                                                        "adm_client_noname"),
                        **extra)
        kb = None
        if key in ("mst_new", "mst_rescheduled"):
            kb = inline_kb([[ibtn(tenant.t(tenant.lang, "btn_adm_open"), f"mK:{b['id']}")]])
        await self.send(tenant, chat, text, kb)

    async def notify_master_resched(self, tenant: Tenant, old, new) -> None:
        if old["master_id"] != new["master_id"]:
            await self.notify_master(tenant, old, "mst_moved")
            await self.notify_master(tenant, new, "mst_new")
            return
        old_start, new_start = parse_dt(old["start_at"]), parse_dt(new["start_at"])
        await self.notify_master(tenant, new, "mst_rescheduled",
                                 old=f"{tenant.day_label(old_start.date(), tenant.lang)}, {fmt_hhmm(old_start)}",
                                 new=f"{tenant.day_label(new_start.date(), tenant.lang)}, {fmt_hhmm(new_start)}")
