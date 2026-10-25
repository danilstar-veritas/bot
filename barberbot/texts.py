"""Усі тексти бота трьома мовами (uk, ru, en).

Будь-який текст можна перевизначити для конкретного закладу в його файлі
налаштувань, у розділі [texts.uk] / [texts.ru] / [texts.en].

Правило: ключі, що починаються з "btn_", "cmd_" або "alert_", — це підписи
кнопок і спливаючі підказки (звичайний текст). Решта — повідомлення з
HTML-розміткою Telegram (<b>, <i>, <code>).
"""

from __future__ import annotations

from html import escape

SUPPORTED_LANGS = ("uk", "ru", "en")
PLAIN_PREFIXES = ("btn_", "cmd_", "alert_")


class Raw(str):
    """Рядок, який уже містить готовий HTML і не потребує екранування."""


WEEKDAYS_SHORT = {
    "uk": ["пн", "вт", "ср", "чт", "пт", "сб", "нд"],
    "ru": ["пн", "вт", "ср", "чт", "пт", "сб", "вс"],
    "en": ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"],
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
