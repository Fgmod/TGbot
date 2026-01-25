import telebot
import os
import json
import logging
from datetime import datetime
from typing import Dict, Any
from flask import Flask, request, jsonify, render_template_string
import threading
import time
from dotenv import load_dotenv

# Загружаем переменные окружения
load_dotenv()

# Создаем Flask приложение
app = Flask(__name__)

# Глобальная переменная для статуса бота
bot_status = {
    "is_running": False,
    "last_start": None,
    "error_count": 0
}

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('bot.log', encoding='utf-8')
    ]
)
logger = logging.getLogger(__name__)

# Токен из переменных окружения
BOT_TOKEN = os.getenv("BOT_TOKEN", "8498564975:AAHDRpdELwIjlxm0o2ueNYf0dHqZvicU58c")
if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN не установлен. Установите его в переменных окружения.")

bot = telebot.TeleBot(BOT_TOKEN)

# Определяем базовую директорию
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Файлы теперь в той же директории
USERS_FILE = os.path.join(BASE_DIR, "users_data.json")
ZIP_FILE_PATH = os.path.join(BASE_DIR, "AltShift_Fast.zip")

logger.info(f"Базовая директория: {BASE_DIR}")
logger.info(f"Путь к ZIP: {ZIP_FILE_PATH}")
logger.info(f"Путь к данным: {USERS_FILE}")

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
            else:
                logger.info(f"Файл {self.filename} не найден, создаем новый")
                # Создаем пустой файл
                with open(self.filename, 'w', encoding='utf-8') as f:
                    json.dump({}, f)
                return {}
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
    
    def get_statistics(self) -> Dict[str, Any]:
        """Возвращает статистику"""
        return {
            "total_users": self.get_total_users(),
            "active_today": self.get_active_today(),
            "total_downloads": sum(user["downloads"] for user in self.users.values()),
            "last_updated": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }


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


# Маршруты Flask
@app.route('/')
def home():
    """Главная страница"""
    stats = user_manager.get_statistics()
    html = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>AltShift Telegram Bot</title>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <style>
            body {
                font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                max-width: 1000px;
                margin: 0 auto;
                padding: 20px;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                min-height: 100vh;
                color: white;
            }
            .container {
                background: rgba(255, 255, 255, 0.95);
                border-radius: 20px;
                padding: 40px;
                box-shadow: 0 20px 60px rgba(0, 0, 0, 0.3);
                color: #333;
            }
            h1 {
                color: #667eea;
                text-align: center;
                margin-bottom: 30px;
                font-size: 2.5em;
            }
            .status-card {
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                color: white;
                padding: 25px;
                border-radius: 15px;
                margin-bottom: 30px;
                text-align: center;
            }
            .stats-grid {
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
                gap: 20px;
                margin: 30px 0;
            }
            .stat-card {
                background: white;
                border-radius: 15px;
                padding: 25px;
                text-align: center;
                box-shadow: 0 5px 15px rgba(0, 0, 0, 0.1);
                border: 2px solid #667eea;
                transition: transform 0.3s ease;
            }
            .stat-card:hover {
                transform: translateY(-5px);
            }
            .stat-card h3 {
                color: #764ba2;
                margin-top: 0;
                font-size: 1.2em;
            }
            .stat-value {
                font-size: 2.5em;
                font-weight: bold;
                color: #667eea;
                margin: 10px 0;
            }
            .bot-info {
                background: #f8f9fa;
                border-radius: 15px;
                padding: 20px;
                margin-top: 30px;
                border-left: 5px solid #667eea;
            }
            .btn {
                display: inline-block;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                color: white;
                padding: 12px 30px;
                border-radius: 50px;
                text-decoration: none;
                font-weight: bold;
                margin: 10px;
                transition: transform 0.3s ease, box-shadow 0.3s ease;
                border: none;
                cursor: pointer;
            }
            .btn:hover {
                transform: translateY(-2px);
                box-shadow: 0 10px 20px rgba(102, 126, 234, 0.4);
            }
            .uptime {
                font-size: 0.9em;
                color: #666;
                margin-top: 10px;
            }
            .online {
                color: #4CAF50;
                font-weight: bold;
                animation: pulse 2s infinite;
            }
            @keyframes pulse {
                0% { opacity: 1; }
                50% { opacity: 0.7; }
                100% { opacity: 1; }
            }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>🤖 AltShift Telegram Bot</h1>
            
            <div class="status-card">
                <h2>Статус: <span class="online">● ONLINE</span></h2>
                <p>Бот работает 24/7 и готов отвечать на запросы</p>
                <div class="uptime">
                    Запущен: {{ start_time }}<br>
                    Ошибок: {{ error_count }}
                </div>
            </div>
            
            <div class="stats-grid">
                <div class="stat-card">
                    <h3>👥 Всего пользователей</h3>
                    <div class="stat-value">{{ total_users }}</div>
                    <p>зарегистрировано в боте</p>
                </div>
                
                <div class="stat-card">
                    <h3>📊 Активных сегодня</h3>
                    <div class="stat-value">{{ active_today }}</div>
                    <p>пользователей</p>
                </div>
                
                <div class="stat-card">
                    <h3>📥 Всего скачиваний</h3>
                    <div class="stat-value">{{ total_downloads }}</div>
                    <p>приложения</p>
                </div>
            </div>
            
            <div style="text-align: center; margin: 30px 0;">
                <a href="https://t.me/your_bot_username" class="btn" target="_blank">
                    💬 Написать боту в Telegram
                </a>
                <a href="/health" class="btn">
                    🩺 Проверить здоровье
                </a>
                <a href="/stats" class="btn">
                    📈 Детальная статистика
                </a>
            </div>
            
            <div class="bot-info">
                <h3>📋 Информация о боте:</h3>
                <p><strong>Команды:</strong> /start, /help, /stats, /download</p>
                <p><strong>ZIP файл:</strong> {% if zip_available %}✅ Доступен{% else %}❌ Не доступен{% endif %}</p>
                <p><strong>Последнее обновление:</strong> {{ last_updated }}</p>
                <p><strong>Поддержка:</strong> <a href="https://t.me/theEvil429">@theEvil429</a></p>
            </div>
        </div>
    </body>
    </html>
    """
    return render_template_string(
        html,
        total_users=stats["total_users"],
        active_today=stats["active_today"],
        total_downloads=stats["total_downloads"],
        last_updated=stats["last_updated"],
        start_time=bot_status["last_start"] or "Неизвестно",
        error_count=bot_status["error_count"],
        zip_available=ZIP_AVAILABLE
    )


@app.route('/health')
def health():
    """Проверка здоровья сервиса"""
    health_status = {
        "status": "healthy",
        "bot_running": bot_status["is_running"],
        "timestamp": datetime.now().isoformat(),
        "zip_file_available": ZIP_AVAILABLE,
        "users_file_exists": os.path.exists(USERS_FILE),
        "total_users": user_manager.get_total_users(),
        "memory_usage": os.path.getsize(USERS_FILE) if os.path.exists(USERS_FILE) else 0
    }
    return jsonify(health_status), 200


@app.route('/stats')
def api_stats():
    """API для получения статистики"""
    stats = user_manager.get_statistics()
    return jsonify(stats), 200


@app.route('/webhook', methods=['POST'])
def webhook():
    """Webhook для Telegram (опционально)"""
    if request.headers.get('content-type') == 'application/json':
        json_string = request.get_data().decode('utf-8')
        update = telebot.types.Update.de_json(json_string)
        bot.process_new_updates([update])
        return ''
    return 'Bad request', 400


@app.route('/restart', methods=['POST'])
def restart():
    """Перезапуск бота (только для админов)"""
    # Здесь можно добавить проверку авторизации
    logger.info("Получен запрос на перезапуск бота")
    return jsonify({"status": "restarting", "timestamp": datetime.now().isoformat()}), 202


# Обработчики команд Telegram бота
@bot.message_handler(commands=['start'])
def send_welcome(message):
    """Приветственное сообщение"""
    user_id = str(message.from_user.id)
    username = message.from_user.username or "без username"
    first_name = message.from_user.first_name or ""
    last_name = message.from_user.last_name or ""

    # Добавляем пользователя в базу
    user_manager.add_user(user_id, username, first_name, last_name)

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

📱 Для связи с разработчиком: https://t.me/theEvil429
    """
    bot.reply_to(message, welcome_text)


