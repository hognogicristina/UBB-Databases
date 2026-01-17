import logging
from app.data import genre_repo
from app.models.genre import Genre

logger = logging.getLogger(__name__)

class GenreService:
    def create_genre(self, payload: Genre) -> dict:
        self._genre_exists(payload.name)
        self._validate_non_empty_string(payload.name, "Name")
        genre = genre_repo.create_genre(payload.name)
        logger.info("Created genre name=%s", payload.name)
        return genre

    def list_genres(self, page: int, limit: int) -> list[dict]:
        offset = (page - 1) * limit
        return genre_repo.list_genres(limit, offset)

    def count_genres(self) -> int:
        return genre_repo.count_genres()

    def get_genre(self, genre_id: int) -> dict | None:
        return genre_repo.get_genre(genre_id)

    def update_genre(self, genre_id: int, payload: Genre) -> dict | None:
        self._genre_name_exists(payload.name, genre_id)
        self._validate_non_empty_string(payload.name, "Name")
        genre = genre_repo.update_genre(genre_id, payload.name)
        logger.info("Updated genre name=%s", payload.name)
        return genre

    def delete_genre(self, genre_id: int) -> bool:
        self._genre_with_books(genre_id)
        genre = genre_repo.delete_genre(genre_id)
        logger.info("Deleted genre successfully")
        return genre

    @staticmethod
    def _genre_exists(name: str) -> None:
        existing_genres = genre_repo.list_genres(1000, 0)
        for genre in existing_genres:
            if genre["name"].lower() == name.lower():
                raise ValueError("Genre with this name already exists.")

    @staticmethod
    def _genre_name_exists(name: str, genre_id: int) -> None:
        existing_genres = genre_repo.list_genres(1000, 0)
        for genre in existing_genres:
            if genre["name"].lower() == name.lower() and genre["id"] != genre_id:
                raise ValueError("Genre with this name already exists.")

    @staticmethod
    def _genre_with_books(genre_id: int) -> None:
        if genre_repo.has_books(genre_id):
            raise ValueError("Cannot delete genre with existing books")

    @staticmethod
    def _validate_non_empty_string(value: str, field_name: str) -> None:
        if not value.strip():
            raise ValueError(f"{field_name} cannot be empty or just spaces.")
