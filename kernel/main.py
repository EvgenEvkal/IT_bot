import telebot
import sqlite3
import os
import datetime
import json
from telebot import types
from typing import Optional, Tuple, List, Dict, Union
import api
global API_TOKEN , DEV_ID , CHANNEL_ID , WORKS_FOLDER , DB_NAME
API_TOKEN = api.TOKEN
DEV_ID = api.DEV_ID
CHANNEL_ID = api.CHANNEL_ID
bot = telebot.TeleBot(API_TOKEN)

# Константы
WORKS_FOLDER = api.WORKS_FOLDER
DB_NAME = api.DB_NAME
os.makedirs(WORKS_FOLDER, exist_ok=True)

# Классы для хранения данных
class User:
    def __init__(self, user_id: int, username: str, full_name: str, role: str, class_name: str, is_blocked: bool):
        self.user_id = user_id
        self.username = username
        self.full_name = full_name
        self.role = role
        self.class_name = class_name
        self.is_blocked = is_blocked

class Work:
    def __init__(self, work_id: int, user_id: int, file_path: str, status: str, created_at: str, teacher_comment: str):
        self.work_id = work_id
        self.user_id = user_id
        self.file_path = file_path
        self.status = status
        self.created_at = created_at
        self.teacher_comment = teacher_comment

# Добавим новые статусы в класс Report
class Report:
    def __init__(self, report_id: int, user_id: int, text: str, status: str, response: str, created_at: str):
        self.report_id = report_id
        self.user_id = user_id
        self.text = text
        self.status = status  # 'Не проверено', 'В работе', 'Решено', 'Отклонено'
        self.response = response
        self.created_at = created_at
def change_report_status(call: types.CallbackQuery, report_id: int):
    user_id = call.from_user.id
    if not check_access(user_id, 'учитель'):
        bot.send_message(user_id, "❌ У вас нет прав на изменение статуса репортов.")
        return
    markup = types.InlineKeyboardMarkup(row_width=1)
    statuses = ["В работе", "Решено", "Отклонено"]
    for status in statuses:
        markup.add(types.InlineKeyboardButton(status, callback_data=f"set_report_status_{report_id}_{status}"))
    markup.add(types.InlineKeyboardButton("🔙 Назад", callback_data=f"report_detail_{report_id}"))
    bot.edit_message_text("Выберите новый статус:",
                         chat_id=user_id,
                         message_id=call.message.message_id,
                         reply_markup=markup)
class TaskManager:
    def __init__(self, user_id: int):
        """
        Инициализация менеджера заданий.
        
        :param user_id: ID пользователя (учителя или разработчика).
        """
        self.user_id = user_id
        self.cursor = conn.cursor()

    def get_all_tasks(self) -> List[Tuple]:
        """
        Получить все задания из базы данных.

        :return: Список всех заданий в формате (task_id, title, description, status).
        """
        try:
            self.cursor.execute("SELECT task_id, title, description, status FROM tasks")
            return self.cursor.fetchall()
        except Exception as e:
            print(f"Error getting tasks: {e}")
            return []

    def create_task(self, title: str, description: str) -> Tuple[bool, str]:
        """
        Создать новое задание.

        :param title: Название задания.
        :param description: Описание задания.
        :return: Результат операции (успех/ошибка) и сообщение.
        """
        if not check_access(self.user_id, 'учитель'):
            return False, "❌ Недостаточно прав для создания заданий."
        try:
            self.cursor.execute(
                "INSERT INTO tasks (title, description, status) VALUES (?, ?, ?)",
                (title, description, 'active')
            )
            conn.commit()
            return True, "✅ Задание успешно создано."
        except Exception as e:
            return False, f"❌ Ошибка при создании задания: {str(e)}"

    def delete_task(self, task_id: int) -> Tuple[bool, str]:
        """
        Удалить задание по ID.

        :param task_id: ID задания.
        :return: Результат операции (успех/ошибка) и сообщение.
        """
        if not check_access(self.user_id, 'учитель'):
            return False, "❌ Недостаточно прав для удаления заданий."
        try:
            self.cursor.execute("DELETE FROM tasks WHERE task_id = ?", (task_id,))
            conn.commit()
            return True, f"✅ Задание #{task_id} успешно удалено."
        except Exception as e:
            return False, f"❌ Ошибка при удалении задания: {str(e)}"

    def change_task_status(self, task_id: int, new_status: str) -> Tuple[bool, str]:
        """
        Изменить статус задания.

        :param task_id: ID задания.
        :param new_status: Новый статус ('active', 'closed').
        :return: Результат операции (успех/ошибка) и сообщение.
        """
        if not check_access(self.user_id, 'учитель'):
            return False, "❌ Недостаточно прав для изменения статуса заданий."
        try:
            self.cursor.execute("UPDATE tasks SET status = ? WHERE task_id = ?", (new_status, task_id))
            conn.commit()
            return True, f"✅ Статус задания #{task_id} успешно изменен на '{new_status}'."
        except Exception as e:
            return False, f"❌ Ошибка при изменении статуса задания: {str(e)}"

    def view_active_tasks(self) -> List[Tuple]:
        """
        Просмотр активных заданий.

        :return: Список активных заданий в формате (task_id, title, description).
        """
        try:
            self.cursor.execute("SELECT task_id, title, description FROM tasks WHERE status = 'active'")
            return self.cursor.fetchall()
        except Exception as e:
            print(f"Error viewing active tasks: {e}")
            return []

    def view_closed_tasks(self) -> List[Tuple]:
        """
        Просмотр закрытых заданий.

        :return: Список закрытых заданий в формате (task_id, title, description).
        """
        try:
            self.cursor.execute("SELECT task_id, title, description FROM tasks WHERE status = 'closed'")
            return self.cursor.fetchall()
        except Exception as e:
            print(f"Error viewing closed tasks: {e}")
            return []

    def check_task_answers(self, task_id: int) -> List[Tuple]:
        """
        Просмотр ответов учеников на конкретное задание.

        :param task_id: ID задания.
        :return: Список ответов в формате (full_name, answer_text, file_path, status).
        """
        try:
            self.cursor.execute("""
                SELECT u.full_name, a.answer_text, a.file_path, a.status 
                FROM answers a
                JOIN users u ON a.user_id = u.user_id
                WHERE a.task_id = ?
            """, (task_id,))
            return self.cursor.fetchall()
        except Exception as e:
            print(f"Error checking task answers: {e}")
            return []
@bot.callback_query_handler(func=lambda call: call.data == 'view_new_tasks')
def view_new_tasks(call: types.CallbackQuery):
    user_id = call.from_user.id
    manager = TaskManager(user_id)
    tasks = manager.view_active_tasks()
    if not tasks:
        bot.send_message(user_id, "❌ Сейчас нет активных заданий.")
        return

    message = "📋 Список новых заданий:\n"
    for task in tasks:
        task_id, title, description = task
        message += f"- #{task_id}: {title}\n{description}\n"

    bot.send_message(user_id, message, reply_markup=student_task_actions_markup(tasks))
@bot.callback_query_handler(func=lambda call: call.data == 'view_old_tasks')
def view_old_tasks(call: types.CallbackQuery):
    user_id = call.from_user.id
    manager = TaskManager(user_id)
    tasks = manager.view_closed_tasks()
    if not tasks:
        bot.send_message(user_id, "❌ У вас пока нет закрытых заданий.")
        return

    message = "📋 Список прошедших заданий:\n"
    for task in tasks:
        task_id, title, description = task
        message += f"- #{task_id}: {title}\n{description}\n"

    bot.send_message(user_id, message, reply_markup=teacher_task_actions_markup())
@bot.callback_query_handler(func=lambda call: call.data == 'create_task')
def create_task(call: types.CallbackQuery):
    user_id = call.from_user.id
    if not check_access(user_id, 'учитель'):
        bot.send_message(user_id, "❌ У вас нет прав на создание заданий.")
        return

    msg = bot.send_message(user_id, "Введите название нового задания:")
    bot.register_next_step_handler(msg, process_task_title)
def process_task_title(message: types.Message):
    user_id = message.from_user.id
    title = message.text.strip()
    if not title or len(title) < 5:
        msg = bot.send_message(user_id, "❌ Название задания слишком короткое. Введите подробнее:")
        bot.register_next_step_handler(msg, process_task_title)
        return

    msg = bot.send_message(user_id, "Введите описание задания:")
    bot.register_next_step_handler(msg, lambda m: process_task_description(m, title))
def process_task_description(message: types.Message, title: str):
    user_id = message.from_user.id
    description = message.text.strip()
    if not description or len(description) < 10:
        msg = bot.send_message(user_id, "❌ Описание задания слишком короткое. Введите подробнее:")
        bot.register_next_step_handler(msg, lambda m: process_task_description(m, title))
        return

    manager = TaskManager(user_id)
    success, result = manager.create_task(title, description)
    bot.send_message(user_id, result, reply_markup=teacher_tasks_menu_markup())
@bot.callback_query_handler(func=lambda call: call.data == 'teacher_tasks')
def teacher_tasks_menu(call: types.CallbackQuery):
    user_id = call.from_user.id
    markup = types.InlineKeyboardMarkup(row_width=1)
    buttons = [
        types.InlineKeyboardButton("📋 Новые задания", callback_data="view_new_tasks"),
        types.InlineKeyboardButton("📚 Прошедшие задания", callback_data="view_old_tasks"),
        types.InlineKeyboardButton("➕ Создать новое задание", callback_data="create_task") if check_access(user_id, 'учитель') else None,
        types.InlineKeyboardButton("🔙 Назад", callback_data="teacher_panel")
    ]
    markup.add(*[b for b in buttons if b])
    bot.edit_message_text("📚 Меню заданий:", chat_id=user_id, message_id=call.message.message_id, reply_markup=markup)
@bot.callback_query_handler(func=lambda call: call.data.startswith('close_task_'))
def close_task(call: types.CallbackQuery):
    user_id = call.from_user.id
    if not check_access(user_id, 'учитель'):
        bot.send_message(user_id, "❌ У вас нет прав на закрытие заданий.")
        return

    try:
        task_id = int(call.data.split('_')[2])
    except (ValueError, IndexError):
        bot.send_message(user_id, "❌ Неверный формат данных для закрытия задания.")
        return

    manager = TaskManager(user_id)
    success, result = manager.change_task_status(task_id, 'closed')
    bot.send_message(user_id, result, reply_markup=teacher_tasks_menu_markup())
