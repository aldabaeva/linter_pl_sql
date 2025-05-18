import re
import sys
import yaml
from datetime import datetime

# --- Загрузка правил ---
def load_rules(file_path='rules.yaml'):
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f).get('rules', {})
    except FileNotFoundError:
        print(f"[ERROR] Файл правил {file_path} не найден.")
        sys.exit(1)

# --- Проверки ---
def check_line_length(config, line_number, line):
    if len(line.rstrip('\n')) > config.get('max_length', 80):
        return {
            'type': config['level'],
            'message': f"Длина строки превышает {config['max_length']} символов",
            'line': line_number
        }

def check_variable_naming(config, line_number, line):
    regex = config.get('regex')
    if not regex:
        return
    matches = re.findall(regex, line)
    for var_name, _ in matches:
        if not any(var_name.lower().startswith(prefix) for prefix in config.get("prefixes", [])):
            return {
                'type': config['level'],
                'message': f"Переменная '{var_name}' не соответствует соглашению об именовании",
                'line': line_number
            }

def check_constant_naming(config, line_number, line):
    regex = config.get('regex')
    if not regex:
        return
    matches = re.findall(r'\bC_[A-Za-z0-9_]+\b', line)
    for const_name in matches:
        if not re.match(regex, const_name):
            return {
                'type': config['level'],
                'message': f"Константа '{const_name}' не соответствует соглашению об именовании",
                'line': line_number
            }

def check_procedure_comments(config, lines, i):
    if i > 0 and re.search(r'\bPROCEDURE\b', lines[i], re.IGNORECASE):
        prev_line = lines[i - 1].strip()
        if not prev_line.startswith('--') and not prev_line.startswith('/*'):
            return {
                'type': config['level'],
                'message': f"Процедура объявлена без комментария выше",
                'line': i + 1
            }

def check_select_star(config, line_number, line):
    regex = config.get('regex')
    flags = re.IGNORECASE if config.get('ignore_case', False) else 0
    if regex and re.search(regex, line, flags):
        return {
            'type': config['level'],
            'message': f"Использование SELECT * — плохая практика",
            'line': line_number
        }

def check_commit_in_trigger(config, lines, i):
    trigger_found = False
    for j, line in enumerate(lines):
        if re.search(r'\bTRIGGER\b', line, re.IGNORECASE):
            trigger_found = True
        elif trigger_found and re.search(r'\b(COMMIT|ROLLBACK)\b', line, re.IGNORECASE):
            return {
                'type': config['level'],
                'message': f"Использование COMMIT/ROLLBACK внутри триггера — запрещено",
                'line': j + 1
            }
            trigger_found = False

def check_comment_min_length(config, line_number, line):
    line = line.strip()
    if line.startswith('--'):
        comment_text = line[2:].strip()
        if len(comment_text) < 2:
            return {
                'type': config['level'],
                'message': f"Комментарий слишком короткий: '{comment_text}'",
                'line': line_number
            }
    elif line.startswith('/*') and line.endswith('*/'):
        comment_text = line[2:-2].strip()
        if len(comment_text) < 2:
            return {
                'type': config['level'],
                'message': f"Комментарий слишком короткий: '{comment_text}'",
                'line': line_number
            }

# --- Маппинг функций ---
CHECK_FUNCTIONS = {
    'check_line_length': check_line_length,
    'check_variable_naming': check_variable_naming,
    'check_constant_naming': check_constant_naming,
    'check_procedure_comments': check_procedure_comments,
    'check_select_star': check_select_star,
    'check_commit_in_trigger': check_commit_in_trigger,
    'check_comment_min_length': check_comment_min_length,
}

