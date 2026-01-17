import logging
from app.data import loan_repo, book_repo, member_repo

logger = logging.getLogger(__name__)


class LoanService:
    def borrow_book(self, book_id: int, member_id: int) -> dict:
        self._validate_borrow(book_id, member_id)
        self._ensure_member_or_book_exists(book_id, member_id)
        loan = loan_repo.create_loan(book_id, member_id)
        book = book_repo.get_book(book_id)
        member = member_repo.get_member(member_id)
        logger.info("Created a loan for book '%s' to member '%s'", book["title"], member["name"])
        return loan

    def return_book(self, loan_id: int) -> dict:
        self._validate_return(loan_id)
        loan = loan_repo.return_loan(loan_id)
        logger.info("Returned book successfully")
        return loan

    def list_active_loans(self, page: int, limit: int) -> list[dict]:
        offset = (page - 1) * limit
        return loan_repo.list_loans(active_only=True, limit=limit, offset=offset)

    def count_active_loans(self) -> int:
        return loan_repo.count_active_loans()

    def member_history(self, member_id: int, page: int, limit: int) -> list[dict]:
        self._validate_member(member_id)
        offset = (page - 1) * limit
        return loan_repo.member_history(member_id, limit, offset)

    def count_member_history(self, member_id: int) -> int:
        self._validate_member(member_id)
        return loan_repo.count_member_history(member_id)

    def overdue_loans(self) -> list[dict]:
        return loan_repo.overdue_loans()

    def get_active_loans(self, member_id: int) -> list[dict]:
        self._validate_member(member_id)
        return loan_repo.get_active_loans_by_member(member_id)

    @staticmethod
    def _validate_borrow(book_id: int, member_id: int):
        if loan_repo.has_active_loan(book_id, member_id):
            raise ValueError("Member already has an active loan for this book")

    @staticmethod
    def _validate_return(loan_id: int):
        loan = loan_repo.get_loan(loan_id)
        if not loan:
            raise ValueError("Loan not found")
        if loan["return_date"]:
            raise ValueError("Book already returned")

    @staticmethod
    def _validate_member(member_id: int):
        member = member_repo.get_member(member_id)
        if not member:
            raise ValueError("Member not found")

    @staticmethod
    def _ensure_member_or_book_exists(book_id: int | None, member_id: int | None) -> None:
        if book_id is not None:
            if not book_repo.get_book(book_id):
                raise ValueError("Please select a valid book.")
        if member_id is not None:
            if not member_repo.get_member(member_id):
                raise ValueError("Please select a valid member.")
