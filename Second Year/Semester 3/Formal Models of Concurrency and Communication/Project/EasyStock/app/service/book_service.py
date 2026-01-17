import logging
from app.data import book_repo, author_repo, genre_repo
from app.models.book import BookCreate, BookUpdate

logger = logging.getLogger(__name__)


class BookService:
    def create_book(self, payload: BookCreate) -> dict:
        self._ensure_isbn_unique(payload.isbn)
        self._validate_isbn(payload.isbn)
        self._ensure_author_exists(payload.author_id)
        self._ensure_genre_exists(payload.genre_id)
        self._validate_non_empty_string(payload.title, "Title")
        book = book_repo.create_book(payload)
        logger.info("Created book title=%s", payload.title)
        return book

    def get_book(self, book_id: int) -> dict | None:
        return book_repo.get_book(book_id)

    def list_books(
        self,
        page: int,
        limit: int,
        genre: str | None = None,
    ) -> list[dict]:
        offset = (page - 1) * limit
        return book_repo.list_books(limit, offset, genre)

    def count_books(self, genre: str | None = None) -> int:
        return book_repo.count_books(genre)

    def update_book(self, book_id: int, payload: BookUpdate) -> dict | None:
        self._ensure_isbn_unique_update(payload.isbn, book_id)
        self._ensure_author_exists(payload.author_id)
        self._ensure_genre_exists(payload.genre_id)
        self._validate_isbn(payload.isbn)
        self._validate_non_empty_string(payload.title, "Title")
        book = book_repo.update_book(book_id, payload)
        logger.info("Updated book title=%s", payload.title)
        return book

    def delete_book(self, book_id: int) -> bool:
        self._validate_no_active_loans(book_id)
        book = book_repo.delete_book(book_id)
        logger.info("Deleted book successfully")
        return book

    @staticmethod
    def _ensure_author_exists(author_id: int | None) -> None:
        if author_id is None:
            return
        if not author_repo.get_author(author_id):
            raise ValueError("Please select a valid author.")

    @staticmethod
    def _ensure_genre_exists(genre_id: int | None) -> None:
        if genre_id is None:
            return
        if not genre_repo.get_genre(genre_id):
            raise ValueError("Please select a valid genre.")

    @staticmethod
    def _validate_non_empty_string(value: str, field_name: str) -> None:
        if not value.strip():
            raise ValueError(f"{field_name} cannot be empty or just spaces.")

    @staticmethod
    def _validate_isbn(isbn: str) -> None:
        if len(isbn) != 13 or not isbn.isdigit():
            raise ValueError("ISBN must be exactly 13 digits.")

    @staticmethod
    def _ensure_isbn_unique(isbn: str) -> None:
        existing_books = book_repo.list_books(1000, 0)
        for book in existing_books:
            if book["isbn"] == isbn:
                raise ValueError("Book already exists.")

    @staticmethod
    def _ensure_isbn_unique_update(isbn: str, book_id: int) -> None:
        existing_books = book_repo.list_books(1000, 0)
        for book in existing_books:
            if book["isbn"] == isbn and book["id"] != book_id:
                raise ValueError("Book already exists.")

    @staticmethod
    def _validate_no_active_loans(book_id: int) -> None:
        if book_repo.has_active_loans(book_id):
            raise ValueError("Cannot delete book with active loans")
