import telebot
from telebot import types
import sqlite3

API_TOKEN = '7650664774:AAF8EsK7_9E_xhcF_lXwzWRJHJ810KtULr0'
bot = telebot.TeleBot(API_TOKEN)

# Подключение к базе данных SQLite
conn = sqlite3.connect('school_bot.db', check_same_thread=False)
cursor = conn.cursor()

# Создание таблиц в базе данных
cursor.execute('''
CREATE TABLE IF NOT EXISTS users(
    user_id INTEGER PRIMARY KEY,
    first_name TEXT,
    last_name TEXT,
    class TEXT,
    role TEXT
)
''')

cursor.execute('''
CREATE TABLE IF NOT EXISTS works(
    work_id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    file_id TEXT,
    file_name TEXT,
    status TEXT,
    upload_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(user_id) REFERENCES users(user_id)
)
''')
conn.commit()

# Вспомогательные функции
def is_registered(user_id):
    cursor.execute("SELECT * FROM users WHERE user_id=?", (user_id,))
    return cursor.fetchone() is not None

def get_user_data(user_id):
    cursor.execute("SELECT first_name, last_name, class, role FROM users WHERE user_id=?", (user_id,))
    return cursor.fetchone()

def get_role(user_id):
    cursor.execute("SELECT role FROM users WHERE user_id=?", (user_id,))
    return cursor.fetchone()[0]

# Команда /start
@bot.message_handler(commands=['start'])
def start(message):
    if message.from_user.id == 1929255974:  # ID Вершинина Евгения (суперпользователь)
        cursor.execute("INSERT OR IGNORE INTO users (user_id, first_name, last_name, class, role) VALUES (?, ?, ?, ?, ?)",
                       (message.from_user.id, "Евгений", "Вершинин", "9А", "разработчик"))
        conn.commit()
        show_user_menu(message)
    elif not is_registered(message.from_user.id):
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        markup.add('Регистрация')
        bot.send_message(message.chat.id, "Привет! Пожалуйста, зарегистрируйтесь.", reply_markup=markup)
    else:
        show_user_menu(message)

# Регистрация пользователя
@bot.message_handler(func=lambda message: message.text == "Регистрация")
def register_user(message):
    msg = bot.send_message(message.chat.id, "Введите ваше имя и фамилию:")
    bot.register_next_step_handler(msg, process_name_step)

def process_name_step(message):
    user_full_name = message.text.split()
    if len(user_full_name) < 2:
        bot.send_message(message.chat.id, "Пожалуйста, введите корректное имя и фамилию.")
        return
    first_name, last_name = user_full_name[0], user_full_name[1]
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add('7А', '8А', '9А')
    msg = bot.send_message(message.chat.id, "Выберите ваш класс:", reply_markup=markup)
    bot.register_next_step_handler(msg, process_class_step, first_name, last_name)

def process_class_step(message, first_name, last_name):
    selected_class = message.text
    if selected_class not in ['7А', '8А', '9А']:
        bot.send_message(message.chat.id, "Пожалуйста, выберите корректный класс.")
        return
    cursor.execute("INSERT INTO users (user_id, first_name, last_name, class, role) VALUES (?, ?, ?, ?, ?)",
                   (message.from_user.id, first_name, last_name, selected_class, 'ученик'))
    conn.commit()
    bot.send_message(message.chat.id, "Вы успешно зарегистрированы!")
    show_user_menu(message)

# Главное меню пользователя
def show_user_menu(message):
    user_data = get_user_data(message.from_user.id)
    if user_data:
        first_name, last_name, user_class, role = user_data
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        markup.add('Статистика', 'Работа', 'Выход')
        if role == 'разработчик':
            markup.add('Панель разработчика')
        bot.send_message(message.chat.id, f"Добро пожаловать, {first_name} {last_name} ({user_class}, {role})", reply_markup=markup)

# Страница "Статистика"
@bot.message_handler(func=lambda message: message.text == "Статистика")
def show_statistics(message):
    user_data = get_user_data(message.from_user.id)
    if user_data:
        first_name, last_name, user_class, role = user_data
        bot.send_message(message.chat.id, f"Имя: {first_name}\nФамилия: {last_name}\nКласс: {user_class}\nРоль: {role}")

# Страница "Работа"
@bot.message_handler(func=lambda message: message.text == "Работа")
def work_menu(message):
    role = get_role(message.from_user.id)
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    if role in ['ученик', 'разработчик']:
        markup.add('Мои работы', 'Загрузить файл', 'Назад')
    if role in ['учитель', 'разработчик']:
        markup.add('Получить работу', 'Назад')
    bot.send_message(message.chat.id, "Выберите действие:", reply_markup=markup)

