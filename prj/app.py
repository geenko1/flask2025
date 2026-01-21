from models import db, User, Brand, Product, CartItem
from flask import Flask, render_template, redirect, url_for, flash, request
from flask_login import (
    LoginManager,
    login_user,
    logout_user,
    login_required,
    current_user,
)
import os
import uuid

BASE_DIR = os.path.abspath(os.path.dirname(__file__))

app = Flask(__name__)
app.config["SECRET_KEY"] = os.urandom(256)
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///" + os.path.join(BASE_DIR, "app.db")
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["UPLOAD_FOLDER"] = os.path.join(BASE_DIR, "static", "uploads")

os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)

db.init_app(app)

login_manager = LoginManager(app)
login_manager.login_view = "login"


from functools import wraps
from flask import flash, redirect, url_for
from flask_login import current_user


def role_required(role):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not current_user.is_authenticated or current_user.role != role:
                flash("Доступ запрещён", "danger")
                return redirect(url_for("index"))
            return f(*args, **kwargs)

        return decorated_function

    return decorator


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


@app.route("/")
def index():
    sort_price = request.args.get("sort_price", "")
    brand_id = request.args.get("brand", "")
    search = request.args.get("search", "").strip()

    # Базовый запрос: только активные продукты
    products_query = Product.query.filter_by(is_active=True)

    # Фильтр по бренду
    if brand_id:
        products_query = products_query.filter_by(brand_id=int(brand_id))

    # Фильтр по названию
    if search:
        products_query = products_query.filter(Product.title.ilike(f"%{search}%"))

    # Сортировка по цене
    if sort_price == "asc":
        products_query = products_query.order_by(Product.price.asc())
    elif sort_price == "desc":
        products_query = products_query.order_by(Product.price.desc())

    products_query = products_query.order_by(
        Product.quantity_available == 0, Product.id
    )
    products = products_query.all()
    brands = Brand.query.all()

    return render_template(
        "index.html",
        products=products,
        brands=brands,
        selected_brand=brand_id,
        sort_price=sort_price,
        search=search,
    )


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]

        if User.query.filter_by(username=username).first():
            flash("Пользователь уже существует", "danger")
            return redirect(url_for("register"))

        user = User(username=username)
        user.set_password(password)
        db.session.add(user)
        db.session.commit()

        flash("Регистрация успешна", "success")
        return redirect(url_for("login"))

    return render_template("register.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]

        user = User.query.filter_by(username=username).first()
        if not user or not user.check_password(password):
            flash("Неверные данные", "danger")
            return redirect(url_for("login"))

        login_user(user)
        return redirect(url_for("index"))

    return render_template("login.html")


@app.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for("index"))


@app.route("/brand/create", methods=["GET", "POST"])
@login_required
@role_required("brand")
def create_brand():
    if request.method == "POST":
        name = request.form["name"]
        description = request.form["description"]
        logo_file = request.files["logo"]

        logo_filename = None
        if logo_file:
            ext = os.path.splitext(logo_file.filename)[1]
            logo_filename = f"{uuid.uuid4()}{ext}"
            logo_file.save(os.path.join(app.config["UPLOAD_FOLDER"], logo_filename))

        # Важно! Передаём owner_id вместо owner
        brand = Brand(
            name=name,
            description=description,
            logo=logo_filename,
            owner_id=current_user.id,  # <-- ключевой момент
        )
        db.session.add(brand)
        db.session.commit()

        flash("Бренд создан", "success")
        return redirect(url_for("brand_page", brand_id=brand.id))

    return render_template("brand_create.html")


@app.route("/brand/<int:brand_id>/edit", methods=["GET", "POST"])
@login_required
@role_required("brand")
def edit_brand(brand_id):
    brand = Brand.query.get_or_404(brand_id)
    if brand.owner != current_user:
        flash("Доступ запрещён", "danger")
        return redirect(url_for("index"))

    if request.method == "POST":
        brand.name = request.form["name"]
        brand.description = request.form["description"]
        logo_file = request.files.get("logo")
        if logo_file:
            ext = os.path.splitext(logo_file.filename)[1]
            logo_filename = f"{uuid.uuid4()}{ext}"
            logo_file.save(os.path.join(app.config["UPLOAD_FOLDER"], logo_filename))
            brand.logo = logo_filename
        db.session.commit()
        flash("Бренд обновлён", "success")
        return redirect(url_for("brand_page", brand_id=brand.id))

    return render_template("brand_edit.html", brand=brand)


