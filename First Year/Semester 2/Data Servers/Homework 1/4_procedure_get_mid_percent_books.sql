CREATE OR REPLACE PROCEDURE GET_MIDDLE_PERCENT_BOOKS(p_percentage IN NUMBER) IS
BEGIN
    IF p_percentage <= 0 OR p_percentage > 100 THEN
        RAISE_APPLICATION_ERROR(-20001, 'Percentage must be between 0 and 100.');
    END IF;
    FOR cat_rec IN (SELECT DISTINCT CATEGORY FROM HAIRBD0028.BOOKS)
    LOOP
        DBMS_OUTPUT.PUT_LINE('Category: ' || cat_rec.CATEGORY);
        FOR book_rec IN (
            WITH ranked_books AS (SELECT BOOK_ID, TITLE, PRICE, CATEGORY,
                                         ROW_NUMBER() OVER (ORDER BY PRICE) AS rn_asc,
                                         COUNT(*) OVER () AS total_count
                FROM HAIRBD0028.BOOKS WHERE CATEGORY = cat_rec.CATEGORY),
            percentile_limits AS (SELECT total_count,
                                         CEIL((50 - p_percentage / 2) * total_count / 100) AS lower_bound,
                                         FLOOR((50 + p_percentage / 2) * total_count / 100) AS upper_bound
                FROM ranked_books FETCH FIRST 1 ROWS ONLY)
            SELECT b.BOOK_ID, b.TITLE, b.PRICE FROM ranked_books b, percentile_limits pl
            WHERE b.rn_asc BETWEEN pl.lower_bound AND pl.upper_bound
            ORDER BY b.PRICE DESC)
        LOOP
            DBMS_OUTPUT.PUT_LINE('Book: ' || book_rec.BOOK_ID || ' - ' || book_rec.TITLE || ' - Price: ' || book_rec.PRICE);
        END LOOP;
    END LOOP;
END;

BEGIN
    HAIRBD0028.GET_MIDDLE_PERCENT_BOOKS(20);
END;
