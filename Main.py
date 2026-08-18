import asyncio
from telebot.async_telebot import AsyncTeleBot
from pyrogram import Client
from pyrogram.errors import FloodWait, RPCError
from pyrogram.raw.functions.account import ReportPeer
from pyrogram.raw.types import InputReportReasonOther
from pyrogram.raw.types import InputPeerUser, InputPeerChannel, InputPeerChat
import os

BOT_TOKEN = "8575618466:AAHqMlwE-fOq7kwANSqTeDnLJJ81skHcghs"

API_ID = 25874957
API_HASH = "c89ef6fd9ba5c8a479abb1f4d2de248d"

ALLOWED_USER_ID = 608502324

REPORT_TEXT = (
    "Открытый доксинг бот. Прописка, паспортные данные, номера телефонов, "
    "ИНН, СНИЛС, фото паспорта, адреса регистрации и проживания, "
    "родственники, кредитная история. Прошу принять меры."
)

REPORTS_PER_BOT = 5
DELAY_BETWEEN_REPORTS = 0.8
DELAY_BETWEEN_BOTS = 2.0

bot = AsyncTeleBot(BOT_TOKEN)

# Глобальные переменные для авторизации
USER_CHAT_ID = None
client = None
auth_phone = None
auth_phone_hash = None
auth_code = None
auth_password = None
auth_waiting = False
auth_step = None  # 'phone', 'code', 'password'


async def init_client():
    """Инициализирует клиент Pyrogram с сессией, если она существует"""
    global client
    
    if os.path.exists("session.session"):
        try:
            client = Client("session", api_id=API_ID, api_hash=API_HASH)
            await client.start()
            print("✅ Сессия Pyrogram загружена")
            return True
        except Exception as e:
            print(f"❌ Ошибка загрузки сессии: {e}")
            client = None
            return False
    else:
        print("📱 Сессия не найдена, ждём авторизацию через бота")
        return False


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


async def complete_auth():
    """Завершает авторизацию в Pyrogram"""
    global client, auth_waiting, auth_step, auth_phone, auth_phone_hash, auth_code, auth_password
    
    try:
        if auth_step == 'code':
            try:
                client = Client("session", api_id=API_ID, api_hash=API_HASH)
                await client.connect()
                await client.sign_in(auth_phone, auth_phone_hash, auth_code)
            except Exception as e:
                if "SESSION_PASSWORD_NEEDED" in str(e) or "PasswordHash" in str(e):
                    auth_step = 'password'
                    auth_waiting = True
                    await send_log("🔐 Требуется пароль 2FA.\nОтправь свой пароль:", USER_CHAT_ID)
                    return False
                raise e
                
        elif auth_step == 'password':
            await client.check_password(auth_password)
        
        await send_log("✅ Авторизация успешна! Сессия сохранена.")
        auth_waiting = False
        auth_step = None
        return True
    except Exception as e:
        error_msg = str(e)
        if 'password' in error_msg.lower() or '2fa' in error_msg.lower() or 'SESSION_PASSWORD_NEEDED' in error_msg:
            auth_step = 'password'
            auth_waiting = True
            await send_log("🔐 Требуется пароль 2FA.\nОтправь свой пароль:", USER_CHAT_ID)
            return False
        await send_log(f"❌ Ошибка авторизации: {e}")
        return False


@bot.message_handler(commands=['start'])
async def start(message):
    global USER_CHAT_ID, auth_waiting, auth_step, client
    
    if message.from_user.id != ALLOWED_USER_ID:
        await bot.reply_to(message, "Access denied.")
        return

    USER_CHAT_ID = message.chat.id
    
    # Проверяем, есть ли сессия
    if not await init_client():
        auth_waiting = True
        auth_step = 'phone'
        await send_log(
            "📱 Для авторизации отправь свой номер телефона в формате:\n"
            "+71234567890\n\n"
            "⚠️ Номер должен быть привязан к аккаунту Telegram",
            message.chat.id
        )
        return
    
    await send_log(
        "✅ Бот запущен (Pyrogram).\n"
        "Отправь список юзернеймов ботов (по одному в строке)\n"
        "Пример:\n"
        "@sexgodbot\n"
        "@findher_bot\n"
        "@leakbase_bot",
        message.chat.id
    )


