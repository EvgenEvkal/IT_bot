import telebot
from datetime import datetime
import sqlite3

# Инициализация бота
BOT_TOKEN = 'YOUR_BOT_TOKEN'
bot = telebot.TeleBot(BOT_TOKEN)

# Подключение к базе данных SQLite
conn = sqlite3.connect('bot.db', check_same_thread=False)
cursor = conn.cursor()

# Создание таблиц в базе данных
def create_tables():
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY,
            telegram_id INTEGER UNIQUE,
            first_name TEXT,
            last_name TEXT,
            role TEXT,
            class TEXT
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS works (
            id INTEGER PRIMARY KEY,
            user_id INTEGER,
            file_name TEXT,
            upload_date TEXT,
            status TEXT,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY,
            sender_id INTEGER,
            message_text TEXT,
            send_date TEXT,
            FOREIGN KEY (sender_id) REFERENCES users(id)
        )
    ''')

    conn.commit()

create_tables()

# Глобальные переменные для состояний
user_states = {}

# Команда /start
@bot.message_handler(commands=['start'])
def start(message):
    user_id = message.from_user.id
    user = get_user_by_telegram_id(user_id)

    # Автоматический вход для разработчика (пример: ID 123456789)
    if user_id == 123456789:
        add_user(user_id, "Евгений", "Вершинин", "разработчик", "9А")
        user = get_user_by_telegram_id(user_id)

    if user:
        show_main_menu(user, message)
    else:
        bot.send_message(message.chat.id, "Добро пожаловать! Пожалуйста, зарегистрируйтесь.")
        bot.send_message(message.chat.id, "Введите ваше имя и фамилию через пробел:")
        user_states[user_id] = 'registration_name'

# Обработка регистрации
@bot.message_handler(func=lambda message: user_states.get(message.from_user.id) == 'registration_name')
def registration_name(message):
    full_name = message.text.split()
    if len(full_name) != 2:
        bot.send_message(message.chat.id, "Пожалуйста, введите имя и фамилию через пробел:")
        return

    first_name, last_name = full_name
    user_states[message.from_user.id] = ('registration_class', first_name, last_name)
    bot.send_message(message.chat.id, "Выберите ваш класс:", reply_markup=get_class_keyboard())

@bot.message_handler(func=lambda message: user_states.get(message.from_user.id) and user_states[message.from_user.id][0] == 'registration_class')
def registration_class(message):
    user_id = message.from_user.id
    state = user_states[user_id]
    first_name, last_name = state[1], state[2]
    class_name = message.text

    add_user(user_id, first_name, last_name, 'ученик', class_name)
    bot.send_message(message.chat.id, "Регистрация завершена!")
    show_main_menu(get_user_by_telegram_id(user_id), message)

# Главное меню
def show_main_menu(user, message):
    markup = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add("Статистика пользователя", "Работа")
    if user['role'] in ['учитель', 'разработчик']:
        markup.add("Рассылка")
    markup.add("Выход")

    bot.send_message(message.chat.id, f"Добро пожаловать, {user['first_name']}!", reply_markup=markup)

# Обработка кнопок главного меню
@bot.message_handler(func=lambda message: message.text in ["Статистика пользователя", "Работа", "Рассылка", "Выход"])
def handle_main_menu(message):
    user_id = message.from_user.id
    user = get_user_by_telegram_id(user_id)

    if message.text == "Статистика пользователя":
        show_user_stats(user, message)
    elif message.text == "Работа":
        show_work_menu(user, message)
    elif message.text == "Рассылка" and user['role'] in ['учитель', 'разработчик']:
        handle_newsletter(message)
    elif message.text == "Выход":
        logout_user(user_id, message)

# Статистика пользователя
def show_user_stats(user, message):
    stats = f"Имя: {user['first_name']} {user['last_name']}\nКласс: {user['class']}\nРоль: {user['role']}"
    markup = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add("Назад")
    bot.send_message(message.chat.id, stats, reply_markup=markup)

# Меню работы
def show_work_menu(user, message):
    markup = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True)
    if user['role'] == 'ученик':
        markup.add("Мои работы", "Загрузить файл")
    elif user['role'] in ['учитель', 'разработчик']:
        markup.add("Получить работу")
    markup.add("Назад")
    bot.send_message(message.chat.id, "Меню работы:", reply_markup=markup)

# Загрузка файла
@bot.message_handler(content_types=['document'])
def handle_file_upload(message):
    user_id = message.from_user.id
    user = get_user_by_telegram_id(user_id)

    if user_states.get(user_id) == 'upload_file':
        file_info = bot.get_file(message.document.file_id)
        file_name = message.document.file_name
        upload_date = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

        add_work(user['id'], file_name, upload_date, 'Не рассмотрено')
        bot.send_message(message.chat.id, "Файл успешно загружен!")
        del user_states[user_id]

# Рассылка
def handle_newsletter(message):
    user_id = message.from_user.id
    bot.send_message(message.chat.id, "Введите текст для рассылки:")
    user_states[user_id] = 'newsletter'

@bot.message_handler(func=lambda message: user_states.get(message.from_user.id) == 'newsletter')
def send_newsletter(message):
    user_id = message.from_user.id
    text = message.text
    send_date = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    # Получаем всех пользователей из базы данных
    cursor.execute('SELECT telegram_id FROM users')
    users = cursor.fetchall()

    for user in users:
        try:
            bot.send_message(user[0], f"РАССЫЛКА:\n{text}")
        except Exception as e:
            print(f"Ошибка отправки сообщения пользователю {user[0]}: {e}")

    add_newsletter(user_id, text, send_date)
    bot.send_message(message.chat.id, "Рассылка успешно отправлена!")
    del user_states[user_id]

# Выход из аккаунта
def logout_user(user_id, message):
    del user_states[user_id]
    bot.send_message(message.chat.id, "Вы вышли из аккаунта.", reply_markup=telebot.types.ReplyKeyboardRemove())
    start(message)

# Вспомогательные функции для работы с базой данных
def add_user(telegram_id, first_name, last_name, role, class_name):
    cursor.execute('INSERT OR REPLACE INTO users (telegram_id, first_name, last_name, role, class) VALUES (?, ?, ?, ?, ?)',
                   (telegram_id, first_name, last_name, role, class_name))
    conn.commit()

def get_user_by_telegram_id(telegram_id):
    cursor.execute('SELECT * FROM users WHERE telegram_id = ?', (telegram_id,))
    row = cursor.fetchone()
    if row:
        return {'id': row[0], 'telegram_id': row[1], 'first_name': row[2], 'last_name': row[3], 'role': row[4], 'class': row[5]}
    return None

def add_work(user_id, file_name, upload_date, status):
    cursor.execute('INSERT INTO works (user_id, file_name, upload_date, status) VALUES (?, ?, ?, ?)',
                   (user_id, file_name, upload_date, status))
    conn.commit()

def add_newsletter(sender_id, message_text, send_date):
    cursor.execute('INSERT INTO messages (sender_id, message_text, send_date) VALUES (?, ?, ?)',
                   (sender_id, message_text, send_date))
    conn.commit()

def get_class_keyboard():
    markup = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True)
    classes = ['1А', '2Б', '3В', '4Г', '5А', '6Б', '7В', '8Г', '9А']
    for cls in classes:
        markup.add(cls)
    return markup

# Команды для разработчика
@bot.message_handler(commands=['set_role'])
def set_role(message):
    user_id = message.from_user.id
    user = get_user_by_telegram_id(user_id)

    if user and user['role'] == 'разработчик':
        args = message.text.split()
        if len(args) == 3:
            target_name = args[1]
            new_role = args[2]

            cursor.execute('UPDATE users SET role = ? WHERE first_name = ?', (new_role, target_name))
            conn.commit()
            bot.send_message(message.chat.id, f"Роль пользователя {target_name} успешно изменена на {new_role}.")
        else:
            bot.send_message(message.chat.id, "Использование: /set_role [имя] [роль]")
    else:
        bot.send_message(message.chat.id, "У вас нет прав для выполнения этой команды.")

@bot.message_handler(commands=['get_users_stats'])
def get_users_stats(message):
    user_id = message.from_user.id
    user = get_user_by_telegram_id(user_id)

    if user and user['role'] == 'разработчик':
        cursor.execute('SELECT * FROM users')
        users = cursor.fetchall()

        stats = "Статистика пользователей:\n"
        for user in users:
            stats += f"ID: {user[0]}, Имя: {user[2]} {user[3]}, Роль: {user[4]}, Класс: {user[5]}\n"

        bot.send_message(message.chat.id, stats)
    else:
        bot.send_message(message.chat.id, "У вас нет прав для выполнения этой команды.")

# Запуск бота
if __name__ == '__main__':
    bot.polling(none_stop=True)