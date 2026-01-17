from app.data.db import get_connection
from app.models.author import Author


def create_author(payload: Author) -> dict:
    with get_connection() as conn:
        cursor = conn.execute(
            "INSERT INTO authors (name, birth_year) VALUES (?, ?)",
            (payload.name, payload.birth_year),
        )
        conn.commit()
        return get_author(cursor.lastrowid)


def list_authors(limit: int, offset: int) -> list[dict]:
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT id, name, birth_year FROM authors ORDER BY name LIMIT ? OFFSET ?",
            (limit, offset),
        ).fetchall()
        return [dict(row) for row in rows]

def count_authors() -> int:
    with get_connection() as conn:
        row = conn.execute("SELECT COUNT(*) AS count FROM authors").fetchone()
        return row["count"] if row else 0


def get_author(author_id: int) -> dict | None:
    with get_connection() as conn:
        row = conn.execute(
            "SELECT id, name, birth_year FROM authors WHERE id = ?",
            (author_id,),
        ).fetchone()
        return dict(row) if row else None


def update_author(author_id: int, payload: Author) -> dict | None:
    with get_connection() as conn:
        cursor = conn.execute(
            "UPDATE authors SET name = ?, birth_year = ? WHERE id = ?",
            (payload.name, payload.birth_year, author_id),
        )
        conn.commit()
        if cursor.rowcount == 0:
            return None
        return get_author(author_id)


def delete_author(author_id: int) -> bool:
    with get_connection() as conn:
        conn.execute("DELETE FROM book_authors WHERE author_id = ?", (author_id,))
        cursor = conn.execute("DELETE FROM authors WHERE id = ?", (author_id,))
        conn.commit()
        return cursor.rowcount > 0


def has_books(author_id: int) -> bool:
    with get_connection() as conn:
        row = conn.execute(
            "SELECT 1 FROM book_authors WHERE author_id = ? LIMIT 1",
            (author_id,),
        ).fetchone()
        return row is not None