# Мои работы (для учеников и разработчиков)
@bot.message_handler(func=lambda message: message.text == "Мои работы")
def show_my_works(message):
    user_id = message.from_user.id
    cursor.execute("SELECT work_id, file_name, status, file_id FROM works WHERE user_id=?", (user_id,))
    works = cursor.fetchall()
    if not works:
        bot.send_message(message.chat.id, "У вас пока нет загруженных работ.")
        return
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    for work in works:
        work_id, file_name, status, file_id = work
        markup.add(f"{file_name} ({status})")
    markup.add("Назад")
    bot.send_message(message.chat.id, "Ваши работы:", reply_markup=markup)
    bot.register_next_step_handler(message, process_my_work_selection, works)

def process_my_work_selection(message, works):
    if message.text == "Назад":
        work_menu(message)
        return
    selected_work = message.text
    file_name = selected_work.split('(')[0].strip()
    cursor.execute("SELECT work_id, file_name, status, file_id FROM works WHERE user_id=? AND file_name=?", (message.from_user.id, file_name))
    work_data = cursor.fetchone()
    if not work_data:
        bot.send_message(message.chat.id, "Работа не найдена.")
        return
    work_id, file_name, status, file_id = work_data
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add("Скачать файл", "Назад")
    bot.send_message(message.chat.id, f"Информация о работе:\nНазвание: {file_name}\nСтатус: {status}", reply_markup=markup)
    bot.register_next_step_handler(message, process_my_work_action, work_id, file_name, status, file_id)

def process_my_work_action(message, work_id, file_name, status, file_id):
    if message.text == "Скачать файл":
        bot.send_document(message.chat.id, file_id)
    elif message.text == "Назад":
        show_my_works(message)
    else:
        bot.send_message(message.chat.id, "Пожалуйста, выберите действие из предложенных.")

# Загрузка файла (для учеников и разработчиков)
@bot.message_handler(func=lambda message: message.text == "Загрузить файл")
def upload_file(message):
    msg = bot.send_message(message.chat.id, "Отправьте файл:")
    bot.register_next_step_handler(msg, process_file_upload)

def process_file_upload(message):
    if message.document:
        file_id = message.document.file_id
        original_file_name = message.document.file_name
        user_data = get_user_data(message.from_user.id)
        if user_data:
            first_name, last_name, _, _ = user_data
            formatted_file_name = f"{last_name}_{first_name}/{original_file_name}"
            cursor.execute("INSERT INTO works (user_id, file_id, file_name, status) VALUES (?, ?, ?, ?)",
                           (message.from_user.id, file_id, formatted_file_name, 'Не проверено'))
            conn.commit()
            bot.send_message(message.chat.id, f"Файл успешно загружен! Название: {formatted_file_name}, Статус: Не проверено")
    else:
        bot.send_message(message.chat.id, "Пожалуйста, отправьте файл.")

# Получение работ (для учителя и разработчика)
@bot.message_handler(func=lambda message: message.text == "Получить работу")
def get_works(message):
    role = get_role(message.from_user.id)
    if role not in ['учитель', 'разработчик']:
        bot.send_message(message.chat.id, "У вас нет прав для выполнения этой команды.")
        return
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add('7А', '8А', '9А', 'Назад')
    msg = bot.send_message(message.chat.id, "Выберите класс:", reply_markup=markup)
    bot.register_next_step_handler(msg, process_class_selection)

def process_class_selection(message):
    if message.text == "Назад":
        work_menu(message)
        return
    selected_class = message.text
    if selected_class not in ['7А', '8А', '9А']:
        bot.send_message(message.chat.id, "Пожалуйста, выберите корректный класс.")
        return
    cursor.execute("SELECT user_id, first_name, last_name FROM users WHERE class=?", (selected_class,))
    students = cursor.fetchall()
    if not students:
        bot.send_message(message.chat.id, f"В классе {selected_class} нет учеников.")
        return
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    for student in students:
        student_id, first_name, last_name = student
        markup.add(f"{first_name} {last_name}")
    markup.add("Назад")
    msg = bot.send_message(message.chat.id, "Выберите ученика:", reply_markup=markup)
    bot.register_next_step_handler(msg, process_student_selection, selected_class)