@bot.callback_query_handler(func=lambda call: call.data.startswith('view_answers_'))
def view_answers(call: types.CallbackQuery):
    user_id = call.from_user.id
    if not check_access(user_id, 'учитель'):
        bot.send_message(user_id, "❌ У вас нет прав на просмотр ответов.")
        return

    try:
        task_id = int(call.data.split('_')[2])
    except (ValueError, IndexError):
        bot.send_message(user_id, "❌ Неверный формат данных для просмотра ответов.")
        return

    manager = TaskManager(user_id)
    answers = manager.check_task_answers(task_id)
    if not answers:
        bot.send_message(user_id, f"❌ Нет ответов на задание #{task_id}.")
        return

    message = f"📋 Ответы на задание #{task_id}:\n"
    for full_name, answer_text, file_path, status in answers:
        if answer_text:
            answer_info = answer_text[:20] + "..." if len(answer_text) > 20 else answer_text
        elif file_path:
            answer_info = "Файл был отправлен"
        else:
            answer_info = "Нет ответа"
        message += (
            f"- Ученик: {full_name}\n"
            f"Ответ: {answer_info}\n"
            f"Статус: {status}\n"
        )

    bot.send_message(user_id, message, reply_markup=teacher_task_actions_markup(task_id))

def teacher_panel_markup() -> types.InlineKeyboardMarkup:
    markup = types.InlineKeyboardMarkup(row_width=2)
    buttons = [
        types.InlineKeyboardButton("📚 Задания", callback_data="teacher_tasks"),
        types.InlineKeyboardButton("➕ Создать задание", callback_data="create_task_menu"),
        types.InlineKeyboardButton("👥 Список учеников", callback_data="student_list"),
        types.InlineKeyboardButton("📊 Статистика учеников", callback_data="student_stats"),
        types.InlineKeyboardButton("🔙 Назад", callback_data="main_menu")
    ]
    markup.add(*buttons)
    return markup
# Список учеников
@bot.callback_query_handler(func=lambda call: call.data == 'student_list')
def student_list(call: types.CallbackQuery):
    user_id = call.from_user.id
    if not check_access(user_id, 'учитель'):
        bot.send_message(user_id, "❌ Недостаточно прав")
        return
    
    cursor.execute("""
        SELECT u.user_id, u.full_name, u.class, COUNT(w.work_id) AS total_works
        FROM users u
        LEFT JOIN works w ON u.user_id = w.user_id
        WHERE u.role = 'ученик'
        GROUP BY u.user_id
        ORDER BY u.class, u.full_name
    """)
    students = cursor.fetchall()
    
    if not students:
        bot.send_message(user_id, "❌ Нет зарегистрированных учеников.")
        return
    
    message = "📋 Список учеников:\n"
    for student in students:
        user_id, full_name, class_name, total_works = student
        message += f"- {full_name} ({class_name}) | Работ: {total_works}\n"
    
    bot.send_message(user_id, message, reply_markup=teacher_panel_markup())

# Статистика учеников
@bot.callback_query_handler(func=lambda call: call.data == 'student_stats')
def student_stats(call: types.CallbackQuery):
    user_id = call.from_user.id
    if not check_access(user_id, 'учитель'):
        bot.send_message(user_id, "❌ Недостаточно прав")
        return
    
    cursor.execute("""
        SELECT u.user_id, u.full_name, u.class,
               SUM(CASE WHEN w.status = 'Проверено' THEN 1 ELSE 0 END) AS checked,
               SUM(CASE WHEN w.status = 'Требует доработки' THEN 1 ELSE 0 END) AS redo,
               SUM(CASE WHEN w.status = 'Удалено' THEN 1 ELSE 0 END) AS deleted
        FROM users u
        LEFT JOIN works w ON u.user_id = w.user_id
        WHERE u.role = 'ученик'
        GROUP BY u.user_id
        ORDER BY u.class, u.full_name
    """)
    stats = cursor.fetchall()
    
    if not stats:
        bot.send_message(user_id, "❌ Нет данных о работе учеников.")
        return
    
    message = "📊 Статистика учеников:\n"
    for stat in stats:
        user_id, full_name, class_name, checked, redo, deleted = stat
        message += (
            f"- {full_name} ({class_name}):\n"
            f"  Проверено: {checked or 0}\n"
            f"  Требует доработки: {redo or 0}\n"
            f"  Удалено: {deleted or 0}\n\n"
        )
    
    bot.send_message(user_id, message, reply_markup=teacher_panel_markup())

# Исправление системы статусов работ
@bot.callback_query_handler(func=lambda call: call.data.startswith('set_status_'))
def process_status_change(call: types.CallbackQuery):
    user_id = call.from_user.id
    try:
        _, _, work_id, new_status = call.data.split('_', 3)
        work_id = int(work_id)
        
        cursor.execute("SELECT file_path, status FROM works WHERE work_id = ?", (work_id,))
        current_file_path, current_status = cursor.fetchone()
        
        if current_status == new_status:
            bot.send_message(user_id, f"❌ Статус работы #{work_id} уже установлен как '{new_status}'.")
            return
        
        # Определяем новую папку
        status_folders = {
            'Проверено': 'checked',
            'Требует доработки': 'redo',
            'Удалено': 'deleted'
        }
        
        if new_status not in status_folders:
            bot.send_message(user_id, f"❌ Неверный статус: {new_status}")
            return
        
        # Создаем новую папку если нужно
        new_folder = os.path.join(WORKS_FOLDER, status_folders[new_status])
        os.makedirs(new_folder, exist_ok=True)
        
        # Перемещаем файл
        new_file_name = os.path.basename(current_file_path)
        new_file_path = os.path.join(new_folder, new_file_name)
        os.rename(current_file_path, new_file_path)
        
        # Обновляем статус в базе данных
        cursor.execute(
            "UPDATE works SET status = ?, file_path = ? WHERE work_id = ?",
            (new_status, new_file_path, work_id)
        )
        conn.commit()
        
        bot.send_message(user_id, f"✅ Статус работы #{work_id} изменен на '{new_status}'")
        show_work_details(call, work_id)
        
    except Exception as e:
        bot.send_message(user_id, f"❌ Ошибка при изменении статуса: {str(e)}")

# Главное меню с рабочими кнопками
def main_menu_markup(user_id: int) -> types.InlineKeyboardMarkup:
    markup = types.InlineKeyboardMarkup(row_width=2)
    buttons = [
        types.InlineKeyboardButton("📚 Задания", callback_data="tasks_menu"),
        types.InlineKeyboardButton("📊 Статистика", callback_data="statistics"),
        types.InlineKeyboardButton("📂 Работы", callback_data="works"),
        types.InlineKeyboardButton("📨 Репорты", callback_data="reports"),
        types.InlineKeyboardButton("ℹ️ О боте", callback_data="about_bot")
    ]
    
    if check_access(user_id, 'учитель'):
        buttons.append(types.InlineKeyboardButton("👨‍🏫 Панель учителя", callback_data="teacher_panel"))
    
    if check_access(user_id, 'разработчик'):
        buttons.append(types.InlineKeyboardButton("👨‍💻 Панель разработчика", callback_data="dev_panel"))
    
    markup.add(*buttons)
    return markup

# Меню заданий
@bot.callback_query_handler(func=lambda call: call.data == 'tasks_menu')
def tasks_menu(call: types.CallbackQuery):
    user_id = call.from_user.id
    markup = types.InlineKeyboardMarkup(row_width=1)
    
    buttons = [
        types.InlineKeyboardButton("📋 Новые задания", callback_data="view_new_tasks"),
        types.InlineKeyboardButton("📚 Прошедшие задания", callback_data="view_old_tasks"),
        types.InlineKeyboardButton("➕ Создать задание", callback_data="create_task") if check_access(user_id, 'учитель') else None,
        types.InlineKeyboardButton("🔙 Назад", callback_data="main_menu")
    ]
    
    markup.add(*[b for b in buttons if b])
    bot.edit_message_text("📚 Меню заданий:", chat_id=user_id, message_id=call.message.message_id, reply_markup=markup)

# Функция для отображения деталей работы
def show_work_details(call: types.CallbackQuery, work_id: int):
    user_id = call.from_user.id
    cursor.execute("""
        SELECT w.work_id, u.full_name, w.file_path, w.status, w.created_at 
        FROM works w 
        JOIN users u ON w.user_id = u.user_id 
        WHERE w.work_id = ?
    """, (work_id,))
    result = cursor.fetchone()
    
    if not result:
        bot.send_message(user_id, "❌ Работа не найдена.")
        return
    
    work_id, full_name, file_path, status, created_at = result
    file_name = os.path.basename(file_path)
    
    message = (
        f"📋 Детали работы #{work_id}:\n"
        f"- Автор: {full_name}\n"
        f"- Файл: {file_name}\n"
        f"- Статус: {status}\n"
        f"- Дата загрузки: {created_at}\n"
    )
    
    markup = types.InlineKeyboardMarkup(row_width=1)
    buttons = [
        types.InlineKeyboardButton("⬇️ Скачать", callback_data=f"download_{work_id}"),
        types.InlineKeyboardButton("✏️ Изменить статус", callback_data=f"change_status_{work_id}"),
        types.InlineKeyboardButton("🔙 Назад", callback_data="view_works")
    ]
    markup.add(*buttons)
    
    bot.edit_message_text(message, chat_id=user_id, message_id=call.message.message_id, reply_markup=markup)

# Обработчик изменения статуса работы
@bot.callback_query_handler(func=lambda call: call.data.startswith('change_status_'))
def change_work_status(call: types.CallbackQuery):
    user_id = call.from_user.id
    try:
        _, _, work_id = call.data.split('_')
        work_id = int(work_id)
        
        cursor.execute("SELECT status FROM works WHERE work_id = ?", (work_id,))
        current_status = cursor.fetchone()[0]
        
        markup = types.InlineKeyboardMarkup(row_width=1)
        statuses = ['Проверено', 'Требует доработки', 'Удалено']
        
        for status in statuses:
            if status != current_status:
                markup.add(types.InlineKeyboardButton(status, callback_data=f"set_status_{work_id}_{status}"))
        
        markup.add(types.InlineKeyboardButton("🔙 Назад", callback_data=f"work_detail_{work_id}"))
        bot.edit_message_text("Выберите новый статус:", chat_id=user_id, message_id=call.message.message_id, reply_markup=markup)
        
    except Exception as e:
        bot.send_message(user_id, f"❌ Ошибка при изменении статуса: {str(e)}")

@bot.callback_query_handler(func=lambda call: call.data.startswith('set_report_status_'))
def process_report_status_change(call: types.CallbackQuery):
    user_id = call.from_user.id
    _, _, report_id, new_status = call.data.split('_', 3)
    report_id = int(report_id)
    cursor = conn.cursor()
    cursor.execute("UPDATE reports SET status = ? WHERE report_id = ?", (new_status, report_id))
    conn.commit()
    bot.send_message(user_id, f"✅ Статус репорта #{report_id} изменен на '{new_status}'")
    show_report_details(call, report_id)
@bot.callback_query_handler(func=lambda call: call.data.startswith('add_response_'))
def add_response(call: types.CallbackQuery):
    user_id = call.from_user.id
    report_id = int(call.data.split("_")[2])
    msg = bot.send_message(user_id, "Введите ответ на репорт:")
    bot.register_next_step_handler(msg, lambda m: process_add_response(m, report_id))

