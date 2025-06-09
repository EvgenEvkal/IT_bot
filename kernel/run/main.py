def check():
    import output.main
    #output.main.main(1 , "Запускаю запуск проверки данных")
    with open("kernel/run/anal.py", 'r', encoding='utf-8') as file:
        exec(file.read())
check()