@bot.message_handler(func=lambda m: True)
async def handle_message(message):
    global USER_CHAT_ID, auth_waiting, auth_step, auth_phone, auth_phone_hash, auth_code, auth_password, client
    
    if message.from_user.id != ALLOWED_USER_ID:
        return

    USER_CHAT_ID = message.chat.id
    
    # Обработка авторизации
    if auth_waiting:
        if auth_step == 'phone':
            auth_phone = message.text.strip()
            try:
                # Временно создаем клиент для отправки кода
                client = Client("session", api_id=API_ID, api_hash=API_HASH)
                await client.connect()
                sent_code = await client.send_code(auth_phone)
                auth_phone_hash = sent_code.phone_code_hash
                auth_step = 'code'
                await send_log(
                    f"📱 Код отправлен на номер {auth_phone}\n"
                    "Отправь код подтверждения из Telegram:",
                    message.chat.id
                )
            except Exception as e:
                await send_log(f"❌ Ошибка: {e}\nПопробуй снова отправить номер.", message.chat.id)
                auth_step = 'phone'
                
        elif auth_step == 'code':
            auth_code = message.text.strip()
            await send_log("⏳ Проверяю код...", message.chat.id)
            
            if await complete_auth():
                auth_waiting = False
                auth_step = None
                await send_log(
                    "✅ Бот готов!\n"
                    "Отправь список юзернеймов ботов (по одному в строке)",
                    message.chat.id
                )
            elif auth_step != 'password':
                await send_log(
                    "❌ Неверный код. Попробуй снова:\n"
                    "Отправь код подтверждения из Telegram:",
                    message.chat.id
                )
                
        elif auth_step == 'password':
            auth_password = message.text.strip()
            await send_log("⏳ Проверяю пароль...", message.chat.id)
            
            if await complete_auth():
                auth_waiting = False
                auth_step = None
                await send_log(
                    "✅ Бот готов!\n"
                    "Отправь список юзернеймов ботов (по одному в строке)",
                    message.chat.id
                )
            else:
                await send_log(
                    "❌ Неверный пароль. Попробуй снова:\n"
                    "🔐 Отправь пароль 2FA:",
                    message.chat.id
                )
        return
    
    # Если сессии нет и не в режиме авторизации
    if not client or not await init_client():
        await send_log("⚠️ Требуется авторизация. Отправь /start", message.chat.id)
        return
    
    # Основная логика (список ботов)
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


async def report_bot(username: str, chat_id: int):
    try:
        await send_log(f"[+] Начинаю жалобы на @{username}")

        # Получаем пользователя/бота через Pyrogram
        peer_obj = await client.resolve_peer(username)
        user_entity = await client.get_users(username)

        await send_log(f"[+] Бот найден: @{username} (ID: {user_entity.id})")

        for i in range(REPORTS_PER_BOT):
            try:
                # Отправка жалобы через raw API Pyrogram
                await client.invoke(
                    ReportPeer(
                        peer=peer_obj,
                        reason=InputReportReasonOther(),
                        message=REPORT_TEXT
                    )
                )
                await send_log(f"    ✅ Жалоба {i+1}/{REPORTS_PER_BOT} отправлена")
            except FloodWait as e:
                await send_log(f"    ⏳ Сработал FloodWait. Жду {e.value} секунд...")
                await asyncio.sleep(e.value)
                # Повторная попытка после флуд-веийта
                await client.invoke(
                    ReportPeer(
                        peer=peer_obj,
                        reason=InputReportReasonOther(),
                        message=REPORT_TEXT
                    )
                )
                await send_log(f"    ✅ Жалоба {i+1}/{REPORTS_PER_BOT} отправлена после ожидания")
            except Exception as e:
                await send_log(f"    ❌ Ошибка {i+1}/{REPORTS_PER_BOT}: {str(e)}")

            if i < REPORTS_PER_BOT - 1:
                await asyncio.sleep(DELAY_BETWEEN_REPORTS)

        await send_log(f"{REPORTS_PER_BOT} снежков отправлено на @{username} ")

    except Exception as e:
        await send_log(f"[-] Ошибка с @{username}: {str(e)}")


async def main():
    global client
    
    print("Запуск бота...")
    
    if not await init_client():
        print("⏳ Ожидание авторизации через бота...")
    else:
        print("✅ Сессия Pyrogram готова")
        await send_log("🛸 Сессия Pyrogram запущена. Бот готов к приёму команд.", ALLOWED_USER_ID)
    
    await bot.delete_webhook()
    print("Webhook удалён")
    
    await bot.infinity_polling(skip_pending=True)


if __name__ == '__main__':
    asyncio.run(main())