def process_add_response(message, report_id):
    user_id = message.from_user.id
    response = message.text.strip()
    cursor.execute("UPDATE reports SET response = ? WHERE report_id = ?", (response, report_id))
    conn.commit()
    bot.send_message(user_id, "✅ Ответ успешно добавлен.")
def show_report_details(call: types.CallbackQuery, report_id: int):
    user_id = call.from_user.id
    cursor = conn.cursor()
    cursor.execute("""
        SELECT r.report_id, r.text, r.status, r.response, r.created_at, u.full_name 
        FROM reports r
        JOIN users u ON r.user_id = u.user_id
        WHERE r.report_id = ?
    """, (report_id,))
    report = cursor.fetchone()
    if not report:
        bot.send_message(user_id, "❌ Репорт не найден.")
        return
    report_id, text, status, response, created_at, student_name = report
    message = (
        f"📝 Репорт #<b>{report_id}</b>"
        f"👤 Отправитель: <b>{student_name}</b>"
        f"📝 Текст: <i>{text}</i>"
        f"🔄 Статус: <b>{status}</b>"
        f"📅 Дата создания: <i>{created_at}</i>"
    )
    if response:
        message += f"❗️ Ответ: <i>{response}</i>"
    user = get_user(user_id)
    bot.edit_message_text(
        message,
        chat_id=user_id,
        message_id=call.message.message_id,
        parse_mode='HTML',
        reply_markup=report_detail_markup(report_id, user.role)
    )

def report_detail_markup(report_id: int, user_role: str) -> types.InlineKeyboardMarkup:
    markup = types.InlineKeyboardMarkup()
    if user_role in ['учитель', 'разработчик']:
        markup.add(types.InlineKeyboardButton("✏️ Изменить статус", callback_data=f"change_report_status_{report_id}"))
        markup.add(types.InlineKeyboardButton("💬 Добавить ответ", callback_data=f"add_response_{report_id}"))
    markup.add(types.InlineKeyboardButton("🔙 Назад", callback_data="reports"))
    return markup

# Инициализация базы данных
def init_db():
    conn = sqlite3.connect(DB_NAME, check_same_thread=False)
    global cursor 
    cursor = conn.cursor()
    
    # Таблица пользователей
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            full_name TEXT NOT NULL,
            role TEXT DEFAULT 'ученик',
            class TEXT,
            is_blocked BOOLEAN DEFAULT 0,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Таблица работ
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS works (
            work_id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            file_path TEXT NOT NULL,
            status TEXT DEFAULT 'Не проверено',
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            teacher_comment TEXT,
            FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
        )
    ''')
    
    # Таблица репортов
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS reports (
            report_id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            text TEXT NOT NULL,
            status TEXT DEFAULT 'Не проверено',
            response TEXT,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
        )
    ''')
    
    # Таблица классов
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS classes (
            class_id INTEGER PRIMARY KEY AUTOINCREMENT,
            class_name TEXT UNIQUE NOT NULL
        )
    ''')
    
    # Таблица заданий
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS tasks (
            task_id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            description TEXT NOT NULL,
            status TEXT DEFAULT 'active',
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Таблица ответов учеников на задания
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS answers (
            answer_id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            task_id INTEGER NOT NULL,
            answer_text TEXT,
            file_path TEXT,
            status TEXT DEFAULT 'Не проверено',
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            teacher_comment TEXT,
            FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE,
            FOREIGN KEY (task_id) REFERENCES tasks(task_id) ON DELETE CASCADE
        )
    ''')
    
    # Добавляем суперпользователя (разработчика)
    cursor.execute("""
        INSERT OR IGNORE INTO users (user_id, username, full_name, role, class)
        VALUES (?, ?, ?, ?, ?)
    """, (api.DEV_ID, "Евгений", "Вершинин", "разработчик", "9А"))
    
    # Добавляем тестовые классы, если их нет
    default_classes = api.CLASS_LIST
    for class_name in default_classes:
        cursor.execute("INSERT OR IGNORE INTO classes (class_name) VALUES (?)", (class_name,))
    
    conn.commit()
    return conn

# Инициализация соединения с БД
conn = init_db()

# Вспомогательные функции
def get_user(user_id: int) -> Optional[User]:
    cursor = conn.cursor()
    cursor.execute("SELECT user_id, username, full_name, role, class, is_blocked FROM users WHERE user_id = ?", (user_id,))
    row = cursor.fetchone()
    return User(*row) if row else None

def is_user_blocked(user_id: int) -> bool:
    cursor = conn.cursor()
    cursor.execute("SELECT is_blocked FROM users WHERE user_id = ?", (user_id,))
    return cursor.fetchone()[0] == 1

def check_access(user_id: int, required_role: str) -> bool:
    cursor.execute("SELECT role FROM users WHERE user_id = ?", (user_id,))
    user = cursor.fetchone()
    if not user:
        return False
    return user[0] == required_role or user[0] == 'разработчик'
def move_file_to_status_folder(file_path: str, new_status: str) -> str:
    """Перемещает файл в папку согласно новому статусу."""
    status_folders = {
        'Проверено': 'checked',
        'Требует доработки': 'redo',
        'Удалено': 'deleted'
    }

    if new_status not in status_folders:
        print(f"Error: Invalid status {new_status}")
        return file_path

    base_name = os.path.basename(file_path)
    new_folder = os.path.join(WORKS_FOLDER, status_folders[new_status])
    os.makedirs(new_folder, exist_ok=True)
    new_path = os.path.join(new_folder, base_name)

    try:
        os.rename(file_path, new_path)
        return new_path
    except OSError as e:
        print(f"Error moving file: {e}")
        return file_path

def get_current_datetime() -> str:
    return datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')

# Обработчики команд
@bot.message_handler(commands=['start'])
def start(message: types.Message):
    user_id = message.from_user.id
    
    if is_user_blocked(user_id):
        bot.send_message(user_id, "⛔ Вы заблокированы. Обратитесь к администратору.")
        return
    
    user = get_user(user_id)
    
    if not user:
        # Регистрация нового пользователя
        msg = bot.send_message(user_id, "👋 Добро пожаловать! Для регистрации введите ваше имя и фамилию:")
        bot.register_next_step_handler(msg, process_full_name_step)
    else:
        bot.send_message(user_id, f"✅ Вы уже зарегистрированы как {user.full_name}!", 
                         reply_markup=main_menu_markup(user_id))

def process_full_name_step(message: types.Message):
    user_id = message.from_user.id
    full_name = message.text.strip()
    
    if len(full_name.split()) < 2:
        msg = bot.send_message(user_id, "❌ Пожалуйста, введите имя и фамилию через пробел:")
        bot.register_next_step_handler(msg, process_full_name_step)
        return
    
    cursor = conn.cursor()
    cursor.execute("INSERT INTO users (user_id, username, full_name) VALUES (?, ?, ?)", 
                  (user_id, message.from_user.username, full_name))
    conn.commit()
    
    bot.send_message(user_id, "🏫 Выберите ваш класс:", reply_markup=classes_markup())

@bot.callback_query_handler(func=lambda call: call.data.startswith('select_class_'))
def process_class_selection(call: types.CallbackQuery):
    user_id = call.from_user.id
    class_name = call.data.split('_')[2]
    
    cursor = conn.cursor()
    cursor.execute("UPDATE users SET class = ? WHERE user_id = ?", (class_name, user_id))
    conn.commit()
    
    bot.edit_message_text(f"✅ Вы выбрали класс {class_name}. Регистрация завершена!", 
                         chat_id=user_id, 
                         message_id=call.message.message_id)
    bot.send_message(user_id, "📋 Главное меню:", reply_markup=main_menu_markup(user_id))

# Меню и клавиатуры
def classes_markup() -> types.InlineKeyboardMarkup:
    cursor = conn.cursor()
    cursor.execute("SELECT class_name FROM classes ORDER BY class_name")
    classes = cursor.fetchall()
    
    markup = types.InlineKeyboardMarkup()
    for class_name in classes:
        markup.add(types.InlineKeyboardButton(class_name[0], callback_data=f"select_class_{class_name[0]}"))
    return markup
@bot.callback_query_handler(func=lambda call: call.data == 'teacher_panel')
def show_teacher_panel(call: types.CallbackQuery):
    user_id = call.from_user.id
    user = get_user(user_id)
    
    if not user:
        bot.send_message(user_id, "❌ Ваш профиль не найден. Пожалуйста, зарегистрируйтесь снова.")
        return
    
    # Разрешаем доступ к панели учителя как учителю, так и разработчику
    if user.role in ['учитель', 'разработчик']:
        bot.edit_message_text("👨‍🏫 Панель учителя:", 
                             chat_id=user_id, 
                             message_id=call.message.message_id, 
                             reply_markup=teacher_panel_markup())
    else:
        bot.send_message(user_id, "❌ У вас нет прав на доступ к панели учителя.")
def main_menu_markup(user_id: int) -> types.InlineKeyboardMarkup:
    user = get_user(user_id)
    markup = types.InlineKeyboardMarkup(row_width=2)
    
    # Общие кнопки
    buttons = [
        types.InlineKeyboardButton("📚 Задания", callback_data="tasks_menu"),
        types.InlineKeyboardButton("📊 Статистика", callback_data="statistics"),
        types.InlineKeyboardButton("📂 Работы", callback_data="works"),
        types.InlineKeyboardButton("📨 Репорты", callback_data="reports"),
        types.InlineKeyboardButton("ℹ️ О боте", callback_data="about_bot")
    ]
    
    # Дополнительные кнопки для учителя
    if check_access(user_id, 'учитель'):
        buttons.append(types.InlineKeyboardButton("👨‍🏫 Панель учителя", callback_data="teacher_panel"))
    
    # Кнопки для разработчика
    if check_access(user_id, 'разработчик'):
        buttons.append(types.InlineKeyboardButton("👨‍💻 Панель разработчика", callback_data="dev_panel"))
    
    markup.add(*buttons)
    return markup
@bot.callback_query_handler(func=lambda call: call.data == 'about_bot')
def about_bot(call: types.CallbackQuery):
    user_id = call.from_user.id
    bot.edit_message_text(
        "🤖 Информация о боте:\n"
        "Это учебный бот для управления заданиями, работами и взаимодействием между учениками и учителями.\n"
        "Основные возможности:\n"
        "- Загрузка и проверка работ\n"
        "- Создание и управление заданиями\n"
        "- Система репортов\n"
        "- Статистика выполненных работ\n",
        chat_id=user_id,
        message_id=call.message.message_id,
        reply_markup=types.InlineKeyboardMarkup().add(
            types.InlineKeyboardButton("🔙 Назад", callback_data="main_menu")
        )
    )

@bot.callback_query_handler(func=lambda call: call.data == 'send_report')
def send_report(call: types.CallbackQuery):
    user_id = call.from_user.id
    msg = bot.send_message(user_id, "📝 Напишите ваш репорт или жалобу:")
    bot.register_next_step_handler(msg, process_send_report)

