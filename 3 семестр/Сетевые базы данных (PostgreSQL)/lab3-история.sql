\c labs

-- Использовать всё содержимое CORP.sql
SELECT * FROM corp;
\d+

WITH RECURSIVE subtree AS (
    -- Якорь: каждый узел является корнем своего поддерева
    SELECT crp_id    AS root_id,
           crp_id    AS node_id,
           crp_worth
    FROM corp

    UNION ALL

    -- Рекурсия: к каждому узлу поддерева добавляем его детей
    SELECT s.root_id,
           c.crp_id,
           c.crp_worth
    FROM subtree s
    JOIN corp c ON c.crp_pid = s.node_id
)
SELECT c.crp_id,
       c.crp_name,
       SUM(s.crp_worth) AS total_worth
FROM subtree s
JOIN corp c ON c.crp_id = s.root_id
GROUP BY c.crp_id, c.crp_name
ORDER BY total_worth DESC;
-- LIMIT 1;

ANALYZE;
-- EXPLAIN ANALYZE <запрос>
