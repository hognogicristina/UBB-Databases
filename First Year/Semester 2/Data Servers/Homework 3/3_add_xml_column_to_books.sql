ALTER TABLE HAIRBD0028.BOOKS
ADD BOOK_XML XMLTYPE;

UPDATE HAIRBD0028.BOOKS
SET BOOK_XML =
    XMLELEMENT("book",
        XMLFOREST(
            BOOK_ID AS "book_id",
            TITLE AS "title",
            AUTHOR AS "author",
            ISBN AS "isbn",
            PUBLISHED_YEAR AS "published_year",
            PRICE AS "price",
            CATEGORY AS "category"
        )
    )
WHERE BOOK_ID IS NOT NULL;
COMMIT;

-- CLOB is used to store large XML data to text
-- XMLSERIALIZE converts XMLTYPE to characters
SELECT BOOK_ID, XMLSERIALIZE(CONTENT BOOK_XML AS CLOB) AS BOOK_XML_TEXT
FROM HAIRBD0028.BOOKS;

SELECT BOOK_ID, BOOK_XML
FROM HAIRBD0028.BOOKS;