def process_send_report(message: types.Message):
    user_id = message.from_user.id
    report_text = message.text.strip()
    if len(report_text) < 10:
        msg = bot.send_message(user_id, "❌ Текст репорта слишком короткий. Пожалуйста, напишите подробнее:")
        bot.register_next_step_handler(msg, process_send_report)
        return
    
    cursor.execute("INSERT INTO reports (user_id, text, status) VALUES (?, ?, ?)", 
                  (user_id, report_text, "Не проверено"))
    conn.commit()
    
    bot.send_message(user_id, "✅ Ваш репорт отправлен на рассмотрение.", reply_markup=main_menu_markup(user_id))
    notify_about_new_report(user_id, report_text)
@bot.callback_query_handler(func=lambda call: call.data == 'my_works')
def show_my_works(call: types.CallbackQuery):
    user_id = call.from_user.id
    cursor.execute("""
        SELECT w.work_id, w.file_path, w.status, w.created_at 
        FROM works w
        WHERE w.user_id = ?
        ORDER BY w.created_at DESC
    """, (user_id,))
    works = cursor.fetchall()
    if not works:
        bot.send_message(user_id, "❌ У вас пока нет загруженных работ.")
        return
    
    message = "📋 Ваши работы:\n"
    for work in works:
        work_id, file_path, status, created_at = work
        file_name = os.path.basename(file_path)
        message += (
            f"- #{work_id}: {file_name}\n"
            f"🔄 Статус: {status}\n"
            f"📅 Дата загрузки: {created_at}\n\n"
        )
    
    bot.send_message(user_id, message)

def works_markup(user_id: int) -> types.InlineKeyboardMarkup:
    user = get_user(user_id)
    if not user:
        return types.InlineKeyboardMarkup()
    
    markup = types.InlineKeyboardMarkup(row_width=1)
    if user.role == 'ученик':
        cursor.execute("SELECT work_id, file_path, status FROM works WHERE user_id = ? ORDER BY created_at DESC", (user_id,))
        works = cursor.fetchall()
        for work_id, file_path, status in works:
            name = os.path.basename(file_path)
            markup.add(types.InlineKeyboardButton(
                f"{name} ({status})", 
                callback_data=f"work_detail_{work_id}"
            ))
        
        # Добавляем кнопку "Мои работы"
        markup.add(types.InlineKeyboardButton("📋 Мои работы", callback_data="my_works"))
        markup.add(types.InlineKeyboardButton("📤 Загрузить работу", callback_data="upload_work"))
    elif user.role == 'учитель':
        markup.add(types.InlineKeyboardButton("👀 Просмотр работ", callback_data="view_works"))
        markup.add(types.InlineKeyboardButton("✅ Проверить работы", callback_data="check_works"))
    else:
        markup.add(types.InlineKeyboardButton("📋 Мои работы", callback_data="my_works"))
        markup.add(types.InlineKeyboardButton("📤 Загрузить работу", callback_data="upload_work"))
        markup.add(types.InlineKeyboardButton("👀 Просмотр работ", callback_data="view_works"))
        markup.add(types.InlineKeyboardButton("✅ Проверить работы", callback_data="check_works"))
    
    markup.add(types.InlineKeyboardButton("🔙 Назад", callback_data="main_menu"))
    return markup
@bot.callback_query_handler(func=lambda call: call.data == 'view_works')
def view_works(call: types.CallbackQuery):
    user_id = call.from_user.id
    if not check_access(user_id, 'учитель'):
        bot.send_message(user_id, "❌ У вас нет прав на просмотр работ.")
        return
    
    cursor.execute("""
        SELECT w.work_id, u.full_name, w.file_path, w.status, w.created_at 
        FROM works w
        JOIN users u ON w.user_id = u.user_id
        ORDER BY w.created_at DESC
    """)
    works = cursor.fetchall()
    if not works:
        bot.edit_message_text("📂 Нет загруженных работ.", 
                             chat_id=user_id, 
                             message_id=call.message.message_id)
        return
    
    message = "📂 Список работ:\n"
    for work in works:
        work_id, full_name, file_path, status, created_at = work
        file_name = os.path.basename(file_path)
        message += (
            f"- #{work_id} от {full_name}\n"
            f"📄 Файл: {file_name}\n"
            f"🔄 Статус: {status}\n"
            f"📅 Дата загрузки: {created_at}\n\n"
        )
    
    bot.edit_message_text(message, 
                         chat_id=user_id, 
                         message_id=call.message.message_id, 
                         reply_markup=view_works_markup(works))

def view_works_markup(works: List[Tuple]) -> types.InlineKeyboardMarkup:
    markup = types.InlineKeyboardMarkup(row_width=2)
    for work in works:
        work_id = work[0]
        markup.add(types.InlineKeyboardButton(
            f"Работа #{work_id}", 
            callback_data=f"work_detail_{work_id}"
        ))
    markup.add(types.InlineKeyboardButton("🔙 Назад", callback_data="teacher_panel"))
    return markup
@bot.callback_query_handler(func=lambda call: call.data == 'check_works')
def check_works(call: types.CallbackQuery):
    user_id = call.from_user.id
    if not check_access(user_id, 'учитель'):
        bot.send_message(user_id, "❌ У вас нет прав на проверку работ.")
        return
    
    cursor.execute("""
        SELECT w.work_id, u.full_name, w.file_path, w.status, w.created_at 
        FROM works w
        JOIN users u ON w.user_id = u.user_id
        WHERE w.status = 'Не проверено'
        ORDER BY w.created_at DESC
    """)
    works = cursor.fetchall()
    if not works:
        bot.send_message(user_id, "❌ Сейчас нет работ для проверки.")
        return
    
    message = "📋 Список работ для проверки:\n"
    for work in works:
        work_id, full_name, file_path, status, created_at = work
        file_name = os.path.basename(file_path)
        message += (
            f"- #{work_id} от {full_name}\n"
            f"📁 Файл: {file_name}\n"
            f"📅 Дата загрузки: {created_at}\n\n"
        )
    
    bot.send_message(user_id, message, reply_markup=check_works_markup(works))

def check_works_markup(works: List[Tuple]) -> types.InlineKeyboardMarkup:
    markup = types.InlineKeyboardMarkup(row_width=1)
    for work in works:
        work_id = work[0]
        markup.add(types.InlineKeyboardButton(
            f"Работа #{work_id}", 
            callback_data=f"work_detail_{work_id}"
        ))
    markup.add(types.InlineKeyboardButton("🔙 Назад", callback_data="teacher_panel"))
    return markup
def work_detail_markup(work_id: int, user_role: str) -> types.InlineKeyboardMarkup:
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("⬇️ Скачать", callback_data=f"download_{work_id}"))
    
    if user_role in ['учитель', 'разработчик']:
        markup.add(types.InlineKeyboardButton("✏️ Изменить статус", callback_data=f"change_status_{work_id}"))
        markup.add(types.InlineKeyboardButton("💬 Добавить комментарий", callback_data=f"add_comment_{work_id}"))
    
    markup.add(types.InlineKeyboardButton("🔙 Назад", callback_data="works"))
    return markup
@bot.callback_query_handler(func=lambda call: call.data.startswith('add_comment_'))
def add_comment(call: types.CallbackQuery):
    user_id = call.from_user.id
    work_id = int(call.data.split('_')[2])
    msg = bot.send_message(user_id, f"📝 Введите комментарий к работе #{work_id}:")
    bot.register_next_step_handler(msg, lambda m: process_add_comment(m, work_id))

def process_add_comment(message: types.Message, work_id: int):
    user_id = message.from_user.id
    comment = message.text.strip()
    if not comment:
        bot.send_message(user_id, "❌ Комментарий не может быть пустым.")
        return
    
    cursor.execute("UPDATE works SET teacher_comment = ? WHERE work_id = ?", (comment, work_id))
    conn.commit()
    bot.send_message(user_id, f"✅ Комментарий успешно добавлен к работе #{work_id}.")
    show_work_details(message, work_id)
def teacher_panel_markup() -> types.InlineKeyboardMarkup:
    markup = types.InlineKeyboardMarkup(row_width=2)
    buttons = [
        types.InlineKeyboardButton("📚 Список всех заданий", callback_data="teacher_task_list"),
        types.InlineKeyboardButton("➕ Создать новое задание", callback_data="create_task"),
        types.InlineKeyboardButton("🔒 Закрыть задание", callback_data="close_task_menu"),
        types.InlineKeyboardButton("🔍 Проверить ответы", callback_data="check_task_menu"),
        types.InlineKeyboardButton("🗑️ Удалить задание", callback_data="delete_task_menu"),
        types.InlineKeyboardButton("🔙 Назад", callback_data="main_menu")
    ]
    markup.add(*buttons)
    return markup
@bot.callback_query_handler(func=lambda call: call.data == 'reports')
def handle_reports(call: types.CallbackQuery):
    user_id = call.from_user.id
    user = get_user(user_id)
    if not user:
        bot.send_message(user_id, "❌ Ваш профиль не найден. Пожалуйста, зарегистрируйтесь снова.")
        return
    if user.role == 'ученик':
        msg = bot.send_message(user_id, "📝 Напишите ваш репорт или жалобу:")
        bot.register_next_step_handler(msg, process_student_report)
    elif user.role in ['учитель', 'разработчик']:
        show_reports_list(call)

@bot.callback_query_handler(func=lambda call: call.data == 'student_list_with_stats')
def show_student_list_with_stats(call: types.CallbackQuery):
    user_id = call.from_user.id
    if not check_access(user_id, 'учитель'):
        bot.send_message(user_id, "❌ У вас нет прав на просмотр списка учеников.")
        return
    
    cursor.execute("""
        SELECT u.user_id, u.full_name, u.class, COUNT(w.work_id) AS total_works,
               SUM(CASE WHEN w.status = 'Проверено' THEN 1 ELSE 0 END) AS checked_works
        FROM users u
        LEFT JOIN works w ON u.user_id = w.user_id
        WHERE u.role = 'ученик'
        GROUP BY u.user_id
    """)
    students = cursor.fetchall()
    
    if not students:
        bot.send_message(user_id, "❌ Нет зарегистрированных учеников.")
        return
    
    bot.send_message(
        user_id, 
        "📋 Список учеников:", 
        reply_markup=students_list_markup(students)
    )

def students_list_markup(students: List[Tuple]) -> types.InlineKeyboardMarkup:
    markup = types.InlineKeyboardMarkup(row_width=1)
    for student in students:
        student_id, full_name, class_name, total_works, checked_works = student
        stats = f"{checked_works}/{total_works}" if total_works else "Нет работ"
        button_text = f"{full_name} ({class_name or 'Не указан'}) - {stats}"
        markup.add(types.InlineKeyboardButton(button_text, callback_data=f"student_detail_{student_id}"))
    markup.add(types.InlineKeyboardButton("🔙 Назад", callback_data="teacher_panel"))
    return markup
