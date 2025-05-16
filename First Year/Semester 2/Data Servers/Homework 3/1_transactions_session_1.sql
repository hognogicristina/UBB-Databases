-- Nonrepeatable Read
-- Initial data read
-- Session 1
SELECT * FROM HAIRBD0028.BOOKS WHERE ISBN = '9781538724736';

-- Second read, after the modification from Session 2
SELECT * FROM HAIRBD0028.BOOKS WHERE ISBN = '9781538724736';

-- Phantom Read
-- Initial data read
-- Session 1
SELECT * FROM HAIRBD0028.BOOKS WHERE PUBLISHED_YEAR = 2023;

-- Second read, after the modification from Session 2
SELECT * FROM HAIRBD0028.BOOKS WHERE PUBLISHED_YEAR = 2023;
COMMIT;