def process_student_selection(message, selected_class):
    if message.text == "Назад":
        get_works(message)
        return
    selected_student = message.text
    first_name, last_name = selected_student.split()
    cursor.execute("SELECT user_id FROM users WHERE first_name=? AND last_name=? AND class=?", (first_name, last_name, selected_class))
    student_id = cursor.fetchone()[0]
    cursor.execute("SELECT work_id, file_name, status, file_id FROM works WHERE user_id=?", (student_id,))
    works = cursor.fetchall()
    if not works:
        bot.send_message(message.chat.id, f"У ученика {selected_student} нет загруженных работ.")
        return
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    for work in works:
        work_id, file_name, status, file_id = work
        markup.add(f"{file_name} ({status})")
    markup.add("Назад")
    bot.send_message(message.chat.id, f"Работы ученика {selected_student}:", reply_markup=markup)
    bot.register_next_step_handler(message, process_work_selection, works, student_id)

def process_work_selection(message, works, student_id):
    if message.text == "Назад":
        get_works(message)
        return
    selected_work = message.text
    file_name = selected_work.split('(')[0].strip()
    cursor.execute("SELECT work_id, file_name, status, file_id FROM works WHERE user_id=? AND file_name=?", (student_id, file_name))
    work_data = cursor.fetchone()
    if not work_data:
        bot.send_message(message.chat.id, "Работа не найдена.")
        return
    work_id, file_name, status, file_id = work_data
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add("Изменить статус", "Скачать файл", "Назад")
    bot.send_message(message.chat.id, f"Информация о работе:\nНазвание: {file_name}\nСтатус: {status}", reply_markup=markup)
    bot.register_next_step_handler(message, process_work_action, work_id, file_name, status, file_id)

def process_work_action(message, work_id, file_name, status, file_id):
    if message.text == "Изменить статус":
        new_status = "Проверено" if status == "Не проверено" else "Не проверено"
        cursor.execute("UPDATE works SET status=? WHERE work_id=?", (new_status, work_id))
        conn.commit()
        bot.send_message(message.chat.id, f"Статус работы '{file_name}' изменен на '{new_status}'.")
    elif message.text == "Скачать файл":
        bot.send_document(message.chat.id, file_id)
    elif message.text == "Назад":
        get_works(message)
    else:
        bot.send_message(message.chat.id, "Пожалуйста, выберите действие из предложенных.")

# Панель разработчика
@bot.message_handler(func=lambda message: message.text == "Панель разработчика")
def developer_panel(message):
    role = get_role(message.from_user.id)
    if role != 'разработчик':
        bot.send_message(message.chat.id, "У вас нет прав для доступа к панели разработчика.")
        return
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add('Выдать роль', 'Список пользователей', 'Назад')
    bot.send_message(message.chat.id, "Добро пожаловать в панель разработчика!", reply_markup=markup)
    bot.register_next_step_handler(message, process_developer_action)

def process_developer_action(message):
    if message.text == "Назад":
        show_user_menu(message)
        return
    elif message.text == "Выдать роль":
        msg = bot.send_message(message.chat.id, "Введите ID пользователя и новую роль (например, 123456789 учитель):")
        bot.register_next_step_handler(msg, assign_role)
    elif message.text == "Список пользователей":
        list_users(message)
    else:
        bot.send_message(message.chat.id, "Пожалуйста, выберите действие из предложенных.")

def assign_role(message):
    try:
        user_id, new_role = message.text.split()
        user_id = int(user_id)
    except ValueError:
        bot.send_message(message.chat.id, "Неверный формат команды. Используйте: ID_пользователя роль")
        return
    if new_role not in ['ученик', 'учитель', 'разработчик']:
        bot.send_message(message.chat.id, "Недопустимая роль. Доступные роли: ученик, учитель, разработчик.")
        return
    cursor.execute("UPDATE users SET role=? WHERE user_id=?", (new_role, user_id))
    conn.commit()
    if cursor.rowcount > 0:
        bot.send_message(message.chat.id, f"Роль пользователя с ID {user_id} успешно изменена на '{new_role}'.")
    else:
        bot.send_message(message.chat.id, "Пользователь с указанным ID не найден.")

def list_users(message):
    cursor.execute("SELECT user_id, first_name, last_name, class, role FROM users")
    users = cursor.fetchall()
    if not users:
        bot.send_message(message.chat.id, "Список пользователей пуст.")
        return
    response = "Список пользователей:\n"
    for user in users:
        user_id, first_name, last_name, user_class, role = user
        response += f"ID: {user_id}, Имя: {first_name} {last_name}, Класс: {user_class}, Роль: {role}\n"
    bot.send_message(message.chat.id, response)

# Выход из аккаунта
@bot.message_handler(func=lambda message: message.text == "Выход")
def exit_user(message):
    bot.send_message(message.chat.id, "Вы вышли из аккаунта.")
    start(message)

# Запуск бота
if __name__ == "__main__":
    bot.polling(none_stop=True)