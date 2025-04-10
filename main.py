import sqlite3
import telebot
from telebot import types
from app import TOKEN
import logging

# Токен вашего Telegram-бота
TOKEN = TOKEN
bot = telebot.TeleBot(TOKEN)

# Подключение к базе данных SQLite
conn = sqlite3.connect('database.db', check_same_thread=False)
cursor = conn.cursor()

VERSHININ_ID = 1929255974  # Убедитесь, что это integer

# Создание таблиц
cursor.execute('''
CREATE TABLE IF NOT EXISTS users (
    user_id INTEGER PRIMARY KEY,
    name TEXT,
    surname TEXT,
    class TEXT,
    role TEXT DEFAULT 'ученик'
)
''')

cursor.execute('''
CREATE TABLE IF NOT EXISTS works (
    work_id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    filename TEXT,
    status TEXT DEFAULT 'Не проверено',
    uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(user_id) REFERENCES users(user_id)
)
''')

conn.commit()

class States:
    REGISTER_NAME = 'register_name'
    REGISTER_CLASS = 'register_class'
    UPLOAD_FILE = 'upload_file'
    SELECT_CLASS = 'select_class'
    SELECT_STATUS = 'select_status'
    SEND_BROADCAST = 'send_broadcast'
    CHANGE_ROLE = 'change_role'

