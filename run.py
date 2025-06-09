import api
import sqlite3
with open("kernel/run/main.py", 'r', encoding='utf-8') as file:
    exec(file.read())