@bot.callback_query_handler(func=lambda call: call.data.startswith('student_detail_'))
def student_detail(call: types.CallbackQuery):
    user_id = call.from_user.id
    student_id = int(call.data.split('_')[2])
    
    cursor.execute("""
        SELECT u.full_name, u.class, COUNT(w.work_id) AS total_works, 
               SUM(CASE WHEN w.status = 'Проверено' THEN 1 ELSE 0 END) AS checked_works
        FROM users u
        LEFT JOIN works w ON u.user_id = w.user_id
        WHERE u.user_id = ? AND u.role = 'ученик'
        GROUP BY u.user_id
    """, (student_id,))
    student = cursor.fetchone()
    
    if not student:
        bot.send_message(user_id, "❌ Ученик не найден.")
        return
    
    full_name, class_name, total_works, checked_works = student
    stats = f"{checked_works}/{total_works}" if total_works else "Нет работ"
    
    bot.send_message(
        user_id, 
        f"📋 Информация об ученике:\n"
        f"Имя: {full_name}\n"
        f"Класс: {class_name or 'Не указан'}\n"
        f"Статистика работ: {stats}",
        reply_markup=types.InlineKeyboardMarkup().add(
            types.InlineKeyboardButton("🔙 Назад", callback_data="student_list_with_stats")
        )
    )
def dev_panel_markup() -> types.InlineKeyboardMarkup:
    markup = types.InlineKeyboardMarkup(row_width=2)
    buttons = [
        types.InlineKeyboardButton("👨‍🏫 Назначить учителя", callback_data="assign_teacher"),
        types.InlineKeyboardButton("🚫 Блокировки", callback_data="ban_management"),
        types.InlineKeyboardButton("📁 Экспорт данных", callback_data="export_data"),
        types.InlineKeyboardButton("📥 Импорт данных", callback_data="import_data"),
        types.InlineKeyboardButton("📊 Полная статистика", callback_data="full_stats"),
        types.InlineKeyboardButton("📋 Список репортов", callback_data="reports"),  # Разработчик видит репорты
        types.InlineKeyboardButton("📚 Список заданий", callback_data="teacher_task_list"),  # Разработчик видит задания
        types.InlineKeyboardButton("📝 Список учеников", callback_data="student_list"),  # Разработчик видит учеников
        types.InlineKeyboardButton("🔙 Назад", callback_data="main_menu")
    ]
    markup.add(*buttons)
    return markup
@bot.callback_query_handler(func=lambda call: call.data == 'full_stats')
def full_statistics(call):
    user_id = call.from_user.id
    if not check_access(user_id, 'разработчик'):
        bot.send_message(user_id, "❌ У вас нет прав на просмотр полной статистики.")
        return

    # Статистика пользователей
    cursor.execute("""
        SELECT COUNT(*), role 
        FROM users 
        GROUP BY role
    """)
    user_stats = cursor.fetchall()

    # Статистика работ
    cursor.execute("""
        SELECT COUNT(*), status 
        FROM works 
        GROUP BY status
    """)
    work_stats = cursor.fetchall()

    # Статистика репортов
    cursor.execute("""
        SELECT COUNT(*), status 
        FROM reports 
        GROUP BY status
    """)
    report_stats = cursor.fetchall()

    stats = (
        "📊 Полная статистика:\n\n"
        "👥 Пользователи:\n"
    )
    for count, role in user_stats:
        stats += f"- {role}: {count}\n"

    stats += "\n📂 Работы:\n"
    for count, status in work_stats:
        stats += f"- {status}: {count}\n"

    stats += "\n📨 Репорты:\n"
    for count, status in report_stats:
        stats += f"- {status}: {count}\n"

    bot.send_message(user_id, stats)
# Обработчики callback-запросов
# Функция для показа статистики пользователя
@bot.callback_query_handler(func=lambda call: call.data == 'assign_teacher')
def assign_teacher(call):
    user_id = call.from_user.id
    if not check_access(user_id, 'разработчик'):
        bot.send_message(user_id, "❌ У вас нет прав на назначение учителя.")
        return

    msg = bot.send_message(user_id, "Введите ID пользователя для назначения учителем:")
    bot.register_next_step_handler(msg, process_assign_teacher)

def process_assign_teacher(message: types.Message):
    user_id = message.from_user.id
    target_id = message.text.strip()
    
    try:
        target_id = int(target_id)
    except ValueError:
        bot.send_message(user_id, "❌ Неверный формат ID. Пожалуйста, введите число.")
        return
    
    # Проверяем, существует ли пользователь с таким ID
    cursor.execute("SELECT user_id FROM users WHERE user_id = ?", (target_id,))
    if not cursor.fetchone():
        bot.send_message(user_id, f"❌ Пользователь с ID {target_id} не найден.")
        return
    
    # Назначаем роль "учитель"
    cursor.execute("UPDATE users SET role = 'учитель' WHERE user_id = ?", (target_id,))
    conn.commit()
    
    bot.send_message(user_id, f"✅ Пользователь {target_id} назначен учителем.")
    bot.send_message(target_id, "✅ Вы были назначены учителем администратором.")
def show_user_statistics(call):
    user_id = call.from_user.id

    # Запрос данных пользователя
    cursor.execute("""
        SELECT username , full_name, class, role, created_at 
        FROM users 
        WHERE user_id = ?
    """, (user_id,))
    user_info = cursor.fetchone()

    # Проверка, что пользователь существует
    if not user_info:
        bot.send_message(user_id, "❌ Профиль пользователя не найден. Пожалуйста, зарегистрируйтесь снова.")
        return

    # Разбор данных пользователя
    username , full_name, class_name, role, created_at = user_info

    # Разделение имени и фамилии из full_name
    name_parts = full_name.split()
    first_name = name_parts[0] if len(name_parts) > 0 else 'Не указано'
    last_name = name_parts[1] if len(name_parts) > 1 else 'Не указана'

    # Статистика работ
    cursor.execute("""
        SELECT COUNT(*), status 
        FROM works 
        WHERE user_id = ? 
        GROUP BY status
    """, (user_id,))
    works_stats = cursor.fetchall()

    # Статистика репортов
    cursor.execute("""
        SELECT COUNT(*), status 
        FROM reports 
        WHERE user_id = ? 
        GROUP BY status
    """, (user_id,))
    reports_stats = cursor.fetchall()

    # Формирование сообщения
    stats = (
        f"📋 Ваш профиль:\n"
        f"Имя: {username}\n"
        f"Фамилия: {first_name}\n"
        f"Роль: {role or 'Не указана'}\n"
        f"Класс: {class_name or 'Не указан'}\n"
        f"Дата регистрации: {created_at}\n\n"
        f"📊 Статистика работ:\n"
    )

    for count, status in works_stats:
        stats += f"- {status}: {count}\n"

    stats += "\n📊 Статистика репортов:\n"
    for count, status in reports_stats:
        stats += f"- {status}: {count}\n"

    # Отправка сообщения
    bot.send_message(user_id, stats)

# Функция для уведомления об новом репорте
def notify_about_new_report(user_id, report_text):
    # Получаем список учителей и разработчиков
    cursor.execute("SELECT user_id FROM users WHERE role IN ('учитель', 'разработчик')")
    admins = cursor.fetchall()

    for admin_id, in admins:
        try:
            bot.send_message(admin_id, f"🚨 Новый репорт от пользователя {user_id}:\n{report_text}")
        except Exception as e:
            print(f"Ошибка при отправке уведомления админу {admin_id}: {e}")
@bot.callback_query_handler(func=lambda call: call.data == 'broadcast')
def broadcast_menu(call):
    user_id = call.from_user.id
    if not check_access(user_id, 'учитель'):
        bot.send_message(user_id, "❌ У вас нет прав на рассылку.")
        return

    markup = types.InlineKeyboardMarkup(row_width=2)
    buttons = [
        types.InlineKeyboardButton("👥 Пользователям", callback_data="broadcast_users"),
        types.InlineKeyboardButton("📢 В группу", callback_data="broadcast_group"),
        types.InlineKeyboardButton("🔙 Назад", callback_data="teacher_panel")
    ]
    markup.add(*buttons)
    bot.edit_message_text("Выберите тип рассылки:", chat_id=user_id, message_id=call.message.message_id, reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data in ['broadcast_users', 'broadcast_group'])
def process_broadcast_type(call):
    user_id = call.from_user.id
    broadcast_type = call.data.split('_')[1]
    msg = bot.send_message(user_id, "Введите текст рассылки:")
    bot.register_next_step_handler(msg, lambda m: process_broadcast(m, broadcast_type))

def process_broadcast(message, broadcast_type):
    user_id = message.from_user.id
    broadcast_text = message.text
    if broadcast_type == "users":
        cursor.execute("SELECT user_id FROM users")
        users = cursor.fetchall()
        for user in users:
            try:
                bot.send_message(user[0], f"📢 Рассылка от администратора:\n{broadcast_text}")
            except Exception as e:
                print(f"Ошибка при отправке рассылки пользователю {user[0]}: {e}")
        bot.send_message(user_id, "✅ Рассылка успешно отправлена пользователям!", 
                         reply_markup=main_menu_markup(user_id))
    elif broadcast_type == "group":
        try:
            bot.send_message(api.CHANNEL_ID, f"📢 Рассылка от администратора:\n{broadcast_text}")
            bot.send_message(user_id, "✅ Рассылка успешно отправлена в группу!", 
                             reply_markup=main_menu_markup(user_id))
        except Exception as e:
            bot.send_message(user_id, f"❌ Ошибка при отправке рассылки в группу: {str(e)}", 
                             reply_markup=main_menu_markup(user_id))
@bot.callback_query_handler(func=lambda call: call.data == 'manage_classes')
def manage_classes_menu(call):
    user_id = call.from_user.id
    if not check_access(user_id, 'учитель'):
        bot.send_message(user_id, "❌ У вас нет прав на управление классами.")
        return

    markup = types.InlineKeyboardMarkup(row_width=2)
    buttons = [
        types.InlineKeyboardButton("➕ Добавить класс", callback_data="add_class"),
        types.InlineKeyboardButton("➖ Удалить класс", callback_data="remove_class"),
        types.InlineKeyboardButton("📋 Список классов", callback_data="list_classes"),
        types.InlineKeyboardButton("🔙 Назад", callback_data="teacher_panel")
    ]
    markup.add(*buttons)
    bot.edit_message_text("👥 Управление классами:", chat_id=user_id, message_id=call.message.message_id, reply_markup=markup)
@bot.callback_query_handler(func=lambda call: call.data == 'remove_class')
def remove_class(call: types.CallbackQuery):
    user_id = call.from_user.id
    if not check_access(user_id, 'учитель'):
        bot.send_message(user_id, "❌ У вас нет прав на удаление классов.")
        return
    msg = bot.send_message(user_id, "Введите название класса, который хотите удалить:")
    bot.register_next_step_handler(msg, process_remove_class)
