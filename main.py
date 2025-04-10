import telebot
from telebot import types
import sqlite3
from datetime import datetime
import hashlib
import json

API_TOKEN = '7650664774:AAF8EsK7_9E_xhcF_lXwzWRJHJ810KtULr0'
bot = telebot.TeleBot(API_TOKEN)

# Подключение к БД
conn = sqlite3.connect('school_bot.db', check_same_thread=False)
cursor = conn.cursor()

# Миграция таблиц
cursor.executescript('''
CREATE TABLE IF NOT EXISTS users(
    user_id INTEGER PRIMARY KEY,
    login TEXT UNIQUE,
    password_hash TEXT,
    first_name TEXT,
    last_name TEXT,
    class TEXT,
    role TEXT,
    session_active INTEGER DEFAULT 0
);

CREATE TABLE IF NOT EXISTS works(
    work_id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    work_name TEXT,
    files JSON,
    status TEXT,
    upload_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(user_id) REFERENCES users(user_id)
);
''')

# Добавление колонки session_active (если не существует)
try:
    cursor.execute("ALTER TABLE users ADD COLUMN session_active INTEGER DEFAULT 0")
    conn.commit()
except sqlite3.OperationalError:
    pass

# Создание пользователя-разработчика
cursor.execute('''
INSERT OR REPLACE INTO users 
(user_id, login, password_hash, first_name, last_name, class, role, session_active)
VALUES (?, ?, ?, ?, ?, ?, ?, 1)
''', (
    1929255974,
    'Evgen_Evkal',
    hashlib.sha256('RITIT2023'.encode()).hexdigest(),
    'Евгений',
    'Евкаль',
    '9А',
    'Разработчик'
))
conn.commit()

# Состояния пользователей
user_states = {}

# Вспомогательные функции
def is_logged_in(user_id):
    cursor.execute("SELECT session_active FROM users WHERE user_id=?", (user_id,))
    result = cursor.fetchone()
    return result and result[0] == 1

def get_user_data(user_id):
    cursor.execute("SELECT first_name, last_name, class, role FROM users WHERE user_id=?", (user_id,))
    return cursor.fetchone()

def get_role(user_id):
    cursor.execute("SELECT role FROM users WHERE user_id=?", (user_id,))
    return cursor.fetchone()[0]

def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

# Старт
@bot.message_handler(commands=['start'])
def start(message):
    user_id = message.from_user.id
    
    if is_logged_in(user_id):
        show_main_menu(message)
    else:
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        markup.add('Регистрация', 'Войти')
        bot.send_message(message.chat.id, "Привет! Выберите действие:", reply_markup=markup)

# Регистрация
@bot.message_handler(func=lambda msg: msg.text == 'Регистрация')
def register(msg):
    user_id = msg.from_user.id
    if is_logged_in(user_id):
        bot.send_message(msg.chat.id, "Сначала выйдите из текущего аккаунта!")
        return
        
    user_states[user_id] = {"action": "register", "attempts": 0}
    bot.send_message(msg.chat.id, "Введите логин:")
    bot.register_next_step_handler(msg, process_login)

def process_login(message):
    user_id = message.from_user.id
    if message.text in ['/start', 'Назад']:
        del user_states[user_id]
        start(message)
        return
        
    login = message.text.strip()
    user_states[user_id]["login"] = login
    bot.send_message(message.chat.id, "Введите пароль:")
    bot.register_next_step_handler(message, process_password)

def process_password(message):
    user_id = message.from_user.id
    if message.text in ['/start', 'Назад']:
        del user_states[user_id]
        start(message)
        return
        
    password_hash = hash_password(message.text.strip())
    user_states[user_id]["password_hash"] = password_hash
    bot.send_message(message.chat.id, "Введите имя и фамилию:")
    bot.register_next_step_handler(message, process_name)

def process_name(message):
    user_id = message.from_user.id
    if message.text in ['/start', 'Назад']:
        del user_states[user_id]
        start(message)
        return
        
    name = message.text.split()
    if len(name) != 2:
        bot.send_message(message.chat.id, "Введите Имя Фамилию через пробел:")
        bot.register_next_step_handler(message, process_name)
        return
        
    user_states[user_id]["first_name"], user_states[user_id]["last_name"] = name
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add('7А', '8А', '9А', 'Назад')
    bot.send_message(message.chat.id, "Выберите класс:", reply_markup=markup)
    bot.register_next_step_handler(message, process_class)

