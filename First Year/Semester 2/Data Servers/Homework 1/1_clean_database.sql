-----------------------------------------------------------
-- DROP TABLES: Drop tables if they already exist
-----------------------------------------------------------

DROP TABLE HAIRBD0028.LOANS CASCADE CONSTRAINTS PURGE;
DROP TABLE HAIRBD0028.MEMBERS CASCADE CONSTRAINTS PURGE;
DROP TABLE HAIRBD0028.BOOKS CASCADE CONSTRAINTS PURGE;

-----------------------------------------------------------
-- DROP PROCEDURES: Drop procedures if they already exist
-----------------------------------------------------------

DROP PROCEDURE HAIRBD0028.GET_MIDDLE_PERCENT_BOOKS;
DROP PROCEDURE HAIRBD0028.GET_PROCEDURE_SOURCE;

-----------------------------------------------------------
-- DROP VIEWS: Drop views if they already exist
-----------------------------------------------------------

DROP VIEW HAIRBD0028.VIEW_AVAILABLE_PROCEDURES;