from datetime import datetime
from app.data.db import get_connection
from app.models.member import Member


def create_member(payload: Member) -> dict:
    registered_at = datetime.utcnow().isoformat(timespec="seconds")
    with get_connection() as conn:
        cursor = conn.execute(
            "INSERT INTO members (name, email, registered_at) VALUES (?, ?, ?)",
            (payload.name, payload.email, registered_at),
        )
        conn.commit()
        return get_member(cursor.lastrowid)


def get_member(member_id: int) -> dict | None:
    with get_connection() as conn:
        row = conn.execute(
            "SELECT id, name, email, registered_at FROM members WHERE id = ?",
            (member_id,),
        ).fetchone()
        return dict(row) if row else None


def update_member(member_id: int, payload: Member) -> dict | None:
    with get_connection() as conn:
        cursor = conn.execute(
            "UPDATE members SET name = ?, email = ? WHERE id = ?",
            (payload.name, payload.email, member_id),
        )
        conn.commit()
        if cursor.rowcount == 0:
            return None
        return get_member(member_id)


def list_members(limit: int, offset: int) -> list[dict]:
    with get_connection() as conn:
        rows = conn.execute(
            """
            SELECT id, name, email, registered_at
            FROM members
            ORDER BY name ASC
            LIMIT ? OFFSET ?
            """,
            (limit, offset),
        ).fetchall()
        return [dict(row) for row in rows]

def count_members() -> int:
    with get_connection() as conn:
        row = conn.execute("SELECT COUNT(*) AS count FROM members").fetchone()
        return row["count"] if row else 0


def delete_member(member_id: int) -> bool:
    with get_connection() as conn:
        conn.execute("DELETE FROM loans WHERE member_id = ?", (member_id,))
        cursor = conn.execute("DELETE FROM members WHERE id = ?", (member_id,))
        conn.commit()
        return cursor.rowcount > 0


def has_active_loans(member_id: int) -> bool:
    with get_connection() as conn:
        row = conn.execute(
            """
            SELECT 1
            FROM loans
            WHERE member_id = ? AND return_date IS NULL
            LIMIT 1
            """,
            (member_id,),
        ).fetchone()
        return row is not None


def members_with_active_loans() -> list[dict]:
    with get_connection() as conn:
        rows = conn.execute(
            """
            SELECT m.id AS member_id, m.name, m.email, COUNT(l.id) AS active_loans
            FROM members m
            JOIN loans l ON l.member_id = m.id
            WHERE l.return_date IS NULL
            GROUP BY m.id
            ORDER BY active_loans DESC, m.name ASC
            """
        ).fetchall()
        return [dict(row) for row in rows]