def process_class(message):
    user_id = message.from_user.id
    if message.text in ['/start', 'Назад']:
        del user_states[user_id]
        start(message)
        return
        
    selected_class = message.text
    if selected_class not in ['7А', '8А', '9А']:
        bot.send_message(message.chat.id, "Неверный класс. Попробуйте снова.")
        bot.register_next_step_handler(message, process_class)
        return
        
    try:
        cursor.execute('''
            INSERT INTO users 
            (user_id, login, password_hash, first_name, last_name, class, role, session_active)
            VALUES (?, ?, ?, ?, ?, ?, ?, 1)
        ''', (
            user_id,
            user_states[user_id]["login"],
            user_states[user_id]["password_hash"],
            user_states[user_id]["first_name"],
            user_states[user_id]["last_name"],
            selected_class,
            'Ученик'
        ))
        conn.commit()
        del user_states[user_id]
        bot.send_message(message.chat.id, "Регистрация успешна!")
        show_main_menu(message)
    except sqlite3.IntegrityError:
        user_states[user_id]["attempts"] += 1
        if user_states[user_id]["attempts"] >= 3:
            bot.send_message(message.chat.id, "Слишком много попыток. Возвращаемся в меню.")
            del user_states[user_id]
            start(message)
        else:
            bot.send_message(message.chat.id, 
                f"Логин занят. Попытка {user_states[user_id]['attempts'] + 1}/3")
            register(message)

# Вход
@bot.message_handler(func=lambda msg: msg.text == 'Войти')
def login(msg):
    user_id = msg.from_user.id
    if is_logged_in(user_id):
        bot.send_message(msg.chat.id, "Вы уже вошли!")
        return
        
    user_states[user_id] = {"action": "login", "attempts": 0}
    bot.send_message(msg.chat.id, "Введите логин:")
    bot.register_next_step_handler(msg, process_login_enter)

def process_login_enter(message):
    user_id = message.from_user.id
    if message.text in ['/start', 'Назад']:
        del user_states[user_id]
        start(message)
        return
        
    login = message.text.strip()
    user_states[user_id]["login"] = login
    bot.send_message(message.chat.id, "Введите пароль:")
    bot.register_next_step_handler(message, process_password_enter)

def process_password_enter(message):
    user_id = message.from_user.id
    if message.text in ['/start', 'Назад']:
        del user_states[user_id]
        start(message)
        return
        
    password_hash = hash_password(message.text.strip())
    cursor.execute('''
        SELECT user_id 
        FROM users 
        WHERE login=? AND password_hash=?
    ''', (user_states[user_id]["login"], password_hash))
    user = cursor.fetchone()
    
    if user:
        cursor.execute('''
            UPDATE users 
            SET session_active=1 
            WHERE user_id=?
        ''', (user_id,))
        conn.commit()
        del user_states[user_id]
        bot.send_message(message.chat.id, "Вход выполнен!")
        show_main_menu(message)
    else:
        user_states[user_id]["attempts"] += 1
        if user_states[user_id]["attempts"] >= 3:
            bot.send_message(message.chat.id, "Слишком много попыток. Возвращаемся в меню.")
            del user_states[user_id]
            start(message)
        else:
            bot.send_message(message.chat.id, 
                f"Неверный логин/пароль. Попытка {user_states[user_id]['attempts'] + 1}/3")
            login(message)

# Главное меню
def show_main_menu(message):
    user_id = message.from_user.id
    user_data = get_user_data(user_id)
    if not user_data:
        start(message)
        return
        
    first_name, last_name, user_class, role = user_data
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add('Статистика', 'Работа', 'Выход')
    if role == 'Разработчик':
        markup.add('Панель разработчика')
    bot.send_message(
        message.chat.id,
        f"Добро пожаловать, {first_name} {last_name} ({user_class}, {role})",
        reply_markup=markup
    )

# Выход
@bot.message_handler(func=lambda msg: msg.text == 'Выход')
def logout(message):
    user_id = message.from_user.id
    if not is_logged_in(user_id):
        bot.send_message(message.chat.id, "Вы не вошли в аккаунт!")
        return
        
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add('Да', 'Нет')
    bot.send_message(
        message.chat.id, 
        "Выйти из аккаунта?",
        reply_markup=markup
    )
    bot.register_next_step_handler(message, confirm_logout)

