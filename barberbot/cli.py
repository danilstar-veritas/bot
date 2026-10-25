"""Команди запуску:

    python3 run.py             — запустити бота(ів)
    python3 run.py check       — перевірити налаштування, токени й ключ AI
    python3 run.py chat [файл] — поговорити з AI-адміністратором у терміналі (без Telegram)
    python3 run.py eval [файл] — прогнати тестові діалоги з config/eval.toml і перевірити поведінку AI
    python3 run.py dialogs [файл] [днів] — вивантажити листування з клієнтами в текстовий файл
    python3 run.py test        — запустити автотести
"""

from __future__ import annotations

import asyncio
import json
import logging
import logging.handlers
import signal
import sys
import tomllib
from datetime import timedelta
from pathlib import Path

from . import __version__
from .config import ConfigError, Settings, Tenant, fmt_hhmm, load_settings, load_tenants
from .db import DB
from .llm import LLMError, make_llm
from .telegram import NetworkError, TelegramAPI, TelegramError

ROOT = Path(__file__).resolve().parent.parent
CONFIG_DIR = ROOT / "config"
SETTINGS_PATH = CONFIG_DIR / "settings.toml"
TENANTS_DIR = CONFIG_DIR / "tenants"

OK, WARN, FAIL = "✅", "⚠️ ", "❌"


def setup_logging(settings: Settings) -> None:
    settings.data_dir.mkdir(parents=True, exist_ok=True)
    fmt = logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s", "%Y-%m-%d %H:%M:%S")
    root = logging.getLogger()
    root.setLevel(settings.log_level)
    console = logging.StreamHandler(sys.stdout)
    console.setFormatter(fmt)
    file = logging.handlers.RotatingFileHandler(settings.data_dir / "bot.log", maxBytes=2_000_000, backupCount=3,
                                                encoding="utf-8")
    file.setFormatter(fmt)
    root.handlers = [console, file]


def load_everything(require_token: bool = True) -> tuple[Settings, list[Tenant], list[str]]:
    try:
        settings = load_settings(SETTINGS_PATH, ROOT)
    except ConfigError as e:
        print(f"{FAIL} {e}")
        sys.exit(1)
    tenants, errors = load_tenants(TENANTS_DIR, require_token)
    return settings, tenants, errors


def pick_tenant(tenants: list[Tenant], name: str | None) -> Tenant:
    enabled = [t for t in tenants if t.enabled] or tenants
    if not enabled:
        print(f"{FAIL} У папці config/tenants немає жодного закладу.")
        sys.exit(1)
    if name:
        stem = Path(name).stem
        for t in tenants:
            if t.slug == stem:
                return t
        print(f"{FAIL} Не знайдено config/tenants/{stem}.toml")
        sys.exit(1)
    return enabled[0]


# ====================================================================== run
def cmd_run() -> int:
    settings, tenants, errors = load_everything()
    for e in errors:
        print(f"{FAIL} {e}")
    enabled = [t for t in tenants if t.enabled]
    if not enabled:
        print(f"{FAIL} Немає жодного увімкненого закладу з правильними налаштуваннями. Запустіть: python3 run.py check")
        return 1
    setup_logging(settings)
    log = logging.getLogger("barberbot")
    for t in enabled:
        for w in t.warnings:
            log.warning("[%s] %s", t.name, w)
    if not settings.ai_available:
        log.warning("Ключ %s не вказано — AI-відповіді вимкнено, бот працює на кнопках.", settings.ai_name)

    from .app import BotApp

    db = DB(settings.data_dir / "bot.db")
    llm = make_llm(settings) if settings.ai_available else None

    async def main() -> None:
        app = BotApp(settings, enabled, db, llm)
        loop = asyncio.get_running_loop()
        for sig in (signal.SIGINT, signal.SIGTERM):
            try:
                loop.add_signal_handler(sig, app.stop)
            except (NotImplementedError, RuntimeError):
                pass
        log.info("Barber Bot %s: закладів — %d. Зупинити: Ctrl+C", __version__, len(enabled))
        await app.run()

    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
    finally:
        db.close()
    log.info("Бота зупинено.")
    return 0


