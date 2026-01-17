from app.data.db import get_connection


def create_genre(name: str) -> dict:
    with get_connection() as conn:
        cursor = conn.execute(
            "INSERT INTO genres (name) VALUES (?)",
            (name,),
        )
        conn.commit()
        return get_genre(cursor.lastrowid)


def list_genres(limit: int, offset: int) -> list[dict]:
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT id, name FROM genres ORDER BY name LIMIT ? OFFSET ?",
            (limit, offset),
        ).fetchall()
    return [dict(row) for row in rows]


def count_genres() -> int:
    with get_connection() as conn:
        row = conn.execute("SELECT COUNT(*) AS count FROM genres").fetchone()
        return row["count"] if row else 0


def get_genre(genre_id: int) -> dict | None:
    with get_connection() as conn:
        row = conn.execute(
            "SELECT id, name FROM genres WHERE id = ?",
            (genre_id,),
        ).fetchone()
        return dict(row) if row else None


def update_genre(genre_id: int, name: str) -> dict | None:
    with get_connection() as conn:
        cursor = conn.execute(
            "UPDATE genres SET name = ? WHERE id = ?",
            (name, genre_id),
        )
        conn.commit()
        if cursor.rowcount == 0:
            return None
        return get_genre(genre_id)


def delete_genre(genre_id: int) -> bool:
    with get_connection() as conn:
        conn.execute("DELETE FROM book_genres WHERE genre_id = ?", (genre_id,))
        cursor = conn.execute("DELETE FROM genres WHERE id = ?", (genre_id,))
        conn.commit()
        return cursor.rowcount > 0


def has_books(genre_id: int) -> bool:
    with get_connection() as conn:
        row = conn.execute(
            "SELECT 1 FROM book_genres WHERE genre_id = ? LIMIT 1",
            (genre_id,),
        ).fetchone()
        return row is not None
