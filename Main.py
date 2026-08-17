import asyncio
from telebot.async_telebot import AsyncTeleBot
from telethon import TelegramClient
from telethon.tl.functions.account import ReportPeerRequest
from telethon.tl.types import InputReportReasonOther

BOT_TOKEN = "8575618466:AAHqMlwE-fOq7kwANSqTeDnLJJ81skHcghs"

API_ID = 25874957
API_HASH = "c89ef6fd9ba5c8a479abb1f4d2de248d"
SESSION_NAME = "IImoderation"

ALLOWED_USER_ID = 608502324

REPORT_TEXT = (
   "Этот бот используется для поиска персональной информации, а так же доксинга этих данных: номер телефона, ФИО, ИНН, СНИЛС, родственники, адрес. Что нарушает правила: https://www.esafety.gov.au/report/options-if-esafety-cant-investigate Прошу принять меры в виде немедленной блокировки этого телеграм бота"
)

REPORTS_PER_BOT = 5
DELAY_BETWEEN_REPORTS = 0.5
DELAY_BETWEEN_BOTS = 2.0

bot = AsyncTeleBot(BOT_TOKEN)
client = TelegramClient(SESSION_NAME, API_ID, API_HASH)

USER_CHAT_ID = None

async def send_log(text: str, chat_id: int = None):
    global USER_CHAT_ID
    if chat_id is None:
        chat_id = USER_CHAT_ID
    if chat_id is None:
        print(f"[LOG] {text}")
        return

    try:
        await bot.send_message(chat_id, text)
        print(f"[LOG] {text}")
    except Exception as e:
        print(f"[ERROR] {e}")

async def report_bot(username: str, chat_id: int):
    try:
        await send_log(f"[+] Начинаю жалобы на @{username}")

        entity = await client.get_entity(username)

        await send_log(f"[+] Бот найден: @{username} (ID: {entity.id})")

        for i in range(REPORTS_PER_BOT):
            try:
                await client(ReportPeerRequest(
                    peer=entity,
                    reason=InputReportReasonOther(),
                    message=REPORT_TEXT
                ))
                await send_log(f"    ✅ Жалоба {i+1}/{REPORTS_PER_BOT} отправлена")
            except Exception as e:
                await send_log(f"    ❌ Ошибка {i+1}/{REPORTS_PER_BOT}: {str(e)}")

            if i < REPORTS_PER_BOT - 1:
                await asyncio.sleep(DELAY_BETWEEN_REPORTS)

        await send_log(f"{REPORTS_PER_BOT} снежков отправлено на @{username} ")

    except Exception as e:
        await send_log(f"[-] Ошибка с @{username}: {str(e)}")

@bot.message_handler(commands=['start'])
async def start(message):
    global USER_CHAT_ID
    if message.from_user.id != ALLOWED_USER_ID:
        await bot.reply_to(message, "Access denied.")
        return

    USER_CHAT_ID = message.chat.id
    await send_log(
        "✅ Бот запущен.\n"
        "Отправь список юзернеймов ботов (по одному в строке)\n"
        "Пример:\n"
        "@sexgodbot\n"
        "@findher_bot\n"
        "@leakbase_bot",
        message.chat.id
    )

@bot.message_handler(func=lambda m: True)
async def handle_list(message):
    global USER_CHAT_ID
    if message.from_user.id != ALLOWED_USER_ID:
        return

    USER_CHAT_ID = message.chat.id

    lines = [line.strip() for line in message.text.splitlines() if line.strip()]
    if not lines:
        await send_log("❌ Пустой список.", message.chat.id)
        return

    valid_usernames = [line.strip().lstrip('@') for line in lines if line.strip()]

    if not valid_usernames:
        await send_log("❌ Нет валидных @username", message.chat.id)
        return

    await send_log(f"🚀 Начинаю обработку. Всего ботов: {len(valid_usernames)}")

    for i, username in enumerate(valid_usernames, 1):
        await send_log(f"🔹 Обрабатываю {i}/{len(valid_usernames)} → @{username}")
        await report_bot(username, message.chat.id)

        if i < len(valid_usernames):
            await send_log(f"⏳ Жду {DELAY_BETWEEN_BOTS} сек перед следующим ботом...")
            await asyncio.sleep(DELAY_BETWEEN_BOTS)

    await send_log("🎉 ВСЕ ГОТОВО. Все жалобы отправлены.")

async def main():
    print("Запуск бота...")
    await client.start()
    print("Telethon сессия готова")
    
    await send_log("🛸 Сессия Telethon запущена. Бот готов к приёму команд.", ALLOWED_USER_ID)
    
    # Удаляем вебхук, если он активен
    await bot.delete_webhook()
    print("Webhook удалён")
    
    await bot.infinity_polling(skip_pending=True)

if __name__ == '__main__':
    asyncio.run(main())