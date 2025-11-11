-----------------------------------------------------------
-- 1. Current valid loans for a member
-- View: all loans that are valid right now
-- Conditions: in order to be valid, a loan must have a
-- valid start date and the end date must be null
-----------------------------------------------------------

CREATE OR REPLACE VIEW V_LOANS_CURRENT_VALID AS
SELECT * FROM HAIRBD0028.LOANS
WHERE (VALID_START <= SYSDATE AND VALID_END IS NULL) OR STATUS = 'ACTIVE';

-- Query: all current valid loans for a specific member (p_member_id = 2 and p_member_id = 29)
SELECT * FROM HAIRBD0028.V_LOANS_CURRENT_VALID WHERE MEMBER_ID = :p_member_id;
SELECT * FROM HAIRBD0028.LOANS WHERE MEMBER_ID = 2;
SELECT * FROM HAIRBD0028.LOANS WHERE MEMBER_ID = 29;

-----------------------------------------------------------
-- 2. History of book copy changes
-- View: book copy or book change log
-- Conditions: show previous and new values for shelf location and condition
-- lag is basically looking back one row in the partitioned data
-----------------------------------------------------------

CREATE OR REPLACE VIEW HAIRBD0028.V_BOOK_COPIES_CHANGE_LOG AS
SELECT COPY_ID, BOOK_ID,
       LAG(SHELF_LOCATION) OVER (PARTITION BY COPY_ID ORDER BY TRANSACTION_START) AS PREV_SHELF_LOCATION,
       SHELF_LOCATION AS NEW_SHELF_LOCATION,
       LAG(CONDITION_DESC) OVER (PARTITION BY COPY_ID ORDER BY TRANSACTION_START) AS PREV_CONDITION,
       CONDITION_DESC AS NEW_CONDITION,
       OPERATION_TYPE, TRANSACTION_START, TRANSACTION_END
FROM HAIRBD0028.BOOK_COPIES_HISTORY;

-- Query: book copy change log for a specific copy (COPY_ID = 12)
SELECT * FROM HAIRBD0028.V_BOOK_COPIES_CHANGE_LOG WHERE COPY_ID = :COPY_ID ORDER BY TRANSACTION_START;
-- Query: book copy change log for a specific book (BOOK_ID = 5 or BOOK_ID = 1)
SELECT * FROM HAIRBD0028.V_BOOK_COPIES_CHANGE_LOG WHERE BOOK_ID = :BOOK_ID ORDER BY COPY_ID, TRANSACTION_START;

-----------------------------------------------------------
-- 3. Conflicts between transaction time and valid time (late data entry)
-- View: late-entry detection, with lag in days
-- Conditions:
-- ENTRY_CLASS: compares first transaction time vs VALID_START
-- RETURN_CLASS: compares loan duration vs 20-day policy
-- if not returned yet, it uses SYSDATE to judge current status
-----------------------------------------------------------

-- The first time each loan was recorded
CREATE OR REPLACE VIEW HAIRBD0028.V_LOANS_FIRST_RECORD AS
SELECT LOAN_ID, MIN(TRANSACTION_START) AS FIRST_RECORD_TIME
FROM HAIRBD0028.LOANS_HISTORY GROUP BY LOAN_ID;

-- Classify: ONTIME/LATE/EARLY
CREATE OR REPLACE VIEW HAIRBD0028.V_LOANS_DATA_ENTRY AS
SELECT L.LOAN_ID, L.MEMBER_ID, L.COPY_ID, L.VALID_START, L.VALID_END, T.FIRST_RECORD_TIME,
       -- calculate the number of days between transaction time and valid start
       -- round to 6 decimal places to avoid rounding errors in the calculation of days
       ROUND(CAST(T.FIRST_RECORD_TIME AS DATE) - L.VALID_START, 6) AS DAYS_LAG,
       CASE
           WHEN TRUNC(T.FIRST_RECORD_TIME) = TRUNC(L.VALID_START) THEN 'ONTIME' -- transaction time equals valid start
           WHEN T.FIRST_RECORD_TIME > CAST(L.VALID_START AS TIMESTAMP) THEN 'LATE' -- transaction time is after a valid start
           WHEN T.FIRST_RECORD_TIME < CAST(L.VALID_START AS TIMESTAMP) THEN 'EARLY' -- transaction time is before a valid start
       END AS ENTRY_LOG
