from app.data.db import get_connection
from app.models.book import BookCreate, BookUpdate

BOOK_SELECT = """
              SELECT b.id,
                     b.title,
                     b.isbn,
                     g.id AS genre_id,
                     g.name AS genre,
                     a.id AS author_id,
                     a.name AS author,
                     CASE
                         WHEN EXISTS (
                             SELECT 1
                             FROM loans l
                             WHERE l.book_id = b.id
                               AND l.return_date IS NULL
                         ) THEN 1
                         ELSE 0
                     END AS is_borrowed
              FROM books b
                       LEFT JOIN book_genres bg ON bg.book_id = b.id
                       LEFT JOIN genres g ON g.id = bg.genre_id
                       LEFT JOIN book_authors ba ON ba.book_id = b.id
                       LEFT JOIN authors a ON a.id = ba.author_id
              """


def row_to_book(row) -> dict:
    return {
        "id": row["id"],
        "title": row["title"],
        "isbn": row["isbn"],
        "genre_id": row["genre_id"],
        "genre": row["genre"],
        "author_id": row["author_id"],
        "author": row["author"],
        "is_borrowed": bool(row["is_borrowed"]),
    }


def replace_book_author(conn, book_id: int, author_id: int) -> None:
    conn.execute("DELETE FROM book_authors WHERE book_id = ?", (book_id,))
    conn.execute(
        "INSERT INTO book_authors (book_id, author_id) VALUES (?, ?)",
        (book_id, author_id),
    )

def replace_book_genre(conn, book_id: int, genre_id: int) -> None:
    conn.execute("DELETE FROM book_genres WHERE book_id = ?", (book_id,))
    conn.execute(
        "INSERT INTO book_genres (book_id, genre_id) VALUES (?, ?)",
        (book_id, genre_id),
    )


def create_book(payload: BookCreate) -> dict:
    with get_connection() as conn:
        cursor = conn.execute(
            """
            INSERT INTO books (title, isbn)
            VALUES (?, ?)
            """,
            (
                payload.title,
                payload.isbn,
            ),
        )

        book_id = cursor.lastrowid
        replace_book_author(conn, book_id, payload.author_id)
        replace_book_genre(conn, book_id, payload.genre_id)
        conn.commit()

    return get_book(book_id)


def get_book(book_id: int) -> dict | None:
    with get_connection() as conn:
        row = conn.execute(
            BOOK_SELECT + " WHERE b.id = ?",
            (book_id,),
        ).fetchone()

    return row_to_book(row) if row else None


def list_books(limit: int, offset: int, genre: str | None = None) -> list[dict]:
    query = BOOK_SELECT
    params = []

    if genre:
        query += " WHERE g.name = ?"
        params.append(genre)

    query += " ORDER BY b.title LIMIT ? OFFSET ?"
    params.extend([limit, offset])

    with get_connection() as conn:
        rows = conn.execute(query, params).fetchall()

    return [row_to_book(r) for r in rows]

def count_books(genre: str | None = None) -> int:
    query = """
            SELECT COUNT(DISTINCT b.id) AS count
            FROM books b
                     LEFT JOIN book_genres bg ON bg.book_id = b.id
                     LEFT JOIN genres g ON g.id = bg.genre_id
            """
    params = []

    if genre:
        query += " WHERE g.name = ?"
        params.append(genre)

    with get_connection() as conn:
        row = conn.execute(query, params).fetchone()
        return row["count"] if row else 0


def list_books_all() -> list[dict]:
    with get_connection() as conn:
        rows = conn.execute(
            BOOK_SELECT + " ORDER BY b.title"
        ).fetchall()

    return [row_to_book(r) for r in rows]


def update_book(book_id: int, payload: BookUpdate) -> dict | None:
    existing = get_book(book_id)
    if not existing:
        return None

    with get_connection() as conn:
        conn.execute(
            """
            UPDATE books
            SET title        = ?,
                isbn         = ?
            WHERE id = ?
            """,
            (
                payload.title or existing["title"],
                payload.isbn or existing["isbn"],
                book_id,
            ),
        )

        if payload.author_id is not None:
            replace_book_author(conn, book_id, payload.author_id)

        if payload.genre_id is not None:
            replace_book_genre(conn, book_id, payload.genre_id)

        conn.commit()

    return get_book(book_id)


def delete_book(book_id: int) -> bool:
    with get_connection() as conn:
        conn.execute("DELETE FROM book_authors WHERE book_id = ?", (book_id,))
        conn.execute("DELETE FROM book_genres WHERE book_id = ?", (book_id,))
        conn.execute("DELETE FROM loans WHERE book_id = ?", (book_id,))
        cursor = conn.execute("DELETE FROM books WHERE id = ?", (book_id,))
        conn.commit()

    return cursor.rowcount > 0


def get_active_loans_count(book_id: int) -> int:
    with get_connection() as conn:
        row = conn.execute(
            "SELECT COUNT(*) AS count FROM loans WHERE book_id = ? AND return_date IS NULL",
            (book_id,),
        ).fetchone()

    return row["count"] if row else 0


def has_active_loans(book_id: int) -> bool:
    return get_active_loans_count(book_id) > 0
