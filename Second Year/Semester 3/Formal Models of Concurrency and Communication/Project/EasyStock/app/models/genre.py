from pydantic import BaseModel


class Genre(BaseModel):
    id: int | None = None
    name: str


class GenreOut(BaseModel):
    id: int
    name: str