def confirm_logout(message):
    user_id = message.from_user.id
    if message.text == 'Да':
        cursor.execute('''
            UPDATE users 
            SET session_active=0 
            WHERE user_id=?
        ''', (user_id,))
        conn.commit()
        bot.send_message(message.chat.id, "Выход выполнен успешно.")
        start(message)
    elif message.text == 'Нет':
        show_main_menu(message)
    else:
        bot.send_message(message.chat.id, "Выберите Да/Нет")
        logout(message)

# Работа с файлами
@bot.message_handler(func=lambda msg: msg.text == 'Работа')
def work_menu(message):
    user_id = message.from_user.id
    if not is_logged_in(user_id):
        bot.send_message(message.chat.id, "Сначала войдите в аккаунт!")
        return
        
    role = get_role(user_id)
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    
    if role in ['Ученик', 'Разработчик']:
        markup.add('Мои работы', 'Загрузить работу', 'Назад')
    if role in ['Учитель', 'Разработчик']:
        markup.add('Проверить работы', 'Назад')
        
    bot.send_message(message.chat.id, "Меню работы:", reply_markup=markup)
    bot.register_next_step_handler(message, handle_work_menu)

def handle_work_menu(message):
    if message.text == 'Назад':
        show_main_menu(message)
        return
        
    if message.text == 'Загрузить работу':
        start_work_upload(message)
    elif message.text == 'Мои работы':
        show_my_works(message)
    elif message.text == 'Проверить работы':
        check_works(message)
    else:
        bot.send_message(message.chat.id, "Неизвестная команда")
        work_menu(message)

# Загрузка работы (несколько файлов)
def start_work_upload(message):
    user_id = message.from_user.id
    if not is_logged_in(user_id):
        bot.send_message(message.chat.id, "Сначала войдите в аккаунт!")
        return
        
    user_states[user_id] = {"action": "upload", "files": []}
    bot.send_message(message.chat.id, "Отправьте файлы для работы. После завершения введите /done")
    bot.register_next_step_handler(message, process_file_upload)

def process_file_upload(message):
    user_id = message.from_user.id
    
    if message.text == '/done':
        if not user_states[user_id]["files"]:
            bot.send_message(message.chat.id, "Нет файлов для сохранения")
            work_menu(message)
            return
            
        user_data = get_user_data(user_id)
        first_name, last_name = user_data[0], user_data[1]
        date = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        work_name = f"{last_name}_{first_name}/{date}"
        
        cursor.execute('''
            INSERT INTO works 
            (user_id, work_name, files, status)
            VALUES (?, ?, ?, ?)
        ''', (
            user_id,
            work_name,
            json.dumps(user_states[user_id]["files"]),
            'Не проверено'
        ))
        conn.commit()
        del user_states[user_id]
        bot.send_message(message.chat.id, f"Работа '{work_name}' сохранена!")
        work_menu(message)
        return
        
    if message.document:
        file_info = {
            "file_id": message.document.file_id,
            "file_name": message.document.file_name
        }
        user_states[user_id]["files"].append(file_info)
        bot.send_message(message.chat.id, f"Файл {message.document.file_name} добавлен. Отправьте еще или /done")
        bot.register_next_step_handler(message, process_file_upload)
    else:
        bot.send_message(message.chat.id, "Отправьте файл или /done для завершения")
        bot.register_next_step_handler(message, process_file_upload)

# Просмотр своих работ
def show_my_works(message):
    user_id = message.from_user.id
    cursor.execute('''
        SELECT work_id, work_name, status 
        FROM works 
        WHERE user_id=?
    ''', (user_id,))
    works = cursor.fetchall()
    
    if not works:
        bot.send_message(message.chat.id, "У вас нет работ")
        work_menu(message)
        return
        
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    for work in works:
        markup.add(f"{work[1]} ({work[2]})")
    markup.add('Назад')
    
    bot.send_message(message.chat.id, "Ваши работы:", reply_markup=markup)
    bot.register_next_step_handler(message, process_my_works)

def process_my_works(message):
    if message.text == 'Назад':
        work_menu(message)
        return
        
    selected_work = message.text.split(' (')[0]
    cursor.execute('''
        SELECT files, status 
        FROM works 
        WHERE user_id=? AND work_name=?
    ''', (message.from_user.id, selected_work))
    work_data = cursor.fetchone()
    
    if not work_data:
        bot.send_message(message.chat.id, "Работа не найдена")
        show_my_works(message)
        return
        
    files, status = json.loads(work_data[0]), work_data[1]
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add('Скачать все файлы', 'Назад')
    
    bot.send_message(
        message.chat.id,
        f"Статус: {status}\nФайлов: {len(files)}",
        reply_markup=markup
    )
    bot.register_next_step_handler(
        message,
        lambda msg: handle_my_work_actions(msg, files)
    )

