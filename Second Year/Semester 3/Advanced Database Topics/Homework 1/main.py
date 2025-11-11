import cx_Oracle
import random
from datetime import datetime, timedelta, date

cx_Oracle.init_oracle_client(lib_dir='/Users/cristinahognogi/instantclient_23_3')
username = 'hairbd0028'
password = 'hairbd002804'
dsn = '193.231.20.20:15211/orcl19c'

conn = cx_Oracle.connect(user=username, password=password, dsn=dsn, encoding="UTF-8")
cur = conn.cursor()


def random_datetime(start_dt: datetime, end_dt: datetime) -> datetime:
    # Random datetime between start_dt and end_dt (format: YYYY-MM-DD HH:MM:SS)
    delta = end_dt - start_dt
    seconds = int(delta.total_seconds())
    return start_dt + timedelta(seconds=random.randint(0, seconds))


male_first_names = ["Andrei", "Mihai", "Vlad", "Tudor", "Radu", "Ionut", "Florin", "Dorin", "Sergiu", "Paul"]
female_first_names = ["Ana", "Ioana", "Maria", "Elena", "Roxana", "Cristina", "Daria", "Monica", "Iulia", "Alexandra"]
last_names = ["Popescu", "Ionescu", "Georgescu", "Dumitrescu", "Muresan", "Stan", "Marin", "Radu", "Morar", "Ilie"]

shelves = ["A1-S1", "A1-S2", "A2-S1", "A3-S2", "B1-S3", "B2-S1", "C1-S2", "C2-S1", "D1-S3", "D2-S2"]
conditions = ["NEW", "FINE", "GOOD", "FAIR", "POOR"]

authors_seed = [
    (1, "J.K. Rowling", "UK"),
    (2, "George R.R. Martin", "USA"),
    (3, "Haruki Murakami", "Japan"),
    (4, "Gabriel García Márquez", "Colombia"),
    (5, "Margaret Atwood", "Canada"),
]

books_seed = [
    (1, "Harry Potter and the Philosopher's Stone", "Fantasy", 1997, 1),
    (2, "A Game of Thrones", "Fantasy", 1996, 2),
    (3, "Kafka on the Shore", "Magical Realism", 2002, 3),
    (4, "One Hundred Years of Solitude", "Magical Realism", 1967, 4),
    (5, "The Handmaid's Tale", "Dystopian", 1985, 5),
    (6, "Norwegian Wood", "Fiction", 1987, 3),
]


def insert_authors():
    cur.executemany(
        "INSERT INTO HAIRBD0028.AUTHORS (AUTHOR_ID, AUTHOR_NAME, NATIONALITY) VALUES (:1, :2, :3)",
        authors_seed
    )


def insert_books():
    cur.executemany(
        "INSERT INTO HAIRBD0028.BOOKS (BOOK_ID, TITLE, GENRE, PUBLICATION_YEAR, AUTHOR_ID) VALUES (:1, :2, :3, :4, :5)",
        books_seed
    )


def insert_members(n=50, start_id=1):
    """
    Insert n members with unique email and phone.
    :param n: Number of members to insert.
    :param start_id: Starting MEMBER_ID.
    """
    rows = []
    for i in range(n):
        member_id = start_id + i
        gender = random.choice(["M", "F"])
        fn = random.choice(male_first_names if gender == "M" else female_first_names)
        ln = random.choice(last_names)
        name = f"{fn} {ln}"
        email = f"{fn.lower()}.{ln.lower()}.{member_id}@example.com"
        phone = f"07{random.randint(0, 9)}{random.randint(1000000, 9999999)}"
        join_dt = random_datetime(datetime(2020, 1, 1, 0, 0, 0), datetime(2024, 12, 31, 23, 59, 59))
        rows.append((member_id, name, email, phone, join_dt))
    cur.executemany(
        """
        INSERT INTO HAIRBD0028.MEMBERS (MEMBER_ID, MEMBER_NAME, EMAIL, PHONE, JOIN_DATE)
        VALUES (:1, :2, :3, :4, :5)
        """,
        rows
    )


def insert_book_copies(min_copies=3, max_copies=4, start_copy_id=1):
    """
    Insert book copies for each book in books_seed.
    Each book gets between min_copies and max_copies copies.
    :return: List of inserted COPY_IDs.
    """
    copy_rows = []
    next_id = start_copy_id
    for (book_id, *_rest) in [(b[0],) for b in books_seed]:
        copies_for_book = random.randint(min_copies, max_copies)
        for _ in range(copies_for_book):
            shelf = random.choice(shelves)
            cond = random.choice(conditions)
            copy_rows.append((next_id, book_id, shelf, cond))
            next_id += 1
    cur.executemany(
        """
        INSERT INTO HAIRBD0028.BOOK_COPIES (COPY_ID, BOOK_ID, SHELF_LOCATION, CONDITION_DESC)
        VALUES (:1, :2, :3, :4)
        """,
        copy_rows
    )
    return [r[0] for r in copy_rows]


