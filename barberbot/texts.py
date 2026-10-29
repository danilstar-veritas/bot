"""Усі тексти бота п'ятьма мовами (uk, ru, en, hu, de).

Будь-який текст можна перевизначити для конкретного закладу в його файлі
налаштувань, у розділі [texts.uk] / [texts.ru] / [texts.en].

Правило: ключі, що починаються з "btn_", "cmd_" або "alert_", — це підписи
кнопок і спливаючі підказки (звичайний текст). Решта — повідомлення з
HTML-розміткою Telegram (<b>, <i>, <code>).
"""

from __future__ import annotations

from html import escape

SUPPORTED_LANGS = ("uk", "ru", "en", "hu", "de")
PLAIN_PREFIXES = ("btn_", "cmd_", "alert_")


class Raw(str):
    """Рядок, який уже містить готовий HTML і не потребує екранування."""


WEEKDAYS_SHORT = {
    "uk": ["пн", "вт", "ср", "чт", "пт", "сб", "нд"],
    "ru": ["пн", "вт", "ср", "чт", "пт", "сб", "вс"],
    "en": ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"],
    "hu": ["H", "K", "Sze", "Cs", "P", "Szo", "V"],
    "de": ["Mo", "Di", "Mi", "Do", "Fr", "Sa", "So"],
}

# Повні назви днів для системного промпту (промпт написаний українською).
WEEKDAYS_FULL_UK = ["понеділок", "вівторок", "середа", "четвер", "пʼятниця", "субота", "неділя"]


