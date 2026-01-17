import os
import prk1

# Устанавливаем переменную окружения, чтобы в prk1.py запустился сервер
os.environ["RUN_FLASK_SERVER"] = "1"

# Запускаем сервер
prk1.app.run(debug=True)