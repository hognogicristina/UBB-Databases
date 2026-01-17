from datetime import datetime
from app.data.db import get_connection


def create_loan(book_id: int, member_id: int) -> dict:
    loan_date = datetime.utcnow().isoformat(timespec="seconds")
    with get_connection() as conn:
        cursor = conn.execute(
            """
            INSERT INTO loans (book_id, member_id, loan_date, return_date)
            VALUES (?, ?, ?, NULL)
            """,
            (book_id, member_id, loan_date),
        )
        conn.commit()
        return get_loan(cursor.lastrowid)


def has_active_loan(book_id: int, member_id: int) -> bool:
    with get_connection() as conn:
        row = conn.execute(
            """
            SELECT 1
            FROM loans
            WHERE book_id = ? AND member_id = ? AND return_date IS NULL
            LIMIT 1
            """,
            (book_id, member_id),
        ).fetchone()
        return row is not None


def return_loan(loan_id: int) -> dict | None:
    return_date = datetime.utcnow().isoformat(timespec="seconds")
    with get_connection() as conn:
        cursor = conn.execute(
            """
            UPDATE loans
            SET return_date = ?
            WHERE id = ? AND return_date IS NULL
            """,
            (return_date, loan_id),
        )
        conn.commit()
        if cursor.rowcount == 0:
            return None
    return get_loan(loan_id)


def get_loan(loan_id: int) -> dict | None:
    with get_connection() as conn:
        row = conn.execute(
            """
            SELECT l.id, l.book_id, l.member_id, l.loan_date, l.return_date,
                   b.title AS book_title,
                   m.name AS member_name
            FROM loans l
            JOIN books b ON b.id = l.book_id
            JOIN members m ON m.id = l.member_id
            WHERE l.id = ?
            """,
            (loan_id,),
        ).fetchone()
        return dict(row) if row else None


def list_loans(active_only: bool = False, limit: int = 10, offset: int = 0) -> list[dict]:
    query = """
        SELECT l.id, l.book_id, l.member_id, l.loan_date, l.return_date,
               b.title AS book_title,
               m.name AS member_name
        FROM loans l
        JOIN books b ON b.id = l.book_id
        JOIN members m ON m.id = l.member_id
    """
    if active_only:
        query += " WHERE l.return_date IS NULL"
    query += " ORDER BY l.loan_date DESC LIMIT ? OFFSET ?"

    with get_connection() as conn:
        rows = conn.execute(query, (limit, offset)).fetchall()
        return [dict(row) for row in rows]

def count_active_loans() -> int:
    with get_connection() as conn:
        row = conn.execute(
            "SELECT COUNT(*) AS count FROM loans WHERE return_date IS NULL"
        ).fetchone()
        return row["count"] if row else 0

def count_member_history(member_id: int) -> int:
    with get_connection() as conn:
        row = conn.execute(
            "SELECT COUNT(*) AS count FROM loans WHERE member_id = ?",
            (member_id,),
        ).fetchone()
        return row["count"] if row else 0


def member_history(member_id: int, limit: int, offset: int) -> list[dict]:
    with get_connection() as conn:
        rows = conn.execute(
            """
            SELECT l.id AS loan_id, l.book_id, l.loan_date, l.return_date,
                   b.title AS book_title
            FROM loans l
            JOIN books b ON b.id = l.book_id
            WHERE l.member_id = ?
            ORDER BY l.loan_date DESC
            LIMIT ? OFFSET ?
            """,
            (member_id, limit, offset),
        ).fetchall()
        return [dict(row) for row in rows]


def overdue_loans() -> list[dict]:
    with get_connection() as conn:
        rows = conn.execute(
            """
            SELECT l.id AS loan_id,
                   b.title AS book_title,
                   m.name AS member_name,
                   l.loan_date,
                   CAST((julianday('now') - julianday(l.loan_date)) - 14 AS INTEGER) AS days_overdue
            FROM loans l
            JOIN books b ON b.id = l.book_id
            JOIN members m ON m.id = l.member_id
            WHERE l.return_date IS NULL
              AND l.loan_date < datetime('now', '-14 days')
            ORDER BY days_overdue DESC, l.loan_date ASC
            """
        ).fetchall()
        return [dict(row) for row in rows]