TEXTS: dict[str, dict[str, str]] = {
    # ------------------------------------------------------------------ UK
    "uk": {
        # Меню клієнта
        "btn_book": "📅 Записатися",
        "btn_my": "🗓 Мої записи",
        "btn_prices": "💈 Послуги і ціни",
        "btn_contacts": "📍 Контакти",
        "btn_webapp": "📅 Онлайн-запис",
        "webapp_invite": "Оберіть послугу, майстра й зручний час у вікні запису 👇",
        "start": "Вітаю! 👋 Я бот-адміністратор <b>{name}</b>.\n\n"
                 "Допоможу записатися, перенести чи скасувати візит і відповім на питання.\n\n"
                 "Оберіть дію в меню 👇 або просто напишіть, що вас цікавить.",
        "start_no_ai": "Вітаю! 👋 Я бот-адміністратор <b>{name}</b>.\n\n"
                       "Допоможу записатися, перенести чи скасувати візит.\nОберіть дію в меню 👇",
        "start_admin_hint": "\n\n🛠 Ви адміністратор цього бота. Панель керування: /admin",
        # Запис кнопками
        "choose_service": "Оберіть послугу:",
        "choose_group": "✨ Оберіть категорію — а далі підберемо майстра й зручний для вас час 👇",
        "choose_service_in_group": "<b>{group}</b>\nОберіть послугу — а далі підберемо майстра й зручний для вас час 👇",
        "btn_service": "{title} · {price}",
        "choose_master": "💈 <b>{service}</b>\n💰 {price} · ⏱ {duration} хв{description}\n\nОберіть майстра 👇",
        "master_service_desc": "\n<i>{description}</i>",
        "btn_any_master": "👥 Будь-який майстер",
        "any_master": "будь-який майстер",
        "choose_day": "💈 <b>{service}</b> · {master}\n\nОберіть день:",
        "no_days": "💈 <b>{service}</b> · {master}\n\nНа жаль, на найближчі {days} дн. вільного часу немає 😕\n"
                   "Напишіть нам — спробуємо щось придумати.",
        "choose_time": "💈 <b>{service}</b> · {master}\n📅 {day}\n\nОберіть час:",
        "no_times": "📅 {day}: вільного часу вже немає. Оберіть інший день:",
        "btn_back": "⬅️ Назад",
        "day_today": "Сьогодні",
        "day_tomorrow": "Завтра",
        "card": "📝 <b>Перевірте, будь ласка:</b>\n\n💈 {service}\n👤 Майстер: {master}\n"
                "📅 {day} о {time}\n⏱ {duration} хв · 💰 {price}",
        "btn_confirm": "✅ Підтвердити",
        "btn_add_addon": "➕ {title} (+{duration} хв, +{price})",
        "btn_other_time": "⬅️ Інший час",
        "btn_no_change": "✖️ Ні, змінити",
        "ask_phone": "Залишилось вказати номер телефону, щоб майстер міг з вами зв'язатися.\n\n"
                     "Натисніть кнопку <b>«📱 Поділитися номером»</b> нижче або напишіть номер повідомленням.",
        "btn_share_phone": "📱 Поділитися номером",
        "btn_cancel": "Скасувати",
        "bad_phone": "Не схоже на номер телефону 🤔\nНатисніть кнопку «📱 Поділитися номером» "
                     "або напишіть номер із кодом країни, наприклад +380501234567.",
        "phone_saved": "Дякую, номер збережено 👍",
        "booking_aborted": "Добре, запис не створено. Якщо передумаєте — «📅 Записатися».",
        "booked": "✅ <b>Готово, ви записані!</b>\n\n💈 {service}\n👤 {master}\n📅 {day} о {time}\n💰 {price}{address}\n\n"
                  "Нагадаю заздалегідь. Перенести чи скасувати — у розділі «🗓 Мої записи».",
        "booked_address": "\n📍 {address}",
        "prepay_block": "\n\n💳 <b>Щоб закріпити запис — передоплата {amount}</b>\nКартка: <code>{card}</code>{recipient}\nОплатіть до <b>{deadline}</b>, інакше запис автоматично скасується. Передоплата входить у вартість послуги.\n\nПісля оплати натисніть «✅ Я оплатив(ла)» або надішліть сюди скрін 👇",
        "prepay_recipient": "\nОтримувач: {recipient}",
        "btn_prepay_done": "✅ Я оплатив(ла)",
        "btn_prepay_done_item": "✅ Я оплатив(ла) {short}",
        "prepay_claimed_client": "Дякуємо! 🙏 Адміністратор перевірить оплату й підтвердить запис — повідомимо тут.",
        "prepay_screenshot_client": "Дякуємо, скрін отримали! 🙏 Адміністратор перевірить оплату й підтвердить запис — повідомимо тут.",
        "prepay_photo_ask": "📸 Це скрін оплати передоплати?",
        "btn_photo_is_payment": "✅ Так, це оплата",
        "btn_photo_other": "Ні, інше питання",
        "prepay_already_paid": "Передоплату вже підтверджено ✅",
        "prepay_paid_client": "✅ <b>Передоплату отримано — запис підтверджено!</b>\n💈 {service} · {master}\n📅 {day} о {time}\n\nЧекаємо на вас 💛",
        "client_cancelled_unpaid": "😔 На жаль, ваш запис скасовано: передоплату не отримано вчасно.\n💈 {service} · {master}\n📅 {day} о {time}\n\nЯкщо ще актуально — запишіться знову, будемо раді 💛",
        "my_prepay_waiting": "\n💳 Очікуємо передоплату {amount} до {deadline}",
        "my_prepay_claimed": "\n💳 Перевіряємо вашу оплату ⏳",
        "my_prepay_paid": "\n💳 Передоплату отримано ✅",
        "already_booked": "✅ Ви вже записані на цей час.",
        "slot_taken": "Ой, цей час щойно зайняли 😕 Оберіть, будь ласка, інший:",
        "week_limit": "На цей тиждень у вас уже максимум записів — {limit} 🙏\nОберіть інший тиждень або перенесіть один із наявних записів.",
        "too_many_active": "Активних записів у вас уже {count} — це максимум. "
                           "Перенесіть або скасуйте один у розділі «🗓 Мої записи».",
        "booking_error": "Не вдалося створити запис 😕 Спробуйте ще раз або напишіть нам.",
        "proposal_declined": "Добре 🙂 Напишіть, що змінити — підберу інший варіант.",
        # Мої записи
        "my_none": "У вас поки немає запланованих візитів 🙂\nСаме час це виправити — оберіть зручний час 👇",
        "my_header": "✨ <b>Ваші записи</b> ✨",
        "my_item": "\n\n📅 <b>{day} о {time}</b>\n✂️ {service}\n💈 Майстер: {master}",
        "my_footer": "\n\n💛 Ми вже чекаємо на вас! Приходьте на кілька хвилин раніше — встигнете видихнути "
                     "й налаштуватися на новий образ ✨\n\nЯкщо плани змінились — перенесіть або скасуйте запис "
                     "кнопками нижче 👇",
        "btn_resched_item": "🔁 Перенести {short}",
        "btn_cancel_item": "❌ Скасувати {short}",
        "cancel_ask": "Скасувати запис?\n\n💈 {service} · {master}\n📅 {day} о {time}",
        "btn_yes_cancel": "Так, скасувати",
        "btn_no": "Ні",
        "cancel_kept": "Добре, запис залишається ✅",
        "cancelled": "Запис скасовано.\nБудемо раді бачити вас іншим разом! Щоб записатися знову — «📅 Записатися».",
        "cancel_too_late": "До візиту менше {hours} год, тому скасувати онлайн уже не можна. "
                           "Зателефонуйте нам, будь ласка{phone}.",
        "cancel_too_late_phone": ": {phone}",
        "booking_inactive": "Цей запис уже неактивний.",
        "resched_choose_day": "🔁 <b>Перенесення</b>\n💈 {service} · {master}\nЗараз: {day} о {time}\n\nОберіть новий день:",
        "resched_choose_time": "🔁 <b>Перенесення</b>\n💈 {service} · {master}\n📅 {day}\n\nОберіть новий час:",
        "resched_card": "🔁 <b>Перенести запис?</b>\n\n💈 {service} · {master}\nБуло: {old}\nСтане: <b>{new}</b>",
        "btn_confirm_resched": "✅ Перенести",
        "rescheduled": "✅ Запис перенесено.\n\n💈 {service} · {master}\n📅 <b>{day} о {time}</b>",
        "resched_none": "На найближчі {days} дн. вільного часу немає 😕 Напишіть нам — щось придумаємо.",
        # Інформація
        "prices_header": "💈 <b>{name}</b>\n✨ <b>ПОСЛУГИ ТА ЦІНИ</b> ✨\n<i>Обирайте, що до душі, — записатися можна одразу, кнопкою внизу 👇</i>",
        "price_group": "\n\n━━━━━━━━━━━━\n<b>{group}</b>",
        "price_item": "\n\n<b>{title}</b> — {price}\n⏱ {duration} хв",
        "price_desc": "\n{description}",
        "prices_addons_header": "\n\n➕ <b>Можна додати до стрижки</b> (кнопкою під час запису)",
        "price_addon_item": "\n{title} — +{price}, +{duration} хв",
        "contacts_header": "📍 <b>{name}</b>",
        "contacts_address": "\n\n🏠 {address}",
        "contacts_phone": "\n📞 {phone}",
        "contacts_hours": "\n\n🕒 <b>Графік роботи</b>\n{hours}",
        "contacts_directions": "\n\n🚗 {directions}",
        "contacts_payment": "\n💳 {payment}",
        "contacts_prepay": "\n💳 Передоплата {amount} — реквізити надішлемо одразу після запису (оплатити протягом {hours} год).",
        "contacts_masters_header": "\n\n━━━━━━━━━━━━\n👥 <b>Наші майстри</b>",
        "contacts_master": "\n\n💈 <b>{name}</b>{about}\n🗓 {schedule}",
        "contacts_master_about": "\n<i>{about}</i>",
        "btn_map": "🗺 Відкрити на карті",
        "day_off": "вихідний",
        # Нагадування
        "reminder": "⏰ <b>Нагадування про візит</b>\n\n📅 {day} о {time}\n💈 {service} · {master}{address}",
        "btn_will_come": "✅ Прийду",
        "btn_resched": "🔁 Перенести",
        "btn_cancel_booking": "❌ Скасувати",
        "will_come_ok": "\n\n✅ Чудово, чекаємо!",
        "nudge": "Привіт, {name}! 👋\nМинуло вже {weeks} тиж. з вашого останнього візиту ({service}). "
                 "Записати вас знову?",
        "btn_book_again": "📅 Записатися",
        "btn_no_nudges": "🔕 Не нагадувати",
        "nudges_off": "Добре, більше не нагадуватиму 🙂",
        # AI та передача людині
        "ai_off": "Оберіть дію в меню 👇 — так буде найшвидше.",
        "ai_error": "Вибачте, зараз не можу відповісти 😔\nСкористайтеся кнопками меню 👇 або спробуйте трохи пізніше.",
        "ai_refusal": "Вибачте, з цим я не допоможу 🙂 Можу записати вас на послугу або передати питання адміністратору.",
        "rate_limited": "Забагато повідомлень за короткий час 🙈 Скористайтеся кнопками меню 👇 або напишіть трохи пізніше.",
        "handoff_client": "Передав ваше питання адміністратору — він відповість тут, у цьому чаті 🙌",
        "handoff_no_admin": "З цим питанням краще звернутися напряму до адміністратора{phone} 🙏",
        "media_received": "Отримав 👍 Передаю адміністратору — він відповість тут, у цьому чаті.",
        "voice_unsupported": "Голосові я поки не слухаю 🙈 Напишіть, будь ласка, текстом.",
        "unsupported": "Я розумію лише текстові повідомлення 🙂",
        "meta_choose_lang": "🌐 Оберіть мову:",
        "btn_language": "🌐 Мова",
        "paused_ack": "Дякуємо за повідомлення! Адміністратор відповість найближчим часом.",
        "admin_title": "Адміністратор",
        "admin_reply_to_client": "👤 <b>{title}:</b>\n{text}",
        "alert_expired": "Ця кнопка вже неактуальна. Почніть, будь ласка, заново.",
        "alert_no_access": "Немає доступу",
        "unknown_command": "Не знаю такої команди 🤔 Оберіть дію в меню 👇",
        "myid": "Ваш Telegram ID: <code>{id}</code>",
        "state_cleared": "Скасовано.",
        # Адмін
        "admin_help": "🛠 <b>Панель керування · {name}</b>\n\n"
                      "/book — записати клієнта (дзвінок, візит)\n"
                      "/today — записи на сьогодні\n"
                      "/tomorrow — записи на завтра\n"
                      "/day 30.10 — записи на будь-яку дату\n"
                      "/week — записи на 7 днів\n"
                      "/all — усі майбутні записи\n"
                      "/find — пошук клієнта (ім'я, @username чи номер)\n"
                      "/stats — статистика й виручка за 30 днів (/stats 7 — за 7)\n"
                      "/export — вивантажити записи в Excel\n"
                      "/block — закрити час (вихідний, відпустка, запис по телефону)\n"
                      "/blocks — список закритого часу\n"
                      "/masters — майстри в боті: запросити, відключити\n"
                      "/prices — змінити ціни на послуги\n"
                      "/pause — вимкнути AI: усі повідомлення клієнтів ідуть вам\n"
                      "/resume — увімкнути AI назад\n"
                      "/reload — перечитати налаштування з файлу\n"
                      "/myid — ваш Telegram ID\n\n"
                      "💬 Щоб відповісти клієнту, відповідайте (свайп вліво → «Відповісти») "
                      "на його повідомлення, яке переслав бот.\n\n"
                      "AI-відповіді: {ai_status}",
        "ai_status_on": "✅ увімкнено",
        "ai_status_paused": "⏸ на паузі (/resume)",
        "ai_status_nokey": "⚪️ вимкнено (немає ключа API в settings.toml)",
        "ai_status_disabled": "⚪️ вимкнено в налаштуваннях закладу",
        "adm_new_booking": "🆕 <b>Новий запис</b>{via}\n\n👤 {client}\n💈 {service} · {master}\n📅 {day} о {time}\n💰 {price}",
        "adm_via_ai": " · через AI-чат 🤖",
        "adm_via_web": " · через онлайн-запис 📲",
        "adm_cancelled": "❌ <b>Скасування</b>\n\n👤 {client}\n💈 {service} · {master}\n📅 {day} о {time}",
        "adm_rescheduled": "🔁 <b>Перенесення</b>\n\n👤 {client}\n💈 {service} · {master}\nБуло: {old}\nСтало: <b>{new}</b>",
        "adm_handoff": "🙋 <b>Потрібна ваша відповідь</b>\n\n👤 {client}\n❓ {reason}{summary}\n\n"
                       "<b>Останні повідомлення:</b>\n{transcript}\n\n"
                       "↩️ Відповідайте на це повідомлення (свайп вліво) — бот перешле відповідь клієнту. "
                       "AI для цього клієнта на паузі {hours} год.",
        "adm_handoff_summary": "\n📝 {summary}",
        "adm_reason_media": "Клієнт надіслав фото або файл (можливо, оплата)",
        "adm_tr_client": "— Клієнт: {text}",
        "adm_tr_bot": "— Бот: {text}",
        "adm_tr_empty": "(немає)",
        "btn_adm_reply": "✍️ Відповісти",
        "btn_adm_resume": "▶️ Повернути бота",
        "adm_client_msg": "💬 <b>{client}</b>:\n{text}",
        "adm_client_media": "💬 {client}",
        "adm_reply_prompt": "Напишіть відповідь для {client} одним повідомленням (або /cancel):",
        "adm_reply_sent": "✅ Надіслано: {client}",
        "adm_reply_failed": "⚠️ Не вдалося надіслати — можливо, клієнт заблокував бота.",
        "adm_resumed": "▶️ AI знову відповідає: {client}",
        "adm_day_header": "📅 <b>{day}</b>{master} — записів: {count}",
        "adm_day_empty": "📅 <b>{day}</b>{master} — записів немає.",
        "adm_item": "\n\n<b>{n}. {start}–{end}</b> · {master}\n💈 {service}\n👤 {client}{flags}",
        "adm_list_day": "\n\n📅 <b>{day}</b> — записів: {count}",
        "adm_list_hint": "\n\nНатисніть запис, щоб перенести, скасувати чи відмітити оплату 👇",
        "adm_day_master": " · {name}",
        "adm_day_hint": "\n\nНатисніть запис, щоб перенести, скасувати, відмітити неявку чи оплату 👇",
        "adm_day_pick": "📅 Оберіть день:",
        "adm_day_usage": "📅 Вкажіть дату, наприклад: /day 30.10 або /day завтра",
        "btn_adm_booking_item": "⚙️ {n} · {when} · {client}",
        "btn_day_prev": "◀️ {day}",
        "btn_day_next": "{day} ▶️",
        "btn_day_pick": "📅 Дата",
        "btn_master_all": "👥 Усі",
        "btn_master_selected": "✅ {name}",
        "adm_card": "📋 <b>Запис #{id}</b>\n\n{summary}\n💰 {price}",
        "adm_card_source_buttons": "\n📱 Записався сам",
        "adm_card_source_ai": "\n🤖 Записався через AI-чат",
        "adm_card_source_admin": "\n📞 Записав адміністратор",
        "adm_card_noshow": "\n🚫 Клієнт не прийшов",
        "adm_card_cancelled": "\n❌ Скасовано — {by}",
        "adm_card_confirmed": "\n✅ Клієнт підтвердив, що прийде",
        "btn_adm_resched": "🔁 Перенести",
        "btn_adm_cancel_short": "🗑 Скасувати",
        "btn_adm_noshow": "🚫 Не прийшов",
        "btn_adm_client": "👤 Клієнт",
        "btn_adm_write": "✉️ Написати",
        "adm_resched_day": "🔁 <b>Перенесення запису #{id}</b>\n\n{summary}\n\nОберіть новий день 👇",
        "adm_resched_none": "🔁 Вільних днів для перенесення немає.\n\n{summary}",
        "adm_resched_time": "🔁 <b>#{id}</b> · {service} · {master}\n📅 {day} — оберіть час 👇",
        "adm_resched_confirm": "🔁 <b>Перенести запис?</b>\n\n💈 {service}\n👤 {client}\nБуло: {old}\nСтане: <b>{new}</b>\n\n{who}",
        "btn_adm_resched_yes": "✅ Перенести",
        "adm_resched_same": "Це той самий час — нічого не змінено.",
        "btn_adm_change_master": "👤 Змінити майстра",
        "btn_adm_master_pick": "💈 {name}",
        "adm_change_master": "👤 <b>Інший майстер для запису #{id}</b>\n\n{summary}\n\nОберіть майстра 👇",
        "adm_change_master_none": "👤 Послугу «{service}» більше ніхто з майстрів не робить.",
        "adm_new_master": "👤 Новий майстер: <b>{master}</b>",
        "adm_master_busy": "👤 Новий майстер: <b>{master}</b>\n⚠️ О {time} цей майстер зайнятий — оберіть інший день.",
        "adm_resched_done": "🔁 <b>Перенесено</b>\n\n{summary}\n\nБуло: {old}\n{who}",
        "adm_resched_notified": "Клієнта повідомлено.",
        "adm_resched_offline": "Клієнта немає в Telegram — повідомте його самі.",
        "adm_find_usage": "🔎 Пошук клієнта: /find Іван, /find @username або /find 0671 (частина номера)",
        "adm_find_none": "🔎 За «{q}» нікого не знайдено.",
        "adm_find_many": "🔎 Знайдено: {count}. Оберіть клієнта 👇",
        "btn_adm_client_item": "👤 {label}",
        "adm_client_card": "👤 <b>{name}</b>\n{contacts}\n{tg}\n\n📊 Візитів: {done} · неявок: {noshow} · скасувань: {cancelled}\n💰 Разом: {spent}{last}{upcoming}{notes}",
        "adm_client_tg_yes": "✉️ Є в боті",
        "adm_client_tg_no": "📵 Немає в Telegram",
        "adm_client_last": "\n🗓 Останній візит: {day} · {service}",
        "adm_client_upcoming": "\n\n<b>Майбутні записи:</b>{items}",
        "adm_client_upcoming_item": "\n• {when} · {service}",
        "adm_client_notes": "\n\n📝 {notes}",
        "btn_adm_client_booking": "⚙️ {when} · {service}",
        "btn_adm_client_book": "📞 Записати",
        "adm_export_usage": "📊 /export — записи за 30 днів і всі майбутні; /export 90 — за 90 днів.",
        "adm_export_empty": "За цей період записів немає.",
        "adm_export_caption": "📊 Записи з {start} (і всі майбутні): {count}",
        "adm_export_headers": "Дата|Час|Кінець|Майстер|Послуга|Ціна|Статус|Клієнт|Телефон|Telegram|Джерело|Передоплата|Коментар|Створено",
        "adm_export_sheet": "Записи",
        "adm_export_statuses": "заплановано|відбувся|не прийшов|скасовано",
        "adm_export_sources": "сам|AI-чат|адмін",
        "adm_export_prepay": "очікуємо|каже, що оплатив|оплачено",
        "adm_master_revenue": "\n   {name}: {count} · {revenue}",
        "adm_evening_report": "🌙 <b>Підсумок дня · {day}</b>\n\n✅ Відбулося: {done} · 🚫 неявок: {noshow} · ❌ скасовано: {cancelled}\n💰 Виручка: <b>{revenue}</b>{by_master}\n\n📅 Завтра записів: {tomorrow}",
        "client_rescheduled_by_admin": "🔁 Адміністратор переніс ваш запис:\n💈 {service} · {master}\nБуло: {old}\nСтало: <b>{new}</b>\n\nЯкщо час не підходить — змініть у «🗓 Мої записи» або напишіть нам.",
        "adm_booking_summary": "<b>{day}, {start}–{end}</b> · {master}\n💈 {service}\n👤 {client}",
        "adm_noshow_done": "🚫 {client} ({time}) — не прийшов",
        "adm_cancel_ask": "Скасувати цей запис?\n\n{booking}\n\n{who}",
        "adm_cancel_notify": "Клієнт отримає повідомлення в Telegram.",
        "adm_cancel_offline": "Клієнта немає в Telegram — повідомте його самі.",
        "adm_cancelled_done": "🗑 <b>Скасовано</b>\n\n{booking}\n\nКлієнта повідомлено.",
        "adm_cancelled_done_offline": "🗑 <b>Скасовано</b>\n\n{booking}\n\nКлієнта немає в Telegram — повідомте його самі.",
        "adm_cancelled_header": "\n\n➖➖➖\n❌ <b>Скасовані</b> — {count}",
        "adm_cancelled_item": "\n{day} {start} · {master} · {service} · {client} — {by}",
        "adm_cancelled_by_client": "скасував клієнт",
        "adm_cancelled_by_admin": "скасував адмін",
        "adm_new_booking_prepay": "\n💳 Чекаємо передоплату {amount} до {deadline}",
        "adm_prepay_claim_note": "💳 <b>Клієнт повідомляє про оплату</b>\n\n{booking}\n\nПеревірте надходження {amount} і підтвердьте 👇",
        "adm_prepay_screenshot": "💳 <b>Клієнт надіслав підтвердження оплати</b> (скрін вище)\n\n{booking}\n\nПеревірте надходження {amount} і підтвердьте 👇",
        "adm_prepay_overdue": "⏰ <b>Оплату ще не підтверджено</b>\nКлієнт повідомив про оплату, але минуло вже {hours} год. Перевірте, будь ласка: такий запис автоматично не скасовується.\n\n{booking}",
        "btn_adm_prepay_ok": "✅ Оплату отримано",
        "btn_adm_cancel_booking": "🗑 Скасувати запис",
        "adm_prepay_ok_done": "✅ <b>Передоплату підтверджено</b>, клієнта повідомлено.\n\n{booking}",
        "adm_prepay_ok_alert": "✅ Оплату підтверджено",
        "adm_prepay_already": "Передоплату вже підтверджено.",
        "adm_prepay_waiting": "\n💳 ⏳ чекаємо передоплату",
        "adm_prepay_claimed": "\n💳 ❔ клієнт каже, що оплатив — перевірте",
        "adm_prepay_paid": "\n💳 ✅ передоплату отримано",
        "adm_cancelled_by_unpaid": "не оплачено",
        "adm_cancelled_unpaid": "⏰ <b>Запис скасовано автоматично</b> — передоплату не підтверджено за {hours} год.\n\n{booking}",
        "btn_adm_clear_cancelled": "🧹 Прибрати скасовані ({count})",
        "adm_clear_ask": "Прибрати скасовані записи зі списку ({count})?\nУ /all їх більше не буде, а в статистиці вони залишаться.",
        "btn_adm_yes_clear": "Так, прибрати",
        "adm_cleared_done": "🧹 Прибрано скасованих записів: {count}. Оновлений список — /all",
        "btn_adm_yes_cancel": "Так, скасувати",
        "client_cancelled_by_admin": "На жаль, ваш запис скасовано адміністратором:\n💈 {service} · {master}\n"
                                     "📅 {day} о {time}\n\nОберіть інший час — «📅 Записатися» — або напишіть нам.",
        "adm_week_header": "🗓 <b>Записи на 7 днів</b>",
        "adm_week_empty": "\n\nЗаписів немає.",
        "adm_week_more": "\n\n➕ Пізніше ще записів: {count} — /all",
        "adm_all_header": "🗓 <b>Усі майбутні записи</b>",
        "adm_note_line": "\n📝 {note}",
        "adm_via_admin": " · записав адміністратор 📞",
        "btn_adm_book_confirm": "✅ Записати",
        "btn_adm_book_cancel": "✖️ Скасувати",
        "adm_book_service": "📞 <b>Запис клієнта</b>\nОберіть послугу:",
        "adm_book_group": "📞 <b>Запис клієнта</b>\nОберіть категорію — далі послуга, майстер, день і час 👇",
        "adm_book_in_group": "📞 <b>{group}</b>\nОберіть послугу — далі майстер, день і час 👇",
        "adm_book_master": "📞 {service}\nОберіть майстра:",
        "adm_book_day": "📞 {service} · {master}\nОберіть день:",
        "adm_book_time": "📞 {service} · {master} · {day}\nОберіть час:",
        "adm_book_no_days": "У майстра {master} немає вільних днів на «{service}». Оберіть іншого майстра:",
        "adm_book_client_prompt": "📞 {service} · {master} · {day} о {time}\n\n"
                                  "Надішліть дані клієнта одним повідомленням: <b>ім'я</b> і <b>телефон</b>, "
                                  "з нового рядка — коментар (необов'язково). Наприклад:\n"
                                  "<code>Олена +380671234567\nхоче коротше, ніж минулого разу</code>\n\n"
                                  "Або поділіться контактом клієнта з Telegram (📎 → Контакт).\n/cancel — скасувати.",
        "adm_book_need_name": "Не бачу імені клієнта. Надішліть ще раз: ім'я, телефон, з нового рядка — коментар.",
        "adm_book_card": "📞 <b>Перевірте запис</b>\n\n👤 {client}\n💈 {service} · {master}\n📅 {day} о {time}\n"
                         "💰 {price}{note}\n\n{hint}\n\nЩоб змінити дані — просто надішліть їх ще раз.",
        "adm_book_hint_tg": "✉️ Клієнт уже є в боті ({client}) — отримає повідомлення і нагадування.",
        "adm_book_hint_known": "🗂 Клієнт уже є в базі ({client}), але не в Telegram — повідомлень не отримає.",
        "adm_book_hint_offline": "📵 Новий клієнт без Telegram — повідомлень і нагадувань не отримає.",
        "adm_book_duplicate": "У клієнта вже є запис на цей час (#{id}).",
        "adm_book_done": "✅ <b>Записано</b> <code>#{id}</code>\n👤 {client}\n💈 {service} · {master}\n"
                         "📅 {day} о {time}{notified}",
        "adm_book_notified": "\n\n✉️ Клієнту надіслано повідомлення в Telegram.",
        "adm_book_not_notified": "\n\n📵 Клієнт не отримав повідомлення (немає в Telegram) — за потреби подзвоніть.",
        "adm_book_aborted": "Запис не створено.",
        "client_booked_by_admin": "📞 Адміністратор записав вас:\n💈 {service} · {master}\n📅 {day} о {time}\n💰 {price}\n\n"
                                  "Перенести чи скасувати — «🗓 Мої записи».",
        "adm_block_usage": "🔒 <b>Закрити час</b>\n\nФормат: <code>/block майстер дата [час] [коментар]</code>\n\n"
                           "Приклади:\n<code>/block {example} 30.10</code> — весь день\n"
                           "<code>/block {example} 30.10 14:00-16:00 запис по телефону</code>\n"
                           "<code>/block all 31.12</code> — вихідний для всіх\n\nМайстри: {masters}",
        "adm_block_bad": "Не зрозумів команду 🤔\n\n{usage}",
        "adm_block_done": "🔒 Закрито: {master}, {day} {range}{note}",
        "adm_block_conflicts": "\n\n⚠️ На цей час уже є записи — скасуйте їх (/today, /tomorrow) або попередьте клієнтів:{lines}",
        "adm_all_masters": "усі майстри",
        "adm_whole_day": "(весь день)",
        "adm_blocks_header": "🔒 <b>Закритий час</b> (натисніть, щоб видалити):",
        "adm_blocks_empty": "Закритого часу немає.",
        "btn_adm_block_item": "🗑 {master} · {day} {range}",
        "adm_block_deleted": "🔓 Видалено. Цей час знову доступний для запису.",
        "adm_paused": "⏸ AI вимкнено. Усі повідомлення клієнтів пересилатимуться вам; кнопки запису працюють.\n"
                      "Увімкнути: /resume",
        "adm_resumed_all": "▶️ AI знову відповідає клієнтам.",
        "adm_reloaded": "🔄 Налаштування оновлено: послуг — {services}, майстрів — {masters}.",
        "adm_reload_failed": "❌ У файлі налаштувань помилка, залишаю попередні:\n<code>{error}</code>",
        "adm_reload_token": "\n⚠️ Токен бота змінено — перезапустіть бота, щоб це застосувати.",
        "adm_digest": "☀️ <b>Доброго ранку!</b>\n\n{body}",
        "adm_ai_alert": "⚠️ <b>AI не відповідає</b> ({name})\n<code>{error}</code>\n\n"
                        "Бот працює на кнопках. Перевірте ключ API та баланс на console.anthropic.com.",
        "adm_budget_alert": "⚠️ Денний ліміт AI вичерпано ({name}). До кінця дня бот відповідає лише кнопками. "
                            "Ліміт змінюється в settings.toml (daily_token_limit).",
        "adm_stats": "📊 <b>Статистика за {days} днів</b>\n\n"
                     "<b>Записи</b>\n"
                     "• створено: {created} (AI-чат: {by_ai}, кнопки: {by_buttons}, адмін: {by_admin})\n"
                     "• уночі (22:00–08:00): {night}\n"
                     "• відбулося: {done} · не прийшли: {noshow} · скасовано: {cancelled}\n"
                     "• попереду: {upcoming}\n\n"
                     "<b>Виручка</b>\n"
                     "• {revenue} · середній чек {avg_check}{by_master}\n"
                     "• очікується з майбутніх записів: {expected}\n\n"
                     "<b>Діалоги</b>\n"
                     "• клієнтів писали: {clients}\n"
                     "• передано вам: {handoffs}\n"
                     "• бот впорався сам: {auto_rate}\n\n"
                     "<b>Нагадування</b>\n"
                     "• надіслано: {reminders} · «Прийду»: {confirmed}\n\n"
                     "<b>AI</b>\n"
                     "• повідомлень оброблено: {ai_calls} · токенів: {tokens}\n"
                     "• приблизна вартість: ${cost}",
        "adm_client_noname": "Клієнт",
        # Команди в меню Telegram
        "cmd_start": "Головне меню",
        "cmd_admin": "Панель власника",
        "cmd_today": "Записи на сьогодні",
        "cmd_tomorrow": "Записи на завтра",
        "cmd_book": "Записати клієнта",
        "cmd_day": "Записи на дату",
        "cmd_find": "Пошук клієнта",
        "cmd_export": "Вивантажити в Excel",
        "cmd_week": "Записи на 7 днів",
        "cmd_all": "Усі майбутні записи",
        "cmd_stats": "Статистика",
        "cmd_block": "Закрити час",
        "cmd_blocks": "Закритий час",
        "cmd_pause": "Вимкнути AI",
        "cmd_resume": "Увімкнути AI",
        "cmd_reload": "Оновити налаштування",
        "cmd_myid": "Мій Telegram ID",
        "cmd_masters": "Майстри в боті",
        "cmd_prices": "Змінити ціни",
        "adm_prices": "💰 <b>Ціни на послуги</b>\nНатисніть послугу, щоб змінити ціну 👇",
        "adm_prices_changed": "\n\n✏️ — ціну змінено тут, у боті (у файлі налаштувань стара).",
        "adm_price_ask": "💰 <b>{title}</b>\nЗараз: <b>{price}</b>\n\nНапишіть нову ціну числом, наприклад 650.",
        "adm_price_file": "\nУ файлі налаштувань: {price}.",
        "btn_adm_price_reset": "↩️ Повернути {price}",
        "adm_price_bad": "Не схоже на ціну 🤔 Напишіть лише число, наприклад 650. Скасувати — /cancel",
        "adm_price_done": "✅ <b>{title}</b>: {old} → <b>{new}</b>\nНову ціну вже бачать клієнти й AI. "
                          "Записи, зроблені раніше, лишаються за старою ціною.",
        "adm_price_combos": "\nЦіни комбінацій із додатками перераховано.",
        "adm_price_changed_note": "💰 {admin} змінив ціну: <b>{title}</b> {old} → <b>{new}</b>",
        "cmd_my": "Мій день",
        "cmd_myweek": "Мій тиждень",
        "cmd_off": "Закрити час",
        "cmd_offs": "Мій закритий час",
        # Майстри: адмін
        "adm_masters": "✂️ <b>Майстри в боті</b>\n\nПідключений майстер бачить свої записи, сам закриває час "
                       "і отримує сповіщення про своїх клієнтів.\n{items}",
        "adm_masters_on": "\n✅ <b>{name}</b> — {who}",
        "adm_masters_off": "\n⚪️ <b>{name}</b> — не підключено",
        "btn_adm_master_invite": "🔗 Запросити: {name}",
        "btn_adm_master_unlink": "✖️ Відключити: {name}",
        "btn_adm_yes_unlink": "✖️ Так, відключити",
        "btn_adm_open": "📋 Відкрити запис",
        "adm_master_invite": "🔗 Посилання для майстра <b>{name}</b>:\n\n{link}\n\nПерешліть його майстру — "
                             "хай відкриє і натисне «Почати». Посилання одноразове, діє {hours} год.",
        "adm_master_no_username": "Не вдалося отримати адресу бота. Спробуйте ще раз за хвилину.",
        "adm_master_unlink_ask": "Відключити майстра <b>{name}</b> від бота? Він більше не бачитиме записи "
                                 "й не отримуватиме сповіщень.",
        "adm_master_unlinked": "✖️ Майстра {name} відключено від бота.",
        "adm_master_joined": "✂️ Майстер <b>{name}</b> підключився до бота ({who}).",
        "adm_master_noshow": "🚫 <b>Майстер {master} відмітив неявку</b>\n\n{booking}",
        "adm_master_off": "🌴 Майстер <b>{master}</b> закрив час: {day} {range}",
        "adm_master_off_conflicts": "\n\n⚠️ <b>На цей час уже є записи</b> — домовтеся з клієнтами "
                                    "(перенести чи скасувати):{lines}",
        "adm_master_on": "🔓 Майстер <b>{master}</b> відкрив час: {day} {range}",
        # Майстри: сам майстер
        "mst_invite_bad": "Це посилання недійсне або вже використане. Попросіть адміністратора надіслати нове.",
        "mst_joined": "✅ <b>Вас підключено як майстра «{name}».</b>\n\n",
        "mst_start": "✂️ <b>{name}</b>, ви майстер у боті «{shop}».\n\n"
                     "📅 <b>Мій день</b> — ваші записи, гортайте дні ◀️ ▶️\n"
                     "🗓 <b>Мій тиждень</b> — записи на 7 днів\n"
                     "🌴 <b>Закрити час</b> — вихідний, перерва, особисті справи\n"
                     "🔒 <b>Мій закритий час</b> — переглянути й відкрити назад\n\n"
                     "Бот повідомить про нові записи, скасування й перенесення, зранку надішле розклад, "
                     "а перед кожним клієнтом — нагадає.",
        "mst_unlinked": "Вас відключено від бота як майстра. Записатися як клієнт можна в меню 👇",
        "btn_mst_day": "📅 Мій день",
        "btn_mst_week": "🗓 Мій тиждень",
        "btn_mst_off": "🌴 Закрити час",
        "btn_mst_offs": "🔒 Мій закритий час",
        "btn_mst_to_day": "⬅️ До дня",
        "mst_day_hint": "\n\nНатисніть запис, щоб відкрити картку 👇",
        "mst_day_off": "\n\n🌴 За графіком у вас вихідний.",
        "mst_day_blocks": "\n\n🔒 Закрито: {ranges}",
        "mst_week_header": "🗓 <b>Ваші записи на 7 днів</b>",
        "mst_off_day": "🌴 <b>Закрити час</b>\n\nОберіть день:",
        "mst_off_range": "🌴 <b>{day}</b> · ваш графік {hours}\n\nЗакрити весь день чи з котрої години?",
        "mst_off_whole_only": "🌴 <b>{day}</b> · {hours}\n\nЗакрити весь день?",
        "mst_off_no_work": "за графіком вихідний",
        "mst_off_end": "🌴 <b>{day}</b>, з {start}\n\nДо котрої години?",
        "btn_mst_whole_day": "🌴 Весь день",
        "btn_mst_off_yes": "✅ Закрити",
        "mst_off_confirm": "Закрити <b>{day} {range}</b>?\nКлієнти не зможуть записатися на цей час.{conflicts}",
        "mst_off_conflicts": "\n\n⚠️ На цей час уже є записи — адміністратор отримає сповіщення, "
                             "щоб домовитися з клієнтами:{lines}",
        "mst_off_done": "🔒 Закрито: <b>{day} {range}</b>. Клієнти не зможуть записатися на цей час.",
        "mst_off_done_conflicts": "\n\n⚠️ Записи на цей час лишилися — адміністратора повідомлено:{lines}",
        "mst_offs_header": "🔒 <b>Ваш закритий час</b>\nНатисніть, щоб відкрити назад:",
        "mst_offs_header_none": "🔒 <b>Ваш закритий час</b>",
        "mst_offs_admin": "\n\nЗакрив адміністратор (змінити може лише він):{lines}",
        "mst_offs_empty": "🔒 Закритого часу немає. Щоб закрити — «🌴 Закрити час».",
        "btn_mst_block_item": "🗑 {label}",
        "alert_mst_opened": "Час знову відкрито для запису",
        "mst_new": "🆕 <b>Новий запис до вас</b>\n\n📅 {day} о {time}\n💈 {service}\n👤 {client}",
        "mst_cancelled": "❌ <b>Запис скасовано</b>\n\n📅 {day} о {time}\n💈 {service}\n👤 {client}",
        "mst_moved": "🔁 <b>Запис перейшов до іншого майстра</b>\n\n📅 {day} о {time}\n💈 {service}\n👤 {client}",
        "mst_rescheduled": "🔁 <b>Запис перенесено</b>\n\n💈 {service}\n👤 {client}\nБуло: {old}\nСтало: <b>{new}</b>",
        "mst_digest": "☀️ <b>Доброго ранку, {name}!</b>\n\n{body}",
        "mst_heads_up": "⏰ <b>О {time}</b> (через {min} хв) — {client}\n💈 {service}",
    },
    # ------------------------------------------------------------------ RU
    "ru": {
        "btn_book": "📅 Записаться",
        "btn_my": "🗓 Мои записи",
        "btn_prices": "💈 Услуги и цены",
        "btn_contacts": "📍 Контакты",
        "btn_webapp": "📅 Онлайн-запись",
        "webapp_invite": "Выберите услугу, мастера и удобное время в окне записи 👇",
        "start": "Здравствуйте! 👋 Я бот-администратор <b>{name}</b>.\n\n"
                 "Помогу записаться, перенести или отменить визит и отвечу на вопросы.\n\n"
                 "Выберите действие в меню 👇 или просто напишите, что вас интересует.",
        "start_no_ai": "Здравствуйте! 👋 Я бот-администратор <b>{name}</b>.\n\n"
                       "Помогу записаться, перенести или отменить визит.\nВыберите действие в меню 👇",
        "start_admin_hint": "\n\n🛠 Вы администратор этого бота. Панель управления: /admin",
        "choose_service": "Выберите услугу:",
        "choose_group": "✨ Выберите категорию — а дальше подберём мастера и удобное для вас время 👇",
        "choose_service_in_group": "<b>{group}</b>\nВыберите услугу — а дальше подберём мастера и удобное для вас время 👇",
        "btn_service": "{title} · {price}",
        "choose_master": "💈 <b>{service}</b>\n💰 {price} · ⏱ {duration} мин{description}\n\nВыберите мастера 👇",
        "master_service_desc": "\n<i>{description}</i>",
        "btn_any_master": "👥 Любой мастер",
        "any_master": "любой мастер",
        "choose_day": "💈 <b>{service}</b> · {master}\n\nВыберите день:",
        "no_days": "💈 <b>{service}</b> · {master}\n\nК сожалению, на ближайшие {days} дн. свободного времени нет 😕\n"
                   "Напишите нам — попробуем что-нибудь придумать.",
        "choose_time": "💈 <b>{service}</b> · {master}\n📅 {day}\n\nВыберите время:",
        "no_times": "📅 {day}: свободного времени уже нет. Выберите другой день:",
        "btn_back": "⬅️ Назад",
        "day_today": "Сегодня",
        "day_tomorrow": "Завтра",
        "card": "📝 <b>Проверьте, пожалуйста:</b>\n\n💈 {service}\n👤 Мастер: {master}\n"
                "📅 {day} в {time}\n⏱ {duration} мин · 💰 {price}",
        "btn_confirm": "✅ Подтвердить",
        "btn_add_addon": "➕ {title} (+{duration} мин, +{price})",
        "btn_other_time": "⬅️ Другое время",
        "btn_no_change": "✖️ Нет, изменить",
        "ask_phone": "Осталось указать номер телефона, чтобы мастер мог с вами связаться.\n\n"
                     "Нажмите кнопку <b>«📱 Поделиться номером»</b> ниже или напишите номер сообщением.",
        "btn_share_phone": "📱 Поделиться номером",
        "btn_cancel": "Отмена",
        "bad_phone": "Не похоже на номер телефона 🤔\nНажмите кнопку «📱 Поделиться номером» "
                     "или напишите номер с кодом страны, например +380501234567.",
        "phone_saved": "Спасибо, номер сохранён 👍",
        "booking_aborted": "Хорошо, запись не создана. Если передумаете — «📅 Записаться».",
        "booked": "✅ <b>Готово, вы записаны!</b>\n\n💈 {service}\n👤 {master}\n📅 {day} в {time}\n💰 {price}{address}\n\n"
                  "Напомню заранее. Перенести или отменить — в разделе «🗓 Мои записи».",
        "booked_address": "\n📍 {address}",
        "prepay_block": "\n\n💳 <b>Чтобы закрепить запись — предоплата {amount}</b>\nКарта: <code>{card}</code>{recipient}\nОплатите до <b>{deadline}</b>, иначе запись автоматически отменится. Предоплата входит в стоимость услуги.\n\nПосле оплаты нажмите «✅ Я оплатил(а)» или пришлите сюда скрин 👇",
        "prepay_recipient": "\nПолучатель: {recipient}",
        "btn_prepay_done": "✅ Я оплатил(а)",
        "btn_prepay_done_item": "✅ Я оплатил(а) {short}",
        "prepay_claimed_client": "Спасибо! 🙏 Администратор проверит оплату и подтвердит запись — сообщим здесь.",
        "prepay_screenshot_client": "Спасибо, скрин получили! 🙏 Администратор проверит оплату и подтвердит запись — сообщим здесь.",
        "prepay_photo_ask": "📸 Это скрин оплаты предоплаты?",
        "btn_photo_is_payment": "✅ Да, это оплата",
        "btn_photo_other": "Нет, другой вопрос",
        "prepay_already_paid": "Предоплата уже подтверждена ✅",
        "prepay_paid_client": "✅ <b>Предоплата получена — запись подтверждена!</b>\n💈 {service} · {master}\n📅 {day} в {time}\n\nЖдём вас 💛",
        "client_cancelled_unpaid": "😔 К сожалению, ваша запись отменена: предоплата не получена вовремя.\n💈 {service} · {master}\n📅 {day} в {time}\n\nЕсли ещё актуально — запишитесь снова, будем рады 💛",
        "my_prepay_waiting": "\n💳 Ожидаем предоплату {amount} до {deadline}",
        "my_prepay_claimed": "\n💳 Проверяем вашу оплату ⏳",
        "my_prepay_paid": "\n💳 Предоплата получена ✅",
        "already_booked": "✅ Вы уже записаны на это время.",
        "slot_taken": "Ой, это время только что заняли 😕 Выберите, пожалуйста, другое:",
        "week_limit": "На эту неделю у вас уже максимум записей — {limit} 🙏\nВыберите другую неделю или перенесите одну из имеющихся записей.",
        "too_many_active": "Активных записей у вас уже {count} — это максимум. "
                           "Перенесите или отмените одну в разделе «🗓 Мои записи».",
        "booking_error": "Не удалось создать запись 😕 Попробуйте ещё раз или напишите нам.",
        "proposal_declined": "Хорошо 🙂 Напишите, что изменить — подберу другой вариант.",
        "my_none": "У вас пока нет запланированных визитов 🙂\nСамое время это исправить — выберите удобное время 👇",
        "my_header": "✨ <b>Ваши записи</b> ✨",
        "my_item": "\n\n📅 <b>{day} в {time}</b>\n✂️ {service}\n💈 Мастер: {master}",
        "my_footer": "\n\n💛 Мы уже ждём вас! Приходите на пару минут раньше — успеете выдохнуть "
                     "и настроиться на новый образ ✨\n\nЕсли планы изменились — перенесите или отмените запись "
                     "кнопками ниже 👇",
        "btn_resched_item": "🔁 Перенести {short}",
        "btn_cancel_item": "❌ Отменить {short}",
        "cancel_ask": "Отменить запись?\n\n💈 {service} · {master}\n📅 {day} в {time}",
        "btn_yes_cancel": "Да, отменить",
        "btn_no": "Нет",
        "cancel_kept": "Хорошо, запись остаётся ✅",
        "cancelled": "Запись отменена.\nБудем рады видеть вас в другой раз! Чтобы записаться снова — «📅 Записаться».",
        "cancel_too_late": "До визита меньше {hours} ч, поэтому отменить онлайн уже нельзя. "
                           "Позвоните нам, пожалуйста{phone}.",
        "cancel_too_late_phone": ": {phone}",
        "booking_inactive": "Эта запись уже неактивна.",
        "resched_choose_day": "🔁 <b>Перенос</b>\n💈 {service} · {master}\nСейчас: {day} в {time}\n\nВыберите новый день:",
        "resched_choose_time": "🔁 <b>Перенос</b>\n💈 {service} · {master}\n📅 {day}\n\nВыберите новое время:",
        "resched_card": "🔁 <b>Перенести запись?</b>\n\n💈 {service} · {master}\nБыло: {old}\nСтанет: <b>{new}</b>",
        "btn_confirm_resched": "✅ Перенести",
        "rescheduled": "✅ Запись перенесена.\n\n💈 {service} · {master}\n📅 <b>{day} в {time}</b>",
        "resched_none": "На ближайшие {days} дн. свободного времени нет 😕 Напишите нам — что-нибудь придумаем.",
        "prices_header": "💈 <b>{name}</b>\n✨ <b>УСЛУГИ И ЦЕНЫ</b> ✨\n<i>Выбирайте, что по душе, — записаться можно сразу, кнопкой внизу 👇</i>",
        "price_group": "\n\n━━━━━━━━━━━━\n<b>{group}</b>",
        "price_item": "\n\n<b>{title}</b> — {price}\n⏱ {duration} мин",
        "price_desc": "\n{description}",
        "prices_addons_header": "\n\n➕ <b>Можно добавить к стрижке</b> (кнопкой при записи)",
        "price_addon_item": "\n{title} — +{price}, +{duration} мин",
        "contacts_header": "📍 <b>{name}</b>",
        "contacts_address": "\n\n🏠 {address}",
        "contacts_phone": "\n📞 {phone}",
        "contacts_hours": "\n\n🕒 <b>График работы</b>\n{hours}",
        "contacts_directions": "\n\n🚗 {directions}",
        "contacts_payment": "\n💳 {payment}",
        "contacts_prepay": "\n💳 Предоплата {amount} — реквизиты пришлём сразу после записи (оплатить в течение {hours} ч).",
        "contacts_masters_header": "\n\n━━━━━━━━━━━━\n👥 <b>Наши мастера</b>",
        "contacts_master": "\n\n💈 <b>{name}</b>{about}\n🗓 {schedule}",
        "contacts_master_about": "\n<i>{about}</i>",
        "btn_map": "🗺 Открыть на карте",
        "day_off": "выходной",
        "reminder": "⏰ <b>Напоминание о визите</b>\n\n📅 {day} в {time}\n💈 {service} · {master}{address}",
        "btn_will_come": "✅ Приду",
        "btn_resched": "🔁 Перенести",
        "btn_cancel_booking": "❌ Отменить",
        "will_come_ok": "\n\n✅ Отлично, ждём!",
        "nudge": "Привет, {name}! 👋\nПрошло уже {weeks} нед. с вашего последнего визита ({service}). "
                 "Записать вас снова?",
        "btn_book_again": "📅 Записаться",
        "btn_no_nudges": "🔕 Не напоминать",
        "nudges_off": "Хорошо, больше не буду напоминать 🙂",
        "ai_off": "Выберите действие в меню 👇 — так будет быстрее всего.",
        "ai_error": "Извините, сейчас не могу ответить 😔\nВоспользуйтесь кнопками меню 👇 или попробуйте чуть позже.",
        "ai_refusal": "Извините, с этим я не помогу 🙂 Могу записать вас на услугу или передать вопрос администратору.",
        "rate_limited": "Слишком много сообщений за короткое время 🙈 Воспользуйтесь кнопками меню 👇 или напишите чуть позже.",
        "handoff_client": "Передал ваш вопрос администратору — он ответит здесь, в этом чате 🙌",
        "handoff_no_admin": "С этим вопросом лучше обратиться напрямую к администратору{phone} 🙏",
        "media_received": "Получил 👍 Передаю администратору — он ответит здесь, в этом чате.",
        "voice_unsupported": "Голосовые я пока не слушаю 🙈 Напишите, пожалуйста, текстом.",
        "unsupported": "Я понимаю только текстовые сообщения 🙂",
        "meta_choose_lang": "🌐 Выберите язык:",
        "btn_language": "🌐 Язык",
        "paused_ack": "Спасибо за сообщение! Администратор ответит в ближайшее время.",
        "admin_title": "Администратор",
        "admin_reply_to_client": "👤 <b>{title}:</b>\n{text}",
        "alert_expired": "Эта кнопка уже неактуальна. Начните, пожалуйста, заново.",
        "alert_no_access": "Нет доступа",
        "unknown_command": "Не знаю такой команды 🤔 Выберите действие в меню 👇",
        "myid": "Ваш Telegram ID: <code>{id}</code>",
        "state_cleared": "Отменено.",
        "admin_help": "🛠 <b>Панель управления · {name}</b>\n\n"
                      "/book — записать клиента (звонок, визит)\n"
                      "/today — записи на сегодня\n"
                      "/tomorrow — записи на завтра\n"
                      "/day 30.10 — записи на любую дату\n"
                      "/week — записи на 7 дней\n"
                      "/all — все будущие записи\n"
                      "/find — поиск клиента (имя, @username или номер)\n"
                      "/stats — статистика и выручка за 30 дней (/stats 7 — за 7)\n"
                      "/export — выгрузить записи в Excel\n"
                      "/block — закрыть время (выходной, отпуск, запись по телефону)\n"
                      "/blocks — список закрытого времени\n"
                      "/masters — мастера в боте: пригласить, отключить\n"
                      "/prices — изменить цены на услуги\n"
                      "/pause — выключить AI: все сообщения клиентов идут вам\n"
                      "/resume — включить AI обратно\n"
                      "/reload — перечитать настройки из файла\n"
                      "/myid — ваш Telegram ID\n\n"
                      "💬 Чтобы ответить клиенту, отвечайте (свайп влево → «Ответить») "
                      "на его сообщение, которое переслал бот.\n\n"
                      "AI-ответы: {ai_status}",
        "ai_status_on": "✅ включены",
        "ai_status_paused": "⏸ на паузе (/resume)",
        "ai_status_nokey": "⚪️ выключены (нет ключа API в settings.toml)",
        "ai_status_disabled": "⚪️ выключены в настройках заведения",
        "adm_new_booking": "🆕 <b>Новая запись</b>{via}\n\n👤 {client}\n💈 {service} · {master}\n📅 {day} в {time}\n💰 {price}",
        "adm_via_ai": " · через AI-чат 🤖",
        "adm_via_web": " · через онлайн-запись 📲",
        "adm_cancelled": "❌ <b>Отмена</b>\n\n👤 {client}\n💈 {service} · {master}\n📅 {day} в {time}",
        "adm_rescheduled": "🔁 <b>Перенос</b>\n\n👤 {client}\n💈 {service} · {master}\nБыло: {old}\nСтало: <b>{new}</b>",
        "adm_handoff": "🙋 <b>Нужен ваш ответ</b>\n\n👤 {client}\n❓ {reason}{summary}\n\n"
                       "<b>Последние сообщения:</b>\n{transcript}\n\n"
                       "↩️ Ответьте на это сообщение (свайп влево) — бот перешлёт ответ клиенту. "
                       "AI для этого клиента на паузе {hours} ч.",
        "adm_handoff_summary": "\n📝 {summary}",
        "adm_reason_media": "Клиент прислал фото или файл (возможно, оплата)",
        "adm_tr_client": "— Клиент: {text}",
        "adm_tr_bot": "— Бот: {text}",
        "adm_tr_empty": "(нет)",
        "btn_adm_reply": "✍️ Ответить",
        "btn_adm_resume": "▶️ Вернуть бота",
        "adm_client_msg": "💬 <b>{client}</b>:\n{text}",
        "adm_client_media": "💬 {client}",
        "adm_reply_prompt": "Напишите ответ для {client} одним сообщением (или /cancel):",
        "adm_reply_sent": "✅ Отправлено: {client}",
        "adm_reply_failed": "⚠️ Не удалось отправить — возможно, клиент заблокировал бота.",
        "adm_resumed": "▶️ AI снова отвечает: {client}",
        "adm_day_header": "📅 <b>{day}</b>{master} — записей: {count}",
        "adm_day_empty": "📅 <b>{day}</b>{master} — записей нет.",
        "adm_item": "\n\n<b>{n}. {start}–{end}</b> · {master}\n💈 {service}\n👤 {client}{flags}",
        "adm_list_day": "\n\n📅 <b>{day}</b> — записей: {count}",
        "adm_list_hint": "\n\nНажмите запись, чтобы перенести, отменить или отметить оплату 👇",
        "adm_day_master": " · {name}",
        "adm_day_hint": "\n\nНажмите запись, чтобы перенести, отменить, отметить неявку или оплату 👇",
        "adm_day_pick": "📅 Выберите день:",
        "adm_day_usage": "📅 Укажите дату, например: /day 30.10 или /day завтра",
        "btn_adm_booking_item": "⚙️ {n} · {when} · {client}",
        "btn_day_prev": "◀️ {day}",
        "btn_day_next": "{day} ▶️",
        "btn_day_pick": "📅 Дата",
        "btn_master_all": "👥 Все",
        "btn_master_selected": "✅ {name}",
        "adm_card": "📋 <b>Запись #{id}</b>\n\n{summary}\n💰 {price}",
        "adm_card_source_buttons": "\n📱 Записался сам",
        "adm_card_source_ai": "\n🤖 Записался через AI-чат",
        "adm_card_source_admin": "\n📞 Записал администратор",
        "adm_card_noshow": "\n🚫 Клиент не пришёл",
        "adm_card_cancelled": "\n❌ Отменено — {by}",
        "adm_card_confirmed": "\n✅ Клиент подтвердил, что придёт",
        "btn_adm_resched": "🔁 Перенести",
        "btn_adm_cancel_short": "🗑 Отменить",
        "btn_adm_noshow": "🚫 Не пришёл",
        "btn_adm_client": "👤 Клиент",
        "btn_adm_write": "✉️ Написать",
        "adm_resched_day": "🔁 <b>Перенос записи #{id}</b>\n\n{summary}\n\nВыберите новый день 👇",
        "adm_resched_none": "🔁 Свободных дней для переноса нет.\n\n{summary}",
        "adm_resched_time": "🔁 <b>#{id}</b> · {service} · {master}\n📅 {day} — выберите время 👇",
        "adm_resched_confirm": "🔁 <b>Перенести запись?</b>\n\n💈 {service}\n👤 {client}\nБыло: {old}\nСтанет: <b>{new}</b>\n\n{who}",
        "btn_adm_resched_yes": "✅ Перенести",
        "adm_resched_same": "Это то же время — ничего не изменено.",
        "btn_adm_change_master": "👤 Сменить мастера",
        "btn_adm_master_pick": "💈 {name}",
        "adm_change_master": "👤 <b>Другой мастер для записи #{id}</b>\n\n{summary}\n\nВыберите мастера 👇",
        "adm_change_master_none": "👤 Услугу «{service}» больше никто из мастеров не делает.",
        "adm_new_master": "👤 Новый мастер: <b>{master}</b>",
        "adm_master_busy": "👤 Новый мастер: <b>{master}</b>\n⚠️ В {time} этот мастер занят — выберите другой день.",
        "adm_resched_done": "🔁 <b>Перенесено</b>\n\n{summary}\n\nБыло: {old}\n{who}",
        "adm_resched_notified": "Клиент уведомлён.",
        "adm_resched_offline": "Клиента нет в Telegram — сообщите ему сами.",
        "adm_find_usage": "🔎 Поиск клиента: /find Иван, /find @username или /find 0671 (часть номера)",
        "adm_find_none": "🔎 По «{q}» никого не найдено.",
        "adm_find_many": "🔎 Найдено: {count}. Выберите клиента 👇",
        "btn_adm_client_item": "👤 {label}",
        "adm_client_card": "👤 <b>{name}</b>\n{contacts}\n{tg}\n\n📊 Визитов: {done} · неявок: {noshow} · отмен: {cancelled}\n💰 Всего: {spent}{last}{upcoming}{notes}",
        "adm_client_tg_yes": "✉️ Есть в боте",
        "adm_client_tg_no": "📵 Нет в Telegram",
        "adm_client_last": "\n🗓 Последний визит: {day} · {service}",
        "adm_client_upcoming": "\n\n<b>Будущие записи:</b>{items}",
        "adm_client_upcoming_item": "\n• {when} · {service}",
        "adm_client_notes": "\n\n📝 {notes}",
        "btn_adm_client_booking": "⚙️ {when} · {service}",
        "btn_adm_client_book": "📞 Записать",
        "adm_export_usage": "📊 /export — записи за 30 дней и все будущие; /export 90 — за 90 дней.",
        "adm_export_empty": "За этот период записей нет.",
        "adm_export_caption": "📊 Записи с {start} (и все будущие): {count}",
        "adm_export_headers": "Дата|Время|Конец|Мастер|Услуга|Цена|Статус|Клиент|Телефон|Telegram|Источник|Предоплата|Комментарий|Создано",
        "adm_export_sheet": "Записи",
        "adm_export_statuses": "запланировано|состоялся|не пришёл|отменено",
        "adm_export_sources": "сам|AI-чат|админ",
        "adm_export_prepay": "ожидаем|говорит, что оплатил|оплачено",
        "adm_master_revenue": "\n   {name}: {count} · {revenue}",
        "adm_evening_report": "🌙 <b>Итоги дня · {day}</b>\n\n✅ Состоялось: {done} · 🚫 неявок: {noshow} · ❌ отменено: {cancelled}\n💰 Выручка: <b>{revenue}</b>{by_master}\n\n📅 Завтра записей: {tomorrow}",
        "client_rescheduled_by_admin": "🔁 Администратор перенёс вашу запись:\n💈 {service} · {master}\nБыло: {old}\nСтало: <b>{new}</b>\n\nЕсли время не подходит — измените в «🗓 Мои записи» или напишите нам.",
        "adm_booking_summary": "<b>{day}, {start}–{end}</b> · {master}\n💈 {service}\n👤 {client}",
        "adm_noshow_done": "🚫 {client} ({time}) — не пришёл",
        "adm_cancel_ask": "Отменить эту запись?\n\n{booking}\n\n{who}",
        "adm_cancel_notify": "Клиент получит сообщение в Telegram.",
        "adm_cancel_offline": "Клиента нет в Telegram — сообщите ему сами.",
        "adm_cancelled_done": "🗑 <b>Отменено</b>\n\n{booking}\n\nКлиент уведомлён.",
        "adm_cancelled_done_offline": "🗑 <b>Отменено</b>\n\n{booking}\n\nКлиента нет в Telegram — сообщите ему сами.",
        "adm_cancelled_header": "\n\n➖➖➖\n❌ <b>Отменённые</b> — {count}",
        "adm_cancelled_item": "\n{day} {start} · {master} · {service} · {client} — {by}",
        "adm_cancelled_by_client": "отменил клиент",
        "adm_cancelled_by_admin": "отменил админ",
        "adm_new_booking_prepay": "\n💳 Ждём предоплату {amount} до {deadline}",
        "adm_prepay_claim_note": "💳 <b>Клиент сообщает об оплате</b>\n\n{booking}\n\nПроверьте поступление {amount} и подтвердите 👇",
        "adm_prepay_screenshot": "💳 <b>Клиент прислал подтверждение оплаты</b> (скрин выше)\n\n{booking}\n\nПроверьте поступление {amount} и подтвердите 👇",
        "adm_prepay_overdue": "⏰ <b>Оплата ещё не подтверждена</b>\nКлиент сообщил об оплате, но прошло уже {hours} ч. Проверьте, пожалуйста: такая запись автоматически не отменяется.\n\n{booking}",
        "btn_adm_prepay_ok": "✅ Оплата получена",
        "btn_adm_cancel_booking": "🗑 Отменить запись",
        "adm_prepay_ok_done": "✅ <b>Предоплата подтверждена</b>, клиент уведомлён.\n\n{booking}",
        "adm_prepay_ok_alert": "✅ Оплата подтверждена",
        "adm_prepay_already": "Предоплата уже подтверждена.",
        "adm_prepay_waiting": "\n💳 ⏳ ждём предоплату",
        "adm_prepay_claimed": "\n💳 ❔ клиент говорит, что оплатил — проверьте",
        "adm_prepay_paid": "\n💳 ✅ предоплата получена",
        "adm_cancelled_by_unpaid": "не оплачено",
        "adm_cancelled_unpaid": "⏰ <b>Запись отменена автоматически</b> — предоплата не подтверждена за {hours} ч.\n\n{booking}",
        "btn_adm_clear_cancelled": "🧹 Убрать отменённые ({count})",
        "adm_clear_ask": "Убрать отменённые записи из списка ({count})?\nВ /all их больше не будет, а в статистике они останутся.",
        "btn_adm_yes_clear": "Да, убрать",
        "adm_cleared_done": "🧹 Убрано отменённых записей: {count}. Обновлённый список — /all",
        "btn_adm_yes_cancel": "Да, отменить",
        "client_cancelled_by_admin": "К сожалению, ваша запись отменена администратором:\n💈 {service} · {master}\n"
                                     "📅 {day} в {time}\n\nВыберите другое время — «📅 Записаться» — или напишите нам.",
        "adm_week_header": "🗓 <b>Записи на 7 дней</b>",
        "adm_week_empty": "\n\nЗаписей нет.",
        "adm_week_more": "\n\n➕ Позже ещё записей: {count} — /all",
        "adm_all_header": "🗓 <b>Все будущие записи</b>",
        "adm_note_line": "\n📝 {note}",
        "adm_via_admin": " · записал администратор 📞",
        "btn_adm_book_confirm": "✅ Записать",
        "btn_adm_book_cancel": "✖️ Отмена",
        "adm_book_service": "📞 <b>Запись клиента</b>\nВыберите услугу:",
        "adm_book_group": "📞 <b>Запись клиента</b>\nВыберите категорию — дальше услуга, мастер, день и время 👇",
        "adm_book_in_group": "📞 <b>{group}</b>\nВыберите услугу — дальше мастер, день и время 👇",
        "adm_book_master": "📞 {service}\nВыберите мастера:",
        "adm_book_day": "📞 {service} · {master}\nВыберите день:",
        "adm_book_time": "📞 {service} · {master} · {day}\nВыберите время:",
        "adm_book_no_days": "У мастера {master} нет свободных дней на «{service}». Выберите другого мастера:",
        "adm_book_client_prompt": "📞 {service} · {master} · {day} в {time}\n\n"
                                  "Отправьте данные клиента одним сообщением: <b>имя</b> и <b>телефон</b>, "
                                  "с новой строки — комментарий (необязательно). Например:\n"
                                  "<code>Елена +380671234567\nхочет короче, чем в прошлый раз</code>\n\n"
                                  "Или поделитесь контактом клиента из Telegram (📎 → Контакт).\n/cancel — отменить.",
        "adm_book_need_name": "Не вижу имени клиента. Отправьте ещё раз: имя, телефон, с новой строки — комментарий.",
        "adm_book_card": "📞 <b>Проверьте запись</b>\n\n👤 {client}\n💈 {service} · {master}\n📅 {day} в {time}\n"
                         "💰 {price}{note}\n\n{hint}\n\nЧтобы изменить данные — просто отправьте их ещё раз.",
        "adm_book_hint_tg": "✉️ Клиент уже есть в боте ({client}) — получит сообщение и напоминания.",
        "adm_book_hint_known": "🗂 Клиент уже есть в базе ({client}), но не в Telegram — сообщений не получит.",
        "adm_book_hint_offline": "📵 Новый клиент без Telegram — сообщений и напоминаний не получит.",
        "adm_book_duplicate": "У клиента уже есть запись на это время (#{id}).",
        "adm_book_done": "✅ <b>Записано</b> <code>#{id}</code>\n👤 {client}\n💈 {service} · {master}\n"
                         "📅 {day} в {time}{notified}",
        "adm_book_notified": "\n\n✉️ Клиенту отправлено сообщение в Telegram.",
        "adm_book_not_notified": "\n\n📵 Клиент не получил сообщение (нет в Telegram) — при необходимости позвоните.",
        "adm_book_aborted": "Запись не создана.",
        "client_booked_by_admin": "📞 Администратор записал вас:\n💈 {service} · {master}\n📅 {day} в {time}\n💰 {price}\n\n"
                                  "Перенести или отменить — «🗓 Мои записи».",
        "adm_block_usage": "🔒 <b>Закрыть время</b>\n\nФормат: <code>/block мастер дата [время] [комментарий]</code>\n\n"
                           "Примеры:\n<code>/block {example} 30.10</code> — весь день\n"
                           "<code>/block {example} 30.10 14:00-16:00 запись по телефону</code>\n"
                           "<code>/block all 31.12</code> — выходной для всех\n\nМастера: {masters}",
        "adm_block_bad": "Не понял команду 🤔\n\n{usage}",
        "adm_block_done": "🔒 Закрыто: {master}, {day} {range}{note}",
        "adm_block_conflicts": "\n\n⚠️ На это время уже есть записи — отмените их (/today, /tomorrow) или предупредите клиентов:{lines}",
        "adm_all_masters": "все мастера",
        "adm_whole_day": "(весь день)",
        "adm_blocks_header": "🔒 <b>Закрытое время</b> (нажмите, чтобы удалить):",
        "adm_blocks_empty": "Закрытого времени нет.",
        "btn_adm_block_item": "🗑 {master} · {day} {range}",
        "adm_block_deleted": "🔓 Удалено. Это время снова доступно для записи.",
        "adm_paused": "⏸ AI выключен. Все сообщения клиентов будут пересылаться вам; кнопки записи работают.\n"
                      "Включить: /resume",
        "adm_resumed_all": "▶️ AI снова отвечает клиентам.",
        "adm_reloaded": "🔄 Настройки обновлены: услуг — {services}, мастеров — {masters}.",
        "adm_reload_failed": "❌ В файле настроек ошибка, оставляю прежние:\n<code>{error}</code>",
        "adm_reload_token": "\n⚠️ Токен бота изменён — перезапустите бота, чтобы это применить.",
        "adm_digest": "☀️ <b>Доброе утро!</b>\n\n{body}",
        "adm_ai_alert": "⚠️ <b>AI не отвечает</b> ({name})\n<code>{error}</code>\n\n"
                        "Бот работает на кнопках. Проверьте ключ API и баланс на console.anthropic.com.",
        "adm_budget_alert": "⚠️ Дневной лимит AI исчерпан ({name}). До конца дня бот отвечает только кнопками. "
                            "Лимит меняется в settings.toml (daily_token_limit).",
        "adm_stats": "📊 <b>Статистика за {days} дней</b>\n\n"
                     "<b>Записи</b>\n"
                     "• создано: {created} (AI-чат: {by_ai}, кнопки: {by_buttons}, админ: {by_admin})\n"
                     "• ночью (22:00–08:00): {night}\n"
                     "• состоялось: {done} · не пришли: {noshow} · отменено: {cancelled}\n"
                     "• впереди: {upcoming}\n\n"
                     "<b>Выручка</b>\n"
                     "• {revenue} · средний чек {avg_check}{by_master}\n"
                     "• ожидается с будущих записей: {expected}\n\n"
                     "<b>Диалоги</b>\n"
                     "• клиентов писали: {clients}\n"
                     "• передано вам: {handoffs}\n"
                     "• бот справился сам: {auto_rate}\n\n"
                     "<b>Напоминания</b>\n"
                     "• отправлено: {reminders} · «Приду»: {confirmed}\n\n"
                     "<b>AI</b>\n"
                     "• сообщений обработано: {ai_calls} · токенов: {tokens}\n"
                     "• примерная стоимость: ${cost}",
        "adm_client_noname": "Клиент",
        "cmd_start": "Главное меню",
        "cmd_admin": "Панель владельца",
        "cmd_today": "Записи на сегодня",
        "cmd_tomorrow": "Записи на завтра",
        "cmd_book": "Записать клиента",
        "cmd_day": "Записи на дату",
        "cmd_find": "Поиск клиента",
        "cmd_export": "Выгрузить в Excel",
        "cmd_week": "Записи на 7 дней",
        "cmd_all": "Все будущие записи",
        "cmd_stats": "Статистика",
        "cmd_block": "Закрыть время",
        "cmd_blocks": "Закрытое время",
        "cmd_pause": "Выключить AI",
        "cmd_resume": "Включить AI",
        "cmd_reload": "Обновить настройки",
        "cmd_myid": "Мой Telegram ID",
        "cmd_masters": "Мастера в боте",
        "cmd_prices": "Изменить цены",
        "adm_prices": "💰 <b>Цены на услуги</b>\nНажмите услугу, чтобы изменить цену 👇",
        "adm_prices_changed": "\n\n✏️ — цена изменена здесь, в боте (в файле настроек старая).",
        "adm_price_ask": "💰 <b>{title}</b>\nСейчас: <b>{price}</b>\n\nНапишите новую цену числом, например 650.",
        "adm_price_file": "\nВ файле настроек: {price}.",
        "btn_adm_price_reset": "↩️ Вернуть {price}",
        "adm_price_bad": "Не похоже на цену 🤔 Напишите только число, например 650. Отменить — /cancel",
        "adm_price_done": "✅ <b>{title}</b>: {old} → <b>{new}</b>\nНовую цену уже видят клиенты и AI. "
                          "Записи, сделанные раньше, остаются по старой цене.",
        "adm_price_combos": "\nЦены комбинаций с дополнениями пересчитаны.",
        "adm_price_changed_note": "💰 {admin} изменил цену: <b>{title}</b> {old} → <b>{new}</b>",
        "cmd_my": "Мой день",
        "cmd_myweek": "Моя неделя",
        "cmd_off": "Закрыть время",
        "cmd_offs": "Моё закрытое время",
        # Мастера: админ
        "adm_masters": "✂️ <b>Мастера в боте</b>\n\nПодключённый мастер видит свои записи, сам закрывает время "
                       "и получает уведомления о своих клиентах.\n{items}",
        "adm_masters_on": "\n✅ <b>{name}</b> — {who}",
        "adm_masters_off": "\n⚪️ <b>{name}</b> — не подключён",
        "btn_adm_master_invite": "🔗 Пригласить: {name}",
        "btn_adm_master_unlink": "✖️ Отключить: {name}",
        "btn_adm_yes_unlink": "✖️ Да, отключить",
        "btn_adm_open": "📋 Открыть запись",
        "adm_master_invite": "🔗 Ссылка для мастера <b>{name}</b>:\n\n{link}\n\nПерешлите её мастеру — "
                             "пусть откроет и нажмёт «Старт». Ссылка одноразовая, действует {hours} ч.",
        "adm_master_no_username": "Не удалось получить адрес бота. Попробуйте ещё раз через минуту.",
        "adm_master_unlink_ask": "Отключить мастера <b>{name}</b> от бота? Он больше не будет видеть записи "
                                 "и получать уведомления.",
        "adm_master_unlinked": "✖️ Мастер {name} отключён от бота.",
        "adm_master_joined": "✂️ Мастер <b>{name}</b> подключился к боту ({who}).",
        "adm_master_noshow": "🚫 <b>Мастер {master} отметил неявку</b>\n\n{booking}",
        "adm_master_off": "🌴 Мастер <b>{master}</b> закрыл время: {day} {range}",
        "adm_master_off_conflicts": "\n\n⚠️ <b>На это время уже есть записи</b> — договоритесь с клиентами "
                                    "(перенести или отменить):{lines}",
        "adm_master_on": "🔓 Мастер <b>{master}</b> открыл время: {day} {range}",
        # Мастера: сам мастер
        "mst_invite_bad": "Эта ссылка недействительна или уже использована. Попросите администратора прислать новую.",
        "mst_joined": "✅ <b>Вы подключены как мастер «{name}».</b>\n\n",
        "mst_start": "✂️ <b>{name}</b>, вы мастер в боте «{shop}».\n\n"
                     "📅 <b>Мой день</b> — ваши записи, листайте дни ◀️ ▶️\n"
                     "🗓 <b>Моя неделя</b> — записи на 7 дней\n"
                     "🌴 <b>Закрыть время</b> — выходной, перерыв, личные дела\n"
                     "🔒 <b>Моё закрытое время</b> — посмотреть и открыть обратно\n\n"
                     "Бот сообщит о новых записях, отменах и переносах, утром пришлёт расписание, "
                     "а перед каждым клиентом — напомнит.",
        "mst_unlinked": "Вы отключены от бота как мастер. Записаться как клиент можно в меню 👇",
        "btn_mst_day": "📅 Мой день",
        "btn_mst_week": "🗓 Моя неделя",
        "btn_mst_off": "🌴 Закрыть время",
        "btn_mst_offs": "🔒 Моё закрытое время",
        "btn_mst_to_day": "⬅️ К дню",
        "mst_day_hint": "\n\nНажмите запись, чтобы открыть карточку 👇",
        "mst_day_off": "\n\n🌴 По графику у вас выходной.",
        "mst_day_blocks": "\n\n🔒 Закрыто: {ranges}",
        "mst_week_header": "🗓 <b>Ваши записи на 7 дней</b>",
        "mst_off_day": "🌴 <b>Закрыть время</b>\n\nВыберите день:",
        "mst_off_range": "🌴 <b>{day}</b> · ваш график {hours}\n\nЗакрыть весь день или с какого часа?",
        "mst_off_whole_only": "🌴 <b>{day}</b> · {hours}\n\nЗакрыть весь день?",
        "mst_off_no_work": "по графику выходной",
        "mst_off_end": "🌴 <b>{day}</b>, с {start}\n\nДо какого часа?",
        "btn_mst_whole_day": "🌴 Весь день",
        "btn_mst_off_yes": "✅ Закрыть",
        "mst_off_confirm": "Закрыть <b>{day} {range}</b>?\nКлиенты не смогут записаться на это время.{conflicts}",
        "mst_off_conflicts": "\n\n⚠️ На это время уже есть записи — администратор получит уведомление, "
                             "чтобы договориться с клиентами:{lines}",
        "mst_off_done": "🔒 Закрыто: <b>{day} {range}</b>. Клиенты не смогут записаться на это время.",
        "mst_off_done_conflicts": "\n\n⚠️ Записи на это время остались — администратор уведомлён:{lines}",
        "mst_offs_header": "🔒 <b>Ваше закрытое время</b>\nНажмите, чтобы открыть обратно:",
        "mst_offs_header_none": "🔒 <b>Ваше закрытое время</b>",
        "mst_offs_admin": "\n\nЗакрыл администратор (изменить может только он):{lines}",
        "mst_offs_empty": "🔒 Закрытого времени нет. Чтобы закрыть — «🌴 Закрыть время».",
        "btn_mst_block_item": "🗑 {label}",
        "alert_mst_opened": "Время снова открыто для записи",
        "mst_new": "🆕 <b>Новая запись к вам</b>\n\n📅 {day} в {time}\n💈 {service}\n👤 {client}",
        "mst_cancelled": "❌ <b>Запись отменена</b>\n\n📅 {day} в {time}\n💈 {service}\n👤 {client}",
        "mst_moved": "🔁 <b>Запись перешла к другому мастеру</b>\n\n📅 {day} в {time}\n💈 {service}\n👤 {client}",
        "mst_rescheduled": "🔁 <b>Запись перенесена</b>\n\n💈 {service}\n👤 {client}\nБыло: {old}\nСтало: <b>{new}</b>",
        "mst_digest": "☀️ <b>Доброе утро, {name}!</b>\n\n{body}",
        "mst_heads_up": "⏰ <b>В {time}</b> (через {min} мин) — {client}\n💈 {service}",
    },
    # ------------------------------------------------------------------ EN
    "en": {
        "btn_book": "📅 Book",
        "btn_my": "🗓 My bookings",
        "btn_prices": "💈 Services & prices",
        "btn_contacts": "📍 Contacts",
        "btn_webapp": "📅 Book online",
        "webapp_invite": "Pick a service, a stylist and a time that suits you in the booking window 👇",
        "start": "Hi! 👋 I'm the booking assistant of <b>{name}</b>.\n\n"
                 "I can book, reschedule or cancel your visit and answer your questions.\n\n"
                 "Pick an option in the menu 👇 or just type your question.",
        "start_no_ai": "Hi! 👋 I'm the booking assistant of <b>{name}</b>.\n\n"
                       "I can book, reschedule or cancel your visit.\nPick an option in the menu 👇",
        "start_admin_hint": "\n\n🛠 You are an admin of this bot. Control panel: /admin",
        "choose_service": "Choose a service:",
        "choose_group": "✨ Choose a category — then we'll find a barber and a time that suits you 👇",
        "choose_service_in_group": "<b>{group}</b>\nChoose a service — then we'll find a barber and a time that suits you 👇",
        "btn_service": "{title} · {price}",
        "choose_master": "💈 <b>{service}</b>\n💰 {price} · ⏱ {duration} min{description}\n\nChoose a barber 👇",
        "master_service_desc": "\n<i>{description}</i>",
        "btn_any_master": "👥 Any barber",
        "any_master": "any barber",
        "choose_day": "💈 <b>{service}</b> · {master}\n\nChoose a day:",
        "no_days": "💈 <b>{service}</b> · {master}\n\nSorry, there are no free slots in the next {days} days 😕\n"
                   "Message us and we'll try to find a solution.",
        "choose_time": "💈 <b>{service}</b> · {master}\n📅 {day}\n\nChoose a time:",
        "no_times": "📅 {day}: no free slots left. Please choose another day:",
        "btn_back": "⬅️ Back",
        "day_today": "Today",
        "day_tomorrow": "Tomorrow",
        "card": "📝 <b>Please check:</b>\n\n💈 {service}\n👤 Barber: {master}\n"
                "📅 {day} at {time}\n⏱ {duration} min · 💰 {price}",
        "btn_confirm": "✅ Confirm",
        "btn_add_addon": "➕ {title} (+{duration} min, +{price})",
        "btn_other_time": "⬅️ Other time",
        "btn_no_change": "✖️ No, change",
        "ask_phone": "One last thing — your phone number, so the barber can reach you.\n\n"
                     "Tap <b>«📱 Share phone number»</b> below or type your number.",
        "btn_share_phone": "📱 Share phone number",
        "btn_cancel": "Cancel",
        "bad_phone": "That doesn't look like a phone number 🤔\nTap «📱 Share phone number» "
                     "or type it with the country code, e.g. +36301234567.",
        "phone_saved": "Thanks, number saved 👍",
        "booking_aborted": "OK, no booking was made. If you change your mind — «📅 Book».",
        "booked": "✅ <b>Done, you're booked!</b>\n\n💈 {service}\n👤 {master}\n📅 {day} at {time}\n💰 {price}{address}\n\n"
                  "I'll remind you in advance. To reschedule or cancel — «🗓 My bookings».",
        "booked_address": "\n📍 {address}",
        "prepay_block": "\n\n💳 <b>To secure your booking — a {amount} prepayment</b>\nCard: <code>{card}</code>{recipient}\nPlease pay by <b>{deadline}</b>, otherwise the booking is cancelled automatically. The prepayment counts towards the price.\n\nAfter paying, tap «✅ I've paid» or send a screenshot here 👇",
        "prepay_recipient": "\nRecipient: {recipient}",
        "btn_prepay_done": "✅ I've paid",
        "btn_prepay_done_item": "✅ I've paid {short}",
        "prepay_claimed_client": "Thank you! 🙏 The admin will check the payment and confirm your booking — we'll let you know here.",
        "prepay_screenshot_client": "Thanks, got the screenshot! 🙏 The admin will check the payment and confirm your booking — we'll let you know here.",
        "prepay_photo_ask": "📸 Is this a screenshot of your prepayment?",
        "btn_photo_is_payment": "✅ Yes, it's the payment",
        "btn_photo_other": "No, something else",
        "prepay_already_paid": "The prepayment is already confirmed ✅",
        "prepay_paid_client": "✅ <b>Prepayment received — your booking is confirmed!</b>\n💈 {service} · {master}\n📅 {day} at {time}\n\nSee you soon 💛",
        "client_cancelled_unpaid": "😔 Sorry, your booking was cancelled: the prepayment didn't arrive in time.\n💈 {service} · {master}\n📅 {day} at {time}\n\nIf it still suits you, book again — we'd be glad to see you 💛",
        "my_prepay_waiting": "\n💳 Awaiting a {amount} prepayment by {deadline}",
        "my_prepay_claimed": "\n💳 Checking your payment ⏳",
        "my_prepay_paid": "\n💳 Prepayment received ✅",
        "already_booked": "✅ You are already booked for this time.",
        "slot_taken": "Oops, this time was just taken 😕 Please choose another one:",
        "week_limit": "You already have the maximum of {limit} bookings this week 🙏\nPick another week or reschedule one of your bookings.",
        "too_many_active": "You already have {count} active bookings — that's the maximum. "
                           "Reschedule or cancel one in «🗓 My bookings».",
        "booking_error": "Couldn't create the booking 😕 Please try again or message us.",
        "proposal_declined": "OK 🙂 Tell me what to change and I'll find another option.",
        "my_none": "No upcoming visits yet 🙂\nLet's fix that — pick a time that suits you 👇",
        "my_header": "✨ <b>Your bookings</b> ✨",
        "my_item": "\n\n📅 <b>{day} at {time}</b>\n✂️ {service}\n💈 Master: {master}",
        "my_footer": "\n\n💛 We're looking forward to seeing you! Come a few minutes early to relax "
                     "and get ready for your new look ✨\n\nIf your plans change, reschedule or cancel "
                     "with the buttons below 👇",
        "btn_resched_item": "🔁 Reschedule {short}",
        "btn_cancel_item": "❌ Cancel {short}",
        "cancel_ask": "Cancel this booking?\n\n💈 {service} · {master}\n📅 {day} at {time}",
        "btn_yes_cancel": "Yes, cancel",
        "btn_no": "No",
        "cancel_kept": "OK, the booking stays ✅",
        "cancelled": "Booking cancelled.\nHope to see you another time! To book again — «📅 Book».",
        "cancel_too_late": "Your visit is less than {hours} h away, so it can't be cancelled online. "
                           "Please call us{phone}.",
        "cancel_too_late_phone": ": {phone}",
        "booking_inactive": "This booking is no longer active.",
        "resched_choose_day": "🔁 <b>Reschedule</b>\n💈 {service} · {master}\nNow: {day} at {time}\n\nChoose a new day:",
        "resched_choose_time": "🔁 <b>Reschedule</b>\n💈 {service} · {master}\n📅 {day}\n\nChoose a new time:",
        "resched_card": "🔁 <b>Reschedule this booking?</b>\n\n💈 {service} · {master}\nWas: {old}\nNew: <b>{new}</b>",
        "btn_confirm_resched": "✅ Reschedule",
        "rescheduled": "✅ Booking rescheduled.\n\n💈 {service} · {master}\n📅 <b>{day} at {time}</b>",
        "resched_none": "No free slots in the next {days} days 😕 Message us and we'll figure something out.",
        "prices_header": "💈 <b>{name}</b>\n✨ <b>SERVICES &amp; PRICES</b> ✨\n<i>Pick what you like — you can book right away with the button below 👇</i>",
        "price_group": "\n\n━━━━━━━━━━━━\n<b>{group}</b>",
        "price_item": "\n\n<b>{title}</b> — {price}\n⏱ {duration} min",
        "price_desc": "\n{description}",
        "prices_addons_header": "\n\n➕ <b>Add-ons</b> (a button while booking)",
        "price_addon_item": "\n{title} — +{price}, +{duration} min",
        "contacts_header": "📍 <b>{name}</b>",
        "contacts_address": "\n\n🏠 {address}",
        "contacts_phone": "\n📞 {phone}",
        "contacts_hours": "\n\n🕒 <b>Opening hours</b>\n{hours}",
        "contacts_directions": "\n\n🚗 {directions}",
        "contacts_payment": "\n💳 {payment}",
        "contacts_prepay": "\n💳 Prepayment {amount} — we'll send the details right after booking (pay within {hours} h).",
        "contacts_masters_header": "\n\n━━━━━━━━━━━━\n👥 <b>Our masters</b>",
        "contacts_master": "\n\n💈 <b>{name}</b>{about}\n🗓 {schedule}",
        "contacts_master_about": "\n<i>{about}</i>",
        "btn_map": "🗺 Open map",
        "day_off": "closed",
        "reminder": "⏰ <b>Visit reminder</b>\n\n📅 {day} at {time}\n💈 {service} · {master}{address}",
        "btn_will_come": "✅ I'll be there",
        "btn_resched": "🔁 Reschedule",
        "btn_cancel_booking": "❌ Cancel",
        "will_come_ok": "\n\n✅ Great, see you!",
        "nudge": "Hi, {name}! 👋\nIt's been {weeks} weeks since your last visit ({service}). "
                 "Shall I book you again?",
        "btn_book_again": "📅 Book",
        "btn_no_nudges": "🔕 Don't remind me",
        "nudges_off": "OK, I won't remind you anymore 🙂",
        "ai_off": "Please pick an option in the menu 👇 — that's the fastest way.",
        "ai_error": "Sorry, I can't answer right now 😔\nPlease use the menu buttons 👇 or try again a bit later.",
        "ai_refusal": "Sorry, I can't help with that 🙂 I can book you a service or pass your question to the admin.",
        "rate_limited": "Too many messages in a short time 🙈 Please use the menu buttons 👇 or write a bit later.",
        "handoff_client": "I've passed your question to the admin — they'll reply right here in this chat 🙌",
        "handoff_no_admin": "For this question it's best to contact the admin directly{phone} 🙏",
        "media_received": "Got it 👍 Passing it to the admin — they'll reply right here in this chat.",
        "voice_unsupported": "I can't listen to voice messages yet 🙈 Please type your message.",
        "unsupported": "I only understand text messages 🙂",
        "meta_choose_lang": "🌐 Choose your language:",
        "btn_language": "🌐 Language",
        "paused_ack": "Thanks for your message! The admin will reply soon.",
        "admin_title": "Admin",
        "admin_reply_to_client": "👤 <b>{title}:</b>\n{text}",
        "alert_expired": "This button has expired. Please start again.",
        "alert_no_access": "No access",
        "unknown_command": "I don't know this command 🤔 Please pick an option in the menu 👇",
        "myid": "Your Telegram ID: <code>{id}</code>",
        "state_cleared": "Cancelled.",
        "admin_help": "🛠 <b>Control panel · {name}</b>\n\n"
                      "/book — book a client (call, walk-in)\n"
                      "/today — today's bookings\n"
                      "/tomorrow — tomorrow's bookings\n"
                      "/day 30.10 — bookings for any date\n"
                      "/week — bookings for 7 days\n"
                      "/all — all upcoming bookings\n"
                      "/find — find a client (name, @username or phone)\n"
                      "/stats — statistics and revenue for 30 days (/stats 7 — for 7)\n"
                      "/export — export bookings to Excel\n"
                      "/block — block time (day off, vacation, phone booking)\n"
                      "/blocks — list of blocked time\n"
                      "/masters — masters in the bot: invite, disconnect\n"
                      "/prices — change service prices\n"
                      "/pause — turn AI off: all client messages go to you\n"
                      "/resume — turn AI back on\n"
                      "/reload — reload settings from the file\n"
                      "/myid — your Telegram ID\n\n"
                      "💬 To answer a client, reply (swipe left → «Reply») to their message forwarded by the bot.\n\n"
                      "AI replies: {ai_status}",
        "ai_status_on": "✅ on",
        "ai_status_paused": "⏸ paused (/resume)",
        "ai_status_nokey": "⚪️ off (no API key in settings.toml)",
        "ai_status_disabled": "⚪️ off in the business settings",
        "adm_new_booking": "🆕 <b>New booking</b>{via}\n\n👤 {client}\n💈 {service} · {master}\n📅 {day} at {time}\n💰 {price}",
        "adm_via_ai": " · via AI chat 🤖",
        "adm_via_web": " · via online booking 📲",
        "adm_cancelled": "❌ <b>Cancellation</b>\n\n👤 {client}\n💈 {service} · {master}\n📅 {day} at {time}",
        "adm_rescheduled": "🔁 <b>Rescheduled</b>\n\n👤 {client}\n💈 {service} · {master}\nWas: {old}\nNow: <b>{new}</b>",
        "adm_handoff": "🙋 <b>Your reply is needed</b>\n\n👤 {client}\n❓ {reason}{summary}\n\n"
                       "<b>Last messages:</b>\n{transcript}\n\n"
                       "↩️ Reply to this message (swipe left) — the bot will forward your answer to the client. "
                       "AI is paused for this client for {hours} h.",
        "adm_handoff_summary": "\n📝 {summary}",
        "adm_reason_media": "The client sent a photo or a file (maybe a payment)",
        "adm_tr_client": "— Client: {text}",
        "adm_tr_bot": "— Bot: {text}",
        "adm_tr_empty": "(none)",
        "btn_adm_reply": "✍️ Reply",
        "btn_adm_resume": "▶️ Resume bot",
        "adm_client_msg": "💬 <b>{client}</b>:\n{text}",
        "adm_client_media": "💬 {client}",
        "adm_reply_prompt": "Type your reply to {client} in one message (or /cancel):",
        "adm_reply_sent": "✅ Sent: {client}",
        "adm_reply_failed": "⚠️ Couldn't send — the client may have blocked the bot.",
        "adm_resumed": "▶️ AI is answering again: {client}",
        "adm_day_header": "📅 <b>{day}</b>{master} — bookings: {count}",
        "adm_day_empty": "📅 <b>{day}</b>{master} — no bookings.",
        "adm_item": "\n\n<b>{n}. {start}–{end}</b> · {master}\n💈 {service}\n👤 {client}{flags}",
        "adm_list_day": "\n\n📅 <b>{day}</b> — bookings: {count}",
        "adm_list_hint": "\n\nTap a booking to reschedule, cancel or mark the payment 👇",
        "adm_day_master": " · {name}",
        "adm_day_hint": "\n\nTap a booking to reschedule, cancel, mark a no-show or the payment 👇",
        "adm_day_pick": "📅 Choose a day:",
        "adm_day_usage": "📅 Give a date, e.g. /day 30.10 or /day tomorrow",
        "btn_adm_booking_item": "⚙️ {n} · {when} · {client}",
        "btn_day_prev": "◀️ {day}",
        "btn_day_next": "{day} ▶️",
        "btn_day_pick": "📅 Date",
        "btn_master_all": "👥 All",
        "btn_master_selected": "✅ {name}",
        "adm_card": "📋 <b>Booking #{id}</b>\n\n{summary}\n💰 {price}",
        "adm_card_source_buttons": "\n📱 Booked by the client",
        "adm_card_source_ai": "\n🤖 Booked via the AI chat",
        "adm_card_source_admin": "\n📞 Booked by an admin",
        "adm_card_noshow": "\n🚫 No-show",
        "adm_card_cancelled": "\n❌ Cancelled — {by}",
        "adm_card_confirmed": "\n✅ The client confirmed they'll come",
        "btn_adm_resched": "🔁 Reschedule",
        "btn_adm_cancel_short": "🗑 Cancel",
        "btn_adm_noshow": "🚫 No-show",
        "btn_adm_client": "👤 Client",
        "btn_adm_write": "✉️ Message",
        "adm_resched_day": "🔁 <b>Reschedule booking #{id}</b>\n\n{summary}\n\nChoose a new day 👇",
        "adm_resched_none": "🔁 No free days to reschedule to.\n\n{summary}",
        "adm_resched_time": "🔁 <b>#{id}</b> · {service} · {master}\n📅 {day} — choose a time 👇",
        "adm_resched_confirm": "🔁 <b>Reschedule this booking?</b>\n\n💈 {service}\n👤 {client}\nWas: {old}\nWill be: <b>{new}</b>\n\n{who}",
        "btn_adm_resched_yes": "✅ Reschedule",
        "adm_resched_same": "That's the same time — nothing changed.",
        "btn_adm_change_master": "👤 Change master",
        "btn_adm_master_pick": "💈 {name}",
        "adm_change_master": "👤 <b>Another master for booking #{id}</b>\n\n{summary}\n\nChoose a master 👇",
        "adm_change_master_none": "👤 No other master does «{service}».",
        "adm_new_master": "👤 New master: <b>{master}</b>",
        "adm_master_busy": "👤 New master: <b>{master}</b>\n⚠️ This master is busy at {time} — choose another day.",
        "adm_resched_done": "🔁 <b>Rescheduled</b>\n\n{summary}\n\nWas: {old}\n{who}",
        "adm_resched_notified": "The client has been notified.",
        "adm_resched_offline": "The client isn't on Telegram — let them know yourself.",
        "adm_find_usage": "🔎 Find a client: /find Ivan, /find @username or /find 0671 (part of the phone)",
        "adm_find_none": "🔎 Nobody found for «{q}».",
        "adm_find_many": "🔎 Found: {count}. Choose a client 👇",
        "btn_adm_client_item": "👤 {label}",
        "adm_client_card": "👤 <b>{name}</b>\n{contacts}\n{tg}\n\n📊 Visits: {done} · no-shows: {noshow} · cancellations: {cancelled}\n💰 Total: {spent}{last}{upcoming}{notes}",
        "adm_client_tg_yes": "✉️ Uses the bot",
        "adm_client_tg_no": "📵 Not on Telegram",
        "adm_client_last": "\n🗓 Last visit: {day} · {service}",
        "adm_client_upcoming": "\n\n<b>Upcoming:</b>{items}",
        "adm_client_upcoming_item": "\n• {when} · {service}",
        "adm_client_notes": "\n\n📝 {notes}",
        "btn_adm_client_booking": "⚙️ {when} · {service}",
        "btn_adm_client_book": "📞 Book",
        "adm_export_usage": "📊 /export — bookings for 30 days and all upcoming; /export 90 — for 90 days.",
        "adm_export_empty": "No bookings for this period.",
        "adm_export_caption": "📊 Bookings since {start} (and all upcoming): {count}",
        "adm_export_headers": "Date|Time|End|Master|Service|Price|Status|Client|Phone|Telegram|Source|Prepayment|Note|Created",
        "adm_export_sheet": "Bookings",
        "adm_export_statuses": "planned|done|no-show|cancelled",
        "adm_export_sources": "client|AI chat|admin",
        "adm_export_prepay": "awaiting|client says paid|paid",
        "adm_master_revenue": "\n   {name}: {count} · {revenue}",
        "adm_evening_report": "🌙 <b>Day summary · {day}</b>\n\n✅ Done: {done} · 🚫 no-shows: {noshow} · ❌ cancelled: {cancelled}\n💰 Revenue: <b>{revenue}</b>{by_master}\n\n📅 Bookings tomorrow: {tomorrow}",
        "client_rescheduled_by_admin": "🔁 The admin rescheduled your booking:\n💈 {service} · {master}\nWas: {old}\nNow: <b>{new}</b>\n\nIf the time doesn't suit you, change it in «🗓 My bookings» or message us.",
        "adm_booking_summary": "<b>{day}, {start}–{end}</b> · {master}\n💈 {service}\n👤 {client}",
        "adm_noshow_done": "🚫 {client} ({time}) — no-show",
        "adm_cancel_ask": "Cancel this booking?\n\n{booking}\n\n{who}",
        "adm_cancel_notify": "The client will get a Telegram message.",
        "adm_cancel_offline": "The client isn't on Telegram — let them know yourself.",
        "adm_cancelled_done": "🗑 <b>Cancelled</b>\n\n{booking}\n\nThe client has been notified.",
        "adm_cancelled_done_offline": "🗑 <b>Cancelled</b>\n\n{booking}\n\nThe client isn't on Telegram — let them know yourself.",
        "adm_cancelled_header": "\n\n➖➖➖\n❌ <b>Cancelled</b> — {count}",
        "adm_cancelled_item": "\n{day} {start} · {master} · {service} · {client} — {by}",
        "adm_cancelled_by_client": "cancelled by client",
        "adm_cancelled_by_admin": "cancelled by admin",
        "adm_new_booking_prepay": "\n💳 Awaiting a {amount} prepayment by {deadline}",
        "adm_prepay_claim_note": "💳 <b>The client says they've paid</b>\n\n{booking}\n\nCheck that {amount} arrived and confirm 👇",
        "adm_prepay_screenshot": "💳 <b>The client sent a payment screenshot</b> (above)\n\n{booking}\n\nCheck that {amount} arrived and confirm 👇",
        "adm_prepay_overdue": "⏰ <b>Payment not confirmed yet</b>\nThe client said they paid {hours} h ago. Please check: such bookings are not cancelled automatically.\n\n{booking}",
        "btn_adm_prepay_ok": "✅ Payment received",
        "btn_adm_cancel_booking": "🗑 Cancel booking",
        "adm_prepay_ok_done": "✅ <b>Prepayment confirmed</b>, the client has been notified.\n\n{booking}",
        "adm_prepay_ok_alert": "✅ Payment confirmed",
        "adm_prepay_already": "The prepayment is already confirmed.",
        "adm_prepay_waiting": "\n💳 ⏳ awaiting prepayment",
        "adm_prepay_claimed": "\n💳 ❔ client says they've paid — please check",
        "adm_prepay_paid": "\n💳 ✅ prepayment received",
        "adm_cancelled_by_unpaid": "not paid",
        "adm_cancelled_unpaid": "⏰ <b>Booking cancelled automatically</b> — prepayment not confirmed within {hours} h.\n\n{booking}",
        "btn_adm_clear_cancelled": "🧹 Clear cancelled ({count})",
        "adm_clear_ask": "Remove cancelled bookings from the list ({count})?\nThey won't show in /all any more but stay in the stats.",
        "btn_adm_yes_clear": "Yes, clear",
        "adm_cleared_done": "🧹 Cancelled bookings cleared: {count}. Updated list — /all",
        "btn_adm_yes_cancel": "Yes, cancel",
        "client_cancelled_by_admin": "Unfortunately, your booking was cancelled by the admin:\n💈 {service} · {master}\n"
                                     "📅 {day} at {time}\n\nPlease choose another time — «📅 Book» — or message us.",
        "adm_week_header": "🗓 <b>Bookings for 7 days</b>",
        "adm_week_empty": "\n\nNo bookings.",
        "adm_week_more": "\n\n➕ {count} more later — /all",
        "adm_all_header": "🗓 <b>All upcoming bookings</b>",
        "adm_note_line": "\n📝 {note}",
        "adm_via_admin": " · booked by admin 📞",
        "btn_adm_book_confirm": "✅ Book",
        "btn_adm_book_cancel": "✖️ Cancel",
        "adm_book_service": "📞 <b>Book a client</b>\nChoose a service:",
        "adm_book_group": "📞 <b>Book a client</b>\nChoose a category — then service, barber, day and time 👇",
        "adm_book_in_group": "📞 <b>{group}</b>\nChoose a service — then barber, day and time 👇",
        "adm_book_master": "📞 {service}\nChoose a master:",
        "adm_book_day": "📞 {service} · {master}\nChoose a day:",
        "adm_book_time": "📞 {service} · {master} · {day}\nChoose a time:",
        "adm_book_no_days": "{master} has no free days for «{service}». Choose another master:",
        "adm_book_client_prompt": "📞 {service} · {master} · {day} at {time}\n\n"
                                  "Send the client's details in one message: <b>name</b> and <b>phone</b>, "
                                  "a comment on a new line (optional). For example:\n"
                                  "<code>Olena +380671234567\nwants it shorter than last time</code>\n\n"
                                  "Or share the client's Telegram contact (📎 → Contact).\n/cancel — cancel.",
        "adm_book_need_name": "I can't see the client's name. Send again: name, phone, a comment on a new line.",
        "adm_book_card": "📞 <b>Check the booking</b>\n\n👤 {client}\n💈 {service} · {master}\n📅 {day} at {time}\n"
                         "💰 {price}{note}\n\n{hint}\n\nTo change the details, just send them again.",
        "adm_book_hint_tg": "✉️ The client is already in the bot ({client}) — they'll get a message and reminders.",
        "adm_book_hint_known": "🗂 The client is already in the database ({client}) but not on Telegram — no messages.",
        "adm_book_hint_offline": "📵 New client without Telegram — no messages or reminders.",
        "adm_book_duplicate": "The client already has a booking at this time (#{id}).",
        "adm_book_done": "✅ <b>Booked</b> <code>#{id}</code>\n👤 {client}\n💈 {service} · {master}\n"
                         "📅 {day} at {time}{notified}",
        "adm_book_notified": "\n\n✉️ The client got a Telegram message.",
        "adm_book_not_notified": "\n\n📵 The client got no message (not on Telegram) — call them if needed.",
        "adm_book_aborted": "Booking not created.",
        "client_booked_by_admin": "📞 The admin booked you in:\n💈 {service} · {master}\n📅 {day} at {time}\n💰 {price}\n\n"
                                  "To reschedule or cancel — «🗓 My bookings».",
        "adm_block_usage": "🔒 <b>Block time</b>\n\nFormat: <code>/block barber date [time] [note]</code>\n\n"
                           "Examples:\n<code>/block {example} 30.10</code> — whole day\n"
                           "<code>/block {example} 30.10 14:00-16:00 phone booking</code>\n"
                           "<code>/block all 31.12</code> — day off for everyone\n\nBarbers: {masters}",
        "adm_block_bad": "I didn't understand the command 🤔\n\n{usage}",
        "adm_block_done": "🔒 Blocked: {master}, {day} {range}{note}",
        "adm_block_conflicts": "\n\n⚠️ There are bookings at this time — cancel them (/today, /tomorrow) or warn the clients:{lines}",
        "adm_all_masters": "all barbers",
        "adm_whole_day": "(whole day)",
        "adm_blocks_header": "🔒 <b>Blocked time</b> (tap to delete):",
        "adm_blocks_empty": "No blocked time.",
        "btn_adm_block_item": "🗑 {master} · {day} {range}",
        "adm_block_deleted": "🔓 Deleted. This time is bookable again.",
        "adm_paused": "⏸ AI is off. All client messages will be forwarded to you; booking buttons still work.\n"
                      "Turn on: /resume",
        "adm_resumed_all": "▶️ AI is answering clients again.",
        "adm_reloaded": "🔄 Settings reloaded: services — {services}, barbers — {masters}.",
        "adm_reload_failed": "❌ The settings file has an error, keeping the previous settings:\n<code>{error}</code>",
        "adm_reload_token": "\n⚠️ The bot token changed — restart the bot to apply it.",
        "adm_digest": "☀️ <b>Good morning!</b>\n\n{body}",
        "adm_ai_alert": "⚠️ <b>AI is not responding</b> ({name})\n<code>{error}</code>\n\n"
                        "The bot keeps working with buttons. Check the API key and balance at console.anthropic.com.",
        "adm_budget_alert": "⚠️ Daily AI limit reached ({name}). Until the end of the day the bot works with buttons only. "
                            "Change the limit in settings.toml (daily_token_limit).",
        "adm_stats": "📊 <b>Statistics for {days} days</b>\n\n"
                     "<b>Bookings</b>\n"
                     "• created: {created} (AI chat: {by_ai}, buttons: {by_buttons}, admin: {by_admin})\n"
                     "• at night (22:00–08:00): {night}\n"
                     "• completed: {done} · no-shows: {noshow} · cancelled: {cancelled}\n"
                     "• upcoming: {upcoming}\n\n"
                     "<b>Revenue</b>\n"
                     "• {revenue} · average check {avg_check}{by_master}\n"
                     "• expected from upcoming bookings: {expected}\n\n"
                     "<b>Conversations</b>\n"
                     "• clients who wrote: {clients}\n"
                     "• handed over to you: {handoffs}\n"
                     "• handled by the bot alone: {auto_rate}\n\n"
                     "<b>Reminders</b>\n"
                     "• sent: {reminders} · «I'll be there»: {confirmed}\n\n"
                     "<b>AI</b>\n"
                     "• messages handled: {ai_calls} · tokens: {tokens}\n"
                     "• estimated cost: ${cost}",
        "adm_client_noname": "Client",
        "cmd_start": "Main menu",
        "cmd_admin": "Owner panel",
        "cmd_today": "Today's bookings",
        "cmd_tomorrow": "Tomorrow's bookings",
        "cmd_book": "Book a client",
        "cmd_day": "Bookings for a date",
        "cmd_find": "Find a client",
        "cmd_export": "Export to Excel",
        "cmd_week": "Bookings for 7 days",
        "cmd_all": "All upcoming bookings",
        "cmd_stats": "Statistics",
        "cmd_block": "Block time",
        "cmd_blocks": "Blocked time",
        "cmd_pause": "Turn AI off",
        "cmd_resume": "Turn AI on",
        "cmd_reload": "Reload settings",
        "cmd_myid": "My Telegram ID",
        "cmd_masters": "Masters in the bot",
        "cmd_prices": "Change prices",
        "adm_prices": "💰 <b>Service prices</b>\nTap a service to change its price 👇",
        "adm_prices_changed": "\n\n✏️ — price changed here in the bot (the settings file has the old one).",
        "adm_price_ask": "💰 <b>{title}</b>\nNow: <b>{price}</b>\n\nSend the new price as a number, e.g. 650.",
        "adm_price_file": "\nIn the settings file: {price}.",
        "btn_adm_price_reset": "↩️ Restore {price}",
        "adm_price_bad": "That doesn't look like a price 🤔 Send just a number, e.g. 650. Cancel — /cancel",
        "adm_price_done": "✅ <b>{title}</b>: {old} → <b>{new}</b>\nClients and the AI already see the new price. "
                          "Earlier bookings keep the old price.",
        "adm_price_combos": "\nAdd-on combination prices recalculated.",
        "adm_price_changed_note": "💰 {admin} changed a price: <b>{title}</b> {old} → <b>{new}</b>",
        "cmd_my": "My day",
        "cmd_myweek": "My week",
        "cmd_off": "Block time",
        "cmd_offs": "My blocked time",
        # Masters: admin
        "adm_masters": "✂️ <b>Masters in the bot</b>\n\nA connected master sees their bookings, blocks their own "
                       "time and gets notified about their clients.\n{items}",
        "adm_masters_on": "\n✅ <b>{name}</b> — {who}",
        "adm_masters_off": "\n⚪️ <b>{name}</b> — not connected",
        "btn_adm_master_invite": "🔗 Invite: {name}",
        "btn_adm_master_unlink": "✖️ Disconnect: {name}",
        "btn_adm_yes_unlink": "✖️ Yes, disconnect",
        "btn_adm_open": "📋 Open booking",
        "adm_master_invite": "🔗 Link for master <b>{name}</b>:\n\n{link}\n\nForward it to the master — they "
                             "open it and tap “Start”. One-time link, valid for {hours} h.",
        "adm_master_no_username": "Couldn't get the bot address. Please try again in a minute.",
        "adm_master_unlink_ask": "Disconnect master <b>{name}</b> from the bot? They will no longer see bookings "
                                 "or get notifications.",
        "adm_master_unlinked": "✖️ Master {name} disconnected from the bot.",
        "adm_master_joined": "✂️ Master <b>{name}</b> connected to the bot ({who}).",
        "adm_master_noshow": "🚫 <b>Master {master} marked a no-show</b>\n\n{booking}",
        "adm_master_off": "🌴 Master <b>{master}</b> blocked time: {day} {range}",
        "adm_master_off_conflicts": "\n\n⚠️ <b>There are bookings at this time</b> — please arrange with "
                                    "the clients (reschedule or cancel):{lines}",
        "adm_master_on": "🔓 Master <b>{master}</b> unblocked time: {day} {range}",
        # Masters: the master
        "mst_invite_bad": "This link is invalid or already used. Ask the administrator for a new one.",
        "mst_joined": "✅ <b>You are connected as master “{name}”.</b>\n\n",
        "mst_start": "✂️ <b>{name}</b>, you are a master in the “{shop}” bot.\n\n"
                     "📅 <b>My day</b> — your bookings, browse days ◀️ ▶️\n"
                     "🗓 <b>My week</b> — bookings for 7 days\n"
                     "🌴 <b>Block time</b> — day off, break, personal matters\n"
                     "🔒 <b>My blocked time</b> — view and unblock\n\n"
                     "The bot will tell you about new bookings, cancellations and reschedules, send your schedule "
                     "in the morning and remind you before each client.",
        "mst_unlinked": "You have been disconnected from the bot as a master. You can still book as a client 👇",
        "btn_mst_day": "📅 My day",
        "btn_mst_week": "🗓 My week",
        "btn_mst_off": "🌴 Block time",
        "btn_mst_offs": "🔒 My blocked time",
        "btn_mst_to_day": "⬅️ To the day",
        "mst_day_hint": "\n\nTap a booking to open its card 👇",
        "mst_day_off": "\n\n🌴 Day off according to your schedule.",
        "mst_day_blocks": "\n\n🔒 Blocked: {ranges}",
        "mst_week_header": "🗓 <b>Your bookings for 7 days</b>",
        "mst_off_day": "🌴 <b>Block time</b>\n\nChoose a day:",
        "mst_off_range": "🌴 <b>{day}</b> · your hours {hours}\n\nBlock the whole day or from what time?",
        "mst_off_whole_only": "🌴 <b>{day}</b> · {hours}\n\nBlock the whole day?",
        "mst_off_no_work": "day off by schedule",
        "mst_off_end": "🌴 <b>{day}</b>, from {start}\n\nUntil what time?",
        "btn_mst_whole_day": "🌴 Whole day",
        "btn_mst_off_yes": "✅ Block",
        "mst_off_confirm": "Block <b>{day} {range}</b>?\nClients won't be able to book this time.{conflicts}",
        "mst_off_conflicts": "\n\n⚠️ There are bookings at this time — the administrator will be notified "
                             "to arrange with the clients:{lines}",
        "mst_off_done": "🔒 Blocked: <b>{day} {range}</b>. Clients won't be able to book this time.",
        "mst_off_done_conflicts": "\n\n⚠️ Bookings at this time remain — the administrator has been notified:{lines}",
        "mst_offs_header": "🔒 <b>Your blocked time</b>\nTap to unblock:",
        "mst_offs_header_none": "🔒 <b>Your blocked time</b>",
        "mst_offs_admin": "\n\nBlocked by the administrator (only they can change it):{lines}",
        "mst_offs_empty": "🔒 No blocked time. To block — “🌴 Block time”.",
        "btn_mst_block_item": "🗑 {label}",
        "alert_mst_opened": "Time is open for booking again",
        "mst_new": "🆕 <b>New booking with you</b>\n\n📅 {day} at {time}\n💈 {service}\n👤 {client}",
        "mst_cancelled": "❌ <b>Booking cancelled</b>\n\n📅 {day} at {time}\n💈 {service}\n👤 {client}",
        "mst_moved": "🔁 <b>Booking moved to another master</b>\n\n📅 {day} at {time}\n💈 {service}\n👤 {client}",
        "mst_rescheduled": "🔁 <b>Booking rescheduled</b>\n\n💈 {service}\n👤 {client}\nWas: {old}\nNow: <b>{new}</b>",
        "mst_digest": "☀️ <b>Good morning, {name}!</b>\n\n{body}",
        "mst_heads_up": "⏰ <b>At {time}</b> (in {min} min) — {client}\n💈 {service}",
    },

    # ------------------------------------------------------------------ HU
    "hu": {
        # Vendég menü
        "btn_book": "📅 Időpontfoglalás",
        "btn_my": "🗓 Foglalásaim",
        "btn_prices": "💈 Szolgáltatások és árak",
        "btn_contacts": "📍 Elérhetőségek",
        "btn_webapp": "📅 Online foglalás",
        "webapp_invite": "Válasszon szolgáltatást, fodrászt és időpontot a foglalási ablakban 👇",
        "start": "Üdvözlöm! 👋 A(z) <b>{name}</b> foglalási asszisztense vagyok.\n\n"
                 "Segítek időpontot foglalni, áthelyezni vagy lemondani, és válaszolok a kérdéseire.\n\n"
                 "Válasszon a menüből 👇 vagy egyszerűen írja le, mi érdekli.",
        "start_no_ai": "Üdvözlöm! 👋 A(z) <b>{name}</b> foglalási asszisztense vagyok.\n\n"
                       "Segítek időpontot foglalni, áthelyezni vagy lemondani.\nVálasszon a menüből 👇",
        "start_admin_hint": "\n\n🛠 Ön a bot adminisztrátora. Vezérlőpult: /admin",
        # Foglalás gombokkal
        "choose_service": "Válasszon szolgáltatást:",
        "choose_group": "✨ Válasszon kategóriát — utána kiválasztjuk a fodrászt és Önnek megfelelő időpontot 👇",
        "choose_service_in_group": "<b>{group}</b>\nVálasszon szolgáltatást — utána kiválasztjuk a fodrászt és Önnek megfelelő időpontot 👇",
        "btn_service": "{title} · {price}",
        "choose_master": "💈 <b>{service}</b>\n💰 {price} · ⏱ {duration} perc{description}\n\nVálasszon fodrászt 👇",
        "master_service_desc": "\n<i>{description}</i>",
        "btn_any_master": "👥 Bármelyik fodrász",
        "any_master": "bármelyik fodrász",
        "choose_day": "💈 <b>{service}</b> · {master}\n\nVálasszon napot:",
        "no_days": "💈 <b>{service}</b> · {master}\n\nSajnos a következő {days} napban nincs szabad időpont 😕\n"
                   "Írjon nekünk, és megpróbálunk megoldást találni.",
        "choose_time": "💈 <b>{service}</b> · {master}\n📅 {day}\n\nVálasszon időpontot:",
        "no_times": "📅 {day}: már nincs szabad időpont. Kérjük, válasszon másik napot:",
        "btn_back": "⬅️ Vissza",
        "day_today": "Ma",
        "day_tomorrow": "Holnap",
        "card": "📝 <b>Kérjük, ellenőrizze:</b>\n\n💈 {service}\n👤 Fodrász: {master}\n"
                "📅 {day}, {time}\n⏱ {duration} perc · 💰 {price}",
        "btn_confirm": "✅ Megerősítés",
        "btn_add_addon": "➕ {title} (+{duration} perc, +{price})",
        "btn_other_time": "⬅️ Másik időpont",
        "btn_no_change": "✖️ Nem, módosítom",
        "ask_phone": "Már csak a telefonszáma hiányzik, hogy a fodrász kapcsolatba tudjon lépni Önnel.\n\n"
                     "Nyomja meg lent a <b>«📱 Telefonszám megosztása»</b> gombot, vagy írja be a számot üzenetben.",
        "btn_share_phone": "📱 Telefonszám megosztása",
        "btn_cancel": "Mégse",
        "bad_phone": "Ez nem tűnik telefonszámnak 🤔\nNyomja meg a «📱 Telefonszám megosztása» gombot, "
                     "vagy írja be a számot országhívóval, pl. +36301234567.",
        "phone_saved": "Köszönjük, a számot elmentettük 👍",
        "booking_aborted": "Rendben, a foglalás nem jött létre. Ha meggondolja magát — «📅 Időpontfoglalás».",
        "booked": "✅ <b>Kész, a foglalása rögzítve!</b>\n\n💈 {service}\n👤 {master}\n📅 {day}, {time}\n💰 {price}{address}\n\n"
                  "Előre emlékeztetni fogjuk. Áthelyezés vagy lemondás — a «🗓 Foglalásaim» menüpontban.",
        "booked_address": "\n📍 {address}",
        "prepay_block": "\n\n💳 <b>A foglalás megerősítéséhez {amount} előleg szükséges</b>\nKártya: <code>{card}</code>{recipient}\nFizetési határidő: <b>{deadline}</b>, ellenkező esetben a foglalás automatikusan törlődik. Az előleg beszámít a szolgáltatás árába.\n\nA fizetés után nyomja meg a «✅ Fizettem» gombot, vagy küldjön ide egy képernyőképet 👇",
        "prepay_recipient": "\nCímzett: {recipient}",
        "btn_prepay_done": "✅ Fizettem",
        "btn_prepay_done_item": "✅ Fizettem {short}",
        "prepay_claimed_client": "Köszönjük! 🙏 Az adminisztrátor ellenőrzi a fizetést és megerősíti a foglalást — itt értesítjük.",
        "prepay_screenshot_client": "Köszönjük, megkaptuk a képernyőképet! 🙏 Az adminisztrátor ellenőrzi a fizetést és megerősíti a foglalást — itt értesítjük.",
        "prepay_photo_ask": "📸 Ez az előleg fizetéséről készült képernyőkép?",
        "btn_photo_is_payment": "✅ Igen, ez a fizetés",
        "btn_photo_other": "Nem, másról van szó",
        "prepay_already_paid": "Az előleg már megerősítve ✅",
        "prepay_paid_client": "✅ <b>Az előleg megérkezett — a foglalás megerősítve!</b>\n💈 {service} · {master}\n📅 {day}, {time}\n\nVárjuk Önt 💛",
        "client_cancelled_unpaid": "😔 Sajnos a foglalását töröltük: az előleg nem érkezett meg időben.\n💈 {service} · {master}\n📅 {day}, {time}\n\nHa még aktuális, foglaljon újra — szívesen látjuk 💛",
        "my_prepay_waiting": "\n💳 Várjuk az előleget ({amount}), határidő: {deadline}",
        "my_prepay_claimed": "\n💳 Ellenőrizzük a fizetését ⏳",
        "my_prepay_paid": "\n💳 Az előleg megérkezett ✅",
        "already_booked": "✅ Erre az időpontra már foglalt.",
        "slot_taken": "Hoppá, ezt az időpontot épp most foglalták le 😕 Kérjük, válasszon másikat:",
        "week_limit": "Erre a hétre már elérte a foglalások maximális számát ({limit}) 🙏\nVálasszon másik hetet, vagy helyezze át az egyik meglévő foglalását.",
        "too_many_active": "Már {count} aktív foglalása van — ez a maximum. "
                           "Helyezze át vagy mondja le valamelyiket a «🗓 Foglalásaim» menüpontban.",
        "booking_error": "Nem sikerült létrehozni a foglalást 😕 Kérjük, próbálja újra, vagy írjon nekünk.",
        "proposal_declined": "Rendben 🙂 Írja meg, mit módosítsak, és keresek másik lehetőséget.",
        # Foglalásaim
        "my_none": "Még nincs közelgő foglalása 🙂\nÉppen ideje változtatni ezen — válasszon Önnek megfelelő időpontot 👇",
        "my_header": "✨ <b>Az Ön foglalásai</b> ✨",
        "my_item": "\n\n📅 <b>{day}, {time}</b>\n✂️ {service}\n💈 Fodrász: {master}",
        "my_footer": "\n\n💛 Már várjuk Önt! Érkezzen néhány perccel korábban, hogy ellazulhasson "
                     "és ráhangolódhasson az új megjelenésére ✨\n\nHa változnak a tervei, helyezze át vagy "
                     "mondja le a foglalást az alábbi gombokkal 👇",
        "btn_resched_item": "🔁 Áthelyezés {short}",
        "btn_cancel_item": "❌ Lemondás {short}",
        "cancel_ask": "Lemondja a foglalást?\n\n💈 {service} · {master}\n📅 {day}, {time}",
        "btn_yes_cancel": "Igen, lemondom",
        "btn_no": "Nem",
        "cancel_kept": "Rendben, a foglalás megmarad ✅",
        "cancelled": "A foglalás lemondva.\nReméljük, máskor találkozunk! Új foglaláshoz — «📅 Időpontfoglalás».",
        "cancel_too_late": "A látogatásig kevesebb mint {hours} óra van hátra, ezért online már nem mondható le. "
                           "Kérjük, hívjon minket{phone}.",
        "cancel_too_late_phone": ": {phone}",
        "booking_inactive": "Ez a foglalás már nem aktív.",
        "resched_choose_day": "🔁 <b>Áthelyezés</b>\n💈 {service} · {master}\nJelenleg: {day}, {time}\n\nVálasszon új napot:",
        "resched_choose_time": "🔁 <b>Áthelyezés</b>\n💈 {service} · {master}\n📅 {day}\n\nVálasszon új időpontot:",
        "resched_card": "🔁 <b>Áthelyezi a foglalást?</b>\n\n💈 {service} · {master}\nEddig: {old}\nÚj időpont: <b>{new}</b>",
        "btn_confirm_resched": "✅ Áthelyezés",
        "rescheduled": "✅ A foglalás áthelyezve.\n\n💈 {service} · {master}\n📅 <b>{day}, {time}</b>",
        "resched_none": "A következő {days} napban nincs szabad időpont 😕 Írjon nekünk, és megoldjuk.",
        # Információk
        "prices_header": "💈 <b>{name}</b>\n✨ <b>SZOLGÁLTATÁSOK ÉS ÁRAK</b> ✨\n<i>Válassza ki, ami tetszik — az alábbi gombbal rögtön foglalhat 👇</i>",
        "price_group": "\n\n━━━━━━━━━━━━\n<b>{group}</b>",
        "price_item": "\n\n<b>{title}</b> — {price}\n⏱ {duration} perc",
        "price_desc": "\n{description}",
        "prices_addons_header": "\n\n➕ <b>Kiegészítők a hajvágáshoz</b> (gombbal, foglalás közben)",
        "price_addon_item": "\n{title} — +{price}, +{duration} perc",
        "contacts_header": "📍 <b>{name}</b>",
        "contacts_address": "\n\n🏠 {address}",
        "contacts_phone": "\n📞 {phone}",
        "contacts_hours": "\n\n🕒 <b>Nyitvatartás</b>\n{hours}",
        "contacts_directions": "\n\n🚗 {directions}",
        "contacts_payment": "\n💳 {payment}",
        "contacts_prepay": "\n💳 Előleg: {amount} — a részleteket a foglalás után rögtön elküldjük (fizetési határidő: {hours} óra).",
        "contacts_masters_header": "\n\n━━━━━━━━━━━━\n👥 <b>Fodrászaink</b>",
        "contacts_master": "\n\n💈 <b>{name}</b>{about}\n🗓 {schedule}",
        "contacts_master_about": "\n<i>{about}</i>",
        "btn_map": "🗺 Megnyitás a térképen",
        "day_off": "zárva",
        # Emlékeztetők
        "reminder": "⏰ <b>Emlékeztető a látogatásra</b>\n\n📅 {day}, {time}\n💈 {service} · {master}{address}",
        "btn_will_come": "✅ Ott leszek",
        "btn_resched": "🔁 Áthelyezés",
        "btn_cancel_booking": "❌ Lemondás",
        "will_come_ok": "\n\n✅ Remek, várjuk!",
        "nudge": "Üdvözlöm, {name}! 👋\nMár {weeks} hete járt nálunk utoljára ({service}). "
                 "Foglaljak Önnek új időpontot?",
        "btn_book_again": "📅 Időpontfoglalás",
        "btn_no_nudges": "🔕 Ne emlékeztessenek",
        "nudges_off": "Rendben, többé nem emlékeztetem 🙂",
        # AI és átadás az adminisztrátornak
        "ai_off": "Kérjük, válasszon a menüből 👇 — így a leggyorsabb.",
        "ai_error": "Elnézést, most nem tudok válaszolni 😔\nHasználja a menü gombjait 👇, vagy próbálja újra egy kicsit később.",
        "ai_refusal": "Elnézést, ebben nem tudok segíteni 🙂 Tudok időpontot foglalni, vagy továbbíthatom a kérdését az adminisztrátornak.",
        "rate_limited": "Túl sok üzenet rövid idő alatt 🙈 Használja a menü gombjait 👇, vagy írjon egy kicsit később.",
        "handoff_client": "Továbbítottam a kérdését az adminisztrátornak — ebben a chatben fog válaszolni 🙌",
        "handoff_no_admin": "Ebben a kérdésben érdemes közvetlenül az adminisztrátorhoz fordulni{phone} 🙏",
        "media_received": "Megkaptam 👍 Továbbítom az adminisztrátornak — ebben a chatben fog válaszolni.",
        "voice_unsupported": "A hangüzeneteket egyelőre nem tudom meghallgatni 🙈 Kérjük, írja le szövegesen.",
        "unsupported": "Csak szöveges üzeneteket értek 🙂",
        "meta_choose_lang": "🌐 Válasszon nyelvet:",
        "btn_language": "🌐 Nyelv",
        "paused_ack": "Köszönjük az üzenetét! Az adminisztrátor hamarosan válaszol.",
        "admin_title": "Adminisztrátor",
        "admin_reply_to_client": "👤 <b>{title}:</b>\n{text}",
        "alert_expired": "Ez a gomb már nem érvényes. Kérjük, kezdje újra.",
        "alert_no_access": "Nincs hozzáférés",
        "unknown_command": "Ez a parancs ismeretlen 🤔 Válasszon a menüből 👇",
        "myid": "Az Ön Telegram-azonosítója: <code>{id}</code>",
        "state_cleared": "Megszakítva.",
        # Admin
        "admin_help": "🛠 <b>Vezérlőpult · {name}</b>\n\n"
                      "/book — vendég foglalása (telefonos, helyszíni)\n"
                      "/today — mai foglalások\n"
                      "/tomorrow — holnapi foglalások\n"
                      "/day 30.10 — foglalások egy tetszőleges napra\n"
                      "/week — foglalások 7 napra\n"
                      "/all — az összes közelgő foglalás\n"
                      "/find — vendég keresése (név, @felhasználónév vagy telefonszám)\n"
                      "/stats — statisztika és bevétel 30 napra (/stats 7 — 7 napra)\n"
                      "/export — foglalások exportálása Excelbe\n"
                      "/block — idő blokkolása (szabadnap, szabadság, telefonos foglalás)\n"
                      "/blocks — blokkolt idők listája\n"
                      "/masters — fodrászok a botban: meghívás, leválasztás\n"
                      "/prices — szolgáltatások árainak módosítása\n"
                      "/pause — AI kikapcsolása: minden vendégüzenet Önhöz kerül\n"
                      "/resume — AI visszakapcsolása\n"
                      "/reload — beállítások újratöltése a fájlból\n"
                      "/myid — az Ön Telegram-azonosítója\n\n"
                      "💬 Vendégnek válaszolni úgy lehet, hogy a bot által továbbított üzenetére válaszol (balra csúsztatás → «Válasz»).\n\n"
                      "AI-válaszok: {ai_status}",
        "ai_status_on": "✅ bekapcsolva",
        "ai_status_paused": "⏸ szünetel (/resume)",
        "ai_status_nokey": "⚪️ kikapcsolva (nincs API-kulcs a settings.toml fájlban)",
        "ai_status_disabled": "⚪️ kikapcsolva a vállalkozás beállításaiban",
        "adm_new_booking": "🆕 <b>Új foglalás</b>{via}\n\n👤 {client}\n💈 {service} · {master}\n📅 {day}, {time}\n💰 {price}",
        "adm_via_ai": " · AI-chaten keresztül 🤖",
        "adm_via_web": " · online foglalással 📲",
        "adm_cancelled": "❌ <b>Lemondás</b>\n\n👤 {client}\n💈 {service} · {master}\n📅 {day}, {time}",
        "adm_rescheduled": "🔁 <b>Áthelyezés</b>\n\n👤 {client}\n💈 {service} · {master}\nEddig: {old}\nMost: <b>{new}</b>",
        "adm_handoff": "🙋 <b>Az Ön válasza szükséges</b>\n\n👤 {client}\n❓ {reason}{summary}\n\n"
                       "<b>Utolsó üzenetek:</b>\n{transcript}\n\n"
                       "↩️ Válaszoljon erre az üzenetre (balra csúsztatás) — a bot továbbítja a válaszát a vendégnek. "
                       "Az AI {hours} órára szünetel ennél a vendégnél.",
        "adm_handoff_summary": "\n📝 {summary}",
        "adm_reason_media": "A vendég fotót vagy fájlt küldött (talán fizetési igazolást)",
        "adm_tr_client": "— Vendég: {text}",
        "adm_tr_bot": "— Bot: {text}",
        "adm_tr_empty": "(nincs)",
        "btn_adm_reply": "✍️ Válasz",
        "btn_adm_resume": "▶️ Bot visszakapcsolása",
        "adm_client_msg": "💬 <b>{client}</b>:\n{text}",
        "adm_client_media": "💬 {client}",
        "adm_reply_prompt": "Írja meg a választ {client} részére egy üzenetben (vagy /cancel):",
        "adm_reply_sent": "✅ Elküldve: {client}",
        "adm_reply_failed": "⚠️ Nem sikerült elküldeni — lehet, hogy a vendég letiltotta a botot.",
        "adm_resumed": "▶️ Az AI újra válaszol: {client}",
        "adm_day_header": "📅 <b>{day}</b>{master} — foglalások: {count}",
        "adm_day_empty": "📅 <b>{day}</b>{master} — nincs foglalás.",
        "adm_item": "\n\n<b>{n}. {start}–{end}</b> · {master}\n💈 {service}\n👤 {client}{flags}",
        "adm_list_day": "\n\n📅 <b>{day}</b> — foglalások: {count}",
        "adm_list_hint": "\n\nÁthelyezéshez, lemondáshoz vagy a fizetés jelöléséhez koppintson egy foglalásra 👇",
        "adm_day_master": " · {name}",
        "adm_day_hint": "\n\nÁthelyezéshez, lemondáshoz, meg nem jelenés vagy fizetés jelöléséhez koppintson egy foglalásra 👇",
        "adm_day_pick": "📅 Válasszon napot:",
        "adm_day_usage": "📅 Adjon meg egy dátumot, pl. /day 30.10 vagy /day holnap",
        "btn_adm_booking_item": "⚙️ {n} · {when} · {client}",
        "btn_day_prev": "◀️ {day}",
        "btn_day_next": "{day} ▶️",
        "btn_day_pick": "📅 Dátum",
        "btn_master_all": "👥 Mind",
        "btn_master_selected": "✅ {name}",
        "adm_card": "📋 <b>Foglalás #{id}</b>\n\n{summary}\n💰 {price}",
        "adm_card_source_buttons": "\n📱 A vendég foglalta",
        "adm_card_source_ai": "\n🤖 AI-chaten keresztül foglalták",
        "adm_card_source_admin": "\n📞 Adminisztrátor foglalta",
        "adm_card_noshow": "\n🚫 Nem jelent meg",
        "adm_card_cancelled": "\n❌ Lemondva — {by}",
        "adm_card_confirmed": "\n✅ A vendég megerősítette, hogy jön",
        "btn_adm_resched": "🔁 Áthelyezés",
        "btn_adm_cancel_short": "🗑 Lemondás",
        "btn_adm_noshow": "🚫 Nem jelent meg",
        "btn_adm_client": "👤 Vendég",
        "btn_adm_write": "✉️ Üzenet",
        "adm_resched_day": "🔁 <b>A(z) #{id} foglalás áthelyezése</b>\n\n{summary}\n\nVálasszon új napot 👇",
        "adm_resched_none": "🔁 Nincs szabad nap, ahová áthelyezhető lenne.\n\n{summary}",
        "adm_resched_time": "🔁 <b>#{id}</b> · {service} · {master}\n📅 {day} — válasszon időpontot 👇",
        "adm_resched_confirm": "🔁 <b>Áthelyezi a foglalást?</b>\n\n💈 {service}\n👤 {client}\nEddig: {old}\nÚj időpont: <b>{new}</b>\n\n{who}",
        "btn_adm_resched_yes": "✅ Áthelyezés",
        "adm_resched_same": "Ugyanaz az időpont — nem történt változás.",
        "btn_adm_change_master": "👤 Fodrász cseréje",
        "btn_adm_master_pick": "💈 {name}",
        "adm_change_master": "👤 <b>Másik fodrász a(z) #{id} foglaláshoz</b>\n\n{summary}\n\nVálasszon fodrászt 👇",
        "adm_change_master_none": "👤 Ezt a szolgáltatást («{service}») más fodrász nem végzi.",
        "adm_new_master": "👤 Új fodrász: <b>{master}</b>",
        "adm_master_busy": "👤 Új fodrász: <b>{master}</b>\n⚠️ {time}-kor ez a fodrász foglalt — válasszon másik napot.",
        "adm_resched_done": "🔁 <b>Áthelyezve</b>\n\n{summary}\n\nEddig: {old}\n{who}",
        "adm_resched_notified": "A vendég értesítést kapott.",
        "adm_resched_offline": "A vendég nincs a Telegramon — értesítse Ön.",
        "adm_find_usage": "🔎 Vendég keresése: /find Ivan, /find @felhasználónév vagy /find 0671 (a telefonszám egy része)",
        "adm_find_none": "🔎 Nincs találat erre: «{q}».",
        "adm_find_many": "🔎 Találatok száma: {count}. Válasszon vendéget 👇",
        "btn_adm_client_item": "👤 {label}",
        "adm_client_card": "👤 <b>{name}</b>\n{contacts}\n{tg}\n\n📊 Látogatások: {done} · meg nem jelenések: {noshow} · lemondások: {cancelled}\n💰 Összesen: {spent}{last}{upcoming}{notes}",
        "adm_client_tg_yes": "✉️ Használja a botot",
        "adm_client_tg_no": "📵 Nincs a Telegramon",
        "adm_client_last": "\n🗓 Utolsó látogatás: {day} · {service}",
        "adm_client_upcoming": "\n\n<b>Közelgő:</b>{items}",
        "adm_client_upcoming_item": "\n• {when} · {service}",
        "adm_client_notes": "\n\n📝 {notes}",
        "btn_adm_client_booking": "⚙️ {when} · {service}",
        "btn_adm_client_book": "📞 Foglalás",
        "adm_export_usage": "📊 /export — foglalások 30 napra és az összes közelgő; /export 90 — 90 napra.",
        "adm_export_empty": "Erre az időszakra nincs foglalás.",
        "adm_export_caption": "📊 Foglalások {start} óta (és az összes közelgő): {count}",
        "adm_export_headers": "Dátum|Idő|Vége|Fodrász|Szolgáltatás|Ár|Állapot|Vendég|Telefon|Telegram|Forrás|Előleg|Megjegyzés|Létrehozva",
        "adm_export_sheet": "Foglalások",
        "adm_export_statuses": "tervezett|megtörtént|nem jelent meg|lemondva",
        "adm_export_sources": "vendég|AI-chat|admin",
        "adm_export_prepay": "várakozik|a vendég szerint fizetett|fizetve",
        "adm_master_revenue": "\n   {name}: {count} · {revenue}",
        "adm_evening_report": "🌙 <b>Napi összesítő · {day}</b>\n\n✅ Megtörtént: {done} · 🚫 meg nem jelenés: {noshow} · ❌ lemondva: {cancelled}\n💰 Bevétel: <b>{revenue}</b>{by_master}\n\n📅 Holnapi foglalások: {tomorrow}",
        "client_rescheduled_by_admin": "🔁 Az adminisztrátor áthelyezte a foglalását:\n💈 {service} · {master}\nEddig: {old}\nMost: <b>{new}</b>\n\nHa az időpont nem megfelelő, módosítsa a «🗓 Foglalásaim» menüpontban, vagy írjon nekünk.",
        "adm_booking_summary": "<b>{day}, {start}–{end}</b> · {master}\n💈 {service}\n👤 {client}",
        "adm_noshow_done": "🚫 {client} ({time}) — nem jelent meg",
        "adm_cancel_ask": "Lemondja a foglalást?\n\n{booking}\n\n{who}",
        "adm_cancel_notify": "A vendég Telegram-üzenetet kap.",
        "adm_cancel_offline": "A vendég nincs a Telegramon — értesítse Ön.",
        "adm_cancelled_done": "🗑 <b>Lemondva</b>\n\n{booking}\n\nA vendég értesítést kapott.",
        "adm_cancelled_done_offline": "🗑 <b>Lemondva</b>\n\n{booking}\n\nA vendég nincs a Telegramon — értesítse Ön.",
        "adm_cancelled_header": "\n\n➖➖➖\n❌ <b>Lemondva</b> — {count}",
        "adm_cancelled_item": "\n{day} {start} · {master} · {service} · {client} — {by}",
        "adm_cancelled_by_client": "a vendég mondta le",
        "adm_cancelled_by_admin": "az adminisztrátor mondta le",
        "adm_new_booking_prepay": "\n💳 Várjuk az előleget ({amount}), határidő: {deadline}",
        "adm_prepay_claim_note": "💳 <b>A vendég szerint fizetett</b>\n\n{booking}\n\nEllenőrizze, megérkezett-e a(z) {amount}, és erősítse meg 👇",
        "adm_prepay_screenshot": "💳 <b>A vendég fizetési képernyőképet küldött</b> (fent)\n\n{booking}\n\nEllenőrizze, megérkezett-e a(z) {amount}, és erősítse meg 👇",
        "adm_prepay_overdue": "⏰ <b>A fizetés még nincs megerősítve</b>\nA vendég {hours} órával ezelőtt jelezte, hogy fizetett. Kérjük, ellenőrizze: az ilyen foglalások nem törlődnek automatikusan.\n\n{booking}",
        "btn_adm_prepay_ok": "✅ A fizetés megérkezett",
        "btn_adm_cancel_booking": "🗑 Foglalás lemondása",
        "adm_prepay_ok_done": "✅ <b>Az előleg megerősítve</b>, a vendég értesítést kapott.\n\n{booking}",
        "adm_prepay_ok_alert": "✅ Fizetés megerősítve",
        "adm_prepay_already": "Az előleg már megerősítve.",
        "adm_prepay_waiting": "\n💳 ⏳ előlegre vár",
        "adm_prepay_claimed": "\n💳 ❔ a vendég szerint fizetett — kérjük, ellenőrizze",
        "adm_prepay_paid": "\n💳 ✅ az előleg megérkezett",
        "adm_cancelled_by_unpaid": "nem fizetett",
        "adm_cancelled_unpaid": "⏰ <b>A foglalás automatikusan törölve</b> — az előleg nem érkezett meg {hours} órán belül.\n\n{booking}",
        "btn_adm_clear_cancelled": "🧹 Lemondottak törlése ({count})",
        "adm_clear_ask": "Eltávolítja a lemondott foglalásokat a listából ({count})?\nAz /all parancs már nem mutatja őket, de a statisztikában megmaradnak.",
        "btn_adm_yes_clear": "Igen, törlöm",
        "adm_cleared_done": "🧹 Lemondott foglalások törölve: {count}. Frissített lista — /all",
        "btn_adm_yes_cancel": "Igen, lemondom",
        "client_cancelled_by_admin": "Sajnos az adminisztrátor lemondta a foglalását:\n💈 {service} · {master}\n"
                                     "📅 {day}, {time}\n\nKérjük, válasszon másik időpontot — «📅 Időpontfoglalás» — vagy írjon nekünk.",
        "adm_week_header": "🗓 <b>Foglalások 7 napra</b>",
        "adm_week_empty": "\n\nNincs foglalás.",
        "adm_week_more": "\n\n➕ további {count} később — /all",
        "adm_all_header": "🗓 <b>Az összes közelgő foglalás</b>",
        "adm_note_line": "\n📝 {note}",
        "adm_via_admin": " · adminisztrátor foglalta 📞",
        "btn_adm_book_confirm": "✅ Foglalás",
        "btn_adm_book_cancel": "✖️ Mégse",
        "adm_book_service": "📞 <b>Vendég foglalása</b>\nVálasszon szolgáltatást:",
        "adm_book_group": "📞 <b>Vendég foglalása</b>\nVálasszon kategóriát — utána szolgáltatás, fodrász, nap és időpont 👇",
        "adm_book_in_group": "📞 <b>{group}</b>\nVálasszon szolgáltatást — utána fodrász, nap és időpont 👇",
        "adm_book_master": "📞 {service}\nVálasszon fodrászt:",
        "adm_book_day": "📞 {service} · {master}\nVálasszon napot:",
        "adm_book_time": "📞 {service} · {master} · {day}\nVálasszon időpontot:",
        "adm_book_no_days": "{master} nem rendelkezik szabad nappal ehhez: «{service}». Válasszon másik fodrászt:",
        "adm_book_client_prompt": "📞 {service} · {master} · {day}, {time}\n\n"
                                  "Küldje el a vendég adatait egy üzenetben: <b>név</b> és <b>telefonszám</b>, "
                                  "megjegyzés új sorban (nem kötelező). Például:\n"
                                  "<code>Éva +36301234567\nrövidebbre kéri, mint legutóbb</code>\n\n"
                                  "Vagy ossza meg a vendég Telegram-névjegyét (📎 → Névjegy).\n/cancel — mégse.",
        "adm_book_need_name": "Nem látom a vendég nevét. Küldje el újra: név, telefonszám, megjegyzés új sorban.",
        "adm_book_card": "📞 <b>Ellenőrizze a foglalást</b>\n\n👤 {client}\n💈 {service} · {master}\n📅 {day}, {time}\n"
                         "💰 {price}{note}\n\n{hint}\n\nAz adatok módosításához egyszerűen küldje el őket újra.",
        "adm_book_hint_tg": "✉️ A vendég már használja a botot ({client}) — üzenetet és emlékeztetőket kap.",
        "adm_book_hint_known": "🗂 A vendég már szerepel az adatbázisban ({client}), de nincs a Telegramon — üzenetet nem kap.",
        "adm_book_hint_offline": "📵 Új vendég Telegram nélkül — nem kap üzenetet és emlékeztetőt.",
        "adm_book_duplicate": "A vendégnek már van foglalása erre az időpontra (#{id}).",
        "adm_book_done": "✅ <b>Lefoglalva</b> <code>#{id}</code>\n👤 {client}\n💈 {service} · {master}\n"
                         "📅 {day}, {time}{notified}",
        "adm_book_notified": "\n\n✉️ A vendég Telegram-üzenetet kapott.",
        "adm_book_not_notified": "\n\n📵 A vendég nem kapott üzenetet (nincs a Telegramon) — szükség esetén hívja fel.",
        "adm_book_aborted": "A foglalás nem jött létre.",
        "client_booked_by_admin": "📞 Az adminisztrátor lefoglalta Önnek:\n💈 {service} · {master}\n📅 {day}, {time}\n💰 {price}\n\n"
                                  "Áthelyezéshez vagy lemondáshoz — «🗓 Foglalásaim».",
        "adm_block_usage": "🔒 <b>Idő blokkolása</b>\n\nFormátum: <code>/block fodrász dátum [idő] [megjegyzés]</code>\n\n"
                           "Példák:\n<code>/block {example} 30.10</code> — egész nap\n"
                           "<code>/block {example} 30.10 14:00-16:00 telefonos foglalás</code>\n"
                           "<code>/block mind 31.12</code> — szabadnap mindenkinek\n\nFodrászok: {masters}",
        "adm_block_bad": "Nem értettem a parancsot 🤔\n\n{usage}",
        "adm_block_done": "🔒 Blokkolva: {master}, {day} {range}{note}",
        "adm_block_conflicts": "\n\n⚠️ Erre az időpontra vannak foglalások — mondja le őket (/today, /tomorrow), vagy figyelmeztesse a vendégeket:{lines}",
        "adm_all_masters": "minden fodrász",
        "adm_whole_day": "(egész nap)",
        "adm_blocks_header": "🔒 <b>Blokkolt idők</b> (koppintson a törléshez):",
        "adm_blocks_empty": "Nincs blokkolt idő.",
        "btn_adm_block_item": "🗑 {master} · {day} {range}",
        "adm_block_deleted": "🔓 Törölve. Ez az idő ismét foglalható.",
        "adm_paused": "⏸ Az AI ki van kapcsolva. Minden vendégüzenet Önhöz kerül; a foglalási gombok továbbra is működnek.\n"
                      "Bekapcsolás: /resume",
        "adm_resumed_all": "▶️ Az AI újra válaszol a vendégeknek.",
        "adm_reloaded": "🔄 Beállítások újratöltve: szolgáltatások — {services}, fodrászok — {masters}.",
        "adm_reload_failed": "❌ Hiba van a beállítások fájljában, a korábbi beállítások maradnak érvényben:\n<code>{error}</code>",
        "adm_reload_token": "\n⚠️ A bot tokenje megváltozott — az érvényesítéshez indítsa újra a botot.",
        "adm_digest": "☀️ <b>Jó reggelt!</b>\n\n{body}",
        "adm_ai_alert": "⚠️ <b>Az AI nem válaszol</b> ({name})\n<code>{error}</code>\n\n"
                        "A bot gombokkal tovább működik. Ellenőrizze az API-kulcsot és az egyenleget a console.anthropic.com oldalon.",
        "adm_budget_alert": "⚠️ Elérte a napi AI-limitet ({name}). A nap végéig a bot csak gombokkal működik. "
                            "A limitet a settings.toml fájlban módosíthatja (daily_token_limit).",
        "adm_stats": "📊 <b>Statisztika {days} napra</b>\n\n"
                     "<b>Foglalások</b>\n"
                     "• létrehozva: {created} (AI-chat: {by_ai}, gombok: {by_buttons}, admin: {by_admin})\n"
                     "• éjszaka (22:00–08:00): {night}\n"
                     "• teljesült: {done} · meg nem jelenés: {noshow} · lemondva: {cancelled}\n"
                     "• közelgő: {upcoming}\n\n"
                     "<b>Bevétel</b>\n"
                     "• {revenue} · átlagos számla {avg_check}{by_master}\n"
                     "• a közelgő foglalásokból várható: {expected}\n\n"
                     "<b>Beszélgetések</b>\n"
                     "• üzenetet író vendégek: {clients}\n"
                     "• Önnek átadva: {handoffs}\n"
                     "• a bot önállóan kezelte: {auto_rate}\n\n"
                     "<b>Emlékeztetők</b>\n"
                     "• elküldve: {reminders} · «Ott leszek»: {confirmed}\n\n"
                     "<b>AI</b>\n"
                     "• kezelt üzenetek: {ai_calls} · tokenek: {tokens}\n"
                     "• becsült költség: ${cost}",
        "adm_client_noname": "Vendég",
        "cmd_start": "Főmenü",
        "cmd_admin": "Tulajdonosi pult",
        "cmd_today": "Mai foglalások",
        "cmd_tomorrow": "Holnapi foglalások",
        "cmd_book": "Vendég foglalása",
        "cmd_day": "Foglalások egy napra",
        "cmd_find": "Vendég keresése",
        "cmd_export": "Exportálás Excelbe",
        "cmd_week": "Foglalások 7 napra",
        "cmd_all": "Az összes közelgő foglalás",
        "cmd_stats": "Statisztika",
        "cmd_block": "Idő blokkolása",
        "cmd_blocks": "Blokkolt idők",
        "cmd_pause": "AI kikapcsolása",
        "cmd_resume": "AI bekapcsolása",
        "cmd_reload": "Beállítások újratöltése",
        "cmd_myid": "Az én Telegram-azonosítóm",
        "cmd_masters": "Fodrászok a botban",
        "cmd_prices": "Árak módosítása",
        "adm_prices": "💰 <b>Szolgáltatások árai</b>\nAz ár módosításához koppintson egy szolgáltatásra 👇",
        "adm_prices_changed": "\n\n✏️ — az ár itt, a botban módosult (a beállítások fájljában még a régi szerepel).",
        "adm_price_ask": "💰 <b>{title}</b>\nJelenleg: <b>{price}</b>\n\nKüldje el az új árat számként, pl. 650.",
        "adm_price_file": "\nA beállítások fájljában: {price}.",
        "btn_adm_price_reset": "↩️ Visszaállítás: {price}",
        "adm_price_bad": "Ez nem tűnik árnak 🤔 Csak egy számot küldjön, pl. 650. Mégse — /cancel",
        "adm_price_done": "✅ <b>{title}</b>: {old} → <b>{new}</b>\nA vendégek és az AI már az új árat látják. "
                          "A korábbi foglalások a régi árat tartják meg.",
        "adm_price_combos": "\nA kiegészítőkkel kombinált árak újraszámolva.",
        "adm_price_changed_note": "💰 {admin} módosította az árat: <b>{title}</b> {old} → <b>{new}</b>",
        "cmd_my": "Az én napom",
        "cmd_myweek": "Az én hetem",
        "cmd_off": "Idő blokkolása",
        "cmd_offs": "Blokkolt időim",
        # Fodrászok: admin
        "adm_masters": "✂️ <b>Fodrászok a botban</b>\n\nA csatlakoztatott fodrász látja a saját foglalásait, blokkolhatja a "
                       "saját idejét, és értesítést kap a vendégeiről.\n{items}",
        "adm_masters_on": "\n✅ <b>{name}</b> — {who}",
        "adm_masters_off": "\n⚪️ <b>{name}</b> — nincs csatlakoztatva",
        "btn_adm_master_invite": "🔗 Meghívás: {name}",
        "btn_adm_master_unlink": "✖️ Leválasztás: {name}",
        "btn_adm_yes_unlink": "✖️ Igen, leválasztom",
        "btn_adm_open": "📋 Foglalás megnyitása",
        "adm_master_invite": "🔗 Hivatkozás <b>{name}</b> fodrász számára:\n\n{link}\n\nKüldje tovább a fodrásznak — "
                             "megnyitja, és megnyomja a «Start» gombot. Egyszer használható hivatkozás, {hours} óráig érvényes.",
        "adm_master_no_username": "Nem sikerült lekérni a bot címét. Kérjük, próbálja újra egy perc múlva.",
        "adm_master_unlink_ask": "Leválasztja <b>{name}</b> fodrászt a botról? Nem fogja látni a foglalásokat, "
                                 "és nem kap értesítéseket.",
        "adm_master_unlinked": "✖️ {name} fodrász leválasztva a botról.",
        "adm_master_joined": "✂️ <b>{name}</b> fodrász csatlakozott a bothoz ({who}).",
        "adm_master_noshow": "🚫 <b>{master} fodrász meg nem jelenést jelölt</b>\n\n{booking}",
        "adm_master_off": "🌴 <b>{master}</b> fodrász blokkolt egy időt: {day} {range}",
        "adm_master_off_conflicts": "\n\n⚠️ <b>Erre az időpontra vannak foglalások</b> — egyeztessen "
                                    "a vendégekkel (áthelyezés vagy lemondás):{lines}",
        "adm_master_on": "🔓 <b>{master}</b> fodrász feloldott egy időt: {day} {range}",
        # Fodrászok: a fodrász
        "mst_invite_bad": "Ez a hivatkozás érvénytelen vagy már felhasználták. Kérjen újat az adminisztrátortól.",
        "mst_joined": "✅ <b>Csatlakozott „{name}” fodrászként.</b>\n\n",
        "mst_start": "✂️ <b>{name}</b>, Ön fodrász a(z) „{shop}” botban.\n\n"
                     "📅 <b>Az én napom</b> — a foglalásai, napok közti lapozás ◀️ ▶️\n"
                     "🗓 <b>Az én hetem</b> — foglalások 7 napra\n"
                     "🌴 <b>Idő blokkolása</b> — szabadnap, szünet, személyes ügyek\n"
                     "🔒 <b>Blokkolt időim</b> — megtekintés és feloldás\n\n"
                     "A bot értesíti az új foglalásokról, lemondásokról és áthelyezésekről, reggel elküldi a "
                     "beosztását, és minden vendég előtt emlékezteti.",
        "mst_unlinked": "Leválasztottuk a botról fodrászként. Vendégként továbbra is foglalhat 👇",
        "btn_mst_day": "📅 Az én napom",
        "btn_mst_week": "🗓 Az én hetem",
        "btn_mst_off": "🌴 Idő blokkolása",
        "btn_mst_offs": "🔒 Blokkolt időim",
        "btn_mst_to_day": "⬅️ Vissza a naphoz",
        "mst_day_hint": "\n\nA foglalás kártyájának megnyitásához koppintson rá 👇",
        "mst_day_off": "\n\n🌴 A beosztása szerint szabadnap.",
        "mst_day_blocks": "\n\n🔒 Blokkolva: {ranges}",
        "mst_week_header": "🗓 <b>Foglalásai 7 napra</b>",
        "mst_off_day": "🌴 <b>Idő blokkolása</b>\n\nVálasszon napot:",
        "mst_off_range": "🌴 <b>{day}</b> · munkaideje: {hours}\n\nAz egész napot blokkolja, vagy mettől?",
        "mst_off_whole_only": "🌴 <b>{day}</b> · {hours}\n\nBlokkolja az egész napot?",
        "mst_off_no_work": "beosztás szerint szabadnap",
        "mst_off_end": "🌴 <b>{day}</b>, {start}-tól\n\nMeddig?",
        "btn_mst_whole_day": "🌴 Egész nap",
        "btn_mst_off_yes": "✅ Blokkolás",
        "mst_off_confirm": "Blokkolja: <b>{day} {range}</b>?\nA vendégek ezt az időt nem tudják lefoglalni.{conflicts}",
        "mst_off_conflicts": "\n\n⚠️ Erre az időpontra vannak foglalások — az adminisztrátor értesítést kap, "
                             "hogy egyeztessen a vendégekkel:{lines}",
        "mst_off_done": "🔒 Blokkolva: <b>{day} {range}</b>. A vendégek ezt az időt nem tudják lefoglalni.",
        "mst_off_done_conflicts": "\n\n⚠️ Erre az időpontra még vannak foglalások — az adminisztrátort értesítettük:{lines}",
        "mst_offs_header": "🔒 <b>Blokkolt időim</b>\nA feloldáshoz koppintson:",
        "mst_offs_header_none": "🔒 <b>Blokkolt időim</b>",
        "mst_offs_admin": "\n\nAz adminisztrátor blokkolta (csak ő módosíthatja):{lines}",
        "mst_offs_empty": "🔒 Nincs blokkolt idő. Blokkoláshoz — „🌴 Idő blokkolása”.",
        "btn_mst_block_item": "🗑 {label}",
        "alert_mst_opened": "Az idő ismét foglalható",
        "mst_new": "🆕 <b>Új foglalás Önhöz</b>\n\n📅 {day}, {time}\n💈 {service}\n👤 {client}",
        "mst_cancelled": "❌ <b>Foglalás lemondva</b>\n\n📅 {day}, {time}\n💈 {service}\n👤 {client}",
        "mst_moved": "🔁 <b>A foglalás másik fodrászhoz került</b>\n\n📅 {day}, {time}\n💈 {service}\n👤 {client}",
        "mst_rescheduled": "🔁 <b>Foglalás áthelyezve</b>\n\n💈 {service}\n👤 {client}\nEddig: {old}\nMost: <b>{new}</b>",
        "mst_digest": "☀️ <b>Jó reggelt, {name}!</b>\n\n{body}",
        "mst_heads_up": "⏰ <b>{time}-kor</b> ({min} perc múlva) — {client}\n💈 {service}",
    },

    # ------------------------------------------------------------------ DE
    "de": {
        # Kundenmenü
        "btn_book": "📅 Termin buchen",
        "btn_my": "🗓 Meine Termine",
        "btn_prices": "💈 Leistungen & Preise",
        "btn_contacts": "📍 Kontakt",
        "btn_webapp": "📅 Online buchen",
        "webapp_invite": "Wählen Sie Leistung, Stylist und Termin im Buchungsfenster 👇",
        "start": "Hallo! 👋 Ich bin der Buchungsassistent von <b>{name}</b>.\n\n"
                 "Ich helfe Ihnen, einen Termin zu buchen, zu verschieben oder abzusagen, und beantworte Ihre Fragen.\n\n"
                 "Wählen Sie eine Option im Menü 👇 oder schreiben Sie einfach Ihre Frage.",
        "start_no_ai": "Hallo! 👋 Ich bin der Buchungsassistent von <b>{name}</b>.\n\n"
                       "Ich helfe Ihnen, einen Termin zu buchen, zu verschieben oder abzusagen.\nWählen Sie eine Option im Menü 👇",
        "start_admin_hint": "\n\n🛠 Sie sind Administrator dieses Bots. Verwaltung: /admin",
        # Buchung mit Buttons
        "choose_service": "Wählen Sie eine Leistung:",
        "choose_group": "✨ Wählen Sie eine Kategorie — danach finden wir einen Stylisten und eine passende Zeit für Sie 👇",
        "choose_service_in_group": "<b>{group}</b>\nWählen Sie eine Leistung — danach finden wir einen Stylisten und eine passende Zeit für Sie 👇",
        "btn_service": "{title} · {price}",
        "choose_master": "💈 <b>{service}</b>\n💰 {price} · ⏱ {duration} Min.{description}\n\nWählen Sie einen Stylisten 👇",
        "master_service_desc": "\n<i>{description}</i>",
        "btn_any_master": "👥 Beliebiger Stylist",
        "any_master": "beliebiger Stylist",
        "choose_day": "💈 <b>{service}</b> · {master}\n\nWählen Sie einen Tag:",
        "no_days": "💈 <b>{service}</b> · {master}\n\nLeider gibt es in den nächsten {days} Tagen keine freien Termine 😕\n"
                   "Schreiben Sie uns, wir versuchen eine Lösung zu finden.",
        "choose_time": "💈 <b>{service}</b> · {master}\n📅 {day}\n\nWählen Sie eine Uhrzeit:",
        "no_times": "📅 {day}: keine freien Zeiten mehr. Bitte wählen Sie einen anderen Tag:",
        "btn_back": "⬅️ Zurück",
        "day_today": "Heute",
        "day_tomorrow": "Morgen",
        "card": "📝 <b>Bitte prüfen Sie:</b>\n\n💈 {service}\n👤 Stylist: {master}\n"
                "📅 {day} um {time}\n⏱ {duration} Min. · 💰 {price}",
        "btn_confirm": "✅ Bestätigen",
        "btn_add_addon": "➕ {title} (+{duration} Min., +{price})",
        "btn_other_time": "⬅️ Andere Zeit",
        "btn_no_change": "✖️ Nein, ändern",
        "ask_phone": "Zum Schluss noch Ihre Telefonnummer, damit der Stylist Sie erreichen kann.\n\n"
                     "Tippen Sie unten auf <b>«📱 Nummer teilen»</b> oder schreiben Sie Ihre Nummer als Nachricht.",
        "btn_share_phone": "📱 Nummer teilen",
        "btn_cancel": "Abbrechen",
        "bad_phone": "Das sieht nicht nach einer Telefonnummer aus 🤔\nTippen Sie auf «📱 Nummer teilen» "
                     "oder schreiben Sie die Nummer mit Ländervorwahl, z. B. +4915112345678.",
        "phone_saved": "Danke, die Nummer ist gespeichert 👍",
        "booking_aborted": "In Ordnung, es wurde kein Termin gebucht. Falls Sie es sich anders überlegen — «📅 Termin buchen».",
        "booked": "✅ <b>Fertig, Ihr Termin ist gebucht!</b>\n\n💈 {service}\n👤 {master}\n📅 {day} um {time}\n💰 {price}{address}\n\n"
                  "Ich erinnere Sie rechtzeitig. Verschieben oder absagen — unter «🗓 Meine Termine».",
        "booked_address": "\n📍 {address}",
        "prepay_block": "\n\n💳 <b>Um Ihren Termin zu sichern — Anzahlung {amount}</b>\nKarte: <code>{card}</code>{recipient}\nBitte zahlen Sie bis <b>{deadline}</b>, sonst wird der Termin automatisch storniert. Die Anzahlung wird auf den Preis angerechnet.\n\nTippen Sie nach der Zahlung auf «✅ Ich habe bezahlt» oder senden Sie hier einen Screenshot 👇",
        "prepay_recipient": "\nEmpfänger: {recipient}",
        "btn_prepay_done": "✅ Ich habe bezahlt",
        "btn_prepay_done_item": "✅ Ich habe bezahlt {short}",
        "prepay_claimed_client": "Danke! 🙏 Der Administrator prüft die Zahlung und bestätigt Ihren Termin — wir melden uns hier.",
        "prepay_screenshot_client": "Danke, Screenshot erhalten! 🙏 Der Administrator prüft die Zahlung und bestätigt Ihren Termin — wir melden uns hier.",
        "prepay_photo_ask": "📸 Ist das ein Screenshot Ihrer Anzahlung?",
        "btn_photo_is_payment": "✅ Ja, das ist die Zahlung",
        "btn_photo_other": "Nein, etwas anderes",
        "prepay_already_paid": "Die Anzahlung ist bereits bestätigt ✅",
        "prepay_paid_client": "✅ <b>Anzahlung erhalten — Ihr Termin ist bestätigt!</b>\n💈 {service} · {master}\n📅 {day} um {time}\n\nWir freuen uns auf Sie 💛",
        "client_cancelled_unpaid": "😔 Leider wurde Ihr Termin storniert: Die Anzahlung ist nicht rechtzeitig eingegangen.\n💈 {service} · {master}\n📅 {day} um {time}\n\nWenn es noch passt, buchen Sie gern erneut — wir freuen uns auf Sie 💛",
        "my_prepay_waiting": "\n💳 Anzahlung {amount} ausstehend bis {deadline}",
        "my_prepay_claimed": "\n💳 Wir prüfen Ihre Zahlung ⏳",
        "my_prepay_paid": "\n💳 Anzahlung erhalten ✅",
        "already_booked": "✅ Sie haben für diese Zeit bereits einen Termin.",
        "slot_taken": "Oh, diese Zeit wurde gerade vergeben 😕 Bitte wählen Sie eine andere:",
        "week_limit": "Sie haben diese Woche bereits die maximale Anzahl von {limit} Terminen 🙏\nWählen Sie eine andere Woche oder verschieben Sie einen Ihrer Termine.",
        "too_many_active": "Sie haben bereits {count} aktive Termine — das ist das Maximum. "
                           "Verschieben oder stornieren Sie einen unter «🗓 Meine Termine».",
        "booking_error": "Der Termin konnte nicht gebucht werden 😕 Bitte versuchen Sie es erneut oder schreiben Sie uns.",
        "proposal_declined": "In Ordnung 🙂 Schreiben Sie, was ich ändern soll, und ich finde eine andere Option.",
        # Meine Termine
        "my_none": "Sie haben noch keine anstehenden Termine 🙂\nZeit, das zu ändern — wählen Sie eine passende Zeit 👇",
        "my_header": "✨ <b>Ihre Termine</b> ✨",
        "my_item": "\n\n📅 <b>{day} um {time}</b>\n✂️ {service}\n💈 Stylist: {master}",
        "my_footer": "\n\n💛 Wir freuen uns auf Sie! Kommen Sie ein paar Minuten früher, um anzukommen "
                     "und sich auf Ihren neuen Look einzustimmen ✨\n\nWenn sich Ihre Pläne ändern, verschieben oder stornieren "
                     "Sie den Termin mit den Buttons unten 👇",
        "btn_resched_item": "🔁 Verschieben {short}",
        "btn_cancel_item": "❌ Stornieren {short}",
        "cancel_ask": "Diesen Termin stornieren?\n\n💈 {service} · {master}\n📅 {day} um {time}",
        "btn_yes_cancel": "Ja, stornieren",
        "btn_no": "Nein",
        "cancel_kept": "In Ordnung, der Termin bleibt bestehen ✅",
        "cancelled": "Termin storniert.\nWir hoffen, Sie ein anderes Mal zu sehen! Neu buchen — «📅 Termin buchen».",
        "cancel_too_late": "Bis zu Ihrem Termin sind es weniger als {hours} Std., daher ist eine Online-Stornierung nicht mehr möglich. "
                           "Bitte rufen Sie uns an{phone}.",
        "cancel_too_late_phone": ": {phone}",
        "booking_inactive": "Dieser Termin ist nicht mehr aktiv.",
        "resched_choose_day": "🔁 <b>Verschieben</b>\n💈 {service} · {master}\nAktuell: {day} um {time}\n\nWählen Sie einen neuen Tag:",
        "resched_choose_time": "🔁 <b>Verschieben</b>\n💈 {service} · {master}\n📅 {day}\n\nWählen Sie eine neue Uhrzeit:",
        "resched_card": "🔁 <b>Termin verschieben?</b>\n\n💈 {service} · {master}\nBisher: {old}\nNeu: <b>{new}</b>",
        "btn_confirm_resched": "✅ Verschieben",
        "rescheduled": "✅ Termin verschoben.\n\n💈 {service} · {master}\n📅 <b>{day} um {time}</b>",
        "resched_none": "In den nächsten {days} Tagen gibt es keine freien Termine 😕 Schreiben Sie uns, wir finden eine Lösung.",
        # Informationen
        "prices_header": "💈 <b>{name}</b>\n✨ <b>LEISTUNGEN &amp; PREISE</b> ✨\n<i>Wählen Sie, was Ihnen gefällt — mit dem Button unten können Sie sofort buchen 👇</i>",
        "price_group": "\n\n━━━━━━━━━━━━\n<b>{group}</b>",
        "price_item": "\n\n<b>{title}</b> — {price}\n⏱ {duration} Min.",
        "price_desc": "\n{description}",
        "prices_addons_header": "\n\n➕ <b>Zusatzleistungen</b> (per Button bei der Buchung)",
        "price_addon_item": "\n{title} — +{price}, +{duration} Min.",
        "contacts_header": "📍 <b>{name}</b>",
        "contacts_address": "\n\n🏠 {address}",
        "contacts_phone": "\n📞 {phone}",
        "contacts_hours": "\n\n🕒 <b>Öffnungszeiten</b>\n{hours}",
        "contacts_directions": "\n\n🚗 {directions}",
        "contacts_payment": "\n💳 {payment}",
        "contacts_prepay": "\n💳 Anzahlung {amount} — die Zahlungsdaten senden wir direkt nach der Buchung (zahlbar innerhalb von {hours} Std.).",
        "contacts_masters_header": "\n\n━━━━━━━━━━━━\n👥 <b>Unser Team</b>",
        "contacts_master": "\n\n💈 <b>{name}</b>{about}\n🗓 {schedule}",
        "contacts_master_about": "\n<i>{about}</i>",
        "btn_map": "🗺 Auf der Karte öffnen",
        "day_off": "geschlossen",
        # Erinnerungen
        "reminder": "⏰ <b>Terminerinnerung</b>\n\n📅 {day} um {time}\n💈 {service} · {master}{address}",
        "btn_will_come": "✅ Ich komme",
        "btn_resched": "🔁 Verschieben",
        "btn_cancel_booking": "❌ Stornieren",
        "will_come_ok": "\n\n✅ Super, bis bald!",
        "nudge": "Hallo, {name}! 👋\nIhr letzter Besuch ({service}) ist schon {weeks} Wochen her. "
                 "Soll ich Ihnen wieder einen Termin buchen?",
        "btn_book_again": "📅 Termin buchen",
        "btn_no_nudges": "🔕 Nicht mehr erinnern",
        "nudges_off": "In Ordnung, ich erinnere Sie nicht mehr 🙂",
        # KI und Übergabe an einen Menschen
        "ai_off": "Bitte wählen Sie eine Option im Menü 👇 — so geht es am schnellsten.",
        "ai_error": "Entschuldigung, ich kann gerade nicht antworten 😔\nBitte nutzen Sie die Menü-Buttons 👇 oder versuchen Sie es etwas später.",
        "ai_refusal": "Entschuldigung, dabei kann ich nicht helfen 🙂 Ich kann Ihnen einen Termin buchen oder Ihre Frage an den Administrator weiterleiten.",
        "rate_limited": "Zu viele Nachrichten in kurzer Zeit 🙈 Bitte nutzen Sie die Menü-Buttons 👇 oder schreiben Sie etwas später.",
        "handoff_client": "Ich habe Ihre Frage an den Administrator weitergeleitet — die Antwort kommt hier in diesem Chat 🙌",
        "handoff_no_admin": "Mit dieser Frage wenden Sie sich am besten direkt an den Administrator{phone} 🙏",
        "media_received": "Erhalten 👍 Ich leite es an den Administrator weiter — die Antwort kommt hier in diesem Chat.",
        "voice_unsupported": "Sprachnachrichten kann ich leider noch nicht anhören 🙈 Bitte schreiben Sie Ihre Nachricht.",
        "unsupported": "Ich verstehe nur Textnachrichten 🙂",
        "meta_choose_lang": "🌐 Wählen Sie Ihre Sprache:",
        "btn_language": "🌐 Sprache",
        "paused_ack": "Danke für Ihre Nachricht! Der Administrator antwortet in Kürze.",
        "admin_title": "Administrator",
        "admin_reply_to_client": "👤 <b>{title}:</b>\n{text}",
        "alert_expired": "Dieser Button ist nicht mehr aktuell. Bitte beginnen Sie von vorn.",
        "alert_no_access": "Kein Zugriff",
        "unknown_command": "Diesen Befehl kenne ich nicht 🤔 Bitte wählen Sie eine Option im Menü 👇",
        "myid": "Ihre Telegram-ID: <code>{id}</code>",
        "state_cleared": "Abgebrochen.",
        # Admin
        "admin_help": "🛠 <b>Verwaltung · {name}</b>\n\n"
                      "/book — Kunden eintragen (Anruf, Laufkundschaft)\n"
                      "/today — Termine heute\n"
                      "/tomorrow — Termine morgen\n"
                      "/day 30.10 — Termine an einem beliebigen Datum\n"
                      "/week — Termine für 7 Tage\n"
                      "/all — alle anstehenden Termine\n"
                      "/find — Kunden suchen (Name, @Benutzername oder Telefon)\n"
                      "/stats — Statistik und Umsatz für 30 Tage (/stats 7 — für 7)\n"
                      "/export — Termine nach Excel exportieren\n"
                      "/block — Zeit sperren (freier Tag, Urlaub, telefonische Buchung)\n"
                      "/blocks — Liste der gesperrten Zeiten\n"
                      "/masters — Stylisten im Bot: einladen, trennen\n"
                      "/prices — Preise der Leistungen ändern\n"
                      "/pause — KI ausschalten: alle Kundennachrichten gehen an Sie\n"
                      "/resume — KI wieder einschalten\n"
                      "/reload — Einstellungen aus der Datei neu laden\n"
                      "/myid — Ihre Telegram-ID\n\n"
                      "💬 Um einem Kunden zu antworten, antworten Sie (nach links wischen → «Antworten») auf seine vom Bot weitergeleitete Nachricht.\n\n"
                      "KI-Antworten: {ai_status}",
        "ai_status_on": "✅ an",
        "ai_status_paused": "⏸ pausiert (/resume)",
        "ai_status_nokey": "⚪️ aus (kein API-Schlüssel in settings.toml)",
        "ai_status_disabled": "⚪️ in den Einstellungen des Geschäfts ausgeschaltet",
        "adm_new_booking": "🆕 <b>Neuer Termin</b>{via}\n\n👤 {client}\n💈 {service} · {master}\n📅 {day} um {time}\n💰 {price}",
        "adm_via_ai": " · über den KI-Chat 🤖",
        "adm_via_web": " · über Online-Buchung 📲",
        "adm_cancelled": "❌ <b>Stornierung</b>\n\n👤 {client}\n💈 {service} · {master}\n📅 {day} um {time}",
        "adm_rescheduled": "🔁 <b>Verschoben</b>\n\n👤 {client}\n💈 {service} · {master}\nBisher: {old}\nJetzt: <b>{new}</b>",
        "adm_handoff": "🙋 <b>Ihre Antwort wird benötigt</b>\n\n👤 {client}\n❓ {reason}{summary}\n\n"
                       "<b>Letzte Nachrichten:</b>\n{transcript}\n\n"
                       "↩️ Antworten Sie auf diese Nachricht (nach links wischen) — der Bot leitet Ihre Antwort an den Kunden weiter. "
                       "Die KI ist für diesen Kunden {hours} Std. pausiert.",
        "adm_handoff_summary": "\n📝 {summary}",
        "adm_reason_media": "Der Kunde hat ein Foto oder eine Datei gesendet (vielleicht eine Zahlung)",
        "adm_tr_client": "— Kunde: {text}",
        "adm_tr_bot": "— Bot: {text}",
        "adm_tr_empty": "(keine)",
        "btn_adm_reply": "✍️ Antworten",
        "btn_adm_resume": "▶️ Bot fortsetzen",
        "adm_client_msg": "💬 <b>{client}</b>:\n{text}",
        "adm_client_media": "💬 {client}",
        "adm_reply_prompt": "Schreiben Sie Ihre Antwort an {client} in einer Nachricht (oder /cancel):",
        "adm_reply_sent": "✅ Gesendet: {client}",
        "adm_reply_failed": "⚠️ Senden fehlgeschlagen — der Kunde hat den Bot möglicherweise blockiert.",
        "adm_resumed": "▶️ Die KI antwortet wieder: {client}",
        "adm_day_header": "📅 <b>{day}</b>{master} — Termine: {count}",
        "adm_day_empty": "📅 <b>{day}</b>{master} — keine Termine.",
        "adm_item": "\n\n<b>{n}. {start}–{end}</b> · {master}\n💈 {service}\n👤 {client}{flags}",
        "adm_list_day": "\n\n📅 <b>{day}</b> — Termine: {count}",
        "adm_list_hint": "\n\nTippen Sie auf einen Termin, um ihn zu verschieben, zu stornieren oder die Zahlung zu markieren 👇",
        "adm_day_master": " · {name}",
        "adm_day_hint": "\n\nTippen Sie auf einen Termin, um ihn zu verschieben, zu stornieren, ein Nichterscheinen oder die Zahlung zu markieren 👇",
        "adm_day_pick": "📅 Wählen Sie einen Tag:",
        "adm_day_usage": "📅 Geben Sie ein Datum an, z. B. /day 30.10 oder /day morgen",
        "btn_adm_booking_item": "⚙️ {n} · {when} · {client}",
        "btn_day_prev": "◀️ {day}",
        "btn_day_next": "{day} ▶️",
        "btn_day_pick": "📅 Datum",
        "btn_master_all": "👥 Alle",
        "btn_master_selected": "✅ {name}",
        "adm_card": "📋 <b>Termin #{id}</b>\n\n{summary}\n💰 {price}",
        "adm_card_source_buttons": "\n📱 Vom Kunden selbst gebucht",
        "adm_card_source_ai": "\n🤖 Über den KI-Chat gebucht",
        "adm_card_source_admin": "\n📞 Vom Administrator eingetragen",
        "adm_card_noshow": "\n🚫 Nicht erschienen",
        "adm_card_cancelled": "\n❌ Storniert — {by}",
        "adm_card_confirmed": "\n✅ Der Kunde hat bestätigt, dass er kommt",
        "btn_adm_resched": "🔁 Verschieben",
        "btn_adm_cancel_short": "🗑 Stornieren",
        "btn_adm_noshow": "🚫 Nicht erschienen",
        "btn_adm_client": "👤 Kunde",
        "btn_adm_write": "✉️ Nachricht",
        "adm_resched_day": "🔁 <b>Termin #{id} verschieben</b>\n\n{summary}\n\nWählen Sie einen neuen Tag 👇",
        "adm_resched_none": "🔁 Keine freien Tage zum Verschieben.\n\n{summary}",
        "adm_resched_time": "🔁 <b>#{id}</b> · {service} · {master}\n📅 {day} — wählen Sie eine Uhrzeit 👇",
        "adm_resched_confirm": "🔁 <b>Termin verschieben?</b>\n\n💈 {service}\n👤 {client}\nBisher: {old}\nNeu: <b>{new}</b>\n\n{who}",
        "btn_adm_resched_yes": "✅ Verschieben",
        "adm_resched_same": "Das ist dieselbe Zeit — nichts geändert.",
        "btn_adm_change_master": "👤 Stylist wechseln",
        "btn_adm_master_pick": "💈 {name}",
        "adm_change_master": "👤 <b>Anderer Stylist für Termin #{id}</b>\n\n{summary}\n\nWählen Sie einen Stylisten 👇",
        "adm_change_master_none": "👤 Kein anderer Stylist bietet «{service}» an.",
        "adm_new_master": "👤 Neuer Stylist: <b>{master}</b>",
        "adm_master_busy": "👤 Neuer Stylist: <b>{master}</b>\n⚠️ Um {time} ist dieser Stylist belegt — wählen Sie einen anderen Tag.",
        "adm_resched_done": "🔁 <b>Verschoben</b>\n\n{summary}\n\nBisher: {old}\n{who}",
        "adm_resched_notified": "Der Kunde wurde benachrichtigt.",
        "adm_resched_offline": "Der Kunde ist nicht bei Telegram — bitte informieren Sie ihn selbst.",
        "adm_find_usage": "🔎 Kunden suchen: /find Anna, /find @benutzername oder /find 0151 (Teil der Telefonnummer)",
        "adm_find_none": "🔎 Niemand gefunden für «{q}».",
        "adm_find_many": "🔎 Gefunden: {count}. Wählen Sie einen Kunden 👇",
        "btn_adm_client_item": "👤 {label}",
        "adm_client_card": "👤 <b>{name}</b>\n{contacts}\n{tg}\n\n📊 Besuche: {done} · nicht erschienen: {noshow} · Stornierungen: {cancelled}\n💰 Gesamt: {spent}{last}{upcoming}{notes}",
        "adm_client_tg_yes": "✉️ Nutzt den Bot",
        "adm_client_tg_no": "📵 Nicht bei Telegram",
        "adm_client_last": "\n🗓 Letzter Besuch: {day} · {service}",
        "adm_client_upcoming": "\n\n<b>Anstehend:</b>{items}",
        "adm_client_upcoming_item": "\n• {when} · {service}",
        "adm_client_notes": "\n\n📝 {notes}",
        "btn_adm_client_booking": "⚙️ {when} · {service}",
        "btn_adm_client_book": "📞 Eintragen",
        "adm_export_usage": "📊 /export — Termine der letzten 30 Tage und alle anstehenden; /export 90 — für 90 Tage.",
        "adm_export_empty": "Keine Termine in diesem Zeitraum.",
        "adm_export_caption": "📊 Termine seit {start} (und alle anstehenden): {count}",
        "adm_export_headers": "Datum|Uhrzeit|Ende|Stylist|Leistung|Preis|Status|Kunde|Telefon|Telegram|Quelle|Anzahlung|Notiz|Erstellt",
        "adm_export_sheet": "Termine",
        "adm_export_statuses": "geplant|erledigt|nicht erschienen|storniert",
        "adm_export_sources": "Kunde|KI-Chat|Admin",
        "adm_export_prepay": "ausstehend|laut Kunde bezahlt|bezahlt",
        "adm_master_revenue": "\n   {name}: {count} · {revenue}",
        "adm_evening_report": "🌙 <b>Tagesbilanz · {day}</b>\n\n✅ Erledigt: {done} · 🚫 nicht erschienen: {noshow} · ❌ storniert: {cancelled}\n💰 Umsatz: <b>{revenue}</b>{by_master}\n\n📅 Termine morgen: {tomorrow}",
        "client_rescheduled_by_admin": "🔁 Der Administrator hat Ihren Termin verschoben:\n💈 {service} · {master}\nBisher: {old}\nJetzt: <b>{new}</b>\n\nWenn die Zeit nicht passt, ändern Sie sie unter «🗓 Meine Termine» oder schreiben Sie uns.",
        "adm_booking_summary": "<b>{day}, {start}–{end}</b> · {master}\n💈 {service}\n👤 {client}",
        "adm_noshow_done": "🚫 {client} ({time}) — nicht erschienen",
        "adm_cancel_ask": "Diesen Termin stornieren?\n\n{booking}\n\n{who}",
        "adm_cancel_notify": "Der Kunde erhält eine Telegram-Nachricht.",
        "adm_cancel_offline": "Der Kunde ist nicht bei Telegram — bitte informieren Sie ihn selbst.",
        "adm_cancelled_done": "🗑 <b>Storniert</b>\n\n{booking}\n\nDer Kunde wurde benachrichtigt.",
        "adm_cancelled_done_offline": "🗑 <b>Storniert</b>\n\n{booking}\n\nDer Kunde ist nicht bei Telegram — bitte informieren Sie ihn selbst.",
        "adm_cancelled_header": "\n\n➖➖➖\n❌ <b>Storniert</b> — {count}",
        "adm_cancelled_item": "\n{day} {start} · {master} · {service} · {client} — {by}",
        "adm_cancelled_by_client": "vom Kunden storniert",
        "adm_cancelled_by_admin": "vom Administrator storniert",
        "adm_new_booking_prepay": "\n💳 Anzahlung {amount} ausstehend bis {deadline}",
        "adm_prepay_claim_note": "💳 <b>Der Kunde gibt an, bezahlt zu haben</b>\n\n{booking}\n\nPrüfen Sie, ob {amount} eingegangen ist, und bestätigen Sie 👇",
        "adm_prepay_screenshot": "💳 <b>Der Kunde hat einen Zahlungs-Screenshot gesendet</b> (oben)\n\n{booking}\n\nPrüfen Sie, ob {amount} eingegangen ist, und bestätigen Sie 👇",
        "adm_prepay_overdue": "⏰ <b>Zahlung noch nicht bestätigt</b>\nDer Kunde hat vor {hours} Std. angegeben, bezahlt zu haben. Bitte prüfen Sie: Solche Termine werden nicht automatisch storniert.\n\n{booking}",
        "btn_adm_prepay_ok": "✅ Zahlung erhalten",
        "btn_adm_cancel_booking": "🗑 Termin stornieren",
        "adm_prepay_ok_done": "✅ <b>Anzahlung bestätigt</b>, der Kunde wurde benachrichtigt.\n\n{booking}",
        "adm_prepay_ok_alert": "✅ Zahlung bestätigt",
        "adm_prepay_already": "Die Anzahlung ist bereits bestätigt.",
        "adm_prepay_waiting": "\n💳 ⏳ Anzahlung ausstehend",
        "adm_prepay_claimed": "\n💳 ❔ laut Kunde bezahlt — bitte prüfen",
        "adm_prepay_paid": "\n💳 ✅ Anzahlung erhalten",
        "adm_cancelled_by_unpaid": "nicht bezahlt",
        "adm_cancelled_unpaid": "⏰ <b>Termin automatisch storniert</b> — Anzahlung nicht innerhalb von {hours} Std. bestätigt.\n\n{booking}",
        "btn_adm_clear_cancelled": "🧹 Stornierte ausblenden ({count})",
        "adm_clear_ask": "Stornierte Termine aus der Liste entfernen ({count})?\nSie erscheinen nicht mehr in /all, bleiben aber in der Statistik.",
        "btn_adm_yes_clear": "Ja, ausblenden",
        "adm_cleared_done": "🧹 Stornierte Termine ausgeblendet: {count}. Aktualisierte Liste — /all",
        "btn_adm_yes_cancel": "Ja, stornieren",
        "client_cancelled_by_admin": "Leider hat der Administrator Ihren Termin storniert:\n💈 {service} · {master}\n"
                                     "📅 {day} um {time}\n\nBitte wählen Sie eine andere Zeit — «📅 Termin buchen» — oder schreiben Sie uns.",
        "adm_week_header": "🗓 <b>Termine für 7 Tage</b>",
        "adm_week_empty": "\n\nKeine Termine.",
        "adm_week_more": "\n\n➕ {count} weitere später — /all",
        "adm_all_header": "🗓 <b>Alle anstehenden Termine</b>",
        "adm_note_line": "\n📝 {note}",
        "adm_via_admin": " · vom Administrator eingetragen 📞",
        "btn_adm_book_confirm": "✅ Eintragen",
        "btn_adm_book_cancel": "✖️ Abbrechen",
        "adm_book_service": "📞 <b>Kunden eintragen</b>\nWählen Sie eine Leistung:",
        "adm_book_group": "📞 <b>Kunden eintragen</b>\nWählen Sie eine Kategorie — dann Leistung, Stylist, Tag und Uhrzeit 👇",
        "adm_book_in_group": "📞 <b>{group}</b>\nWählen Sie eine Leistung — dann Stylist, Tag und Uhrzeit 👇",
        "adm_book_master": "📞 {service}\nWählen Sie einen Stylisten:",
        "adm_book_day": "📞 {service} · {master}\nWählen Sie einen Tag:",
        "adm_book_time": "📞 {service} · {master} · {day}\nWählen Sie eine Uhrzeit:",
        "adm_book_no_days": "{master} hat keine freien Tage für «{service}». Wählen Sie einen anderen Stylisten:",
        "adm_book_client_prompt": "📞 {service} · {master} · {day} um {time}\n\n"
                                  "Senden Sie die Kundendaten in einer Nachricht: <b>Name</b> und <b>Telefon</b>, "
                                  "ein Kommentar in einer neuen Zeile (optional). Zum Beispiel:\n"
                                  "<code>Anna +4915112345678\nmöchte es kürzer als beim letzten Mal</code>\n\n"
                                  "Oder teilen Sie den Telegram-Kontakt des Kunden (📎 → Kontakt).\n/cancel — abbrechen.",
        "adm_book_need_name": "Ich sehe keinen Kundennamen. Senden Sie erneut: Name, Telefon, Kommentar in einer neuen Zeile.",
        "adm_book_card": "📞 <b>Termin prüfen</b>\n\n👤 {client}\n💈 {service} · {master}\n📅 {day} um {time}\n"
                         "💰 {price}{note}\n\n{hint}\n\nUm die Daten zu ändern, senden Sie sie einfach erneut.",
        "adm_book_hint_tg": "✉️ Der Kunde nutzt den Bot bereits ({client}) — er erhält eine Nachricht und Erinnerungen.",
        "adm_book_hint_known": "🗂 Der Kunde ist bereits in der Datenbank ({client}), aber nicht bei Telegram — keine Nachrichten.",
        "adm_book_hint_offline": "📵 Neuer Kunde ohne Telegram — keine Nachrichten oder Erinnerungen.",
        "adm_book_duplicate": "Der Kunde hat zu dieser Zeit bereits einen Termin (#{id}).",
        "adm_book_done": "✅ <b>Eingetragen</b> <code>#{id}</code>\n👤 {client}\n💈 {service} · {master}\n"
                         "📅 {day} um {time}{notified}",
        "adm_book_notified": "\n\n✉️ Der Kunde hat eine Telegram-Nachricht erhalten.",
        "adm_book_not_notified": "\n\n📵 Der Kunde hat keine Nachricht erhalten (nicht bei Telegram) — rufen Sie ihn bei Bedarf an.",
        "adm_book_aborted": "Termin nicht erstellt.",
        "client_booked_by_admin": "📞 Der Administrator hat einen Termin für Sie eingetragen:\n💈 {service} · {master}\n📅 {day} um {time}\n💰 {price}\n\n"
                                  "Verschieben oder absagen — «🗓 Meine Termine».",
        "adm_block_usage": "🔒 <b>Zeit sperren</b>\n\nFormat: <code>/block stylist datum [zeit] [notiz]</code>\n\n"
                           "Beispiele:\n<code>/block {example} 30.10</code> — ganzer Tag\n"
                           "<code>/block {example} 30.10 14:00-16:00 telefonische Buchung</code>\n"
                           "<code>/block alle 31.12</code> — freier Tag für alle\n\nStylisten: {masters}",
        "adm_block_bad": "Ich habe den Befehl nicht verstanden 🤔\n\n{usage}",
        "adm_block_done": "🔒 Gesperrt: {master}, {day} {range}{note}",
        "adm_block_conflicts": "\n\n⚠️ Zu dieser Zeit gibt es Termine — stornieren Sie sie (/today, /tomorrow) oder informieren Sie die Kunden:{lines}",
        "adm_all_masters": "alle Stylisten",
        "adm_whole_day": "(ganzer Tag)",
        "adm_blocks_header": "🔒 <b>Gesperrte Zeiten</b> (zum Löschen tippen):",
        "adm_blocks_empty": "Keine gesperrten Zeiten.",
        "btn_adm_block_item": "🗑 {master} · {day} {range}",
        "adm_block_deleted": "🔓 Gelöscht. Diese Zeit ist wieder buchbar.",
        "adm_paused": "⏸ Die KI ist aus. Alle Kundennachrichten werden an Sie weitergeleitet; die Buchungs-Buttons funktionieren weiter.\n"
                      "Einschalten: /resume",
        "adm_resumed_all": "▶️ Die KI antwortet den Kunden wieder.",
        "adm_reloaded": "🔄 Einstellungen neu geladen: Leistungen — {services}, Stylisten — {masters}.",
        "adm_reload_failed": "❌ Die Einstellungsdatei enthält einen Fehler, die bisherigen Einstellungen bleiben aktiv:\n<code>{error}</code>",
        "adm_reload_token": "\n⚠️ Der Bot-Token hat sich geändert — starten Sie den Bot neu, um ihn zu übernehmen.",
        "adm_digest": "☀️ <b>Guten Morgen!</b>\n\n{body}",
        "adm_ai_alert": "⚠️ <b>Die KI antwortet nicht</b> ({name})\n<code>{error}</code>\n\n"
                        "Der Bot funktioniert weiter mit Buttons. Prüfen Sie den API-Schlüssel und das Guthaben auf console.anthropic.com.",
        "adm_budget_alert": "⚠️ Tageslimit der KI erreicht ({name}). Bis zum Ende des Tages funktioniert der Bot nur mit Buttons. "
                            "Das Limit ändern Sie in settings.toml (daily_token_limit).",
        "adm_stats": "📊 <b>Statistik für {days} Tage</b>\n\n"
                     "<b>Termine</b>\n"
                     "• erstellt: {created} (KI-Chat: {by_ai}, Buttons: {by_buttons}, Admin: {by_admin})\n"
                     "• nachts (22:00–08:00): {night}\n"
                     "• erledigt: {done} · nicht erschienen: {noshow} · storniert: {cancelled}\n"
                     "• anstehend: {upcoming}\n\n"
                     "<b>Umsatz</b>\n"
                     "• {revenue} · durchschnittlicher Bon {avg_check}{by_master}\n"
                     "• erwartet aus anstehenden Terminen: {expected}\n\n"
                     "<b>Gespräche</b>\n"
                     "• Kunden, die geschrieben haben: {clients}\n"
                     "• an Sie übergeben: {handoffs}\n"
                     "• vom Bot allein erledigt: {auto_rate}\n\n"
                     "<b>Erinnerungen</b>\n"
                     "• gesendet: {reminders} · «Ich komme»: {confirmed}\n\n"
                     "<b>KI</b>\n"
                     "• bearbeitete Nachrichten: {ai_calls} · Tokens: {tokens}\n"
                     "• geschätzte Kosten: ${cost}",
        "adm_client_noname": "Kunde",
        "cmd_start": "Hauptmenü",
        "cmd_admin": "Verwaltung",
        "cmd_today": "Termine heute",
        "cmd_tomorrow": "Termine morgen",
        "cmd_book": "Kunden eintragen",
        "cmd_day": "Termine an einem Datum",
        "cmd_find": "Kunden suchen",
        "cmd_export": "Export nach Excel",
        "cmd_week": "Termine für 7 Tage",
        "cmd_all": "Alle anstehenden Termine",
        "cmd_stats": "Statistik",
        "cmd_block": "Zeit sperren",
        "cmd_blocks": "Gesperrte Zeiten",
        "cmd_pause": "KI ausschalten",
        "cmd_resume": "KI einschalten",
        "cmd_reload": "Einstellungen neu laden",
        "cmd_myid": "Meine Telegram-ID",
        "cmd_masters": "Stylisten im Bot",
        "cmd_prices": "Preise ändern",
        "adm_prices": "💰 <b>Preise der Leistungen</b>\nTippen Sie auf eine Leistung, um den Preis zu ändern 👇",
        "adm_prices_changed": "\n\n✏️ — Preis hier im Bot geändert (in der Einstellungsdatei steht noch der alte).",
        "adm_price_ask": "💰 <b>{title}</b>\nAktuell: <b>{price}</b>\n\nSenden Sie den neuen Preis als Zahl, z. B. 650.",
        "adm_price_file": "\nIn der Einstellungsdatei: {price}.",
        "btn_adm_price_reset": "↩️ Zurücksetzen auf {price}",
        "adm_price_bad": "Das sieht nicht nach einem Preis aus 🤔 Senden Sie nur eine Zahl, z. B. 650. Abbrechen — /cancel",
        "adm_price_done": "✅ <b>{title}</b>: {old} → <b>{new}</b>\nKunden und die KI sehen bereits den neuen Preis. "
                          "Frühere Termine behalten den alten Preis.",
        "adm_price_combos": "\nPreise der Kombinationen mit Zusatzleistungen neu berechnet.",
        "adm_price_changed_note": "💰 {admin} hat einen Preis geändert: <b>{title}</b> {old} → <b>{new}</b>",
        "cmd_my": "Mein Tag",
        "cmd_myweek": "Meine Woche",
        "cmd_off": "Zeit sperren",
        "cmd_offs": "Meine gesperrten Zeiten",
        # Stylisten: Admin
        "adm_masters": "✂️ <b>Stylisten im Bot</b>\n\nEin verbundener Stylist sieht seine Termine, sperrt seine eigene "
                       "Zeit und wird über seine Kunden benachrichtigt.\n{items}",
        "adm_masters_on": "\n✅ <b>{name}</b> — {who}",
        "adm_masters_off": "\n⚪️ <b>{name}</b> — nicht verbunden",
        "btn_adm_master_invite": "🔗 Einladen: {name}",
        "btn_adm_master_unlink": "✖️ Trennen: {name}",
        "btn_adm_yes_unlink": "✖️ Ja, trennen",
        "btn_adm_open": "📋 Termin öffnen",
        "adm_master_invite": "🔗 Link für Stylist <b>{name}</b>:\n\n{link}\n\nLeiten Sie ihn an den Stylisten weiter — "
                             "er öffnet ihn und tippt auf «Start». Einmaliger Link, gültig für {hours} Std.",
        "adm_master_no_username": "Die Bot-Adresse konnte nicht abgerufen werden. Bitte versuchen Sie es in einer Minute erneut.",
        "adm_master_unlink_ask": "Stylist <b>{name}</b> vom Bot trennen? Er sieht dann keine Termine mehr "
                                 "und erhält keine Benachrichtigungen.",
        "adm_master_unlinked": "✖️ Stylist {name} wurde vom Bot getrennt.",
        "adm_master_joined": "✂️ Stylist <b>{name}</b> hat sich mit dem Bot verbunden ({who}).",
        "adm_master_noshow": "🚫 <b>Stylist {master} hat ein Nichterscheinen markiert</b>\n\n{booking}",
        "adm_master_off": "🌴 Stylist <b>{master}</b> hat Zeit gesperrt: {day} {range}",
        "adm_master_off_conflicts": "\n\n⚠️ <b>Zu dieser Zeit gibt es Termine</b> — bitte sprechen Sie sich "
                                    "mit den Kunden ab (verschieben oder stornieren):{lines}",
        "adm_master_on": "🔓 Stylist <b>{master}</b> hat Zeit freigegeben: {day} {range}",
        # Stylisten: der Stylist
        "mst_invite_bad": "Dieser Link ist ungültig oder wurde bereits verwendet. Bitten Sie den Administrator um einen neuen.",
        "mst_joined": "✅ <b>Sie sind als Stylist „{name}“ verbunden.</b>\n\n",
        "mst_start": "✂️ <b>{name}</b>, Sie sind Stylist im Bot „{shop}“.\n\n"
                     "📅 <b>Mein Tag</b> — Ihre Termine, Tage blättern ◀️ ▶️\n"
                     "🗓 <b>Meine Woche</b> — Termine für 7 Tage\n"
                     "🌴 <b>Zeit sperren</b> — freier Tag, Pause, private Termine\n"
                     "🔒 <b>Meine gesperrten Zeiten</b> — ansehen und freigeben\n\n"
                     "Der Bot informiert Sie über neue Termine, Stornierungen und Verschiebungen, sendet morgens "
                     "Ihren Tagesplan und erinnert Sie vor jedem Kunden.",
        "mst_unlinked": "Sie wurden als Stylist vom Bot getrennt. Als Kunde können Sie weiterhin buchen 👇",
        "btn_mst_day": "📅 Mein Tag",
        "btn_mst_week": "🗓 Meine Woche",
        "btn_mst_off": "🌴 Zeit sperren",
        "btn_mst_offs": "🔒 Meine gesperrten Zeiten",
        "btn_mst_to_day": "⬅️ Zum Tag",
        "mst_day_hint": "\n\nTippen Sie auf einen Termin, um die Karte zu öffnen 👇",
        "mst_day_off": "\n\n🌴 Laut Ihrem Plan ein freier Tag.",
        "mst_day_blocks": "\n\n🔒 Gesperrt: {ranges}",
        "mst_week_header": "🗓 <b>Ihre Termine für 7 Tage</b>",
        "mst_off_day": "🌴 <b>Zeit sperren</b>\n\nWählen Sie einen Tag:",
        "mst_off_range": "🌴 <b>{day}</b> · Ihre Arbeitszeit {hours}\n\nDen ganzen Tag sperren oder ab welcher Uhrzeit?",
        "mst_off_whole_only": "🌴 <b>{day}</b> · {hours}\n\nDen ganzen Tag sperren?",
        "mst_off_no_work": "laut Plan freier Tag",
        "mst_off_end": "🌴 <b>{day}</b>, ab {start}\n\nBis wann?",
        "btn_mst_whole_day": "🌴 Ganzer Tag",
        "btn_mst_off_yes": "✅ Sperren",
        "mst_off_confirm": "<b>{day} {range}</b> sperren?\nKunden können diese Zeit dann nicht buchen.{conflicts}",
        "mst_off_conflicts": "\n\n⚠️ Zu dieser Zeit gibt es Termine — der Administrator wird benachrichtigt, "
                             "um sich mit den Kunden abzustimmen:{lines}",
        "mst_off_done": "🔒 Gesperrt: <b>{day} {range}</b>. Kunden können diese Zeit nicht buchen.",
        "mst_off_done_conflicts": "\n\n⚠️ Zu dieser Zeit bestehen noch Termine — der Administrator wurde benachrichtigt:{lines}",
        "mst_offs_header": "🔒 <b>Ihre gesperrten Zeiten</b>\nZum Freigeben tippen:",
        "mst_offs_header_none": "🔒 <b>Ihre gesperrten Zeiten</b>",
        "mst_offs_admin": "\n\nVom Administrator gesperrt (nur er kann das ändern):{lines}",
        "mst_offs_empty": "🔒 Keine gesperrten Zeiten. Zum Sperren — „🌴 Zeit sperren“.",
        "btn_mst_block_item": "🗑 {label}",
        "alert_mst_opened": "Die Zeit ist wieder buchbar",
        "mst_new": "🆕 <b>Neuer Termin bei Ihnen</b>\n\n📅 {day} um {time}\n💈 {service}\n👤 {client}",
        "mst_cancelled": "❌ <b>Termin storniert</b>\n\n📅 {day} um {time}\n💈 {service}\n👤 {client}",
        "mst_moved": "🔁 <b>Termin an einen anderen Stylisten übergeben</b>\n\n📅 {day} um {time}\n💈 {service}\n👤 {client}",
        "mst_rescheduled": "🔁 <b>Termin verschoben</b>\n\n💈 {service}\n👤 {client}\nBisher: {old}\nJetzt: <b>{new}</b>",
        "mst_digest": "☀️ <b>Guten Morgen, {name}!</b>\n\n{body}",
        "mst_heads_up": "⏰ <b>Um {time}</b> (in {min} Min.) — {client}\n💈 {service}",
    },
}


def is_plain_key(key: str) -> bool:
    return key.startswith(PLAIN_PREFIXES)


def render(template: str, key: str, kwargs: dict) -> str:
    """Підставляє значення в шаблон. Для HTML-шаблонів екранує рядки."""
    if is_plain_key(key):
        values = {k: ("" if v is None else v) for k, v in kwargs.items()}
    else:
        values = {}
        for k, v in kwargs.items():
            if v is None:
                values[k] = ""
            elif isinstance(v, Raw):
                values[k] = str(v)
            elif isinstance(v, str):
                values[k] = escape(v, quote=False)
            else:
                values[k] = v
    try:
        return template.format(**values)
    except (KeyError, IndexError, ValueError):
        # Помилка в перевизначеному тексті не повинна ламати бота.
        return template
