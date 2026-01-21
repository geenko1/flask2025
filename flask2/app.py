import os
import uuid
import hashlib
import json
from datetime import datetime
from flask import Flask, request, render_template_string, flash, redirect, url_for, send_from_directory

UPLOAD_FOLDER = "uploads"
DATA_FILE = "files_data.json"
ALLOWED_EXTENSIONS = {'.txt', '.pdf', '.png', '.jpg', '.jpeg', '.gif'}  

app = Flask(__name__)
app.secret_key = "supersecretkey"
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER


if os.path.exists(DATA_FILE):
    with open(DATA_FILE, 'r', encoding='utf-8') as f:
        files_data = json.load(f)
else:
    files_data = []


def allowed_file(filename):
    ext = os.path.splitext(filename)[1].lower()
    return ext in ALLOWED_EXTENSIONS


def file_md5(file_path):
    hash_md5 = hashlib.md5()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            hash_md5.update(chunk)
    return hash_md5.hexdigest()


def save_data():
    with open(DATA_FILE, 'w', encoding='utf-8') as f:
        json.dump(files_data, f, indent=4, ensure_ascii=False)


HTML_TEMPLATE = """
<!doctype html>
<html lang="ru">
<head>
    <meta charset="utf-8">
    <title>Загрузка файлов</title>
</head>
<body>
    <h1>Загрузка файлов</h1>

    {% with messages = get_flashed_messages() %}
      {% if messages %}
        <ul style="color: red;">
        {% for msg in messages %}
          <li>{{ msg }}</li>
        {% endfor %}
        </ul>
      {% endif %}
    {% endwith %}

    <form method="post" enctype="multipart/form-data">
        <input type="file" name="file">
        <button type="submit">Загрузить</button>
    </form>

    <h2>Список загруженных файлов</h2>
    <ul>
    {% for file in files %}
        <li>
            UUID: {{ file['uuid'] }} | 
            Оригинальное имя: {{ file['original_name'] }} | 
            Расширение: {{ file['extension'] }} | 
            Дата: {{ file['date'] }} | 
            <a href="{{ url_for('serve_file', path=file['path']) }}" target="_blank">Открыть файл</a>
        </li>
    {% endfor %}
    </ul>
</body>
</html>
"""

@app.route("/", methods=['GET', 'POST'])
def upload_file():
    if request.method == 'POST':
        uploaded_file = request.files.get('file')
        if not uploaded_file:
            flash("Файл не выбран")
            return redirect(request.url)

        original_name = uploaded_file.filename
        ext = os.path.splitext(original_name)[1].lower()

        if not allowed_file(original_name):
            flash(f"Недопустимый тип файла: {ext}")
            return redirect(request.url)


        uuid_name = str(uuid.uuid4()) + ext


        folder_path = os.path.join(app.config['UPLOAD_FOLDER'], uuid_name[:2], uuid_name[2:4])
        os.makedirs(folder_path, exist_ok=True)

        file_path = os.path.join(folder_path, uuid_name)
        uploaded_file.save(file_path)


        md5_hash = file_md5(file_path)
        for f in files_data:
            if f['md5'] == md5_hash:
                os.remove(file_path)
                flash("Файл уже загружен (дубликат)")
                return redirect(request.url)


        file_info = {
            "uuid": uuid_name,
            "original_name": original_name,
            "extension": ext,
            "date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "path": file_path.replace("\\", "/"),
            "md5": md5_hash
        }
        files_data.append(file_info)
        save_data()
        flash("Файл успешно загружен")
        return redirect(url_for('upload_file'))

    return render_template_string(HTML_TEMPLATE, files=files_data)

@app.route('/uploads/<path:path>')
def serve_file(path):
    directory = os.path.dirname(path)
    filename = os.path.basename(path)
    return send_from_directory(directory, filename)

if __name__ == "__main__":
    os.makedirs(UPLOAD_FOLDER, exist_ok=True)
    app.run(debug=True)
