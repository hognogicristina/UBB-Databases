from pydantic import BaseModel

class LoanCreate(BaseModel):
    book_id: int
    member_id: int

class LoanOut(BaseModel):
    id: int
    book_id: int
    member_id: int
    book_title: str
    member_name: str
    loan_date: str
    return_date: str | None
