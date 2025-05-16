-------------------------------------------------------------------------------------------------------------------------------------------
-- Write a query that displays all products in the "Software" category (including all its subcategories) without using the category code or
-- ID directly (the category name must be used instead).
-------------------------------------------------------------------------------------------------------------------------------------------

-- doesn't include the root category
SELECT LEVEL, P.COD, P.DENUMIRE FROM HAIRBD0028.STRUCTURA S
JOIN HAIRBD0028.PRODUSE P ON S.COD = P.COD
START WITH S.CODP IN (SELECT COD FROM HAIRBD0028.PRODUSE WHERE DENUMIRE = 'Software')
CONNECT BY PRIOR S.COD = S.CODP -- parent-child relationship
ORDER BY LEVEL;

-- includes the root category
SELECT LEVEL, P.COD, P.DENUMIRE FROM HAIRBD0028.STRUCTURA S
RIGHT JOIN HAIRBD0028.PRODUSE P ON S.COD = P.COD
START WITH P.DENUMIRE = 'Software'
CONNECT BY PRIOR P.COD = S.CODP -- parent-child relationship
ORDER BY LEVEL;

-------------------------------------------------------------------------------------------------------------------------------------------
-- Write a query that displays all root nodes in the hierarchy, and for each root node, the number of its direct descendants; also, add a
-- column to the products table that stores, in XML format, the information about the direct descendants (code, name, position).
-------------------------------------------------------------------------------------------------------------------------------------------

SELECT P.COD, P.DENUMIRE, COUNT(S.COD) AS NR_DESCENDENTI
FROM HAIRBD0028.PRODUSE P LEFT JOIN HAIRBD0028.STRUCTURA S ON P.COD = S.CODP
WHERE P.COD NOT IN (SELECT DISTINCT COD FROM HAIRBD0028.STRUCTURA) -- root nodes
GROUP BY P.COD, P.DENUMIRE;

ALTER TABLE HAIRBD0028.PRODUSE ADD DESCENDENTI_XML XMLTYPE;

UPDATE HAIRBD0028.PRODUSE P
SET P.DESCENDENTI_XML = (
    SELECT XMLElement("descendenti",
        XMLAgg(
            XMLElement("descendent",
                XMLFOREST(
                    S.COD AS "cod",
                    REGEXP_REPLACE(
                        (SELECT DENUMIRE FROM HAIRBD0028.PRODUSE WHERE COD = S.COD),
                        '[^[:alnum:][:space:]<>&"''-]', ''
                    ) AS "denumire",
                    S.POZITIA AS "pozitia"
                )
            )
        )
    )
    FROM HAIRBD0028.STRUCTURA S
    WHERE S.CODP = P.COD
)
WHERE P.COD IN (SELECT DISTINCT CODP FROM HAIRBD0028.STRUCTURA); -- direct descendants

SELECT COD, DENUMIRE, XMLSERIALIZE(CONTENT DESCENDENTI_XML AS CLOB) AS XML_TEXT FROM HAIRBD0028.PRODUSE
WHERE DESCENDENTI_XML IS NOT NULL;
COMMIT;

-------------------------------------------------------------------------------------------------------------------------------------------
-- Display the first 7 products on each level that are at levels 3 and 4 in the hierarchy and which have at least 2 vowels in their name,
-- ordered alphabetically within each level (the level should also be displayed).
-------------------------------------------------------------------------------------------------------------------------------------------

SELECT NIVEL, COD, DENUMIRE FROM (
    SELECT LEVEL as NIVEL, P.COD, P.DENUMIRE, ROW_NUMBER() OVER (PARTITION BY LEVEL ORDER BY DENUMIRE) AS RNUM
    FROM HAIRBD0028.PRODUSE P LEFT JOIN HAIRBD0028.STRUCTURA S ON P.COD = S.COD
    WHERE REGEXP_COUNT(LOWER(P.DENUMIRE), '[aeiou]') >= 2
    START WITH S.CODP IS NULL
    CONNECT BY PRIOR P.COD = S.CODP
) WHERE NIVEL IN (3, 4) AND RNUM <= 7
ORDER BY NIVEL, DENUMIRE;

-------------------------------------------------------------------------------------------------------------------------------------------
-- Create the necessary scripts (INSERTs, UPDATEs) to modify the structure so that the hierarchy contains at least one cycle. Then highlight 
-- that cycle in the result of a query — for example, by displaying "YES" or another string for the node that causes the cycle.
-------------------------------------------------------------------------------------------------------------------------------------------

INSERT INTO HAIRBD0028.STRUCTURA(COD, CODP) VALUES (1111, 516);
INSERT INTO HAIRBD0028.STRUCTURA (COD, CODP) VALUES (1106, 595);
COMMIT;

SELECT COD, CODP,  SYS_CONNECT_BY_PATH(COD, ' -> ') AS CALE, CASE WHEN CONNECT_BY_ISCYCLE = 1 THEN 'YES' ELSE 'NO' END AS IS_CYCLE
FROM HAIRBD0028.STRUCTURA
START WITH COD IN (1111, 1106)
CONNECT BY NOCYCLE PRIOR COD = CODP; -- to avoid infinite loop

DELETE FROM HAIRBD0028.STRUCTURA WHERE COD = 1111 AND CODP = 516;
DELETE FROM HAIRBD0028.STRUCTURA WHERE COD = 1106 AND CODP = 595;
COMMIT;
