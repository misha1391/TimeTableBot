import json
import logging  # Вывод отчетов о работе Бота (Ошибки, добавление и удаление книг м тд ..)
from datetime import datetime  # Дата и время для уведомлений и логов
from pathlib import Path  # для того чтобы найти папку data с данными для программы

from telegram import Update, \
    ReplyKeyboardMarkup  # Подключаем Update - Ловит все действия пользователей в чатах. Второе для создания кнопок
from telegram.ext import (
    Application,  # Основной класс для работы бота. Запускает бота.
    CommandHandler,  # Ловит команды по типу /start
    ContextTypes,  # Для определения типа сообщения текст/команда/фото/видео/ответ
    MessageHandler,  # Если не команда текст
    filters
)

from config import BOT_TOKEN

# Настройка логирования (вывод отчета в консоль)
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)  # Запуск логирования

# Пути к данным
DATA_DIR = Path("data")
TIME_FILE = DATA_DIR / "timeTable.json"

DATA_DIR.mkdir(exist_ok=True)  # Если такой паки нет => создать ее

def load_timeTable():
    if TIME_FILE.exists():  # Если файл books.json есть то открываем и считываем
        with open(TIME_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return []
def save_timeTable(data):
    with open(TIME_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

# Загрузка данных для бота
timeTable = load_timeTable()

# Получить настоящее время в секундах
def getCurrentTime():
    _curTime = datetime.now()
    _hours = _curTime.hour * 3600
    _minutes = _curTime.minute * 60
    _seconds = _curTime.second
    return _hours + _minutes + _seconds

# Получить день недели
def getWeekday():
    return datetime.now().weekday()

# 24:00 в секунды
def fromStrToSeconds(_time: str):
     _timeInInt = [int(i) for i in _time.split(':', _time)]
     _hoursS = _timeInInt[0] * 3600
     _minutesS = _timeInInt[1] * 60
     return _hoursS + _minutesS
# Получить время из json файла формата 24:00 на сегодня
def getAllTimes():
    return timeTable[getWeekday()]

def getNextTime():
    _tableTimes = getAllTimes()
    _nextTime = 0
    try:
        for i in range(_tableTimes):
            _nextTime = _tableTimes
            if _tableTimes[i-1] < _nextTime < _tableTimes[i+1]:
                return _nextTime
    except:
        pass
    return 0

# Получить разницу для when в job-queue
def getTimeToWhen():
    return getNextTime() - getCurrentTime()

# /start
async def start(update: Update,
                context: ContextTypes.DEFAULT_TYPE):  # context помогает нам хранить информацию о боте и пользователе + помогает Pycharm Давать подсказет
    await update.message.reply_text(  # Отправка сообщения пользователю
        "Добро пожаловать в бота для напоминания расписания!"
    )
# Напоминание
async def handle_remind(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if context.job_queue is None:  # Проверяем доступность уведомлений
        await update.message.reply_text(
            "⚠️ Напоминания недоступны.",
        )
        return

    user_id = update.effective_user.id
    current_jobs = context.job_queue.get_jobs_by_name(str(user_id))
    for job in current_jobs:
        job.schedule_removal()

    When = getTimeToWhen()
    if When < 0:
        await update.message.reply_text("⏰ Напоминаний больше нет")
    else:
        context.job_queue.run_once(
            send_reminder,
            when=When,
            chat_id=user_id,
            name=str(user_id)
        )
        await update.message.reply_text("⏰ Напоминание установлено на ", getTimeToWhen())
# Получить отрывок
async def send_reminder(context: ContextTypes.DEFAULT_TYPE):
    job = context.job  # Получаем задаение об отправке сообщения
    await context.bot.send_message(
        chat_id=job.chat_id,  # Говорим боту кому отправить напоминание
        text="📖 Не забудьте почитать сегодня! Нажмите «Получить отрывок» в меню.",
    )
# Обработка текстовых сообщений
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    # Прикрепляем к тексту сответствующиие команды
    if text == "⏰ Напоминание о чтении":
        return await handle_remind(update, context)

    # Неизвестный ввод
    await update.message.reply_text("Пожалуйста, используйте кнопки меню.")

# Основная функция
if __name__ == "__main__":
    application = Application.builder().token(BOT_TOKEN).build()  # Инициализируем Бота (Создаем)

    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    logger.info("Бот запущен с кнопками и функцией 'Мои прочитанные'...")
    application.run_polling()  # Запускаем Бота