def process_remove_class(message: types.Message):
    user_id = message.from_user.id
    class_name = message.text.strip()
    cursor.execute("SELECT class_id FROM classes WHERE class_name = ?", (class_name,))
    class_data = cursor.fetchone()
    if not class_data:
        bot.send_message(user_id, f"❌ Класс '{class_name}' не найден.")
        return
    class_id = class_data[0]
    cursor.execute("DELETE FROM classes WHERE class_id = ?", (class_id,))
    conn.commit()
    bot.send_message(user_id, f"✅ Класс '{class_name}' успешно удален.", reply_markup=main_menu_markup(user_id))
@bot.callback_query_handler(func=lambda call: call.data == 'add_class')
def add_class(call):
    user_id = call.from_user.id
    msg = bot.send_message(user_id, "Введите название нового класса:")
    bot.register_next_step_handler(msg, process_add_class)

def process_add_class(message):
    user_id = message.from_user.id
    class_name = message.text.strip()
    cursor.execute("INSERT OR IGNORE INTO classes (class_name) VALUES (?)", (class_name,))
    conn.commit()
    bot.send_message(user_id, f"✅ Класс '{class_name}' добавлен.", reply_markup=main_menu_markup(user_id))

@bot.callback_query_handler(func=lambda call: call.data == 'list_classes')
def list_classes(call):
    user_id = call.from_user.id
    cursor.execute("SELECT class_name FROM classes ORDER BY class_name")
    classes = cursor.fetchall()

    if not classes:
        bot.send_message(user_id, "❌ Нет доступных классов.")
        return

    message = "📋 Список классов:\n"
    for class_name in classes:
        message += f"- {class_name[0]}\n"

    bot.send_message(user_id, message)
@bot.callback_query_handler(func=lambda call: call.data == 'ban_user')
def ask_user_id_to_ban(call: types.CallbackQuery):
    user_id = call.from_user.id
    if not check_access(user_id, 'разработчик'):
        bot.send_message(user_id, "❌ У вас нет прав на блокировку пользователей.")
        return
    msg = bot.send_message(user_id, "Введите ID пользователя для блокировки:")
    bot.register_next_step_handler(msg, process_ban_user)

def process_ban_user(message: types.Message):
    user_id = message.from_user.id
    target_id = message.text.strip()
    try:
        target_id = int(target_id)
    except ValueError:
        bot.send_message(user_id, "❌ Неверный формат ID. Пожалуйста, введите число.")
        return

    # Проверяем, существует ли пользователь с таким ID
    cursor.execute("SELECT user_id FROM users WHERE user_id = ?", (target_id,))
    if not cursor.fetchone():
        bot.send_message(user_id, "❌ Пользователь с указанным ID не найден.")
        return

    if target_id == user_id:
        bot.send_message(user_id, "❌ Вы не можете заблокировать себя.")
        return

    # Блокируем пользователя
    cursor.execute("UPDATE users SET is_blocked = 1 WHERE user_id = ?", (target_id,))
    conn.commit()

    # Отправляем уведомление заблокированному пользователю
    bot.send_message(target_id, "⛔ Вы были заблокированы администратором.")

    # Подтверждаем операцию администратору
    bot.send_message(user_id, f"✅ Пользователь {target_id} успешно заблокирован.", 
                     reply_markup=main_menu_markup(user_id))
@bot.callback_query_handler(func=lambda call: call.data == 'unban_user')
def ask_user_id_to_unban(call: types.CallbackQuery):
    user_id = call.from_user.id
    if not check_access(user_id, 'разработчик'):
        bot.send_message(user_id, "❌ У вас нет прав на разблокировку пользователей.")
        return
    msg = bot.send_message(user_id, "Введите ID пользователя для разблокировки:")
    bot.register_next_step_handler(msg, process_unban_user)

def process_unban_user(message: types.Message):
    user_id = message.from_user.id
    target_id = message.text.strip()
    try:
        target_id = int(target_id)
    except ValueError:
        bot.send_message(user_id, "❌ Неверный формат ID. Пожалуйста, введите число.")
        return

    # Проверяем, существует ли пользователь с таким ID
    cursor.execute("SELECT user_id FROM users WHERE user_id = ?", (target_id,))
    if not cursor.fetchone():
        bot.send_message(user_id, "❌ Пользователь с указанным ID не найден.")
        return

    # Разблокируем пользователя
    cursor.execute("UPDATE users SET is_blocked = 0 WHERE user_id = ?", (target_id,))
    conn.commit()

    # Отправляем уведомление разблокированному пользователю
    bot.send_message(target_id, "✅ Вы были разблокированы администратором.")

    # Подтверждаем операцию администратору
    bot.send_message(user_id, f"✅ Пользователь {target_id} успешно разблокирован.", 
                     reply_markup=main_menu_markup(user_id))

@bot.callback_query_handler(func=lambda call: call.data == 'banned_list')
def banned_list(call):
    user_id = call.from_user.id
    cursor.execute("SELECT user_id, full_name FROM users WHERE is_blocked = 1")
    banned_users = cursor.fetchall()

    if not banned_users:
        bot.send_message(user_id, "❌ Нет заблокированных пользователей.")
        return

    message = "📋 Список заблокированных пользователей:\n"
    for user in banned_users:
        message += f"- ID: {user[0]}, Имя: {user[1]}\n"

    bot.send_message(user_id, message)
@bot.callback_query_handler(func=lambda call: True)
def callback_handler(call: types.CallbackQuery):
    user_id = call.from_user.id
    if is_user_blocked(user_id):
        bot.send_message(user_id, "⛔ Вы заблокированы. Обратитесь к администратору.")
        return
    
    user = get_user(user_id)
    if not user:
        bot.send_message(user_id, "❌ Ваш профиль не найден. Пожалуйста, зарегистрируйтесь снова.")
        return
    
    try:
        if call.data == "main_menu":
            bot.edit_message_text("📋 Главное меню:", 
                                chat_id=user_id, 
                                message_id=call.message.message_id, 
                                reply_markup=main_menu_markup(user_id))
        elif call.data == "statistics":
            show_user_statistics(call)
        elif call.data == "works":
            bot.edit_message_text("📂 Ваши работы:", 
                                chat_id=user_id, 
                                message_id=call.message.message_id, 
                                reply_markup=works_markup(user_id))
        elif call.data == "upload_work":
            msg = bot.send_message(user_id, "📎 Пожалуйста, загрузите файл с вашей работой:")
            bot.register_next_step_handler(msg, process_work_upload)
        elif call.data.startswith("work_detail_"):
            work_id = int(call.data.split("_")[2])
            show_work_details(call, work_id)
        elif call.data.startswith("download_"):
            work_id = int(call.data.split("_")[1])
            download_work(user_id, work_id)
        elif call.data.startswith("change_status_"):
            work_id = int(call.data.split("_")[2])
            change_work_status(call, work_id)
        elif call.data == "teacher_panel":
            bot.edit_message_text("👨‍🏫 Панель учителя:", 
                                chat_id=user_id, 
                                message_id=call.message.message_id, 
                                reply_markup=teacher_panel_markup())
        elif call.data == "dev_panel":
            bot.edit_message_text("👨‍💻 Панель разработчика:", 
                                chat_id=user_id, 
                                message_id=call.message.message_id, 
                                reply_markup=dev_panel_markup())
        elif call.data == "export_data":
            if check_access(user_id, 'разработчик'):
                export_data(user_id)
            else:
                bot.send_message(user_id, "❌ У вас нет прав на экспорт данных.")
        elif call.data == "ban_management":
            if check_access(user_id, 'разработчик'):
                ban_management_menu(call)
            else:
                bot.send_message(user_id, "❌ У вас нет прав на управление блокировками.")
    except Exception as e:
        bot.send_message(user_id, f"❌ Произошла ошибка: {str(e)}")
        print(f"Error in callback handler: {e}")
def teacher_tasks_menu_markup() -> types.InlineKeyboardMarkup:
    markup = types.InlineKeyboardMarkup(row_width=2)
    buttons = [
        types.InlineKeyboardButton("➕ Создать новое задание", callback_data="create_task"),
        types.InlineKeyboardButton("🔒 Закрыть задание", callback_data="close_task_menu"),
        types.InlineKeyboardButton("🔍 Просмотреть ответы", callback_data="check_task_menu"),
        types.InlineKeyboardButton("🗑️ Удалить задание", callback_data="delete_task_menu"),
        types.InlineKeyboardButton("📋 Список всех заданий", callback_data="teacher_task_list"),
        types.InlineKeyboardButton("🔙 Назад", callback_data="teacher_panel")
    ]
    markup.add(*buttons)
    return markup
def teacher_task_actions_markup(task_id: int) -> types.InlineKeyboardMarkup:
    markup = types.InlineKeyboardMarkup(row_width=1)
    buttons = [
        types.InlineKeyboardButton("🔒 Закрыть задание", callback_data=f"close_task_{task_id}"),
        types.InlineKeyboardButton("🔍 Просмотреть ответы", callback_data=f"view_answers_{task_id}")
    ]
    markup.add(*buttons)
    markup.add(types.InlineKeyboardButton("🔙 Назад", callback_data="teacher_works"))
    return markup
@bot.callback_query_handler(func=lambda call: call.data.startswith('close_task_'))
def close_task(call: types.CallbackQuery):
    user_id = call.from_user.id
    if not check_access(user_id, 'учитель'):
        bot.send_message(user_id, "❌ У вас нет прав на закрытие заданий.")
        return
    
    task_id = int(call.data.split('_')[2])
    cursor.execute("UPDATE tasks SET status = 'closed' WHERE task_id = ?", (task_id,))
    conn.commit()
    
    bot.send_message(user_id, f"✅ Задание #{task_id} закрыто.", reply_markup=teacher_tasks_menu_markup())
# Функции для работы с работами
def process_work_upload(message: types.Message):
    user_id = message.from_user.id
    
    if not message.document:
        msg = bot.send_message(user_id, "❌ Пожалуйста, отправьте файл как документ.")
        bot.register_next_step_handler(msg, process_work_upload)
        return
    
    try:
        file_id = message.document.file_id
        file_info = bot.get_file(file_id)
        downloaded_file = bot.download_file(file_info.file_path)
        
        # Создаем уникальное имя файла
        timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
        file_ext = message.document.file_name.split('.')[-1]
        file_name = f"work_{user_id}_{timestamp}.{file_ext}"
        file_path = os.path.join(WORKS_FOLDER, "pending", file_name)
        
        # Сохраняем файл
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        with open(file_path, 'wb') as f:
            f.write(downloaded_file)
        
        # Сохраняем в БД
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO works (user_id, file_path, status) VALUES (?, ?, ?)",
            (user_id, file_path, "Не проверено")
        )
        conn.commit()
        
        bot.send_message(user_id, "✅ Работа успешно загружена!", reply_markup=main_menu_markup(user_id))
    
    except Exception as e:
        bot.send_message(user_id, f"❌ Ошибка при загрузке работы: {str(e)}")

