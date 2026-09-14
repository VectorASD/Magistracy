--	Удаление таблиц учебной БД (PostgreSQL)

DROP TABLE IF EXISTS ord, cust, sal;

-- Важно: порядок здесь исходит из освобождения FK!
-- Хотя, в случае postgres, это не важно...
