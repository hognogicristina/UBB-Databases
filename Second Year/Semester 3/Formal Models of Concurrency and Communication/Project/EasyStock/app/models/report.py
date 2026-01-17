from pydantic import BaseModel

class MemberActiveLoan(BaseModel):
    member_id: int
    name: str
    email: str
    active_loans: int

class MemberBorrowRecord(BaseModel):
    loan_id: int
    book_id: int
    book_title: str
    loan_date: str
    return_date: str | None

class OverdueLoan(BaseModel):
    loan_id: int
    book_title: str
    member_name: str
    loan_date: str
    days_overdue: int
