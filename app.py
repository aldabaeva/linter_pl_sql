import os
import yaml

from datetime import datetime
from dotenv import load_dotenv
from flask import Flask, render_template, request, redirect, url_for
from flask import session
from flask import send_file
from markupsafe import escape
from functools import wraps

load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv('FLASK_SECRET_KEY', 'fallback_secret_key')
RULES_FILE = 'rules.yaml'
DEFAULT_RULES_FILE = 'default_rules.yaml'

def load_rules():
    with open(RULES_FILE, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)

def save_rules(rules_data):
    with open(RULES_FILE, 'w', encoding='utf-8') as f:
        yaml.dump(rules_data, f, allow_unicode=True, sort_keys=False)

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        action = request.form.get('action')

        if action == 'save':
            rules_data = load_rules()
            for rule_key in rules_data['rules']:
                rules_data['rules'][rule_key]['enabled'] = request.form.get(f'{rule_key}_enabled') == 'on'
                level = request.form.get(f'{rule_key}_level')
                if level in ['warning', 'error', 'info']:
                    rules_data['rules'][rule_key]['level'] = level
                description = request.form.get(f'{rule_key}_description')
                if description:
                    rules_data['rules'][rule_key]['description'] = description
                regex = request.form.get(f'{rule_key}_regex')
                if 'regex' in rules_data['rules'][rule_key]:
                    rules_data['rules'][rule_key]['regex'] = regex or None
            save_rules(rules_data)

        elif action == 'reset':
            with open(DEFAULT_RULES_FILE, 'r', encoding='utf-8') as src:
                default_data = yaml.safe_load(src)
            with open(RULES_FILE, 'w', encoding='utf-8') as dst:
                yaml.dump(default_data, dst, allow_unicode=True, sort_keys=False)

        elif action == 'upload':
            uploaded_file = request.files['yaml_file']
            if uploaded_file:
                try:
                    data = yaml.safe_load(uploaded_file.stream)
                    with open(RULES_FILE, 'w', encoding='utf-8') as f:
                        yaml.dump(data, f, allow_unicode=True, sort_keys=False)
                except Exception as e:
                    print("Ошибка при загрузке YAML:", e)

        return redirect(url_for('index'))

    rules = load_rules()
    return render_template('index.html', rules=rules)

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'username' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

@app.route('/login', methods=['GET', 'POST'])
def login():
    error = None
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        try:
            # Открываем файл users.yaml с указанием кодировки UTF-8
            with open('users.yaml', encoding='utf-8') as f:
                users_data = yaml.safe_load(f)
                print("Содержимое users.yaml:", users_data)  # Отладочная информация
                users = users_data.get('users', {})
            
            if not users:
                error = "Файл users.yaml не содержит пользователей."
                return render_template('login.html', error=error)
            
            if username in users and users[username]['password'] == password:
                session['username'] = username
                return redirect(url_for('index'))
            else:
                error = 'Неверный логин или пароль'
        except FileNotFoundError:
            error = "Файл users.yaml не найден."
        except yaml.YAMLError as e:
            error = f"Ошибка разбора YAML: {e}"
        except Exception as e:
            print("Неизвестная ошибка:", e)  # Отладочная информация
            error = 'Произошла ошибка при проверке учетных данных'
    
    return render_template('login.html', error=error)

@app.route('/logout')
def logout():
    session.pop('username', None)
    return redirect(url_for('login'))

# Импорт / Экспорт
@app.route('/export')
@login_required
def export_yaml():
    return send_file(RULES_FILE, as_attachment=True)

@app.route('/preview')
@login_required
def preview():
    with open('examples/sample_code.sql') as f:
        code = f.read()
    with open('examples/sample_output.md') as f:
        output = f.read()
    return render_template('preview.html', code=code, output=output)

@app.route('/check')
def check_file():
    """Страница проверки файла доступна без авторизации"""
    return render_template('check_file.html')

@app.route('/process_check', methods=['POST'])
def process_check():
    """Обработка проверки файла доступна без авторизации"""
    if 'sql_file' not in request.files:
        return redirect(url_for('check_file'))
    
    file = request.files['sql_file']
    if file.filename == '':
        return redirect(url_for('check_file'))
    
    # Сохраняем временный файл
    temp_path = os.path.join('static', 'temp', file.filename)
    os.makedirs(os.path.dirname(temp_path), exist_ok=True)
    file.save(temp_path)
    
    # Запускаем линтер
    rules = load_rules()
    from linter import lint_file    

    # Генерируем имя файла отчета с меткой даты и времени
    now = datetime.now()
    timestamp = now.strftime("%Y-%m-%d_%H-%M-%S")
    report_filename = f'report_{timestamp}.html'
    report_path = os.path.join('static', 'temp', report_filename).replace('\\', '/')
    
    # Запускаем линтер и генерируем отчет
    lint_file(temp_path, rules['rules'], report_path) 
    
    # Возвращаем ссылку на отчет
    return render_template('check_file.html', report_path=report_path)

@app.route('/manage_rules', methods=['GET', 'POST'])
@login_required
def manage_rules():
    if request.method == 'POST':
        action = request.form.get('action')

        if action == 'save':
            rules_data = load_rules()
            for rule_key in rules_data['rules']:
                rules_data['rules'][rule_key]['enabled'] = request.form.get(f'{rule_key}_enabled') == 'on'
                level = request.form.get(f'{rule_key}_level')
                if level in ['warning', 'error', 'info']:
                    rules_data['rules'][rule_key]['level'] = level
                description = request.form.get(f'{rule_key}_description')
                if description:
                    rules_data['rules'][rule_key]['description'] = description
                regex = request.form.get(f'{rule_key}_regex')
                if 'regex' in rules_data['rules'][rule_key]:
                    rules_data['rules'][rule_key]['regex'] = regex or None
            save_rules(rules_data)

        elif action == 'reset':
            with open(DEFAULT_RULES_FILE, 'r', encoding='utf-8') as src:
                default_data = yaml.safe_load(src)
            with open(RULES_FILE, 'w', encoding='utf-8') as dst:
                yaml.dump(default_data, dst, allow_unicode=True, sort_keys=False)

        elif action == 'upload':
            uploaded_file = request.files['yaml_file']
            if uploaded_file:
                try:
                    data = yaml.safe_load(uploaded_file.stream)
                    with open(RULES_FILE, 'w', encoding='utf-8') as f:
                        yaml.dump(data, f, allow_unicode=True, sort_keys=False)
                except Exception as e:
                    print("Ошибка при загрузке YAML:", e)

        return redirect(url_for('manage_rules'))

    rules = load_rules()
    return render_template('manage_rules.html', rules=rules)

if __name__ == '__main__':
    app.run(debug=True)