logging.basicConfig(
    format='%(asctime)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

def is_user_registered(user_id):
    cursor.execute('SELECT * FROM users WHERE user_id = ?', (user_id,))
    return cursor.fetchone() is not None

def get_user_role(user_id):
    cursor.execute('SELECT role FROM users WHERE user_id = ?', (user_id,))
    result = cursor.fetchone()
    return result[0] if result else None

def show_main_menu(message):
    user_id = message.from_user.id
    cursor.execute('SELECT name, surname, class, role FROM users WHERE user_id = ?', (user_id,))
    user = cursor.fetchone()
    
    if user:
        name, surname, class_name, role = user
        keyboard = types.InlineKeyboardMarkup(row_width=2)
        
        if role == 'ученик':
            keyboard.add(
                types.InlineKeyboardButton('Мои работы', callback_data='student_works'),
                types.InlineKeyboardButton('Загрузить файл', callback_data='upload_file')
            )
        elif role in ['учитель', 'разработчик']:
            keyboard.add(
                types.InlineKeyboardButton('Получить работу', callback_data='get_work'),
                types.InlineKeyboardButton('Рассылка', callback_data='broadcast')
            )
        
        if role == 'разработчик':
            keyboard.add(
                types.InlineKeyboardButton('Мои работы', callback_data='dev_works')
            )
        
        keyboard.add(types.InlineKeyboardButton('Выход', callback_data='logout'))
        
        bot.send_message(
            message.chat.id,
            f"Здравствуйте, {name} {surname} ({role}, {class_name})",
            reply_markup=keyboard
        )
    else:
        bot.send_message(
            message.chat.id,
            "Пожалуйста, зарегистрируйтесь.",
            reply_markup=types.ReplyKeyboardRemove()
        )
        bot.set_state(message.from_user.id, States.REGISTER_NAME, message.chat.id)
        bot.send_message(message.chat.id, "Введите ваше имя:")

@bot.message_handler(commands=['start'])
def start(message):
    if message.chat.id == VERSHININ_ID:
        cursor.execute('''
            INSERT OR REPLACE INTO users 
            (user_id, name, surname, class, role) 
            VALUES (?, ?, ?, ?, ?)
        ''', (VERSHININ_ID, 'Евгений', 'Вершинин', '9А', 'разработчик'))
        conn.commit()
    
    if not is_user_registered(message.from_user.id):
        bot.send_message(
            message.chat.id,
            "Добро пожаловать! Пожалуйста, зарегистрируйтесь.",
            reply_markup=types.ReplyKeyboardRemove()
        )
        bot.set_state(message.from_user.id, States.REGISTER_NAME, message.chat.id)
        bot.send_message(message.chat.id, "Введите ваше имя:")
    else:
        show_main_menu(message)

# Регистрация
@bot.message_handler(state=States.REGISTER_NAME)
def register_name(message):
    name = message.text.strip()
    bot.set_state(message.from_user.id, States.REGISTER_CLASS, message.chat.id)
    bot.send_message(message.chat.id, "Введите вашу фамилию:")
    
    with bot.retrieve_data(message.from_user.id, message.chat.id) as data:
        data['name'] = name

@bot.message_handler(state=States.REGISTER_CLASS)
def register_class(message):
    surname = message.text.strip()
    keyboard = types.InlineKeyboardMarkup()
    
    for cls in ['7А', '8А', '9А']:
        keyboard.add(types.InlineKeyboardButton(text=cls, callback_data=f'register_class_{cls}'))
    
    bot.send_message(
        message.chat.id,
        "Выберите ваш класс:",
        reply_markup=keyboard
    )
    
    with bot.retrieve_data(message.from_user.id, message.chat.id) as data:
        data['surname'] = surname

@bot.callback_query_handler(func=lambda call: call.data.startswith('register_class_'))
def register_class_callback(call):
    class_name = call.data.split('_')[-1]
    user_id = call.from_user.id
    
    with bot.retrieve_data(user_id, call.message.chat.id) as data:
        name = data['name']
        surname = data['surname']
    
    try:
        cursor.execute('''
            INSERT INTO users (user_id, name, surname, class)
            VALUES (?, ?, ?, ?)
        ''', (user_id, name, surname, class_name))
        conn.commit()
        bot.answer_callback_query(call.id, "Регистрация завершена!")
        bot.delete_state(user_id, call.message.chat.id)
        show_main_menu(call.message)
    except Exception as e:
        logging.error(f"Ошибка регистрации: {e}")
        bot.answer_callback_query(call.id, "Ошибка регистрации")

# Обработчик callback-кнопок
@bot.callback_query_handler(func=lambda call: True)
def handle_callbacks(call):
    handlers = {
        'student_works': show_student_works,
        'upload_file': handle_upload_file,
        'get_work': show_classes,
        'broadcast': handle_broadcast,
        'logout': logout_user,
        'back': show_main_menu,
        'work_': show_work_details,
        'download_': handle_download,
        'status_': handle_status_change,
        'change_status_to_': finalize_status_change
    }
    
    for key in handlers:
        if call.data.startswith(key):
            handlers[key](call)
            break

# Функции для работы с кнопками
def show_student_works(call):
    user_id = call.from_user.id
    cursor.execute('''
        SELECT work_id, filename, status 
        FROM works 
        WHERE user_id = ?
    ''', (user_id,))
    
    works = cursor.fetchall()
    keyboard = types.InlineKeyboardMarkup()
    
    if works:
        for work in works:
            work_id, filename, status = work
            btn = types.InlineKeyboardButton(f"{filename} ({status})", callback_data=f'work_{work_id}')
            keyboard.add(btn)
    else:
        keyboard.add(types.InlineKeyboardButton("Назад", callback_data='back'))
    
    bot.send_message(
        call.message.chat.id,
        "Ваши работы:",
        reply_markup=keyboard
    )

def handle_upload_file(call):
    bot.set_state(call.from_user.id, States.UPLOAD_FILE, call.message.chat.id)
    bot.send_message(
        call.message.chat.id,
        "Отправьте файл для загрузки:",
        reply_markup=types.ReplyKeyboardRemove()
    )

def show_classes(call):
    keyboard = types.InlineKeyboardMarkup()
    
    for cls in ['7А', '8А', '9А']:
        keyboard.add(types.InlineKeyboardButton(text=cls, callback_data=f'select_class_{cls}'))
    
    bot.send_message(
        call.message.chat.id,
        "Выберите класс:",
        reply_markup=keyboard
    )

def handle_broadcast(call):
    bot.set_state(call.from_user.id, States.SEND_BROADCAST, call.message.chat.id)
    bot.send_message(
        call.message.chat.id,
        "Введите текст для рассылки:"
    )

def show_work_details(call):
    work_id = int(call.data.split('_')[1])
    cursor.execute('''
        SELECT filename, status, uploaded_at, user_id 
        FROM works 
        WHERE work_id = ?
    ''', (work_id,))
    
    work = cursor.fetchone()
    if work:
        filename, status, uploaded_at, user_id = work
        cursor.execute('''
            SELECT name, surname FROM users WHERE user_id = ?
        ''', (user_id,))
        user_data = cursor.fetchone()
        
        text = f'''Файл: {filename}
Статус: {status}
Дата: {uploaded_at}
Автор: {user_data[0]} {user_data[1]}'''
        
        keyboard = types.InlineKeyboardMarkup()
        keyboard.add(
            types.InlineKeyboardButton('Загрузить', callback_data=f'download_{work_id}'),
            types.InlineKeyboardButton('Изменить статус', callback_data=f'status_{work_id}'),
            types.InlineKeyboardButton('Назад', callback_data='back')
        )
        
        bot.send_message(
            call.message.chat.id,
            text,
            reply_markup=keyboard
        )
    else:
        bot.send_message(call.message.chat.id, "Работа не найдена")

def handle_download(call):
    work_id = int(call.data.split('_')[1])
    cursor.execute('SELECT filename FROM works WHERE work_id = ?', (work_id,))
    filename = cursor.fetchone()[0]
    
    try:
        with open(filename, 'rb') as file:
            bot.send_document(call.message.chat.id, file)
    except FileNotFoundError:
        bot.send_message(call.message.chat.id, "Файл не найден")

def handle_status_change(call):
    work_id = int(call.data.split('_')[1])
    cursor.execute('SELECT status FROM works WHERE work_id = ?', (work_id,))
    current_status = cursor.fetchone()[0]
    
    statuses = ['Проверено', 'Не проверено', 'Удалено']
    keyboard = types.InlineKeyboardMarkup()
    
    for status in statuses:
        if status != current_status:
            keyboard.add(types.InlineKeyboardButton(
                status,
                callback_data=f'change_{status.lower()}_{work_id}'
            ))
    
    keyboard.add(types.InlineKeyboardButton('Назад', callback_data='back'))
    
    bot.send_message(
        call.message.chat.id,
        "Выберите новый статус:",
        reply_markup=keyboard
    )

def finalize_status_change(call):
    parts = call.data.split('_')
    new_status = parts[1]
    work_id = int(parts[2])
    
    try:
        cursor.execute('''
            UPDATE works 
            SET status = ?
            WHERE work_id = ?
        ''', (new_status, work_id))
        conn.commit()
        bot.send_message(
            call.message.chat.id,
            f"Статус изменён на '{new_status}'",
            reply_markup=types.InlineKeyboardMarkup()
        )
    except Exception as e:
        logging.error(f"Ошибка: {e}")
        bot.send_message(call.message.chat.id, "Ошибка изменения статуса")

# Загрузка файла
@bot.message_handler(content_types=['document'], state=States.UPLOAD_FILE)
def process_upload(message):
    file_info = bot.get_file(message.document.file_id)
    filename = message.document.file_name
    user_id = message.from_user.id
    
    try:
        cursor.execute('''
            INSERT INTO works (user_id, filename)
            VALUES (?, ?)
        ''', (user_id, filename))
        conn.commit()
        bot.send_message(
            message.chat.id,
            "Файл загружен",
            reply_markup=types.ReplyKeyboardRemove()
        )
        bot.delete_state(message.from_user.id, message.chat.id)
        show_main_menu(message)
    except Exception as e:
        logging.error(f"Ошибка: {e}")
        bot.send_message(message.chat.id, "Ошибка загрузки файла")

# Рассылка
@bot.message_handler(state=States.SEND_BROADCAST)
def process_broadcast(message):
    text = message.text
    cursor.execute('SELECT user_id FROM users')
    
    for row in cursor.fetchall():
        user_id = row[0]
        try:
            bot.send_message(user_id, text)
        except Exception as e:
            logging.error(f"Ошибка рассылки для {user_id}: {e}")
    
    bot.send_message(
        message.chat.id,
        "Рассылка завершена",
        reply_markup=types.ReplyKeyboardRemove()
    )
    bot.delete_state(message.from_user.id, message.chat.id)
    show_main_menu(message)

def logout_user(call):
    bot.send_message(
        call.message.chat.id,
        "Вы вышли из аккаунта",
        reply_markup=types.ReplyKeyboardRemove()
    )
    show_main_menu(call.message)

# Изменение роли
@bot.message_handler(commands=['change_role'])
def change_role(message):
    if get_user_role(message.from_user.id) != 'разработчик':
        return
    
    bot.set_state(message.from_user.id, States.CHANGE_ROLE, message.chat.id)
    bot.send_message(
        message.chat.id,
        "Введите ID пользователя:"
    )

@bot.message_handler(state=States.CHANGE_ROLE)
def process_role_id(message):
    try:
        target_id = int(message.text.strip())
        
        with bot.retrieve_data(message.from_user.id, message.chat.id) as data:
            data['target_id'] = target_id
        
        bot.send_message(
            message.chat.id,
            "Выберите новую роль:\n"
            "1. Ученик\n"
            "2. Учитель\n"
            "3. Разработчик"
        )
    except ValueError:
        bot.send_message(message.chat.id, "Неверный формат ID")

@bot.message_handler(state=States.CHANGE_ROLE, content_types=['text'])
def set_role(message):
    choice = message.text.strip()
    roles = {'1': 'ученик', '2': 'учитель', '3': 'разработчик'}
    
    if choice not in roles:
        bot.send_message(message.chat.id, "Неверный выбор")
        return
    
    with bot.retrieve_data(message.from_user.id, message.chat.id) as data:
        target_id = data['target_id']
    
    new_role = roles[choice]
    cursor.execute('''
        UPDATE users 
        SET role = ?
        WHERE user_id = ?
    ''', (new_role, target_id))
    conn.commit()
    
    bot.send_message(
        message.chat.id,
        f"Роль изменена на '{new_role}'",
        reply_markup=types.ReplyKeyboardRemove()
    )
    bot.delete_state(message.from_user.id, message.chat.id)
    show_main_menu(message)

# Просмотр работы
def get_work(call):
    work_id = int(call.data.split('_')[-1])
    cursor.execute('''
        SELECT filename, status, uploaded_at FROM works 
        WHERE work_id = ?
    ''', (work_id,))
    
    work = cursor.fetchone()
    if work:
        filename, status, uploaded_at = work
        bot.send_message(
            call.message.chat.id,
            f"Файл: {filename}\nСтатус: {status}\nДата: {uploaded_at}"
        )
    else:
        bot.send_message(call.message.chat.id, "Работа не найдена")

# Выбор класса учителем
@bot.callback_query_handler(func=lambda call: call.data.startswith('select_class_'))
def handle_class_selection(call):
    class_name = call.data.split('_')[-1]
    cursor.execute('''
        SELECT work_id, filename, status, uploaded_at 
        FROM works 
        WHERE class = ?
    ''', (class_name,))
    
    works = cursor.fetchall()
    keyboard = types.InlineKeyboardMarkup()
    
    if works:
        for work in works:
            work_id, filename, status, uploaded_at = work
            btn_text = f"{filename} ({status})"
            keyboard.add(types.InlineKeyboardButton(btn_text, callback_data=f'work_{work_id}'))
    else:
        keyboard.add(types.InlineKeyboardButton("Назад", callback_data='back'))
    
    bot.send_message(
        call.message.chat.id,
        f"Работы класса {class_name}:",
        reply_markup=keyboard
    )

# Загрузка файла учителем
@bot.callback_query_handler(func=lambda call: call.data.startswith('download_'))
def download_file(call):
    work_id = int(call.data.split('_')[1])
    cursor.execute('SELECT filename FROM works WHERE work_id = ?', (work_id,))
    filename = cursor.fetchone()[0]
    
    try:
        with open(filename, 'rb') as file:
            bot.send_document(call.message.chat.id, file)
    except FileNotFoundError:
        bot.send_message(call.message.chat.id, "Файл не найден")

# Изменение статуса работы учителем
@bot.callback_query_handler(func=lambda call: call.data.startswith('status_'))
def change_status(call):
    work_id = int(call.data.split('_')[1])
    cursor.execute('SELECT status FROM works WHERE work_id = ?', (work_id,))
    current_status = cursor.fetchone()[0]
    
    statuses = ['Проверено', 'Не проверено', 'Удалено']
    keyboard = types.InlineKeyboardMarkup()
    
    for status in statuses:
        if status != current_status:
            keyboard.add(types.InlineKeyboardButton(
                status,
                callback_data=f'change_status_{status.lower()}_{work_id}'
            ))
    
    keyboard.add(types.InlineKeyboardButton('Назад', callback_data='back'))
    
    bot.send_message(
        call.message.chat.id,
        "Выберите новый статус:",
        reply_markup=keyboard
    )

@bot.callback_query_handler(func=lambda call: call.data.startswith('change_status_'))
def finalize_status_change(call):
    parts = call.data.split('_')
    new_status = parts[2]
    work_id = int(parts[3])
    
    try:
        cursor.execute('''
            UPDATE works 
            SET status = ?
            WHERE work_id = ?
        ''', (new_status, work_id))
        conn.commit()
        bot.send_message(
            call.message.chat.id,
            f"Статус изменён на '{new_status}'",
            reply_markup=types.InlineKeyboardMarkup()
        )
    except Exception as e:
        logging.error(f"Ошибка: {e}")
        bot.send_message(call.message.chat.id, "Ошибка изменения статуса")

# Статистика пользователя
def show_user_statistics(message):
    user_id = message.from_user.id
    cursor.execute('''
        SELECT name, surname, class, role 
        FROM users 
        WHERE user_id = ?
    ''', (user_id,))
    
    user = cursor.fetchone()
    if user:
        name, surname, class_name, role = user
        bot.send_message(
            message.chat.id,
            f"Имя: {name}\n"
            f"Фамилия: {surname}\n"
            f"Класс: {class_name}\n"
            f"Роль: {role}",
            parse_mode='Markdown'
        )
    else:
        bot.send_message(message.chat.id, "Пользователь не найден")

# Обработчик возврата в главное меню
@bot.callback_query_handler(func=lambda call: call.data == 'back')
def back_to_menu(call):
    show_main_menu(call.message)

# Основные функции
def get_work(call):
    work_id = int(call.data.split('_')[-1])
    cursor.execute('''
        SELECT filename, status, uploaded_at FROM works 
        WHERE work_id = ?
    ''', (work_id,))
    
    work = cursor.fetchone()
    if work:
        filename, status, uploaded_at = work
        bot.send_message(
            call.message.chat.id,
            f"Файл: {filename}\n"
            f"Статус: {status}\n"
            f"Дата: {uploaded_at}"
        )
    else:
        bot.send_message(call.message.chat.id, "Работа не найдена")

# Запуск бота
if __name__ == '__main__':
    try:
        bot.polling(none_stop=True)
    except Exception as e:
        logging.error(f"Ошибка запуска: {e}")