def show_work_details(call: types.CallbackQuery, work_id: int):
    user_id = call.from_user.id
    cursor.execute("""
        SELECT w.work_id, u.full_name, w.file_path, w.status, w.created_at, w.teacher_comment 
        FROM works w
        JOIN users u ON w.user_id = u.user_id
        WHERE w.work_id = ?
    """, (work_id,))
    work = cursor.fetchone()
    if not work:
        bot.send_message(user_id, "❌ Работа не найдена.")
        return
    
    work_id, full_name, file_path, status, created_at, teacher_comment = work
    message = (
        f"📋 Работа #{work_id}\n"
        f"👤 Автор: {full_name}\n"
        f"🔄 Статус: {status}\n"
        f"📅 Дата загрузки: {created_at}\n"
    )
    if teacher_comment:
        message += f"❗️ Комментарий учителя: {teacher_comment}\n"
    
    bot.edit_message_text(
        message,
        chat_id=user_id,
        message_id=call.message.message_id,
        reply_markup=work_detail_markup(work_id, get_user(user_id).role)
    )
def download_work(user_id: int, work_id: int):
    cursor.execute("SELECT file_path FROM works WHERE work_id = ?", (work_id,))
    file_path = cursor.fetchone()[0]
    if not os.path.exists(file_path):
        bot.send_message(user_id, "❌ Файл не найден.")
        return
    
    with open(file_path, 'rb') as f:
        bot.send_document(user_id, f, caption=f"Файл работы #{work_id}")

def change_work_status(call: types.CallbackQuery, work_id: int):
    user_id = call.from_user.id
    if not check_access(user_id, 'учитель'):
        bot.send_message(user_id, "❌ У вас нет прав на изменение статуса работ.")
        return

    cursor.execute("SELECT file_path, status FROM works WHERE work_id = ?", (work_id,))
    work = cursor.fetchone()
    if not work:
        bot.send_message(user_id, "❌ Работа не найдена.")
        return

    current_file_path, current_status = work
    markup = types.InlineKeyboardMarkup(row_width=1)
    statuses = ["Проверено", "Требует доработки", "Удалено"]

    for status in statuses:
        if status != current_status:
            markup.add(types.InlineKeyboardButton(status, callback_data=f"set_status_{work_id}_{status}"))

    markup.add(types.InlineKeyboardButton("🔙 Назад", callback_data=f"work_detail_{work_id}"))
    bot.edit_message_text("Выберите новый статус:", chat_id=user_id, message_id=call.message.message_id, reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith('set_status_'))
def process_status_change(call: types.CallbackQuery):
    user_id = call.from_user.id
    try:
        _, _, work_id, new_status = call.data.split('_', 3)
        work_id = int(work_id)
        
        # Получаем текущий путь к файлу
        cursor.execute("SELECT file_path FROM works WHERE work_id = ?", (work_id,))
        result = cursor.fetchone()
        if not result:
            bot.send_message(user_id, "❌ Работа не найдена.")
            return
        
        current_file_path = result[0]
        
        # Определяем новую папку
        status_folders = {
            'Проверено': 'checked',
            'Требует доработки': 'redo',
            'Удалено': 'deleted'
        }
        
        if new_status not in status_folders:
            bot.send_message(user_id, f"❌ Неверный статус: {new_status}")
            return
        
        # Создаем новую папку если нужно
        new_folder = os.path.join(WORKS_FOLDER, status_folders[new_status])
        os.makedirs(new_folder, exist_ok=True)
        
        # Перемещаем файл
        new_file_name = os.path.basename(current_file_path)
        new_file_path = os.path.join(new_folder, new_file_name)
        os.rename(current_file_path, new_file_path)
        
        # Обновляем статус в базе данных
        cursor.execute(
            "UPDATE works SET status = ?, file_path = ? WHERE work_id = ?",
            (new_status, new_file_path, work_id)
        )
        conn.commit()
        
        bot.send_message(user_id, f"✅ Статус работы #{work_id} изменен на '{new_status}'")
        show_work_details(call, work_id)
        
    except Exception as e:
        bot.send_message(user_id, f"❌ Ошибка при изменении статуса: {str(e)}")
@bot.callback_query_handler(func=lambda call: call.data == 'manage_users')
def manage_users_menu(call: types.CallbackQuery):
    user_id = call.from_user.id
    if not check_access(user_id, 'учитель'):
        bot.send_message(user_id, "❌ У вас нет прав на управление пользователями.")
        return
    
    markup = types.InlineKeyboardMarkup(row_width=1)
    buttons = [
        types.InlineKeyboardButton("👥 Список пользователей", callback_data="user_list"),
        types.InlineKeyboardButton("🎓 Назначить ученика", callback_data="assign_student"),
        types.InlineKeyboardButton("📚 Добавить в класс", callback_data="add_to_class"),
        types.InlineKeyboardButton("🔙 Назад", callback_data="teacher_panel")
    ]
    markup.add(*buttons)
    bot.edit_message_text("👥 Управление пользователями:", chat_id=user_id, message_id=call.message.message_id, reply_markup=markup)
@bot.callback_query_handler(func=lambda call: call.data == 'user_list')
def user_list(call: types.CallbackQuery):
    user_id = call.from_user.id
    if not check_access(user_id, 'учитель'):
        bot.send_message(user_id, "❌ У вас нет прав на просмотр списка пользователей.")
        return
    
    cursor.execute("""
        SELECT user_id, full_name, role, class, is_blocked 
        FROM users WHERE role != 'учитель' AND role != 'разработчик'
    """)
    users = cursor.fetchall()
    
    if not users:
        bot.send_message(user_id, "❌ Нет зарегистрированных пользователей.")
        return
    
    message = "📋 Список пользователей:\n"
    for user in users:
        user_id, full_name, role, class_name, is_blocked = user
        status = "⛔ Заблокирован" if is_blocked else "✅ Активен"
        role = role or "Не назначен"
        class_name = class_name or "Не назначен"
        message += f"- ID: {user_id} | {full_name} | {role} | {class_name} | {status}\n"
    
    bot.send_message(user_id, message, reply_markup=manage_users_markup())

def manage_users_markup() -> types.InlineKeyboardMarkup:
    markup = types.InlineKeyboardMarkup(row_width=1)
    buttons = [
        types.InlineKeyboardButton("👥 Список пользователей", callback_data="user_list"),
        types.InlineKeyboardButton("🎓 Назначить ученика", callback_data="assign_student"),
        types.InlineKeyboardButton("🚫 Заблокировать", callback_data="block_user"),
        types.InlineKeyboardButton("✅ Разблокировать", callback_data="unblock_user"),
        types.InlineKeyboardButton("📚 Добавить в класс", callback_data="add_to_class"),
        types.InlineKeyboardButton("🔙 Назад", callback_data="manage_users")
    ]
    markup.add(*buttons)
    return markup

# Назначение роли ученика
@bot.callback_query_handler(func=lambda call: call.data == 'assign_student')
def assign_student(call: types.CallbackQuery):
    user_id = call.from_user.id
    if not check_access(user_id, 'учитель'):
        bot.send_message(user_id, "❌ У вас нет прав на назначение учеников.")
        return
    
    msg = bot.send_message(user_id, "Введите ID пользователя для назначения учеником:")
    bot.register_next_step_handler(msg, process_assign_student)

def process_assign_student(message: types.Message):
    admin_id = message.from_user.id
    target_id = message.text.strip()
    
    if not target_id.isdigit():
        bot.send_message(admin_id, "❌ Введите корректный ID пользователя.")
        return
    
    target_id = int(target_id)
    
    # Проверяем существование пользователя
    cursor.execute("SELECT user_id FROM users WHERE user_id = ?", (target_id,))
    if not cursor.fetchone():
        bot.send_message(admin_id, "❌ Пользователь с таким ID не найден.")
        return
    
    # Назначаем роль ученика
    cursor.execute("""
        UPDATE users SET role = 'ученик' 
        WHERE user_id = ?
    """, (target_id,))
    conn.commit()
    
    bot.send_message(admin_id, f"✅ Пользователь {target_id} назначен учеником.")
    bot.send_message(target_id, "✅ Вы были назначены учеником учителем.")

# Добавление в класс
@bot.callback_query_handler(func=lambda call: call.data == 'add_to_class')
def add_to_class(call: types.CallbackQuery):
    user_id = call.from_user.id
    if not check_access(user_id, 'учитель'):
        bot.send_message(user_id, "❌ У вас нет прав на добавление в класс.")
        return
    
    msg = bot.send_message(user_id, "Введите ID пользователя и название класса через пробел:")
    bot.register_next_step_handler(msg, process_add_to_class)

def process_add_to_class(message: types.Message):
    admin_id = message.from_user.id
    data = message.text.strip().split()
    
    if len(data) != 2 or not data[0].isdigit():
        bot.send_message(admin_id, "❌ Неверный формат данных. Введите ID и класс через пробел.")
        return
    
    target_id, class_name = data
    target_id = int(target_id)
    
    # Проверяем существование пользователя
    cursor.execute("SELECT user_id FROM users WHERE user_id = ?", (target_id,))
    if not cursor.fetchone():
        bot.send_message(admin_id, "❌ Пользователь с таким ID не найден.")
        return
    
    # Проверяем существование класса
    cursor.execute("SELECT class_name FROM classes WHERE class_name = ?", (class_name,))
    if not cursor.fetchone():
        bot.send_message(admin_id, "❌ Такой класс не существует.")
        return
    
    # Добавляем в класс
    cursor.execute("""
        UPDATE users SET class = ? 
        WHERE user_id = ?
    """, (class_name, target_id))
    conn.commit()
    
    bot.send_message(admin_id, f"✅ Пользователь {target_id} добавлен в класс {class_name}.")
    bot.send_message(target_id, f"✅ Вы были добавлены в класс {class_name} учителем.")
# Функции для работы с репортами
@bot.callback_query_handler(func=lambda call: call.data == 'reports')
def handle_reports(call: types.CallbackQuery):
    user_id = call.from_user.id
    user = get_user(user_id)
    
    if not user:
        return
    
    if user.role == 'ученик':
        msg = bot.send_message(user_id, "📝 Напишите ваш репорт или жалобу:")
        bot.register_next_step_handler(msg, process_student_report)
    else:
        show_reports_list(call)

def process_student_report(message: types.Message):
    user_id = message.from_user.id
    report_text = message.text
    
    if not report_text or len(report_text) < 10:
        msg = bot.send_message(user_id, "❌ Текст репорта слишком короткий. Пожалуйста, напишите подробнее:")
        bot.register_next_step_handler(msg, process_student_report)
        return
    
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO reports (user_id, text, status) VALUES (?, ?, ?)",
        (user_id, report_text, "Не проверено")
    )
    conn.commit()
    
    bot.send_message(user_id, "✅ Ваш репорт отправлен на рассмотрение.", reply_markup=main_menu_markup(user_id))
    
    # Уведомление учителей и разработчика
    notify_about_new_report(user_id, report_text)

