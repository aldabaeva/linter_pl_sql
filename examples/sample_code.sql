-- Хорошая процедура
PROCEDURE update_salary(v_employee_id IN NUMBER) IS
    v_salary NUMBER;
BEGIN
    SELECT salary INTO v_salary FROM employees WHERE employee_id = v_employee_id;
END;

-- Плохая процедура без комментария
PROCEDURE bad_proc IS
    cnt NUMBER; -- короткое имя переменной
    C_MAX_EMPLOYEES CONSTANT NUMBER := 1000; -- правильно названная константа
    c_min_salary CONSTANT NUMBER := 500;     -- НЕПРАВИЛЬНОЕ имя константы
BEGIN
    SELECT * FROM departments; -- использование SELECT *
END;

-- Очень длинная строка — превышает 80 символов
SELECT very_long_column_name_here, another_long_column_name FROM some_long_table_name WHERE condition = 'some_value';

-- Триггер с запрещённым COMMIT
CREATE OR REPLACE TRIGGER log_update
AFTER UPDATE ON employees
BEGIN
    INSERT INTO logs (message) VALUES ('Updated');
    COMMIT; -- Запрещено!
END;