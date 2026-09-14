--  Построение таблиц для учебной базы данных (PostgreSQL)

CREATE TABLE sal (
    snum  INTEGER      NOT NULL,
    sname VARCHAR(10)  NOT NULL,
    city  VARCHAR(10)  NOT NULL,
    comm  NUMERIC(7,2) NOT NULL,
    CONSTRAINT sal_pk_snum PRIMARY KEY (snum)
);

CREATE TABLE cust (
    cnum   INTEGER     NOT NULL,
    cname  VARCHAR(10) NOT NULL,
    city   VARCHAR(10) NOT NULL,
    rating INTEGER     NOT NULL,
    snum   INTEGER,
    CONSTRAINT cust_pk_cnum PRIMARY KEY (cnum),
    CONSTRAINT cust_fk_snum FOREIGN KEY (snum)
        REFERENCES sal(snum)
);

CREATE TABLE ord (
    onum  INTEGER      NOT NULL,
    amt   NUMERIC(7,2) NOT NULL,
    odate DATE         NOT NULL,
    cnum  INTEGER,
    snum  INTEGER,
    CONSTRAINT ord_pk_onum PRIMARY KEY (onum),
    CONSTRAINT ord_fk_cnum FOREIGN KEY (cnum)
        REFERENCES cust(cnum),
    CONSTRAINT ord_fk_snum FOREIGN KEY (snum)
        REFERENCES sal(snum)
);