def show_reports_list(call: types.CallbackQuery):
    user_id = call.from_user.id
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT r.report_id, r.text, r.status, r.created_at, u.full_name 
        FROM reports r
        JOIN users u ON r.user_id = u.user_id
        ORDER BY r.created_at DESC
    """)
    
    reports = cursor.fetchall()
    
    if not reports:
        bot.edit_message_text("📨 Нет доступных репортов.",
                            chat_id=user_id,
                            message_id=call.message.message_id)
        return
    
    message = "📨 Список репортов:\n\n"
    for report in reports:
        report_id, text, status, created_at, user_name = report
        message += (
            f"🔹 <b>#{report_id}</b> от <i>{user_name}</i>\n"
            f"📅 {created_at}\n"
            f"🔄 Статус: {status}\n\n"
        )
    
    bot.edit_message_text(message,
                         chat_id=user_id,
                         message_id=call.message.message_id,
                         parse_mode='HTML',
                         reply_markup=reports_list_markup(reports))

def reports_list_markup(reports: List[Tuple]) -> types.InlineKeyboardMarkup:
    markup = types.InlineKeyboardMarkup(row_width=2)
    
    for report in reports:
        report_id = report[0]
        markup.add(types.InlineKeyboardButton(
            f"Репорт #{report_id}", 
            callback_data=f"report_detail_{report_id}"
        ))
    
    markup.add(types.InlineKeyboardButton("🔙 Назад", callback_data="main_menu"))
    return markup

# Функции для панели администратора
def ban_management_menu(call: types.CallbackQuery):
    user_id = call.from_user.id
    markup = types.InlineKeyboardMarkup(row_width=2)
    
    buttons = [
        types.InlineKeyboardButton("🚫 Заблокировать", callback_data="ban_user"),
        types.InlineKeyboardButton("✅ Разблокировать", callback_data="unban_user"),
        types.InlineKeyboardButton("📋 Список заблокированных", callback_data="banned_list"),
        types.InlineKeyboardButton("🔙 Назад", callback_data="dev_panel")
    ]
    
    markup.add(*buttons)
    bot.edit_message_text("🚫 Управление блокировками:",
                         chat_id=user_id,
                         message_id=call.message.message_id,
                         reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data == 'ban_user')
def ask_user_id_to_ban(call: types.CallbackQuery):
    user_id = call.from_user.id
    if not check_access(user_id, 'разработчик'):
        bot.send_message(user_id, "❌ У вас нет прав на блокировку пользователей.")
        return
    msg = bot.send_message(user_id, "Введите ID пользователя для блокировки:")
    bot.register_next_step_handler(msg, process_ban_user)

def process_ban_user(message: types.Message):
    user_id = message.from_user.id
    target_id = message.text.strip()
    try:
        target_id = int(target_id)
    except ValueError:
        bot.send_message(user_id, "❌ Неверный формат ID. Пожалуйста, введите число.")
        return

    # Проверяем, существует ли пользователь с таким ID
    cursor.execute("SELECT user_id FROM users WHERE user_id = ?", (target_id,))
    if not cursor.fetchone():
        bot.send_message(user_id, "❌ Пользователь с указанным ID не найден.")
        return

    if target_id == user_id:
        bot.send_message(user_id, "❌ Вы не можете заблокировать себя.")
        return

    # Блокируем пользователя
    cursor.execute("UPDATE users SET is_blocked = 1 WHERE user_id = ?", (target_id,))
    conn.commit()

    # Отправляем уведомление заблокированному пользователю
    bot.send_message(target_id, "⛔ Вы были заблокированы администратором.")

    # Подтверждаем операцию администратору
    bot.send_message(user_id, f"✅ Пользователь {target_id} успешно заблокирован.", 
                     reply_markup=main_menu_markup(user_id))
# Аналогично реализуйте unban_user и banned_list

# Функции для экспорта/импорта данных
def export_data(user_id: int):
    try:
        cursor = conn.cursor()
        
        # Получаем данные из всех таблиц
        cursor.execute("SELECT * FROM users")
        users = cursor.fetchall()
        
        cursor.execute("SELECT * FROM works")
        works = cursor.fetchall()
        
        cursor.execute("SELECT * FROM reports")
        reports = cursor.fetchall()
        
        cursor.execute("SELECT * FROM classes")
        classes = cursor.fetchall()
        
        # Формируем словарь с данными
        data = {
            "users": users,
            "works": works,
            "reports": reports,
            "classes": classes,
            "export_date": get_current_datetime()
        }
        
        # Сохраняем в файл
        export_file = "bot_data_export.json"
        with open(export_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        
        # Отправляем файл пользователю
        with open(export_file, 'rb') as f:
            bot.send_document(user_id, f, caption="Экспорт данных бота")
        
    except Exception as e:
        bot.send_message(user_id, f"❌ Ошибка при экспорте данных: {str(e)}")

@bot.callback_query_handler(func=lambda call: call.data == 'import_data')
def ask_import_file(call: types.CallbackQuery):
    user_id = call.from_user.id
    bot.send_message(user_id, "Пожалуйста, отправьте JSON-файл с данными для импорта:")
    bot.register_next_step_handler(call.message, process_import_data)

def process_import_data(message: types.Message):
    user_id = message.from_user.id
    
    if not message.document:
        bot.send_message(user_id, "❌ Пожалуйста, отправьте файл в формате JSON.")
        return
    
    try:
        file_info = bot.get_file(message.document.file_id)
        downloaded_file = bot.download_file(file_info.file_path)
        
        # Сохраняем временный файл
        import_file = "bot_data_import.json"
        with open(import_file, 'wb') as f:
            f.write(downloaded_file)
        
        # Читаем данные
        with open(import_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # Импортируем данные
        cursor = conn.cursor()
        
        # Очищаем таблицы (осторожно!)
        cursor.execute("DELETE FROM works")
        cursor.execute("DELETE FROM reports")
        cursor.execute("DELETE FROM users WHERE role != 'разработчик'")
        cursor.execute("DELETE FROM classes")
        
        # Вставляем данные
        cursor.executemany("INSERT INTO users VALUES (?, ?, ?, ?, ?, ?, ?)", data.get("users", []))
        cursor.executemany("INSERT INTO works VALUES (?, ?, ?, ?, ?, ?)", data.get("works", []))
        cursor.executemany("INSERT INTO reports VALUES (?, ?, ?, ?, ?, ?)", data.get("reports", []))
        cursor.executemany("INSERT INTO classes VALUES (?, ?)", data.get("classes", []))
        
        conn.commit()
        bot.send_message(user_id, "✅ Данные успешно импортированы!")
    
    except Exception as e:
        bot.send_message(user_id, f"❌ Ошибка при импорте данных: {str(e)}")
@bot.callback_query_handler(func=lambda call: call.data.startswith('view_answers_'))
def view_answers(call: types.CallbackQuery):
    user_id = call.from_user.id
    if not check_access(user_id, 'учитель'):
        bot.send_message(user_id, "❌ У вас нет прав на просмотр ответов.")
        return
    
    task_id = int(call.data.split('_')[2])
    cursor.execute("""
        SELECT u.user_id, u.full_name, a.answer_text, a.file_path, a.status 
        FROM answers a
        JOIN users u ON a.user_id = u.user_id
        WHERE a.task_id = ?
    """, (task_id,))
    answers = cursor.fetchall()
    
    if not answers:
        bot.send_message(user_id, f"❌ Нет ответов на задание #{task_id}.")
        return
    
    message = f"📋 Ответы на задание #{task_id}:\n"
    for answer in answers:
        student_id, full_name, answer_text, file_path, status = answer
        if answer_text:
            answer_info = answer_text[:20] + "..." if len(answer_text) > 20 else answer_text
        elif file_path:
            answer_info = "Файл был отправлен"
        else:
            answer_info = "Нет ответа"
        
        message += (
            f"- Ученик: {full_name}\n"
            f"Ответ: {answer_info}\n"
            f"Статус: {status}\n\n"
        )
    
    bot.send_message(user_id, message, reply_markup=answers_menu_markup(answers))

def answers_menu_markup(answers: List[Tuple]) -> types.InlineKeyboardMarkup:
    markup = types.InlineKeyboardMarkup(row_width=1)
    for answer in answers:
        student_id, _, _, _, _ = answer
        markup.add(types.InlineKeyboardButton(
            f"Ответ от ученика ID{student_id}", 
            callback_data=f"answer_detail_{student_id}"
        ))
    markup.add(types.InlineKeyboardButton("🔙 Назад", callback_data="teacher_works"))
    return markup
@bot.callback_query_handler(func=lambda call: call.data.startswith('answer_detail_'))
def show_answer_detail(call: types.CallbackQuery):
    user_id = call.from_user.id
    student_id = int(call.data.split('_')[2])
    
    cursor.execute("""
        SELECT u.full_name, t.title, a.answer_text, a.file_path, a.status 
        FROM answers a
        JOIN users u ON a.user_id = u.user_id
        JOIN tasks t ON a.task_id = t.task_id
        WHERE a.user_id = ?
    """, (student_id,))
    answer = cursor.fetchone()
    
    if not answer:
        bot.send_message(user_id, "❌ Ответ не найден.")
        return
    
    full_name, task_title, answer_text, file_path, status = answer
    message = (
        f"📋 Ответ от {full_name} на задание '{task_title}':\n"
        f"🔄 Статус: {status}\n"
    )
    if answer_text:
        message += f"📝 Ответ: {answer_text}\n"
    elif file_path:
        message += f"📎 Файл был отправлен.\n"
    
    bot.edit_message_text(
        message,
        chat_id=user_id,
        message_id=call.message.message_id,
        reply_markup=answer_detail_markup(student_id, status)
    )

def answer_detail_markup(student_id: int, current_status: str) -> types.InlineKeyboardMarkup:
    markup = types.InlineKeyboardMarkup(row_width=1)
    statuses = ["Правильно", "Требует доработки", "Удалено"]
    for status in statuses:
        if status != current_status:
            markup.add(types.InlineKeyboardButton(status, callback_data=f"set_answer_status_{student_id}_{status}"))
    markup.add(types.InlineKeyboardButton("🔙 Назад", callback_data="view_student_answers"))
    return markup
@bot.callback_query_handler(func=lambda call: call.data.startswith('set_answer_status_'))
def set_answer_status(call: types.CallbackQuery):
    user_id = call.from_user.id
    if not check_access(user_id, 'учитель'):
        bot.send_message(user_id, "❌ У вас нет прав на изменение статуса ответов.")
        return
    
    _, _, student_id, new_status = call.data.split('_')
    student_id = int(student_id)
    
    cursor.execute("""
        UPDATE answers 
        SET status = ? 
        WHERE user_id = ?
    """, (new_status, student_id))
    conn.commit()
    
    bot.send_message(user_id, f"✅ Статус ответа от ученика ID{student_id} изменен на '{new_status}'.")
# Запуск бота
if __name__ == '__main__':
    print("Бот запущен...")
    bot.infinity_polling()