def handle_my_work_actions(message, files):
    if message.text == 'Скачать все файлы':
        for file in files:
            bot.send_document(message.chat.id, file["file_id"])
        show_my_works(message)
    elif message.text == 'Назад':
        show_my_works(message)
    else:
        bot.send_message(message.chat.id, "Неизвестная команда")
        show_my_works(message)

# Проверка работ (для учителей/разработчиков)
def check_works(message):
    user_id = message.from_user.id
    if get_role(user_id) not in ['Учитель', 'Разработчик']:
        bot.send_message(message.chat.id, "Нет доступа")
        work_menu(message)
        return
        
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add('7А', '8А', '9А', 'Назад')
    bot.send_message(message.chat.id, "Выберите класс:", reply_markup=markup)
    bot.register_next_step_handler(
        message,
        process_class_check
    )

def process_class_check(message):
    if message.text == 'Назад':
        work_menu(message)
        return
        
    selected_class = message.text
    if selected_class not in ['7А', '8А', '9А']:
        bot.send_message(message.chat.id, "Неверный класс")
        check_works(message)
        return
        
    cursor.execute('''
        SELECT user_id, first_name, last_name 
        FROM users 
        WHERE class=?
    ''', (selected_class,))
    students = cursor.fetchall()
    
    if not students:
        bot.send_message(message.chat.id, "В классе нет учеников")
        check_works(message)
        return
        
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    for student in students:
        markup.add(f"{student[1]} {student[2]}")
    markup.add('Назад')
    
    bot.send_message(
        message.chat.id,
        "Выберите ученика:",
        reply_markup=markup
    )
    bot.register_next_step_handler(
        message,
        lambda msg: process_student_check(msg, selected_class)
    )

def process_student_check(message, selected_class):
    if message.text == 'Назад':
        check_works(message)
        return
        
    student_name = message.text.split()
    if len(student_name) != 2:
        bot.send_message(message.chat.id, "Неверный формат имени")
        process_class_check(message)
        return
        
    first_name, last_name = student_name
    cursor.execute('''
        SELECT user_id 
        FROM users 
        WHERE first_name=? AND last_name=? AND class=?
    ''', (first_name, last_name, selected_class))
    student_id = cursor.fetchone()
    
    if not student_id:
        bot.send_message(message.chat.id, "Ученик не найден")
        process_class_check(message)
        return
        
    cursor.execute('''
        SELECT work_id, work_name, status, files 
        FROM works 
        WHERE user_id=?
    ''', (student_id[0],))
    works = cursor.fetchall()
    
    if not works:
        bot.send_message(message.chat.id, "У ученика нет работ")
        process_class_check(message)
        return
        
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    for work in works:
        markup.add(f"{work[1]} ({work[2]})")
    markup.add('Назад')
    
    bot.send_message(
        message.chat.id,
        "Работы ученика:",
        reply_markup=markup
    )
    bot.register_next_step_handler(
        message,
        lambda msg: process_work_check(msg, student_id[0])
    )

def process_work_check(message, student_id):
    if message.text == 'Назад':
        check_works(message)
        return
        
    selected_work = message.text.split(' (')[0]
    cursor.execute('''
        SELECT work_id, work_name, status, files 
        FROM works 
        WHERE user_id=? AND work_name=?
    ''', (student_id, selected_work))
    work_data = cursor.fetchone()
    
    if not work_data:
        bot.send_message(message.chat.id, "Работа не найдена")
        check_works(message)
        return
        
    work_id, work_name, status, files = work_data
    files = json.loads(files)
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add('Изменить статус', 'Скачать все файлы', 'Назад')
    
    bot.send_message(
        message.chat.id,
        f"Работа: {work_name}\nСтатус: {status}\nФайлов: {len(files)}",
        reply_markup=markup
    )
    bot.register_next_step_handler(
        message,
        lambda msg: handle_work_actions(msg, work_id, files)
    )

