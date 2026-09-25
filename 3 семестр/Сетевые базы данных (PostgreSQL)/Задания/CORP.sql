--  Создание таблицы организаций (иерархия) для учебной БД (PostgreSQL)

CREATE TABLE corp (
    crp_id    INTEGER NOT NULL,
    crp_pid   INTEGER REFERENCES corp(crp_id),
    crp_name  VARCHAR(20),
    crp_worth INTEGER,
    CONSTRAINT corp_pk PRIMARY KEY (crp_id)
);

INSERT INTO corp (crp_id, crp_pid, crp_name, crp_worth) VALUES
    (1, NULL, 'MainFactory',       900),
    (2, NULL, 'ImportantBank',     900),
    (3, 1,    'AutoFactory',       700),
    (4, 1,    'DevFactory',        500),
    (5, 2,    'SubBank',           300),
    (6, 2,    'UnderBank',         500),
    (7, 4,    'SomeCarFactory',    400),
    (8, 4,    'AnotherCarFactory', 400),
    (9, 5,    'MicroBank',         100);

/*
       MainFactory                     ImportantBank
      /           \                   /             \
AutoFactory    DevFactory        UnderBank        SubBank
              /          \                       /
     SomeCarFactory AnotherCarFactory   MicroBank
*/
