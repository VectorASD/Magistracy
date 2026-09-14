CREATE DATABASE labs;
\c labs

-- Использовать всё содержимое CREATE.sql
\d+
DROP TABLE IF EXISTS ord, cust, sal;  -- DROP.sql
\d+  -- Did not find any relations.
-- Убедились, что DROP.sql работает
-- Ещё раз использовать всё содержимое CREATE.sql
\d+

-- Использовать всё содержимое INSERT.sql
SELECT * FROM sal;
SELECT * FROM cust;
SELECT * FROM ord;
\d+  -- все таблицы теперь весят по 8 kB (один блок?)

SHOW block_size; -- 8192... да, файлы БД всегда кратны этому
SELECT pg_size_pretty(pg_relation_size('sal'));       --  8 kB, только данные
SELECT pg_size_pretty(pg_total_relation_size('sal')); -- 24 kB, данные + индексы + TOAST
SELECT pg_size_pretty(pg_table_size('sal'));          --  8 kB, данные + TOAST, без индексов
SELECT pg_size_pretty(pg_indexes_size('sal'));        -- 16 kB, только индексы