def insert_loans_at_least(count=60, members_range=(1, 50), copies=None, start_loan_id=1):
    """
    Insert >= count loans with realistic validity.
    - Some RETURNED (valid_end set), some still ACTIVE (valid_end NULL).
    - Some members re-borrow later (same or different copy).
    - Exactly one loan (the first) will use the precise timestamp FIXED_FIRST_LOAN_TS if USE_FIXED_FIRST_LOAN_TS is True.
    """
    if not copies:
        raise ValueError("Copies list must be provided")

    # use datetimes to preserve time components
    start_date_dt = datetime(2024, 9, 15, 0, 0, 0)
    end_date_dt = datetime(2025, 10, 15, 23, 59, 59)

    rows = []
    loan_id = start_loan_id
    target = max(count, 65)

    for idx in range(target):
        member_id = random.randint(members_range[0], members_range[1])
        copy_id = random.choice(copies)
        start_dt = random_datetime(start_date_dt, end_date_dt)

        # 70% RETURNED, 30% ACTIVE
        returned = random.random() < 0.7
        if returned:
            # return within 7-45 days after start (cap to end_date_dt)
            end_candidate = start_dt + timedelta(days=random.randint(7, 45))
            # add random time component within that day
            end_candidate += timedelta(hours=random.randint(0, 23),
                                       minutes=random.randint(0, 59),
                                       seconds=random.randint(0, 59))
            # make sure we don't go past the overall end date
            end_candidate = min(end_candidate, end_date_dt)
            if end_candidate < start_dt:
                end_candidate = start_dt # edge case if start_dt is very close to end_date_dt
            valid_end_dt = end_candidate
            status = 'RETURNED'
        else:
            valid_end_dt = None
            status = 'ACTIVE'

        # cx_Oracle will bind Python datetime to Oracle DATE (with time) correctly
        rows.append((loan_id, member_id, copy_id, start_dt, valid_end_dt, status))
        loan_id += 1

    cur.executemany(
        """
        INSERT INTO HAIRBD0028.LOANS (LOAN_ID, MEMBER_ID, COPY_ID, VALID_START, VALID_END, STATUS)
        VALUES (:1, :2, :3, :4, :5, :6)
        """,
        rows
    )

    # Re-borrowing events: 10 members borrow again later
    reborrow_rows = []
    for member_id in random.sample(range(members_range[0], members_range[1] + 1), k=10):
        # start some time in 2025 with midnight time
        copy_id = random.choice(copies)
        start_dt = random_datetime(datetime(2025, 1, 1, 0, 0, 0), end_date_dt)

        if random.random() < 0.4:
            valid_end_dt = None
            status = 'ACTIVE'
        else:
            end_candidate = start_dt + timedelta(days=random.randint(5, 30))
            end_candidate += timedelta(hours=random.randint(0, 23),
                                       minutes=random.randint(0, 59),
                                       seconds=random.randint(0, 59))
            end_candidate = min(end_candidate, end_date_dt)
            if end_candidate < start_dt:
                end_candidate = start_dt
            valid_end_dt = end_candidate
            status = 'RETURNED'
        reborrow_rows.append((loan_id, member_id, copy_id, start_dt, valid_end_dt, status))
        loan_id += 1

    cur.executemany(
        """
        INSERT INTO HAIRBD0028.LOANS (LOAN_ID, MEMBER_ID, COPY_ID, VALID_START, VALID_END, STATUS)
        VALUES (:1, :2, :3, :4, :5, :6)
        """,
        reborrow_rows
    )


def simulate_transaction_time_updates(copies, members_range=(1, 50)):
    """
    Touch book_copies (to fill book_copies_history) and loans (to fill loans_history).
    No member updates; members is plain now.
    """
    # Update 6 book copies: change shelf/condition (triggers history)
    to_update_copies = random.sample(copies, k=min(6, len(copies)))
    for cid in to_update_copies:
        new_shelf = random.choice(shelves)
        new_cond = random.choice(conditions)
        cur.execute(
            """
            UPDATE HAIRBD0028.BOOK_COPIES
            SET SHELF_LOCATION = :1,
                   CONDITION_DESC = :2
            WHERE COPY_ID = :3
            """,
            (new_shelf, new_cond, cid)
        )

    # Update 8 loans:
    # - Some get a valid_end now (RETURNED)
    cur.execute("SELECT LOAN_ID, VALID_START FROM HAIRBD0028.LOANS")
    all_loans = cur.fetchall()
    for (loan_id, vstart) in random.sample(all_loans, k=min(8, len(all_loans))):
        if random.random() < 0.6:
            new_end = vstart + timedelta(days=random.randint(7, 30))
            cur.execute(
                "UPDATE HAIRBD0028.LOANS SET VALID_END = :1, STATUS = 'RETURNED' WHERE LOAN_ID = :2",
                (new_end, loan_id)
            )


def main():
    print("Seeding authors...")
    insert_authors()
    print("Seeding books...")
    insert_books()
    print("Seeding members (50, unique email/phone)...")
    insert_members(n=50, start_id=1)
    print("Seeding book copies (3–4 per book)...")
    copies = insert_book_copies(min_copies=3, max_copies=4, start_copy_id=1)

    print("Inserting >= 60 loans with realistic valid-time changes...")
    insert_loans_at_least(count=60, members_range=(1, 50), copies=copies, start_loan_id=1)

    print("Simulating transaction-time updates for history...")
    simulate_transaction_time_updates(copies, members_range=(1, 50))

    conn.commit()
    print("Done. Commit complete.")


try:
    main()
except Exception as e:
    conn.rollback()
    print("Error, rolled back:", e)
finally:
    cur.close()
    conn.close()
