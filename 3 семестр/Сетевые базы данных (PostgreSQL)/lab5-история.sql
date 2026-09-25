CREATE OR REPLACE PROCEDURE print_sal_v1(
    p_sname text,
    p_city  text
)
LANGUAGE plpgsql AS $$
DECLARE
    v_rec record;
BEGIN
    FOR v_rec IN
        EXECUTE format(
            'SELECT snum, sname, city, comm
             FROM sal
             WHERE sname = %L AND city = %L',
            p_sname, p_city
        )
    LOOP
        RAISE NOTICE 'snum=%, sname=%, city=%, comm=%',
            v_rec.snum, v_rec.sname, v_rec.city, v_rec.comm;
    END LOOP;
END;
$$;

\pset pager off
\df+

SELECT * FROM sal;
CALL print_sal_v1('Peel', 'London');  -- args
CALL print_sal_v1('Peel', 'San Jose');  -- нет такой записи
CALL print_sal_v1(p_city => 'London', p_sname => 'Peel');  -- kwargs
-- Точно та же логика, что и в python, только нет явного доступа к args и kwargs из процедур и функций
-- Аналог *args – VARIADIC, например: func(VARIADIC nums int[]).
-- Аналога **kwargs нет: PostgreSQL требует, чтобы имена соответствовали объявленным параметрам.


CREATE OR REPLACE PROCEDURE print_sal_v2(
    p_sname text DEFAULT NULL,
    p_city  text DEFAULT NULL
)
LANGUAGE plpgsql AS $$
DECLARE
    v_where text;
    v_sql   text;
    v_rec   record;
BEGIN
    -- %L - аналог repr (с кавычками)
    -- %s - аналог str  (без кавычек)

    -- Сборка WHERE из кусочков (AND - фиксированный)
    v_where := concat_ws(
        ' AND ',
        CASE WHEN p_sname IS NOT NULL THEN format('sname = %L', p_sname) END,
        CASE WHEN p_city  IS NOT NULL THEN format('city  = %L', p_city)  END
    );

    -- Полный SQL
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

CALL print_sal_v2('Peel', 'London');
CALL print_sal_v2('Peel');
CALL print_sal_v2(p_city => 'London');
CALL print_sal_v2();  -- SELECT * FROM sal;


CREATE OR REPLACE PROCEDURE print_sal_v3(
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
    p_op := upper(p_op);

    IF p_op NOT IN ('AND', 'OR') THEN
        RAISE EXCEPTION 'Оператор должен быть AND или OR, получено: %', p_op;
    END IF;

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


CALL print_sal_v3('Peel', 'San Jose', 'OR');
CALL print_sal_v3('Peel', 'San Jose', 'oR');  -- проверка upper, исключения нет
CALL print_sal_v3('Peel', 'San Jose', 'xor');  -- исключение есть
\set ON_ERROR_STOP off  -- похоже на аналог "set -e" в bash, но это на REPL (psql), а не процедуры
CALL print_sal_v3('Peel', 'San Jose', 'xor');  -- ничего не поменялось
\set ON_ERROR_STOP on
CALL print_sal_v3('Peel', 'San Jose', 'xor');  -- опять ничего не поменялось