def handle_work_actions(message, work_id, files):
    if message.text == 'Изменить статус':
        new_status = 'Проверено' if get_work_status(work_id) == 'Не проверено' else 'Не проверено'
        cursor.execute('''
            UPDATE works 
            SET status=? 
            WHERE work_id=?
        ''', (new_status, work_id))
        conn.commit()
        bot.send_message(message.chat.id, f"Статус изменен на {new_status}")
        check_works(message)
    elif message.text == 'Скачать все файлы':
        for file in files:
            bot.send_document(message.chat.id, file["file_id"])
        check_works(message)
    elif message.text == 'Назад':
        check_works(message)
    else:
        bot.send_message(message.chat.id, "Неизвестная команда")
        check_works(message)

def get_work_status(work_id):
    cursor.execute("SELECT status FROM works WHERE work_id=?", (work_id,))
    return cursor.fetchone()[0]

# Панель разработчика
@bot.message_handler(func=lambda msg: msg.text == 'Панель разработчика')
def developer_panel(message):
    if get_role(message.from_user.id) != 'Разработчик':
        bot.send_message(message.chat.id, "Нет доступа")
        show_main_menu(message)
        return
        
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add('Выдать роль', 'Список пользователей', 'Назад')
    bot.send_message(
        message.chat.id,
        "Панель разработчика:",
        reply_markup=markup
    )
    bot.register_next_step_handler(
        message,
        process_developer_actions
    )

def process_developer_actions(message):
    if message.text == 'Назад':
        show_main_menu(message)
        return
        
    if message.text == 'Выдать роль':
        list_users_for_role(message)
    elif message.text == 'Список пользователей':
        list_all_users(message)
    else:
        bot.send_message(message.chat.id, "Неизвестная команда")
        developer_panel(message)

def list_users_for_role(message):
    cursor.execute('''
        SELECT user_id, first_name, last_name 
        FROM users
    ''')
    users = cursor.fetchall()
    
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    for user in users:
        markup.add(f"{user[1]} {user[2]}")
    markup.add('Назад')
    
    bot.send_message(
        message.chat.id,
        "Выберите пользователя:",
        reply_markup=markup
    )
    bot.register_next_step_handler(
        message,
        process_user_select_for_role
    )

def process_user_select_for_role(message):
    if message.text == 'Назад':
        developer_panel(message)
        return
        
    user_name = message.text.split()
    if len(user_name) != 2:
        bot.send_message(message.chat.id, "Неверный формат имени")
        list_users_for_role(message)
        return
        
    first_name, last_name = user_name
    cursor.execute('''
        SELECT user_id 
        FROM users 
        WHERE first_name=? AND last_name=?
    ''', (first_name, last_name))
    user_id = cursor.fetchone()
    
    if not user_id:
        bot.send_message(message.chat.id, "Пользователь не найден")
        list_users_for_role(message)
        return
        
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add('Ученик', 'Учитель', 'Разработчик', 'Назад')
    bot.send_message(
        message.chat.id,
        "Выберите роль:",
        reply_markup=markup
    )
    bot.register_next_step_handler(
        message,
        lambda msg: set_role(msg, user_id[0])
    )

def set_role(message, target_user_id):
    if message.text == 'Назад':
        developer_panel(message)
        return
        
    new_role = message.text
    if new_role not in ['Ученик', 'Учитель', 'Разработчик']:
        bot.send_message(message.chat.id, "Неверная роль")
        list_users_for_role(message)
        return
        
    cursor.execute('''
        UPDATE users 
        SET role=? 
        WHERE user_id=?
    ''', (new_role, target_user_id))
    conn.commit()
    bot.send_message(message.chat.id, f"Роль изменена на {new_role}")
    developer_panel(message)

def list_all_users(message):
    cursor.execute('''
        SELECT login, first_name, last_name, class, role 
        FROM users
    ''')
    users = cursor.fetchall()
    
    response = "Список пользователей:\n"
    for user in users:
        response += f"Логин: {user[0]}, Имя: {user[1]} {user[2]}, Класс: {user[3]}, Роль: {user[4]}\n"
        
    bot.send_message(message.chat.id, response)
    developer_panel(message)

# Статистика
@bot.message_handler(func=lambda message: message.text == "Статистика")
def show_statistics(message):
    user_id = message.from_user.id
    if not is_logged_in(user_id):
        bot.send_message(message.chat.id, "Сначала войдите в аккаунт!")
        return
        
    user_data = get_user_data(user_id)
    first_name, last_name, user_class, role = user_data
    bot.send_message(
        message.chat.id,
        f"Имя: {first_name}\nФамилия: {last_name}\nКласс: {user_class}\nРоль: {role}"
    )
    show_main_menu(message)
# Запуск бота
if __name__ == "__main__":
    bot.polling(none_stop=True)