# ====================================================================== check
def cmd_check() -> int:
    settings, tenants, errors = load_everything()
    problems = len(errors)
    print(f"Barber Bot {__version__} · Python {sys.version.split()[0]}\n")
    print(f"{OK} settings.toml прочитано. AI: {settings.ai_name}, модель: {settings.ai_model}, effort: {settings.effort}")
    if settings.ai_available:
        print(f"{OK} Ключ {settings.ai_name} вказано")
    else:
        print(f"{WARN} Ключ {settings.ai_name} не вказано — бот працюватиме лише на кнопках (без AI-відповідей)")
    print()
    for e in errors:
        print(f"{FAIL} {e}\n")
    if not tenants and not errors:
        print(f"{FAIL} У config/tenants немає файлів *.toml")
        return 1

    from .booking import BookingService

    db = DB(":memory:")
    for t in tenants:
        status = "" if t.enabled else "  (ВИМКНЕНО: enabled = false)"
        print(f"── {t.name} [{t.path.name}]{status}")
        print(f"   Послуг: {len(t.visible_services())}, майстрів: {len(t.masters)}, мови: {', '.join(t.languages)}, "
              f"часовий пояс: {t.timezone}")
        print(f"   Адміністратори (Telegram ID): {', '.join(map(str, t.admins)) or '— немає'}")
        print("   Графік закладу: " + t.schedule_summary(t.lang).replace("\n", "; "))
        for w in t.warnings:
            print(f"   {WARN} {w}")
        svc = next((s for s in t.services.values() if t.masters_for(s.id)), None)
        if svc:
            booking = BookingService(t, db)
            days = booking.available_days(svc.id, "any", limit=1)
            if days:
                slots = list(booking.free_slots(svc.id, "any", days[0]))
                print(f"   Найближчий вільний час на «{svc.title}»: {t.day_label(days[0], t.lang)} — "
                      f"{', '.join(slots[:6])}{' …' if len(slots) > 6 else ''}")
            else:
                print(f"   {WARN} На «{svc.title}» немає вільного часу на {t.days_ahead} днів — перевірте графік.")
        if t.enabled:
            try:
                me = TelegramAPI(t.bot_token, settings.telegram_api_base).call_sync("getMe", timeout=15)
                print(f"   {OK} Telegram: бот @{me.get('username')} — токен правильний")
            except TelegramError as e:
                problems += 1
                print(f"   {FAIL} Telegram відхилив токен: {e.description}. Перевірте bot_token.")
            except NetworkError as e:
                problems += 1
                print(f"   {FAIL} Немає зв'язку з Telegram: {e}")
        print()

    db.close()
    if settings.ai_available and tenants:
        from .prompt import static_prompt, tool_definitions

        t = pick_tenant(tenants, None)
        try:
            tokens = make_llm(settings, retries=0).count_tokens_sync({
                "model": settings.model,
                "system": static_prompt(t),
                "tools": tool_definitions(t),
                "messages": [{"role": "user", "content": "Привіт"}],
            })
            print(f"{OK} Ключ {settings.ai_name} працює. Розмір промпту «{t.name}»: ~{tokens} токенів")
        except LLMError as e:
            problems += 1
            print(f"{FAIL} {settings.ai_name} API: {e}")
    print()
    if problems:
        print(f"{FAIL} Знайдено проблем: {problems}. Виправте їх і запустіть перевірку ще раз.")
        return 1
    print(f"{OK} Усе готово. Запуск бота: python3 run.py")
    return 0