@bot.message_handler(commands=['stats'])
def show_stats(message):
    """Показать статистику пользователей"""
    user_id = str(message.from_user.id)

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


@bot.message_handler(commands=['download'])
def send_application(message):
    """Отправка ZIP-архива с приложением"""
    user_id = str(message.from_user.id)

    if not ZIP_AVAILABLE:
        bot.reply_to(message, "❌ Файл приложения временно недоступен. Попробуйте позже.")
        return

    bot.send_chat_action(message.chat.id, 'upload_document')

    try:
        file_size_mb = os.path.getsize(ZIP_FILE_PATH) / (1024 * 1024)
        
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

❓ Проблемы? Пишите: https://t.me/theEvil429
                """
            )

        user_manager.increment_download(user_id)
        
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
По всем вопросам пишите: https://t.me/theEvil429

🌐 Дополнительные ресурсы:
• GitHub: https://github.com/Fgmod/AltShift-v1.0.0
    """
    bot.reply_to(message, help_text)


@bot.message_handler(func=lambda message: True)
def handle_text(message):
    """Обработка текстовых сообщений"""
    response = f"Привет, {message.from_user.first_name}! 👋\n\n"
    response += "Я понимаю только команды. Попробуйте:\n"
    response += "/start - для начала работы\n"
    response += "/help - для получения справки"
    bot.reply_to(message, response)


def run_telegram_bot():
    """Запуск Telegram бота с автоматическим перезапуском"""
    while True:
        try:
            bot_status["is_running"] = True
            bot_status["last_start"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            
            logger.info("=" * 50)
            logger.info("Запуск Telegram бота...")
            logger.info(f"Токен: {BOT_TOKEN[:10]}...")
            logger.info(f"Всего пользователей: {user_manager.get_total_users()}")
            logger.info(f"ZIP файл доступен: {ZIP_AVAILABLE}")
            logger.info("=" * 50)

            bot.infinity_polling(timeout=60, long_polling_timeout=60, restart_on_change=True)

        except Exception as e:
            bot_status["error_count"] += 1
            bot_status["is_running"] = False
            
            logger.error(f"Бот упал с ошибкой: {e}")
            logger.info("Перезапуск через 10 секунд...")
            time.sleep(10)


def start_bot_in_thread():
    """Запуск бота в отдельном потоке"""
    bot_thread = threading.Thread(target=run_telegram_bot, daemon=True)
    bot_thread.start()
    logger.info("Telegram бот запущен в отдельном потоке")


# Запуск приложения
if __name__ == "__main__":
    # Запускаем Telegram бот в отдельном потоке
    start_bot_in_thread()
    
    # Определяем порт для Render
    port = 5000
    
    # Запускаем Flask сервер
    logger.info(f"Запуск Flask сервера на порту {port}...")
    if __name__ == "__main__":
        start_bot_in_thread()
        app.run()

