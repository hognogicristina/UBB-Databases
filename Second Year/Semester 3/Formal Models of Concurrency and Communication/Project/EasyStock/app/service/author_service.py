import logging
from app.data import author_repo
from app.models.author import Author

logger = logging.getLogger(__name__)


class AuthorService:
    def create_author(self, payload: Author) -> dict:
        self._author_name_exists(payload.name, payload.birth_year, None)
        self._validate_year(payload.birth_year)
        self._validate_non_empty_string(payload.name, "Name")
        author = author_repo.create_author(payload)
        logger.info("Created author name=%s", payload.name)
        return author

    def list_authors(self, page: int, limit: int) -> list[dict]:
        offset = (page - 1) * limit
        return author_repo.list_authors(limit, offset)

    def count_authors(self) -> int:
        return author_repo.count_authors()

    def delete_author(self, author_id: int) -> bool:
        self._author_with_books(author_id)
        author = author_repo.delete_author(author_id)
        logger.info("Deleted author successfully")
        return author

    def get_author(self, author_id: int) -> dict | None:
        return author_repo.get_author(author_id)

    def update_author(self, author_id: int, payload: Author) -> dict | None:
        self._author_name_exists(payload.name, payload.birth_year, author_id)
        self._validate_year(payload.birth_year)
        self._validate_non_empty_string(payload.name, "Name")
        author = author_repo.update_author(author_id, payload)
        logger.info("Updated author name=%s", payload.name)
        return author

    @staticmethod
    def _author_name_exists(name: str, birth_year: int | None, author_id: int | None = None) -> None:
        existing_authors = author_repo.list_authors(1000, 0)
        for author in existing_authors:
            if (author["name"].lower() == name.lower() and author["birth_year"] == birth_year and (
                    author_id is None or author["id"] != author_id)):
                raise ValueError("An author with the same name and birth year already exists.")

    @staticmethod
    def _author_with_books(author_id: int) -> None:
        if author_repo.has_books(author_id):
            raise ValueError("Cannot delete author with existing books")

    @staticmethod
    def _validate_year(birth_year: int | None) -> None:
        if not isinstance(birth_year, int):
            raise ValueError("Birth year must be a number.")

        if birth_year < 1000 or birth_year > 9999:
            raise ValueError("Year must be a 4 digit number.")

    @staticmethod
    def _validate_non_empty_string(value: str, field_name: str) -> None:
        if not value.strip():
            raise ValueError(f"{field_name} cannot be empty or just spaces.")