# ====================================================================== chat
class ConsoleSession:
    """AI-адміністратор у терміналі: та сама логіка, що й у Telegram, але без нього."""

    def __init__(self, settings: Settings, tenant: Tenant, llm):
        from .agent import Agent
        from .booking import BookingService

        self.settings = settings
        self.tenant = tenant
        self.db = DB(":memory:")
        self.booking = BookingService(tenant, self.db)
        self.agent = Agent(settings, llm)
        self.client = self.db.upsert_client(tenant.slug, 1, "Тест", None, "tester", tenant.lang, tenant.now())

    def close(self) -> None:
        self.db.close()

    async def say(self, text: str, confirm=None) -> dict:
        """confirm(card_text) -> bool — що робити з карткою підтвердження."""
        from .agent import add_note
        from .booking import BookingError

        self.client = self.db.get_client(self.client["id"])
        self.db.log_event(self.tenant.slug, self.client["id"], "ai_message", self.tenant.now())
        result = await self.agent.reply(self.tenant, self.booking, self.db, self.client, text)
        out = {"text": result.text, "error": result.error, "refusal": result.refusal,
               "tools": list(result.tools_used), "effects": [e["type"] for e in result.effects], "notes": []}
        for e in result.effects:
            t = self.tenant
            try:
                if e["type"] == "confirm_booking":
                    start = e["start"]
                    card = (f"[Картка] {t.services[e['service_id']].title} · {t.masters[e['master_id']].name} · "
                            f"{t.day_label(start.date(), t.lang)} {fmt_hhmm(start)}")
                    if confirm and confirm(card):
                        b = self.booking.create(self.client["id"], e["service_id"], e["master_id"], start, "ai")
                        add_note(self.db, t, self.client["id"], f"Клієнт підтвердив запис №{b['id']}.", self.settings)
                        out["notes"].append(f"{card} → ПІДТВЕРДЖЕНО (запис №{b['id']})")
                    else:
                        out["notes"].append(card)
                elif e["type"] == "confirm_cancel":
                    card = f"[Картка] Скасувати запис №{e['booking_id']}?"
                    if confirm and confirm(card):
                        self.booking.cancel(e["booking_id"], "client", self.client["id"])
                        add_note(self.db, t, self.client["id"], f"Запис №{e['booking_id']} скасовано.", self.settings)
                        out["notes"].append(f"{card} → СКАСОВАНО")
                    else:
                        out["notes"].append(card)
                elif e["type"] == "confirm_reschedule":
                    card = f"[Картка] Перенести запис №{e['booking_id']} на {e['start']:%d.%m %H:%M}?"
                    if confirm and confirm(card):
                        self.booking.reschedule(e["booking_id"], e["start"], e["master_id"], self.client["id"])
                        add_note(self.db, t, self.client["id"], f"Запис №{e['booking_id']} перенесено.", self.settings)
                        out["notes"].append(f"{card} → ПЕРЕНЕСЕНО")
                    else:
                        out["notes"].append(card)
                elif e["type"] == "handoff":
                    out["notes"].append(f"[Передано адміністратору] {e.get('reason')}: {e.get('summary')}")
            except BookingError as err:
                out["notes"].append(f"[Помилка запису: {err.code}]")
        return out


def cmd_chat(args: list[str]) -> int:
    settings, tenants, errors = load_everything(require_token=False)
    for e in errors:
        print(f"{FAIL} {e}")
    if not settings.ai_available:
        print(f"{FAIL} Для чату потрібен ключ {settings.ai_name} у config/settings.toml ({settings.ai_key_field}).")
        return 1
    tenant = pick_tenant(tenants, args[0] if args else None)
    llm = make_llm(settings)
    session = ConsoleSession(settings, tenant, llm)
    print(f"Чат з AI-адміністратором «{tenant.name}». Пишіть як клієнт.")
    print("Команди: /exit — вийти, /bookings — записи в цій тестовій сесії. Дані не зберігаються.\n")

    def confirm(card: str) -> bool:
        answer = input(f"   {card}\n   Натиснути «Підтвердити»? (так/ні): ").strip().lower()
        return answer in ("так", "т", "y", "yes", "да", "+")

    async def loop() -> None:
        while True:
            try:
                text = input("Ви: ").strip()
            except (EOFError, KeyboardInterrupt):
                print()
                return
            if not text:
                continue
            if text == "/exit":
                return
            if text == "/bookings":
                for b in session.db.q("SELECT * FROM bookings ORDER BY start_at"):
                    print(f"   №{b['id']} {b['start_at']} {b['service_title']} · {b['master_name']} · {b['status']}")
                continue
            out = await session.say(text, confirm)
            if out["error"]:
                print(f"   {FAIL} Помилка AI: {out['error']}")
            if out["refusal"]:
                print("Бот: (модель відмовилась відповідати)")
            if out["text"]:
                print(f"Бот: {out['text']}")
            if out["tools"]:
                print(f"   [інструменти: {', '.join(out['tools'])}]")
            for note in out["notes"]:
                print(f"   {note}")

    try:
        asyncio.run(loop())
    finally:
        session.close()
    return 0


