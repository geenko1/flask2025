from flask import Flask, request, render_template_string
import random
import unittest
import os

app = Flask(__name__)

# Генерация
def generate_numbers():
    numbers = set()
    while len(numbers) < 1000:

        num = '89' + ''.join(str(random.randint(0, 9)) for _ in range(9))
        numbers.add(num)
    return sorted(numbers)

PHONE_NUMBERS = generate_numbers()

INDEX_TEMPLATE = """
<!doctype html>
<html lang="ru">
<head>
    <meta charset="utf-8">
    <title>Список номеров</title>
</head>
<body>
    <h1>Список телефонных номеров</h1>

    <form action="/number/" method="get">
        <input type="text" name="number" placeholder="Введите номер или строку">
        <button type="submit">Показать</button>
    </form>

    <ul>
        {% for num in numbers %}
            <li>
                <a href="/number/?number={{ num }}">{{ num }}</a>
            </li>
        {% endfor %}
    </ul>
</body>
</html>
"""

NUMBER_TEMPLATE = """
<!doctype html>
<html lang="ru">
<head>
    <meta charset="utf-8">
    <title>Информация о номере</title>
</head>
<body>
    <h1>Подробная информация</h1>
    <p>Введённое значение:</p>
    <strong>{{ number }}</strong>

    <p><a href="/">Вернуться к списку</a></p>
</body>
</html>
"""

@app.route("/")
def index():
    return render_template_string(INDEX_TEMPLATE, numbers=PHONE_NUMBERS)

@app.route("/number/")
def number_info():
    number = request.args.get("number", "")
    return render_template_string(NUMBER_TEMPLATE, number=number)


class FlaskAppTestCase(unittest.TestCase):
    def setUp(self):
        self.client = app.test_client()
        self.client.testing = True

    def test_index_page_loads(self):
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        text = response.get_data(as_text=True)
        self.assertIn("Список телефонных номеров", text)

    def test_number_page_with_number(self):
        response = self.client.get("/number/?number=1234567890")
        self.assertEqual(response.status_code, 200)
        text = response.get_data(as_text=True)
        self.assertIn("1234567890", text)

    def test_number_page_with_string(self):
        response = self.client.get("/number/?number=test-string")
        self.assertEqual(response.status_code, 200)
        text = response.get_data(as_text=True)
        self.assertIn("test-string", text)

    def test_number_page_empty(self):
        response = self.client.get("/number/")
        self.assertEqual(response.status_code, 200)
        text = response.get_data(as_text=True)
        self.assertIn("Подробная информация", text)


if __name__ == "__main__":
    app.run(debug=True)