@app.route("/brand/<int:brand_id>/delete", methods=["POST"])
@login_required
@role_required("brand")
def delete_brand(brand_id):
    brand = Brand.query.get_or_404(brand_id)
    if brand.owner != current_user:
        flash("Доступ запрещён", "danger")
        return redirect(url_for("index"))

    db.session.delete(brand)
    db.session.commit()
    flash("Бренд удалён", "success")
    return redirect(url_for("my_brands"))


@app.route("/product/create", methods=["GET", "POST"])
@login_required
@role_required("brand")
def create_product():
    # Получаем все бренды пользователя
    user_brands = current_user.brands
    if not user_brands:
        flash("Сначала создайте бренд", "warning")
        return redirect(url_for("create_brand"))

    if request.method == "POST":
        title = request.form["title"]
        description = request.form["description"]
        price = float(request.form["price"])
        brand_id = int(request.form["brand_id"])  # выбранный бренд
        image_file = request.files["image"]

        image_filename = None
        if image_file:
            ext = os.path.splitext(image_file.filename)[1]
            image_filename = f"{uuid.uuid4()}{ext}"
            image_file.save(os.path.join(app.config["UPLOAD_FOLDER"], image_filename))

        # Находим выбранный бренд
        brand = Brand.query.get_or_404(brand_id)

        product = Product(
            title=title,
            description=description,
            price=price,
            image=image_filename,
            brand=brand,
        )
        db.session.add(product)
        db.session.commit()
        flash("Продукт создан", "success")
        return redirect(url_for("brand_page", brand_id=brand.id))

    return render_template("product_create.html", user_brands=user_brands)


@app.route("/product/<int:product_id>/edit", methods=["GET", "POST"])
@login_required
def edit_product(product_id):
    product = Product.query.get_or_404(product_id)

    # Доступ только владельцу бренда или администратору
    if product.brand.owner_id != current_user.id and current_user.role != "admin":
        flash("Доступ запрещён", "danger")
        return redirect(url_for("index"))

    if request.method == "POST":
        product.title = request.form["title"]
        product.description = request.form["description"]
        product.price = float(request.form["price"])
        product.quantity_available = int(request.form["quantity_available"])
        image_file = request.files["image"]

        if image_file:
            ext = os.path.splitext(image_file.filename)[1]
            image_filename = f"{uuid.uuid4()}{ext}"
            image_file.save(os.path.join(app.config["UPLOAD_FOLDER"], image_filename))
            product.image = image_filename

        db.session.commit()
        flash("Продукт обновлён", "success")
        return redirect(url_for("product_page", product_id=product.id))

    return render_template("product_edit.html", product=product)


@app.route("/product/<int:product_id>/delete", methods=["POST"])
@login_required
def delete_product(product_id):
    product = Product.query.get_or_404(product_id)

    if product.brand.owner_id != current_user.id and current_user.role != "admin":
        flash("Доступ запрещён", "danger")
        return redirect(url_for("index"))

    db.session.delete(product)
    db.session.commit()
    flash("Продукт удалён", "success")
    return redirect(url_for("brand_page", brand_id=product.brand.id))


@app.route("/product/<int:product_id>")
def product_page(product_id):
    product = Product.query.get_or_404(product_id)
    return render_template("product_page.html", product=product)


@app.route("/brand/<int:brand_id>")
def brand_page(brand_id):
    brand = Brand.query.get_or_404(brand_id)
    return render_template("brand.html", brand=brand)


@app.route("/admin/users")
@login_required
@role_required("admin")
def admin_users():
    users = User.query.all()
    return render_template("admin_users.html", users=users)


@app.route("/admin/user/<int:user_id>/role", methods=["POST"])
@login_required
@role_required("admin")
def change_user_role(user_id):
    user = User.query.get_or_404(user_id)
    new_role = request.form["role"]
    user.role = new_role
    db.session.commit()
    flash("Роль изменена", "success")
    return redirect(url_for("admin_users"))


@app.route("/admin/brands")
@login_required
@role_required("admin")
def admin_brands():
    brands = Brand.query.all()
    return render_template("admin_brands.html", brands=brands)