# ====================================================================== eval
def cmd_eval(args: list[str], llm=None, scenarios_path: Path | None = None) -> int:
    settings, tenants, errors = load_everything(require_token=False)
    for e in errors:
        print(f"{FAIL} {e}")
    if llm is None:
        if not settings.ai_available:
            print(f"{FAIL} Для перевірки діалогів потрібен ключ {settings.ai_name} у config/settings.toml.")
            return 1
        llm = make_llm(settings)
    tenant = pick_tenant(tenants, args[0] if args else None)
    path = scenarios_path or (CONFIG_DIR / "eval.toml")
    try:
        scenarios = tomllib.loads(path.read_text(encoding="utf-8")).get("scenario", [])
    except (OSError, tomllib.TOMLDecodeError) as e:
        print(f"{FAIL} Не вдалося прочитати {path.name}: {e}")
        return 1
    report: list[str] = [f"Перевірка AI-адміністратора «{tenant.name}», модель {settings.ai_model}", ""]
    passed = 0

    async def run_one(sc: dict) -> tuple[bool, list[str]]:
        session = ConsoleSession(settings, tenant, llm)
        lines = [f"■ {sc.get('name', 'без назви')}"]
        tools: list[str] = []
        effects: list[str] = []
        replies: list[str] = []
        problems: list[str] = []
        auto_confirm = bool(sc.get("confirm_cards", False))
        for msg in sc.get("messages", []):
            out = await session.say(msg, (lambda card: auto_confirm))
            lines.append(f"  Клієнт: {msg}")
            if out["error"]:
                problems.append(f"помилка AI: {out['error']}")
            lines.append(f"  Бот: {out['text'] or '—'}")
            if out["tools"]:
                lines.append(f"    інструменти: {', '.join(out['tools'])}")
            lines.extend(f"    {n}" for n in out["notes"])
            tools += out["tools"]
            effects += out["effects"]
            replies.append(out["text"] or "")
        session.close()
        for tool in sc.get("expect_tools", []):
            if tool not in tools:
                problems.append(f"очікувався виклик {tool}")
        for tool in sc.get("forbid_tools", []):
            if tool in tools:
                problems.append(f"не мав викликатися {tool}")
        for eff in sc.get("expect_effects", []):
            if eff not in effects:
                problems.append(f"очікувалась дія {eff}")
        for eff in sc.get("forbid_effects", []):
            if eff in effects:
                problems.append(f"не мала бути дія {eff}")
        joined = "\n".join(replies).lower()
        for s in sc.get("must_not_contain", []):
            if s.lower() in joined:
                problems.append(f"у відповіді не має бути «{s}»")
        any_of = sc.get("must_contain_any", [])
        if any_of and not any(s.lower() in joined for s in any_of):
            problems.append(f"у відповіді має бути щось із: {', '.join(any_of)}")
        ok = not problems
        lines.append(f"  {'PASS' if ok else 'FAIL'}" + ("" if ok else ": " + "; ".join(problems)))
        return ok, lines

    async def run_all() -> None:
        nonlocal passed
        for sc in scenarios:
            ok, lines = await run_one(sc)
            passed += ok
            print("\n".join(lines) + "\n")
            report.extend(lines + [""])

    asyncio.run(run_all())
    summary = f"Результат: {passed} з {len(scenarios)} сценаріїв пройдено."
    print(summary)
    report.append(summary)
    settings.data_dir.mkdir(parents=True, exist_ok=True)
    out_path = settings.data_dir / f"eval-{tenant.slug}.txt"
    out_path.write_text("\n".join(report), encoding="utf-8")
    print(f"Звіт збережено: {out_path}")
    return 0 if passed == len(scenarios) else 1


