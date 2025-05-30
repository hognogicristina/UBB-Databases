-----------------------------------------------------------
-- TABLE: BOOKS
-----------------------------------------------------------

CREATE TABLE HAIRBD0028.BOOKS
(
    BOOK_ID        NUMBER GENERATED BY DEFAULT AS IDENTITY,
    TITLE          VARCHAR2(50 CHAR)        NOT NULL,
    AUTHOR         VARCHAR2(100 CHAR)       NOT NULL,
    ISBN           VARCHAR2(13 CHAR) UNIQUE NOT NULL,
    PUBLISHED_YEAR NUMBER(4)                NOT NULL,
    PRICE          NUMBER(8, 2)             NOT NULL,
    CATEGORY       VARCHAR2(50 CHAR)        NOT NULL,

    CONSTRAINT PK_BOOKS PRIMARY KEY (BOOK_ID),
    CONSTRAINT CK_PUBLISHED_YEAR CHECK (PUBLISHED_YEAR >= 1900),
    CONSTRAINT CK_PRICE CHECK (PRICE > 0)
);

COMMENT ON TABLE HAIRBD0028.BOOKS IS 'Table that stores details about each book in the library.';
COMMENT ON COLUMN HAIRBD0028.BOOKS.ISBN IS 'International Standard Book Number. Must be unique.';
COMMENT ON COLUMN HAIRBD0028.BOOKS.PRICE IS 'Price of the book in RON. Must be a non-negative and not-null value.';
COMMENT ON COLUMN HAIRBD0028.BOOKS.CATEGORY IS 'Category of the book.';

/* Index on Author for faster search by author name, it is a common search criteria for books in a library system.
It can be used to quickly find books by a specific author. */
CREATE INDEX IDX_AUTHOR ON HAIRBD0028.BOOKS (AUTHOR);

-----------------------------------------------------------
-- TABLE: MEMBERS
-----------------------------------------------------------

CREATE TABLE HAIRBD0028.MEMBERS
(
    MEMBER_ID       NUMBER GENERATED BY DEFAULT AS IDENTITY,
    FULL_NAME       VARCHAR2(100 CHAR)        NOT NULL,
    EMAIL           VARCHAR2(100 CHAR) UNIQUE NOT NULL,
    PHONE_NUMBER    VARCHAR2(10 CHAR) UNIQUE  NOT NULL,
    MEMBERSHIP_DATE DATE DEFAULT SYSDATE,
    STATUS          VARCHAR2(20)              NOT NULL,

    CONSTRAINT PK_MEMBERS PRIMARY KEY (MEMBER_ID),
    CONSTRAINT CK_MEMBER_STATUS CHECK (STATUS IN ('Active', 'Inactive', 'Banned')),
    CONSTRAINT CK_PHONE_NUMBER CHECK (LENGTH(PHONE_NUMBER) = 10)
);

COMMENT ON TABLE HAIRBD0028.MEMBERS IS 'Table that stores details about library members.';
COMMENT ON COLUMN HAIRBD0028.MEMBERS.EMAIL IS 'Unique email address of the member.';
COMMENT ON COLUMN HAIRBD0028.MEMBERS.PHONE_NUMBER IS 'Unique contact phone number of the member.';
COMMENT ON COLUMN HAIRBD0028.MEMBERS.MEMBERSHIP_DATE IS 'Date when the membership was created.';
COMMENT ON COLUMN HAIRBD0028.MEMBERS.STATUS IS 'Current status of the membership: Active, Inactive, or Banned.';

/* Index on Status to quickly find members by their status.
It can be used to quickly find active, inactive, or banned members. */
CREATE INDEX IDX_MEMBERS_STATUS ON HAIRBD0028.MEMBERS (STATUS);

-----------------------------------------------------------
-- TABLE: LOANS (Many-to-Many relationship between MEMBERS and BOOKS)
-----------------------------------------------------------

CREATE TABLE HAIRBD0028.LOANS
(
    BOOK_ID     NUMBER NOT NULL,
    MEMBER_ID   NUMBER NOT NULL,
    LOAN_DATE   DATE DEFAULT SYSDATE,
    DUE_DATE    DATE   NOT NULL,
    RETURN_DATE DATE,

    CONSTRAINT FK_LOANS_BOOKS FOREIGN KEY (BOOK_ID) REFERENCES HAIRBD0028.Books (BOOK_ID),
    CONSTRAINT FK_LOANS_MEMBERS FOREIGN KEY (MEMBER_ID) REFERENCES HAIRBD0028.MEMBERS (MEMBER_ID),
    CONSTRAINT PK_LOANS PRIMARY KEY (BOOK_ID, MEMBER_ID),
    CONSTRAINT CK_DUE_DATE CHECK (DUE_DATE > LOAN_DATE),
    CONSTRAINT CK_UQ_loan UNIQUE (BOOK_ID, MEMBER_ID, LOAN_DATE)
);

COMMENT ON TABLE HAIRBD0028.LOANS IS 'Table that records each loan transaction of books by members.';
COMMENT ON COLUMN HAIRBD0028.LOANS.LOAN_DATE IS 'Date when the book was loaned.';
COMMENT ON COLUMN HAIRBD0028.LOANS.DUE_DATE IS 'Date when the book should be returned.';
COMMENT ON COLUMN HAIRBD0028.LOANS.RETURN_DATE IS 'Date when the book was actually returned.';

/* Index on DueDate to find upcoming due books. It can be used to quickly find books that are due soon or overdue
and send reminders to members. */
CREATE INDEX IDX_DUE_DATE ON HAIRBD0028.LOANS (DUE_DATE);

-----------------------------------------------------------
-- INDEXES: Indexes for foreign key columns
-----------------------------------------------------------

CREATE INDEX IDX_FK_BOOKS ON HAIRBD0028.LOANS (BOOK_ID);
CREATE INDEX IDX_FK_MEMBERS ON HAIRBD0028.LOANS (MEMBER_ID);

