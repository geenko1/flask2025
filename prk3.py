import os
import json
from datetime import datetime
from flask import Flask, redirect, url_for, flash, render_template_string
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField
from wtforms.validators import DataRequired, Length
from werkzeug.security import generate_password_hash, check_password_hash

DATA_FILE = "users.json"

app = Flask(__name__)
app.secret_key = "secret_key_for_forms"

def load_users():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

def save_users(users):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(users, f, indent=4, ensure_ascii=False)

users = load_users()


class LoginForm(FlaskForm):
    username = StringField("Логин", validators=[DataRequired()])
    password = PasswordField("Пароль", validators=[DataRequired()])
    submit = SubmitField("Войти")

class RegisterForm(FlaskForm):
    username = StringField("Логин", validators=[DataRequired(), Length(min=4)])
    password = PasswordField("Пароль", validators=[DataRequired(), Length(min=8)])
    submit = SubmitField("Создать пользователя")

def is_bad_password(password):
    return password.isdigit() or password.isalpha()


if "admin" not in users:
    users["admin"] = {
        "password": generate_password_hash("admin123"),
        "registered_at": datetime.now().isoformat(),
        "last_login": None
    }
    save_users(users)


@app.route("/", methods=["GET", "POST"])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        user = users.get(form.username.data)
        if user and check_password_hash(user["password"], form.password.data):
            user["last_login"] = datetime.now().isoformat()
            save_users(users)
            return redirect(url_for("register"))
        flash("Неверный логин или пароль")
    return render_template_string(TEMPLATE_LOGIN, form=form)

@app.route("/register", methods=["GET", "POST"])
def register():
    form = RegisterForm()
    if form.validate_on_submit():
        username = form.username.data

        if username in users:
            flash("Пользователь с таким логином уже существует")
            return redirect(url_for("register"))

        if is_bad_password(form.password.data):
            flash("Пароль слишком простой")
            return redirect(url_for("register"))

        users[username] = {
            "password": generate_password_hash(form.password.data),
            "registered_at": datetime.now().isoformat(),
            "last_login": None
        }
        save_users(users)
        flash("Пользователь успешно создан")
    return render_template_string(TEMPLATE_REGISTER, form=form, users=users)


TEMPLATE_LOGIN = """
<h2>Вход администратора</h2>
<form method="post">
    {{ form.hidden_tag() }}
    {{ form.username.label }} {{ form.username() }}<br>
    {{ form.password.label }} {{ form.password() }}<br>
    {{ form.submit() }}
</form>
{% for msg in get_flashed_messages() %}
<p style="color:red">{{ msg }}</p>
{% endfor %}
"""

TEMPLATE_REGISTER = """
<h2>Регистрация пользователей</h2>
<form method="post">
    {{ form.hidden_tag() }}
    {{ form.username.label }} {{ form.username() }}<br>
    {{ form.password.label }} {{ form.password() }}<br>
    {{ form.submit() }}
</form>

<h3>Существующие пользователи</h3>
<ul>
{% for name, data in users.items() %}
    <li>
        {{ name }} |
        зарегистрирован: {{ data.registered_at }} |
        последний вход: {{ data.last_login }}
    </li>
{% endfor %}
</ul>

{% for msg in get_flashed_messages() %}
<p style="color:red">{{ msg }}</p>
{% endfor %}
"""

if __name__ == "__main__":
    app.run(debug=True)