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
        "btn_service": "{title} · {price}",
        "choose_master": "💈 <b>{service}</b>\n\nОберіть майстра:",
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
        "already_booked": "✅ Ви вже записані на цей час.",
        "slot_taken": "Ой, цей час щойно зайняли 😕 Оберіть, будь ласка, інший:",
        "too_many_active": "Активних записів у вас уже {count} — це максимум. "
                           "Перенесіть або скасуйте один у розділі «🗓 Мої записи».",
        "booking_error": "Не вдалося створити запис 😕 Спробуйте ще раз або напишіть нам.",
        "proposal_declined": "Добре 🙂 Напишіть, що змінити — підберу інший варіант.",
        # Мої записи
        "my_none": "У вас немає запланованих візитів.",
        "my_header": "🗓 <b>Ваші записи:</b>",
        "my_item": "\n\n📅 <b>{day} о {time}</b>\n💈 {service} · {master}",
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
        "prices_header": "💈 <b>Послуги і ціни</b>",
        "price_item": "\n\n<b>{title}</b> — {price}\n⏱ {duration} хв{masters}",
        "price_masters": " · {masters}",
        "price_desc": "\n{description}",
        "prices_addons_header": "\n\n➕ <b>Можна додати до стрижки</b> (кнопкою під час запису)",
        "price_addon_item": "\n{title} — +{price}, +{duration} хв",
        "contacts_header": "📍 <b>{name}</b>",
        "contacts_address": "\n\n🏠 {address}",
        "contacts_phone": "\n📞 {phone}",
        "contacts_hours": "\n\n🕒 <b>Графік роботи</b>\n{hours}",
        "contacts_directions": "\n\n🚗 {directions}",
        "contacts_payment": "\n💳 {payment}",
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
                      "/week — записи на 7 днів\n"
                      "/all — усі майбутні записи\n"
                      "/stats — статистика за 30 днів\n"
                      "/block — закрити час (вихідний, відпустка, запис по телефону)\n"
                      "/blocks — список закритого часу\n"
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
        "adm_day_header": "📅 <b>{day}</b> — записів: {count}",
        "adm_day_empty": "📅 <b>{day}</b> — записів немає.",
        "adm_booking_line": "\n\n<b>{start}–{end}</b> · {master}\n💈 {service}\n👤 {client}{flags}  <code>#{id}</code>",
        "adm_legend": "\n\n🚫 — клієнт не прийшов · 🗑 — скасувати запис",
        "adm_noshow_done": "🚫 Позначено «не прийшов»: #{id}",
        "adm_cancel_ask": "Скасувати запис #{id}? Клієнт отримає повідомлення.\n{line}",
        "btn_adm_yes_cancel": "Так, скасувати",
        "adm_cancelled_done": "🗑 Запис #{id} скасовано, клієнта повідомлено.",
        "client_cancelled_by_admin": "На жаль, ваш запис скасовано адміністратором:\n💈 {service} · {master}\n"
                                     "📅 {day} о {time}\n\nОберіть інший час — «📅 Записатися» — або напишіть нам.",
        "adm_week_header": "🗓 <b>Записи на 7 днів</b>",
        "adm_week_day": "\n\n<b>{day}</b> — {count}",
        "adm_week_line": "\n{start} {master} · {service} · {client}",
        "adm_week_empty": "\n\nЗаписів немає.",
        "adm_week_more": "\n\n➕ Пізніше ще записів: {count} — /all",
        "adm_all_header": "🗓 <b>Усі майбутні записи</b>",
        "adm_cancel_hint": "\n\n🗑 — скасувати запис (клієнт у Telegram отримає повідомлення)",
        "adm_cancelled_done_offline": "🗑 Запис #{id} скасовано. Клієнта немає в Telegram — повідомте його самі.",
        "adm_note_line": "\n📝 {note}",
        "adm_via_admin": " · записав адміністратор 📞",
        "btn_adm_book_confirm": "✅ Записати",
        "btn_adm_book_cancel": "✖️ Скасувати",
        "adm_book_service": "📞 <b>Запис клієнта</b>\nОберіть послугу:",
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
        "adm_day_cancelled": " (скасовано: {count})",
        "adm_cancelled_by_client": " — ❌ скасував клієнт",
        "adm_cancelled_by_admin": " — ❌ скасував адміністратор",
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
                     "• створено: {created} (AI-чат: {by_ai}, кнопки: {by_buttons})\n"
                     "• уночі (22:00–08:00): {night}\n"
                     "• відбулося: {done} · не прийшли: {noshow} · скасовано: {cancelled}\n"
                     "• попереду: {upcoming}\n\n"
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
        "cmd_week": "Записи на 7 днів",
        "cmd_all": "Усі майбутні записи",
        "cmd_stats": "Статистика",
        "cmd_block": "Закрити час",
        "cmd_blocks": "Закритий час",
        "cmd_pause": "Вимкнути AI",
        "cmd_resume": "Увімкнути AI",
        "cmd_reload": "Оновити налаштування",
        "cmd_myid": "Мій Telegram ID",
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
        "btn_service": "{title} · {price}",
        "choose_master": "💈 <b>{service}</b>\n\nВыберите мастера:",
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
        "already_booked": "✅ Вы уже записаны на это время.",
        "slot_taken": "Ой, это время только что заняли 😕 Выберите, пожалуйста, другое:",
        "too_many_active": "Активных записей у вас уже {count} — это максимум. "
                           "Перенесите или отмените одну в разделе «🗓 Мои записи».",
        "booking_error": "Не удалось создать запись 😕 Попробуйте ещё раз или напишите нам.",
        "proposal_declined": "Хорошо 🙂 Напишите, что изменить — подберу другой вариант.",
        "my_none": "У вас нет запланированных визитов.",
        "my_header": "🗓 <b>Ваши записи:</b>",
        "my_item": "\n\n📅 <b>{day} в {time}</b>\n💈 {service} · {master}",
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
        "prices_header": "💈 <b>Услуги и цены</b>",
        "price_item": "\n\n<b>{title}</b> — {price}\n⏱ {duration} мин{masters}",
        "price_masters": " · {masters}",
        "price_desc": "\n{description}",
        "prices_addons_header": "\n\n➕ <b>Можно добавить к стрижке</b> (кнопкой при записи)",
        "price_addon_item": "\n{title} — +{price}, +{duration} мин",
        "contacts_header": "📍 <b>{name}</b>",
        "contacts_address": "\n\n🏠 {address}",
        "contacts_phone": "\n📞 {phone}",
        "contacts_hours": "\n\n🕒 <b>График работы</b>\n{hours}",
        "contacts_directions": "\n\n🚗 {directions}",
        "contacts_payment": "\n💳 {payment}",
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
                      "/week — записи на 7 дней\n"
                      "/all — все будущие записи\n"
                      "/stats — статистика за 30 дней\n"
                      "/block — закрыть время (выходной, отпуск, запись по телефону)\n"
                      "/blocks — список закрытого времени\n"
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
        "adm_day_header": "📅 <b>{day}</b> — записей: {count}",
        "adm_day_empty": "📅 <b>{day}</b> — записей нет.",
        "adm_booking_line": "\n\n<b>{start}–{end}</b> · {master}\n💈 {service}\n👤 {client}{flags}  <code>#{id}</code>",
        "adm_legend": "\n\n🚫 — клиент не пришёл · 🗑 — отменить запись",
        "adm_noshow_done": "🚫 Отмечено «не пришёл»: #{id}",
        "adm_cancel_ask": "Отменить запись #{id}? Клиент получит уведомление.\n{line}",
        "btn_adm_yes_cancel": "Да, отменить",
        "adm_cancelled_done": "🗑 Запись #{id} отменена, клиент уведомлён.",
        "client_cancelled_by_admin": "К сожалению, ваша запись отменена администратором:\n💈 {service} · {master}\n"
                                     "📅 {day} в {time}\n\nВыберите другое время — «📅 Записаться» — или напишите нам.",
        "adm_week_header": "🗓 <b>Записи на 7 дней</b>",
        "adm_week_day": "\n\n<b>{day}</b> — {count}",
        "adm_week_line": "\n{start} {master} · {service} · {client}",
        "adm_week_empty": "\n\nЗаписей нет.",
        "adm_week_more": "\n\n➕ Позже ещё записей: {count} — /all",
        "adm_all_header": "🗓 <b>Все будущие записи</b>",
        "adm_cancel_hint": "\n\n🗑 — отменить запись (клиент в Telegram получит сообщение)",
        "adm_cancelled_done_offline": "🗑 Запись #{id} отменена. Клиента нет в Telegram — сообщите ему сами.",
        "adm_note_line": "\n📝 {note}",
        "adm_via_admin": " · записал администратор 📞",
        "btn_adm_book_confirm": "✅ Записать",
        "btn_adm_book_cancel": "✖️ Отмена",
        "adm_book_service": "📞 <b>Запись клиента</b>\nВыберите услугу:",
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
        "adm_day_cancelled": " (отменено: {count})",
        "adm_cancelled_by_client": " — ❌ отменил клиент",
        "adm_cancelled_by_admin": " — ❌ отменил администратор",
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
                     "• создано: {created} (AI-чат: {by_ai}, кнопки: {by_buttons})\n"
                     "• ночью (22:00–08:00): {night}\n"
                     "• состоялось: {done} · не пришли: {noshow} · отменено: {cancelled}\n"
                     "• впереди: {upcoming}\n\n"
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
        "cmd_week": "Записи на 7 дней",
        "cmd_all": "Все будущие записи",
        "cmd_stats": "Статистика",
        "cmd_block": "Закрыть время",
        "cmd_blocks": "Закрытое время",
        "cmd_pause": "Выключить AI",
        "cmd_resume": "Включить AI",
        "cmd_reload": "Обновить настройки",
        "cmd_myid": "Мой Telegram ID",
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
        "btn_service": "{title} · {price}",
        "choose_master": "💈 <b>{service}</b>\n\nChoose a barber:",
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
        "already_booked": "✅ You are already booked for this time.",
        "slot_taken": "Oops, this time was just taken 😕 Please choose another one:",
        "too_many_active": "You already have {count} active bookings — that's the maximum. "
                           "Reschedule or cancel one in «🗓 My bookings».",
        "booking_error": "Couldn't create the booking 😕 Please try again or message us.",
        "proposal_declined": "OK 🙂 Tell me what to change and I'll find another option.",
        "my_none": "You have no upcoming visits.",
        "my_header": "🗓 <b>Your bookings:</b>",
        "my_item": "\n\n📅 <b>{day} at {time}</b>\n💈 {service} · {master}",
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
        "prices_header": "💈 <b>Services & prices</b>",
        "price_item": "\n\n<b>{title}</b> — {price}\n⏱ {duration} min{masters}",
        "price_masters": " · {masters}",
        "price_desc": "\n{description}",
        "prices_addons_header": "\n\n➕ <b>Add-ons</b> (a button while booking)",
        "price_addon_item": "\n{title} — +{price}, +{duration} min",
        "contacts_header": "📍 <b>{name}</b>",
        "contacts_address": "\n\n🏠 {address}",
        "contacts_phone": "\n📞 {phone}",
        "contacts_hours": "\n\n🕒 <b>Opening hours</b>\n{hours}",
        "contacts_directions": "\n\n🚗 {directions}",
        "contacts_payment": "\n💳 {payment}",
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
                      "/week — bookings for 7 days\n"
                      "/all — all upcoming bookings\n"
                      "/stats — 30-day statistics\n"
                      "/block — block time (day off, vacation, phone booking)\n"
                      "/blocks — list of blocked time\n"
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
        "adm_day_header": "📅 <b>{day}</b> — bookings: {count}",
        "adm_day_empty": "📅 <b>{day}</b> — no bookings.",
        "adm_booking_line": "\n\n<b>{start}–{end}</b> · {master}\n💈 {service}\n👤 {client}{flags}  <code>#{id}</code>",
        "adm_legend": "\n\n🚫 — client didn't show up · 🗑 — cancel booking",
        "adm_noshow_done": "🚫 Marked as no-show: #{id}",
        "adm_cancel_ask": "Cancel booking #{id}? The client will be notified.\n{line}",
        "btn_adm_yes_cancel": "Yes, cancel",
        "adm_cancelled_done": "🗑 Booking #{id} cancelled, the client was notified.",
        "client_cancelled_by_admin": "Unfortunately, your booking was cancelled by the admin:\n💈 {service} · {master}\n"
                                     "📅 {day} at {time}\n\nPlease choose another time — «📅 Book» — or message us.",
        "adm_week_header": "🗓 <b>Bookings for 7 days</b>",
        "adm_week_day": "\n\n<b>{day}</b> — {count}",
        "adm_week_line": "\n{start} {master} · {service} · {client}",
        "adm_week_empty": "\n\nNo bookings.",
        "adm_week_more": "\n\n➕ {count} more later — /all",
        "adm_all_header": "🗓 <b>All upcoming bookings</b>",
        "adm_cancel_hint": "\n\n🗑 — cancel a booking (clients on Telegram get a message)",
        "adm_cancelled_done_offline": "🗑 Booking #{id} cancelled. The client isn't on Telegram — let them know yourself.",
        "adm_note_line": "\n📝 {note}",
        "adm_via_admin": " · booked by admin 📞",
        "btn_adm_book_confirm": "✅ Book",
        "btn_adm_book_cancel": "✖️ Cancel",
        "adm_book_service": "📞 <b>Book a client</b>\nChoose a service:",
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
        "adm_day_cancelled": " (cancelled: {count})",
        "adm_cancelled_by_client": " — ❌ cancelled by client",
        "adm_cancelled_by_admin": " — ❌ cancelled by admin",
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
                     "• created: {created} (AI chat: {by_ai}, buttons: {by_buttons})\n"
                     "• at night (22:00–08:00): {night}\n"
                     "• completed: {done} · no-shows: {noshow} · cancelled: {cancelled}\n"
                     "• upcoming: {upcoming}\n\n"
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
        "cmd_week": "Bookings for 7 days",
        "cmd_all": "All upcoming bookings",
        "cmd_stats": "Statistics",
        "cmd_block": "Block time",
        "cmd_blocks": "Blocked time",
        "cmd_pause": "Turn AI off",
        "cmd_resume": "Turn AI on",
        "cmd_reload": "Reload settings",
        "cmd_myid": "My Telegram ID",
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