FROM HAIRBD0028.LOANS L LEFT JOIN HAIRBD0028.V_LOANS_FIRST_RECORD T ON T.LOAN_ID = L.LOAN_ID;

-- Query: on-time entries (valid start = transaction time)
SELECT * FROM HAIRBD0028.V_LOANS_DATA_ENTRY WHERE ENTRY_LOG = 'ONTIME' ORDER BY DAYS_LAG DESC;
-- Query: late entries (valid start < transaction time)
SELECT * FROM HAIRBD0028.V_LOANS_DATA_ENTRY WHERE ENTRY_LOG = 'LATE' ORDER BY DAYS_LAG DESC;
-- Query: early entries (valid start > transaction time)
SELECT * FROM HAIRBD0028.V_LOANS_DATA_ENTRY WHERE ENTRY_LOG = 'EARLY' ORDER BY DAYS_LAG DESC;

-----------------------------------------------------------
-- 4. Show all loans valid during specific periods
-- View: loans validity periods
-----------------------------------------------------------

CREATE OR REPLACE VIEW V_LOANS_VALIDITY AS
SELECT LOAN_ID, MEMBER_ID, COPY_ID, VALID_START, VALID_END
FROM HAIRBD0028.LOANS;

-- Query: loans valid during a specific period (e.g., 2025-10-15) using WHERE clause for valid time
SELECT * FROM HAIRBD0028.V_LOANS_VALIDITY
WHERE VALID_START <= TO_DATE('2025-10-15 00:00:00', 'YYYY-MM-DD HH24:MI:SS')
AND (VALID_END IS NULL OR VALID_END > TO_DATE('2025-10-15 00:00:00', 'YYYY-MM-DD HH24:MI:SS'))
ORDER BY VALID_START;
-- Query: loans valid during another specific period using AS OF PERIOD FOR VALID_TIME
SELECT LOAN_ID, MEMBER_ID, COPY_ID, VALID_START, VALID_END
FROM HAIRBD0028.LOANS AS OF PERIOD FOR VALID_TIME DATE '2025-10-15' ORDER BY VALID_START;

-----------------------------------------------------------
-- 5. Transaction time querying for loan history
-- View: history records of loans with specific dates
-- Conditions: show all versions that were open on a calendar day or period
-- truncation is bassically setting the time to 00:00:00 for comparison
-----------------------------------------------------------

CREATE OR REPLACE VIEW HAIRBD0028.V_HISTORY_RECORDS AS
SELECT LOAN_ID, VALID_START, VALID_END, STATUS, OPERATION_TYPE, TRANSACTION_START, TRANSACTION_END
FROM HAIRBD0028.LOANS_HISTORY;

-- Query: all versions that were open on a selected period (e.g., 2025-10-27 to 2025-10-29)
-- Using range comparison to filter by transaction time
SELECT * FROM HAIRBD0028.V_HISTORY_RECORDS
WHERE TRANSACTION_START >= TIMESTAMP '2025-10-27 00:00:00' AND TRANSACTION_START <  TIMESTAMP '2025-10-29 00:00:00'
ORDER BY TRANSACTION_START;

-- Query: all versions that were open on a calendar day using TRUNC function (e.g., 2025-10-28)
-- Using TRUNC to filter by date, ignoring time component
SELECT * FROM HAIRBD0028.V_HISTORY_RECORDS
WHERE TRUNC(TRANSACTION_START) = DATE '2025-10-28' ORDER BY TRANSACTION_START;
