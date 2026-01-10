import telebot
import os
import json
import logging
from datetime import datetime
from typing import Dict, Any


# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Инициализация бота
bot = telebot.TeleBot("8379708495:AAGWhbXpOVC5Xj7mPdAWJKP-8eVBS6RPHHQ")  # Замените на свой токен

# Файл для хранения статистики пользователей
USERS_FILE = "users_data.json"
# Путь к вашему ZIP-архиву
ZIP_FILE_PATH = "https://github.com/Fgmod/TGbot/blob/cb1b96ae0185d6d2aa564576e6575efab788e987/AltShift_Fast.zip"  # Замените на реальный путь

# Класс для управления пользователями
class UserManager:
    def __init__(self, filename: str):
        self.filename = filename
        self.users: Dict[str, Dict[str, Any]] = self.load_users()

    def load_users(self) -> Dict[str, Dict[str, Any]]:
        """Загружает данные пользователей из файла"""
        try:
            if os.path.exists(self.filename):
                with open(self.filename, 'r', encoding='utf-8') as f:
                    return json.load(f)
        except Exception as e:
            logger.error(f"Ошибка загрузки пользователей: {e}")
        return {}

    def save_users(self):
        """Сохраняет данные пользователей в файл"""
        try:
            with open(self.filename, 'w', encoding='utf-8') as f:
                json.dump(self.users, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"Ошибка сохранения пользователей: {e}")

    def add_user(self, user_id: str, username: str, first_name: str, last_name: str = ""):
        """Добавляет/обновляет информацию о пользователе"""
        if user_id not in self.users:
            self.users[user_id] = {
                "username": username,
                "first_name": first_name,
                "last_name": last_name,
                "join_date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "downloads": 0,
                "last_active": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }
            logger.info(f"Добавлен новый пользователь: {username} ({user_id})")
        else:
            self.users[user_id]["last_active"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            self.users[user_id]["username"] = username
            self.users[user_id]["first_name"] = first_name
            if last_name:
                self.users[user_id]["last_name"] = last_name

        self.save_users()

    def increment_download(self, user_id: str):
        """Увеличивает счетчик скачиваний для пользователя"""
        if user_id in self.users:
            self.users[user_id]["downloads"] += 1
            self.save_users()

    def get_total_users(self) -> int:
        """Возвращает общее количество пользователей"""
        return len(self.users)

    def get_active_today(self) -> int:
        """Возвращает количество пользователей, активных сегодня"""
        today = datetime.now().strftime("%Y-%m-%d")
        count = 0
        for user_data in self.users.values():
            if user_data.get("last_active", "").startswith(today):
                count += 1
        return count


# Инициализация менеджера пользователей
user_manager = UserManager(USERS_FILE)

# Проверка существования ZIP-файла
if not os.path.exists(ZIP_FILE_PATH):
    logger.warning(f"ZIP файл не найден по пути: {ZIP_FILE_PATH}")
    logger.info("Бот будет работать, но функция скачивания недоступна")
    ZIP_AVAILABLE = False
else:
    ZIP_AVAILABLE = True
    file_size = os.path.getsize(ZIP_FILE_PATH) / (1024 * 1024)  # Размер в МБ
    logger.info(f"ZIP файл найден. Размер: {file_size:.2f} MB")


# Обработчик команды /start
@bot.message_handler(commands=['start'])
def send_welcome(message):
    """Приветственное сообщение"""
    user_id = str(message.from_user.id)
    username = message.from_user.username or "без username"
    first_name = message.from_user.first_name or ""
    last_name = message.from_user.last_name or ""

    # Добавляем пользователя в базу
    user_manager.add_user(user_id, username, first_name, last_name)

    # Формируем приветственное сообщение
    welcome_text = f"""
👋 Привет, {first_name}!

Я бот для распространения приложения -AltShift-.

📊 Статистика на данный момент:
• Всего пользователей: {user_manager.get_total_users()}
• Активных сегодня: {user_manager.get_active_today()}

✨ Доступные команды:
/start - Приветственное сообщение
/stats - Показать статистику
/download - Скачать приложение
/help - Помощь и инструкции

📱 Для связи с разработчиком: https://t.me/carXa7
    """

    bot.reply_to(message, welcome_text)


# Обработчик команды /stats
@bot.message_handler(commands=['stats'])
def show_stats(message):
    """Показать статистику пользователей"""
    user_id = str(message.from_user.id)

    # Обновляем активность пользователя
    if user_id in user_manager.users:
        user_manager.users[user_id]["last_active"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        user_manager.save_users()

    stats_text = f"""
📈 СТАТИСТИКА БОТА:

👥 Пользователи:
• Всего зарегистрировано: {user_manager.get_total_users()}
• Активных сегодня: {user_manager.get_active_today()}

📥 Скачивания приложения:
• Всего скачиваний: {sum(user["downloads"] for user in user_manager.users.values())}

🏆 Топ-5 скачивающих:
{get_top_downloaders()}

🔄 Бот обновлен: {datetime.now().strftime("%d.%m.%Y %H:%M")}
    """

    bot.reply_to(message, stats_text)


def get_top_downloaders() -> str:
    """Возвращает строку с топом скачивающих"""
    top_users = sorted(
        [(data["first_name"], data["downloads"])
         for data in user_manager.users.values() if data["downloads"] > 0],
        key=lambda x: x[1],
        reverse=True
    )[:5]

    if not top_users:
        return "Пока нет данных о скачиваниях"

    result = ""
    for i, (name, downloads) in enumerate(top_users, 1):
        result += f"{i}. {name}: {downloads} скач.\n"

    return result


# Обработчик команды /download
@bot.message_handler(commands=['download'])
def send_application(message):
    """Отправка ZIP-архива с приложением"""
    user_id = str(message.from_user.id)

    if not ZIP_AVAILABLE:
        bot.reply_to(message, "❌ Файл приложения временно недоступен. Попробуйте позже.")
        return

    # Отправляем сообщение о начале загрузки
    bot.send_chat_action(message.chat.id, 'upload_document')

    try:
        # Читаем размер файла
        file_size_mb = os.path.getsize(ZIP_FILE_PATH) / (1024 * 1024)

        # Отправляем файл
        with open(ZIP_FILE_PATH, 'rb') as zip_file:
            bot.send_document(
                message.chat.id,
                zip_file,
                caption=f"""
📦 Ваше приложение готово к скачиванию!

📝 Инструкция по установки:
1. Скачайте этот архив
2. Распакуйте в любую папку
3. Запустите файл .exe из распакованной папки

⚠️ Примечания:
• Антивирус может запросить разрешение (это нормально)
• Не удаляйте и не перемещайте файлы внутри папки
• Размер архива: {file_size_mb:.1f} МБ

🔄 Если необходимо, то после установки перезагрузите компьютер(необязательно)

❓ Проблемы? Пишите: https://t.me/carXa7
                """
            )

        # Увеличиваем счетчик скачиваний
        user_manager.increment_download(user_id)

        # Отправляем дополнительное сообщение
        bot.send_message(
            message.chat.id,
            "✅ Файл успешно отправлен! Проверьте вложения выше.\n\n"
            "Если возникли проблемы со скачиванием, попробуйте команду /download еще раз."
        )

        logger.info(f"Пользователь {user_id} скачал приложение")

    except Exception as e:
        error_msg = f"❌ Ошибка при отправке файла: {str(e)}"
        bot.reply_to(message, error_msg)
        logger.error(f"Ошибка отправки файла пользователю {user_id}: {e}")


# Обработчик команды /help
@bot.message_handler(commands=['help'])
def send_help(message):
    """Помощь и инструкции"""
    help_text = """
🆘 ПОМОЩЬ И ИНСТРУКЦИИ

📋 Основные команды:
/start - Начать работу с ботом
/stats - Статистика пользователей
/download - Скачать приложение
/help - Эта справка

📥 Как установить приложение:
1. Используйте команду /download
2. Сохраните архив на компьютер
3. Распакуйте архив программой WinRAR или 7-Zip
4. Запустите файл .exe из распакованной папки

⚠️ Возможные проблемы:
• Антивирус блокирует файл - добавьте в исключения
• Файл не запускается - установите Microsoft Visual C++ Redistributable
• Архив поврежден - попробуйте скачать заново

💬 Техническая поддержка:
По всем вопросам пишите: https://t.me/carXa7

🌐 Дополнительные ресурсы:
• GitHub: https://github.com/Fgmod/AltShift-v1.0.0
    """

    bot.reply_to(message, help_text)


# Обработчик текстовых сообщений
@bot.message_handler(func=lambda message: True)
def handle_text(message):
    """Обработка текстовых сообщений"""
    user_id = str(message.from_user.id)

    # Простое эхо с предложением команд
    response = f"Привет, {message.from_user.first_name}! 👋\n\n"
    response += "Я понимаю только команды. Попробуйте:\n"
    response += "/start - для начала работы\n"
    response += "/help - для получения справки"

    bot.reply_to(message, response)


# Функция для автоматической отправки статистики
def send_daily_stats():
    """Отправка ежедневной статистики (можно запускать по расписанию)"""
    stats = f"""
📊 ЕЖЕДНЕВНАЯ СТАТИСТИКА
Дата: {datetime.now().strftime('%d.%m.%Y')}

👥 Пользователи: {user_manager.get_total_users()}
📥 Скачиваний сегодня: {user_manager.get_active_today()}
🆕 Новых пользователей: {len([u for u in user_manager.users.values()
                             if u['join_date'].startswith(datetime.now().strftime('%Y-%m-%d'))])}
    """

    # Здесь можно добавить отправку в канал или админу
    # bot.send_message(CHANNEL_ID, stats)
    logger.info(f"Ежедневная статистика: {stats}")


# Основная функция запуска бота
def main():
    """Запуск бота"""
    logger.info("Запуск Telegram бота...")
    logger.info(f"Всего пользователей в базе: {user_manager.get_total_users()}")
    logger.info(f"ZIP файл доступен: {ZIP_AVAILABLE}")

    # Запуск бота
    try:
        bot.infinity_polling(timeout=60, long_polling_timeout=60)
    except Exception as e:
        logger.error(f"Ошибка в работе бота: {e}")


# Запуск при условии, что файл запускается напрямую
if __name__ == "__main__":
    # ИСПРАВЛЕНИЕ: Создаем папку для данных, только если указан путь к папке
    users_dir = os.path.dirname(USERS_FILE)
    if users_dir:  # Если указана папка (например, "data/users.json")
        os.makedirs(users_dir, exist_ok=True)
        logger.info(f"Создана папка для данных: {users_dir}")

    # Альтернативный вариант - просто использовать текущую директорию
    # и создать файл в ней
    if not os.path.exists(USERS_FILE):
        # Создаем пустой файл, если его нет
        with open(USERS_FILE, 'w', encoding='utf-8') as f:
            json.dump({}, f)
        logger.info(f"Создан файл данных: {USERS_FILE}")

    # Запускаем бота
    main()