# --- Логика линтера ---
def lint_file(filename, rules, report_path=None):
    MULTILINE_CHECKS = {'check_procedure_comments', 'check_commit_in_trigger'}
    issues = []
    try:
        with open(filename, 'r', encoding='utf-8') as f:
            lines = f.readlines()

        print(f"Проверяю файл: {filename}")
        for i, line in enumerate(lines, start=1):
            for rule_key, config in rules.items():
                if not config.get('enabled', True):
                    continue
                func_name = config.get('function')
                if func_name in CHECK_FUNCTIONS:
                    func = CHECK_FUNCTIONS[func_name]
                    if func_name in MULTILINE_CHECKS:
                        result = func(config, lines, i - 1)
                    else:
                        result = func(config, i, line)
                    if result:
                        result['rule'] = config['description']
                        issues.append(result)

    except FileNotFoundError:
        print(f"[ERROR] Файл {filename} не найден.")
        sys.exit(1)

    # Генерация HTML-отчета с использованием report_path
    generate_html_report(issues, filename, report_path or "report.html")
    print(f"\n[INFO] Сгенерирован отчет: {report_path or 'report.html'}")

# --- Генерация HTML ---
def generate_html_report(issues, file_name, report_path="report.html"):
    html = """<html>
<head>
    <title>PL/SQL Lint Report</title>
    <style>
        body {{ font-family: Arial, sans-serif; padding: 20px; background: #f9f9f9; color: #333; }}
        h1 {{ color: #333; }}
        table {{ border-collapse: collapse; width: 100%; margin-top: 20px; }}
        th, td {{ border: 1px solid #ccc; padding: 8px; text-align: left; }}
        .warning {{ background-color: #fff3cd; }}
        .error {{ background-color: #f8d7da; color: #721c24; }}
        input[type="text"] {{ margin-bottom: 10px; padding: 5px; width: 100%; box-sizing: border-box; }}
    </style>
    <script>
        function filterTable() {{
            const filters = {{
                line: document.getElementById('filter-line').value.toLowerCase(),
                type: document.getElementById('filter-type').value.toLowerCase(),
                rule: document.getElementById('filter-rule').value.toLowerCase(),
                message: document.getElementById('filter-message').value.toLowerCase()
            }};

            const rows = document.querySelectorAll("table tbody tr");
            rows.forEach(row => {{
                const line = row.children[0].textContent.toLowerCase();
                const type = row.children[1].textContent.toLowerCase();
                const rule = row.children[2].textContent.toLowerCase();
                const message = row.children[3].textContent.toLowerCase();

                const matches = 
                    line.includes(filters.line) &&
                    type.includes(filters.type) &&
                    rule.includes(filters.rule) &&
                    message.includes(filters.message);

                row.style.display = matches ? "" : "none";
            }});
        }}
    </script>
</head>
<body>
    <h1>PL/SQL Lint Report — {}</h1>
    <p>Дата: {}</p>

    <!-- Фильтры -->
    <label for="filter-line">Фильтр по строке:</label>
    <input type="text" id="filter-line" onkeyup="filterTable()" placeholder="Поиск по строке...">

    <label for="filter-type">Фильтр по типу:</label>
    <input type="text" id="filter-type" onkeyup="filterTable()" placeholder="Поиск по типу...">

    <label for="filter-rule">Фильтр по правилу:</label>
    <input type="text" id="filter-rule" onkeyup="filterTable()" placeholder="Поиск по правилу...">

    <label for="filter-message">Фильтр по сообщению:</label>
    <input type="text" id="filter-message" onkeyup="filterTable()" placeholder="Поиск по сообщению...">

    <!-- Таблица -->
    <table>
        <thead>
            <tr>
                <th>Строка</th>
                <th>Тип</th>
                <th>Правило</th>
                <th>Сообщение</th>
            </tr>
        </thead>
        <tbody>
""".format(file_name, datetime.now().strftime("%Y-%m-%d %H:%M:%S"))

    for issue in issues:
        row_class = 'warning' if issue['type'] == 'warning' else 'error'
        html += f"""
<tr class="{row_class}">
    <td>{issue['line']}</td>
    <td>{issue['type'].upper()}</td>
    <td>{issue['rule']}</td>
    <td>{issue['message']}</td>
</tr>
"""

    html += """
        </tbody>
    </table>
</body>
</html>
"""

    # Сохранение отчета в указанный путь
    with open(report_path, "w", encoding="utf-8") as f:
        f.write(html)

if __name__ == '__main__':
    if len(sys.argv) != 2:
        print("Использование: python linter.py <имя_файла>")
        sys.exit(1)

    rules = load_rules()
    lint_file(sys.argv[1], rules)