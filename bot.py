import logging
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters
from telegram import Update
from telegram.ext import CallbackContext
from openai import OpenAI

# Настройка логирования
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# Инициализация OpenAI клиента
openai_client = OpenAI(api_key="YOUR_OPENAI_API_KEY")  # Вставь свой API-ключ здесь

# Системный промпт для ChatGPT
SYSTEM_PROMPT = "YOUR_SYSTEM_PROMPT"  # Вставь свой системный промпт здесь

# Глобальные переменные для хранения состояния сессии
session_active = False
session_messages = []
bot_username = None  # Будет установлено при запуске бота

# Функция для проверки, является ли сообщение командой
def is_epignostika_command(text: str) -> bool:
    return text.lower() in ["эпигностика. начало", "эпигностика. далее", "эпигностика. конец"]

# Обработчик команды "Эпигностика. Начало"
def start_session(update: Update, context: CallbackContext) -> None:
    global session_active, session_messages
    if update.message.chat.type in ['group', 'supergroup']:
        if update.message.text.lower() == "эпигностика. начало":
            session_active = True
            session_messages = []  # Очищаем историю сообщений
            update.message.reply_text("Сессия с ChatGPT начата. Пишите сообщения, а затем используйте 'Эпигностика. Далее' для получения ответа.")
        else:
            update.message.reply_text("Сессия уже активна или команда неверная.")

# Обработчик команды "Эпигностика. Далее"
def process_messages(update: Update, context: CallbackContext) -> None:
    global session_active, session_messages
    if update.message.chat.type in ['group', 'supergroup'] and session_active:
        if update.message.text.lower() == "эпигностика. далее":
            if not session_messages:
                update.message.reply_text("Нет сообщений для обработки. Напишите что-нибудь перед использованием 'Эпигностика. Далее'.")
                return

            # Компонуем сообщения в один текст
            compiled_text = "\n".join([f"@{msg['username']}: {msg['text']}" for msg in session_messages])
            logger.info(f"Скомпонованный текст: {compiled_text}")

            try:
                # Отправляем запрос в ChatGPT
                response = openai_client.chat.completions.create(
                    model="gpt-4",  # Или другой доступный модель, например, "gpt-3.5-turbo"
                    messages=[
                        {"role": "system", "content": SYSTEM_PROMPT},
                        {"role": "user", "content": compiled_text}
                    ],
                    max_tokens=500  # Ограничение на длину ответа
                )
                # Получаем ответ от ChatGPT
                chatgpt_response = response.choices[0].message.content

                # Отправляем ответ в чат
                update.message.reply_text(chatgpt_response)

            except Exception as e:
                logger.error(f"Ошибка при запросе к OpenAI: {e}")
                update.message.reply_text("Извините, произошла ошибка при обработке запроса.")
        else:
            update.message.reply_text("Сессия не активна или команда неверная.")
    else:
        update.message.reply_text("Сессия не активна. Начните с 'Эпигностика. Начало'.")

# Обработчик команды "Эпигностика. Конец"
def end_session(update: Update, context: CallbackContext) -> None:
    global session_active, session_messages
    if update.message.chat.type in ['group', 'supergroup'] and session_active:
        if update.message.text.lower() == "эпигностика. конец":
            session_active = False
            session_messages = []
            update.message.reply_text("Сессия с ChatGPT завершена. Используйте 'Эпигностика. Начало' для новой сессии.")
        else:
            update.message.reply_text("Сессия не активна или команда неверная.")
    else:
        update.message.reply_text("Сессия не активна. Начните с 'Эпигностика. Начало'.")

# Обработчик текстовых сообщений
def handle_message(update: Update, context: CallbackContext) -> None:
    global session_active, session_messages, bot_username
    if update.message.chat.type in ['group', 'supergroup'] and session_active:
        # Игнорируем сообщения от бота (ответы ChatGPT)
        if update.message.from_user.username != bot_username:
            # Игнорируем команды "Эпигностика"
            if not is_epignostika_command(update.message.text.lower()):
                # Сохраняем сообщение пользователя
                session_messages.append({
                    "username": update.message.from_user.username or update.message.from_user.first_name,
                    "text": update.message.text
                })
                logger.info(f"Сохранено сообщение от @{update.message.from_user.username}: {update.message.text}")

# Функция для получения имени бота
def set_bot_username(context: CallbackContext) -> None:
    global bot_username
    bot_username = context.bot.get_me().username
    logger.info(f"Имя бота установлено: {bot_username}")

# Основная функция для запуска бота
def main() -> None:
    # Токен бота от BotFather
    updater = Updater("YOUR_TELEGRAM_BOT_TOKEN", use_context=True)  # Вставь токен бота

    # Получаем диспетчер для регистрации обработчиков
    dp = updater.dispatcher

    # Устанавливаем имя бота
    set_bot_username(dp.bot)

    # Обработчики текстовых сообщений
    dp.add_handler(MessageHandler(Filters.text & ~Filters.command & Filters.regex(r'^(?i)Эпигностика\. Начало$'), start_session))
    dp.add_handler(MessageHandler(Filters.text & ~Filters.command & Filters.regex(r'^(?i)Эпигностика\. Далее$'), process_messages))
    dp.add_handler(MessageHandler(Filters.text & ~Filters.command & Filters.regex(r'^(?i)Эпигностика\. Конец$'), end_session))
    dp.add_handler(MessageHandler(Filters.text & ~Filters.command, handle_message))

    # Запускаем бота
    updater.start_polling()
    logger.info("Бот запущен")
    updater.idle()

if __name__ == '__main__':
    main()