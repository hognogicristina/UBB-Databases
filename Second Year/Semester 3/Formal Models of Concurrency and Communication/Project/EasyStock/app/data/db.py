import sqlite3
from pathlib import Path
from datetime import datetime, timedelta
import random

DB_PATH = Path(__file__).resolve().parent.parent.parent / "data" / "easystock.db"


def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db() -> None:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)

    with get_connection() as conn:
        create_tables(conn)
        migrate_book_genres(conn)
        seed_if_empty(conn)
        conn.commit()


def create_tables(conn: sqlite3.Connection) -> None:
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS genres (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE
        );

        CREATE TABLE IF NOT EXISTS authors (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            birth_year INTEGER
        );

        CREATE TABLE IF NOT EXISTS books (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            isbn TEXT NOT NULL UNIQUE
        );

        CREATE TABLE IF NOT EXISTS book_authors (
            book_id INTEGER NOT NULL,
            author_id INTEGER NOT NULL,
            PRIMARY KEY (book_id, author_id),
            FOREIGN KEY (book_id) REFERENCES books (id),
            FOREIGN KEY (author_id) REFERENCES authors (id)
        );

        CREATE TABLE IF NOT EXISTS book_genres (
            book_id INTEGER NOT NULL,
            genre_id INTEGER NOT NULL,
            PRIMARY KEY (book_id, genre_id),
            FOREIGN KEY (book_id) REFERENCES books (id),
            FOREIGN KEY (genre_id) REFERENCES genres (id)
        );

        CREATE TABLE IF NOT EXISTS members (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT NOT NULL UNIQUE,
            registered_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS loans (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            book_id INTEGER NOT NULL,
            member_id INTEGER NOT NULL,
            loan_date TEXT NOT NULL,
            return_date TEXT,
            FOREIGN KEY (book_id) REFERENCES books (id),
            FOREIGN KEY (member_id) REFERENCES members (id)
        );
        """
    )


def table_empty(conn: sqlite3.Connection, table: str) -> bool:
    return conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0] == 0


def table_has_column(conn: sqlite3.Connection, table: str, column: str) -> bool:
    rows = conn.execute(f"PRAGMA table_info({table})").fetchall()
    return any(row["name"] == column for row in rows)


def migrate_book_genres(conn: sqlite3.Connection) -> None:
    if not table_has_column(conn, "books", "genre_id"):
        return
    if not table_empty(conn, "book_genres"):
        return

    rows = conn.execute(
        "SELECT id, genre_id FROM books WHERE genre_id IS NOT NULL"
    ).fetchall()
    if not rows:
        return

    conn.executemany(
        "INSERT OR IGNORE INTO book_genres (book_id, genre_id) VALUES (?, ?)",
        [(row["id"], row["genre_id"]) for row in rows],
    )


def seed_if_empty(conn: sqlite3.Connection) -> None:
    if table_empty(conn, "genres"):
        seed_genres(conn)

    if table_empty(conn, "authors"):
        seed_authors(conn)

    if table_empty(conn, "books"):
        seed_books(conn)
        seed_book_authors(conn)
        seed_book_genres(conn)

    if table_empty(conn, "members"):
        seed_members(conn)

    if table_empty(conn, "loans"):
        seed_loans(conn)


def seed_genres(conn: sqlite3.Connection) -> None:
    genres = [
        ("Sci-Fi",),
        ("Fantasy",),
        ("Dystopian",),
        ("Classic",),
        ("Horror",),
        ("Mystery",),
    ]
    conn.executemany("INSERT INTO genres (name) VALUES (?)", genres)


def seed_authors(conn: sqlite3.Connection) -> None:
    authors = [
        ("Frank Herbert", 1920),
        ("J.R.R. Tolkien", 1892),
        ("George Orwell", 1903),
        ("Jane Austen", 1775),
        ("Andy Weir", 1972),
        ("Harper Lee", 1926),
        ("Aldous Huxley", 1894),
        ("Ursula K. Le Guin", 1929),
        ("Isaac Asimov", 1920),
        ("Philip K. Dick", 1928),
        ("Stephen King", 1947),
        ("Neil Gaiman", 1960),
        ("Brandon Sanderson", 1975),
        ("Agatha Christie", 1890),
    ]

    conn.executemany(
        "INSERT INTO authors (name, birth_year) VALUES (?, ?)",
        authors,
    )


def seed_books(conn: sqlite3.Connection) -> None:
    books = [
        ("Dune", "9780441172719", "Sci-Fi"),
        ("The Hobbit", "9780345339683", "Fantasy"),
        ("1984", "9780451524935", "Dystopian"),
        ("Pride and Prejudice", "9780141439518", "Classic"),
        ("The Martian", "9780553418026", "Sci-Fi"),
        ("To Kill a Mockingbird", "9780061120084", "Classic"),
        ("Brave New World", "9780060850524", "Dystopian"),
        ("Foundation", "9780553293357", "Sci-Fi"),
        ("The Shining", "9780307743657", "Horror"),
        ("Mistborn", "9780765350381", "Fantasy"),
        ("Murder on the Orient Express", "9780062693662", "Mystery"),
    ]

    rows = [(title, isbn) for title, isbn, _genre in books]
    conn.executemany("INSERT INTO books (title, isbn) VALUES (?, ?)", rows)


def seed_book_genres(conn: sqlite3.Connection) -> None:
    books = [
        ("Dune", "Sci-Fi"),
        ("The Hobbit", "Fantasy"),
        ("1984", "Dystopian"),
        ("Pride and Prejudice", "Classic"),
        ("The Martian", "Sci-Fi"),
        ("To Kill a Mockingbird", "Classic"),
        ("Brave New World", "Dystopian"),
        ("Foundation", "Sci-Fi"),
        ("The Shining", "Horror"),
        ("Mistborn", "Fantasy"),
        ("Murder on the Orient Express", "Mystery"),
    ]

    genre_map = {
        row["name"]: row["id"]
        for row in conn.execute("SELECT id, name FROM genres")
    }
    book_map = {
        row["title"]: row["id"]
        for row in conn.execute("SELECT id, title FROM books")
    }

    conn.executemany(
        "INSERT INTO book_genres (book_id, genre_id) VALUES (?, ?)",
        [(book_map[title], genre_map[genre]) for title, genre in books],
    )


def seed_book_authors(conn: sqlite3.Connection) -> None:
    authors = {r["name"]: r["id"] for r in conn.execute("SELECT * FROM authors")}
    books = {r["title"]: r["id"] for r in conn.execute("SELECT * FROM books")}

    relations = [
        ("Dune", "Frank Herbert"),
        ("The Hobbit", "J.R.R. Tolkien"),
        ("1984", "George Orwell"),
        ("Pride and Prejudice", "Jane Austen"),
        ("The Martian", "Andy Weir"),
        ("To Kill a Mockingbird", "Harper Lee"),
        ("Brave New World", "Aldous Huxley"),
        ("Foundation", "Isaac Asimov"),
        ("The Shining", "Stephen King"),
        ("Mistborn", "Brandon Sanderson"),
        ("Murder on the Orient Express", "Agatha Christie"),
    ]

    conn.executemany(
        "INSERT INTO book_authors (book_id, author_id) VALUES (?, ?)",
        [(books[b], authors[a]) for b, a in relations],
    )


def seed_members(conn: sqlite3.Connection) -> None:
    base_date = datetime.utcnow() - timedelta(days=90)

    members = [
        ("Alex Morgan", "alex@example.com"),
        ("Priya Patel", "priya@example.com"),
        ("Diego Ramirez", "diego@example.com"),
        ("Elena Popescu", "elena@example.com"),
        ("Andrei Ionescu", "andrei@example.com"),
    ]

    rows = []
    for name, email in members:
        registered_at = base_date + timedelta(days=random.randint(0, 60))
        rows.append((name, email, registered_at.isoformat(timespec="seconds")))

    conn.executemany(
        "INSERT INTO members (name, email, registered_at) VALUES (?, ?, ?)",
        rows,
    )


def seed_loans(conn: sqlite3.Connection) -> None:
    members = conn.execute("SELECT * FROM members").fetchall()
    books = conn.execute("SELECT * FROM books").fetchall()
    loans = []

    for book in books:
        member = random.choice(members)
        registered_at = datetime.fromisoformat(member["registered_at"])
        history_count = random.randint(1, 3)

        last_loan_date = registered_at

        for i in range(history_count):
            loan_date = last_loan_date + timedelta(days=random.randint(10, 40))
            is_active = i == history_count - 1 and random.choice([True, False])
            is_overdue = is_active and random.choice([True, False])

            if is_active:
                if is_overdue:
                    loan_date = datetime.utcnow() - timedelta(days=random.randint(15, 40))
                return_date = None
            else:
                return_date = loan_date + timedelta(days=random.randint(7, 30))

            loans.append(
                (
                    book["id"],
                    member["id"],
                    loan_date.isoformat(timespec="seconds"),
                    return_date.isoformat(timespec="seconds") if return_date else None,
                )
            )

            last_loan_date = loan_date

    conn.executemany(
        """
        INSERT INTO loans (book_id, member_id, loan_date, return_date)
        VALUES (?, ?, ?, ?)
        """,
        loans,
    )
