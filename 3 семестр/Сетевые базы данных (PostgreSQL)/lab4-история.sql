\c labs

-- Использовать всё содержимое wc2024.sql
SELECT * FROM shooter_list;
\d+
\d+ shooter_list


-- Первое задание

SELECT sh_id,
       sh_name,
       sh_pos,
       sh_pen,
       SUM(COALESCE(sh_pen, 0)) OVER (PARTITION BY sh_pos) AS pen_by_pos
FROM shooter_list
ORDER BY sh_pos, sh_id;
-- COALESCE здесь только в качестве примера обменника NULL на 0
-- Для SUM это не значительно, но если все sh_pen = NULL,
-- в результате мы получими NULL, а не 0.

ANALYZE;
-- EXPLAIN ANALYZE <запрос>

ALTER TABLE shooter_list ALTER COLUMN sh_pos SET NOT NULL;
\d+ shooter_list

ANALYZE;
-- EXPLAIN ANALYZE <запрос>


-- Второй задание

SELECT sh_id, sh_name, sh_team, sh_pos,
    sh_goals, sh_pen,
    sh_goals - sh_pen AS goals_no_pen,
    ROW_NUMBER() OVER (PARTITION BY sh_team ORDER BY (sh_goals - sh_pen) DESC) AS rn
FROM shooter_list;
-- WHERE rn <= 3; нельзя, используем WITH-обёртку!

-- Sort Key: sh_team, ((sh_goals - sh_pen)) DESC
-- Sort Method: quicksort  Memory: 36kB
-- Сортируем и по партициям, а после, и по ORDER BY.
-- Но вот сам узел WindowAgg указывает, что партициями являются только sh_team!

WITH ranked AS (
    SELECT sh_id, sh_name, sh_team, sh_pos,
           sh_goals, sh_pen,
           sh_goals - sh_pen AS goals_no_pen,
           RANK() OVER (PARTITION BY sh_team ORDER BY (sh_goals - sh_pen) DESC) AS rn
    FROM shooter_list
)
SELECT *
FROM ranked
WHERE rn <= 3
ORDER BY sh_team, rn;
-- ROW_NUMBER заменён на RANK

ANALYZE;
-- EXPLAIN ANALYZE <запрос>


-- Третье задание

SELECT sh_id, sh_name, sh_team, sh_pos, sh_goals,
       (SELECT COUNT(*)
        FROM shooter_list s2
        WHERE s2.sh_team = s1.sh_team
          AND s2.sh_goals > s1.sh_goals) AS players_with_more
FROM shooter_list s1
ORDER BY sh_team, sh_goals DESC, sh_id;

SELECT sh_id, sh_name, sh_team, sh_pos, sh_goals,
       RANK() OVER (
           PARTITION BY sh_team
           ORDER BY sh_goals DESC
       ) - 1 AS players_with_more
FROM shooter_list
ORDER BY sh_team, sh_goals DESC, sh_id;

\pset pager off  -- чтобы можно было их хотябы сравнить без LIMIT 20!

ANALYZE;
-- EXPLAIN ANALYZE <запрос>


-- Четвёртое задание

SELECT sh_id, sh_name, sh_team, sh_min,
       ROUND(AVG(sh_min) OVER (PARTITION BY sh_team), 2) AS avg_min_scorers
FROM shooter_list
WHERE sh_goals > 0
ORDER BY sh_team, sh_id;
-- FROM → WHERE → GROUP BY → HAVING → SELECT (оконные, включая PARTITION BY) → ORDER BY → LIMIT

ANALYZE;
-- EXPLAIN ANALYZE <запрос>


-- Пятое задание

WITH ranked AS (
    SELECT sh_team, sh_min,
           RANK() OVER (PARTITION BY sh_team ORDER BY sh_goals DESC) AS rn
    FROM shooter_list
    WHERE sh_goals > 0  -- отсекаем не бомбардиров (не забивших), чтобы не портить AVG
)
SELECT sh_team,
       ROUND(AVG(sh_min), 2) AS avg_min_top3
FROM ranked
WHERE rn <= 3  -- в задание не сказано, сколько лучших бомбардиров...
GROUP BY sh_team
ORDER BY avg_min_top3 DESC, sh_team;
-- sh_team в ORDER BY - это тай-брейкер, просто ради
-- детерминированности результата при одинаковых avg_min_top3

ANALYZE;
-- EXPLAIN ANALYZE <запрос>
