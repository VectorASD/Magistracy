

  CREATE TABLE "CORP" 
   (	"CRP_ID" NUMBER not null, 
	"CRP_PID" NUMBER, 
	"CRP_NAME" VARCHAR2(20 BYTE), 
	"CRP_WORTH" NUMBER
   )  ;
REM INSERTING into CORP
SET DEFINE OFF;
Insert into CORP (CRP_ID,CRP_PID,CRP_NAME,CRP_WORTH) values (1,null,'MainFactory',900);
Insert into CORP (CRP_ID,CRP_PID,CRP_NAME,CRP_WORTH) values (2,null,'ImportantBank',900);
Insert into CORP (CRP_ID,CRP_PID,CRP_NAME,CRP_WORTH) values (3,1,'AutoFactory',700);
Insert into CORP (CRP_ID,CRP_PID,CRP_NAME,CRP_WORTH) values (4,1,'DevFactory',500);
Insert into CORP (CRP_ID,CRP_PID,CRP_NAME,CRP_WORTH) values (5,2,'SubBank',300);
Insert into CORP (CRP_ID,CRP_PID,CRP_NAME,CRP_WORTH) values (6,2,'UnderBank',500);
Insert into CORP (CRP_ID,CRP_PID,CRP_NAME,CRP_WORTH) values (7,4,'SomeCarFactory',400);
Insert into CORP (CRP_ID,CRP_PID,CRP_NAME,CRP_WORTH) values (8,4,'AnotherCarFactory',400);
Insert into CORP (CRP_ID,CRP_PID,CRP_NAME,CRP_WORTH) values (9,5,'MicroBank',100);
--------------------------------------------------------
--  DDL for Index CORP_PK
--------------------------------------------------------

  CREATE UNIQUE INDEX "CORP_PK" ON "CORP" ("CRP_ID");
--------------------------------------------------------
--  Constraints for Table CORP
--------------------------------------------------------

  ALTER TABLE "CORP" ADD CONSTRAINT "CORP_PK" PRIMARY KEY ("CRP_ID");