# ====================================================================== dialogs
def cmd_dialogs(args: list[str]) -> int:
    settings, tenants, _ = load_everything(require_token=False)
    tenant = pick_tenant(tenants, args[0] if args else None)
    days = int(args[1]) if len(args) > 1 and args[1].isdigit() else 7
    db_path = settings.data_dir / "bot.db"
    if not db_path.exists():
        print(f"{FAIL} База ще не створена — бот жодного разу не запускався.")
        return 1
    db = DB(db_path)
    since = (tenant.now() - timedelta(days=days)).strftime("%Y-%m-%d %H:%M:%S")
    rows = db.q(
        """SELECT e.*, c.first_name, c.username, c.phone FROM events e LEFT JOIN clients c ON c.id = e.client_id
           WHERE e.tenant = ? AND e.created_at >= ?
             AND e.kind IN ('msg_in', 'msg_out', 'handoff', 'booking_created', 'booking_cancelled',
                            'booking_rescheduled', 'admin_reply', 'ai_error')
           ORDER BY e.client_id, e.id""", tenant.slug, since)
    labels = {"msg_in": "Клієнт", "msg_out": "Бот", "handoff": "→ ПЕРЕДАНО ВЛАСНИКУ", "booking_created": "✓ ЗАПИС",
              "booking_cancelled": "✗ СКАСУВАННЯ", "booking_rescheduled": "↻ ПЕРЕНЕСЕННЯ",
              "admin_reply": "Власник відповів", "ai_error": "! ПОМИЛКА AI"}
    lines = [f"Діалоги «{tenant.name}» за {days} дн. (вивантажено {tenant.now():%d.%m.%Y %H:%M})"]
    current = None
    for r in rows:
        if r["client_id"] != current:
            current = r["client_id"]
            who = " · ".join(x for x in (r["first_name"], f"@{r['username']}" if r["username"] else "", r["phone"]) if x)
            lines += ["", f"=== {who or 'клієнт'} (id {current}) ==="]
        data = json.loads(r["data"] or "{}")
        detail = data.get("text") or data.get("reason") or data.get("error") or ""
        lines.append(f"[{r['created_at'][5:16]}] {labels.get(r['kind'], r['kind'])}: {detail}".rstrip(": "))
    out_path = settings.data_dir / f"dialogs-{tenant.slug}-{tenant.now():%Y%m%d}.txt"
    out_path.write_text("\n".join(lines), encoding="utf-8")
    print(f"{OK} Збережено {len(rows)} подій: {out_path}")
    return 0


# ====================================================================== test
def cmd_test() -> int:
    import unittest

    suite = unittest.defaultTestLoader.discover(str(ROOT / "tests"), top_level_dir=str(ROOT))
    result = unittest.TextTestRunner(verbosity=1).run(suite)
    return 0 if result.wasSuccessful() else 1


def main(argv: list[str]) -> int:
    cmd = argv[0] if argv else "run"
    rest = argv[1:]
    if cmd == "run":
        return cmd_run()
    if cmd == "check":
        return cmd_check()
    if cmd == "chat":
        return cmd_chat(rest)
    if cmd == "eval":
        return cmd_eval(rest)
    if cmd == "dialogs":
        return cmd_dialogs(rest)
    if cmd == "test":
        return cmd_test()
    print(__doc__)
    return 0 if cmd in ("help", "-h", "--help") else 1

