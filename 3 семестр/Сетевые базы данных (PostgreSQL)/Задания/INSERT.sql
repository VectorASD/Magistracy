--	Заполнение таблиц учебной БД (PostgreSQL)

INSERT INTO sal (snum, sname, city, comm) VALUES
    (1001, 'Peel',    'London',    0.12),
    (1002, 'Serres',  'San Jose',  0.13),
    (1004, 'Motica',  'London',    0.11),
    (1007, 'Rifkin',  'Barcelona', 0.15),
    (1003, 'Axelrod', 'New York',  0.10);

INSERT INTO cust (cnum, cname, city, rating, snum) VALUES
    (2001, 'Hoffman',  'London',   100, 1001),
    (2002, 'Giovanni', 'Rome',     200, 1003),
    (2003, 'Liu',      'San Jose', 200, 1002),
    (2004, 'Grass',    'Berlin',   300, 1002),
    (2006, 'Clemens',  'London',   100, 1001),
    (2008, 'Cisneros', 'San Jose', 300, 1007),
    (2007, 'Pereira',  'Rome',     100, 1004);

INSERT INTO ord (onum, amt, odate, cnum, snum) VALUES
    (3001,   18.69, to_date('03.01.2006','dd.mm.yyyy'), 2008, 1007),
    (3003,  767.19, to_date('03.01.2006','dd.mm.yyyy'), 2001, 1001),
    (3002, 1900.10, to_date('03.01.2006','dd.mm.yyyy'), 2007, 1004),
    (3005, 5160.45, to_date('03.01.2006','dd.mm.yyyy'), 2003, 1002),
    (3006, 1098.16, to_date('03.01.2006','dd.mm.yyyy'), 2008, 1007),
    (3009, 1713.23, to_date('04.01.2006','dd.mm.yyyy'), 2002, 1003),
    (3007,   75.75, to_date('04.01.2006','dd.mm.yyyy'), 2004, 1002),
    (3008, 4723.00, to_date('05.01.2006','dd.mm.yyyy'), 2006, 1001),
    (3010, 1309.95, to_date('06.01.2006','dd.mm.yyyy'), 2004, 1002),
    (3011, 9891.88, to_date('06.01.2006','dd.mm.yyyy'), 2006, 1001);

SELECT count(*) FROM sal;   -- 5
SELECT count(*) FROM cust;  -- 7
SELECT count(*) FROM ord;   -- 10

-- COMMIT в PostgreSQL не обязателен (автокоммит включён по умолчанию),
-- но оставлен для совместимости с Oracle-версией скрипта.
COMMIT;  -- there is no transaction in progress
