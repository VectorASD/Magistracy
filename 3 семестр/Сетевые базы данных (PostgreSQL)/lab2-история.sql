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

\t  -- если ранее случайно было \T или \t, иначе шапки и служебные секции таблиц для \d+ отпадут


SHOW jit; -- on
-- SHOW ALL и pg_settings показывают одни и те же GUC-значения, но pg_settings даёт больше колонок и фильтруется как обычная таблица

SELECT name, setting, unit, short_desc
FROM pg_settings
WHERE name LIKE '%\_cost' ESCAPE '\'
ORDER BY name;
/*
          name           | setting | unit |                                             short_desc
-------------------------+---------+------+----------------------------------------------------------------------------------------------------
 cpu_index_tuple_cost    | 0.005   |      | Sets the planner's estimate of the cost of processing each index entry during an index scan.
 cpu_operator_cost       | 0.0025  |      | Sets the planner's estimate of the cost of processing each operator or function call.
 cpu_tuple_cost          | 0.01    |      | Sets the planner's estimate of the cost of processing each tuple (row).
 jit_above_cost          | 100000  |      | Perform JIT compilation if query is more expensive.
 jit_inline_above_cost   | 500000  |      | Perform JIT inlining if query is more expensive.
 jit_optimize_above_cost | 500000  |      | Optimize JIT-compiled functions if query is more expensive.
 parallel_setup_cost     | 1000    |      | Sets the planner's estimate of the cost of starting up worker processes for parallel query.
 parallel_tuple_cost     | 0.1     |      | Sets the planner's estimate of the cost of passing each tuple (row) from worker to leader backend.
 random_page_cost        | 4       |      | Sets the planner's estimate of the cost of a nonsequentially fetched disk page.
 seq_page_cost           | 1       |      | Sets the planner's estimate of the cost of a sequentially fetched disk page.
(10 rows)

 * - seq_page_cost (по умолчанию 1) и random_page_cost (по умолчанию 4)
 *   — стоимости чтения одной страницы последовательно и вразнобой.
 *   Дефолт 4 подобран под типичный HDD, где random-доступ дороже
 *   sequential из-за seek + rotational latency.
 *
 * - На SSD/NVMe latency random и sequential почти одинакова,
 *   поэтому рекомендуют random_page_cost = 1.1–1.5. Иначе планировщик
 *   будет недооценивать индексы и слишком часто выбирать Seq Scan.
 *
 * - cpu_*_cost — стоимость обработки строки/индекса/операции процессором.
 *   Они становятся важны на больших объёмах и аналитических запросах,
 *   где узким местом становится CPU, а не диск.
 *
 * - jit_*_above_cost — это НЕ стоимости, а ПОРОГИ включения JIT.
 *   Если оценочная стоимость плана превышает порог, планировщик
 *   включает JIT-компиляцию. Значения большие (100k+), потому что
 *   JIT сам по себе дорогой и окупается только на тяжёлых запросах.
 *
 * - parallel_setup_cost и parallel_tuple_cost — стоимости запуска
 *   параллельных воркеров и передачи строк от воркера лидеру.
 *
 * При контейнеризации (Docker, WSL, k8s) картина усложняется:
 * данные идут через overlayfs → хостовый диск, или через сетевой
 * volume (EBS, Ceph, NFS). Реальную latency такого «диска» нельзя
 * определить по типу носителя хоста — надо либо мерить, либо
 * ставить значения консервативно.
 *
 * На учебной БД (десятки строк) эти параметры не проявляются:
 * таблица помещается в одну страницу, и Seq Scan всегда дешевле
 * Index Scan. Эффект виден только на больших объёмах.
*/


-- Первое основное задание

SELECT c.cnum, c.cname, c.city, c.rating
FROM cust c
WHERE c.rating = (
    SELECT MAX(c2.rating)
    FROM cust c2
    WHERE c2.city = c.city
)
ORDER BY c.cnum;

SELECT c.cnum, c.cname, c.city, c.rating
FROM cust c
WHERE c.rating >= ALL (
    SELECT c2.rating
    FROM cust c2
    WHERE c2.city = c.city
)
ORDER BY c.cnum;

ANALYZE;
-- EXPLAIN <запрос>  смотрим планы...
-- EXPLAIN ANALYZE <запрос>  тоже самое, но как verbose


-- Второе основное задание

SELECT DISTINCT s.snum, s.sname, s.city
FROM sal s
JOIN cust c
  ON c.city = s.city
 AND c.snum <> s.snum
ORDER BY s.snum;

SELECT s.snum, s.sname, s.city
FROM sal s
WHERE EXISTS (
    SELECT 1
    FROM cust c
    WHERE c.city = s.city
      AND c.snum <> s.snum
)
ORDER BY s.snum;

ANALYZE;
-- EXPLAIN ANALYZE <запрос>


-- Первое контрольное задание

SELECT MIN(s1.snum + 1) AS first_unused
FROM sal s1
WHERE s1.snum > 1002
  AND NOT EXISTS (
      SELECT 1
      FROM sal s2
      WHERE s2.snum = s1.snum + 1
  );

SELECT MIN(s1.snum + 1) AS first_unused
FROM sal s1
LEFT JOIN sal s2
  ON s2.snum = s1.snum + 1
WHERE s1.snum > 1002
  AND s2.snum IS NULL;

ANALYZE;
-- EXPLAIN ANALYZE <запрос>


-- Второе контрольное задание

SELECT s1.snum, s1.sname, s1.city
FROM sal s1
WHERE EXISTS (
    SELECT 1
    FROM sal s2
    WHERE s2.city = s1.city
      AND s2.snum <> s1.snum
);

SELECT DISTINCT s1.snum, s1.sname, s1.city
FROM sal s1
JOIN sal s2
  ON s2.city = s1.city
 AND s2.snum <> s1.snum;

ANALYZE;
-- EXPLAIN ANALYZE <запрос>


-- Третьем контрольное задание

SELECT c1.cnum, c1.cname, c1.city, c1.rating
FROM cust c1
WHERE c1.rating < ALL (
    SELECT c2.rating
    FROM cust c2
    WHERE c2.city <> c1.city
);

SELECT c1.cnum, c1.cname, c1.city, c1.rating
FROM cust c1
WHERE NOT EXISTS (
    SELECT 1
    FROM cust c2
    WHERE c2.city <> c1.city
      AND c2.rating <= c1.rating
);

ANALYZE;
-- EXPLAIN ANALYZE <запрос>