@app.route("/admin/brand/edit/<int:brand_id>", methods=["GET", "POST"])
@login_required
@role_required("admin")
def admin_edit_brand(brand_id):
    brand = Brand.query.get_or_404(brand_id)

    if request.method == "POST":
        brand.name = request.form["name"]
        brand.description = request.form["description"]
        logo_file = request.files.get("logo")

        if logo_file:
            ext = os.path.splitext(logo_file.filename)[1]
            logo_filename = f"{uuid.uuid4()}{ext}"
            logo_file.save(os.path.join(app.config["UPLOAD_FOLDER"], logo_filename))
            brand.logo = logo_filename

        db.session.commit()
        flash("Бренд обновлён", "success")
        return redirect(url_for("admin_brands"))

    return render_template("admin_edit_brand.html", brand=brand)


@app.route("/admin/brand/delete/<int:brand_id>", methods=["POST"])
@login_required
@role_required("admin")
def admin_delete_brand(brand_id):
    brand = Brand.query.get_or_404(brand_id)
    db.session.delete(brand)
    db.session.commit()
    flash("Бренд удалён", "success")
    return redirect(url_for("admin_brands"))


@app.route("/admin/product/delete/<int:product_id>", methods=["POST"])
@login_required
@role_required("admin")
def admin_delete_product(product_id):
    product = Product.query.get_or_404(product_id)
    db.session.delete(product)
    db.session.commit()
    flash("Продукт удалён", "success")
    return redirect(url_for("brand_page", brand_id=product.brand_id))


@app.route("/admin/product/<int:product_id>/edit", methods=["GET", "POST"])
@login_required
@role_required("admin")
def admin_edit_product(product_id):
    product = Product.query.get_or_404(product_id)

    if request.method == "POST":
        product.title = request.form["title"]
        product.description = request.form["description"]
        product.price = float(request.form["price"])
        image_file = request.files.get("image")

        if image_file:
            ext = os.path.splitext(image_file.filename)[1]
            image_filename = f"{uuid.uuid4()}{ext}"
            image_file.save(os.path.join(app.config["UPLOAD_FOLDER"], image_filename))
            product.image = image_filename

        db.session.commit()
        flash("Продукт обновлён (админ)", "success")
        return redirect(url_for("brand_page", brand_id=product.brand.id))

    return render_template("product_edit.html", product=product)


@app.route("/my_brands")
@login_required
@role_required("brand")
def my_brands():
    brands = Brand.query.filter_by(owner_id=current_user.id).all()
    return render_template("my_brands.html", brands=brands)


@app.route("/cart/add/<int:product_id>", methods=["POST"])
@login_required
def add_to_cart(product_id):
    if current_user.role != "buyer":
        flash("Только покупатели могут добавлять товары в корзину", "danger")
        return redirect(url_for("index"))

    product = Product.query.get_or_404(product_id)
    quantity = int(request.form.get("quantity", 1))

    if quantity < 1 or quantity > product.quantity_available:
        flash("Неверное количество", "warning")
        return redirect(url_for("product_page", product_id=product.id))

    cart_item = CartItem.query.filter_by(
        user_id=current_user.id, product_id=product.id
    ).first()
    if cart_item:

        new_quantity = cart_item.quantity + quantity
        if new_quantity > product.quantity_available:
            new_quantity = product.quantity_available
        cart_item.quantity = new_quantity
    else:
        cart_item = CartItem(
            user_id=current_user.id, product_id=product.id, quantity=quantity
        )
        db.session.add(cart_item)

    db.session.commit()
    flash(f"Добавлено {quantity} шт. в корзину", "success")
    return redirect(url_for("product_page", product_id=product.id))


@app.route("/cart")
@login_required
def cart_page():
    if current_user.role != "buyer":
        flash("Только покупатели имеют корзину", "danger")
        return redirect(url_for("index"))

    cart_items = CartItem.query.filter_by(user_id=current_user.id).all()
    total = sum(item.product.price * item.quantity for item in cart_items)
    return render_template("cart.html", cart_items=cart_items, total=total)


@app.route("/cart/remove/<int:cart_item_id>", methods=["POST"])
@login_required
def remove_from_cart(cart_item_id):
    cart_item = CartItem.query.get_or_404(cart_item_id)
    if cart_item.user != current_user:
        flash("Доступ запрещён", "danger")
        return redirect(url_for("cart_page"))

    db.session.delete(cart_item)
    db.session.commit()
    flash("Товар удалён из корзины", "success")
    return redirect(url_for("cart_page"))


if __name__ == "__main__":
    with app.app_context():
        db.create_all()
        if not User.query.filter_by(username="admin").first():
            admin = User(username="admin", role="admin")
            admin.set_password("12345")  # пароль админа
            db.session.add(admin)
            db.session.commit()
    app.run(debug=True)
