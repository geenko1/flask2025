from flask import Flask, redirect, url_for, request, render_template_string, flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, login_user, login_required, logout_user, UserMixin, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime

app = Flask(__name__)
app.config["SECRET_KEY"] = "secret"
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///blog.db"
db = SQLAlchemy(app)

login_manager = LoginManager(app)
login_manager.login_view = "login"


class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)

class Post(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    content = db.Column(db.Text, nullable=False)
    is_private = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    author_id = db.Column(db.Integer, db.ForeignKey("user.id"))

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


@app.route("/")
def index():
    if current_user.is_authenticated:
        posts = Post.query.order_by(Post.created_at.desc()).all()
    else:
        posts = Post.query.filter_by(is_private=False).order_by(Post.created_at.desc()).all()
    return render_template_string(TEMPLATE_INDEX, posts=posts)

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        user = User.query.filter_by(username=request.form["username"]).first()
        if user and check_password_hash(user.password, request.form["password"]):
            login_user(user)
            return redirect(url_for("index"))
        flash("Неверный логин или пароль")
    return render_template_string(TEMPLATE_LOGIN)

@app.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for("index"))

@app.route("/post/new", methods=["GET", "POST"])
@login_required
def create_post():
    if request.method == "POST":
        post = Post(
            title=request.form["title"],
            content=request.form["content"],
            is_private=bool(request.form.get("is_private")),
            author_id=current_user.id
        )
        db.session.add(post)
        db.session.commit()
        return redirect(url_for("index"))
    return render_template_string(TEMPLATE_POST)

@app.route("/post/edit/<int:id>", methods=["GET", "POST"])
@login_required
def edit_post(id):
    post = Post.query.get_or_404(id)
    if request.method == "POST":
        post.title = request.form["title"]
        post.content = request.form["content"]
        post.is_private = bool(request.form.get("is_private"))
        db.session.commit()
        return redirect(url_for("index"))
    return render_template_string(TEMPLATE_POST, post=post)


TEMPLATE_INDEX = """
<h1>Блог</h1>

{% if current_user.is_authenticated %}
<p>Вы вошли как {{ current_user.username }} |
<a href="/logout">Выйти</a> |
<a href="/post/new">Новый пост</a></p>
{% else %}
<a href="/login">Войти</a>
{% endif %}

<hr>

{% for post in posts %}
<h3>{{ post.title }}</h3>
<p>{{ post.content }}</p>
{% if post.is_private %}
<em>Приватный пост</em>
{% endif %}
{% if current_user.is_authenticated %}
<p><a href="/post/edit/{{ post.id }}">Редактировать</a></p>
{% endif %}
<hr>
{% endfor %}
"""

TEMPLATE_LOGIN = """
<h2>Вход</h2>
<form method="post">
    <input name="username" placeholder="Логин"><br>
    <input name="password" type="password" placeholder="Пароль"><br>
    <button>Войти</button>
</form>
{% for msg in get_flashed_messages() %}
<p style="color:red">{{ msg }}</p>
{% endfor %}
"""

TEMPLATE_POST = """
<h2>Пост</h2>
<form method="post">
    <input name="title" placeholder="Заголовок" value="{{ post.title if post else '' }}"><br>
    <textarea name="content">{{ post.content if post else '' }}</textarea><br>
    <label>
        <input type="checkbox" name="is_private" {% if post and post.is_private %}checked{% endif %}>
        Приватный пост
    </label><br>
    <button>Сохранить</button>
</form>
"""


if __name__ == "__main__":
    with app.app_context():
        db.create_all()


        if not User.query.filter_by(username="admin").first():
            user = User(
                username="admin",
                password=generate_password_hash("admin")
            )
            db.session.add(user)
        if not User.query.filter_by(username="user1").first():
            user1 = User(
                username="user1",
                password=generate_password_hash("user123")
            )
            db.session.add(user1)
            db.session.commit()

    app.run(debug=True)