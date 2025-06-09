import api as api
import kernel.errors.main
import output.main
if api.LOCATE_KERNEL == "":
    #output.main.main(0 , kernel.errors.main.LOCATE_KERNEL_ERROR)
    print(kernel.errors.main.LOCATE_KERNEL_ERROR)
elif api.VERSION == "":
    #output.main.main(0 , kernel.errors.main.TOKEN_ERROR)
    print(kernel.errors.main.TOKEN_ERROR)
elif api.LOCATE_START == "":
    #output.main.main(0 , kernel.errors.main.LOCATE_START_ERROR)
    print(kernel.errors.main.LOCATE_START_ERROR)
else:
    #output.main.main(1 , "Проверка завершена! Запускаю ядро бота!")
    with open('kernel/main.py', 'r', encoding='utf-8') as file:
        exec(file.read())